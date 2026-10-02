"""Admin review of member template proposals (WORKSTREAM-PORTAL).

Mounted on the main app *before* the sqladmin sub-application so ``/admin/vorlagen-vorschlaege``
is matched here instead of by the generic sqladmin mount. Admin-only: an authenticated
non-admin gets 403, an anonymous visitor is sent to the portal login.

Approving a proposal only flips its status and writes an audit event. It never writes into the
read-only ``brain/`` archive — the actual brain update is the owner's decision later.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User, utcnow
from ..security import NotAuthenticated, audit, current_user
from .deps import CSRF, DB, render
from .library_models import PROPOSAL_STATUS, TemplateProposal

router = APIRouter(tags=["admin-vorlagen"])

_STATUS_LABELS = {"pending": "Offen", "approved": "Angenommen", "rejected": "Abgelehnt"}


def require_admin(request: Request, db: Session = Depends(get_db)) -> User:
    user = current_user(request, db)
    if user is None:
        raise NotAuthenticated
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Administration ist Administratoren vorbehalten.")
    request.state.current_user = user
    return user


AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/admin/vorlagen-vorschlaege", include_in_schema=False)
def vorschlaege(request: Request, db: DB, admin: AdminUser, status: str | None = None):
    stmt = select(TemplateProposal).order_by(TemplateProposal.created_at.desc())
    selected = status if status in PROPOSAL_STATUS else ""
    if selected:
        stmt = stmt.where(TemplateProposal.status == selected)
    proposals = db.scalars(stmt).all()
    counts = {
        key: len(db.scalars(select(TemplateProposal).where(TemplateProposal.status == key)).all())
        for key in PROPOSAL_STATUS
    }
    author_ids = {p.user_id for p in proposals}
    authors = {
        user_id: (db.get(User, user_id).email if db.get(User, user_id) else "")
        for user_id in author_ids
    }
    return render(
        request,
        "app/admin/vorlagen_vorschlaege.html",
        proposals=proposals,
        counts=counts,
        authors=authors,
        status_labels=_STATUS_LABELS,
        selected_status=selected,
        active="admin",
        crumbs=[("Übersicht", "/app"), ("Administration", "/admin/vorlagen-vorschlaege"), ("Vorschläge", None)],
    )


@router.post("/admin/vorlagen-vorschlaege/{proposal_id}/genehmigen", include_in_schema=False, dependencies=[CSRF])
async def genehmigen(request: Request, db: DB, admin: AdminUser, proposal_id: str):
    proposal = _get_or_404(db, proposal_id)
    form = await request.form()
    proposal.status = "approved"
    proposal.review_note = str(form.get("review_note", "")).strip()[:2000]
    proposal.reviewed_at = utcnow()
    proposal.reviewed_by = admin.id
    db.commit()
    audit(db, event="template_proposal.approved", user_id=admin.id,
          target_type="template_proposal", target_id=proposal.id, request=request,
          diagnosis=proposal.diagnosis)
    return RedirectResponse("/admin/vorlagen-vorschlaege?m=vorschlag_genehmigt", status_code=303)


@router.post("/admin/vorlagen-vorschlaege/{proposal_id}/ablehnen", include_in_schema=False, dependencies=[CSRF])
async def ablehnen(request: Request, db: DB, admin: AdminUser, proposal_id: str):
    proposal = _get_or_404(db, proposal_id)
    form = await request.form()
    proposal.status = "rejected"
    proposal.review_note = str(form.get("review_note", "")).strip()[:2000]
    proposal.reviewed_at = utcnow()
    proposal.reviewed_by = admin.id
    db.commit()
    audit(db, event="template_proposal.rejected", user_id=admin.id,
          target_type="template_proposal", target_id=proposal.id, request=request,
          diagnosis=proposal.diagnosis)
    return RedirectResponse("/admin/vorlagen-vorschlaege?m=vorschlag_abgelehnt", status_code=303)


def _get_or_404(db: Session, proposal_id: str) -> TemplateProposal:
    proposal = db.get(TemplateProposal, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Vorschlag nicht gefunden.")
    return proposal


__all__ = ["router", "require_admin"]
