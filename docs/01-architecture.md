# Briefato — architecture, decisions, stages

Owner: Mohamed Sabry. Implementer/operator: SYSADMIN agent. Created 2026-10-01.

## 1. Vision

German medical practices (Arztpraxen, Praxen für Physio/Logopädie, Pflegedienste, Gutachter) lose
hours writing Arztbriefe, Atteste, Befunde and patient letters. Today they either type them or dictate
into a clinical DMS that costs more than it should. Briefato turns a raw dictation into a correctly
formatted, letterhead-ready document — per patient, with history, for a flat monthly fee.

Positioning rule: **it is a writing tool, not a medical device.** No diagnosis, no treatment advice,
no claims about medical correctness. That keeps it outside MDR/medical-device scope and keeps the
liability model sane (the member approves every letter before it is used).

## 2. Decisions (ADR-style)

**D1 — One portal, no per-member AI agent runtime.** Rejected: giving every member his own Hermes
profile (tools, skills, files, memory). It multiplies runtime cost, drift, audit surface and escape
risk. Member data lives in the portal DB; the model is a stateless server-side function.
*Consequence:* member history is a first-class product feature (per patient, searchable) rather than a
side effect of an opaque agent session.

**D2 — Server-rendered UI, no SPA.** FastAPI + Jinja2 + HTMX + hand-rolled CSS design system.
No node/npm/build step. Rationale: form-and-document product; a SPA adds toolchain, bundle and
attack surface with no user-visible gain.

**D3 — Sync SQLAlchemy 2.0 + SQLite/WAL.** Low concurrency (tens of members), single writer is fine.
Postgres only when a second app worker appears. Migrations with Alembic from day one.

**D4 — Pseudonymise before every model call.** Patient identifiers are tokenised locally
(`{{PATIENT_NAME}}` …), the model sees only tokens, the real values are re-inserted locally after the
call. This is a code-level guarantee, not a policy comment — it must hold even for a non-EU provider.

**D5 — Provider-agnostic model layer.** OpenAI-compatible interface, configured by env
(`BRIEFATO_LLM_BASE_URL / _API_KEY / _MODEL`). Default target for production: an EU-hosted model
(Mistral / Azure EU) with an AVV. `BRIEFATO_LLM_MOCK=true` for dev/test — no network calls.

**D6 — Money by Stripe-hosted flows only.** Checkout + Customer Portal + webhooks. No card data,
no billing UI of our own. Test mode until the compliance gate passes.

**D7 — Encrypted at rest for clinical text.** Dictation and generated letter text are stored
Fernet-encrypted (key via env/pass); the DB file itself is not trusted. Backups are encrypted and one
copy leaves the host.

**D8 — Isolation is a tested property, not an assertion.** Every query is scoped by `user_id`; an
adversarial test suite must prove cross-tenant reads fail (404/403), for letters, patients, files and
exports.

## 3. Deployment

- Host: N305 `phontary` (192.168.178.100), Docker 29.6.1 + Portainer.
- Repo on host: `/mnt/fast/docker/briefato` (mirror of `/workspace/briefato`, minus `.venv`).
- One container `briefato`, host port **8085**, data volume `/mnt/fast/docker/briefato/data`.
- Reverse proxy: existing Caddy stack — `briefato.sabry.io` → `192.168.178.100:8085`.
- Capacity baseline measured 2026-10-01: RAM 31.8 GB (15.9 GB available), **swap 7268/8191 MB used**,
  load 4.93, 48 containers. The portal is small (~250 MB), but the swap pressure is a pre-existing
  problem that must be fixed before any public beta (tracked as S5 blocker).

## 4. Stages

**S0 — Recon & freeze (done 2026-10-01).** SSH/Docker/Portainer access verified from the agent
container; capacity snapshot taken; interfaces frozen in `docs/02-spec-interfaces.md`.

**S1 — Foundation.** Package layout, config, DB models, auth (argon2 + server-side sessions + CSRF),
tenant scoping helper, audit log, health endpoint, Dockerfile, Portainer stack, Caddy route,
systemd/cron backup of the portal DB. Exit test: signup → login → logout end to end, all tests green.

**S2 — Core product.** Patient records (CRUD, archive, search), dictation intake, generation pipeline
(pseudonymise → model → restore → store), letter editor with approve-and-lock, DOCX export on the
member's letterhead, per-patient history and full-text search.

**S3 — Marketing & funnel.** Landing page (German, value prop, pricing, trust/privacy section),
pricing page, signup with email verification, onboarding wizard (practice data → letterhead →
first letter), Impressum/Datenschutz/AGB placeholders marked for legal review.

**S4 — Billing.** Stripe test-mode Checkout + Portal + webhook idempotency, plan table, monthly quota
enforcement, admin (sqladmin) over users/patients/letters/subscriptions, per-member cost meter.

**S5 — Compliance & hardening.** DSGVO pack (AVV with the model provider, retention policy, deletion
and export on request, processing register), encrypted off-host backups + a restore test, rate limits,
login throttling, security headers, monitoring in Healthchecks, swap-pressure fix.

**S6 — Beta & launch.** 3–5 invited testers (colleagues), feedback loop, bug fix round, then the
public site + real money — which requires a public domain, not the LAN-only `*.sabry.io`.

## 5. Open decisions owned by Mohamed

See the "Questions" section of the owner review
(`/workspace/sysadmin/analyses/review-2026-10-01-schreibdienst-saas-plan.md`). Short list:
public domain, model/AVV route, hosting for paying customers (N305 vs EU VPS), audience,
pricing/quota, Stripe account status, legal texts owner, voice input in v1.

## 6. Non-goals for v1

Voice-in-the-browser (S3+), mobile apps, team accounts with roles, DMS/HL7 integrations, claims
processing, multi-language output (German only), self-hosted model inference.
