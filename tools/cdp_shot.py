#!/usr/bin/env python3
"""Drive the shared Chromium (N305 Stack 58) over CDP to screenshot + smoke-test Briefato staging.

Usage:
  .venv/bin/python tools/cdp_shot.py fields <url>          # list form fields of a page
  .venv/bin/python tools/cdp_shot.py shots                 # full visual pass -> artifacts/

Endpoint: ws://172.18.0.50:9223 (static IP; DevTools rejects non-IP Host headers).
The Chromium container reaches the portal over the shared docker network as http://briefato:8080.
Requires: websocket-client.
"""

from __future__ import annotations

import base64
import json
import pathlib
import sys
import time
import urllib.request

import websocket

ENDPOINT = "http://172.18.0.50:9223"
APP = "http://briefato:8080"
OUT = pathlib.Path("/workspace/briefato/artifacts")
EMAIL = "demo@briefato.test"
PASSWORD = "Demo-Passwort-2026"


def targets() -> list[dict]:
    return json.loads(urllib.request.urlopen(ENDPOINT + "/json/list", timeout=8).read())


def connect() -> tuple:
    pages = [t for t in targets() if t.get("type") == "page"]
    ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=40)
    state = {"id": 0}

    def cmd(method: str, params: dict | None = None):
        state["id"] += 1
        ws.send(json.dumps({"id": state["id"], "method": method, "params": params or {}}))
        while True:
            reply = json.loads(ws.recv())
            if reply.get("id") == state["id"]:
                if "error" in reply:
                    raise RuntimeError(f"{method} -> {reply['error']}")
                return reply.get("result", {})

    def ev(expr: str):
        res = cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return res.get("result", {}).get("value")

    return ws, cmd, ev


def viewport(cmd, width: int, height: int) -> None:
    cmd("Emulation.setDeviceMetricsOverride",
        {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": width < 600})


def goto(cmd, ev, url: str, wait: float = 4.0) -> dict:
    cmd("Page.navigate", {"url": url})
    time.sleep(wait)
    return {"title": ev("document.title"), "url": ev("location.href"),
            "text": ev("document.body ? document.body.innerText.slice(0,160) : ''")}


def shot(cmd, name: str, max_height: int = 3200) -> pathlib.Path:
    metrics = cmd("Page.getLayoutMetrics")
    size = metrics.get("cssContentSize") or metrics.get("contentSize")
    height = min(int(size["height"]) + 40, max_height)
    width = int(size["width"])
    res = cmd("Page.captureScreenshot", {
        "format": "png",
        "captureBeyondViewport": True,
        "clip": {"x": 0, "y": 0, "width": width, "height": height, "scale": 1},
    })
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    path.write_bytes(base64.b64decode(res["data"]))
    print(f"  shot {name}: {path} ({path.stat().st_size // 1024} KB, {width}x{height})")
    return path


def list_fields(ev) -> list[dict]:
    return ev("""(() => Array.from(document.querySelectorAll('form input, form textarea, form select'))
        .filter(e => e.type !== 'hidden')
        .map(e => ({tag:e.tagName, name:e.name, id:e.id, type:e.type||'', ph:e.placeholder||''})))()""")


def fill(ev, *, name: str | None = None, type_: str | None = None, value: str) -> bool:
    selector = "form input, form textarea"
    js = f"""(() => {{
      const els = Array.from(document.querySelectorAll({json.dumps(selector)}));
      const el = els.find(e => {json.dumps(name)} && e.name === {json.dumps(name)})
             || els.find(e => {json.dumps(type_)} && e.type === {json.dumps(type_)});
      if (!el) return false;
      el.focus(); el.value = {json.dumps(value)};
      el.dispatchEvent(new Event('input', {{bubbles:true}}));
      el.dispatchEvent(new Event('change', {{bubbles:true}}));
      return true;
    }})()"""
    return bool(ev(js))


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "shots"
    ws, cmd, ev = connect()
    try:
        cmd("Page.enable")
        cmd("Runtime.enable")
        if action == "fields":
            print(goto(cmd, ev, sys.argv[2]))
            print(json.dumps(list_fields(ev), indent=1, ensure_ascii=False))
            return 0

        # ---------------------------------------------------------------- public
        viewport(cmd, 1440, 900)
        print("landing:", goto(cmd, ev, f"{APP}/"))
        shot(cmd, "01-landing-1440")
        viewport(cmd, 390, 844)
        goto(cmd, ev, f"{APP}/")
        shot(cmd, "02-landing-390")
        viewport(cmd, 1440, 900)
        goto(cmd, ev, f"{APP}/preise")
        shot(cmd, "03-preise")
        goto(cmd, ev, f"{APP}/datenschutz")
        shot(cmd, "04-datenschutz")

        # ---------------------------------------------------------------- login
        goto(cmd, ev, f"{APP}/anmelden")
        shot(cmd, "05-anmelden")
        print("fields:", json.dumps(list_fields(ev), ensure_ascii=False))
        print("fill email:", fill(ev, name="email", type_="email", value=EMAIL))
        print("fill pw:", fill(ev, name="password", type_="password", value=PASSWORD))
        ev("document.querySelector('form').submit(); true")
        time.sleep(5)
        print("after login:", ev("location.href"), "|", (ev("document.title") or "")[:60])

        # ---------------------------------------------------------------- app
        for name, path in [("06-dashboard", "/app"), ("07-patienten", "/app/patienten"),
                           ("08-briefe", "/app/briefe"), ("09-konto", "/app/konto")]:
            print(name, goto(cmd, ev, f"{APP}{path}", wait=3))
            shot(cmd, name)

        letter_id = ev("""(() => {const a=Array.from(document.querySelectorAll('a'))
            .map(x=>x.getAttribute('href')||'').find(h=>/\\/app\\/briefe\\/[0-9a-f]{32}$/.test(h)); return a||'';})()""")
        print("letter link:", letter_id)
        if letter_id:
            goto(cmd, ev, f"{APP}{letter_id}", wait=3)
            print("editor title:", ev("document.title"))
            print("editor text head:", (ev("document.body.innerText") or "")[:200].replace("\n", " | "))
            shot(cmd, "10-brief-editor")
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
