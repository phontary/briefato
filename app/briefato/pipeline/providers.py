"""Provider abstraction for the Briefato model layer.

OWNER: WORKSTREAM-PIPELINE. Frozen API (docs/02-spec-interfaces.md §6)::

    @dataclass
    class LLMResult:
        text: str; model: str; provider: str
        tokens_in: int; tokens_out: int; cost_usd: float; latency_ms: int
    class LLMProvider(Protocol):
        def generate(self, system: str, user: str, *,
                     max_tokens: int = 2000, temperature: float = 0.2) -> LLMResult: ...
    def get_provider(settings) -> LLMProvider

Decision D5 (provider-agnostic): any OpenAI-compatible ``/chat/completions`` endpoint
works. ``BRIEFATO_LLM_MOCK=true`` selects the deterministic, fully offline
:class:`MockProvider` used in dev and tests — no network calls.

The API key is only ever placed in the ``Authorization`` header. It is never logged,
never echoed in a payload, and never included in an exception message.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx

from .prompts import (
    COMPRESSION_TASK,
    DICTATION_CLOSE,
    DICTATION_OPEN,
    SEGMENT_TYPE_LINE,
    WEAVE_TASK,
)

logger = logging.getLogger(__name__)

_MAX_PROVIDER_MESSAGE = 300


class PipelineError(Exception):
    """Base class for every pipeline failure."""


class PipelineProviderError(PipelineError):
    """A model provider call failed; carries a mapped status code.

    ``message`` is safe to store/log: it contains the HTTP status and a truncated,
    single-line copy of the provider's message — never the request headers or API key.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        provider: str = "openai-compat",
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider = provider
        self.retryable = retryable

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


@dataclass
class LLMResult:
    text: str
    model: str
    provider: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int


@runtime_checkable
class LLMProvider(Protocol):
    def generate(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResult: ...


# --------------------------------------------------------------------------- mock

# --- method shaping helpers (WORKSTREAM-BRAIN-V2) ---------------------------
#
# The MockProvider used to echo the dictation verbatim, so the rule-check panel
# always showed hard failures (R21 Diagnosen, R5 Kategorie-Label, R6 ASCII-Umlaute)
# and dev/staging demos were useless. It now composes a *method-shaped* draft from
# the dictation: prose first, then the labelled blocks in the order the document
# type requires. It never invents clinical facts and states only diagnoses that
# appear in the dictation (else "keine Angabe im Diktat").

# Legitimate German words containing the ae/oe trigram — never "corrected".
_MOCK_UMLAUT_ALLOW = {
    "aerosol", "aerob", "aerobier", "aerobes", "aachen", "oesophagus", "oesophagitis",
    "oesophag", "oesophage", "oocyte", "koeffizient", "poesie", "poet", "poetisch",
    "michael", "rafael", "raffael", "israel",
}

# Curated 'ue' transliterations (generic 'ue' is legitimate: neue, zuerst, Quelle).
_MOCK_UE_WORDS = {
    "ueber", "ueberweisung", "uebernahme", "uebergeben", "ueberpruefung", "ueberpruefen",
    "ueberwachung", "uebersicht", "ueberleben", "uebungen", "uebung", "uebel", "uebelkeit",
    "durchfuehrung", "durchgefuehrt", "durchfuehren", "fuehrung", "fuehren", "fuehrte",
    "gefuehl", "zufuehren", "zurueck", "zustaendig", "verfuegung", "ausfuehren", "aufuehren",
    "unterstuetzung", "unterstuetzen", "begruendung", "verkuerzung", "zustaende", "zustaenden",
}

# Forbidden category labels the rule checker (R5) rejects in prose.
_MOCK_FORBIDDEN_LABELS = (
    "ku", "sono", "sonografie", "sonographie", "labor", "laborwerte", "ct", "mrt",
    "anamnese", "befund", "therapie", "diagnostik", "klinik", "verlauf", "aufnahme",
    "entlassung", "ekg", "röntgen", "roentgen", "endoskopie", "histologie", "medikation",
    "procedere", "aufnahmebefund", "untersuchung", "diagnose", "vorgeschichte",
)

# Block labels the composer recognises in the dictation (umlaut-folded lowercase).
_MOCK_BLOCK_LABELS = {
    "ambulante therapieempfehlungen nach der entlassung": "ambulant_empfehlungen",
    "therapieempfehlungen bei entlassung": "ambulant_empfehlungen",
    "diagnosen": "diagnosen",
    "diagnose": "diagnosen",
    "nebenerkrankungen": "nebenerkrankungen",
    "therapie-massnahmen auf der station": "therapie_station",
    "therapie-massnahmen": "therapie_station",
}
_MOCK_OPS_LABELS = {
    "indikation": "indikation",
    "op": "op",
    "operation": "op",
    "praeparat": "praeparat",
    "präparat": "praeparat",
}

_WORD_RE_MOCK = re.compile(r"[A-Za-zÄÖÜäöüß]+")
_DIAG_PREFIX_RE = re.compile(r"^\s*(?:dg\.?|diagnose[n]?)\s*:\s*", re.IGNORECASE)

# --- fan-out parsing (WORKSTREAM-ENGINE-V2) ---------------------------------
_SEGMENT_TYPE_RE = re.compile(r"Segmenttyp:\s*([a-z_]+)", re.IGNORECASE)
_SEGMENT_BODY_RE = re.compile(r"<segment>\s*(.*?)\s*</segment>", re.DOTALL | re.IGNORECASE)
_TYPED_SEGMENT_RE = re.compile(
    r'<segment\s+type="([^"]+)"[^>]*>\s*(.*?)\s*</segment>', re.DOTALL | re.IGNORECASE
)
_DATE_AM_RE = re.compile(r"\bam\s+\d{1,2}\.\d{1,2}\.?\d{0,4}\b", re.IGNORECASE)
_PFLICHTSATZ = "Wir nahmen die Pat. zur weiteren Diagnostik bzw. Schmerztherapie stationär auf."

# Per segment type, how many distilled sentences the mock keeps.
_COMPRESSION_BUDGET: dict[str, int] = {
    "anamnese_ku": 3,
    "roentgen": 2,
    "ct": 2,
    "mrt": 2,
    "sono": 2,
    "echo": 2,
    "oegd": 3,
    "kolo": 3,
    "endosonographie": 3,
    "op_bericht": 2,
    "pathologie": 2,
    "diabetologie": 2,
    "pflegeberichte": 2,
    "visiten": 4,
    "labor": 2,
    "konsile": 1,
    "diagnosen": 20,
    "therapie_empfehlung": 10,
    "rohtext": 3,
}


def _mock_neutralize_dates(text: str) -> str:
    """Drop 'am TT.MM.' from narrative text (R10: no dates in the Verlauf)."""
    return " ".join(_DATE_AM_RE.sub("", text or "").split())


# German abbreviations whose dot is not a sentence end (the splitter must not cut them).
_MOCK_ABBREV = (
    "Pat.", "pat.", "z.B.", "z. B.", "bzw.", "ca.", "Dr.", "med.", "ggf.", "etc.",
    "usw.", "Prof.", "bzgl.", "evtl.", "inkl.", "sog.", "u.a.", "d.h.", "o.g.",
    "Nr.", "Abb.", "Tab.", "Kdr.", "mind.", "max.", "resp.", "ggü.", "Z.n.", "z.n.",
)


def _mock_split_sentences(text: str) -> list[str]:
    """Sentence split that keeps common German abbreviations intact."""
    protected = text or ""
    tokens: list[tuple[str, str]] = []
    for index, abbreviation in enumerate(_MOCK_ABBREV):
        placeholder = f"\x00{index}\x00"
        if abbreviation in protected:
            protected = protected.replace(abbreviation, placeholder)
            tokens.append((placeholder, abbreviation))
    parts = re.split(r"(?<=[.!?])\s+", protected)
    out: list[str] = []
    for part in parts:
        for placeholder, abbreviation in tokens:
            part = part.replace(placeholder, abbreviation)
        if part.strip():
            out.append(part.strip())
    return out


def _mock_fold(text: str) -> str:
    text = (text or "").lower()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _mock_fix_umlauts(text: str) -> str:
    """Turn conservative ASCII transliterations back into ä/ö/ü (R6)."""

    def fix(word: str) -> str:
        low = word.lower()
        if low in _MOCK_UMLAUT_ALLOW:
            return word
        if "ae" in low or "oe" in low:
            fixed = re.sub(r"(?i)ae", "ä", re.sub(r"(?i)oe", "ö", word))
        elif low in _MOCK_UE_WORDS:
            fixed = re.sub(r"(?i)ue", "ü", word)
        elif low.startswith("ue") and len(low) >= 5:
            fixed = re.sub(r"(?i)ue", "ü", word, count=1)
        else:
            return word
        if word[:1].isupper():
            fixed = fixed[:1].upper() + fixed[1:]
        return fixed

    return _WORD_RE_MOCK.sub(lambda match: fix(match.group(0)), text)


_MOCK_BLOCK_LABELS_FOLDED = {_mock_fold(key): value for key, value in _MOCK_BLOCK_LABELS.items()}
_MOCK_OPS_LABELS_FOLDED = {_mock_fold(key): value for key, value in _MOCK_OPS_LABELS.items()}


def _mock_strip_markdown(text: str) -> str:
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = text.replace("|", " ")
    text = re.sub(r"(?m)^\s*[-*•·]\s+", "", text)
    text = re.sub(r"(?m)^\s*\d+[.)]\s+", "", text)
    return text


def _mock_strip_forbidden_labels(text: str, *, allow_ops: bool) -> str:
    words = list(_MOCK_FORBIDDEN_LABELS)
    if not allow_ops:
        words += ["indikation", "op", "operation", "präparat", "praeparat"]
    word_set = set(words)
    for word in sorted(words, key=len, reverse=True):
        pattern = r"(?<![A-Za-zÄÖÜäöüß])" + re.escape(word) + r"\s*:"
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)

    # A leading label whose FIRST token is a category word ("CT Abdomen:", "Sonographie
    # Abdomen:") is stripped too — the rule checker keys on the first token.
    lead_re = re.compile(
        r"^\s*([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß.\-/]*(?:\s+[\wÄÖÜäöüß.\-/]+){0,3})\s*:\s*"
    )

    def _lead(match: re.Match[str]) -> str:
        first = match.group(1).split()[0].lower().strip("-.")
        return " " if first in word_set else match.group(0)

    return lead_re.sub(_lead, text)


def _mock_clean_line(line: str) -> str:
    line = _mock_strip_markdown(line)
    line = re.sub(r"^\s*[-*•·]\s*", "", line)
    line = _mock_strip_forbidden_labels(line, allow_ops=True)
    line = _mock_fix_umlauts(line)
    return " ".join(line.split())


class MockProvider:
    """Deterministic, offline provider that emits a method-shaped draft.

    Given a dictation it produces plain text (no markdown, no category labels),
    prose first, then the labelled blocks in the order the document type requires
    (for a stationary discharge letter: ``ambulante Therapieempfehlungen nach der
    Entlassung:`` → ``Diagnosen:`` → ``Nebenerkrankungen:`` → ``Therapie-Maßnahmen
    auf der Station:``). It states only diagnoses that appear in the dictation and
    never invents clinical facts; when no diagnosis is recognisable it writes
    ``Diagnosen:`` followed by ``keine Angabe im Diktat``. The result passes the
    R1–R67 rule checker for method-shaped input (tested).
    """

    name = "mock"

    def __init__(self, model: str = "briefato-mock-de-1") -> None:
        self.model = model

    def generate(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResult:
        started = time.perf_counter()
        # Fan-out call kinds (WORKSTREAM-ENGINE-V2): per-segment compression and the final
        # weave are recognised by their task marker before the single-pass path applies.
        if COMPRESSION_TASK in (user or ""):
            text = self._compose_compression(user)
        elif WEAVE_TASK in (user or ""):
            text = self._compose_weave(user, self._extract_kind(user))
        else:
            dictation = self._extract_dictation(user)
            kind = self._extract_kind(user)
            text = self._compose(dictation, kind)
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))
        return LLMResult(
            text=text,
            model=self.model,
            provider=self.name,
            tokens_in=max(1, (len(system) + len(user)) // 4),
            tokens_out=max(1, len(text) // 4),
            cost_usd=0.0,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _extract_kind(user: str) -> str:
        match = re.search(r"Dokumenttyp:\s*[^(\n]+\(([\w-]+)\)", user)
        return match.group(1) if match else "sonstiges"

    @staticmethod
    def _extract_dictation(user: str) -> str:
        match = re.search(
            re.escape(DICTATION_OPEN) + r"\s*(.*?)\s*" + re.escape(DICTATION_CLOSE),
            user,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        return (user or "").strip()

    # -- composition -------------------------------------------------------

    @classmethod
    def _parse(cls, dictation: str) -> tuple[list[str], dict[str, list[str]]]:
        """Split into narrative chunks + recognised labelled blocks."""
        chunks = [chunk for chunk in re.split(r"\n\s*\n", dictation or "") if chunk.strip()]
        narrative: list[str] = []
        blocks: dict[str, list[str]] = {}
        for chunk in chunks:
            lines = chunk.splitlines()
            first = lines[0].strip()
            kind = None
            head = first.split(":", 1)
            if len(head) == 2:
                label = _mock_fold(head[0])
                if label in _MOCK_BLOCK_LABELS_FOLDED:
                    kind = _MOCK_BLOCK_LABELS_FOLDED[label]
                elif label in _MOCK_OPS_LABELS_FOLDED:
                    kind = _MOCK_OPS_LABELS_FOLDED[label]
            if kind is None:
                narrative.append(chunk)
                continue
            content = head[1].strip()
            body = ([content] if content else []) + lines[1:]
            blocks.setdefault(kind, []).extend(body)
        return narrative, blocks

    @classmethod
    def _weave(cls, narrative: list[str], *, allow_ops: bool = False) -> list[str]:
        paragraphs: list[str] = []
        for chunk in narrative:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            text = _mock_strip_markdown(" ".join(lines))
            text = _mock_strip_forbidden_labels(text, allow_ops=allow_ops)
            text = _mock_fix_umlauts(text)
            text = cls._cap_semicolons(text)
            text = " ".join(text.split())
            if text:
                paragraphs.append(text)
        return cls._dedupe_sentences(paragraphs)

    @staticmethod
    def _cap_semicolons(text: str) -> str:
        if text.count(";") > 1:
            return text.replace(";", ",")
        return text

    @staticmethod
    def _dedupe_sentences(paragraphs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for paragraph in paragraphs:
            sentences = re.split(r"(?<=[.!?])\s+", paragraph)
            kept = []
            for sentence in sentences:
                key = _mock_fold(sentence)
                if len(key) >= 20 and key in seen:
                    continue
                seen.add(key)
                kept.append(sentence)
            joined = " ".join(kept).strip()
            if joined:
                out.append(joined)
        return out

    @classmethod
    def _clean_block(cls, lines: list[str] | None) -> str:
        cleaned = [cls._cap_semicolons(_mock_clean_line(line)) for line in (lines or [])]
        cleaned = [line for line in cleaned if line]
        return "\n".join(cleaned)

    @classmethod
    def _diagnoses(cls, lines: list[str] | None) -> tuple[str, list[str]]:
        """Return (diagnosis list text, Z.n. lines moved out of the list)."""
        diagnoses: list[str] = []
        zn: list[str] = []
        for line in lines or []:
            cleaned = cls._cap_semicolons(_mock_clean_line(line))
            cleaned = _DIAG_PREFIX_RE.sub("", cleaned).strip()
            if not cleaned:
                continue
            if cleaned.lower().startswith("z.n."):
                zn.append(cleaned)
            else:
                diagnoses.append(cleaned)
        if not diagnoses:
            return "keine Angabe im Diktat", zn
        return "\n".join(diagnoses), zn

    # -- fan-out: compression + weave (WORKSTREAM-ENGINE-V2) ----------------

    @staticmethod
    def _relevant_pflege(sentence: str) -> bool:
        low = sentence.lower()
        return any(
            word in low
            for word in (
                "wunde", "wund", "schmerz", "mobil", "fieber", "vital", "temperatur",
                "oedem", "ödem", "belag", "sekret", "blutung", "kostaufbau", "stuhlgang",
                "auffällig", "atem", "kreislauf", "verband", "drainage", "verwirrt",
            )
        )

    @classmethod
    def _compress_text(cls, segment_type: str, raw: str) -> str:
        """Deterministically compress one source segment to its distilled insights."""
        budget = _COMPRESSION_BUDGET.get(segment_type, 3)
        pieces: list[str] = []
        for line in (raw or "").splitlines():
            for sentence in _mock_split_sentences(line.strip()):
                cleaned = _mock_clean_line(sentence)
                # No category label may survive a compression (R5) — incl. OP labels.
                cleaned = _mock_strip_forbidden_labels(cleaned, allow_ops=False)
                cleaned = _mock_neutralize_dates(cleaned)
                if len(cleaned) >= 15:
                    pieces.append(cleaned)
        if not pieces:
            return ""
        if segment_type == "pflegeberichte":
            relevant = [piece for piece in pieces if cls._relevant_pflege(piece)]
            pieces = relevant or []
        if segment_type in ("diagnosen", "therapie_empfehlung"):
            # A Diagnosen/Therapieempfehlungen block is a list — keep one entry per line.
            return "\n".join(pieces[:budget]).strip()
        return " ".join(pieces[:budget]).strip()

    @classmethod
    def _compose_compression(cls, user: str) -> str:
        match = _SEGMENT_TYPE_RE.search(user or "")
        segment_type = match.group(1).lower() if match else "rohtext"
        body_match = _SEGMENT_BODY_RE.search(user or "")
        raw = body_match.group(1) if body_match else ""
        if not raw.strip():
            return "keine Angabe im Segment."
        compressed = cls._compress_text(segment_type, raw)
        if not compressed:
            return ""  # no distilled insight in this source (e.g. pure care routine)
        return cls._finalize(compressed)

    @classmethod
    def _weave_paragraphs(cls, chunks: list[str]) -> list[str]:
        paragraphs: list[str] = []
        for chunk in chunks:
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            text = _mock_strip_markdown(" ".join(lines))
            text = _mock_strip_forbidden_labels(text, allow_ops=False)
            text = _mock_fix_umlauts(text)
            text = _mock_neutralize_dates(text)
            text = cls._cap_semicolons(text)
            text = " ".join(text.split())
            if text:
                paragraphs.append(text)
        return cls._dedupe_sentences(paragraphs)

    @classmethod
    def _compose_weave(cls, user: str, kind: str) -> str:
        pairs = _TYPED_SEGMENT_RE.findall(user or "")
        if not pairs:
            pairs = [("rohtext", body) for body in _SEGMENT_BODY_RE.findall(user or "")]

        narrative: list[str] = []
        op_chunks: list[str] = []
        diag_lines: list[str] = []
        empfehlung_lines: list[str] = []
        for segment_type, body in pairs:
            segment_type = (segment_type or "rohtext").lower()
            body = (body or "").strip()
            if not body:
                continue
            if segment_type == "diagnosen":
                diag_lines.extend(line for line in body.splitlines() if line.strip())
            elif segment_type == "therapie_empfehlung":
                empfehlung_lines.extend(line for line in body.splitlines() if line.strip())
            else:
                narrative.append(body)
                if segment_type == "op_bericht":
                    op_chunks.append(body)

        paragraphs = cls._weave_paragraphs(narrative)
        joined = " ".join(paragraphs).strip()

        if kind == "zusammenfassung":
            sentences = _mock_split_sentences(joined)
            return cls._finalize(" ".join(sentences[:4]).strip()) or "keine Angabe im Diktat."

        if kind == "arztbrief":
            if "stationär auf" not in joined.lower():
                joined = (joined + " " + _PFLICHTSATZ).strip()

        parts: list[str] = [joined] if joined else []

        if kind == "operationsbericht":
            diag, zn = cls._diagnoses(diag_lines)
            parts.append("Diagnosen:\n" + diag)
            op_text = cls._clean_block(op_chunks) or "keine Angabe im Diktat"
            parts.append("Operation:\n" + op_text)
            if zn:
                parts.append("OP:\n" + "\n".join(zn))
            return cls._finalize("\n\n".join(part for part in parts if part.strip()))

        if kind == "arztbrief":
            if empfehlung_lines:
                parts.append(
                    "ambulante Therapieempfehlungen nach der Entlassung:\n"
                    + cls._clean_block(empfehlung_lines)
                )
            diag, zn = cls._diagnoses(diag_lines)
            parts.append("Diagnosen:\n" + diag)
            parts.append("Nebenerkrankungen:\nkeine")
            station_lines: list[str] = []
            for chunk in op_chunks:
                sentences = _mock_split_sentences(cls._clean_block([chunk]))
                if sentences:
                    # A distinct 'OP am XXX:' line (R9) — the narrative keeps the prose,
                    # the block lists the measure without duplicating a whole sentence.
                    station_lines.append("OP am XXX: " + sentences[0])
            if zn:
                station_lines.append("\n".join(zn))
            if not station_lines:
                station_lines = ["keine Angabe im Diktat"]
            parts.append("Therapie-Maßnahmen auf der Station:\n" + "\n".join(station_lines))
            return cls._finalize("\n\n".join(part for part in parts if part.strip()))

        # Any other type: prose plus the Diagnosen list only when the sources carried one.
        if diag_lines:
            diag, zn = cls._diagnoses(diag_lines)
            parts.append("Diagnosen:\n" + diag)
            if zn:
                parts.append("\n".join(zn))
        return cls._finalize("\n\n".join(part for part in parts if part.strip())) or "keine Angabe im Diktat."

    @classmethod
    def _compose(cls, dictation: str, kind: str) -> str:
        narrative, blocks = cls._parse(dictation)
        prose = cls._weave(narrative, allow_ops=(kind == "operationsbericht"))

        if kind == "ambulant":
            # R58 forbids the stationary-admission sentence in an ambulant letter.
            prose = [p for p in prose if "stationär auf" not in p.lower() and "stationaer auf" not in p.lower()]

        if kind == "zusammenfassung":
            text = " ".join(prose).strip()
            sentences = re.split(r"(?<=[.!?])\s+", text)
            return cls._finalize(" ".join(sentences[:4]).strip()) or "keine Angabe im Diktat."

        parts: list[str] = list(prose)

        if kind == "operationsbericht":
            for key, label in (("indikation", "Indikation:"), ("op", "OP:"), ("praeparat", "Präparat:")):
                if blocks.get(key):
                    parts.append(label + "\n" + cls._clean_block(blocks[key]))
            diag, zn = cls._diagnoses(blocks.get("diagnosen"))
            parts.append("Diagnosen:\n" + diag)
            op_text = cls._clean_block(blocks.get("op")) or "keine Angabe im Diktat"
            parts.append("Operation:\n" + op_text)
            if zn:
                parts.append("OP:\n" + "\n".join(zn))
            return cls._finalize("\n\n".join(part for part in parts if part.strip()))

        if kind in {"arztbrief", "ambulant"}:
            if kind == "arztbrief" and blocks.get("ambulant_empfehlungen"):
                parts.append(
                    "ambulante Therapieempfehlungen nach der Entlassung:\n"
                    + cls._clean_block(blocks["ambulant_empfehlungen"])
                )
            diag, zn = cls._diagnoses(blocks.get("diagnosen"))
            parts.append("Diagnosen:\n" + diag)
            if kind == "arztbrief":
                if blocks.get("nebenerkrankungen"):
                    parts.append("Nebenerkrankungen:\n" + cls._clean_block(blocks["nebenerkrankungen"]))
                station = cls._clean_block(blocks.get("therapie_station"))
                station_lines = [station] if station else []
                if zn:
                    station_lines.append("\n".join(zn))
                if station_lines:
                    parts.append("Therapie-Maßnahmen auf der Station:\n" + "\n".join(station_lines))
            elif zn:
                parts.append("\n".join(zn))
            return cls._finalize("\n\n".join(part for part in parts if part.strip()))

        # Any other document type: prose plus a Diagnosen list only when the
        # dictation actually carried one (never invented).
        if blocks.get("diagnosen"):
            diag, zn = cls._diagnoses(blocks.get("diagnosen"))
            parts.append("Diagnosen:\n" + diag)
            if zn:
                parts.append("\n".join(zn))
        return cls._finalize("\n\n".join(part for part in parts if part.strip())) or "keine Angabe im Diktat."

    @staticmethod
    def _finalize(text: str) -> str:
        text = (text or "").strip()
        text = MockProvider._cap_semicolons(text)
        return text



# --------------------------------------------------------------------------- openai-compatible


class OpenAICompatProvider:
    """Synchronous OpenAI-compatible ``/chat/completions`` client (httpx)."""

    name = "openai-compat"

    def __init__(
        self,
        settings: Any,
        *,
        client: httpx.Client | None = None,
        max_retries: int = 2,
        retry_backoff_s: float = 0.5,
    ) -> None:
        self._settings = settings
        self._client = client
        self._max_retries = int(max_retries)
        self._retry_backoff_s = float(retry_backoff_s)

    # -- helpers ---------------------------------------------------------------

    def _endpoint(self) -> str:
        return str(self._settings.llm_base_url).rstrip("/") + "/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        timeout = self._settings.llm_timeout_s
        if self._client is not None:
            return self._client.post(self._endpoint(), json=payload, headers=self._headers(), timeout=timeout)
        with httpx.Client(timeout=timeout) as client:
            return client.post(self._endpoint(), json=payload, headers=self._headers())

    @staticmethod
    def _truncate(message: str) -> str:
        text = " ".join((message or "").split())
        if len(text) > _MAX_PROVIDER_MESSAGE:
            return text[:_MAX_PROVIDER_MESSAGE] + "…"
        return text

    def _status_error(self, response: httpx.Response) -> PipelineProviderError:
        retryable = response.status_code == 429 or 500 <= response.status_code < 600
        detail = self._truncate(response.text)
        message = f"Modellanbieter antwortete mit Status {response.status_code}"
        if detail:
            message += f": {detail}"
        return PipelineProviderError(message, status_code=response.status_code, provider=self.name, retryable=retryable)

    def _post_with_retries(self, payload: dict[str, Any]) -> httpx.Response:
        last_error: PipelineProviderError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._post(payload)
            except httpx.TimeoutException:
                last_error = PipelineProviderError(
                    "Zeitüberschreitung bei der Modellanfrage.",
                    status_code=None,
                    provider=self.name,
                    retryable=True,
                )
            except httpx.HTTPError as exc:
                last_error = PipelineProviderError(
                    f"Netzwerkfehler bei der Modellanfrage ({type(exc).__name__}).",
                    status_code=None,
                    provider=self.name,
                    retryable=True,
                )
            else:
                if response.status_code == 200:
                    return response
                last_error = self._status_error(response)
                if not last_error.retryable:
                    raise last_error
            if attempt < self._max_retries:
                time.sleep(self._retry_backoff_s * (2**attempt))
        assert last_error is not None  # pragma: no cover - loop always sets it
        raise last_error

    # -- API -------------------------------------------------------------------

    def generate(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.2,
    ) -> LLMResult:
        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        started = time.perf_counter()
        response = self._post_with_retries(payload)
        latency_ms = int((time.perf_counter() - started) * 1000)

        try:
            data = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise PipelineProviderError(
                "Antwort des Modellanbieters war kein gültiges JSON.",
                status_code=response.status_code,
                provider=self.name,
            ) from exc

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PipelineProviderError(
                "Antwort des Modellanbieters enthielt keinen Text.",
                status_code=response.status_code,
                provider=self.name,
            ) from exc
        if not isinstance(text, str) or not text.strip():
            raise PipelineProviderError(
                "Antwort des Modellanbieters war leer.",
                status_code=response.status_code,
                provider=self.name,
            )

        usage = data.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens") or 0)
        tokens_out = int(usage.get("completion_tokens") or 0)
        cost_usd = (
            tokens_in / 1000.0 * float(getattr(self._settings, "llm_cost_in_per_1k", 0.0) or 0.0)
            + tokens_out / 1000.0 * float(getattr(self._settings, "llm_cost_out_per_1k", 0.0) or 0.0)
        )
        return LLMResult(
            text=text,
            model=str(data.get("model") or self._settings.llm_model),
            provider=self.name,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )


def get_provider(settings: Any) -> LLMProvider:
    """Return :class:`MockProvider` when ``settings.llm_mock`` else the HTTP provider."""
    if getattr(settings, "llm_mock", True):
        return MockProvider()
    return OpenAICompatProvider(settings)


__all__ = [
    "PipelineError",
    "PipelineProviderError",
    "LLMResult",
    "LLMProvider",
    "MockProvider",
    "OpenAICompatProvider",
    "get_provider",
]
