"""Document-type triage — Auftragsart -> Dokumenttyp (kern.md section 2).

OWNER: WORKSTREAM-BRAIN-WIRING.

Triage runs *before* any generated text. The routing table is transcribed from
``brain/kern.md`` (K2.1-K2.4) and ``brain/dokumenttypen/*.md`` triggers:

| signal in the order                                         | document type             |
|-------------------------------------------------------------|---------------------------|
| raw material / no order                                     | arztbrief (stationär)     |
| "Zusammenfassung"                                           | zusammenfassung           |
| "OP-Bericht"                                                | operationsbericht         |
| ambulant / tageschirurgisch / NFA without stationäre Aufnahme| ambulant                 |
| pflegeberichte as source material                           | pflegebericht             |
| "Medikationsplan" / "MoP"                                   | entlassmedikationsplan    |
| "OP-Bericht + Zusammenfassung"                              | BOTH documents            |
| Ablehnungsbogen / WBO, KV, Logbuch, QS                      | ablehnungsbogen / weiterbildung-kv-nachweise |

The returned :class:`TriageDecision` carries the type(s), a confidence and a
human-readable reason (shown in the UI / audit). ``doc_type_options()`` exposes the
type list for the portal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import brain_loader

# Output types (what triage may return). ``entlassbrief`` is a routing playbook, not
# an output type: it resolves to arztbrief or ambulant.
DOC_TYPES: tuple[str, ...] = (
    "arztbrief",
    "zusammenfassung",
    "operationsbericht",
    "ambulant",
    "pflegebericht",
    "entlassmedikationsplan",
    "ablehnungsbogen",
    "weiterbildung-kv-nachweise",
)

DOC_TYPE_LABELS = brain_loader.DOKUMENTTYP_LABELS

# Legacy ``letters.kind`` values the frozen portal still submits. Only ``arztbrief``
# is an unambiguous hint; the rest carry no brain playbook and fall through to the
# dictation-based routing.
LEGACY_KINDS: dict[str, str | None] = {
    "arztbrief": "arztbrief",
    "attest": None,
    "befund": None,
    "ueberweisung": None,
    "sonstiges": None,
}


@dataclass(frozen=True)
class TriageDecision:
    doc_type: str
    doc_types: tuple[str, ...]
    confidence: float
    reason: str
    signals: tuple[str, ...] = field(default_factory=tuple)

    @property
    def combined(self) -> bool:
        return len(self.doc_types) > 1

    def as_dict(self) -> dict[str, object]:
        return {
            "doc_type": self.doc_type,
            "doc_types": list(self.doc_types),
            "label": DOC_TYPE_LABELS.get(self.doc_type, self.doc_type),
            "confidence": self.confidence,
            "reason": self.reason,
            "signals": list(self.signals),
            "combined": self.combined,
        }


def doc_type_options() -> list[dict[str, str]]:
    """The type list for the UI: ``[{"value": ..., "label": ...}, ...]``."""
    return [{"value": key, "label": DOC_TYPE_LABELS.get(key, key)} for key in DOC_TYPES]


def _find(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text)]


# Trigger patterns (case-insensitive against a pre-lowercased, umlaut-normalised text).
_ZUSAMMENFASSUNG = (r"\bzusammenfassung\b", r"\bzusammenfassen\b", r"nur die zusammenfass")
_OP = (r"\bop[-\s]?bericht\b", r"\boperationsbericht\b")
_MEDIKATION = (r"medikationsplan", r"\bmop\b", r"verabreichungsplan", r"entlassmedikation", r"mediks\s*plan")
_ABLEHNUNG = (r"ablehnungsbogen", r"thieme\s*compliance", r"aufkl[äa]rungsbogen")
_WEITERBILDUNG = (r"\bwbo\b", r"weiterbildung", r"kv[-\s]?genehmigung", r"logbuch", r"\bqs\b", r"nachweis")
_PFLEGE = (r"pflegebericht", r"pflegedokumentation", r"pflegeberichte", r"pflegerische dokumentation")
_AMBULANT = (
    r"\bambulant\w*\b.*(brief|fall|vorstellung|eingriff)",
    r"\btageschirurgisch\w*\b",
    r"ohne station[äa]re aufnahme",
    r"keine station[äa]re aufnahme",
    r"nicht station[äa]r",
    r"\bnfa\b.*(vorstellung|vorstellen)",
    r"(entlassung|entlassen).*am op[-\s]?tag",
    r"noch am op[-\s]?tag",
)
_ENTLASSBRIEF = (r"entlassbrief", r"entlassungsbrief", r"\barztbrief\b", r"verlegungsbericht", r"aufnahmebrief")
_STATIONAER = (r"station[äa]r", r"übernacht", r"\bübernachtung\b", r"mehrt[äa]gig", r"tagesklinik")
_AMBULANT_CONTEXT = (r"\btageschirurgisch", r"ohne station[äa]re", r"keine station[äa]re", r"\bnfa\b", r"noch am op[-\s]?tag")


def _dictation_route(text: str) -> tuple[tuple[str, ...], float, str, tuple[str, ...]]:
    """Pure routing on the dictation text; returns (types, confidence, reason, signals)."""
    op = _find(text, _OP)
    zus = _find(text, _ZUSAMMENFASSUNG)
    medik = _find(text, _MEDIKATION)
    ablehn = _find(text, _ABLEHNUNG)
    wb = _find(text, _WEITERBILDUNG)
    pflege = _find(text, _PFLEGE)
    amb = _find(text, _AMBULANT)
    entlass = _find(text, _ENTLASSBRIEF)
    stat = _find(text, _STATIONAER)

    # 0) combined order: two formats in ONE order -> both documents
    if op and zus:
        return (
            ("operationsbericht", "zusammenfassung"),
            0.9,
            "Kombinierter Auftrag: „OP-Bericht + Zusammenfassung“ → beide Fassungen",
            ("op-bericht", "zusammenfassung"),
        )

    # 1) Medikationsplan (MoP) — highest specificity among single orders
    if medik:
        return ("entlassmedikationsplan",), 0.85, "Auftrag „Medikationsplan/MoP“", tuple(medik)

    # 2) Ablehnungsbogen
    if ablehn:
        return ("ablehnungsbogen",), 0.8, "Auftrag „Ablehnungsbogen“", tuple(ablehn)

    # 3) Weiterbildungs-/KV-Nachweise
    if wb:
        return ("weiterbildung-kv-nachweise",), 0.75, "Auftrag Weiterbildung/KV-Nachweis", tuple(wb)

    # 4) Zusammenfassung (Vorrang vor der Diagnoselisten-Regel)
    if zus:
        return ("zusammenfassung",), 0.85, "Auftrag „Zusammenfassung“", tuple(zus)

    # 5) OP-Bericht
    if op:
        return ("operationsbericht",), 0.85, "Auftrag „OP-Bericht“", tuple(op)

    # 6) Pflegeberichte als Quellmaterial
    if pflege:
        return ("pflegebericht",), 0.7, "Pflegeberichte als Quellmaterial", tuple(pflege)

    # 7) Ambulant (keine stationäre Aufnahme)
    if amb:
        return ("ambulant",), 0.8, "Ambulanter/tageschirurgischer Fall ohne stationäre Aufnahme", tuple(amb)

    # 8) Entlassbrief/Arztbrief genannt, Briefart unklar -> Triage
    if entlass:
        if _find(text, _AMBULANT_CONTEXT):
            return ("ambulant",), 0.6, "„Entlassbrief“, aber Verlauf ambulanter Anhalt (keine Übernachtung)", tuple(entlass)
        return ("arztbrief",), 0.7, "Entlassbrief/Arztbrief, stationärer Verlauf", tuple(entlass)

    # 9) Default: stationärer Arztbrief (Rohmaterial ohne Auftrag)
    if stat:
        return ("arztbrief",), 0.5, "Stationärer Verlauf → Arztbrief (Default)", tuple(stat)
    return ("arztbrief",), 0.4, "Rohmaterial ohne speziellen Auftrag → stationärer Arztbrief (Default)", ()


def triage(dictation: str, explicit: str | None = None) -> TriageDecision:
    """Decide the document type for ``dictation``.

    ``explicit`` is the type/kinds hint the caller supplies (the frozen portal passes
    one of ``letters.kind``). A real brain type is honoured unless the dictation asks
    for a *combination*; a generic legacy kind (attest/befund/…) falls back to the
    dictation routing.
    """
    text = (dictation or "").lower()

    routed_types, routed_conf, routed_reason, routed_signals = _dictation_route(text)

    explicit_clean = (explicit or "").strip().lower()

    # A combined dictation always wins (R59: deliver both, never choose).
    if len(routed_types) > 1:
        return TriageDecision(
            doc_type=routed_types[0],
            doc_types=routed_types,
            confidence=max(routed_conf, 0.9),
            reason=routed_reason,
            signals=routed_signals,
        )

    if explicit_clean in DOC_TYPES:
        # Respect an explicit real type — but the default type (arztbrief) yields to a
        # stronger dictation-specific order, and an explicit "zusammenfassung" keeps
        # its documented precedence.
        if explicit_clean == "arztbrief":
            return TriageDecision(
                doc_type=routed_types[0],
                doc_types=routed_types,
                confidence=max(routed_conf, 0.6),
                reason=f"Briefart arztbrief + Diktat: {routed_reason}"
                if routed_types[0] != "arztbrief"
                else "Stationärer Arztbrief (explizit/Default)",
                signals=routed_signals,
            )
        return TriageDecision(
            doc_type=explicit_clean,
            doc_types=(explicit_clean,),
            confidence=0.9,
            reason=f"Explizit gewählter Dokumenttyp „{DOC_TYPE_LABELS.get(explicit_clean, explicit_clean)}“",
            signals=(explicit_clean,),
        )

    if explicit_clean in LEGACY_KINDS:
        return TriageDecision(
            doc_type=routed_types[0],
            doc_types=routed_types,
            confidence=routed_conf,
            reason=f"Alt-Typ „{explicit_clean}“ ohne Brain-Playbook; Routing per Diktat: {routed_reason}",
            signals=routed_signals,
        )

    return TriageDecision(
        doc_type=routed_types[0],
        doc_types=routed_types,
        confidence=routed_conf,
        reason=routed_reason,
        signals=routed_signals,
    )


__all__ = [
    "DOC_TYPES",
    "DOC_TYPE_LABELS",
    "LEGACY_KINDS",
    "TriageDecision",
    "doc_type_options",
    "triage",
]
