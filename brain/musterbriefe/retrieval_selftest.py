#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Retrieval-Selbsttest für die Briefato-Musterbrief-Bibliothek.

Lädt manifest.json, implementiert einen simplen Keyword-Scorer und zeigt für
15 realistische deutsche Indikationen die Top-3-Treffer, damit ein Mensch die
Retrieval-Qualität beurteilen kann.

Aufruf:
    cd /workspace/briefato && .venv/bin/python brain/musterbriefe/retrieval_selftest.py
Nur Standardbibliothek (json, re, os, sys, unicodedata).
"""
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "manifest.json")

STOP = {
    "mit", "und", "der", "die", "das", "bei", "nach", "von", "im", "in", "am",
    "auf", "den", "dem", "des", "eine", "einer", "einem", "ohne", "zur", "zum",
    "für", "fuer", "als", "ist", "ein", "eine", "vom", "aus", "zur",
}


def norm(s):
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def load_templates():
    with open(MANIFEST, encoding="utf-8") as f:
        m = json.load(f)
    return m


def template_tokens(t):
    toks = set()

    def add(s):
        for w in norm(s).split():
            if len(w) >= 3:
                toks.add(w)

    add(t["title"])
    for kw in t["indication_keywords"]:
        add(kw)
    add(t["file"][:-3])
    return toks


def score(query, t):
    qt = [w for w in norm(query).split() if len(w) >= 3 and w not in STOP]
    if not qt:
        return 0.0
    cand = t["_toks"]
    total = 0.0
    matched = 0
    for q in qt:
        best = 0.0
        for c in cand:
            if q == c:
                best = max(best, 2.0)
            elif len(q) >= 4 and (q in c or c in q):
                # längere Überlappung etwas höher gewichten
                ov = min(len(q), len(c))
                best = max(best, 1.0 + min(ov, 8) / 20.0)
        if best > 0:
            matched += 1
        total += best
    # Abdeckung der Query-Tokens leicht belohnen
    coverage = matched / len(qt)
    return round((total / len(qt)) * (0.5 + 0.5 * coverage), 4)


# (query, erwartete Datei(en) als Teilstring)
QUERIES = [
    ("Gallensteine mit Kolik", "Cholezystolithiasis.md"),
    ("Subduralhämatom nach Sturz", "Subduralhaematom"),
    ("Divertikulitis linke Unterbauchschmerzen", "Divertikulitis"),
    ("Lungenembolie", "Lungenembolie.md"),
    ("AC-Gelenk Schulterverletzung", "AC-Gelenk"),
    ("Appendizitis Blinddarmentzündung", "append"),
    ("Leistenhernie Operation", "Leistenhernie"),
    ("Tiefe Beinvenenthrombose", "Tiefe_Beinvenenthrombose"),
    ("pAVK Schaufensterkrankheit", "pAVK"),
    ("Pneumonie Lungenentzündung", "Pneumonie.md"),
    ("Vorhofflimmern Herzrhythmusstörung", "Vorhofflimmern"),
    ("Nierensteine Kolik", "Urolithiasis"),
    ("Gichtanfall", "Gichtarthritis.md"),
    ("Schlaganfall Hemiparese", "Apoplex"),
    ("Harnwegsinfekt Blasenentzündung", "Harnwegsinfekt.md"),
]


def main():
    m = load_templates()
    templates = m["templates"]
    for t in templates:
        t["_toks"] = template_tokens(t)

    print("=" * 78)
    print("Retrieval-Selbsttest – Briefato Musterbriefe")
    print(f"Bibliothek: {m['count']} Musterbriefe  |  Quelle: {m['source']}")
    print("=" * 78)

    top1_hits = 0
    for q, expected in QUERIES:
        scored = [(score(q, t), t) for t in templates]
        scored = [x for x in scored if x[0] > 0]
        scored.sort(key=lambda x: x[0], reverse=True)
        ranked = scored[:3]
        print(f"\nQuery: {q!r}")
        if not ranked:
            print("   (keine Treffer)")
        for i, (s, t) in enumerate(ranked, 1):
            print(f"   {i}. [{s:>6.3f}] {t['title']}  ({t['file']})")
        best = ranked[0][1]["file"] if ranked else ""
        ok = expected.lower() in best.lower()
        top1_hits += 1 if ok else 0
        print(f"   -> Top-1 {'OK ' if ok else 'MISS'} (erwartet: {expected})")

    print("\n" + "=" * 78)
    print(f"Top-1-Trefferquote: {top1_hits}/{len(QUERIES)}")
    print("=" * 78)
    return 0 if top1_hits == len(QUERIES) else 1


if __name__ == "__main__":
    sys.exit(main())
