#!/usr/bin/env python3
"""Real end-to-end check on staging: generate a document through the brain pipeline via the UI."""

from __future__ import annotations

import base64
import json
import pathlib
import time
import urllib.request

import websocket

OUT = pathlib.Path("/workspace/briefato/artifacts")
LETTER = "/app/briefe/b0aacbada1984794bfd9c4835d06e704"
DICTATION = (
    "Patientin mit seit zwei Tagen bestehenden linksseitigen Unterbauchschmerzen, Druckschmerz im "
    "linken Unterbau, kein Fieber. Sonographie zeigt eine wandverdickte Sigma-Schlinge ohne freie "
    "Fluessigkeit. Labor: CRP 42 mg/l, Leukozyten 12,3/nl. Wir nahmen die Pat. zur weiteren "
    "Diagnostik und Schmerztherapie stationaer auf. Befund im Verlauf ruecklaeufig, Kostaufbau "
    "problemlos, Pat. beschwerdefrei entlassen."
)

pages = [t for t in json.loads(urllib.request.urlopen("http://172.18.0.50:9223/json/list", timeout=8).read())
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
    return cmd("Runtime.evaluate", {"expression": expr, "returnByValue": True}).get("result", {}).get("value")


def txt(expr):
    return (ev(expr) or "").replace("\n", " | ")


cmd("Page.enable")
cmd("Runtime.enable")
cmd("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 950, "deviceScaleFactor": 1, "mobile": False})
cmd("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]})
cmd("Page.navigate", {"url": "http://briefato:8080" + LETTER})
time.sleep(4)

print("dictation field:", ev("(() => {const t=document.querySelector('textarea'); if(!t) return 'none'; "
                            "t.focus(); t.value=" + json.dumps(DICTATION) +
                            "; t.dispatchEvent(new Event('input',{bubbles:true})); return t.name||t.id;})()"))
print("form action:", ev("(() => {const f=document.querySelector('textarea').closest('form'); "
                         "if(!f) return 'none'; f.submit(); return f.getAttribute('action');})()"))
time.sleep(14)

print("url/title:", ev("location.href"), "|", ev("document.title"))
print("rule check:", txt("(document.querySelector('.rule-check')||{}).innerText||''")[:300])
print("templates:", txt("(() => {const el=Array.from(document.querySelectorAll('section,div,ul'))"
                        ".find(e=>/Verwendete Vorlagen/i.test(e.innerText||'') && (e.innerText||'').length<420);"
                        " return el? el.innerText.slice(0,240):'not found';})()"))
print("doc type:", txt("(() => {const el=document.querySelector('select'); return el? "
                       "el.options[el.selectedIndex].text + ' (value=' + el.value + ')':'none';})()"))
body = ev("((document.querySelector('#text-result')||{}).innerText||'')") or ""
print("result chars:", len(body))
print("result head:", body[:300].replace("\n", " | "))
print("result tail:", body[-260:].replace("\n", " | "))
print("has 'Diagnosen:' at the end:", "Diagnosen:" in body[-300:])
OUT.joinpath("m05-gen-result.png").write_bytes(base64.b64decode(cmd("Page.captureScreenshot", {"format": "png"})["data"]))
print("shot: m05-gen-result.png")
ws.close()
