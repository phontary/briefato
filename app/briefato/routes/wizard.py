"""Sequential, document-type-dependent letter wizard (``/app/neu``).

WORKSTREAM-PORTAL. The wizard asks exactly one question per step, fades between steps,
never generates anything before the member confirms the summary, and ends on the plain-text
result with the primary "Text kopieren" action.

State model (documented decision)
---------------------------------
The wizard carries its whole state in a single hidden field (``wiz_state``, JSON) that is
re-posted with every step. Widgets only carry the *current* step's answer; the route merges
them into the JSON state before moving on. This keeps "back without data loss" true for free
(going back re-renders the previous step's widgets from the JSON), needs no session store and
no schema change, and keeps the strict CSP intact (no inline scripts). The state never leaves
the member: foreign patient/letter ids in it are validated against the tenant and yield 404.

Transitions: ``GET`` renders the first question; every step is a ``POST`` to ``/app/neu``.
The last step is the summary; only its confirm form posts to ``/app/neu/erzeugen`` — that is
the single route that can create a letter. The result is rendered by ``GET
/app/neu/ergebnis/{letter_id}`` and, right after generation, inline so that runtime-only
enrichments returned by the pipeline are still available (the frozen schema has no column to
persist them).
"""

from __future__ import annotations

import inspect
import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from ..models import Letter, Patient, new_id
from ..pipeline import generate as pipeline_generate
from ..security import audit, decrypt_field, encrypt_field
from . import brain_bridge
from .deps import (
    CSRF,
    DB,
    CurrentUser,
    get_letter_or_404,
    get_patient_or_404,
    render,
)
from .letters import _letter_ids, _fold_pipeline_letters, _quota

router = APIRouter(prefix="/app", tags=["neu"])

_GENERIC_GENERATE_ERROR = (
    "Der Text konnte nicht erzeugt werden. Bitte prüfen Sie die Angaben und versuchen Sie es erneut."
)
_PIPELINE_GENERATION_ERROR = getattr(pipeline_generate, "PipelineGenerationError", None)

# Label dropdown for the repeating "Quelle hinzufügen" control.
SOURCE_LABELS = (
    "CT",
    "MRT",
    "Röntgen",
    "Sono",
    "Echo",
    "ÖGD",
    "Kolo",
    "Endosonografie",
    "OP-Bericht",
    "Pathologie",
    "Diabetologie",
    "Pflegebericht",
    "Visite",
    "Sonstiges",
)

# The nine cards of step 1. ``doc_type`` is the brain document type handed to the pipeline;
# ``letter_kind`` stays inside the frozen ``letters.kind`` vocabulary (String(20)).
WIZARD_CARDS: tuple[dict[str, str], ...] = (
    {
        "key": "aufnahmebogen",
        "doc_type": "arztbrief",
        "letter_kind": "arztbrief",
        "label": "Aufnahmebogen",
        "desc": "Stationäre Aufnahme: Anamnese, KU und Aufnahmegrund, wenn der Verlauf weiterläuft.",
    },
    {
        "key": "entlassbrief",
        "doc_type": "arztbrief",
        "letter_kind": "arztbrief",
        "label": "Stationärer Entlassbrief",
        "desc": "Mehrtägiger stationärer Aufenthalt, der mit der Entlassung endet.",
    },
    {
        "key": "verlegungsbericht",
        "doc_type": "arztbrief",
        "letter_kind": "arztbrief",
        "label": "Verlegungsbericht",
        "desc": "Übernahme in eine andere Abteilung oder Klinik — mit Verlegungssatz.",
    },
    {
        "key": "ambulant",
        "doc_type": "ambulant",
        "letter_kind": "arztbrief",
        "label": "Ambulanter Brief",
        "desc": "Sprechstunde oder Notaufnahme ohne stationäre Aufnahme, auch am OP-Tag entlassen.",
    },
    {
        "key": "operationsbericht",
        "doc_type": "operationsbericht",
        "label": "OP-Bericht",
        "letter_kind": "arztbrief",
        "desc": "Ausführliche Schritt-für-Schritt-Darstellung einer Operation.",
    },
    {
        "key": "zusammenfassung",
        "doc_type": "zusammenfassung",
        "letter_kind": "arztbrief",
        "label": "Zusammenfassung",
        "desc": "Kurze Verdichtung eines Verlaufs — ohne Diagnoseliste.",
    },
    {
        "key": "entlassmedikationsplan",
        "doc_type": "entlassmedikationsplan",
        "letter_kind": "sonstiges",
        "label": "Entlassmedikationsplan",
        "desc": "Medikationsplan für die Entlassung anpassen: geänderte Zeilen alt → neu.",
    },
    {
        "key": "pflegebericht",
        "doc_type": "pflegebericht",
        "letter_kind": "arztbrief",
        "label": "Pflegebericht-Integration",
        "desc": "Pflegeberichte als Quellmaterial in den klinischen Verlauf einweben.",
    },
    {
        "key": "ablehnungsbogen",
        "doc_type": "ablehnungsbogen",
        "letter_kind": "sonstiges",
        "label": "Ablehnungsbogen",
        "desc": "Ablehnung einer Maßnahme gegen ärztlichen Rat (Thieme Compliance, Dok 1).",
    },
)

_CARD_BY_KEY: dict[str, dict[str, str]] = {card["key"]: card for card in WIZARD_CARDS}

_TYPE_STEP: dict[str, Any] = {
    "key": "typ",
    "render": "cards",
    "title": "Was möchten Sie schreiben?",
    "help": "Wählen Sie die Dokumentart. Die nächsten Fragen richten sich danach.",
    "fields": [],
}

_SUMMARY_STEP: dict[str, Any] = {
    "key": "pruefen",
    "render": "summary",
    "title": "Alles bereit?",
    "help": "Prüfen Sie Typ, Patient/in und Quellen. Erst nach Ihrer Bestätigung wird der Text erzeugt.",
    "fields": [],
}


def _f(
    name: str,
    label: str,
    ftype: str = "text",
    *,
    required: bool = False,
    rows: int = 6,
    placeholder: str = "",
    hint: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "type": ftype,
        "required": required,
        "rows": rows,
        "placeholder": placeholder,
        "hint": hint,
        "value": "",
    }


_PATIENT_FIELD = _f("patient_id", "Patient/in", "select", required=True)
_PATIENT_FIELD["source"] = "patients"


def _patient_step() -> dict[str, Any]:
    return {
        "key": "patient",
        "render": "fields",
        "title": "Für welche Patientin oder welchen Patienten ist das Dokument?",
        "help": "Dokumente werden immer einer Patientin oder einem Patienten zugeordnet.",
        "fields": [dict(_PATIENT_FIELD)],
    }


def _sources_step() -> dict[str, Any]:
    return {
        "key": "quellen",
        "render": "sources",
        "title": "Welche Quellen und Befunde liegen vor?",
        "help": "Fügen Sie das Rohmaterial einzeln hinzu — Befund, Bildgebung, Labor oder Verlauf. "
        "Ab 6 Quellen teilt die Erzeugung die Quellen automatisch auf.",
        "fields": [],
    }


def build_steps(card_key: str) -> list[dict[str, Any]]:
    """The type-dependent steps (everything after step 1), ending with the summary."""
    if card_key in ("aufnahmebogen", "entlassbrief", "verlegungsbericht"):
        steps = [
            _patient_step(),
            {
                "key": "anamnese",
                "render": "fields",
                "title": "Aufnahme-Anamnese und Aufnahmebefund (KU)",
                "help": "Die Anamnese wird auf zwei Sätze verdichtet, die KU auf den diagnoseführenden "
                "Befund plus wegweisende Ausschlussbefunde.",
                "fields": [
                    _f(
                        "anamnese",
                        "Aufnahme-Anamnese",
                        "textarea",
                        rows=6,
                        hint="Vorstellungsweg, Beschwerden, Dauer, Vorbehandlung, Aufnahmegrund.",
                    ),
                    _f(
                        "ku",
                        "Körperliche Untersuchung (KU)",
                        "textarea",
                        rows=5,
                        hint="Nur diagnoseführender Befund und wegweisende Ausschlussbefunde.",
                    ),
                ],
            },
        ]
        if card_key == "verlegungsbericht":
            steps.append(
                {
                    "key": "zielklinik",
                    "render": "fields",
                    "title": "In welche Klinik oder Abteilung wurde verlegt?",
                    "help": "Freiwillig. Bleibt das Feld leer, setzt der Text den Platzhalter XXX ein.",
                    "fields": [
                        _f(
                            "zielklinik",
                            "Zielklinik / Abteilung",
                            "text",
                            hint="Leer lassen, wenn unbekannt — wird als XXX eingesetzt.",
                        )
                    ],
                }
            )
        steps.append(_sources_step())
        steps.append(dict(_SUMMARY_STEP))
        return steps

    if card_key == "ambulant":
        return [
            _patient_step(),
            {
                "key": "kontext",
                "render": "fields",
                "title": "Wie war der Aufnahme- und Entlasskontext?",
                "help": "Vorstellung, Indikation und wann die Entlassung erfolgte (ohne stationäre Aufnahme).",
                "fields": [
                    _f("kontext", "Aufnahme-/Entlasskontext", "textarea", rows=6)
                ],
            },
            {
                "key": "befund",
                "render": "fields",
                "title": "Welcher Befund und welche Maßnahme wurden dokumentiert?",
                "help": "KU/Befund, durchgeführte Maßnahme bzw. OP-Absatz und die empfohlene Nachsorge.",
                "fields": [_f("befund", "Befund und Maßnahme", "textarea", rows=7)],
            },
            _sources_step(),
            dict(_SUMMARY_STEP),
        ]

    if card_key == "operationsbericht":
        return [
            _patient_step(),
            {
                "key": "op_datum",
                "render": "fields",
                "title": "Wann wurde operiert?",
                "help": "Das OP-Datum wird in der Indikation genannt.",
                "fields": [_f("op_datum", "OP-Datum", "date")],
            },
            {
                "key": "indikation",
                "render": "fields",
                "title": "Warum wurde operiert (Indikation)?",
                "help": "Beschwerdebild/Diagnose und die Begründung des Eingriffs, in einem Absatz.",
                "fields": [_f("indikation", "Indikation", "textarea", rows=5)],
            },
            {
                "key": "zugang_kernbefund",
                "render": "fields",
                "title": "Welcher Zugang und welcher Kernbefund?",
                "help": "Zugang/Technik und der entscheidende intraoperative Befund.",
                "fields": [
                    _f("zugang", "Zugang", "text", placeholder="z. B. laparoskopisch, transumbilikaler Zugang"),
                    _f("kernbefund", "Kernbefund", "textarea", rows=5),
                ],
            },
            {
                "key": "massnahmen",
                "render": "fields",
                "title": "Welche Maßnahmen wurden durchgeführt?",
                "help": "Der Kernschritt und die wesentlichen weiteren Maßnahmen.",
                "fields": [_f("massnahmen", "Maßnahmen", "textarea", rows=5)],
            },
            {
                "key": "drainagen",
                "render": "fields",
                "title": "Drainagen und Standarddetails",
                "help": "Drainagen werden knapp benannt. Standarddetails können aus der Referenz ergänzt werden.",
                "fields": [
                    _f("drainagen", "Drainagen", "text", placeholder="z. B. Lasche Unterbauch rechts, entfernt am 2. Tag"),
                    _f(
                        "standarddetails",
                        "Standarddetails aus Referenz ergänzen",
                        "checkbox",
                        hint="Desinfektion, sterile Abdeckung, Team-Time-out, Wundverschluss werden ergänzt, "
                        "wenn sie nicht dokumentiert sind.",
                    ),
                ],
            },
            _sources_step(),
            dict(_SUMMARY_STEP),
        ]

    if card_key == "zusammenfassung":
        return [
            _patient_step(),
            {
                "key": "verdichtung",
                "render": "fields",
                "title": "Welchen Verlauf soll die Zusammenfassung verdichten?",
                "help": "Ohne Vorgabe entstehen 3–4 Sätze, chronologisch, ohne Diagnoseliste.",
                "fields": [
                    _f(
                        "verlauf",
                        "Verlauf / Rohmaterial",
                        "textarea",
                        rows=10,
                        hint="Ein Verlauf über mehrere Episoden, oder ein einzelnes OP-Diktat.",
                    )
                ],
            },
            dict(_SUMMARY_STEP),
        ]

    if card_key == "entlassmedikationsplan":
        return [
            _patient_step(),
            {
                "key": "plan",
                "render": "fields",
                "title": "Wie lautet der aktuelle Medikationsplan?",
                "help": "Fügen Sie den Plan ein, wie er vorliegt (KIS, Ausdruck oder kopierter Text).",
                "fields": [_f("medikationsplan", "Aktueller Medikationsplan", "textarea", rows=10)],
            },
            {
                "key": "aenderungen",
                "render": "fields",
                "title": "Was hat sich geändert?",
                "help": "Die anzupassenden Zeilen alt → neu und die Begründung, soweit dokumentiert.",
                "fields": [_f("aenderungen", "Änderungen", "textarea", rows=6)],
            },
            dict(_SUMMARY_STEP),
        ]

    if card_key == "pflegebericht":
        return [
            _patient_step(),
            {
                "key": "pflege",
                "render": "fields",
                "title": "Bitte geben Sie die Pflegeberichte ein.",
                "help": "Nur klinisch relevante Beobachtungen werden übernommen (Wunde, Stuhlgang, "
                "Bilanz, Schmerz, Mobilisation, besondere Vorkommnisse).",
                "fields": [_f("pflegeberichte", "Pflegeberichte", "textarea", rows=10)],
            },
            {
                "key": "klinik",
                "render": "fields",
                "title": "Wie ist der klinische Verlauf?",
                "help": "Der Rahmen, in den die Pflegebeobachtungen eingewoben werden.",
                "fields": [_f("pflege_klinik", "Klinischer Verlauf", "textarea", rows=8)],
            },
            dict(_SUMMARY_STEP),
        ]

    if card_key == "ablehnungsbogen":
        return [
            _patient_step(),
            {
                "key": "ablehnung",
                "render": "fields",
                "title": "Welche Maßnahme wurde abgelehnt?",
                "help": "Die abgelehnte Maßnahme konkret und mit Diagnosebezug benennen.",
                "fields": [_f("abgelehnte_massnahme", "Abgelehnte Maßnahme und Diagnose", "textarea", rows=6)],
            },
            {
                "key": "begruendung",
                "render": "fields",
                "title": "Wie dringlich ist die Maßnahme und warum?",
                "help": "Dringlichkeit, Begründung und die möglichen Komplikationen bei Ablehnung.",
                "fields": [_f("dringlichkeit", "Dringlichkeit und Begründung", "textarea", rows=8)],
            },
            dict(_SUMMARY_STEP),
        ]

    return [_patient_step(), dict(_SUMMARY_STEP)]


# --------------------------------------------------------------------------- helpers


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _parse_state(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, str) or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _state_json(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False, separators=(",", ":"))


def _flow(card: dict[str, str] | None) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [dict(_TYPE_STEP)]
    if card is not None:
        steps.extend(build_steps(card["key"]))
    return steps


def _patient_for(db, user, state: dict[str, Any]) -> Patient | None:
    patient_id = str(state.get("patient_id") or "").strip()
    if not patient_id:
        return None
    return db.scalar(select(Patient).where(Patient.id == patient_id, Patient.user_id == user.id))


def _summary_rows(card: dict[str, str], steps: list[dict[str, Any]], state: dict[str, Any],
                  patient: Patient | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = [
        {"label": "Dokumenttyp", "value": card["label"]},
        {"label": "Patient/in", "value": patient.display_name if patient else "—"},
    ]
    for step in steps:
        for field in step.get("fields", []):
            if field.get("type") == "select":
                continue
            value = str(state.get(field["name"]) or "").strip()
            if value:
                if field.get("type") == "checkbox":
                    value = "Ja"
                rows.append({"label": field["label"], "value": value})
    sources = list(state.get("sources") or [])
    rows.append({"label": "Quellen", "value": str(len(sources))})
    return rows


def _compose_preamble(card: dict[str, str]) -> str:
    if card["key"] == "entlassbrief":
        return "Auftrag: stationärer Entlassbrief."
    if card["key"] == "aufnahmebogen":
        return "Auftrag: stationärer Aufnahmebrief."
    if card["key"] == "verlegungsbericht":
        return "Auftrag: Verlegungsbericht."
    return f"Auftrag: {card['label']}."


def _compose_dictation(card: dict[str, str], steps: list[dict[str, Any]], state: dict[str, Any]) -> str:
    """Compose the source-stack dictation the pipeline segments and fan-outs on.

    Answers and sources are emitted as ``Label:\\n<text>`` blocks: the pipeline's segmenter
    reads each block as one source (it recognises the German headings), and the >5-source
    fan-out is driven by the resulting segment count.
    """
    parts = [_compose_preamble(card)]
    for step in steps:
        for field in step.get("fields", []):
            if field.get("type") == "checkbox":
                if state.get(field["name"]):
                    parts.append(f"{field['label']}: ja")
                continue
            value = str(state.get(field["name"]) or "").strip()
            if value:
                parts.append(f"{field['label']}:\n{value}")
    for source in state.get("sources") or []:
        label = str(source.get("label") or "Sonstiges").strip() or "Sonstiges"
        text = str(source.get("text") or "").strip()
        if text:
            parts.append(f"{label}:\n{text}")
    return "\n\n".join(parts)


def _structured(card: dict[str, str], steps: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    answers: dict[str, str] = {}
    for step in steps:
        for field in step.get("fields", []):
            if field.get("type") == "select":
                continue
            value = str(state.get(field["name"]) or "").strip()
            if value:
                answers[field["name"]] = value
    return {
        "wizard": card["key"],
        "doc_type": card["doc_type"],
        "answers": answers,
        "sources": [
            {"label": str(s.get("label") or "Sonstiges"), "text": str(s.get("text") or "")}
            for s in (state.get("sources") or [])
        ],
    }


def _call_pipeline(db, user, patient, card, dictation, letterhead, extra_text, structured, *,
                   enrich: bool | None = None):
    """Call the frozen ``generate_letter`` and pass fan-out/enrichment kwargs only when the
    pipeline's signature actually accepts them (the parallel workstream extends it)."""
    function = pipeline_generate.generate_letter
    try:
        parameters = inspect.signature(function).parameters
    except (TypeError, ValueError):
        parameters = {}

    kwargs: dict[str, Any] = {
        "user": user,
        "patient": patient,
        "kind": card["doc_type"],
        "dictation": dictation,
        "letterhead": letterhead,
    }
    if not parameters or "extra" in parameters:
        kwargs["extra"] = extra_text
    accepts_var_kwargs = bool(parameters) and any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    optional = {
        "sources": structured["sources"],
        "structured": structured,
        "doc_type": card["doc_type"],
        "wizard": structured,
        "enrich": enrich,
    }
    if parameters:
        for key, value in optional.items():
            if (key in parameters or accepts_var_kwargs) and value is not None:
                kwargs[key] = value

    try:
        return function(db, **kwargs)
    except TypeError as exc:
        # Only fall back when the *signature* rejected one of our optional keywords — never
        # mask a genuine TypeError raised inside the pipeline.
        message = str(exc)
        if "unexpected keyword" in message or "positional argument" in message:
            return function(
                db,
                user=user,
                patient=patient,
                kind=card["doc_type"],
                dictation=dictation,
                letterhead=letterhead,
                extra=extra_text,
            )
        raise


def _pipeline_error_message(exc: BaseException) -> str:
    if _PIPELINE_GENERATION_ERROR is not None and isinstance(exc, _PIPELINE_GENERATION_ERROR):
        text = str(exc).strip()
        if text:
            return text
    return _GENERIC_GENERATE_ERROR


def _normalise_enrichments(raw: Any) -> list[dict[str, str]]:
    """Accept dataclasses / dicts / tuples from the pipeline and flatten to {text, source}."""
    if raw is None:
        return []
    if isinstance(raw, dict):
        for key in ("enrichments", "ergaenzungen", "added", "items"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            return []
    out: list[dict[str, str]] = []
    for item in raw or []:
        if hasattr(item, "as_dict"):
            item = item.as_dict()
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("content") or item.get("label") or "").strip()
            source = str(
                item.get("source") or item.get("file") or item.get("template")
                or item.get("title") or item.get("reference") or ""
            ).strip()
        elif isinstance(item, (tuple, list)):
            text = str(item[0]).strip() if item else ""
            source = str(item[1]).strip() if len(item) > 1 else ""
        else:
            text, source = str(item).strip(), ""
        if text:
            out.append({"text": text, "source": source})
    return out


def _read_enrichments(result: Any, letter: Letter) -> list[dict[str, str]]:
    for obj in (result, letter):
        if obj is None:
            continue
        found = _normalise_enrichments(getattr(obj, "enrichments", None))
        if found:
            return found
        last_check = getattr(obj, "last_check", None)
        if isinstance(last_check, dict):
            found = _normalise_enrichments(last_check.get("enrichments"))
            if found:
                return found
    return []


# --------------------------------------------------------------------------- rendering


def _wizard_response(
    request: Request,
    db,
    user,
    state: dict[str, Any],
    *,
    error: str | None = None,
    status_code: int = 200,
):
    card = _CARD_BY_KEY.get(str(state.get("wtype") or ""))
    steps = build_steps(card["key"]) if card is not None else []
    flow = _flow(card)
    step_index = max(0, min(_int(state.get("step"), 0), len(flow) - 1))
    step = flow[step_index]

    if step.get("render") == "fields":
        for field in step["fields"]:
            field["value"] = state.get(field["name"], "")

    is_summary = step.get("render") == "summary"
    if is_summary:
        state["at_summary"] = True
    else:
        state.pop("at_summary", None)
    state["step"] = step_index

    patients = db.scalars(
        select(Patient)
        .where(Patient.user_id == user.id, Patient.archived_at.is_(None))
        .order_by(Patient.last_name, Patient.first_name)
    ).all()
    sources = list(state.get("sources") or [])
    summary = (
        _summary_rows(card, steps, state, _patient_for(db, user, state))
        if (is_summary and card is not None)
        else []
    )

    return render(
        request,
        "app/neu.html",
        status_code=status_code,
        active="briefe",
        crumbs=[("Übersicht", "/app"), ("Briefe", "/app/briefe"), ("Neu", None)],
        card=card,
        wizard_cards=list(WIZARD_CARDS),
        patients=patients,
        step=step,
        step_index=step_index,
        step_no=step_index + 1,
        step_total=len(flow),
        show_progress=card is not None,
        sources=sources,
        source_labels=SOURCE_LABELS,
        summary=summary,
        state_json=_state_json(state),
        error=error,
    )


def _result_context(db, user, letter: Letter, *, error: str | None = None,
                    enrichments: list[dict[str, str]] | None = None,
                    generated: bool = False) -> dict[str, Any]:
    dictation = decrypt_field(letter.dictation_enc)
    content = decrypt_field(letter.content_enc)
    selected_type = brain_bridge.resolve_explicit_type(letter.template_id)
    detection = brain_bridge.detect_type(dictation, selected_type)
    has_text = bool(content.strip())
    return {
        "letter": letter,
        "content": content,
        "detection": detection,
        "rule_check": brain_bridge.check_rules(content, detection["key"], dictation) if has_text else None,
        "used_templates": brain_bridge.search_templates(dictation) if has_text else [],
        "enrichments": enrichments or [],
        "generated": generated,
        "error": error,
        "active": "briefe",
        "crumbs": [
            ("Übersicht", "/app"),
            ("Briefe", "/app/briefe"),
            (letter.title or "Dokument", None),
        ],
    }


# --------------------------------------------------------------------------- routes


@router.get("/neu", include_in_schema=False)
def wizard(request: Request, db: DB, user: CurrentUser, patient_id: str | None = None):
    state: dict[str, Any] = {"step": 0, "sources": []}
    return _wizard_response(request, db, user, state)


@router.post("/neu", include_in_schema=False, dependencies=[CSRF])
async def wizard_post(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    state = _parse_state(form.get("wiz_state"))
    step_index = _int(form.get("wiz_step"), _int(state.get("step"), 0))

    # Step 1 — choosing a document type starts a fresh run.
    wtype = str(form.get("wtype") or "").strip()
    if wtype:
        card = _CARD_BY_KEY.get(wtype)
        if card is None:
            return RedirectResponse("/app/neu", status_code=303)
        return _wizard_response(
            request, db, user,
            {"wtype": wtype, "doc_type": card["doc_type"], "step": 1, "sources": []},
        )

    card = _CARD_BY_KEY.get(str(state.get("wtype") or ""))
    if card is None:
        return RedirectResponse("/app/neu", status_code=303)
    steps = build_steps(card["key"])
    flow_len = len(steps) + 1
    step_index = max(0, min(step_index, flow_len - 1))
    typed_index = step_index - 1
    action = str(form.get("action") or "")

    # Merge the current step's answers into the carried state.
    if 0 <= typed_index < len(steps):
        step = steps[typed_index]
        if step["render"] == "fields":
            for field in step["fields"]:
                name = field["name"]
                if field["type"] == "checkbox":
                    state[name] = "1" if form.get(name) else ""
                elif name in form:
                    state[name] = str(form.get(name))
        elif step["render"] == "sources":
            if form.get("remove_source") is not None:
                index = _int(form.get("remove_source"), -1)
                sources = list(state.get("sources") or [])
                if 0 <= index < len(sources):
                    sources.pop(index)
                state["sources"] = sources
            # A filled source row is taken along on "Quelle hinzufügen" and — so the member
            # never loses a typed source — also on "Weiter".
            pending_text = str(form.get("src_text") or "").strip()
            if action == "add_source" or (action == "next" and pending_text):
                label = str(form.get("src_label") or "Sonstiges").strip() or "Sonstiges"
                if pending_text:
                    sources = list(state.get("sources") or [])
                    sources.append({"label": label, "text": pending_text})
                    state["sources"] = sources

    # Tenant isolation: a foreign patient id in the carried state is a 404, not a leak.
    patient_id = str(state.get("patient_id") or "").strip()
    if patient_id:
        get_patient_or_404(db, user, patient_id)

    if action == "back":
        step_index = max(0, step_index - 1)
    elif action == "add_source" or form.get("remove_source") is not None:
        pass  # stay on the sources step
    else:
        step_index = min(step_index + 1, flow_len - 1)

    state["step"] = step_index
    return _wizard_response(request, db, user, state)


@router.post("/neu/erzeugen", include_in_schema=False, dependencies=[CSRF])
async def wizard_erzeugen(request: Request, db: DB, user: CurrentUser):
    """The ONLY route that creates a letter — reachable only from the summary confirm."""
    form = await request.form()
    state = _parse_state(form.get("wiz_state"))
    card = _CARD_BY_KEY.get(str(state.get("wtype") or ""))
    if card is None or not state.get("at_summary"):
        return RedirectResponse("/app/neu", status_code=303)

    patient_id = str(state.get("patient_id") or "").strip()
    if not patient_id:
        state["step"] = len(build_steps(card["key"]))
        return _wizard_response(
            request, db, user, state,
            error="Bitte wählen Sie eine Patientin oder einen Patienten.", status_code=400,
        )
    patient = get_patient_or_404(db, user, patient_id)

    quota = _quota(db, user)
    if quota.get("remaining", 0) <= 0:
        state["step"] = len(build_steps(card["key"]))
        return _wizard_response(
            request, db, user, state,
            error="Ihr Kontingent ist aufgebraucht. Bitte wählen Sie unter „Abrechnung“ einen Plan, "
                  "um weitere Briefe zu erzeugen.",
            status_code=402,
        )

    steps = build_steps(card["key"])
    dictation = _compose_dictation(card, steps, state)
    structured = _structured(card, steps, state)
    # OP-Bericht: "Standarddetails aus Referenz ergänzen" opts this one letter into the
    # pipeline's grounded enrichment when the pipeline supports it.
    enrich = True if state.get("standarddetails") else None

    patient_label = (patient.last_name or patient.first_name or "").strip()
    title = f"{card['label']} {patient_label}".strip()[:200]
    letter = Letter(
        id=new_id(),
        user_id=user.id,
        patient_id=patient.id,
        kind=card["letter_kind"],
        status="draft",
        title=title,
        language=user.ui_lang or "de",
        template_id=card["doc_type"],
        dictation_enc=encrypt_field(dictation),
    )
    db.add(letter)
    db.commit()
    audit(db, event="letter.created", user_id=user.id, target_type="letter",
          target_id=letter.id, request=request, wizard=card["key"])

    before_ids = _letter_ids(db, user)
    result = None
    error: str | None = None
    try:
        result = _call_pipeline(db, user, patient, card, dictation, user.letterhead_json or {},
                                "", structured, enrich=enrich)
    except NotImplementedError:
        error = "Die Brief-Erzeugung ist in dieser Umgebung noch nicht verfügbar."
        audit(db, event="letter.generate_unavailable", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request)
    except Exception as exc:  # noqa: BLE001 - surface a plain German message, log the rest
        error = _pipeline_error_message(exc)
        audit(db, event="letter.generate_failed", user_id=user.id, target_type="letter",
              target_id=letter.id, request=request, error=f"{type(exc).__name__}")

    _fold_pipeline_letters(db, user, letter, before_ids, result)
    letter.template_id = card["doc_type"]
    if error is not None and letter.status != "failed":
        letter.status = "failed"
        letter.error = error
    elif error is None:
        letter.error = ""
    db.commit()

    enrichments = _read_enrichments(result, letter)
    return render(
        request,
        "app/neu/ergebnis.html",
        status_code=200,
        **_result_context(db, user, letter, error=error, enrichments=enrichments,
                          generated=error is None),
    )


@router.get("/neu/ergebnis/{letter_id}", include_in_schema=False)
def wizard_ergebnis(request: Request, db: DB, user: CurrentUser, letter_id: str):
    letter = get_letter_or_404(db, user, letter_id)
    return render(
        request,
        "app/neu/ergebnis.html",
        **_result_context(db, user, letter, generated=letter.status in ("done", "approved")),
    )
