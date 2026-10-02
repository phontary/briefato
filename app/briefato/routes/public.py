"""Public routes: the static landing site, assets and the health endpoint."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from ..config import get_settings
from .deps import STATIC_DIR

router = APIRouter()

# marketing slug -> candidate file names inside the landing directory
LANDING_PAGES = {
    "/": ("index.html",),
    "/preise": ("preise.html", "preise/index.html"),
    "/impressum": ("impressum.html", "impressum/index.html"),
    "/datenschutz": ("datenschutz.html", "datenschutz/index.html"),
    "/agb": ("agb.html", "agb/index.html"),
}

_ASSET_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".json": "application/json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".webmanifest": "application/manifest+json",
}


def _landing_file(page: str) -> Path | None:
    landing_dir = get_settings().landing_dir
    for candidate in LANDING_PAGES.get(page, ()):
        path = landing_dir / candidate
        if path.is_file():
            return path
    return None


def _render_landing(page: str) -> HTMLResponse:
    path = _landing_file(page)
    if path is None:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden.")
    return HTMLResponse(content=path.read_text(encoding="utf-8"), status_code=200)


def _safe_asset(rel_path: str) -> Path | None:
    """Resolve an asset path inside the allowed roots, refusing traversal."""
    rel = rel_path.strip().lstrip("/\\")
    if not rel or "\x00" in rel:
        return None
    candidate_parts = Path(rel).parts
    if ".." in candidate_parts:
        return None
    roots = [get_settings().landing_dir / "assets", STATIC_DIR]
    for root in roots:
        try:
            resolved_root = root.resolve()
            resolved = (resolved_root / rel).resolve()
        except (OSError, RuntimeError):
            continue
        if resolved == resolved_root or resolved_root in resolved.parents:
            if resolved.is_file():
                return resolved
    return None


@router.get("/healthz", include_in_schema=False)
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/", include_in_schema=False)
def landing_index() -> HTMLResponse:
    return _render_landing("/")


@router.get("/preise", include_in_schema=False)
def landing_preise() -> HTMLResponse:
    return _render_landing("/preise")


@router.get("/impressum", include_in_schema=False)
def landing_impressum() -> HTMLResponse:
    return _render_landing("/impressum")


@router.get("/datenschutz", include_in_schema=False)
def landing_datenschutz() -> HTMLResponse:
    return _render_landing("/datenschutz")


@router.get("/agb", include_in_schema=False)
def landing_agb() -> HTMLResponse:
    return _render_landing("/agb")


@router.get("/assets/{path:path}", include_in_schema=False)
def assets(path: str) -> Response:
    resolved = _safe_asset(path)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Datei nicht gefunden.")
    suffix = resolved.suffix.lower()
    media_type = _ASSET_TYPES.get(suffix) or mimetypes.guess_type(resolved.name)[0] or "application/octet-stream"
    return Response(
        content=resolved.read_bytes(),
        media_type=media_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )
