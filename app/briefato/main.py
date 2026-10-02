"""Briefato portal application factory (WORKSTREAM-PORTAL).

Boot:  .venv/bin/uvicorn briefato.main:app --app-dir app --port 8080
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from .db import init_db
from .routes import (
    account,
    admin,
    admin_vorlagen,
    auth,
    billing,
    letters,
    methode,
    patients,
    portal,
    public,
    wizard,
)
from .routes.deps import render
from .routes.library_models import ensure_library_tables
from .security import CSRF_COOKIE, NotAuthenticated, new_csrf_token

logger = logging.getLogger("briefato")

CSP_PORTAL = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)
CSP_LANDING = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)
# sqladmin renders some inline script/style of its own; keep it functional but scoped.
CSP_ADMIN = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

LANDING_PATHS = {"/", "/preise", "/impressum", "/datenschutz", "/agb"}


def _apply_security_headers(response: Response, request: Request) -> None:
    settings = get_settings()
    is_admin = request.url.path.startswith("/admin")
    is_landing = request.url.path in LANDING_PATHS
    csp = CSP_ADMIN if is_admin else (CSP_LANDING if is_landing else CSP_PORTAL)
    response.headers.setdefault("Content-Security-Policy", csp)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    if settings.is_prod:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


def create_app() -> FastAPI:
    settings = get_settings()
    init_db()
    ensure_library_tables()

    app = FastAPI(
        title="Briefato",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # ------------------------------------------------------------------ middleware
    @app.middleware("http")
    async def portal_context(request: Request, call_next):
        had_cookie = CSRF_COOKIE in request.cookies
        token = request.cookies.get(CSRF_COOKIE) or new_csrf_token()
        request.state.csrf_token = token
        response = await call_next(request)
        if not had_cookie:
            response.set_cookie(
                CSRF_COOKIE,
                token,
                httponly=True,
                samesite="lax",
                secure=settings.is_prod,
                max_age=settings.session_ttl_hours * 3600,
                path="/",
            )
        _apply_security_headers(response, request)
        return response

    # ------------------------------------------------------------------ routers
    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(portal.router)
    app.include_router(patients.router)
    app.include_router(letters.router)
    # Sequential wizard at /app/neu (its own router; the split editor stays at /app/briefe/{id}).
    app.include_router(wizard.router)
    app.include_router(account.router)
    app.include_router(billing.router)
    app.include_router(billing.webhook_router)
    # Method pages + template library (portal).
    app.include_router(methode.router)
    # Admin review must be registered BEFORE the sqladmin mount at /admin so the exact path
    # /admin/vorlagen-vorschlaege is matched here instead of by the generic sub-application.
    app.include_router(admin_vorlagen.router)

    # ------------------------------------------------------------------ exception handlers
    @app.exception_handler(NotAuthenticated)
    async def not_authenticated(request: Request, exc: NotAuthenticated):
        target = request.url.path
        if request.url.query:
            target = f"{target}?{request.url.query}"
        login_url = "/anmelden?next=" + quote(target, safe="/?=&")
        if request.headers.get("HX-Request"):
            return Response(status_code=200, headers={"HX-Redirect": login_url})
        return RedirectResponse(login_url, status_code=303)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception(request: Request, exc: StarletteHTTPException):
        status = exc.status_code
        if request.url.path.startswith("/webhooks/"):
            return JSONResponse({"error": "Anfrage konnte nicht verarbeitet werden."}, status_code=status)
        if status == 401:
            login_url = "/anmelden?next=" + quote(request.url.path, safe="/?=&")
            return RedirectResponse(login_url, status_code=303)
        if status == 403:
            return render(request, "errors/403.html", status_code=403)
        return render(request, "errors/404.html", status_code=status if 400 <= status < 500 else 404)

    @app.exception_handler(RequestValidationError)
    async def validation_exception(request: Request, exc: RequestValidationError):
        if request.url.path.startswith("/webhooks/"):
            return JSONResponse({"error": "Ungültige Anfrage."}, status_code=422)
        logger.warning("validation error on %s: %s", request.url.path, exc.errors())
        return render(request, "errors/404.html", status_code=400)

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception):
        logger.exception("unhandled error on %s", request.url.path, exc_info=exc)
        return render(request, "errors/500.html", status_code=500)

    # ------------------------------------------------------------------ admin
    admin.mount_admin(app)

    return app


app = create_app()
