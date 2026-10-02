"""Bridge from the portal to the Briefato method "brain" (WORKSTREAM-PORTAL).

The frozen interface (``docs/02-spec-interfaces.md`` §6, extended by the parallel brain
workstream) is expected to expose::

    briefato.brain.triage.detect(text, explicit_type) -> ...
    briefato.brain.triage.TYPES
    briefato.brain.retrieval.search(text) -> ...
    briefato.brain.rule_checker.check(text, doc_type, dictation) -> ...
    briefato.brain.brain_loader

This module calls those names when the package is importable and normalises their results
into small, stable dicts the templates can render. When the package is not importable it
falls back to a **portal-side preliminary implementation** built only from the brain's own
read-only data files (``regelwerk.md``, ``manifest.json``, the dokumenttypen playbooks) so
the editor keeps working, and reports which source produced the result. It never raises:
a broken/importerror brain degrades to a German message, not a stack trace.
"""

from __future__ import annotations

import html
import json
import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("briefato.method")

# repo root: .../app/briefato/routes/brain_bridge.py -> parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]
BRAIN_DIR = REPO_ROOT / "brain"
MANIFEST_PATH = BRAIN_DIR / "musterbriefe" / "manifest.json"
DOKUMENTTYPEN_DIR = BRAIN_DIR / "dokumenttypen"
KERN_PATH = BRAIN_DIR / "kern.md"
REGELWERK_PATH = BRAIN_DIR / "regelwerk.md"
PRAXIS_PATH = BRAIN_DIR / "regeln-aus-praxis.md"
ANTIPATTERNS_PATH = BRAIN_DIR / "ANTI-PATTERNS.md"

AUTO_TYPE = "auto"
DEFAULT_DOC_TYPE = "arztbrief"

# From brain/musterbriefe/scrub-report.md "Manuell bestätigte Treffer": these files carry
# real patient traces and MUST NOT be reachable from the product until Mohamed has cleaned
# them. They stay visible in the library as "gesperrt (Prüfung ausstehend)".
SCRUB_PENDING: tuple[str, ...] = (
    "Cholezystolithiasis.md",
    "Struma_nodosa_Hyperthyreose.md",
    "Acne-inversa.md",
)

# Fallback type catalog; keys match brain/dokumenttypen/*.md. ``triage.TYPES`` wins when the
# brain package is importable.
FALLBACK_TYPES: tuple[tuple[str, str], ...] = (
    ("arztbrief", "Arztbrief (stationär)"),
    ("ambulant", "Ambulanter / tageschirurgischer Brief"),
    ("operationsbericht", "Operationsbericht"),
    ("zusammenfassung", "Zusammenfassung"),
    ("entlassmedikationsplan", "Entlassmedikationsplan"),
    ("pflegebericht", "Pflegebericht (Integration)"),
    ("ablehnungsbogen", "Ablehnungsbogen (Thieme Compliance)"),
    ("weiterbildung-kv-nachweise", "Weiterbildung / KV-Nachweise"),
)

# Fallback routing, derived verbatim from the trigger table in brain/kern.md §2 / §K2.
_ROUTING_TRIGGERS: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("zusammenfassung",), "zusammenfassung", "Auftrag „Zusammenfassung“ (K2.3)"),
    (("op-bericht", "operationsbericht", "op bericht"), "operationsbericht", "Auftrag „OP-Bericht“ (K2.2)"),
    (("ambulant", "tageschirurgisch", "nfa"), "ambulant", "Ambulanter/tageschirurgischer Fall (K2.1/K57)"),
    (("medikationsplan", "mop", "mediks plan"), "entlassmedikationsplan", "Auftrag „Medikationsplan“ (K8.3)"),
    (("ablehnungsbogen",), "ablehnungsbogen", "Auftrag „Ablehnungsbogen“"),
    (("weiterbildung", "wbo", "kv-genehmigung", "logbuch"), "weiterbildung-kv-nachweise", "Nachweis-/Rechtsfrage"),
    (("pflegebericht",), "pflegebericht", "Pflegeberichte als Quellmaterial"),
)

# Fallback rule checks: a deliberately small, unambiguous subset of brain/regelwerk.md that
# can be checked mechanically. Ma\u00dfgeblich ist rule_checker.check der Methode.
_FALLBACK_TRANSLITERATIONS = (
    "fuer", "ueber", "koennen", "muessen", "waere", "moeglich", "moeglichkeit",
    "aerzt", "aertzlich", "oefter", "haeufig", "hauefig", "ausserdem", "groesse",
)
_ALLOWED_END_LABELS = (
    "Diagnosen:", "Nebenerkrankungen:", "Therapie-Maßnahmen auf der Station:",
    "ambulante Therapieempfehlungen nach der Entlassung:",
)


class MethodUnavailable(Exception):
    """Raised internally when the brain package cannot be imported."""


# --------------------------------------------------------------------------- brain import


@lru_cache(maxsize=1)
def _import_brain():
    """Import and return the brain submodules, or None if unavailable.

    Cached so a missing package is only probed once per process; importing the platform on
    every request would be wasteful. ``briefato.pipeline`` is imported first on purpose:
    the brain's prompt assembly imports the pipeline prompts, and importing the pipeline
    first keeps that dependency graph acyclic (importing the brain first can otherwise fail
    with a circular-import error depending on which module the process loaded first).
    """
    try:
        import briefato.pipeline  # noqa: F401
    except Exception:  # noqa: BLE001 - the pipeline itself is another workstream's concern
        pass
    try:
        from briefato.brain import brain_loader, retrieval, rule_checker, triage  # type: ignore
    except Exception as exc:  # ImportError or any error inside the package
        logger.info("briefato.brain is not importable (%s); using portal fallback", type(exc).__name__)
        return None
    return {"triage": triage, "retrieval": retrieval, "rule_checker": rule_checker, "loader": brain_loader}


def brain_available() -> bool:
    return _import_brain() is not None


def method_message() -> str:
    """German note shown when the platform-side method is not importable."""
    return (
        "Die Methode (briefato.brain) ist in dieser Umgebung nicht eingebunden. "
        "Es wird die portal-seitige Vorprüfung verwendet; maßgeblich ist die Methode."
    )


# --------------------------------------------------------------------------- helpers


def _norm(value: str) -> str:
    text = (value or "").lower()
    for a, b in (("\u00e4", "ae"), ("\u00f6", "oe"), ("\u00fc", "ue"), ("\u00df", "ss")):
        text = text.replace(a, b)
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


# public alias: the same normalisation the brain's retrieval_selftest.py uses
normalize = _norm


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _first(obj, *keys, default=""):
    for key in keys:
        if isinstance(obj, dict) and key in obj and obj[key] not in (None, ""):
            return obj[key]
        value = getattr(obj, key, None)
        if value not in (None, ""):
            return value
    return default


# --------------------------------------------------------------------------- document types


def available_types() -> list[dict[str, str]]:
    """Document types for the selector: ``[{"key","label"}]`` (brain first, fallback second)."""
    brain = _import_brain()
    if brain is not None:
        module = brain["triage"]
        options = getattr(module, "doc_type_options", None)
        if callable(options):
            try:
                normalised = _normalise_types(options())
                if normalised:
                    return normalised
            except Exception as exc:  # noqa: BLE001
                logger.warning("triage.doc_type_options failed: %s", type(exc).__name__)
        for attribute in ("TYPES", "DOC_TYPES"):
            normalised = _normalise_types(getattr(module, attribute, None))
            if normalised:
                return normalised
    return [{"key": key, "label": label} for key, label in FALLBACK_TYPES]


def _normalise_types(raw) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not raw:
        return out
    items = raw.items() if isinstance(raw, dict) else raw
    for item in items:
        if isinstance(item, dict):
            key = str(_first(item, "key", "id", "type", "slug", "value", default="")).strip()
            label = str(_first(item, "label", "title", "name", "text", default=key)).strip()
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            key, label = str(item[0]).strip(), str(item[1]).strip()
        else:
            key = label = str(item).strip()
        if key:
            out.append({"key": key, "label": label or key})
    return out


def type_label(key: str) -> str:
    for entry in available_types():
        if entry["key"] == key:
            return entry["label"]
    for key2, label in FALLBACK_TYPES:
        if key2 == key:
            return label
    return key or DEFAULT_DOC_TYPE


def resolve_explicit_type(raw: str | None) -> str:
    """Map a submitted selector value to a concrete key, or ``AUTO_TYPE``."""
    value = (raw or "").strip()
    if not value or value in (AUTO_TYPE, "standard"):
        return AUTO_TYPE
    known = {entry["key"] for entry in available_types()}
    return value if value in known else AUTO_TYPE


def detect_type(text: str, explicit_type: str | None = None) -> dict:
    """Return ``{"key","label","reason","explicit"}`` for the document type."""
    explicit = resolve_explicit_type(explicit_type)
    if explicit != AUTO_TYPE:
        return {
            "key": explicit,
            "label": type_label(explicit),
            "reason": "Von Ihnen gewählt.",
            "explicit": True,
        }

    brain = _import_brain()
    if brain is not None:
        module = brain["triage"]
        function = getattr(module, "detect", None) or getattr(module, "triage", None)
        if callable(function):
            try:
                result = function(text or "", None)
                data = result.as_dict() if hasattr(result, "as_dict") else result
                key = str(_first(data, "type", "key", "doc_type", "document_type", default="")).strip()
                if key:
                    reason = str(_first(data, "reason", "rationale", "why", default="")).strip()
                    return {
                        "key": key,
                        "label": str(_first(data, "label", "title", default=type_label(key))).strip(),
                        "reason": reason or "Automatisch erkannt.",
                        "explicit": False,
                    }
            except Exception as exc:  # noqa: BLE001 - never break the editor on a brain bug
                logger.warning("triage.detect failed: %s", type(exc).__name__)

    haystack = _norm(text or "")
    for needles, key, reason in _ROUTING_TRIGGERS:
        if any(needle in haystack for needle in needles):
            return {"key": key, "label": type_label(key), "reason": reason, "explicit": False}
    return {
        "key": DEFAULT_DOC_TYPE,
        "label": type_label(DEFAULT_DOC_TYPE),
        "reason": "Kein spezieller Auftrag erkannt – Default ist der stationäre Arztbrief (K2.1).",
        "explicit": False,
    }


# --------------------------------------------------------------------------- template library


@lru_cache(maxsize=1)
def load_manifest() -> dict:
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("Musterbriefe manifest unreadable: %s", type(exc).__name__)
        return {"count": 0, "templates": [], "groups": {}, "source": ""}


def manifest_templates() -> list[dict]:
    return list(load_manifest().get("templates") or [])


def template_entry(file_name: str) -> dict | None:
    for entry in manifest_templates():
        if entry.get("file") == file_name:
            return entry
    return None


def is_locked(file_name: str) -> bool:
    return file_name in SCRUB_PENDING


def _source_dir() -> Path | None:
    override = os.environ.get("BRIEFATO_MUSTERBRIEFE_DIR", "").strip()
    candidates = [Path(override)] if override else []
    source = (load_manifest().get("source") or "").strip()
    if source:
        candidates.append(Path(source))
    candidates.append(BRAIN_DIR / "musterbriefe")
    for candidate in candidates:
        try:
            if candidate.is_dir() and any(candidate.glob("*.md")):
                return candidate
        except OSError:
            continue
    return None


def template_body(file_name: str) -> str | None:
    """Full text of a template, or ``None`` when locked / not found / archive absent."""
    if is_locked(file_name):
        return None
    if "/" in file_name or "\\" in file_name or file_name.startswith("."):
        return None
    brain = _import_brain()
    if brain is not None:
        try:
            text = brain["loader"].read_template(file_name)
            if text:
                return text
        except Exception:  # noqa: BLE001 - fall through to the portal-side resolution
            pass
    directory = _source_dir()
    if directory is None:
        return None
    path = (directory / file_name).resolve()
    if directory.resolve() not in path.parents:
        return None
    text = _read_text(path)
    return text or None


def archive_available() -> bool:
    return _source_dir() is not None


def _score_against(text_norm: str, tokens: set[str]) -> int:
    if not text_norm or not tokens:
        return 0
    words = set(text_norm.split())
    hits = {t for t in tokens if len(t) >= 4 and (t in words or t in text_norm)}
    return len(hits)


def search_templates(text: str, limit: int = 5) -> list[dict]:
    """Match Musterbriefe to a dictation. Brain retrieval wins; manifest scoring is the fallback."""
    brain = _import_brain()
    if brain is not None:
        module = brain["retrieval"]
        function = getattr(module, "search", None) or getattr(module, "retrieve", None)
        if callable(function):
            try:
                raw = function(text or "")
                normalised = _normalise_search(raw)
                if normalised is not None:
                    return normalised[:limit]
            except Exception as exc:  # noqa: BLE001
                logger.warning("retrieval.search failed: %s", type(exc).__name__)

    haystack = _norm(text or "")
    if not haystack:
        return []
    scored: list[tuple[int, dict]] = []
    for entry in manifest_templates():
        file_name = str(entry.get("file", ""))
        if is_locked(file_name):
            continue
        tokens = set(_norm(entry.get("title", "")).split())
        for keyword in entry.get("indication_keywords", []) or []:
            tokens.update(_norm(keyword).split())
        tokens.discard("")
        score = _score_against(haystack, tokens)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda item: (-item[0], -(item[1].get("chars") or 0)))
    out = []
    for score, entry in scored[:limit]:
        out.append({"file": entry.get("file", ""), "title": entry.get("title", ""), "score": score})
    return out


def _normalise_search(raw) -> list[dict] | None:
    """Accept a list of dicts / dataclasses / tuples / filenames from the brain, flatten it."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = raw.get("results", raw.get("matches", raw.get("templates")))
        if raw is None:
            return None
    out: list[dict] = []
    for item in raw:
        if hasattr(item, "as_dict"):
            item = item.as_dict()
        if isinstance(item, dict):
            file_name = str(_first(item, "file", "filename", "id", default="")).strip()
            title = str(_first(item, "title", "name", default="")).strip()
            score = _first(item, "score", "rank", "weight", default=0)
        elif isinstance(item, (tuple, list)) and item:
            file_name = str(item[0]).strip()
            title = ""
            score = item[1] if len(item) > 1 else 0
        else:
            file_name = str(item).strip()
            title = ""
            score = 0
        if not file_name:
            continue
        if isinstance(score, float):
            score = round(score, 2)
        entry = template_entry(file_name)
        out.append({
            "file": file_name,
            "title": title or (entry or {}).get("title", file_name),
            "score": score,
        })
    return out


# --------------------------------------------------------------------------- rule check


def rule_count() -> int:
    rules = rules_grouped()
    return sum(len(group["rules"]) for group in rules) or 67


def rules_grouped() -> list[dict]:
    """Parse ``regelwerk.md`` into ``[{"title","rules":[{"id","text","provenance"}]}]``."""
    text = _read_text(REGELWERK_PATH)
    groups: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current = {"title": heading.group(1).strip(), "rules": []}
            groups.append(current)
            continue
        rule = re.match(r"^(R\d+):\s*(.+?)\s*$", line)
        if rule and current is not None:
            body = rule.group(2)
            provenance = ""
            if "\u2014 Provenienz:" in body:
                body, provenance = body.split("\u2014 Provenienz:", 1)
            elif "— Provenienz:" in body:
                body, provenance = body.split("— Provenienz:", 1)
            current["rules"].append({
                "id": rule.group(1),
                "text": body.strip().rstrip(".") + ".",
                "provenance": provenance.strip(),
            })
    return [g for g in groups if g["rules"]]


def check_rules(text: str, doc_type: str, dictation: str = "") -> dict:
    """Normalised rule check: ``{"source","available","clean","findings","rules_total"}``."""
    total = rule_count()
    brain = _import_brain()
    if brain is not None:
        module = brain["rule_checker"]
        function = getattr(module, "check", None)
        if callable(function):
            try:
                raw = function(text or "", doc_type, dictation or "")
                findings = _normalise_findings(raw)
                counted = _first(raw, "rule_count", default=None)
                return {
                    "source": "methode",
                    "available": True,
                    "clean": not findings,
                    "findings": findings,
                    "rules_total": int(counted) if counted else total,
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("rule_checker.check failed: %s", type(exc).__name__)

    findings = _fallback_findings(text or "", doc_type or DEFAULT_DOC_TYPE)
    return {
        "source": "portal",
        "available": True,
        "clean": not findings,
        "findings": findings,
        "rules_total": total,
    }


def _normalise_findings(raw) -> list[dict]:
    """Accept the brain's CheckResult/dataclasses or plain dicts/lists and flatten them."""
    if raw is None:
        return []
    if hasattr(raw, "findings"):
        raw = raw.findings
    if hasattr(raw, "as_dict"):
        raw = raw.as_dict()
    if isinstance(raw, dict):
        combined: list = []
        for key in ("findings", "violations", "issues"):
            if isinstance(raw.get(key), list):
                combined.extend(raw[key])
        if not combined:
            for key in ("hard", "soft"):
                if isinstance(raw.get(key), list):
                    combined.extend(raw[key])
        raw = combined
    out: list[dict] = []
    for item in raw or []:
        if hasattr(item, "as_dict"):
            item = item.as_dict()
        severity = ""
        if isinstance(item, dict):
            rule = str(_first(item, "rule", "rule_id", "id", "code", default="")).strip()
            message = str(_first(item, "message", "text", "reason", "detail", "explanation", default="")).strip()
            severity = str(_first(item, "severity", default="")).strip()
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            rule, message = str(item[0]).strip(), str(item[1]).strip()
        else:
            rule, message = "", str(item).strip()
        if not rule and not message:
            continue
        out.append({
            "rule": rule or "R",
            "message": message or "Regel nicht erfüllt.",
            "severity": severity,
        })
    return out


def _fallback_findings(text: str, doc_type: str) -> list[dict]:
    findings: list[dict] = []
    body = text or ""

    if re.search(r"(\*\*|__|`|^\s{0,3}#{1,6}\s|^\s{0,3}[-*+]\s|^\s{0,3}\d+\.\s|\[[^\]]+\]\([^)]+\))", body, re.M):
        findings.append({"rule": "R4", "message": "Der Text enthält Markdown-Formatierung; die Ausgabe muss reiner Text sein."})
    if re.search(r"(?i)hiermit berichten wir|wir berichten über|o\.\s*g\.\s*pat", body):
        findings.append({"rule": "R2", "message": "Der Text enthält einen Einleitungssatz; der Brief beginnt ohne Einleitung."})
    if re.search(r"(?i)zusammenfassend lässt sich|abschließend lässt sich|abschliessend laesst", body):
        findings.append({"rule": "R3", "message": "Der Text enthält eine Schlussfloskel; der Brief endet ohne Zusammenfassung."})
    label = re.search(r"(?m)^\s*(KU|Labor|Sono|Sonografie|CT|MRT|Befund|Therapie|Anamnese|Diagnostik|Klinik)\s*:\s*\S", body)
    if label:
        findings.append({"rule": "R5", "message": f"Kategorie-Label „{label.group(1)}:“ im Fließtext; die Informationen gehören in den Erzähltext."})
    lowered = body.lower()
    bad = [needle for needle in _FALLBACK_TRANSLITERATIONS if needle in lowered]
    if bad:
        findings.append({"rule": "R6", "message": "Umlaute/ß fehlen (ae/oe/ue/ss). Ausgabetext muss ä, ö, ü und ß verwenden."})
    if body.count(";") > 1:
        findings.append({"rule": "R8", "message": "Mehr als ein Semikolon; höchstens eines pro Brief, im Zweifel keines."})
    if doc_type == "zusammenfassung":
        if re.search(r"(?m)^Diagnosen:\s*$", body):
            findings.append({"rule": "R24", "message": "Die Zusammenfassung enthält eine Diagnoseliste; sie muss ohne Diagnoseliste auskommen."})
    elif doc_type in ("arztbrief", "ambulant", "operationsbericht"):
        if not re.search(r"(?m)^Diagnosen:\s*$", body):
            findings.append({"rule": "R21", "message": "Keine Diagnoseliste am Dokumentende (Zeile „Diagnosen:“) gefunden."})
    diag = re.search(r"(?m)^Diagnosen:\s*$", body)
    if diag and re.search(r"(?m)^(Dg\.:|\d+\.\s|[-*]\s)", body[diag.end():]):
        findings.append({"rule": "R22", "message": "Die Diagnoseliste enthält Präfixe/Nummerierung/Aufzählungszeichen."})
    return findings


# --------------------------------------------------------------------------- method text


def kern_sections() -> list[dict]:
    """Parse ``kern.md`` into ``[{"title","rules":[{"id","title","text"}]}]``."""
    text = _read_text(KERN_PATH)
    groups: list[dict] = []
    current: dict | None = None
    block: dict | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal block, buffer
        if block is not None:
            block["text"] = "\n".join(line for line in buffer if line.strip()).strip()
            current["rules"].append(block)  # type: ignore[union-attr]
        block, buffer = None, []

    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            flush()
            current = {"title": heading.group(1).strip(), "rules": []}
            groups.append(current)
            continue
        rule = re.match(r"^-\s+\*\*(K[\d.]+)\s*[—-]\s*(.+?)\*\*\s*(.*)$", line)
        if rule and current is not None:
            flush()
            block = {"id": rule.group(1), "title": rule.group(2).strip().rstrip("."), "text": ""}
            if rule.group(3).strip():
                buffer.append(rule.group(3).strip())
            continue
        if block is not None and line.strip():
            buffer.append(re.sub(r"^\s+", "", line))
    flush()
    return [g for g in groups if g["rules"]]


def practice_groups() -> list[dict]:
    """Parse ``regeln-aus-praxis.md`` into ``[{"title","rules":[{"id","text","provenance"}]}]``."""
    text = _read_text(PRAXIS_PATH)
    groups: list[dict] = []
    current: dict | None = None
    regex = re.compile(r"^\*\*(P\d+)\.\*\*\s*(.*)$")
    buffer: list[str] = []
    pending: dict | None = None

    def flush() -> None:
        nonlocal pending, buffer
        if pending is not None:
            whole = " ".join(buffer).strip()
            provenance = ""
            match = re.search(r"Provenienz:\s*(.*)$", whole, re.S)
            if match:
                provenance = match.group(1).strip()
                whole = whole[: match.start()].strip()
            pending["text"] = re.sub(r"\s+", " ", whole).strip()
            pending["provenance"] = re.sub(r"\s+", " ", provenance).strip()
            current["rules"].append(pending)  # type: ignore[union-attr]
        pending, buffer = None, []

    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            flush()
            current = {"title": heading.group(1).strip(), "rules": []}
            groups.append(current)
            continue
        started = regex.match(line)
        if started and current is not None:
            flush()
            pending = {"id": started.group(1), "text": "", "provenance": ""}
            buffer.append(started.group(2))
            continue
        if pending is not None and line.strip():
            buffer.append(line.strip())
    flush()
    return [g for g in groups if g["rules"]]


def anti_patterns() -> list[dict]:
    """Parse ``ANTI-PATTERNS.md`` into ``[{"id","title","generic","replacement","provenance"}]``."""
    text = _read_text(ANTIPATTERNS_PATH)
    items: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        heading = re.match(r"^###\s+(AP-\d+)\s*[—-]\s*(.+?)\s*$", line)
        if heading:
            current = {"id": heading.group(1), "title": heading.group(2).strip(),
                       "generic": "", "replacement": "", "provenance": ""}
            items.append(current)
            continue
        if current is None:
            continue
        field = re.match(r"^-\s+\*\*(.+?):\*\*\s*(.*)$", line.strip())
        if field:
            name, value = field.group(1).lower(), field.group(2).strip()
            if "llm tut" in name or "generische" in name:
                current["generic"] = value
            elif "ersatzregel" in name:
                current["replacement"] = value
            elif "provenienz" in name:
                current["provenance"] = value
    return items


def render_markdown_lite(text: str) -> str:
    """Escape HTML then render ``#``/``##`` headings and paragraphs. Safe for template use."""
    if not text:
        return ""
    out: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            out.append("<p>" + "<br>".join(html.escape(line) for line in paragraph) + "</p>")
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line:
            flush()
            continue
        heading = re.match(r"^(#{1,4})\s+(.*)$", line)
        if heading:
            flush()
            level = min(len(heading.group(1)) + 1, 5)
            out.append(f"<h{level}>{html.escape(heading.group(2).strip())}</h{level}>")
            continue
        paragraph.append(line.strip())
    flush()
    return "\n".join(out)


__all__ = [
    "AUTO_TYPE",
    "DEFAULT_DOC_TYPE",
    "SCRUB_PENDING",
    "anti_patterns",
    "archive_available",
    "available_types",
    "brain_available",
    "check_rules",
    "detect_type",
    "is_locked",
    "kern_sections",
    "load_manifest",
    "manifest_templates",
    "method_message",
    "normalize",
    "practice_groups",
    "render_markdown_lite",
    "resolve_explicit_type",
    "rule_count",
    "rules_grouped",
    "search_templates",
    "template_body",
    "template_entry",
    "type_label",
]
