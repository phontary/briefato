"""Governance model for template proposals (WORKSTREAM-PORTAL).

This module owns exactly one table, ``template_proposals``, and is the *only* place in the
portal that adds a table. It lives outside the frozen ``briefato/models.py`` (which the
portal workstream must not edit) and is registered on the shared ``Base`` so that
``init_db()`` / ``Base.metadata.create_all`` create it at startup. ``ensure_library_tables()``
is also exported and called from ``create_app`` so the table exists even when a caller
creates the schema explicitly for a subset of models.

Why a separate table: approving a proposal must never write into the read-only source
archive (``brain/``). A proposal is member-submitted data with its own lifecycle
(``pending`` → ``approved`` | ``rejected``) and an audit trail, so it belongs in the
database, not in the brain files.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base, engine
from ..models import new_id, utcnow

PROPOSAL_STATUS = ("pending", "approved", "rejected")


class TemplateProposal(Base):
    """A member's suggestion to add a Musterbrief for a diagnosis that had no match."""

    __tablename__ = "template_proposals"
    __table_args__ = (Index("ix_template_proposals_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    diagnosis: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    proposed_sections: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False, index=True)
    review_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )


def ensure_library_tables() -> None:
    """Create the proposal table if missing. Idempotent; safe to call on every boot."""
    Base.metadata.create_all(engine, tables=[TemplateProposal.__table__], checkfirst=True)


__all__ = ["PROPOSAL_STATUS", "TemplateProposal", "ensure_library_tables"]
