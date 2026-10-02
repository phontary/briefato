#!/usr/bin/env python3
"""Parent-side verification of the brain-v2 changes (retrieval ranking + mock shape)."""

from __future__ import annotations

import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP))

from briefato.brain import retrieval  # noqa: E402

QUERIES = [
    ("Divertikulitis-Diktat (der reale Staging-Fall)",
     "Patientin mit seit zwei Tagen bestehenden linksseitigen Unterbauchschmerzen, Druckschmerz im "
     "linken Unterbau, kein Fieber. Sonographie zeigt eine wandverdickte Sigma-Schlinge. Labor: CRP "
     "42 mg/l. Wir nahmen die Pat. zur weiteren Diagnostik stationaer auf."),
    ("Gallensteine mit Kolik", "Gallensteine mit Kolik, Oberbauchschmerzen"),
    ("Subduralhämatom nach Sturz", "Subduralhämatom nach Sturz"),
    ("Leistenhernie TAPP", "Leistenhernie, laparoskopische TAPP-Versorgung"),
    ("TVT", "Tiefe Beinvenenthrombose links"),
]

for label, text in QUERIES:
    hits = retrieval.retrieve(text)
    print(f"\n{label}")
    for i, hit in enumerate(hits[:4], 1):
        name = getattr(hit, "title", None) or getattr(hit, "file", "?")
        score = getattr(hit, "score", 0)
        reason = getattr(hit, "reason", "")
        print(f"  {i}. [{score:5.2f}] {name}  {reason}")
