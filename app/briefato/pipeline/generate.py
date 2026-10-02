"""Letter generation orchestration — now wired onto the harvested brain.

OWNER: WORKSTREAM-BRAIN-WIRING. Frozen API (docs/02-spec-interfaces.md §6)::

    def generate_letter(db, *, user, patient, kind: str, dictation: str,
                        letterhead: dict, extra: str = "") -> Letter

Flow (D4/D5/D7 + the brain workstream):

    triage(kind, dictation)            -> document type(s) (kern.md routing table)
      -> create Letter(status="generating", kind=<doc type>)
      -> pseudonymise dictation AND patient context (Pseudonymizer)
      -> retrieve Musterbriefe (scrub-pending excluded, licence-review flagged)
      -> assemble prompt from kern/regelwerk/anti-patterns/playbook/structure
      -> debug assertion that no raw identifier reached the prompt (env != "prod")
      -> provider.generate  (mock in dev)
      -> restore tokens
      -> rule_check(text, doc_type, dictation)   (R1-R67 + anti-patterns)
      -> HARD findings: retry ONCE with the findings as correction instructions
      -> store content_enc (Fernet), status="done", tokens/cost
      -> Generation row (pseudonymised=True)
      -> increment subscription.letters_used (only on success)
      -> audit event with kind/templates/findings
      -> attach ``letter.last_check`` (runtime attribute, no schema change)

Combined orders ("OP-Bericht + Zusammenfassung") produce BOTH documents: each type
is generated and checked separately, then joined with one blank line.

On a provider failure the letter is marked ``failed`` with a German-safe error string,
the quota is left untouched and :class:`PipelineGenerationError` is raised. The
Generation row's ``error`` column then carries a compact JSON diagnostics string.

The frozen schema has no JSON column for the audit detail, so the per-letter
checker/retrieval detail is (a) persisted via ``security.audit(...)`` and (b)
returned on the Letter as the runtime attribute ``letter.last_check`` for the UI.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import date, datetime
from typing import Any

from sqlalchemy import select

from .. import security
from ..brain import brain_loader, retrieval
from ..brain import triage as brain_triage
from ..brain.prompt_assembly import (
    PROMPT_VERSION,
    build_prompt,
    correction_block,
    reference_support_text,
)
from ..brain.rule_checker import autofix_umlauts, check as rule_check
from ..config import get_settings
from ..models import Generation, Letter, Subscription
from ..research import enrich_default, filter_generic, get_research_provider
from . import fanout, routing, segmenter
from .letterhead import render_docx  # re-exported for the frozen generate.py API
from .providers import PipelineError, get_provider
from .pseudonym import Pseudonymizer

logger = logging.getLogger(__name__)

_GENERIC_ERROR = "Die Erzeugung ist fehlgeschlagen. Bitte versuchen Sie es erneut."

# How much of the dictation is used as the retrieval query (bounded for speed).
_RETRIEVAL_QUERY_CHARS = 800
_RETRIEVAL_LIMIT = 5

# Identifiers that are genuinely patient-specific and must never reach the prompt.
# Weak fields (city, zip) are excluded: they can legitimately coincide with the
# practice's own address, which is part of the letterhead and intentionally sent.
_STRONG_IDENTIFIER_TOKENS = (
    "{{LAST_NAME}}",
    "{{FIRST_NAME}}",
    "{{BIRTH_DATE}}",
    "{{INSURANCE_NUMBER}}",
    "{{STREET}}",
    "{{PHONE}}",
    "{{EMAIL}}",
)


class PipelineGenerationError(PipelineError):
    """Raised when a letter could not be generated (letter row now status='failed')."""


def _format_birth_date(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y")
    return str(value).strip()


def _patient_context(patient: Any) -> dict[str, str]:
    if patient is None:
        return {}
    context = {
        "last_name": getattr(patient, "last_name", "") or "",
        "first_name": getattr(patient, "first_name", "") or "",
        "birth_date": _format_birth_date(getattr(patient, "birth_date", None)),
        "sex": getattr(patient, "sex", "") or "",
        "insurance": getattr(patient, "insurance", "") or "",
        "insurance_number": getattr(patient, "insurance_number", "") or "",
        "street": getattr(patient, "street", "") or "",
        "zip": getattr(patient, "zip", "") or "",
        "city": getattr(patient, "city", "") or "",
        "phone": getattr(patient, "phone", "") or "",
        "email": getattr(patient, "email", "") or "",
    }
    return {key: str(value).strip() for key, value in context.items() if str(value).strip()}


def _effective_letterhead(letterhead: dict | None, user: Any) -> dict:
    merged = dict(letterhead or {})
    for key in ("practice_name", "full_name", "street", "zip", "city", "phone", "email", "tax_id"):
        if not str(merged.get(key) or "").strip():
            value = getattr(user, key, "")
            if value:
                merged[key] = value
    return merged


def _custom_rules(user: Any) -> str:
    """Member's own writing rules (``letterhead_json['custom_rules']``), if any."""
    data = getattr(user, "letterhead_json", None) or {}
    if isinstance(data, dict):
        value = data.get("custom_rules")
        if isinstance(value, (list, tuple)):
            return "\n".join(str(item).strip() for item in value if str(item).strip())
        if value:
            return str(value).strip()
    return ""


def _error_message(exc: BaseException) -> str:
    """German-safe error string: no patient data, no provider payload, no key."""
    message = _GENERIC_ERROR
    status_code = getattr(exc, "status_code", None)
    if status_code:
        message += f" (Fehlercode {status_code})"
    return message


def _assert_prompt_is_pseudonymised(
    pseudonymizer: Pseudonymizer, prompt: str, settings: Any, *, ignore: str = ""
) -> None:
    """Enforce D4 in code: no raw identifier may appear in the outgoing prompt.

    Values that are also part of the practice's own letterhead (e.g. a practice named
    'Praxis Dr. Anna Beispiel' with a patient called Anna) are legitimately present in the
    prompt and are therefore excluded from the check.

    Guarded to non-production environments so an unforeseen false positive can never
    take down a live request; in dev/staging it fails loudly (AssertionError).
    """
    if getattr(settings, "env", "dev") == "prod":
        return
    haystack = prompt.lower()
    ignore = (ignore or "").lower()
    leaked = [
        value
        for value in pseudonymizer.sensitive_values(_STRONG_IDENTIFIER_TOKENS)
        if len(value) >= 3 and value in haystack and value not in ignore
    ]
    if leaked:
        # Never echo the leaked values themselves.
        raise AssertionError(
            f"pseudonymisation leak: {len(leaked)} raw identifier(s) present in the provider prompt"
        )


def _retrieval_query(masked_dictation: str) -> str:
    return (masked_dictation or "")[:_RETRIEVAL_QUERY_CHARS]


def _mark_failed(
    db: Any,
    *,
    letter_id: str,
    user_id: str,
    kind: str,
    exc: BaseException,
    model: str,
    diagnostics: dict | None = None,
) -> None:
    try:
        letter = db.get(Letter, letter_id)
        if letter is None:
            return
        letter.status = "failed"
        letter.error = _error_message(exc)
        db.add(letter)
        # Record the failed attempt for observability; quota is never touched here.
        # The Generation schema has no JSON column, so the (compact) diagnostics go
        # into ``error`` on failure only.
        error_detail = ""
        if diagnostics:
            try:
                error_detail = json.dumps(diagnostics, ensure_ascii=False, separators=(",", ":"))
            except (TypeError, ValueError):  # pragma: no cover - defensive
                error_detail = ""
        try:
            db.add(
                Generation(
                    user_id=user_id,
                    letter_id=letter_id,
                    provider=str(getattr(exc, "provider", "") or ""),
                    model=model,
                    tokens_in=0,
                    tokens_out=0,
                    cost_usd=0.0,
                    latency_ms=0,
                    status="error",
                    pseudonymised=True,
                    error=error_detail,
                )
            )
        except Exception:  # pragma: no cover - defensive
            logger.exception("could not record failed Generation row for letter %s", letter_id)
        db.commit()
        try:
            security.audit(
                db,
                event="letter.failed",
                user_id=user_id,
                target_type="letter",
                target_id=letter_id,
                kind=kind,
                error_type=type(exc).__name__,
                **(diagnostics or {}),
            )
        except Exception:  # pragma: no cover - audit must not mask the failure
            logger.exception("audit failed for failed letter %s", letter_id)
    except Exception:  # pragma: no cover - last-resort safety net
        db.rollback()
        logger.exception("could not mark letter %s as failed", letter_id)


def _short_findings_summary(check_result: Any) -> str:
    ids = ", ".join(dict.fromkeys(finding.rule_id for finding in check_result.hard))
    return f"Regelprüfung: {len(check_result.hard)} harte Hinweise ({ids})"[:400]


def _fanout_guard(pseudonymizer: Pseudonymizer, settings: Any):
    """Return a guard that verifies a compression/weave prompt carries MASKED text only.

    It extracts the patient-derived payload (the ``<segment>``/``<segment type=…>``
    bodies, which are the only patient-originated parts of a fan-out prompt) and applies
    the same leak + idempotency assertions as the single-pass path.
    """
    payload_re = re.compile(r"<segment[^>]*>(.*?)</segment>", re.DOTALL | re.IGNORECASE)

    def guard(_system: str, user: str) -> None:
        payload = "\n".join(payload_re.findall(user or ""))
        if not payload:
            return
        _assert_prompt_is_pseudonymised(pseudonymizer, payload, settings, ignore="")
        if pseudonymizer.mask(payload) != payload:
            raise AssertionError("pseudonymisation is not idempotent: raw identifiers survive masking")

    return guard


def _collect_enrichment(
    *,
    doc_type: str,
    masked_dictation: str,
    raw_patient_values: list[str],
    settings: Any,
    research_provider: Any,
    enrich_flag: bool,
    raw_patient_context: dict | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Run grounded enrichment and return ``(items, detail)``.

    Research is opt-in; if it is off, unavailable, or fails, the list is empty and the
    letter is still produced. Every kept statement passes the generic guardrail and is
    additionally checked against the patient's strong identifiers (defence in depth).
    """
    detail: dict[str, Any] = {
        "enabled": bool(enrich_flag),
        "web_available": bool(os.environ.get("BRIEFATO_RESEARCH_BASE_URL", "").strip()),
        "items": [],
        "sources": [],
        "blocked": 0,
        "ui_note": "",
    }
    if not enrich_flag:
        return [], detail

    provider = research_provider
    if provider is None:
        provider = get_research_provider(settings)
    if provider is None:
        detail["blocked"] = 0
        return [], detail

    try:
        raw_items = provider.enrich(
            doc_type=doc_type,
            context_text=masked_dictation or "",
            patient_context=dict(raw_patient_context or {}),
            dictation=masked_dictation or "",
            max_items=6,
        )
    except Exception:  # pragma: no cover - research must never break generation
        logger.exception("enrichment provider failed; continuing without reference knowledge")
        return [], detail

    kept, blocked = filter_generic(raw_items, dictation=masked_dictation or "")
    # Never surface a statement that carries a raw patient identifier.
    survivors = []
    for item in kept:
        statement = (getattr(item, "statement", "") or "").lower()
        if any(value and value in statement for value in raw_patient_values):
            blocked += 1
            continue
        survivors.append(item)

    detail["items"] = [item.as_dict() for item in survivors]
    detail["sources"] = sorted({str(getattr(item, "source", "")) for item in survivors if getattr(item, "source", "")})
    detail["blocked"] = blocked
    if survivors:
        detail["ui_note"] = "aus Referenz ergänzt – bitte prüfen"
    return survivors, detail


def _single_pass_document(
    *,
    doc_type: str,
    provider: Any,
    pseudonymizer: Pseudonymizer,
    masked_dictation: str,
    masked_context: dict,
    letterhead: dict,
    custom_rules: str,
    extra: str,
    settings: Any,
    hits: list,
    dictation: str,
    enrichment: list | None,
    tracker: fanout.ConcurrencyTracker,
) -> dict[str, Any]:
    """Generate one document in one pass, retrying once on hard rule violations."""
    ignore = " ".join(str(value) for value in letterhead.values())
    calls_before = tracker.calls

    def _call(prompt_extra: str):
        bundle = build_prompt(
            doc_type=doc_type,
            dictation=masked_dictation,
            letterhead=letterhead,
            patient_ctx=masked_context,
            templates=hits,
            custom_rules=custom_rules,
            extra=prompt_extra,
            enrichment=enrichment,
        )
        # The pseudonymisation guarantee concerns *patient-derived* text only: the masked dictation
        # and the masked patient context are the only patient-originated parts the model sees. The
        # letterhead and the retrieved templates legitimately contain words that can coincide with a
        # patient value (practice name; headings such as „Musterbrief"), so checking the whole
        # assembled prompt produced false positives that aborted real generations (2026-10-02).
        patient_payload = f"{masked_dictation}\n{json.dumps(masked_context, ensure_ascii=False)}"
        _assert_prompt_is_pseudonymised(pseudonymizer, patient_payload, settings, ignore=ignore)
        if pseudonymizer.mask(masked_dictation) != masked_dictation:
            # Defensive: masking must be idempotent, i.e. no raw identifier may survive it.
            raise AssertionError("pseudonymisation is not idempotent: raw identifiers survive masking")
        result = provider.generate(bundle.system, bundle.user)
        restored = pseudonymizer.restore(result.text)
        fixed, umlaut_fixes = autofix_umlauts(restored)
        reference = reference_support_text(hits, enrichment)
        return bundle, result, fixed, rule_check(
            fixed, doc_type, dictation, autofix=umlaut_fixes, reference=reference
        )

    bundle, result, text, check_result = _call(extra)
    retried = False
    if check_result.hard:
        retried = True
        correction = correction_block(check_result.correction_instructions())
        retry_extra = (extra + "\n\n" + correction).strip()
        try:
            bundle2, result2, text2, check2 = _call(retry_extra)
        except Exception:  # pragma: no cover - keep the first draft if the retry dies
            logger.exception("rule-check retry failed for doc_type=%s", doc_type)
        else:
            # Prefer the retry only if it does not introduce *more* hard violations.
            if len(check2.hard) <= len(check_result.hard):
                bundle, result, text, check_result = bundle2, result2, text2, check2

    return {
        "doc_type": doc_type,
        "text": text,
        "result": result,
        "bundle": bundle,
        "check": check_result,
        "retried": retried,
        "route": None,
        "compression": None,
        "calls": tracker.calls - calls_before,
    }


def _fanout_document(
    *,
    doc_type: str,
    provider: Any,
    pseudonymizer: Pseudonymizer,
    masked_dictation: str,
    masked_context: dict,
    letterhead: dict,
    custom_rules: str,
    extra: str,
    settings: Any,
    hits: list,
    dictation: str,
    segments: list,
    route: routing.RouteDecision,
    max_parallel: int,
    enrichment: list | None,
    tracker: fanout.ConcurrencyTracker,
) -> dict[str, Any]:
    """Segment → bounded-parallel compression → one weave (then the existing retry)."""
    calls_before = tracker.calls
    guard = _fanout_guard(pseudonymizer, settings)
    ignore = " ".join(str(value) for value in letterhead.values())

    compressed, stats = fanout.compress_segments(
        segments,
        provider=provider,
        doc_type=doc_type,
        tracker=tracker,
        max_parallel=max_parallel,
        guard=guard,
        enrichment=enrichment,
    )

    def _guard_weave(_system: str, user: str) -> None:
        payload = "\n".join(re.findall(r"<segment[^>]*>(.*?)</segment>", user or "", re.DOTALL | re.IGNORECASE))
        patient_payload = f"{payload}\n{json.dumps(masked_context, ensure_ascii=False)}"
        _assert_prompt_is_pseudonymised(pseudonymizer, patient_payload, settings, ignore=ignore)

    weave = fanout.run_weave(
        doc_type=doc_type,
        compressed=compressed,
        provider=provider,
        pseudonymizer=pseudonymizer,
        letterhead=letterhead,
        patient_ctx=masked_context,
        templates=hits,
        custom_rules=custom_rules,
        enrichment=enrichment,
        extra=extra,
        guard=_guard_weave,
        dictation=dictation,
    )
    weave["route"] = route
    weave["compression"] = stats
    weave["compressed"] = compressed
    weave["calls"] = tracker.calls - calls_before
    return weave


def _generate_document(
    *,
    doc_type: str,
    provider: Any,
    pseudonymizer: Pseudonymizer,
    masked_dictation: str,
    masked_context: dict,
    letterhead: dict,
    custom_rules: str,
    extra: str,
    settings: Any,
    hits: list,
    dictation: str,
    segments: list,
    route: routing.RouteDecision,
    max_parallel: int,
    enrichment: list | None,
    tracker: fanout.ConcurrencyTracker,
) -> dict[str, Any]:
    """Dispatch one document to the fan-out or the single-pass pipeline."""
    if route is not None and route.is_fanout:
        return _fanout_document(
            doc_type=doc_type,
            provider=provider,
            pseudonymizer=pseudonymizer,
            masked_dictation=masked_dictation,
            masked_context=masked_context,
            letterhead=letterhead,
            custom_rules=custom_rules,
            extra=extra,
            settings=settings,
            hits=hits,
            dictation=dictation,
            segments=segments,
            route=route,
            max_parallel=max_parallel,
            enrichment=enrichment,
            tracker=tracker,
        )
    return _single_pass_document(
        doc_type=doc_type,
        provider=provider,
        pseudonymizer=pseudonymizer,
        masked_dictation=masked_dictation,
        masked_context=masked_context,
        letterhead=letterhead,
        custom_rules=custom_rules,
        extra=extra,
        settings=settings,
        hits=hits,
        dictation=dictation,
        enrichment=enrichment,
        tracker=tracker,
    )


def generate_letter(
    db,
    *,
    user,
    patient,
    kind: str,
    dictation: str,
    letterhead: dict,
    extra: str = "",
    enrich: bool | None = None,
    max_parallel: int | None = None,
    research_provider: Any = None,
) -> Letter:
    settings = get_settings()

    # Routing inputs (WORKSTREAM-ENGINE-V2): the source segmentation and the concurrency
    # cap are computed once per letter; the >5-source fan-out rule is evaluated per
    # document type from the segment count.
    segments = segmenter.segment(dictation or "")
    max_parallel_cap = fanout.resolve_max_parallel(max_parallel)
    tracker = fanout.ConcurrencyTracker(max_parallel_cap)

    # 1) triage — Auftragsart -> Dokumenttyp (kern.md routing)
    decision = brain_triage.triage(dictation or "", explicit=kind, source_count=len(segments))
    doc_types = decision.doc_types
    doc_type = decision.doc_type

    label = brain_loader.DOKUMENTTYP_LABELS.get(doc_type, doc_type)
    patient_name = ""
    if patient is not None:
        patient_name = (
            (getattr(patient, "last_name", "") or "").strip()
            or (getattr(patient, "first_name", "") or "").strip()
        )
    if len(doc_types) > 1:
        combined_label = " + ".join(brain_loader.DOKUMENTTYP_LABELS.get(t, t) for t in doc_types)
        title = f"{combined_label} {patient_name}".strip()[:200]
    else:
        title = f"{label} {patient_name}".strip()[:200] or label

    letter = Letter(
        user_id=user.id,
        patient_id=getattr(patient, "id", None),
        kind=doc_type,
        status="generating",
        title=title,
        dictation_enc=security.encrypt_field(dictation or ""),
        language=(getattr(user, "ui_lang", None) or settings.ui_lang),
        model=settings.llm_model,
    )
    db.add(letter)
    db.commit()
    db.refresh(letter)

    # Diagnostics carried into the audit + failure Generation row. No patient data.
    diagnostics: dict[str, Any] = {
        "doc_type": doc_type,
        "doc_types": list(doc_types),
        "triage_confidence": decision.confidence,
        "prompt_version": PROMPT_VERSION,
        "source_count": len(segments),
    }

    try:
        pseudonymizer = Pseudonymizer.from_patient(patient)
        masked_dictation = pseudonymizer.mask(dictation or "")
        raw_patient_context = _patient_context(patient)
        masked_context = {
            key: pseudonymizer.mask(value) for key, value in raw_patient_context.items()
        }
        effective_letterhead = _effective_letterhead(letterhead, user)
        member_rules = _custom_rules(user)

        hits = retrieval.retrieve(_retrieval_query(masked_dictation), limit=_RETRIEVAL_LIMIT)
        diagnostics["templates"] = [
            {"file": hit.file, "score": hit.score, "reference_only": hit.reference_only}
            for hit in hits
        ]

        # Grounded enrichment ('Improvisation') — per-request opt-in, default from the
        # BRIEFATO_ENRICH_DEFAULT setting. Off/unavailable/failed → empty list.
        enrich_flag = enrich_default() if enrich is None else bool(enrich)
        enrichments, enrichment_detail = _collect_enrichment(
            doc_type=doc_type,
            masked_dictation=masked_dictation,
            raw_patient_values=pseudonymizer.sensitive_values(_STRONG_IDENTIFIER_TOKENS),
            settings=settings,
            research_provider=research_provider,
            enrich_flag=enrich_flag,
            raw_patient_context=raw_patient_context,
        )
        diagnostics["enrichment_sources"] = enrichment_detail.get("sources", [])
        diagnostics["enrichment_blocked"] = enrichment_detail.get("blocked", 0)

        provider = fanout.TrackedProvider(get_provider(settings), tracker)

        documents: list[dict[str, Any]] = []
        routes: list[dict[str, Any]] = []
        for current_type in doc_types:
            route = routing.decide_route(current_type, len(segments))
            routes.append(route.as_dict())
            documents.append(
                _generate_document(
                    doc_type=current_type,
                    provider=provider,
                    pseudonymizer=pseudonymizer,
                    masked_dictation=masked_dictation,
                    masked_context=masked_context,
                    letterhead=effective_letterhead,
                    custom_rules=member_rules,
                    extra=extra or "",
                    settings=settings,
                    hits=hits,
                    dictation=dictation or "",
                    segments=segments,
                    route=route,
                    max_parallel=max_parallel_cap,
                    enrichment=enrichments,
                    tracker=tracker,
                )
            )
        diagnostics["routing"] = routes

        content = "\n\n".join(document["text"] for document in documents)

        # Aggregate token/cost accounting across every provider call.
        tokens_in = sum(int(d["result"].tokens_in or 0) for d in documents)
        tokens_out = sum(int(d["result"].tokens_out or 0) for d in documents)
        cost_usd = sum(float(d["result"].cost_usd or 0.0) for d in documents)
        latency_ms = sum(int(d["result"].latency_ms or 0) for d in documents)
        last_result = documents[-1]["result"]

        all_findings = [finding for d in documents for finding in d["check"].findings]
        hard_findings = [finding for d in documents for finding in d["check"].hard]
        retried = any(d["retried"] for d in documents)
        checks = [
            {
                "doc_type": d["doc_type"],
                "ok": d["check"].ok,
                "summary": d["check"].summary,
                "findings": [finding.as_dict() for finding in d["check"].findings],
            }
            for d in documents
        ]

        letter.content_enc = security.encrypt_field(content)
        letter.tokens_in = tokens_in
        letter.tokens_out = tokens_out
        letter.cost_usd = cost_usd
        letter.model = last_result.model or settings.llm_model
        letter.status = "done"
        if hard_findings:
            # Short summary only in the Letter row; the detail lives in last_check/audit.
            letter.error = _short_findings_summary(documents[0]["check"] if len(documents) == 1 else _CombinedCheck(hard_findings))
        else:
            letter.error = ""
        db.add(letter)

        db.add(
            Generation(
                user_id=user.id,
                letter_id=letter.id,
                provider=last_result.provider,
                model=letter.model,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status="ok",
                pseudonymised=True,
                error="",
            )
        )

        subscription = db.scalar(select(Subscription).where(Subscription.user_id == user.id))
        if subscription is not None:
            subscription.letters_used = int(subscription.letters_used or 0) + 1

        db.commit()

        # Runtime detail for the UI — no schema change (see module docstring).
        compression = [d.get("compression") for d in documents if d.get("compression")]
        route_primary = routes[0] if routes else None
        letter.last_check = {
            "doc_type": doc_type,
            "doc_types": list(doc_types),
            "triage": decision.as_dict(),
            "templates": diagnostics.get("templates", []),
            "reference_only": [hit.file for hit in hits if hit.reference_only],
            "prompt_version": PROMPT_VERSION,
            "checks": checks,
            "hard_count": len(hard_findings),
            "soft_count": len(all_findings) - len(hard_findings),
            "retried": retried,
            # --- fan-out / routing (WORKSTREAM-ENGINE-V2) ---
            "route": route_primary,
            "routing": routes,
            "source_count": len(segments),
            "segments": segmenter.segment_as_dicts(segments),
            "compression": compression,
            "max_parallel": max_parallel_cap,
            "model_calls": tracker.calls,
            "max_concurrency": tracker.peak,
            # --- grounded enrichment ('Improvisation') ---
            "enrichment": enrichment_detail,
        }
        # Runtime attributes for the UI (no schema change), consumed by the wizard/editor:
        # the enrichment list (statement + source) and the routing label.
        letter.enrichments = [
            {
                "text": item.get("statement", ""),
                "source": item.get("source", ""),
                "kind": item.get("kind", ""),
                "origin": item.get("origin", ""),
            }
            for item in enrichment_detail.get("items", [])
        ]
        letter.route_label = route_primary["ui_label"] if route_primary else ""
    except Exception as exc:
        db.rollback()
        logger.exception("letter generation failed letter_id=%s kind=%s", letter.id, kind)
        _mark_failed(
            db,
            letter_id=letter.id,
            user_id=user.id,
            kind=kind,
            exc=exc,
            model=settings.llm_model,
            diagnostics=diagnostics,
        )
        raise PipelineGenerationError(_error_message(exc)) from exc

    # Success audit is best-effort: the letter is already committed as done.
    try:
        security.audit(
            db,
            event="letter.generated",
            user_id=user.id,
            target_type="letter",
            target_id=letter.id,
            kind=doc_type,
            doc_types=list(doc_types),
            templates=[
                hit.file for hit in hits
            ][:10],
            retrieval_scores={hit.file: hit.score for hit in hits[:10]},
            findings=[finding.as_dict() for finding in all_findings][:40],
            hard_count=len(hard_findings),
            soft_count=len(all_findings) - len(hard_findings),
            retried=retried,
            model=letter.model,
            tokens_in=letter.tokens_in,
            tokens_out=letter.tokens_out,
            cost_usd=letter.cost_usd,
            pseudonymised=True,
            route=routes[0]["route"] if routes else None,
            source_count=len(segments),
            model_calls=tracker.calls,
            max_concurrency=tracker.peak,
            max_parallel=max_parallel_cap,
            compression_gaps=[
                gap.get("type")
                for document in documents
                for gap in ((document.get("compression") or {}).get("gaps") or [])
            ],
            enrichment_sources=enrichment_detail.get("sources", []),
            enrichment_blocked=enrichment_detail.get("blocked", 0),
        )
    except Exception:  # pragma: no cover - audit failure must not fail the letter
        logger.exception("audit failed for letter %s", letter.id)

    # Enrichment audit (separate event) — only when reference knowledge was actually used.
    if enrichment_detail.get("items"):
        try:
            security.audit(
                db,
                event="letter.enriched",
                user_id=user.id,
                target_type="letter",
                target_id=letter.id,
                kind=doc_type,
                sources=enrichment_detail.get("sources", []),
                kinds=sorted(
                    {str(item.get("kind", "")) for item in enrichment_detail["items"] if item.get("kind")}
                ),
                statement_count=len(enrichment_detail["items"]),
                blocked=enrichment_detail.get("blocked", 0),
                web_used=any(
                    str(item.get("origin", "")) == "web" for item in enrichment_detail["items"]
                ),
                ui_note=enrichment_detail.get("ui_note", ""),
            )
        except Exception:  # pragma: no cover - audit failure must not fail the letter
            logger.exception("enrichment audit failed for letter %s", letter.id)

    return letter


class _CombinedCheck:
    """Tiny adapter so :func:`_short_findings_summary` can accept merged findings."""

    def __init__(self, hard: list) -> None:
        self.hard = hard


__all__ = ["generate_letter", "render_docx", "PipelineGenerationError"]
