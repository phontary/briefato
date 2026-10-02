#!/usr/bin/env python3
"""Drive the shared Chromium (N305) over CDP to capture the Briefato chat portal.

Endpoint: ws://172.18.0.50:9223 (static IP; the DevTools host check rejects names).
The Chromium container reaches the portal over the shared docker network as http://briefato:8080.

Usage:
  .venv/bin/python tools/cdp_chat_shot.py recon   # login + dump page facts
  .venv/bin/python tools/cdp_chat_shot.py shots   # full visual pass -> artifacts/

This is the chat-portal sibling of tools/cdp_shot.py (same connection/screenshot pattern).
"""

from __future__ import annotations

import base64
import json
import os
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

OP_DICTATION = (
    "OP-Bericht: 54-jaehrige Patientin, laparoskopische Cholezystektomie bei "
    "Cholezystolithiasis. Indikation: rezidivierende rechtsseitige Oberbauchschmerzen. "
    "Zugang: laparoskopisch, Vier-Trokar-Technik. Kernbefund: chronisch entzuendete, "
    "wandverdickte Gallenblase. Massnahmen: praeparierte und durchtrennte Strukturen, "
    "Bergung ueber den Nabel. Drainagen: Lasche Unterbauch rechts entfernt am 2. Tag."
)


def targets() -> list[dict]:
    return json.loads(urllib.request.urlopen(ENDPOINT + "/json/list", timeout=8).read())


def connect():
    pages = [t for t in targets() if t.get("type") == "page"]
    ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=60)
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


def set_viewport(cmd, width: int, height: int) -> None:
    """Set a CSS viewport of exactly ``width`` x ``height``.

    This Chromium runs with `--force-device-scale-factor=0.5`, so both dimensions of the
    emulated viewport come out 2x the requested value with deviceScaleFactor 2 (measured:
    request 720x900/dsf2 -> innerWidth 1440, innerHeight 1800, dpr 1, layout shell 1400px
    centred). Requesting half the target at dsf 2 therefore yields the real CSS viewport at
    dpr 1, and a plain (clip-less) capture returns the viewport at 1:1.
    """
    cmd("Emulation.setDeviceMetricsOverride",
        {"width": max(1, width // 2), "height": max(1, height // 2),
         "deviceScaleFactor": 2, "mobile": False})


def goto(cmd, ev, url: str, wait: float = 3.0) -> dict:
    cmd("Page.navigate", {"url": url})
    time.sleep(wait)
    return {
        "title": ev("document.title"),
        "url": ev("location.href"),
        "text": (ev("document.body ? document.body.innerText.slice(0,200) : ''") or ""),
    }


def shot(cmd, ev, name: str, width: int, max_height: int = 4200, resize: bool = True) -> pathlib.Path:
    """Full-page shot: size the viewport to the content, then capture it without a clip.

    `Page.captureScreenshot` with a `clip` + `captureBeyondViewport` interacts badly with the
    emulated device scale here (2x image, offset content). Resizing the viewport and taking a
    plain capture is exact. ``resize=False`` captures the current viewport as-is (useful for a
    "what the member sees on screen" shot).
    """
    if resize:
        content = int(ev("Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)") or 900)
        height = min(content + 20, max_height)
        set_viewport(cmd, width, height)
        time.sleep(0.4)
    res = cmd("Page.captureScreenshot", {"format": "png"})
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.png"
    path.write_bytes(base64.b64decode(res["data"]))
    print(f"  shot {name}: {path} ({path.stat().st_size // 1024} KB, viewport {width})")
    return path


def fill(ev, *, name: str, value: str) -> bool:
    js = f"""(() => {{
      const els = Array.from(document.querySelectorAll('form input, form textarea'));
      const el = els.find(e => e.name === {json.dumps(name)});
      if (!el) return false;
      el.focus(); el.value = {json.dumps(value)};
      el.dispatchEvent(new Event('input', {{bubbles:true}}));
      el.dispatchEvent(new Event('change', {{bubbles:true}}));
      return true;
    }})()"""
    return bool(ev(js))


def wait_for(ev, expr: str, timeout: float = 240.0, step: float = 3.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if ev(expr):
                return True
        except Exception:
            pass
        time.sleep(step)
    return False


def login(cmd, ev) -> None:
    # The shared Chromium keeps cookies from earlier runs: use the existing session when it
    # belongs to the demo account, otherwise log in through the login form explicitly.
    goto(cmd, ev, f"{APP}/app")
    url = ev("location.href") or ""
    account = ev("(() => {const e=document.querySelector('[data-account]'); return e?e.textContent.trim():'';})()")
    if "/anmelden" not in url and account:
        print("already logged in as:", account)
        return
    goto(cmd, ev, f"{APP}/anmelden")
    fill(ev, name="email", value=EMAIL)
    fill(ev, name="password", value=PASSWORD)
    submitted = ev("(() => {const p=document.querySelector('input[name=password]');"
                   " if(!p || !p.form) return false; p.form.submit(); return true;})()")
    time.sleep(5)
    print("after login:", ev("location.href"), "| submitted:", submitted,
          "|", (ev("document.title") or "")[:50])


def ensure_patient(cmd, ev) -> str:
    options = ev("""(() => Array.from(document.querySelectorAll('#chat-patient option'))
        .map(o => ({v:o.value, t:o.textContent.trim()})))()""") or []
    real = [o for o in options if o.get("v")]
    if real:
        return ev("document.querySelector('#chat-patient').value") or real[0]["v"]
    print("no patient yet -> creating one")
    goto(cmd, ev, f"{APP}/app/patienten/neu")
    fill(ev, name="last_name", value="Beispiel")
    fill(ev, name="first_name", value="Greta")
    fill(ev, name="city", value="Musterstadt")
    ev("document.querySelector('main form').submit(); true")
    time.sleep(4)
    goto(cmd, ev, f"{APP}/app/chat")
    options = ev("""(() => Array.from(document.querySelectorAll('#chat-patient option'))
        .map(o => ({v:o.value, t:o.textContent.trim()})))()""") or []
    real = [o for o in options if o.get("v")]
    return real[0]["v"] if real else ""


def set_media(cmd, reduced: bool) -> None:
    """Light theme for readability; optionally reduced motion (also un-stalls the focus fade)."""
    features = [{"name": "prefers-color-scheme", "value": "light"}]
    if reduced:
        features.append({"name": "prefers-reduced-motion", "value": "reduce"})
    cmd("Emulation.setEmulatedMedia", {"features": features})


def open_best_case(cmd, ev) -> str:
    """Newest persisted case that already contains a letter (prefer one with a follow-up)."""
    goto(cmd, ev, f"{APP}/app/chat")
    links = ev("Array.from(document.querySelectorAll('a[href^=\"/app/chat?thread=\"]'))"
               ".map(a => a.getAttribute('href'))") or []
    print("persisted cases:", links)
    fallback = ""
    for href in links[:6]:
        goto(cmd, ev, APP + href, wait=2.5)
        count = ev("document.querySelectorAll('.chat-letter').length")
        if count and count >= 2:
            print("reusing case (with follow-up):", href)
            return href.split("thread=")[-1]
        if count and not fallback:
            fallback = href.split("thread=")[-1]
    if fallback:
        print("reusing case (single letter):", fallback)
    return fallback


def run_fresh_case(cmd, ev) -> str:
    """Run one real dictation + follow-up through the chat (real model calls) and return the id."""
    goto(cmd, ev, f"{APP}/app/chat")
    patient_id = ensure_patient(cmd, ev)
    ev(f"(() => {{ const s=document.querySelector('#chat-patient'); s.value={json.dumps(patient_id)};"
       " s.dispatchEvent(new Event('change',{bubbles:true})); return s.value; })()")
    selected = ev("(() => {const s=document.querySelector('#chat-patient');"
                  " return s.selectedIndex>=0 ? s.options[s.selectedIndex].textContent.trim() : '';})()") or ""
    parts = [p.strip() for p in selected.split(",")]
    name = f"{parts[1]} {parts[0]}" if len(parts) == 2 else selected
    dictation = (f"OP-Bericht für {name}: " + OP_DICTATION.split(": ", 1)[1]) if name else OP_DICTATION
    print("patient:", selected, "| dictation head:", dictation[:60])
    fill(ev, name="message", value=dictation)
    ev("document.querySelector('[data-chat-form]').submit(); true")
    if not wait_for(ev, "document.readyState==='complete' && !!document.querySelector('.chat-letter')", 240):
        print("fresh generation did not render a letter (model slow/failed) — falling back to a persisted case")
        return ""
    print("fresh letter rule line:", ev("(() => {const e=document.querySelector('.chat-rule-line'); return e?e.textContent.trim():'';})()"))
    fill(ev, name="message", value="kuerzer")
    ev("document.querySelector('[data-chat-form]').submit(); true")
    ok = wait_for(ev, "document.readyState==='complete' && document.querySelectorAll('.chat-letter').length>=2", 240)
    print("fresh follow-up rendered:", ok)
    return ev("(() => {const i=document.querySelector('input[name=thread_id]'); return i?i.value:'';})()") or ""


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "shots"
    ws, cmd, ev = connect()
    try:
        cmd("Page.enable")
        cmd("Runtime.enable")
        cmd("Network.enable")
        # The shared browser keeps an HTTP cache from earlier runs; without this the previous
        # app.js/app.css would be served and the new chat behaviour would not appear.
        cmd("Network.setCacheDisabled", {"cacheDisabled": True})
        cmd("Page.bringToFront")
        # Capture in the light theme so the screenshots stay readable (dark is the browser's
        # default and the app supports both).
        cmd("Emulation.setEmulatedMedia",
            {"features": [{"name": "prefers-color-scheme", "value": "light"}]})
        set_viewport(cmd, 1440, 900)
        login(cmd, ev)

        if action == "recon":
            goto(cmd, ev, f"{APP}/app/chat")
            print(json.dumps({
                "url": ev("location.href"),
                "has_composer": ev("!!document.querySelector('[data-chat-composer]')"),
                "sentences": ev("document.querySelectorAll('[data-chat-sentence]').length"),
                "patient_options": ev("""(() => Array.from(document.querySelectorAll('#chat-patient option'))
                    .map(o => ({v:o.value, t:o.textContent.trim()})))()"""),
                "forms": ev("Array.from(document.forms).map(f => f.getAttribute('action'))"),
                "text_head": (ev("document.body.innerText") or "")[:400],
            }, indent=1, ensure_ascii=False))
            return 0

        # ---------------------------------------------------------------- idle (1440)
        goto(cmd, ev, f"{APP}/app/chat")
        print("viewport:", ev("window.innerWidth"), "x", ev("window.innerHeight"),
              "dpr", ev("window.devicePixelRatio"))
        shot(cmd, ev, "c01-chat-idle-1440", 1440)
        print("idle text:", (ev("document.body.innerText") or "")[:160].replace("\n", " | "))

        # ---------------------------------------------------------------- focus (1440)
        # CSS transitions do not advance in this (unrendered) browser page, so the fade would
        # never land before the capture. Emulating `prefers-reduced-motion: reduce` disables the
        # transitions in our own CSS and the fade applies at once — the same end state a member
        # sees after the 0.25 s transition.
        set_media(cmd, reduced=True)
        ev("document.querySelector('#chat-message').focus(); true")
        time.sleep(0.6)
        focused = ev("document.body.classList.contains('is-chat-focus')")
        nav_state = ev("(()=>{const n=document.querySelector('.shell-nav');const c=getComputedStyle(n);return [c.opacity,c.visibility];})()")
        print("focus class set:", focused, "| shell-nav computed:", nav_state)
        shot(cmd, ev, "c02-chat-focus-1440", 1440)
        ev("document.activeElement && document.activeElement.blur(); true")
        time.sleep(0.4)
        print("focus class after blur:", ev("document.body.classList.contains('is-chat-focus')"))
        set_media(cmd, reduced=False)

        # ---------------------------------------------------------------- a case from the chat
        thread_id = ""
        if os.environ.get("BRIEFATO_CHAT_SHOT_GENERATE") == "1":
            thread_id = run_fresh_case(cmd, ev)
        if not thread_id:
            thread_id = open_best_case(cmd, ev)
        if thread_id:
            goto(cmd, ev, f"{APP}/app/chat?thread={thread_id}", wait=3)
            print("case letters:", ev("document.querySelectorAll('.chat-letter').length"))
            print("doc type badge:", ev("(() => {const e=document.querySelector('.chat-letter-meta .badge'); return e?e.textContent.trim():'';})()"))
            print("rule line:", ev("(() => {const e=document.querySelector('.chat-rule-line'); return e?e.textContent.trim():'';})()"))
            print("letter id(s):", ev("Array.from(document.querySelectorAll('.chat-letter-text')).map(e=>e.id)"))
            print("follow-up instruction on page:", ev("(()=>{const t=document.querySelectorAll('.chat-msg--followup .chat-bubble-text'); return t.length?t[t.length-1].textContent.trim():'';})()"))
            print("letter head:", (ev("document.querySelector('.chat-letter-text').textContent") or "")[:200].replace("\n", " | "))
            print("editor link:", ev("(()=>{const a=document.querySelector('.chat-letter a[href^=\"/app/briefe/\"]'); return a?a.getAttribute('href'):'';})()"))
            print("templates shown:", ev("document.querySelectorAll('.chat-letter .used-list li').length"))
            # c03: the case as it appears on screen (letter bubble at the top of the thread)
            set_viewport(cmd, 1440, 1000)
            time.sleep(0.4)
            shot(cmd, ev, "c03-chat-letter-1440", 1440, resize=False)
            if ev("document.querySelectorAll('.chat-letter').length") >= 2:
                shot(cmd, ev, "c04-chat-followup-1440", 1440, max_height=5200)

        # ---------------------------------------------------------------- mobile (390)
        set_viewport(cmd, 390, 844)
        goto(cmd, ev, f"{APP}/app/chat")
        print("mobile viewport:", ev("window.innerWidth"), "x", ev("window.innerHeight"))
        shot(cmd, ev, "c05-chat-idle-390", 390)
        set_media(cmd, reduced=True)
        ev("document.querySelector('#chat-message').focus(); true")
        time.sleep(0.6)
        print("mobile focus class:", ev("document.body.classList.contains('is-chat-focus')"))
        shot(cmd, ev, "c06-chat-focus-390", 390)
        set_media(cmd, reduced=False)
        if thread_id:
            goto(cmd, ev, f"{APP}/app/chat?thread={thread_id}", wait=3)
            shot(cmd, ev, "c07-chat-thread-390", 390, max_height=5200)
            print("mobile case letters:", ev("document.querySelectorAll('.chat-letter').length"))
    finally:
        ws.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
