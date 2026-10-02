# Briefato portal (`WORKSTREAM-PORTAL`)

FastAPI + Jinja2 + HTMX application serving the member-facing portal and the public
landing routes, exactly against the frozen contract in `docs/02-spec-interfaces.md`
(§4 template blocks, §5 route map, §7 design system).

Owner of these paths: `app/briefato/main.py`, `app/briefato/routes/**`,
`app/briefato/templates/**`, `app/briefato/static/**`, `app/tests/test_portal.py`,
`app/tests/test_isolation.py`, this README. The foundation (`config`, `db`, `models`,
`security`) and the `pipeline`/`billing` packages are owned by other workstreams and are
imported as-is.

## Reproducible self-check

```bash
cd /workspace/briefato

# full test suite (offline, mock LLM, temporary DB)
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests -q

# boot the real app and check the public surface
BRIEFATO_DATA_DIR=/tmp/briefato-portal BRIEFATO_LLM_MOCK=true \
  .venv/bin/python -m uvicorn briefato.main:app --app-dir app --port 8099
for u in / /healthz /anmelden /app /preise /impressum /datenschutz /agb \
         /assets/css/app.css /gibt-es-nicht; do
  printf '%s  %s\n' "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8099$u)" "$u"
done
```

## Layout

| Path | What |
|---|---|
| `main.py` | app factory, CSRF/security-header middleware, exception handlers, router wiring, sqladmin mount |
| `routes/deps.py` | template env, `render()` helper, CSRF guard, auth dependencies, tenant-scoped getters |
| `routes/public.py` | `/`, `/preise`, `/impressum`, `/datenschutz`, `/agb` (static from `landing/`), `/healthz`, `/assets/*` |
| `routes/auth.py` | register, login (+ throttling), logout, password forgot/reset |
| `routes/portal.py` | `/app` dashboard, `/app/suche` full-text search |
| `routes/patients.py` | patient CRUD + archive |
| `routes/letters.py` | letter draft → generate → edit → approve → DOCX export → delete |
| `routes/account.py` | profile, practice data, letterhead, plan/quota, JSON export, deletion request |
| `routes/billing.py` | `/app/abrechnung*` + `POST /webhooks/stripe` |
| `routes/admin.py` | sqladmin views, admin-only authentication backend |
| `templates/` | `base.html` (blocks `title`, `head`, `content`, `scripts`), `app_base.html`, auth/app/error templates |
| `static/css/tokens.css` | colour ramp (one accent), type/spacing scale, radii, shadows, dark mode |
| `static/css/app.css` | portal components (no framework CSS) |
| `static/js/htmx.min.js` | HTMX 2.0.11, vendored (verify it starts with JS, not `<`) |
| `static/js/app.js` | Ctrl+Enter submit, toast dismiss, confirm dialogs |

## Tenant isolation

Every query filters on `user_id` of the session user. Objects fetched by id go through
`get_patient_or_404` / `get_letter_or_404`, which raise **404** for anything the current
user does not own. Client-supplied `patient_id`/`user_id` values are re-scoped, never
trusted. `app/tests/test_isolation.py` proves it adversarially (reads, edits, deletes,
exports, guesses, search, create-with-foreign-patient-id).

## Security

- Session cookie: `HttpOnly`, `SameSite=Lax`, `Secure` in prod.
- CSRF: signed double-submit token in cookie + hidden field on every POST, enforced by
  `security.check_csrf` (403 on failure); HTMX may send the `X-CSRF-Token` header.
- Login throttling: recent `auth.login_failed` audit events inside
  `BRIEFATO_LOGIN_WINDOW_MINUTES` → 429 after `BRIEFATO_LOGIN_MAX_ATTEMPTS`; failed logins
  always show one generic message (no user enumeration).
- Security headers on every response: CSP (no `unsafe-inline` for portal pages), nosniff,
  `Referrer-Policy`, `X-Frame-Options: DENY` / `frame-ancestors 'none'`, HSTS in prod.
- Custom 404/403/500 pages; unhandled errors are logged and never leak a traceback.
- `/assets/*` resolves inside `landing/assets` then `static/`, refusing `..` traversal.

## Notes

- HTMX is vendored, no CDN in the portal.
- Portal pages carry no inline styles/scripts (CSP-clean); the landing pages keep their own
  inline style attributes, so they get a `style-src 'unsafe-inline'` variant of the CSP.
- The pipeline creates and returns its own `Letter` row and increments the quota; the portal
  folds that result back onto the member's draft (re-pointing `Generation` rows) so exactly
  one letter exists per generation.
- No new dependencies were needed; no `app/requirements.portal.txt` was created.
