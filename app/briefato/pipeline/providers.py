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

from .prompts import DICTATION_CLOSE, DICTATION_OPEN, KIND_LABELS

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


class MockProvider:
    """Deterministic, offline provider.

    It does not invent clinical content: it only re-emits the (pseudonymised)
    dictation wrapped in a plausible German letter skeleton, so token restoration
    and the end-to-end flow can be exercised without a network call. Token counts
    are estimated from character counts; cost is always 0.
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
        kind = self._extract_kind(user)
        dictation = self._extract_dictation(user)
        text = self._compose(kind, dictation)
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
        match = re.search(r"Dokumenttyp:\s*[^(\n]+\((\w+)\)", user)
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

    @staticmethod
    def _compose(kind: str, dictation: str) -> str:
        label = KIND_LABELS.get(kind, KIND_LABELS["sonstiges"])
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", dictation) if p.strip()]
        body = "\n\n".join(paragraphs) or "Keine Angaben übermittelt."
        return (
            "Sehr geehrte Damen und Herren,\n\n"
            f"Betreff: {label}\n\n"
            f"{body}\n\n"
            "Mit freundlichen Grüßen"
        )


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
