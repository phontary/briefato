"""Patient pseudonymisation for the Briefato generation pipeline.

OWNER: WORKSTREAM-PIPELINE. Frozen API (docs/02-spec-interfaces.md §6)::

    class Pseudonymizer:
        FIELDS = ("last_name", "first_name", "birth_date", "insurance_number",
                  "street", "zip", "city", "phone", "email")
        @classmethod
        def from_patient(cls, patient) -> "Pseudonymizer"
        def mask(self, text: str) -> str
        def restore(self, text: str) -> str
        def masked_fields(self) -> dict[str, str]

Design notes (decision D4 — pseudonymise before every model call):

* Every identifier is replaced by a stable uppercase token ``{{FIELD}}``; the
  token->value map stays local and is never sent to the provider.
* Matching is case-insensitive on the *raw* value but the emitted token is always
  uppercase, so ``MÜLLER``/``müller`` both become ``{{LAST_NAME}}``.
* Values are tried longest-first, so a full street ("Musterstraße 12") wins over
  a shorter overlapping value.
* Birth dates are matched in both common German renderings (breit ``02.03.1974``
  and ISO ``1974-03-02``); :meth:`restore` re-inserts the canonical German form.
* :meth:`mask` is idempotent: text that already contains ``{{TOKEN}}`` placeholders
  is left untouched (the token alternative is consumed first and returned as-is),
  so masking an already-masked string cannot corrupt it.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Iterable

# A placeholder produced by this module (tolerates inner whitespace and any case,
# because a model may echo it slightly differently).
_TOKEN_RE = r"\{\{\s*[A-Za-z0-9_]+\s*\}\}"


def _token(field: str) -> str:
    return "{{" + field.upper() + "}}"


class Pseudonymizer:
    """Builds a token <-> value map for one patient and masks/restores text."""

    FIELDS = (
        "last_name",
        "first_name",
        "birth_date",
        "insurance_number",
        "street",
        "zip",
        "city",
        "phone",
        "email",
    )

    def __init__(self) -> None:
        self._token_to_value: dict[str, str] = {}
        self._value_to_token: dict[str, str] = {}  # lowercased raw value -> token

    # ------------------------------------------------------------------ build

    @classmethod
    def from_patient(cls, patient: Any) -> "Pseudonymizer":
        pz = cls()
        if patient is None:
            return pz
        for field in cls.FIELDS:
            value = getattr(patient, field, None)
            if field == "birth_date":
                pz._add_birth_date(value)
                continue
            if value is None:
                continue
            text = str(value).strip()
            if text:
                pz._add(_token(field), text)
        return pz

    def _add(self, token: str, canonical: str, extra_variants: Iterable[str] = ()) -> None:
        if not canonical.strip():
            return
        # Keep the first (canonical) value for the token; later equal values do not win.
        self._token_to_value.setdefault(token, canonical)
        for variant in (canonical, *tuple(extra_variants)):
            variant = (variant or "").strip()
            if variant:
                self._value_to_token.setdefault(variant.lower(), token)

    def _add_birth_date(self, value: Any) -> None:
        token = _token("birth_date")
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        german: str | None = None
        iso: str | None = None
        if isinstance(value, (datetime, date)):
            german = value.strftime("%d.%m.%Y")
            iso = value.strftime("%Y-%m-%d")
        else:
            text = str(value).strip()
            iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
            de_match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", text)
            if iso_match:
                iso = text
                german = f"{int(iso_match.group(3)):02d}.{int(iso_match.group(2)):02d}.{iso_match.group(1)}"
            elif de_match:
                german = text
                year = de_match.group(3)
                if len(year) == 2:
                    year = "19" + year
                iso = f"{year}-{int(de_match.group(2)):02d}-{int(de_match.group(1)):02d}"
            else:
                german = text
        variants = tuple(v for v in (german, iso) if v)
        canonical = german or iso or ""
        self._add(token, canonical, variants)

    # ------------------------------------------------------------------ mask

    def mask(self, text: str) -> str:
        if not text or not self._value_to_token:
            return text
        # Longest raw value first so overlapping values resolve deterministically.
        values = sorted(self._value_to_token.keys(), key=len, reverse=True)
        alternation = "|".join(re.escape(v) for v in values)
        pattern = re.compile(f"({_TOKEN_RE}|{alternation})", re.IGNORECASE | re.UNICODE)

        def _repl(match: re.Match[str]) -> str:
            found = match.group(0)
            # Never touch an existing placeholder: this makes mask() idempotent.
            if found.startswith("{{") and found.endswith("}}"):
                return found
            return self._value_to_token.get(found.lower(), found)

        return pattern.sub(_repl, text)

    # ------------------------------------------------------------------ restore

    def restore(self, text: str) -> str:
        if not text:
            return text
        for token, value in self._token_to_value.items():
            inner = re.escape(token[2:-2])
            pattern = re.compile(r"\{\{\s*" + inner + r"\s*\}\}", re.IGNORECASE)
            text = pattern.sub(lambda _m, v=value: v, text)
        return text

    # ------------------------------------------------------------------ introspection

    def masked_fields(self) -> dict[str, str]:
        """Token -> real value (for logging/audit; never send to a provider)."""
        return dict(self._token_to_value)

    def raw_values(self) -> list[str]:
        """Every raw value that must never appear in an outgoing prompt (lowercased)."""
        return list(self._value_to_token.keys())

    def sensitive_values(self, tokens: Iterable[str]) -> list[str]:
        """Raw values (incl. date variants) bound to the given token set, lowercased."""
        wanted = set(tokens)
        return [value for value, token in self._value_to_token.items() if token in wanted]


__all__ = ["Pseudonymizer"]
