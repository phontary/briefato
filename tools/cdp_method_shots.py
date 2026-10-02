#!/usr/bin/env python3
"""Screenshot + evidence pass for the method UI (staging) over CDP.

Usage: .venv/bin/python tools/cdp_method_shots.py
Saves PNGs to artifacts/ and prints rendered-HTML evidence (copy button, rule check, templates).
"""

from __future__ import annotations

import base64
import json
import pathlib
import time
import urllib.request

import websocket

ENDPOINT = "http://172.18.0.50:9223"
APP = "http://briefato:8080"
OUT = pathlib.Path("/workspace/briefato/artifacts")
EMAIL = "demo@briefato.test"
PASSWORD = "Demo-Passwort-2026"


def connect():
    pages = [t for t in json.loads(urllib.request.urlopen(ENDPOINT + "/json/list", timeout=8).read())
             if t.get("type") == "page"]
    ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
    state = {"id": 0}

    def cmd(method, params=None):
        state["id"] += 1
        ws.send(json.dumps({"id": state["id"], "method": method, "params": params or {}}))
        while True:
            r = json.loads(ws.recv())
            if r.get("id") == state["id"]:
                if "error" in r:
                    raise RuntimeError(r["error"])
                return r.get("result", {})

    def ev(expr):
        return cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True}) \
            .get("result", {}).get("value")

    return ws, cmd, ev


def main() -> int:
    ws, cmd, ev = connect()
    try:
        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 950, "deviceScaleFactor": 1, "mobile": False})
        cmd("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]})

        def go(path, wait=3.5):
            cmd("Page.navigate", {"url": APP + path})
            time.sleep(wait)
            return ev("location.href")

        def shot(name):
            data = cmd("Page.captureScreenshot", {"format": "png"})["data"]
            p = OUT / f"{name}.png"
            p.write_bytes(base64.b64decode(data))
            print(f"  {name}: {p.stat().st_size // 1024} KB")

        # ensure a session
        go("/app")
        if "/anmelden" in (ev("location.href") or ""):
            ev("""(() => {const f=document.querySelector('form');
                 f.querySelector('input[name=email]').value=%s;
                 f.querySelector('input[name=password]').value=%s; f.submit(); return 1;})()"""
               % (json.dumps(EMAIL), json.dumps(PASSWORD)))
            time.sleep(4)
        print("session url:", ev("location.href"))

        go("/app/methode")
        print("methode:", ev("document.title"), "| rules on page:", ev("document.querySelectorAll('.rule-id').length"))
        shot("m01-methode")

        go("/app/vorlagen")
        print("vorlagen:", ev("document.title"), "| library count text:",
              ev("(document.querySelector('.lib-count')||document.body).innerText.slice(0,120).replace(/\\n/g,' ')"),
              "| locked badges:", ev("document.body.innerText.split('gesperrt').length - 1"))
        shot("m02-vorlagen")

        # letter editor: open the first letter in the list
        go("/app/briefe")
        href = ev("""(() => {const a=Array.from(document.querySelectorAll('a'))
            .map(x=>x.getAttribute('href')||'').find(h=>/\\/app\\/briefe\\/[0-9a-f]{32}$/.test(h)); return a||'';})()""")
        print("letter link:", href)
        if href:
            go(href, wait=3)
            print("copy button present:", ev("!!document.querySelector('[data-copy-target]')"))
            print("rule check present:", ev("!!document.querySelector('.rule-check')"))
            print("rule check text:", (ev("(document.querySelector('.rule-check')||{}).innerText||''") or "").replace("\n", " | ")[:220])
            shot("m03-brief-editor")

            # trigger generation through the real form
            clicked = ev("""(() => {const b=Array.from(document.querySelectorAll('button,form button'))
                .find(x=>/erzeugen/i.test(x.innerText||'')); if(b){b.click(); return b.innerText.trim();} return '';})()""")
            print("generate button:", clicked)
            time.sleep(9)
            print("after generate url:", ev("location.href"))
            print("rule check text (after):", (ev("(document.querySelector('.rule-check')||{}).innerText||''") or "").replace("\n", " | ")[:300])
            print("used templates:", (ev("((document.querySelector('.used-templates')||{}).innerText||'')") or "").replace("\n", " | ")[:200])
            print("result text head:", (ev("((document.querySelector('#text-result')||{}).innerText||'')") or "")[:200].replace("\n", " | "))
            shot("m04-brief-result")
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
