"""German prompt engineering for the Briefato letter pipeline.

OWNER: WORKSTREAM-PIPELINE. Frozen API (docs/02-spec-interfaces.md §6)::

    def system_prompt(kind: str, language: str = "de") -> str
    def user_prompt(kind: str, dictation: str, patient_ctx: dict,
                    letterhead: dict, extra: str = "") -> str

Prompt design is researched and cited in ``README.md`` (Arztbrief/Attest structure,
DIN 5008, and hallucination-reduction practice). The rules encoded here:

* Output German, formal register ("Sehr geehrte …").
* Correct per-kind structure (Arztbrief / Attest / Befund / Überweisung / sonstiges).
* Only restructure the supplied dictation — never invent clinical facts, dates,
  dosages, medications or diagnoses.
* Keep ``{{TOKENS}}`` verbatim.
* No markdown, no commentary, no disclaimer text inside the letter, plain paragraphs.

``PROMPT_VERSION`` is bumped whenever the wording changes.
"""

from __future__ import annotations

PROMPT_VERSION = "de-1"

KIND_LABELS: dict[str, str] = {
    # legacy frozen kinds (kept for the portal dropdown / DOCX export)
    "arztbrief": "Arztbrief",
    "attest": "Attest",
    "befund": "Befund",
    "ueberweisung": "Überweisung",
    "sonstiges": "Schreiben",
    # real document types from the brain (brain/dokumenttypen/*)
    "zusammenfassung": "Zusammenfassung",
    "operationsbericht": "OP-Bericht",
    "ambulant": "Ambulanter Brief",
    "entlassbrief": "Entlassbrief",
    "pflegebericht": "Pflegebericht-Integration",
    "entlassmedikationsplan": "Entlassmedikationsplan",
    "ablehnungsbogen": "Ablehnungsbogen",
    "weiterbildung-kv-nachweise": "Weiterbildungs-/KV-Nachweis",
}

# Canonical section order per document type (see README.md sources).
KIND_STRUCTURE: dict[str, tuple[str, ...]] = {
    "arztbrief": ("Anrede", "Betreff", "Anamnese", "Befund", "Diagnose", "Therapie/Procedere", "Grußformel", "Unterschrift"),
    "attest": ("Zweck", "Befund", "Beurteilung", "Grußformel", "Unterschrift"),
    "befund": ("Fragestellung", "Methode", "Befund", "Beurteilung", "Grußformel", "Unterschrift"),
    "ueberweisung": ("Fragestellung", "bisherige Befunde", "Auftrag", "Grußformel", "Unterschrift"),
    "sonstiges": ("Anrede", "Betreff", "Inhalt", "Grußformel", "Unterschrift"),
}

PATIENT_LABELS: dict[str, str] = {
    "last_name": "Nachname",
    "first_name": "Vorname",
    "birth_date": "Geburtsdatum",
    "sex": "Geschlecht",
    "insurance": "Kostenträger",
    "insurance_number": "Versicherungsnummer",
    "street": "Straße",
    "zip": "PLZ",
    "city": "Ort",
    "phone": "Telefon",
    "email": "E-Mail",
}

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

# The dictation is wrapped in this marker so the mock provider (and any test spy)
# can locate the raw clinical input unambiguously.
DICTATION_OPEN = "<diktat>"
DICTATION_CLOSE = "</diktat>"


def _sections(kind: str) -> str:
    return " → ".join(KIND_STRUCTURE.get(kind, KIND_STRUCTURE["sonstiges"]))


def system_prompt(kind: str, language: str = "de") -> str:
    """Return the system instruction for a letter of ``kind`` (German output)."""
    label = KIND_LABELS.get(kind, KIND_LABELS["sonstiges"])
    sections = _sections(kind)
    return (
        "Sie sind der Schreibassistent von Briefato für deutschsprachige Arztpraxen.\n"
        f"Aufgabe: Formulieren Sie aus dem gelieferten Diktat (Stichpunkte oder Fließtext) genau ein "
        f"fertiges Dokument vom Typ „{label}“. Sie strukturieren und formulieren um – Sie recherchieren "
        "nicht und fügen nichts hinzu.\n\n"
        "Verbindliche Regeln:\n"
        "1. Sprache und Register: ausschließlich Deutsch, formell und sachlich, in der dritten Person "
        "bzw. mit formeller Anrede („Sehr geehrte Damen und Herren,“ / „Sehr geehrte Frau …,“ / "
        "„Sehr geehrter Herr …,“). Keine Umgangssprache, keine Floskeln, keine Werbung.\n"
        f"2. Aufbau für „{label}“ in dieser Reihenfolge: {sections}. Lassen Sie einen Abschnitt weg, "
        "wenn das Diktat dazu keine Angaben enthält.\n"
        "3. Keine Erfindungen: Übernehmen Sie ausschließlich Informationen, Zahlen, Daten, Dosierungen, "
        "Medikamente, Diagnosen und Befunde, die im Diktat ausdrücklich stehen. Ergänzen Sie keine "
        "Diagnosen, keine ICD-Codes, keine Laborwerte, keine Datumsangaben und keine Medikamente. "
        "Fehlt eine Angabe, lassen Sie sie weg – erfinden Sie sie nicht.\n"
        "4. Pseudonyme Platzhalter wie {{LAST_NAME}}, {{FIRST_NAME}}, {{BIRTH_DATE}}, "
        "{{INSURANCE_NUMBER}}, {{STREET}}, {{ZIP}}, {{CITY}}, {{PHONE}}, {{EMAIL}} sind unverändert und "
        "exakt (Großschreibung, doppelte geschweifte Klammern) im Text zu belassen. Sie dürfen nicht "
        "erklärt, ausgeschrieben, übersetzt oder verändert werden.\n"
        "5. Ausgabeformat: reiner Text. Absätze werden durch genau eine Leerzeile getrennt. Kein "
        "Markdown (keine *, #, ----, Backticks, keine Aufzählungszeichen mit Formatierung), keine "
        "Tabellen, keine ausgezeichneten Überschriften.\n"
        "6. Keine Kommentare, keine Einleitungs- oder Schlusssätze außerhalb des Briefes, kein Hinweis "
        "„KI-generiert“, kein Haftungsausschluss, keine Anrede an die lesende Person des Prompts.\n"
        "7. Keine Rückfragen, keine Alternativen, kein Vorwort. Geben Sie ausschließlich das fertige "
        "Dokument aus.\n"
        "8. Unterschrift: Nennen Sie Name und Fachbezeichnung nur, wenn sie im Diktat oder in den "
        "Praxisdaten stehen; andernfalls bleibt die Unterschriftszeile leer.\n"
        "9. Kurz und präzise, ohne Wiederholungen und ohne Selbstverständlichkeiten; Vollständigkeit "
        "und klare Gliederung gehen der Kürze vor.\n\n"
        f"Prompt-Version: {PROMPT_VERSION}\n"
        f"Ausgabesprache: {language}\n"
    )


def _render_pairs(data: dict, labels: dict[str, str]) -> str:
    lines: list[str] = []
    for key, label in labels.items():
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            lines.append(f"- {label}: {text}")
    return "\n".join(lines)


def user_prompt(
    kind: str,
    dictation: str,
    patient_ctx: dict,
    letterhead: dict,
    extra: str = "",
) -> str:
    """Return the user instruction containing sender, (masked) patient context and dictation."""
    label = KIND_LABELS.get(kind, KIND_LABELS["sonstiges"])
    sender = _render_pairs(dict(letterhead or {}), LETTERHEAD_LABELS) or "- (keine Angaben)"
    patient = _render_pairs(dict(patient_ctx or {}), PATIENT_LABELS) or "- (keine Angaben)"
    extra_text = (extra or "").strip() or "—"

    return (
        f"Dokumenttyp: {label} ({kind})\n"
        "Sprache: de\n"
        "Hinweis: Alle Platzhalter in doppelten geschweiften Klammern sind patientenbezogene Daten. "
        "Sie sind unverändert zu übernehmen.\n\n"
        "PRAXIS / ABSENDER (Briefkopf – nicht verändern, nicht erfinden):\n"
        f"{sender}\n\n"
        "PATIENTENBEZUG (dient nur der korrekten Zuordnung):\n"
        f"{patient}\n\n"
        "DIKTAT (einzige inhaltliche Quelle):\n"
        f"{DICTATION_OPEN}\n{dictation or ''}\n{DICTATION_CLOSE}\n\n"
        "ZUSATZHINWEISE:\n"
        f"{extra_text}\n\n"
        f"Erzeugen Sie jetzt ausschließlich den fertigen Brieftext „{label}“."
    )


__all__ = [
    "PROMPT_VERSION",
    "KIND_LABELS",
    "KIND_STRUCTURE",
    "PATIENT_LABELS",
    "LETTERHEAD_LABELS",
    "DICTATION_OPEN",
    "DICTATION_CLOSE",
    "system_prompt",
    "user_prompt",
]
