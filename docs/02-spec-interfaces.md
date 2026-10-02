# Briefato — interface contracts (frozen 2026-10-01)

Everything below is a **contract**. Parallel workstreams may only write files inside their own
directory. If a workstream needs a change to a frozen item (schema, route path, template block,
function signature), it must NOT change it — it must be reported instead.

## 1. Ownership map

| Path | Owner | Notes |
|---|---|---|
| `README.md`, `docs/01-architecture.md`, `docs/02-spec-interfaces.md` | SYSADMIN | frozen |
| `app/pyproject.toml`, `app/Dockerfile`, `app/briefato/{__init__,config,db,models,security}.py` | SYSADMIN | frozen foundation |
| `app/briefato/main.py`, `app/briefato/routes/**`, `app/briefato/templates/**`, `app/briefato/static/**` | WORKSTREAM-PORTAL | routes, UI, design system |
| `app/briefato/pipeline/**`, `app/tests/test_pipeline.py` | WORKSTREAM-PIPELINE | generation, pseudonymisation, DOCX |
| `app/briefato/billing/**`, `app/tests/test_billing.py` | WORKSTREAM-BILLING | Stripe |
| `landing/**` | WORKSTREAM-LANDING | static marketing site |
| `docs/compliance/**` | WORKSTREAM-COMPLIANCE | DSGVO/legal/threat model |
| `deploy/**` | SYSADMIN | compose, Caddy, backups |

Nobody edits another workstream's files. Cross-module imports go through the signatures below.

## 2. Environment / runtime

- Python 3.12, dev venv at `/workspace/briefato/.venv` (deps already installed; `app/requirements.txt`
  is the pinned list).
- Dev run: `BRIEFATO_DATA_DIR=/tmp/bd BRIEFATO_LLM_MOCK=true .venv/bin/uvicorn briefato.main:app --app-dir app --port 8080`
- Tests: `.venv/bin/python -m pytest app/tests -q`  (must pass with `BRIEFATO_LLM_MOCK=true`)
- No network calls in tests. No `TODO`/`pass  # implement later` left behind.

## 3. Frozen data model (`app/briefato/models.py`)

All tables carry `id` (uuid hex, string 32) and UTC-naive `created_at`.
Tenant column is always `user_id` (FK `users.id`).

- `users`: email(unique,lower), password_hash, full_name, practice_name, street, zip, city, country,
  phone, tax_id, is_active, is_admin, email_verified_at, last_login_at, letterhead_json,
  ui_lang, created_at, updated_at
- `auth_sessions`: token_hash(unique), user_id, expires_at, revoked_at, ip, user_agent, created_at
- `patients`: user_id, external_ref, first_name, last_name, birth_date, sex, insurance,
  insurance_number, street, zip, city, phone, email, referring_doctor, notes_enc, archived_at,
  created_at, updated_at
- `letters`: user_id, patient_id, kind(arztbrief|attest|befund|ueberweisung|sonstiges), status
  (draft|queued|generating|done|failed|approved), title, dictation_enc, content_enc, language,
  template_id, model, tokens_in, tokens_out, cost_usd, error, approved_at, created_at, updated_at
- `generations`: user_id, letter_id, provider, model, tokens_in, tokens_out, cost_usd, latency_ms,
  status, pseudonymised(bool), error, created_at
- `subscriptions`: user_id(unique), plan_code(free|starter|praxis|klinik), status, stripe_customer_id,
  stripe_subscription_id, current_period_start, current_period_end, letters_quota, letters_used,
  cancel_at_period_end, created_at, updated_at
- `audit_events`: user_id(nullable), event, target_type, target_id, ip, user_agent, meta_json,
  created_at

Encrypted columns end in `_enc` and hold Fernet tokens (base64 str). Never return them raw to a
template — always decrypt with `security.decrypt_field()` first.

## 4. Frozen helpers

`briefato/config.py` → `get_settings()` (lru_cache) returning `Settings` (pydantic-settings,
prefix `BRIEFATO_`). Highlights: `env`, `base_url`, `secret_key`, `data_dir`, `db_url`,
`llm_base_url/llm_api_key/llm_model/llm_timeout_s/llm_mock`, `field_key`, `stripe_*`,
`quota_default_letters`, `session_ttl_hours`, `admin_email`, `ui_lang`.

`briefato/db.py` → `Base`, `engine`, `SessionLocal`, `get_db()` (FastAPI dependency),
`init_db()`, `session_scope()`.

`briefato/security.py`:
- `hash_password(pw) -> str`, `verify_password(pw, hash) -> bool` (argon2)
- `new_session_token() -> (raw, token_hash)`, `hash_token(raw) -> str`
- `encrypt_field(plain: str) -> str`, `decrypt_field(token: str|None) -> str`
- `new_csrf_token() -> str`, `check_csrf(session, token) -> bool`
- `current_user(request, db) -> User | None`, `require_user(...) -> User` (raises `NotAuthenticated`)
- `login_user(db, user, request) -> raw_token`, `logout_user(db, raw_token)`

## 5. Route map (owned by WORKSTREAM-PORTAL)

Public (no auth): `GET /` (landing, static files from `landing/`), `GET /preise` (pricing),
`GET /impressum`, `GET /datenschutz`, `GET /agb`, `GET /healthz` → `{"status":"ok"}`.
Auth: `GET|POST /registrieren`, `GET|POST /anmelden`, `POST /abmelden`,
`GET /passwort-vergessen`, `POST /passwort-vergessen`, `GET|POST /passwort-zuruecksetzen`.
App (auth required, all under `/app`):
- `GET /app` dashboard (counters: patients, letters this month, quota left, recent letters)
- `GET /app/patienten`, `GET|POST /app/patienten/neu`, `GET /app/patienten/{id}`,
  `GET|POST /app/patienten/{id}/bearbeiten`, `POST /app/patienten/{id}/archivieren`
- `GET /app/briefe`, `GET|POST /app/briefe/neu`, `GET /app/briefe/{id}`,
  `POST /app/briefe/{id}/erzeugen`, `POST /app/briefe/{id}/speichern`,
  `POST /app/briefe/{id}/freigeben`, `GET /app/briefe/{id}/export.docx`,
  `POST /app/briefe/{id}/loeschen`
- `GET /app/suche?q=`
- `GET /app/konto` (profile, practice data, letterhead, plan/quota, export-my-data, delete-account)
- `GET /app/abrechnung` → Stripe Checkout redirect, `POST /app/abrechnung/portal`
- `POST /webhooks/stripe` (billing workstream)
- `GET /admin` (sqladmin, admin users only)

Templates live in `app/briefato/templates/`; base template `base.html` must define blocks
`title`, `head`, `content`, `scripts` and include CSRF meta + HTMX from local static files
(no CDN in the portal — self-host `static/js/htmx.min.js`).

## 6. Frozen module APIs

### pipeline (`briefato/pipeline/`)

```python
# pseudonym.py
class Pseudonymizer:
    FIELDS = ("last_name", "first_name", "birth_date", "insurance_number", "street", "zip", "city", "phone", "email")
    @classmethod
    def from_patient(cls, patient) -> "Pseudonymizer"      # builds token->value map
    def mask(self, text: str) -> str                        # replaces values with {{TOKEN_n}} / {{TOKEN}}
    def restore(self, text: str) -> str                     # inverse
    def masked_fields(self) -> dict[str, str]               # token -> value (for logging/audit)

# providers.py
@dataclass
class LLMResult:
    text: str; model: str; provider: str; tokens_in: int; tokens_out: int; cost_usd: float; latency_ms: int
class LLMProvider(Protocol):
    def generate(self, system: str, user: str, *, max_tokens: int = 2000, temperature: float = 0.2) -> LLMResult: ...
def get_provider(settings) -> LLMProvider        # MockProvider when settings.llm_mock else OpenAICompatProvider

# prompts.py
def system_prompt(kind: str, language: str = "de") -> str
def user_prompt(kind: str, dictation: str, patient_ctx: dict, letterhead: dict, extra: str = "") -> str

# letterhead.py
def render_docx(letter_text: str, letterhead: dict, patient_ctx: dict, out_path: Path, kind: str) -> Path

# generate.py
def generate_letter(db, *, user, patient, kind: str, dictation: str, letterhead: dict, extra: str = "") -> Letter
    """Creates the Letter row, pseudonymises, calls the provider, restores, stores encrypted,
    writes a Generation row with tokens/cost/latency, writes audit event, returns the Letter."""
```

### billing (`briefato/billing/`)

```python
def create_checkout_url(db, user, plan_code: str, success_url: str, cancel_url: str) -> str
def create_portal_url(db, user, return_url: str) -> str
def handle_webhook(db, payload: bytes, sig_header: str) -> dict     # idempotent, returns {"handled": bool, "event": str}
def quota_state(db, user) -> dict   # {"plan": str, "quota": int, "used": int, "remaining": int, "period_end": iso}
```

## 7. UI / design system (WORKSTREAM-PORTAL, must also be usable by the landing page)

- Tokens in `app/briefato/static/css/tokens.css`: colour ramp (one accent), type scale, spacing scale,
  radii, shadows, dark-mode variables. No framework CSS.
- Portal CSS `static/css/app.css`; landing uses its own copy `landing/assets/css/briefato.css`
  (duplicated tokens are fine — no build step).
- German UI copy, `du`-free (neutral `Sie`), plain language, no AI-slop phrasing ("revolutionär",
  "KI-gestützt" as marketing filler are banned). Show privacy facts, not adjectives.
- Accessibility: WCAG AA contrast, visible focus states, real `<label>`s, keyboard-operable.
- Responsive: 360 px → 1440 px; portal app shell = left nav (collapses to top bar under 900 px).

## 8. Definition of done per workstream

1. Code runs: `pytest` green, `uvicorn` boots, no import errors, no missing templates.
2. A reproducible self-check command is documented in the workstream's own `README` inside its dir.
3. No secrets, no real patient data, no placeholder text in shipped pages.
4. Every deviation from this contract is reported in the final summary, not silently applied.
