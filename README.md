# briefato

A web portal for German medical practices that turns a raw dictation into a correctly formatted, letterhead-ready document — per patient, with history, for a flat monthly fee.

**Positioning:** a writing tool, not a medical device. No diagnosis, no treatment advice, no claims about medical correctness. The member approves every letter before it is used.

---

## Features

- **AI letter generation** — paste or dictate free text; the engine triages the input, asks one clarifying question if needed, and produces a finished letter (Arztbrief, Attest, Befund, OP-Bericht, Entlassbrief, …)
- **Chat portal** — a ChatGPT-style composer that refines the same letter across a thread; `XXX` placeholders are highlighted and counted so nothing stays empty
- **Wizard** — a step-by-step alternative entry
- **141 standard templates (Musterbriefe)** — pre-written medical letters for common diagnoses, from *Abszess* to *Zeckenstich*, updated from the clinical library
- **Patient records** — per-patient history, searchable
- **Billing** — Stripe-hosted Checkout and Portal (test-mode), subscription plans
- **Admin panel** — manage letter templates, users, settings
- **Compliance pack** — internal docs: Verarbeitungsverzeichnis, AVV-Checkliste, TOM, Löschkonzept, Betroffenenrechte, Bedrohungsmodell, MDR-Grenzbestimmung, Auftragsverarbeitung, Bibliothekslizenz, Vorlagenhygiene
- **Research retrieval** — web-based evidence collection for generated letters
- **Pseudonymisation** — patient identifiers are tokenised before every model call and re-inserted after
- **Multi-language UI** — German and English interfaces

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Python 3, FastAPI, SQLAlchemy 2.0 |
| Frontend | Jinja2 + HTMX + hand-rolled CSS |
| Database | SQLite (WAL) — Postgres only if a second worker appears |
| AI | Server-side stateless model call (DeepSeek, configurable) |
| Billing | Stripe Checkout / Customer Portal |
| Deployment | Docker, Portainer stack, Caddy reverse proxy |
| Test | pytest — 357 automated checks |

Architecture and decisions are documented in `docs/01-architecture.md`.

---

## Quick start (development)

```bash
# Clone
git clone git@github.com:phontary/briefato.git
cd briefato

# Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

# Run tests
cd app && .venv/bin/python -m pytest tests/

# Start the app
cd app && .venv/bin/uvicorn briefato.main:app --reload
```

**Configuration** is loaded from environment variables (`deploy/stack.env.example` lists every key). A local `.env` or `stack.env` file is read if present; never commit secrets.

---

## Deployment

Production runs on the box (`phontary`, N305) in a Docker container behind Caddy, managed through Portainer (stack 69).

- `deploy/docker-compose.yml` — the stack definition (image `briefato:latest`, built locally)
- `deploy/deploy-staging.sh` — rsync repo to host, rebuild image, update stack
- `deploy/caddy-briefato.caddyfile` — reverse proxy config
- `deploy/sync-to-host.sh` — copy code tree to the host

The app answers at `briefato.sabry.io` on the LAN.

---

## Project structure

```
app/                  Python package (briefato/) + tests/
  briefato/           app package
    main.py           FastAPI entry point
    brain/            generation engine (triage, retrieval, prompt assembly, rule checker)
    pipeline/         letter generation (fan-out, prompts, providers, pseudonymisation)
    routes/           all web routes (chat, wizard, patients, billing, admin, …)
    templates/        Jinja2 templates
    static/           CSS and JavaScript
  tests/              357 automated checks
brain/                medical content (musterbriefe library, standards, rule set)
deploy/               Docker, Caddy, Portainer, backup scripts
docs/                 architecture, specifications, compliance pack, beta plan
    compliance/        Verarbeitungsverzeichnis, AVV, TOM, MDR-boundary, … (11 files)
    eval/runs/        LLM-judge scorecards and evaluation evidence
landing/              public marketing site (index, pricing, data protection, terms)
tools/                CDP screenshot utilities, eval harness, pack-brain.py
```

Full documentation is in `docs/01-architecture.md` through `docs/08-beta-release-plan.md`.

---

## Release cycle

One improvement a week, every Tuesday at 17:00 UTC, run by the **Briefato weekly improvement loop** (job `ce4c4659917d` of the Phontary Holding manager). Each cycle picks one change, tests it, and commits to `main`. Changes that need deployment to the host are handled separately.

See the report ledger at `phontary/projects/briefato/reports/` (inside the record).

---

## License

MIT — see `LICENSE`.