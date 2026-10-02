#!/usr/bin/env python3
"""Drive the new wizard (/app/neu) on staging with the REAL model and screenshot the result."""

from __future__ import annotations

import base64
import json
import pathlib
import time
import urllib.request

import websocket

OUT = pathlib.Path("/workspace/briefato/artifacts")
APP = "http://briefato:8080"

ANAMNESE = (
    "Die Pat. stellte sich mit seit zwei Tagen zunehmenden linksseitigen Unterbauchschmerzen vor, "
    "Fieber und Erbrechen bestanden nicht. Wir nahmen die Pat. zur weiteren Diagnostik bzw. "
    "Schmerztherapie stationaer auf."
)
KU = "Abd. weich, DS li. UB, keine ABW, DG regelrecht, pDMS intakt."
SOURCES = [
    ("Labor", "CRP 42 mg/l, Leukozyten 12,3/nl, Krea 0,9 mg/dl."),
    ("CT", "V.a. akute Divertikulitis links, keine Perforation, keine freie Luft."),
    ("Sonographie", "Wandverdickte Sigma-Schlinge, kein freier Flussigkeit, keine Abszessbildung."),
    ("Visiten", "Unter AB-Therapie Rueckgang der Beschwerden, Kostaufbau ab Tag 2 problemlos."),
    ("Pathologie", "Keine Histologie im Aufenthalt entnommen."),
    ("OP-Bericht", "Keine Operation im Aufenthalt."),
    ("Röntgen", "Thorax roentgen: keine Infiltrate."),
]

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


def shot(name):
    data = cmd("Page.captureScreenshot", {"format": "png"})["data"]
    p = OUT / f"{name}.png"
    p.write_bytes(base64.b64decode(data))
    print(f"  shot {name}: {p.stat().st_size // 1024} KB")


cmd("Page.enable")
cmd("Runtime.enable")
cmd("Emulation.setDeviceMetricsOverride", {"width": 1440, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
cmd("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": "light"}]})

cmd("Page.navigate", {"url": APP + "/app/neu"})
time.sleep(4)
if "/anmelden" in (ev("location.href") or ""):
    print("logging in…")
    ev("""(() => {const f=document.querySelector('form');
         f.querySelector('input[name=email]').value='demo@briefato.test';
         f.querySelector('input[name=password]').value='Demo-Passwort-2026'; f.submit(); return 1;})()""")
    time.sleep(4)
    cmd("Page.navigate", {"url": APP + "/app/neu"})
    time.sleep(3)

print("step1 heading:", ev("(document.querySelector('[data-wizard-heading],h2,h1')||{}).innerText"))
shot("w01-typauswahl")
print("cards:", ev("""(() => Array.from(document.querySelectorAll('button[value], label, .card, .type-card'))
    .map(e => (e.innerText||'').trim().split('\\n')[0]).filter(Boolean).slice(0,14))()"""))

# choose the Entlassbrief card/button
clicked = ev("""(() => {const els = Array.from(document.querySelectorAll('button,label,a,input[type=submit]'));
  const el = els.find(e => /entlassbrief/i.test(e.innerText||e.value||'')) ;
  if (!el) return 'NOT FOUND';
  (el.closest('form')||document).requestSubmit?.call(el.closest('form'));
  el.click(); return (el.innerText||el.value||'').trim();})()""")
print("clicked:", clicked)
time.sleep(4)


def step_state(label):
    print(f"\n--- {label} ---")
    print("url:", ev("location.href"))
    print("heading:", ev("(document.querySelector('[data-wizard-heading],h2')||{}).innerText"))
    print("progress:", ev("(document.querySelector('.wizard-progress')||{}).innerText"))
    print("fields:", ev("""(() => Array.from(document.querySelectorAll('form input:not([type=hidden]),form select,form textarea'))
        .map(e => (e.tagName+':'+(e.name||e.id||'')+(e.type?('.'+e.type):'')).slice(0,40)))()"""))
    print("buttons:", ev("""(() => Array.from(document.querySelectorAll('form button,form input[type=submit]'))
        .map(e => ((e.innerText||e.value||'').trim()+'|'+(e.name||'')+'='+(e.value||'')).slice(0,50)))()"""))


step_state("Schritt 2")
shot("w02-schritt2")

FILL = """
(() => {
  const setv = (el, v) => { if (!el) return false; el.focus();
    el.value = v; el.dispatchEvent(new Event('input',{bubbles:true}));
    el.dispatchEvent(new Event('change',{bubbles:true})); return true; };
  const out = [];
  document.querySelectorAll('form select').forEach(s => {
    if (!s.value || s.selectedIndex <= 0) { const o = Array.from(s.options).find(x => x.value); if (o) { setv(s, o.value); out.push('select '+s.name+'='+o.value); } }
  });
  document.querySelectorAll('form textarea, form input[type=text], form input[type=date]').forEach(t => {
    if (t.value) return;
    const n = (t.name||'').toLowerCase();
    let v = 'PLATZHALTER';
    if (n.includes('anamnese') || n.includes('aufnahme')) v = ANAMNESE;
    else if (n.includes('ku') || n.includes('befund') || n.includes('untersuchung')) v = KU;
    else if (n.includes('datum') || t.type === 'date') v = '2026-09-30';
    else if (n.includes('indikation')) v = 'Akute Divertikulitis links';
    else if (n.includes('zugang')) v = 'Laparoskopie, 4 Trokare';
    else if (n.includes('massnahme') || n.includes('maßnahme')) v = 'Sigmadivertikelresektion';
    else if (n.includes('drainage')) v = 'Keine Drainage';
    else if (t.tagName === 'TEXTAREA') v = 'Befund und Verlauf dokumentiert.';
    if (setv(t, v)) out.push('field '+t.name);
  });
  return out;
})()
"""
print("filled:", ev(FILL.replace("ANAMNESE", json.dumps(ANAMNESE)).replace("KU", json.dumps(KU))))

# sources: add until we have >=6, then continue to the summary
# sources: fill whatever the sources step offers (single dictation box and/or labelled sources)
MULTI_SOURCE = (
    "Anamnese: seit zwei Tagen zunehmende linksseitige Unterbauchschmerzen, kein Fieber, "
    "kein Erbrechen. Aufnahme zur weiteren Diagnostik und Schmerztherapie stationaer.\n"
    "KU: Abd. weich, DS li. UB, keine ABW, DG regelrecht, pDMS intakt.\n"
    "Labor: CRP 42 mg/l, Leukozyten 12,3/nl, Krea 0,9 mg/dl.\n"
    "Sonographie: wandverdickte Sigma-Schlinge, kein freier Flussigkeit, keine Abszessbildung.\n"
    "CT Abdomen: V.a. akute Divertikulitis links, keine Perforation, keine freie Luft.\n"
    "Roentgen Thorax: keine Infiltrate.\n"
    "Visiten: unter AB-Therapie Rueckgang der Beschwerden, Kostaufbau ab Tag 2 problemlos.\n"
    "OP-Bericht: keine Operation im Aufenthalt.\n"
    "Entlassung: beschwerdefrei, Entlassung am 08.10.2026, Kontrolle beim Hausarzt, "
    "Koloskopie in 6 Wochen empfohlen."
)
for i, (label, text) in enumerate(SOURCES):
    ok = ev("""(() => {
      const sel = Array.from(document.querySelectorAll('form select')).find(s => /quelle|source|label/i.test(s.name||''));
      const ta  = Array.from(document.querySelectorAll('form textarea')).find(t => /quelle|source|text/i.test(t.name||''));
      if (!sel || !ta) return false;
      sel.value = %s; sel.dispatchEvent(new Event('change',{bubbles:true}));
      ta.focus(); ta.value = %s; ta.dispatchEvent(new Event('input',{bubbles:true}));
      const bs = Array.from(document.querySelectorAll('form button')).filter(b => /hinzuf|add|quelle/i.test(b.innerText||''));
      if (bs.length) { bs[bs.length-1].click(); return true; }
      return false;})()""" % (json.dumps(label), json.dumps(text)))
    time.sleep(2.0)
    print(f"  source {i+1} ({label}): {ok}")

step_state("nach Quellen")
W = """(() => {const bs = Array.from(document.querySelectorAll('form button,form input[type=submit]'));
  const b = bs.find(x => /weiter|nächste|naechste|erzeugen|bestätigen|abschließen/i.test((x.innerText||x.value||'')));
  if (!b) return 'NO BUTTON'; const f=b.closest('form'); if (f) f.requestSubmit ? f.requestSubmit(b) : f.submit(); else b.click();
  return (b.innerText||b.value||'').trim();})()"""
for n in range(6):
    txt = ev(W)
    time.sleep(4)
    print(f"continue[{n}]: {txt} | url={ev('location.href')} | heading={ev('(document.querySelector(\"[data-wizard-heading],h2\")||{}).innerText')}")
    if "ergebnis" in (ev("location.href") or ""):
        break
    ev(FILL.replace("ANAMNESE", json.dumps(ANAMNESE)).replace("KU", json.dumps(KU)))
    # on the sources step, paste a labelled multi-source KIS text so the engine fan-outs
    ev("""(() => {const t = Array.from(document.querySelectorAll('form textarea'))
      .find(x => !x.value);
      if (!t) return 'no empty textarea';
      t.focus(); t.value = %s; t.dispatchEvent(new Event('input',{bubbles:true})); return 'pasted';})()"""
       % json.dumps(MULTI_SOURCE))
    time.sleep(1.5)

time.sleep(3)
shot("w03-ergebnis")
print("result url:", ev("location.href"))
rc_text = ev("(document.querySelector('.rule-check')||{}).innerText||''") or ""
print("rule check:", rc_text.replace("\n", " | ")[:200])
print("templates:", (ev("""(() => {const el=Array.from(document.querySelectorAll('section,div,ul')).find(e=>/Verwendete Vorlagen/i.test(e.innerText||'') && (e.innerText||'').length<300); return el? el.innerText.slice(0,200):'not found';})()""") or "").replace("\n", " | "))
print("route badge:", (ev("""(() => {const el=document.querySelector('.chip, .badge, .meta'); return el? el.innerText.slice(0,160):'';})()""") or "").replace("\n", " | "))
body = ev("((document.querySelector('#result-text,#text-result')||{}).innerText||'')") or ""
print("chars:", len(body))
print("TEXT HEAD:", body[:420].replace("\n", " "))
print("TEXT TAIL:", body[-320:].replace("\n", " "))
ws.close()
