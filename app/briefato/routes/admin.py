"""sqladmin administration area, restricted to portal users with ``is_admin``."""

from __future__ import annotations

from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

from ..config import get_settings
from ..db import SessionLocal, engine
from ..models import AuditEvent, Generation, Letter, Patient, Subscription, User
from ..security import verify_password


class AdminAuth(AuthenticationBackend):
    """Admin login backed by portal users; only ``is_admin`` accounts pass."""

    async def login(self, request: Request):
        form = await request.form()
        email = str(form.get("username", "")).strip().lower()
        password = str(form.get("password", ""))
        db = SessionLocal()
        try:
            account = db.scalar(select(User).where(User.email == email))
            if (
                account is not None
                and account.is_admin
                and account.is_active
                and verify_password(password, account.password_hash)
            ):
                request.session["admin_user_id"] = account.id
                return True
        finally:
            db.close()
        return False

    async def logout(self, request: Request):
        request.session.pop("admin_user_id", None)
        return True

    async def authenticate(self, request: Request):
        user_id = request.session.get("admin_user_id")
        if not user_id:
            return False
        db = SessionLocal()
        try:
            account = db.get(User, user_id)
            return bool(account is not None and account.is_admin and account.is_active)
        finally:
            db.close()


class UserAdmin(ModelView, model=User):
    name = "Benutzer"
    name_plural = "Benutzer"
    icon = "fa-solid fa-user"
    column_list = [User.email, User.full_name, User.practice_name, User.is_active, User.is_admin, User.created_at]
    column_searchable_list = [User.email, User.full_name, User.practice_name]
    column_sortable_list = [User.email, User.created_at]
    form_excluded_columns = [User.password_hash]


class PatientAdmin(ModelView, model=Patient):
    name = "Patient"
    name_plural = "Patienten"
    column_list = [Patient.last_name, Patient.first_name, Patient.user_id, Patient.archived_at, Patient.created_at]
    column_searchable_list = [Patient.last_name, Patient.first_name]
    column_sortable_list = [Patient.last_name, Patient.created_at]


class LetterAdmin(ModelView, model=Letter):
    name = "Brief"
    name_plural = "Briefe"
    column_list = [Letter.title, Letter.kind, Letter.status, Letter.user_id, Letter.created_at, Letter.approved_at]
    column_searchable_list = [Letter.title]
    column_sortable_list = [Letter.created_at, Letter.status]


class SubscriptionAdmin(ModelView, model=Subscription):
    name = "Abonnement"
    name_plural = "Abonnements"
    column_list = [
        Subscription.user_id,
        Subscription.plan_code,
        Subscription.status,
        Subscription.letters_quota,
        Subscription.letters_used,
        Subscription.current_period_end,
    ]


class GenerationAdmin(ModelView, model=Generation):
    name = "Erzeugung"
    name_plural = "Erzeugungen"
    column_list = [
        Generation.letter_id,
        Generation.model,
        Generation.tokens_in,
        Generation.tokens_out,
        Generation.cost_usd,
        Generation.status,
        Generation.created_at,
    ]


class AuditEventAdmin(ModelView, model=AuditEvent):
    name = "Audit-Ereignis"
    name_plural = "Audit-Ereignisse"
    column_list = [AuditEvent.event, AuditEvent.user_id, AuditEvent.target_type, AuditEvent.created_at]
    column_searchable_list = [AuditEvent.event]
    column_sortable_list = [AuditEvent.created_at]


def mount_admin(app) -> Admin:
    settings = get_settings()
    admin = Admin(
        app,
        engine,
        base_url="/admin",
        title="Briefato Administration",
        authentication_backend=AdminAuth(secret_key=settings.secret_key),
    )
    for view in (
        UserAdmin,
        PatientAdmin,
        LetterAdmin,
        SubscriptionAdmin,
        GenerationAdmin,
        AuditEventAdmin,
    ):
        admin.add_view(view)
    return admin
