"""Frozen data model. Every tenant-owned table carries ``user_id``; every query filters on it."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    """UTC, tz-naive (SQLite friendly)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    practice_name: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    street: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    zip: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="DE", nullable=False)
    phone: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    tax_id: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    letterhead_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    ui_lang: Mapped[str] = mapped_column(String(5), default="de", nullable=False)

    patients: Mapped[list["Patient"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    letters: Mapped[list["Letter"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    subscription: Mapped["Subscription | None"] = relationship(cascade="all, delete-orphan", uselist=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"
    __table_args__ = (Index("ix_patients_user_name", "user_id", "last_name", "first_name"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    external_ref: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    birth_date: Mapped[object | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str] = mapped_column(String(10), default="", nullable=False)  # m | w | d | ''
    insurance: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    insurance_number: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    street: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    zip: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    phone: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    referring_doctor: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    notes_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="patients")
    letters: Mapped[list["Letter"]] = relationship(back_populates="patient")

    @property
    def display_name(self) -> str:
        return f"{self.last_name}, {self.first_name}".strip(", ")


LETTER_KINDS = ("arztbrief", "attest", "befund", "ueberweisung", "sonstiges")
LETTER_STATUS = ("draft", "queued", "generating", "done", "failed", "approved")


class Letter(Base, TimestampMixin):
    __tablename__ = "letters"
    __table_args__ = (Index("ix_letters_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id: Mapped[str | None] = mapped_column(
        ForeignKey("patients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20), default="arztbrief", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    dictation_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="de", nullable=False)
    template_id: Mapped[str] = mapped_column(String(40), default="standard", nullable=False)
    model: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="letters")
    patient: Mapped[Patient | None] = relationship(back_populates="letters")


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    letter_id: Mapped[str | None] = mapped_column(
        ForeignKey("letters.id", ondelete="CASCADE"), nullable=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ok", nullable=False)
    pseudonymised: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    plan_code: Mapped[str] = mapped_column(String(20), default="free", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    stripe_customer_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    stripe_subscription_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    letters_quota: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    letters_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_user_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    event: Mapped[str] = mapped_column(String(60), nullable=False)
    target_type: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    user_agent: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)


__all__ = [
    "AuditEvent",
    "AuthSession",
    "Generation",
    "Letter",
    "LETTER_KINDS",
    "LETTER_STATUS",
    "Patient",
    "Subscription",
    "User",
    "new_id",
    "utcnow",
]
