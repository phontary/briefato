#!/usr/bin/env python3
"""selfcheck_praxis.py — stdlib-only self-check for the Briefato 'brain' praxis harvest.

Prüft die vom Praxis-Harvest erzeugten Dateien in brain/:
  - stolperfallen.md, regeln-aus-praxis.md, product-relevant-skills.md, ANTI-PATTERNS.md
  - jede Stolperfalle (### PIT-xx) trägt eine Provenienz
  - jede Praxisregel (### Pxx) trägt eine Provenienz
  - jeder Anti-Pattern-Eintrag (### AP-xx) nennt LLM-Fehlverhalten UND Ersatzregel
  - keine TODO-/Platzhalter-Reste, keine leeren Dateien
  - Mindestzahlen (Pitfalls, Regeln, Skill-Zeilen, Anti-Patterns)

Ausgabe: PASS/FAIL pro Check + Zusammenfassung. Exit-Code 0 = alles PASS, 1 = mindestens ein FAIL.
Nur Standardbibliothek (os, re, sys, pathlib).
"""

from __future__ import annotations

import os
import re
import sys

BRAIN = os.path.dirname(os.path.abspath(__file__))

F_PITFALLS = "stolperfallen.md"
F_RULES = "regeln-aus-praxis.md"
F_SKILLS = "product-relevant-skills.md"
F_ANTI = "ANTI-PATTERNS.md"

REQUIRED = [F_PITFALLS, F_RULES, F_SKILLS, F_ANTI]

# Mindestzahlen
MIN_PITFALLS = 30
MIN_RULES = 30
MIN_SKILL_ROWS = 15
MIN_ANTI = 15

SOURCE_TOKENS = (".md", "SKILL.md", "log.md", "SOUL.md", "MEMORY.md", "USER.md", "references/")

results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def split_sections(text: str, heading_re: re.Pattern[str]) -> list[tuple[str, str]]:
    """Return [(heading, body)] for every heading matching heading_re (body = up to next heading)."""
    sections: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    for line in text.splitlines():
        if heading_re.match(line):
            if current is not None:
                sections.append((current[0], current[1]))
            current = [line.strip(), []]
        elif current is not None:
            current[1].append(line)
    if current is not None:
        sections.append((current[0], current[1]))
    return [(h, "\n".join(b)) for h, b in sections]


def check_files_exist_nonempty() -> None:
    all_ok = True
    for name in REQUIRED:
        path = os.path.join(BRAIN, name)
        if not os.path.isfile(path):
            record(f"Datei vorhanden & nicht leer: {name}", False, "fehlt")
            all_ok = False
        elif os.path.getsize(path) == 0:
            record(f"Datei vorhanden & nicht leer: {name}", False, "leer")
            all_ok = False
        else:
            record(f"Datei vorhanden & nicht leer: {name}", True, f"{os.path.getsize(path)} Bytes")
    if all_ok:
        pass


def check_provenance(name: str, text: str, heading_re: re.Pattern[str], kind: str) -> None:
    sections = split_sections(text, heading_re)
    if not sections:
        record(f"{name}: {kind}-Einträge gefunden", False, "0 Einträge")
        return
    missing: list[str] = []
    for heading, body in sections:
        if "provenienz" not in body.lower():
            missing.append(heading[:70])
        elif not any(tok in body for tok in SOURCE_TOKENS):
            missing.append(heading[:70] + " (keine Quelldatei)")
    record(
        f"{name}: {len(sections)} {kind} mit Provenienz",
        not missing,
        "" if not missing else f"{len(missing)} ohne: " + " | ".join(missing[:5]),
    )


def check_no_marker(name: str, text: str, marker: str) -> None:
    hits = [i + 1 for i, line in enumerate(text.splitlines()) if marker in line.lower()]
    record(f"{name}: kein '{marker}'", not hits, "" if not hits else f"Zeile(n) {hits[:10]}")


def check_min_count(name: str, actual: int, minimum: int) -> None:
    record(f"{name}: >= {minimum}", actual >= minimum, f"gefunden: {actual}")


def check_anti_patterns(text: str) -> None:
    sections = split_sections(text, re.compile(r"^### AP-\d+"))
    if not sections:
        record("ANTI-PATTERNS: Einträge gefunden", False, "0 Einträge")
        return
    bad: list[str] = []
    for heading, body in sections:
        low = body.lower()
        if "was das generische llm tut" not in low or "ersatzregel" not in low:
            bad.append(heading[:70])
    record(
        "ANTI-PATTERNS: jeder Eintrag nennt Fehlverhalten + Ersatzregel",
        not bad,
        "" if not bad else "unvollständig: " + " | ".join(bad[:5]),
    )


def main() -> int:
    # Dateien zuerst laden
    texts: dict[str, str] = {}
    for name in REQUIRED:
        path = os.path.join(BRAIN, name)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            texts[name] = read(path)

    check_files_exist_nonempty()

    if F_PITFALLS in texts:
        t = texts[F_PITFALLS]
        check_provenance(F_PITFALLS, t, re.compile(r"^### PIT-\d+"), "Stolperfallen")
        check_min_count(f"{F_PITFALLS}: Stolperfallen", len(split_sections(t, re.compile(r"^### PIT-\d+"))), MIN_PITFALLS)
        check_no_marker(F_PITFALLS, t, "todo")
        check_no_marker(F_PITFALLS, t, "[skill_pruned]")

    if F_RULES in texts:
        t = texts[F_RULES]
        rule_re = re.compile(r"^\*\*P\d+\.")
        check_provenance(F_RULES, t, rule_re, "Praxisregeln")
        check_min_count(f"{F_RULES}: Praxisregeln", len(split_sections(t, rule_re)), MIN_RULES)
        check_no_marker(F_RULES, t, "todo")
        check_no_marker(F_RULES, t, "[skill_pruned]")

    if F_SKILLS in texts:
        t = texts[F_SKILLS]
        rows = [l for l in t.splitlines() if l.lstrip().startswith("|") and "---" not in l and "Skill |" not in l and "| Skill " not in l]
        check_min_count(f"{F_SKILLS}: Skill-Zeilen", len(rows), MIN_SKILL_ROWS)
        check_no_marker(F_SKILLS, t, "todo")
        # jede Zeile muss eine Bewertung yes/partly/no tragen
        bad = [l[:60] for l in rows if not re.search(r"\|\s*(yes|partly|no)\s*\|", l)]
        record(f"{F_SKILLS}: jede Zeile mit yes/partly/no", not bad, "" if not bad else f"{len(bad)} ohne: {bad[:3]}")

    if F_ANTI in texts:
        t = texts[F_ANTI]
        check_anti_patterns(t)
        check_min_count(f"{F_ANTI}: Anti-Patterns", len(split_sections(t, re.compile(r"^### AP-\d+"))), MIN_ANTI)
        check_no_marker(F_ANTI, t, "todo")
        check_no_marker(F_ANTI, t, "[skill_pruned]")

    # Zusammenfassung
    print("=" * 72)
    print("Briefato brain/ – Praxis Selbstcheck")
    print("=" * 72)
    passed = 0
    for name, ok, detail in results:
        tag = "PASS" if ok else "FAIL"
        line = f"[{tag}] {name}"
        if detail:
            line += f"  ({detail})"
        print(line)
        if ok:
            passed += 1
    total = len(results)
    failed = total - passed
    print("-" * 72)
    print(f"Ergebnis: {passed}/{total} Checks bestanden, {failed} fehlgeschlagen.")
    if failed == 0:
        print("SUMMARY: PASS")
        return 0
    print("SUMMARY: FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
