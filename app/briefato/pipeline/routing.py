"""Routing — the >5-source fan-out rule (kern routing table + decision 2026-10-02).

OWNER: WORKSTREAM-ENGINE-V2.

Mohamed's decision (2026-10-02, authoritative): a **stationary** letter (Entlass-,
Aufnahme- or Verlegungsbrief) for which the member submits **more than five** source
documents is always processed as a fan-out — every source is summarised on its own and
the whole thing is then rewritten (weave) into the final document. Everything else, and
any stationary letter with five or fewer sources, stays on the existing single-pass
pipeline.

The decision is emitted into the audit trail and attached to the letter's runtime detail
so the UI can render it (``Route: Fan-out (14 Quellen)``).

The threshold is configurable through ``BRIEFATO_FANOUT_THRESHOLD`` (default ``5``);
per the rule the comparison is strictly *greater than* the threshold.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

FANOUT = "fan-out"
SINGLE_PASS = "single-pass"

#: Document types that constitute a "stationary letter". ``arztbrief`` is what triage
#: returns for an Entlass-/Aufnahme-/Verlegungsbrief (see brain/dokumenttypen/
#: entlassbrief.md), so it is the fan-out candidate. Standalone reports
#: (OP-Bericht, Zusammenfassung, ambulant, …) never fan out.
STATIONARY_DOC_TYPES: frozenset[str] = frozenset({"arztbrief"})

#: Optional explicit brief-art hints (the portal may pass one through ``kind``).
STATIONARY_BRIEFART_HINTS: frozenset[str] = frozenset(
    {"entlassbrief", "entlassungsbrief", "aufnahmebrief", "verlegungsbrief", "verlegung", "arztbrief"}
)

DEFAULT_THRESHOLD = 5


def fanout_threshold() -> int:
    """Configured source-count threshold (strictly greater-than comparison)."""
    raw = os.environ.get("BRIEFATO_FANOUT_THRESHOLD", "").strip()
    if not raw:
        return DEFAULT_THRESHOLD
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_THRESHOLD
    return value if value >= 0 else DEFAULT_THRESHOLD


@dataclass(frozen=True)
class RouteDecision:
    """The routing verdict for one document type + source count."""

    route: str
    reason: str
    source_count: int
    threshold: int
    doc_type: str

    @property
    def is_fanout(self) -> bool:
        return self.route == FANOUT

    @property
    def ui_label(self) -> str:
        if self.is_fanout:
            return f"Route: Fan-out ({self.source_count} Quellen)"
        return f"Route: Single-Pass ({self.source_count} Quellen)"

    def as_dict(self) -> dict[str, object]:
        return {
            "route": self.route,
            "reason": self.reason,
            "source_count": self.source_count,
            "threshold": self.threshold,
            "doc_type": self.doc_type,
            "ui_label": self.ui_label,
        }


def is_stationary(doc_type: str, briefart: str | None = None) -> bool:
    """True when ``doc_type`` (or an explicit brief-art hint) is a stationary letter."""
    if (doc_type or "").strip().lower() in STATIONARY_DOC_TYPES:
        return True
    return (briefart or "").strip().lower() in STATIONARY_BRIEFART_HINTS


def decide_route(
    doc_type: str,
    source_count: int,
    *,
    briefart: str | None = None,
    threshold: int | None = None,
) -> RouteDecision:
    """Emit the fan-out vs single-pass decision for one document type."""
    limit = fanout_threshold() if threshold is None else int(threshold)
    count = max(0, int(source_count))
    stationary = is_stationary(doc_type, briefart)
    if stationary and count > limit:
        reason = (
            f"Stationärer Brief mit {count} Quellen (> {limit}) → Fan-out: "
            "Quellen segmentieren, je Segment verdichten, Per-Segment-Kompression "
            f"(max. 3 parallel), anschließend ein Weave zum {doc_type}."
        )
        return RouteDecision(FANOUT, reason, count, limit, doc_type)
    if stationary:
        reason = (
            f"Stationärer Brief mit {count} Quellen (≤ {limit}) → Single-Pass "
            "(kern-Regel: Fan-out erst oberhalb der Quellenschwelle)."
        )
    else:
        reason = (
            f"Dokumenttyp „{doc_type}“ ist kein stationärer Entlass-/Aufnahme-/"
            "Verlegungsbrief → Single-Pass."
        )
    return RouteDecision(SINGLE_PASS, reason, count, limit, doc_type)


__all__ = [
    "DEFAULT_THRESHOLD",
    "FANOUT",
    "SINGLE_PASS",
    "STATIONARY_BRIEFART_HINTS",
    "STATIONARY_DOC_TYPES",
    "RouteDecision",
    "decide_route",
    "fanout_threshold",
    "is_stationary",
]
