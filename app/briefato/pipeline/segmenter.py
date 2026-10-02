"""Source segmenter — split a KIS-style multi-source input into labelled segments.

OWNER: WORKSTREAM-ENGINE-V2.

Mohamed submits a *stack* of different source documents (Aufnahme-Anamnese/KU, imaging,
endoscopy, OP-Bericht, Pathologie, Pflege, Visiten, Labor, Konsile …) and the method
requires each one to be summarised **separately** before the whole thing is rewritten
into the final document (kern K0.2 "distilled insights" + the fan-out decision of
2026-10-02). This module performs the first stage of that fan-out: it finds the source
boundaries in real, noisy KIS export text.

Robustness requirements (tested in ``app/tests/test_fanout.py``):

* **German heading patterns** — a closed vocabulary of ~20 source types with umlaut- and
  transliteration-tolerant regexes.
* **Form-label noise** — lines such as ``Seite 3/7``, ``Pat.-Nr: …``, ``KIS-Export`` or
  a bare ``Befund:`` never start a segment; any payload after them is kept in the
  running segment.
* **Duplicate labels** — two directly adjacent blocks of the same type are merged into
  one segment (``Visite`` … ``Visite``); non-adjacent repeats stay separate sources.
* **Missing labels** — if no heading is recognised at all the whole input becomes one
  ``rohtext`` segment with confidence ``0.0`` (never a silent empty result).

A segment carries its ``segment_type``, the ``text``, the matched ``heading`` and a
``confidence`` in ``[0, 1]`` (higher = the boundary was recognised more explicitly).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

# The source vocabulary. The 16 types named by the method come first; the trailing
# entries cover the blocks of a final discharge letter that also arrive as "sources"
# in a KIS export (Diagnosen/Therapieempfehlung) plus the fallback bucket.
SEGMENT_TYPES: tuple[str, ...] = (
    "anamnese_ku",
    "roentgen",
    "ct",
    "mrt",
    "sono",
    "echo",
    "oegd",
    "kolo",
    "endosonographie",
    "op_bericht",
    "pathologie",
    "diabetologie",
    "pflegeberichte",
    "visiten",
    "labor",
    "konsile",
    "diagnosen",
    "therapie_empfehlung",
    "rohtext",
)

#: Human labels for the UI / the demo output.
SEGMENT_LABELS: dict[str, str] = {
    "anamnese_ku": "Anamnese/KU",
    "roentgen": "Röntgen",
    "ct": "CT",
    "mrt": "MRT",
    "sono": "Sonographie",
    "echo": "Echokardiographie",
    "oegd": "ÖGD",
    "kolo": "Koloskopie",
    "endosonographie": "Endosonographie",
    "op_bericht": "OP-Bericht",
    "pathologie": "Pathologie",
    "diabetologie": "Diabetologie",
    "pflegeberichte": "Pflegeberichte",
    "visiten": "Visiten",
    "labor": "Labor",
    "konsile": "Konsile",
    "diagnosen": "Diagnosen",
    "therapie_empfehlung": "Therapieempfehlungen",
    "rohtext": "Rohtext",
}

# Heading vocabulary, **order matters**: the more specific pattern wins (Endosonographie
# before Sonographie, Echo before Endosonographie's "sono" substring, …).
_HEADINGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "anamnese_ku",
        (
            r"^anamnese",
            r"^aufnahme[- ]?anamnese",
            r"^vorgeschichte",
            r"^ku\b",
            r"^k(?:oe|ö)rperliche untersuchung",
            r"^klinische untersuchung",
            r"^aufnahmebefund",
            r"^aufnahme[- ]?ku",
            r"^untersuchungsbefund",
        ),
    ),
    ("ct", (r"^ct\b", r"^cct\b", r"^computertomograph", r"^ct[- ]")),
    ("mrt", (r"^mrt\b", r"^mri\b", r"^magnetresonanz", r"^mr[- ]")),
    ("endosonographie", (r"^endosono", r"^eus\b")),
    ("echo", (r"^echokardiograph", r"^echo\b", r"^herzecho", r"^tte\b", r"^tee\b", r"^transthorakal")),
    ("oegd", (
        r"^(?:oe|ö)gd\b",
        r"^gastroskop",
        r"^(?:oe|ö)sophagogastroduodenoskop",
        r"^magenspiegel",
    )),
    ("kolo", (r"^kolo", r"^coloskop", r"^darmspiegel", r"^ileokoloskop", r"^rektosigmo")),
    ("sono", (
        r"^sonograph",
        r"^sonograf\b",
        r"^sono\b",
        r"^sono[- ]",
        r"^ultraschall",
        r"^abdomensonograph",
    )),
    ("roentgen", (r"^(?:roe|rö)ntgen", r"^x[- ]?ray", r"^thoraxaufnahme", r"^thorax\b")),
    (
        "op_bericht",
        (
            r"^op[- ]?bericht",
            r"^operationsbericht",
            r"^op[- ]?protokoll",
            r"^op\b",
            r"^operation\b",
            r"^eingriff\b",
        ),
    ),
    ("pathologie", (
        r"^patholog",
        r"^histolog",
        r"^patho[- ]?befund",
        r"^feingewebe",
        r"^biops",
        r"^pe[- ]?histolog",
        r"^pr(?:ae|ä)parat",
    )),
    ("diabetologie", (r"^diabetolog", r"^diabetes", r"^blutzucker", r"^bz[- ]?kontrolle", r"^hba1c")),
    ("pflegeberichte", (r"^pflegebericht", r"^pflegedokument", r"^pflegerische dokumentation", r"^pflege\b")),
    ("visiten", (r"^visite", r"^stationsvisite", r"^kurvenvisite", r"^stationsverlauf", r"^verlauf\b")),
    ("labor", (r"^labor", r"^blutwerte", r"^laborwerte", r"^laborbefund", r"^laborkontrolle")),
    ("konsile", (r"^konsil", r"^konsiliar", r"^mitbeurteilung", r"^fachkonsil")),
    ("diagnosen", (r"^diagnosen", r"^diagnose\b", r"^hauptdiagnose", r"^nebendiagnosen")),
    (
        "therapie_empfehlung",
        (
            r"^ambulante therapieempfehl",
            r"^therapieempfehl",
            r"^empfehlung",
            r"^nachsorge",
            r"^procedere",
        ),
    ),
)

# Form fields that appear in KIS exports and must never be read as a source heading.
_FORM_LABELS: frozenset[str] = frozenset(
    {
        "befund",
        "frage",
        "antwort",
        "seite",
        "druckdatum",
        "pat-nr",
        "patnr",
        "fall-nr",
        "fallnr",
        "kis-export",
        "kisexport",
        "aufgenommen",
        "entlassen",
        "station",
        "zimmer",
        "arzt",
        "aerztin",
        "erstellt",
        "gedruckt",
        "ausdruck",
        "bericht",
        "formular",
    }
)

# Pure-noise lines dropped without any payload.
_NOISE_LINES_RE = re.compile(
    r"^\s*(?:"
    r"-{3,}"
    r"|={3,}"
    r"|seite\s+\d+(?:\s*/\s*\d+)?"
    r"|\d+\s*/\s*\d+"
    r"|kis[- ]?export\b.*"
    r"|druckdatum\b.*"
    r"|(?:pat|fall)[- ]?nr\.?\s*:.*"
    r")\s*$",
    re.IGNORECASE,
)

_UMLAUT_FOLD = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"))
_LABEL_RE = re.compile(r"^\s*([^:]{2,60}?)\s*:\s*(.*)$")
# "Visite am 12.09.2026" / "Visite 12.09." style headings keep the date as heading tail.
_HEADING_TAIL_RE = re.compile(r"^(.*?)\s*(?:am\s+\d{1,2}\.\d{1,2}\.?\d{0,4}|\d{1,2}\.\d{1,2}\.?\d{0,4})$")

_MAX_HEADING_LEN = 70


def _fold(text: str) -> str:
    text = (text or "").lower()
    for source, target in _UMLAUT_FOLD:
        text = text.replace(source, target)
    return " ".join(text.split())


def _match_heading(label: str) -> str | None:
    """Return the segment type for a (folded) heading label, or ``None``."""
    folded = _fold(label).strip(" .-:")
    if not folded:
        return None
    if folded in _FORM_LABELS:
        return None
    for segment_type, patterns in _HEADINGS:
        for pattern in patterns:
            if re.search(pattern, folded):
                return segment_type
    return None


@dataclass(frozen=True)
class Segment:
    """One recognised source document (or the 'rohtext' fallback)."""

    segment_type: str
    text: str
    confidence: float
    heading: str = ""
    index: int = 0
    duplicate_of: int | None = None

    @property
    def label(self) -> str:
        return SEGMENT_LABELS.get(self.segment_type, self.segment_type)

    @property
    def chars(self) -> int:
        return len(self.text or "")

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "type": self.segment_type,
            "label": self.label,
            "heading": self.heading,
            "confidence": round(self.confidence, 3),
            "chars": self.chars,
            "duplicate_of": self.duplicate_of,
        }


# Pure form-noise labels: a line starting with one of these is dropped entirely (it is a
# KIS form field, never a source section). Clinical labels such as "Befund:" are NOT here
# (their payload is kept).
_NOISE_LABELS: frozenset[str] = frozenset(
    {
        "seite",
        "druckdatum",
        "patnr",
        "fallnr",
        "kisexport",
        "erstellt",
        "gedruckt",
        "ausdruck",
        "zimmer",
        "station",
        "arzt",
        "aerztin",
        "formular",
        "aufgenommen",
        "entlassen",
    }
)


def _noise_key(label: str) -> str:
    """Normalise a label for the noise set (drop dots/dashes/spaces): 'Pat.-Nr' -> 'patnr'."""
    return re.sub(r"[^a-z0-9]", "", _fold(label))


def _is_noise_line(line: str) -> bool:
    """True for a KIS form field / separator line that must never start a segment."""
    stripped = (line or "").strip()
    if not stripped:
        return False
    if _NOISE_LINES_RE.match(stripped):
        return True
    match = _LABEL_RE.match(stripped)
    if match and _noise_key(match.group(1)) in _NOISE_LABELS:
        return True
    return False


def _detect_heading(line: str) -> tuple[str, str, str, float] | None:
    """Classify a line as a heading.

    Returns ``(segment_type, heading_text, rest_text, confidence)`` or ``None``.
    ``rest_text`` is the payload that stood on the same line after the colon.
    """
    stripped = line.strip()
    if not stripped or _NOISE_LINES_RE.match(stripped):
        return None

    match = _LABEL_RE.match(stripped)
    if match:
        label, rest = match.group(1).strip(), match.group(2).strip()
        segment_type = _match_heading(label)
        if segment_type is not None:
            confidence = 0.95 if rest else 0.8
            return segment_type, label, rest, confidence
        # A form label with payload: keep the payload, do not start a segment.
        if _fold(label).strip(" .-:") in _FORM_LABELS:
            return None
        return None

    # Standalone heading line without a colon ("Sonographie Abdomen").
    if len(stripped) <= _MAX_HEADING_LEN and not stripped.endswith((".", "!", "?")):
        candidate = stripped
        tail = _HEADING_TAIL_RE.match(candidate)
        if tail and tail.group(1).strip():
            candidate = tail.group(1).strip()
        # Reject diagnosis-like standalone lines: a bare list entry such as
        # "Diabetes mellitus Typ 2" must not be split off as its own source.
        if re.search(r"\d", candidate) or len(candidate.split()) > 4:
            return None
        segment_type = _match_heading(candidate)
        if segment_type is not None:
            return segment_type, candidate, "", 0.6
    return None


def segment(text: str) -> list[Segment]:
    """Split ``text`` into ordered :class:`Segment` objects.

    The result is never empty: a text without any recognised heading yields exactly one
    ``rohtext`` segment with confidence ``0.0``.
    """
    raw = text or ""
    lines = raw.splitlines()

    chunks: list[tuple[str, str, list[str], float]] = []  # (type, heading, body, conf)
    current_type: str | None = None
    current_heading = ""
    current_body: list[str] = []
    current_conf = 0.0
    leading: list[str] = []

    def flush() -> None:
        nonlocal current_type, current_heading, current_body, current_conf
        if current_type is None:
            return
        body = "\n".join(current_body).strip("\n")
        if body.strip() or current_heading:
            chunks.append((current_type, current_heading, body.splitlines(), current_conf))
        current_type = None
        current_heading = ""
        current_body = []
        current_conf = 0.0

    for line in lines:
        if _is_noise_line(line):
            continue
        heading = _detect_heading(line)
        if heading is not None:
            flush()
            current_type, current_heading, rest, current_conf = heading
            if rest:
                current_body.append(rest)
            continue
        if current_type is None:
            leading.append(line)
        else:
            current_body.append(line)

    flush()

    if not chunks:
        return [Segment(segment_type="rohtext", text=raw.strip("\n"), confidence=0.0, heading="")]

    # Text before the first recognised heading is preserved as a leading rohtext segment
    # (never silently dropped).
    leading_text = "\n".join(leading).strip("\n")
    if leading_text.strip():
        chunks.insert(0, ("rohtext", "", leading_text.splitlines(), 0.2))

    segments: list[Segment] = []
    seen_type_index: dict[str, int] = {}
    for segment_type, heading, body, conf in chunks:
        index = len(segments)
        body_text = "\n".join(body).strip("\n")
        duplicate_of = None
        # Merge directly adjacent same-type blocks (duplicate labels).
        if segments and segments[-1].segment_type == segment_type:
            previous = segments[-1]
            merged_text = (previous.text + "\n" + body_text).strip("\n")
            merged_conf = max(previous.confidence, conf)
            segments[-1] = Segment(
                segment_type=segment_type,
                text=merged_text,
                confidence=merged_conf,
                heading=previous.heading or heading,
                index=previous.index,
                duplicate_of=None,
            )
            continue
        # A non-adjacent repeat of an earlier type is a duplicate source, not a merge.
        if segment_type in seen_type_index and segment_type != "rohtext":
            duplicate_of = seen_type_index[segment_type]
        segments.append(
            Segment(
                segment_type=segment_type,
                text=body_text,
                confidence=conf,
                heading=heading,
                index=index,
                duplicate_of=duplicate_of,
            )
        )
        seen_type_index.setdefault(segment_type, index)

    # Re-index after any merge.
    return [
        Segment(
            segment_type=item.segment_type,
            text=item.text,
            confidence=item.confidence,
            heading=item.heading,
            index=position,
            duplicate_of=item.duplicate_of,
        )
        for position, item in enumerate(segments)
    ]


def segment_as_dicts(segments: Iterable[Segment]) -> list[dict[str, object]]:
    return [item.as_dict() for item in segments]


__all__ = [
    "SEGMENT_LABELS",
    "SEGMENT_TYPES",
    "Segment",
    "segment",
    "segment_as_dicts",
]
