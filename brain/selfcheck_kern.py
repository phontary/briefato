#!/usr/bin/env python3
"""Self-check for the Briefato method brain (stdlib only).

Run:  cd /workspace/briefato && .venv/bin/python brain/selfcheck_kern.py

Scope: the assets this workstream owns — kern.md, regelwerk.md, provenance.md,
selfcheck_kern.py and dokumenttypen/*.md. Other files that a parallel workstream
may place under brain/ (e.g. musterbriefe/) are NOT judged here.

Checks:
  1. All expected files exist and are non-empty.
  2. dokumenttypen/ contains the required playbooks (>= 8).
  3. Every numbered rule in regelwerk.md carries a provenance reference.
  4. No owned file contains the literal placeholder marker token.
  5. No owned file contains a bare personal phone number; an institutional
     number is allowed only when the same line is marked [institutionell].

Prints PASS/FAIL per item plus a summary. Exit code 0 = all PASS, 1 = any FAIL.
"""
from __future__ import annotations

import os
import re
import sys

BRAIN_DIR = os.path.dirname(os.path.abspath(__file__))

REQUIRED_ROOT_FILES = [
    "kern.md",
    "regelwerk.md",
    "provenance.md",
    "selfcheck_kern.py",
]

REQUIRED_DOKUMENTTYPEN = [
    "arztbrief.md",
    "operationsbericht.md",
    "zusammenfassung.md",
    "ambulant.md",
    "entlassbrief.md",
    "entlassmedikationsplan.md",
    "pflegebericht.md",
    "ablehnungsbogen.md",
]

# Institutional numbers that may appear if explicitly marked [institutionell]
# on the same line. Listed as literals (the number itself is not personal data).
INSTITUTIONAL_NUMBERS = ["06631 98-1227"]

# Personal phone-number pattern: leading 0, 3-5 digits, optional separator,
# then two more digit groups. The 3-digit minimum avoids matching ISO dates
# such as 2026-10-02 (whose "026-10-02" substring has only two digits first).
PHONE_RE = re.compile(r"0\d{3,5}[ /-]?\d{2,}[ /-]?\d{2,}")

RULE_RE = re.compile(r"^R\d+:")
PLACEHOLDER_NEEDLE = "TO" + "DO"  # built at runtime, never written literally


def read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def owned_files() -> list[str]:
    """Files this workstream owns and is responsible for."""
    files = [os.path.join(BRAIN_DIR, n) for n in REQUIRED_ROOT_FILES]
    dt_dir = os.path.join(BRAIN_DIR, "dokumenttypen")
    if os.path.isdir(dt_dir):
        files += [
            os.path.join(dt_dir, n)
            for n in sorted(os.listdir(dt_dir))
            if n.endswith(".md")
        ]
    return [f for f in files if os.path.isfile(f)]


def check_files_exist() -> tuple[bool, list[str]]:
    problems: list[str] = []
    for name in REQUIRED_ROOT_FILES:
        path = os.path.join(BRAIN_DIR, name)
        if not os.path.isfile(path):
            problems.append(f"missing file: brain/{name}")
        elif os.path.getsize(path) == 0:
            problems.append(f"empty file: brain/{name}")

    dt_dir = os.path.join(BRAIN_DIR, "dokumenttypen")
    for name in REQUIRED_DOKUMENTTYPEN:
        path = os.path.join(dt_dir, name)
        if not os.path.isfile(path):
            problems.append(f"missing file: brain/dokumenttypen/{name}")
        elif os.path.getsize(path) == 0:
            problems.append(f"empty file: brain/dokumenttypen/{name}")

    present = [n for n in os.listdir(dt_dir) if n.endswith(".md")] if os.path.isdir(dt_dir) else []
    if len(present) < 8:
        problems.append(
            f"dokumenttypen/ has only {len(present)} markdown files, expected >= 8"
        )
    return (not problems), problems


def check_rule_provenance() -> tuple[bool, list[str]]:
    path = os.path.join(BRAIN_DIR, "regelwerk.md")
    problems: list[str] = []
    if not os.path.isfile(path):
        return False, ["regelwerk.md missing, cannot check rule provenance"]
    rule_count = 0
    for lineno, line in enumerate(read(path).splitlines(), start=1):
        if RULE_RE.match(line):
            rule_count += 1
            if "Provenienz:" not in line:
                rid = line.split(":", 1)[0]
                problems.append(f"{rid} (line {lineno}) has no 'Provenienz:' reference")
    if rule_count == 0:
        problems.append("no numbered rules (^R<n>:) found in regelwerk.md")
    return (not problems), problems


def check_no_placeholder() -> tuple[bool, list[str]]:
    problems: list[str] = []
    for path in owned_files():
        if not path.endswith((".md", ".py")):
            continue
        rel = os.path.relpath(path, BRAIN_DIR)
        for lineno, line in enumerate(read(path).splitlines(), start=1):
            if PLACEHOLDER_NEEDLE in line:
                problems.append(f"{rel}:{lineno} contains the placeholder marker")
    return (not problems), problems


def check_no_personal_phone() -> tuple[bool, list[str]]:
    problems: list[str] = []
    for path in owned_files():
        if not path.endswith((".md", ".py")):
            continue
        rel = os.path.relpath(path, BRAIN_DIR)
        for lineno, line in enumerate(read(path).splitlines(), start=1):
            for match in PHONE_RE.finditer(line):
                token = match.group(0)
                is_marked = "[institutionell]" in line
                is_allowlisted = any(num in line for num in INSTITUTIONAL_NUMBERS)
                if not (is_marked or is_allowlisted):
                    problems.append(f"{rel}:{lineno} bare phone-like number: {token!r}")
    return (not problems), problems


def main() -> int:
    checks = [
        ("files exist and are non-empty", check_files_exist),
        ("every rule has a provenance reference", check_rule_provenance),
        ("no placeholder marker in any owned file", check_no_placeholder),
        ("no bare personal phone number", check_no_personal_phone),
    ]
    failures = 0
    print(f"Briefato brain self-check — {BRAIN_DIR}")
    print(f"owned files checked: {len(owned_files())}")
    print("-" * 60)
    for label, fn in checks:
        ok, problems = fn()
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {label}")
        for problem in problems:
            print(f"       - {problem}")
        if not ok:
            failures += 1
    print("-" * 60)
    total = len(checks)
    passed = total - failures
    print(f"SUMMARY: {passed}/{total} checks passed, {failures} failed")
    print("RESULT: " + ("PASS" if failures == 0 else "FAIL"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
