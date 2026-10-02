# Briefato

**Codename:** `briefato` — SaaS for German medical practices (Arztbriefe / Atteste / Befunde).
Dictation in → finished letter out, with patient records, history and subscription billing.

Owner: Mohamed Sabry (phontary). Implemented and operated by the SYSADMIN agent.
Staging URL: `https://briefato.sabry.io` (LAN-internal DNS for now).

## What it is (and is not)

- **Is:** a multi-tenant web portal. Members sign up, keep patient records, paste/dictate text,
  receive a finished, letterhead-formatted document, and keep their own searchable history.
- **Is not:** a per-member AI agent. There is exactly ONE application; the model is called
  server-side as a stateless function (no member profile, no member tools, no member memory).
  Member data lives in the portal database, owned by the member's account — not in an agent runtime.

## Architecture in one line

FastAPI + Jinja2 + HTMX server-rendered portal, SQLite (WAL) + SQLAlchemy, one Docker container
behind the existing Caddy, Stripe-hosted Checkout/Portal for money. No SPA, no node toolchain.

## Stage plan (full detail: `docs/01-architecture.md`)

| Stage | Content | State |
|---|---|---|
| S0 | Recon, capacity, architecture freeze, interface contracts | done (this scaffold) |
| S1 | Foundation: repo, models, auth, isolation, staging deploy | in progress |
| S2 | Core: patients, dictation intake, letter generation, history, DOCX export | queued |
| S3 | Landing page + pricing + signup funnel | queued |
| S4 | Billing (Stripe test mode), quota, admin, cost meter | queued |
| S5 | Compliance (DSGVO), encrypted backups + restore test, hardening | queued |
| S6 | Closed beta (invite-only) → public launch | queued |

## Layout

```
briefato/
├─ landing/         static marketing site (served at /)
├─ app/             the portal (Python package `briefato/`)
├─ deploy/          docker-compose + Caddy snippet
├─ docs/            architecture, contracts, compliance
└─ .venv/           dev virtualenv (gitignored)
```

## Run locally

```bash
cd /workspace/briefato
.venv/bin/pip install -r app/requirements.txt
BRIEFATO_DATA_DIR=/tmp/briefato-data BRIEFATO_LLM_MOCK=true \
  .venv/bin/uvicorn briefato.main:app --app-dir app --port 8080
```

## Rules of engagement

1. Nothing is deployed to production and no real patient data is processed before the compliance
   gate in `docs/compliance/` is signed off by Mohamed.
2. Every change is committed to git; every decision is written down.
3. No secrets in the repo — env only (`deploy/stack.env` on the host, never in git).
