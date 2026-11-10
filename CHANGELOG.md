# Changelog

All notable changes to briefato. This file is maintained from the weekly improvement loop.

---

## 2026-11-10 — v0.2.0

- **Template sync with Schreibdienst archive:** 17 of the 141 packaged Musterbriefe templates were outdated; all are now at the latest version
- **`pack-brain --check` now reports every drifted file** instead of stopping at the first one (T-366, cycle 2)
- **Test suite:** 348 checks (two more), all green
- **Repo pushed to GitHub** (`phontary/briefato`, public); deploy key set up for push from the agent container

## 2026-11-03 — v0.1.1

- **Initial template regeneration:** packaged Musterbriefe templates regenerated from the source archive (cycle 1)
- **Fixed the first cycle's infrastructure:** claim-on-start to prevent duplicate runs, per-app report ledger, all record files checked

## 2026-10-04 — v0.1.0

- **Beta release plan** — frozen workstream contract, ownership map, definition of done per area
- **Production‑ready generation engine:** triage, retrieval, prompt assembly, rule checker (R1–R67), fan-out, enrichment
  - Real-model measured: `must_contain` 94/94 (100 %), LLM-judge mean 4.73/5
- **OP department standards** (`brain/standards`): OP-Berichte 13/13 and 11/11
- **Chat portal** — ChatGPT-style composer, focus fade, self-triage, persisted thread
- **Wizard** — step-by-step alternative entry
- **Patient records, letters, editor, method/library pages**
- **Billing** — Stripe Checkout + Portal, subscription plans (test-mode)
- **Compliance pack** — 11 internal documents (Verarbeitungsverzeichnis, AVV, TOM, …)
- **Deploy** — Docker compose, Caddy, Portainer stack; sync script to the host

## 2026-10-02 — pre-release

- All earlier commits: evaluation scorecards, referee-aware invention check, real-model wiring, provider stability fixes, CDP screenshot tooling, staging verification, deployment automation