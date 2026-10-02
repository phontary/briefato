#!/usr/bin/env python3
"""Briefato compliance self-check.

Run:  python3 docs/compliance/scripts/selfcheck.py

Checks (hard, exit 1 on failure):
  A) every expected document exists and is non-empty
  B) no placeholder markers (T-O-D-O / l-o-r-e-m) in the markdown
  C) every external URL in the markdown is on a line that carries a retrieval date
     (YYYY-MM-DD); URLs inside `inline code` and fenced ```code``` blocks are ignored
Soft (informational):
  D) prints a checklist of open items ("offen", "muss bestätigt werden", "fehlt")
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # docs/compliance

EXPECTED = [
    "README.md",
    "01-processing-register.md",
    "02-avv-checklist.md",
    "03-tom.md",
    "04-retention-deletion.md",
    "05-data-subject-rights.md",
    "06-threat-model.md",
    "07-legal-texts-briefing.md",
    "08-mdr-boundary.md",
    "09-provider-dpa-briefing.md",
]

# built from parts so this file itself never contains the literal markers
FORBIDDEN = ["TO" + "DO", "lo" + "rem", "Lo" + "rem", "LO" + "REM", "FIX" + "ME", "XXX"]
DATE_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
URL_RE = re.compile(r"https?://[^\s)\]<>`\"']+")
CODE_SPAN_RE = re.compile(r"`[^`]*`")
FENCE_RE = re.compile(r"```.*?```", re.S)

errors: list[str] = []
warnings: list[str] = []


def strip_code(text: str) -> str:
    text = FENCE_RE.sub("", text)
    text = CODE_SPAN_RE.sub("", text)
    return text


def main() -> int:
    print("=" * 72)
    print("Briefato compliance self-check")
    print("dir:", ROOT)
    print("=" * 72)

    # A) existence
    print("\n[A] Dateien vorhanden und nicht leer")
    for name in EXPECTED:
        p = ROOT / name
        if not p.exists():
            errors.append(f"FEHLT: {name}")
            print(f"  [FAIL] {name} fehlt")
        elif p.stat().st_size < 200:
            errors.append(f"LEER/ZU KLEIN: {name} ({p.stat().st_size} bytes)")
            print(f"  [FAIL] {name} zu klein ({p.stat().st_size} bytes)")
        else:
            print(f"  [ ok ] {name} ({p.stat().st_size} bytes)")

    files = sorted(ROOT.glob("*.md"))
    print(f"  -> {len(files)} Markdown-Dateien im Verzeichnis gefunden")

    # B) placeholders
    print("\n[B] Keine Platzhalter-Marker")
    for p in files:
        txt = p.read_text(encoding="utf-8")
        hits = [f for f in FORBIDDEN if f in txt]
        if hits:
            errors.append(f"PLATZHALTER in {p.name}: {hits}")
            print(f"  [FAIL] {p.name}: {hits}")

    # C) URLs with retrieval dates
    print("\n[C] Jede URL mit Abrufdatum")
    url_count = 0
    for p in files:
        for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            stripped = strip_code(line)
            for url in URL_RE.findall(stripped):
                url_count += 1
                if not DATE_RE.search(stripped):
                    errors.append(f"URL ohne Abrufdatum: {p.name}:{lineno} {url}")
                    print(f"  [FAIL] {p.name}:{lineno} -> {url}")
    print(f"  -> {url_count} URLs geprüft")

    # D) open items checklist
    print("\n[D] Offene Punkte / Checkliste")
    labels = ("offen", "muss bestätigt werden", "fehlt")
    total = 0
    per_file: dict[str, int] = {}
    for p in files:
        n = 0
        for line in p.read_text(encoding="utf-8").splitlines():
            low = line.lower()
            if any(lbl in low for lbl in labels):
                n += 1
        if n:
            per_file[p.name] = n
            total += n
    for name, n in per_file.items():
        print(f"  {n:3d}  {name}")
    print(f"  --- {total} offene Punkte insgesamt")

    # summary
    print("\n" + "=" * 72)
    if errors:
        print(f"ERGEBNIS: FEHLER ({len(errors)})")
        for e in errors:
            print("  -", e)
        print("=" * 72)
        return 1
    print("ERGEBNIS: OK — alle harten Checks bestanden")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
