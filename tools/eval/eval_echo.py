"""Echo detection — the metric that answers Mohamed's criticism.

His objection: *"in every test you write the whole letter yourself precisely, and
the output is just a copy of what you wrote — there is no craft in it."*

This module measures exactly that. It compares the model **output** against the
**input material** (the dictation) and asks: is the output just a re-arranged copy
of the input, or was something genuinely re-formulated?

Two independent numbers are computed after normalisation:

* ``similarity`` — ``difflib.SequenceMatcher`` ratio on the normalised **character**
  strings (the figure named in the method spec);
* ``token_ratio`` — ``SequenceMatcher`` ratio on the normalised **token sequence**;
* ``jaccard`` — token-set overlap ``|A ∩ B| / |A ∪ B|``.

The structural block labels (``Diagnosen:``, ``Nebenerkrankungen:``,
``Therapie-Maßnahmen auf der Station:``, ``Indikation:``, ``OP:``, ``Präparat:``,
``Operation:`` …) are removed before comparison: they legitimately appear verbatim
in both input and output and would otherwise inflate the ratio.

Verdict: **``ECHO (keine eigene Formulierung)``** when ``similarity > 0.85``.

Pure stdlib. No network, no repo imports.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field

# The method-mandated threshold (task spec): above this the draft is a copy.
ECHO_THRESHOLD = 0.85
ECHO_VERDICT = "ECHO (keine eigene Formulierung)"
REWRITE_VERDICT = "eigene Formulierung (kein Echo)"

# Per-document-type thresholds. Zusammenfassung and Entlassmedikationsplan are
# *compression* tasks: a faithful output is a condensed subset of the dictation, so its
# character-level overlap with the input is inherently higher than for narrative letter
# types. Holding them to the plain 0.85 bar would flag a correct short summary as a copy.
# The raised bar keeps the verdict meaningful for exactly those types.
ECHO_THRESHOLDS_BY_TYPE: dict[str, float] = {
    "zusammenfassung": 0.92,
    "entlassmedikationsplan": 0.92,
}


def echo_threshold_for(doc_type: str | None) -> float:
    """Return the echo threshold for ``doc_type`` (falling back to the global default)."""
    return ECHO_THRESHOLDS_BY_TYPE.get((doc_type or "").strip().lower(), ECHO_THRESHOLD)

# Block labels that may legitimately appear verbatim in both material and output.
STRUCTURAL_LABELS: tuple[str, ...] = (
    "ambulante therapieempfehlungen nach der entlassung",
    "therapieempfehlungen bei entlassung",
    "therapie-massnahmen auf der station",
    "therapie-massnahmen",
    "nebenerkrankungen",
    "diagnosen",
    "indikation",
    "präparat",
    "praeparat",
    "operation",
    "op-bericht",
    "operationsbericht",
    "op",
)

_UMLAUT_MAP = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}

# Very common German function words carry no signal for an echo verdict.
_STOPWORDS = frozenset(
    {
        "der", "die", "das", "und", "den", "dem", "des", "ein", "eine", "einen",
        "einem", "einer", "eines", "ist", "sind", "war", "waren", "wird", "werden",
        "wurde", "wurden", "mit", "auf", "bei", "von", "für", "fuer", "als", "aus",
        "sich", "nicht", "kein", "keine", "auch", "sowie", "über", "ueber", "unter",
        "nach", "vor", "zum", "zur", "im", "in", "am", "an", "es", "zu", "so",
        "sich", "dass", "sich", "hier", "dort", "ohne", "durch", "wieder",
    }
)


def _fold(text: str) -> str:
    """Lowercase and fold ä/ö/ü/ß to ae/oe/ue/ss so ASCII and real umlauts compare equal."""
    text = (text or "").lower()
    for source, target in _UMLAUT_MAP.items():
        text = text.replace(source, target)
    return text


def _strip_structural_labels(folded: str) -> str:
    """Remove block labels (whole-line and inline ``label:`` forms) from folded text."""
    for label in sorted(STRUCTURAL_LABELS, key=len, reverse=True):
        # whole-line label (with or without trailing colon)
        folded = re.sub(rf"(?m)^[ \t]*{re.escape(label)}[ \t]*:?[ \t]*$", " ", folded)
        # inline "label:" occurrence
        folded = re.sub(rf"(?<![a-z0-9]){re.escape(label)}[ \t]*:", " ", folded)
    return folded


def normalise(text: str, *, strip_labels: bool = True) -> str:
    """Return the comparison form: folded, label-stripped, punctuation-free."""
    folded = _fold(text)
    if strip_labels:
        folded = _strip_structural_labels(folded)
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return " ".join(folded.split())


def _tokens(normalised: str) -> list[str]:
    return [token for token in normalised.split() if len(token) >= 3 and token not in _STOPWORDS]


@dataclass
class EchoResult:
    similarity: float
    token_ratio: float
    jaccard: float
    verdict: str
    is_echo: bool
    threshold: float
    shared_tokens: int
    input_tokens: int
    output_tokens: int
    content_echo: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "similarity": round(self.similarity, 4),
            "token_ratio": round(self.token_ratio, 4),
            "jaccard": round(self.jaccard, 4),
            "verdict": self.verdict,
            "is_echo": self.is_echo,
            "content_echo": self.content_echo,
            "threshold": self.threshold,
            "shared_tokens": self.shared_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


def detect_echo(
    dictation: str,
    output: str,
    *,
    threshold: float = ECHO_THRESHOLD,
) -> EchoResult:
    """Compare ``output`` against ``dictation`` and return an :class:`EchoResult`.

    ``similarity`` (character SequenceMatcher ratio) drives the verdict; the token
    ratio and Jaccard are reported alongside for transparency.
    """
    norm_in = normalise(dictation)
    norm_out = normalise(output)

    if not norm_in or not norm_out:
        return EchoResult(
            similarity=0.0,
            token_ratio=0.0,
            jaccard=0.0,
            verdict="nicht bewertbar (leere Eingabe/Ausgabe)",
            is_echo=False,
            threshold=threshold,
            shared_tokens=0,
            input_tokens=len(_tokens(norm_in)),
            output_tokens=len(_tokens(norm_out)),
        )

    similarity = difflib.SequenceMatcher(None, norm_in, norm_out).ratio()

    in_tokens = _tokens(norm_in)
    out_tokens = _tokens(norm_out)
    token_ratio = difflib.SequenceMatcher(None, in_tokens, out_tokens).ratio()

    in_set, out_set = set(in_tokens), set(out_tokens)
    union = in_set | out_set
    jaccard = len(in_set & out_set) / len(union) if union else 0.0

    is_echo = similarity > threshold
    # Secondary, content-level signal: even a re-ordered draft shares every content
    # word with the input. High Jaccard + low character similarity = "rearranged copy".
    content_echo = jaccard > threshold and len(out_tokens) >= 8
    return EchoResult(
        similarity=similarity,
        token_ratio=token_ratio,
        jaccard=jaccard,
        verdict=ECHO_VERDICT if is_echo else REWRITE_VERDICT,
        is_echo=is_echo,
        threshold=threshold,
        shared_tokens=len(in_set & out_set),
        input_tokens=len(in_tokens),
        output_tokens=len(out_tokens),
        content_echo=content_echo,
    )


__all__ = [
    "ECHO_THRESHOLD",
    "ECHO_THRESHOLDS_BY_TYPE",
    "ECHO_VERDICT",
    "REWRITE_VERDICT",
    "STRUCTURAL_LABELS",
    "EchoResult",
    "detect_echo",
    "echo_threshold_for",
    "normalise",
]
