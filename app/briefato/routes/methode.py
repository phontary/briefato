"""Method pages: the read-only method view (/app/methode) and the template library
(/app/vorlagen) with the member-side proposal flow. WORKSTREAM-PORTAL.

The method itself lives in ``brain/`` and is owned by the brain workstream; this module only
*reads* those files through :mod:`briefato.routes.brain_bridge`. The member's own rules are
stored in ``user.letterhead_json['custom_rules']`` (no schema change) and are appended to the
generation prompt after the Kern.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from ..security import audit
from . import brain_bridge
from .deps import CSRF, DB, CurrentUser, render
from .library_models import TemplateProposal

router = APIRouter(prefix="/app", tags=["methode"])

CUSTOM_RULES_MAX = 4000
_METHOD_CRUMBS = [("Übersicht", "/app"), ("Methode", None)]


# --------------------------------------------------------------------------- /app/methode


@router.get("/methode", include_in_schema=False)
def methode(request: Request, db: DB, user: CurrentUser):
    kern = brain_bridge.kern_sections()
    rules = brain_bridge.rules_grouped()
    practice = brain_bridge.practice_groups()
    anti = brain_bridge.anti_patterns()
    custom = str((user.letterhead_json or {}).get("custom_rules", "") or "")
    return render(
        request,
        "app/methode.html",
        kern=kern,
        rule_groups=rules,
        rule_total=brain_bridge.rule_count(),
        practice_groups=practice,
        practice_total=sum(len(group["rules"]) for group in practice),
        anti_patterns=anti,
        custom_rules=custom,
        brain_available=brain_bridge.brain_available(),
        method_message=brain_bridge.method_message(),
        active="methode",
        crumbs=_METHOD_CRUMBS,
    )


@router.post("/methode/regeln", include_in_schema=False, dependencies=[CSRF])
async def methode_regeln(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    custom = str(form.get("custom_rules", "")).strip()[:CUSTOM_RULES_MAX]
    data = dict(user.letterhead_json or {})
    if custom:
        data["custom_rules"] = custom
    else:
        data.pop("custom_rules", None)
    user.letterhead_json = data
    db.commit()
    audit(db, event="method.custom_rules_updated", user_id=user.id, target_type="user",
          target_id=user.id, request=request)
    return RedirectResponse("/app/methode?m=regeln_gespeichert", status_code=303)


# --------------------------------------------------------------------------- /app/vorlagen


def _library_entries(query: str = "") -> list[dict]:
    term = brain_bridge.normalize(query)
    entries: list[dict] = []
    for entry in brain_bridge.manifest_templates():
        item = dict(entry)
        item["locked"] = brain_bridge.is_locked(str(entry.get("file", "")))
        item["internal"] = entry.get("licence_risk") == "review"
        if term:
            blob = brain_bridge.normalize(
                " ".join(
                    [str(entry.get("title", "")), str(entry.get("group", "")), str(entry.get("file", ""))]
                    + [str(k) for k in entry.get("indication_keywords", []) or []]
                )
            )
            if term not in blob:
                continue
        entries.append(item)
    entries.sort(key=lambda e: (e.get("group", ""), e.get("title", "")))
    return entries


@router.get("/vorlagen", include_in_schema=False)
def vorlagen(request: Request, db: DB, user: CurrentUser, q: str | None = None):
    entries = _library_entries(q or "")
    all_entries = brain_bridge.manifest_templates()
    locked_count = sum(1 for e in all_entries if brain_bridge.is_locked(str(e.get("file", ""))))
    return render(
        request,
        "app/vorlagen/liste.html",
        entries=entries,
        q=(q or "").strip(),
        total=len(all_entries),
        locked_count=locked_count,
        archive_available=brain_bridge.archive_available(),
        brain_available=brain_bridge.brain_available(),
        active="vorlagen",
        crumbs=[("Übersicht", "/app"), ("Vorlagen", None)],
    )


@router.get("/vorlagen/vorschlaege", include_in_schema=False)
def vorlagen_vorschlaege(request: Request, db: DB, user: CurrentUser):
    proposals = db.scalars(
        select(TemplateProposal)
        .where(TemplateProposal.user_id == user.id)
        .order_by(TemplateProposal.created_at.desc())
    ).all()
    return render(
        request,
        "app/vorlagen/vorschlaege.html",
        proposals=proposals,
        status_labels={"pending": "Offen", "approved": "Angenommen", "rejected": "Abgelehnt"},
        active="vorlagen",
        crumbs=[("Übersicht", "/app"), ("Vorlagen", "/app/vorlagen"), ("Vorschläge", None)],
    )


@router.post("/vorlagen/vorschlag", include_in_schema=False, dependencies=[CSRF])
async def vorlagen_vorschlag(request: Request, db: DB, user: CurrentUser):
    form = await request.form()
    diagnosis = str(form.get("diagnosis", "")).strip()[:200]
    note = str(form.get("note", "")).strip()[:2000]
    sections_raw = str(form.get("sections", "")).strip()[:2000]
    source = str(form.get("source_template", "")).strip()[:200]
    if not diagnosis:
        return RedirectResponse("/app/vorlagen?m=vorschlag_ungueltig", status_code=303)

    sections = [part.strip() for part in sections_raw.replace(";", ",").split(",") if part.strip()]
    proposal = TemplateProposal(
        user_id=user.id,
        diagnosis=diagnosis,
        proposed_sections={"sections": sections[:20], "source_template": source},
        note=note,
        status="pending",
    )
    db.add(proposal)
    db.commit()
    audit(db, event="template_proposal.created", user_id=user.id, target_type="template_proposal",
          target_id=proposal.id, request=request, diagnosis=diagnosis)
    return RedirectResponse("/app/vorlagen/vorschlaege?m=vorschlag_gesendet", status_code=303)


@router.get("/vorlagen/{file_name}", include_in_schema=False)
def vorlage_detail(request: Request, db: DB, user: CurrentUser, file_name: str):
    from fastapi import HTTPException

    entry = brain_bridge.template_entry(file_name)
    if entry is None or brain_bridge.is_locked(file_name):
        raise HTTPException(status_code=404, detail="Vorlage nicht gefunden.")
    body = brain_bridge.template_body(file_name)
    return render(
        request,
        "app/vorlagen/detail.html",
        entry=entry,
        body_html=brain_bridge.render_markdown_lite(body or ""),
        body_available=body is not None,
        archive_available=brain_bridge.archive_available(),
        internal=entry.get("licence_risk") == "review",
        active="vorlagen",
        crumbs=[("Übersicht", "/app"), ("Vorlagen", "/app/vorlagen"), (entry.get("title", file_name), None)],
    )


__all__ = ["router"]
