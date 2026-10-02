#!/usr/bin/env python3
"""Briefato landing self-check.

Validates every static page in this directory without any external dependency
(standard library only). Run it with the repository virtualenv:

    .venv/bin/python landing/selfcheck.py

Checks per page:
  1. parses as HTML (doctype, closing </html>, balanced container tags)
  2. has a non-empty <title>, <meta name="viewport">, <html lang="de">,
     <meta charset="utf-8"> and a meta description
  3. every internal href/src resolves to an existing file
     (portal routes such as /anmelden are declared and accepted explicitly)
  4. zero external http(s) references anywhere in the file
  5. no "TODO", "Lorem" or "Platzhalter" text
  6. links the landing stylesheet, and that stylesheet exists
  7. exactly one <h1>; every <img> carries an alt attribute
  8. every <form> control has a matching <label>

Exit code is 0 when all pages pass, 1 otherwise.
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PAGES = [
    "index.html",
    "preise.html",
    "impressum.html",
    "datenschutz.html",
    "agb.html",
    "404.html",
]

STYLESHEET = "/assets/css/briefato.css"

# Routes served by the portal (WORKSTREAM-PORTAL) that intentionally have no
# file inside landing/. See docs/02-spec-interfaces.md §5.
PORTAL_ROUTES = {
    "/anmelden",
    "/registrieren",
    "/abmelden",
    "/passwort-vergessen",
    "/passwort-zuruecksetzen",
    "/app",
    "/healthz",
}

BANNED = ("todo", "lorem", "platzhalter")

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

# Container tags we expect to be explicitly closed in these hand-written pages.
BALANCED = {
    "html", "head", "body", "div", "article", "section", "header", "footer",
    "nav", "main", "ul", "ol", "li", "p", "h1", "h2", "h3", "table", "thead",
    "tbody", "tr", "th", "td", "details", "summary", "a", "span", "strong",
    "em", "svg", "g", "address", "button", "pre", "code", "small", "caption",
}

LINK_ATTRS = ("href", "src", "poster", "action", "data")


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: str | None = None
        self.title_parts: list[str] = []
        self.in_title = False
        self.metas: list[dict[str, str]] = []
        self.refs: list[tuple[str, str]] = []  # (tag, value) for href/src-like
        self.counts: dict[str, int] = {}
        self.h1 = 0
        self.imgs: list[dict[str, str]] = []
        self.labels_for: set[str] = set()
        self.inputs: list[dict[str, str]] = []
        self.text_parts: list[str] = []

    # --- tags ---
    def _count(self, tag: str, delta: int) -> None:
        if tag in BALANCED:
            self.counts[tag] = self.counts.get(tag, 0) + delta

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: (v or "") for k, v in attrs}
        if tag == "html" and self.html_lang is None:
            self.html_lang = a.get("lang")
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            self.metas.append(a)
        if tag == "h1":
            self.h1 += 1
        if tag == "img":
            self.imgs.append(a)
        if tag == "label":
            if a.get("for"):
                self.labels_for.add(a["for"])
        if tag in ("input", "select", "textarea"):
            self.inputs.append(a)
        for attr in LINK_ATTRS:
            if attr in a and a[attr]:
                self.refs.append((tag, a[attr]))
        if tag not in VOID:
            self._count(tag, 1)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self._count(tag, -1)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        self._count(tag, -1)

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        self.text_parts.append(data)


def _resolve(ref: str) -> tuple[str, Path | None]:
    """Return ('ok'|'portal'|'missing'|'external', resolved_path)."""
    ref = ref.strip()
    if not ref or ref.startswith("#"):
        return "ok", None
    if ref.startswith(("mailto:", "tel:", "data:", "javascript:")):
        return "ok", None
    if ref.startswith("//") or ref.startswith("http://") or ref.startswith("https://"):
        return "external", None

    path = ref.split("#", 1)[0].split("?", 1)[0]
    if path in PORTAL_ROUTES:
        return "portal", None

    if path.startswith("/"):
        rel = path.lstrip("/")
    else:
        rel = path  # relative to this directory (all pages live in ROOT)

    if rel == "" or rel.endswith("/"):
        candidate = ROOT / (rel + "index.html")
    else:
        candidate = ROOT / rel

    if candidate.is_file():
        return "ok", candidate
    # /preise -> preise.html
    if not candidate.suffix:
        alt = candidate.with_suffix(".html")
        if alt.is_file():
            return "ok", alt
    return "missing", candidate


def check_page(name: str) -> tuple[bool, list[str]]:
    path = ROOT / name
    problems: list[str] = []

    if not path.is_file():
        return False, ["Datei fehlt"]

    raw = path.read_text(encoding="utf-8")

    # 4. external references (strict raw scan, comments included)
    if "http://" in raw or "https://" in raw or "//cdn" in raw:
        problems.append("externe http(s)-Referenz gefunden")

    # 5. banned words
    low = raw.lower()
    for word in BANNED:
        if word in low:
            problems.append(f"verbotenes Wort: {word!r}")

    # 1. parses
    if not raw.lstrip().lower().startswith("<!doctype html>"):
        problems.append("kein <!DOCTYPE html>")
    if "</html>" not in low:
        problems.append("kein schließendes </html>")

    parser = PageParser()
    try:
        parser.feed(raw)
        parser.close()
    except Exception as exc:  # pragma: no cover - defensive
        return False, [f"HTML-Parserfehler: {exc}"]

    # balanced container tags
    bad = {t: c for t, c in parser.counts.items() if c != 0}
    if bad:
        problems.append("unbalancierte Tags: " + ", ".join(f"{t}({c:+d})" for t, c in sorted(bad.items())))

    # 2. head requirements
    title = "".join(parser.title_parts).strip()
    if not title:
        problems.append("kein <title>")
    if parser.html_lang != "de":
        problems.append("lang-Attribut ist nicht 'de'")
    charset_ok = any(m.get("charset", "").lower() == "utf-8" for m in parser.metas)
    if not charset_ok:
        problems.append("kein <meta charset=utf-8>")
    viewport_ok = any(m.get("name", "").lower() == "viewport" and m.get("content") for m in parser.metas)
    if not viewport_ok:
        problems.append("kein <meta name=viewport>")
    desc_ok = any(m.get("name", "").lower() == "description" and m.get("content") for m in parser.metas)
    if not desc_ok:
        problems.append("keine meta description")

    # 6. stylesheet
    if STYLESHEET not in raw:
        problems.append(f"Stylesheet {STYLESHEET} nicht verlinkt")
    if not (ROOT / STYLESHEET.lstrip("/")).is_file():
        problems.append(f"Stylesheet-Datei fehlt: {STYLESHEET}")

    # 7. structure
    if parser.h1 != 1:
        problems.append(f"genau eine <h1> erwartet, gefunden: {parser.h1}")
    for img in parser.imgs:
        if "alt" not in img:
            problems.append(f"<img> ohne alt: src={img.get('src', '?')}")

    # 8. form labels
    for inp in parser.inputs:
        itype = inp.get("type", "text").lower()
        if itype in ("hidden", "submit", "button", "reset", "image"):
            continue
        if inp.get("aria-label") or inp.get("aria-labelledby") or inp.get("title"):
            continue
        iid = inp.get("id")
        if not iid or iid not in parser.labels_for:
            problems.append(f"Formularfeld ohne <label>: {iid or '(' + itype + ')'}")

    # 3. internal references resolve
    for tag, value in parser.refs:
        status, resolved = _resolve(value)
        if status == "external":
            problems.append(f"externe Referenz in <{tag}>: {value}")
        elif status == "missing":
            problems.append(f"Ziel fehlt: <{tag}> {value} -> {resolved}")

    return (len(problems) == 0), problems


def main() -> int:
    print("Briefato landing self-check")
    print(f"Verzeichnis: {ROOT}")
    print("-" * 68)
    failed = 0
    for name in PAGES:
        ok, problems = check_page(name)
        if ok:
            print(f"PASS  {name}")
        else:
            failed += 1
            print(f"FAIL  {name}")
            for p in problems:
                print(f"        - {p}")
    print("-" * 68)
    total = len(PAGES)
    passed = total - failed
    print(f"Ergebnis: {passed}/{total} Seiten bestanden"
          + ("" if failed == 0 else f" — {failed} fehlgeschlagen"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
