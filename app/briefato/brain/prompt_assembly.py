"""Prompt assembly from the brain — system + user prompt for one document.

OWNER: WORKSTREAM-BRAIN-WIRING.

The assembled prompt is grounded in Mohamed's real method, not an invented generic
policy. It is built from:

* ``kern.md`` — the method (the five SOUL core rules + routing + verbote),
* ``regelwerk.md`` — R1..R67 as machine-testable rule lines,
* ``ANTI-PATTERNS.md`` — AP-01..AP-25 (what the generic LLM does wrong),
* the document-type playbook (``dokumenttypen/<typ>.md``),
* the retrieved Musterbriefe's **sections** (structure reference only — never the
  licensed prose of a ``reference_only`` template),
* the member's letterhead / practice data and optional
  ``user.letterhead_json['custom_rules']``.

The output is mandated to be plain text: no markdown, no category labels, no
intro/closing, the ``Diagnosen:`` list at the end, and the labelled blocks in the
exact order of the playbook.

The pseudonymisation contract is unchanged: the caller passes an already-masked
dictation and patient context, and this module only ever embeds ``{{TOKEN}}``
placeholders — it never sees raw identifiers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import brain_loader, retrieval

# The dictation markers live in ``..pipeline.prompts`` (frozen, single source of
# truth). They are imported lazily inside build_prompt to avoid a circular import
# (pipeline/__init__ -> generate -> brain.prompt_assembly).

PROMPT_VERSION = "brain-1"

# Practice fields shown to the model (never patient identifiers).
LETTERHEAD_LABELS: dict[str, str] = {
    "practice_name": "Praxisname",
    "full_name": "Ärztin/Arzt",
    "street": "Straße",
    "zip": "PLZ",
    "city": "Ort",
    "phone": "Telefon",
    "email": "E-Mail",
    "tax_id": "Steuernummer",
    "website": "Website",
}

# Block order for a stationary discharge letter (R25-R27).
DISCHARGE_BLOCK_ORDER = (
    "ambulante Therapieempfehlungen nach der Entlassung:",
    "Diagnosen:",
    "Nebenerkrankungen:",
    "Therapie-Maßnahmen auf der Station:",
)

_KERN_RULE_RE = re.compile(r"^- \*\*(K[\d.]+)\s*—\s*(.+?)\*\*$")


def _kern_rules() -> list[str]:
    """Extract ``K<id> — <title>: <(a) sentence>`` lines from kern.md."""
    rules: list[str] = []
    current: tuple[str, str] | None = None
    for line in brain_loader.kern_text().splitlines():
        match = _KERN_RULE_RE.match(line.strip())
        if match:
            current = (match.group(1), match.group(2).strip())
            continue
        if current is not None:
            stripped = line.strip()
            if stripped.startswith("(a)"):
                body = stripped[3:].strip()
                rules.append(f"{current[0]} — {current[1]}: {body}")
                current = None
    return rules


def _render_pairs(data: dict, labels: dict[str, str]) -> str:
    out: list[str] = []
    for key, label in labels.items():
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            out.append(f"- {label}: {text}")
    return "\n".join(out)


@dataclass
class PromptBundle:
    system: str
    user: str
    doc_type: str
    doc_types: tuple[str, ...]
    template_files: list[str] = field(default_factory=list)
    reference_only_files: list[str] = field(default_factory=list)
    kern_rules: int = 0
    regelwerk_rules: int = 0
    prompt_version: str = PROMPT_VERSION

    @property
    def combined(self) -> bool:
        return len(self.doc_types) > 1

    def as_dict(self) -> dict[str, object]:
        return {
            "doc_type": self.doc_type,
            "doc_types": list(self.doc_types),
            "template_files": list(self.template_files),
            "reference_only_files": list(self.reference_only_files),
            "kern_rules": self.kern_rules,
            "regelwerk_rules": self.regelwerk_rules,
            "prompt_version": self.prompt_version,
        }


def _output_mandate(doc_type: str) -> str:
    label = brain_loader.DOKUMENTTYP_LABELS.get(doc_type, doc_type)
    blocks = "\n".join(f"  {index}. {block}" for index, block in enumerate(DISCHARGE_BLOCK_ORDER, 1))
    extra = ""
    if doc_type == "zusammenfassung":
        extra = (
            "\n- AUSNAHME Zusammenfassung: KEINE Diagnoseliste, KEINE Therapie-Maßnahmen-Liste, "
            "3–4 Sätze Fließtext, Datum abgekürzt als Monat (z. B. „Sep. 2026“)."
        )
    if doc_type == "operationsbericht":
        extra = (
            "\n- OP-Bericht: Absätze mit den Labels „Indikation:“, „OP:“, „Präparat:“; am Dokumentende "
            "„Diagnosen:“ (ein Eintrag/Zeile) und „Operation:“."
        )
    if doc_type == "ambulant":
        extra = (
            "\n- Ambulant: KEIN „wir nahmen … stationär auf“-Satz, KEINE Therapie-Maßnahmen-Liste; "
            "Diagnoseliste am Ende."
        )
    return (
        f"VERBINDLICHES AUSGABEFORMAT für „{label}“:\n"
        "- Reiner Plain-Text, copy-paste-fähig. KEIN Markdown (keine *, _, #, `, Tabellen, "
        "Aufzählungszeichen im Erzähltext).\n"
        "- KEINE Kategorie-Labels im Fließtext (nicht „KU:“, „Labor:“, „Sono:“, „CT:“, „Anamnese:“, "
        "„Befund:“, „Therapie:“). Ein durchgehender Erzähltext.\n"
        "- KEINE Einleitung (nicht „Hiermit berichten wir“, nicht „Wir berichten über o. g. Pat.“) und "
        "KEINE Schlussfolgerung/Floskel.\n"
        "- Korrekte deutsche Umlaute (ä, ö, ü) und ß; KEIN ae/oe/ue/ss.\n"
        "- Höchstens EIN Semikolon im gesamten Text, im Zweifel keines.\n"
        "- Keine Datumsangaben im Verlauf („am TT.MM.“) — nur OP-Datum und Entlassdatum; fehlendes "
        "Datum als Platzhalter XXX, nicht erfinden.\n"
        "- Die Diagnosen stehen als Liste am Dokumentende, eingeleitet durch die Plain-Text-Zeile "
        "„Diagnosen:“ (kein „Dg.:“-Präfix, keine Nummerierung).\n"
        "- Blockreihenfolge bei stationärem Entlassbrief:\n"
        f"{blocks}\n"
        "- Keine erfundenen Diagnosen, ICD-Codes, Befunde, Laborwerte, Konsile, Dosierungen oder "
        "Patientendaten.\n"
        f"{extra}"
    )


def _pseudonym_contract() -> str:
    return (
        "PSEUDONYMISIERUNG (nicht abschwächen): Alle Platzhalter in doppelten geschweiften Klammern "
        "(z. B. {{LAST_NAME}}, {{FIRST_NAME}}, {{BIRTH_DATE}}, {{INSURANCE_NUMBER}}, {{STREET}}, "
        "{{ZIP}}, {{CITY}}, {{PHONE}}, {{EMAIL}}) sind patientenbezogene Daten. Sie sind exakt "
        "(Großschreibung, doppelte Klammern) und unverändert im Text zu belassen, dürfen nie erklärt, "
        "ausgeschrieben, übersetzt oder verändert werden. Erfinden Sie keine Patientendaten."
    )


def _structure_reference(templates: list[retrieval.TemplateHit]) -> str:
    if not templates:
        return "- (keine Musterbrief-Treffer; Struktur ausschließlich aus dem Playbook ableiten)"
    lines: list[str] = []
    for hit in templates:
        marker = " [REFERENCE-ONLY – nur Struktur, Prosa NICHT übernehmen]" if hit.reference_only else ""
        sections = ", ".join(hit.sections_present) or "(keine)"
        lines.append(f"- {hit.title} ({hit.file}, {hit.score:.3f}){marker}\n  Sektionen: {sections}")
    lines.append(
        "Hinweis: Musterbriefe dienen ausschließlich als Strukturvorlage (Sektionen "
        "Klinik/Diagnostik/Therapie/Nachsorge). Keine Prosa, keine Falldaten übernehmen."
    )
    return "\n".join(lines)


def build_prompt(
    *,
    doc_type: str,
    dictation: str,
    letterhead: dict | None = None,
    patient_ctx: dict | None = None,
    templates: list[retrieval.TemplateHit] | None = None,
    custom_rules: str = "",
    extra: str = "",
    doc_types: tuple[str, ...] | None = None,
    language: str = "de",
) -> PromptBundle:
    """Assemble the system + user prompt for one document of ``doc_type``.

    ``dictation`` and ``patient_ctx`` must already be pseudonymised by the caller.
    """
    if doc_type not in brain_loader.DOKUMENTTYPEN:
        raise ValueError(f"unknown document type: {doc_type!r}")
    from ..pipeline.prompts import DICTATION_CLOSE, DICTATION_OPEN

    types = tuple(doc_types or (doc_type,))
    hits = list(templates or [])

    kern = _kern_rules()
    regelwerk = brain_loader.rule_lines()
    anti = brain_loader.anti_pattern_lines()
    playbook = brain_loader.dokumenttyp_text(doc_type)

    system_parts = [
        "Sie sind der Schreibassistent von Briefato für deutschsprachige Arztpraxen. "
        "Sie arbeiten nach der dokumentierten Methode des Schreibdienstes und formulieren "
        "ausschließlich um — Sie recherchieren nicht und erfinden nichts.",
        "KERN-METHODE (verbindlich):\n" + "\n".join(f"- {line}" for line in kern),
        "REGELWERK (R1–R67, jede Regel ist verbindlich):\n" + "\n".join(regelwerk),
        "ANTI-PATTERNS (generisches LLM-Verhalten — verboten):\n" + "\n".join(anti),
        f"PLAYBOOK DOKUMENTTYP „{doc_type}“:\n{playbook}",
        _output_mandate(doc_type),
        _pseudonym_contract(),
        f"Prompt-Version: {PROMPT_VERSION} | Sprache: {language} | Dokumenttyp: {doc_type}",
    ]
    system = "\n\n".join(system_parts)

    sender = _render_pairs(dict(letterhead or {}), LETTERHEAD_LABELS) or "- (keine Angaben)"
    patient = _render_pairs(dict(patient_ctx or {}), {k: k for k in (patient_ctx or {})}) or "- (keine Angaben)"
    custom = (custom_rules or "").strip() or "—"
    extra_text = (extra or "").strip() or "—"
    concurrency = (
        "Erzeugen Sie die Fassungen getrennt, ohne Überschrift, getrennt durch genau eine Leerzeile."
        if len(types) > 1
        else ""
    )

    user = (
        f"Dokumenttyp: {brain_loader.DOKUMENTTYP_LABELS.get(doc_type, doc_type)} ({doc_type})\n"
        f"Sprache: {language}\n"
        "Hinweis: Alle Platzhalter in doppelten geschweiften Klammern sind patientenbezogene Daten "
        "und unverändert zu übernehmen.\n\n"
        "PRAXIS / ABSENDER (Briefkopf — nicht verändern, nicht erfinden):\n"
        f"{sender}\n\n"
        "PATIENTENBEZUG (dient nur der Zuordnung):\n"
        f"{patient}\n\n"
        "MUSTERBRIEF-STRUKTUR (nur Sektionen als Referenz):\n"
        f"{_structure_reference(hits)}\n\n"
        "PRAXISREGELN DES MITGLIEDS (verbindlich, sofern vorhanden):\n"
        f"{custom}\n\n"
        f"{('BEIDE FASSUNGEN — ' + concurrency + chr(10)) if concurrency else ''}"
        "DIKTAT (einzige inhaltliche Quelle):\n"
        f"{DICTATION_OPEN}\n{dictation or ''}\n{DICTATION_CLOSE}\n\n"
        "ZUSATZHINWEISE:\n"
        f"{extra_text}\n\n"
        f"Erzeugen Sie jetzt ausschließlich den fertigen Text „{doc_type}“."
    )

    return PromptBundle(
        system=system,
        user=user,
        doc_type=doc_type,
        doc_types=types,
        template_files=[hit.file for hit in hits],
        reference_only_files=[hit.file for hit in hits if hit.reference_only],
        kern_rules=len(kern),
        regelwerk_rules=len(regelwerk),
    )


def correction_block(correction_instructions: list[str]) -> str:
    """Build the retry 'KORREKTURHINWEISE' text appended after a failed check."""
    if not correction_instructions:
        return ""
    lines = "\n".join(f"- {item}" for item in correction_instructions)
    return (
        "KORREKTURHINWEISE — der vorige Entwurf verletzte verbindliche Regeln. "
        "Beheben Sie genau diese Punkte, ohne neue Inhalte zu erfinden:\n" + lines
    )


__all__ = [
    "DISCHARGE_BLOCK_ORDER",
    "LETTERHEAD_LABELS",
    "PROMPT_VERSION",
    "PromptBundle",
    "build_prompt",
    "correction_block",
]
