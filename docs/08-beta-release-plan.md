# Briefato — beta release plan & workstream contract (frozen for wave 1)

Owner decision (2026-10-02, evening): finish the product today with parallel workstreams. This file is
the **contract**: the ownership map, the frozen interfaces, and the definition of done per workstream.
A workstream that needs a change to something it does not own must **report it**, never alter it.

## Where we actually are (verified, not claimed)

| Area | State |
|---|---|
| Generation engine (brain, triage, retrieval, prompt, rule checker R1–R67, fan-out, enrichment) | done; measured on the real model: `must_contain` 94/94 = 100 %, LLM-judge mean 4.73/5 |
| Department OP standards (`brain/standards`) | done; OP-Berichte 13/13 and 11/11, routine steps grounded (soft `R-REFERENZ`) |
| Chat portal (`/app/chat`) | done: centred composer, rotating capability line, focus fade, self-triage + one clarifying question, persisted per-case thread refining the **same** letter, `XXX` placeholders highlighted + counted |
| Wizard (`/app/neu`) | kept as an alternative entry |
| Portal shell, patients, letters, editor, method/library pages | working, **designed before the nizam design language** → visually inconsistent |
| Billing (Stripe module + simulation) | implemented; test-mode only, no live prices/keys |
| Compliance pack (`docs/compliance/01–11`) | drafted; legal review pending |
| Deploy (Caddy, Portainer stack 69, sync script) | working; **no backup for the encrypted clinical data volume yet** |
| Host capacity (N305) | fine: 31.8 GB RAM (15.7 GB available), load 2.5, `/mnt/fast` 31 % — the earlier 88 % reading is stale |
| Tests | 346 green (offline) |
| Residual quality defects | 3 hard findings: `R6` umlaut autofix miss (`entlassbrief-03`), 2 surviving `R-INVENT` passages (`entlassbrief-04`, `opbericht-02`) |

## Ownership map (wave 1 — nobody writes outside their row)

| Path | Owner |
|---|---|
| `app/briefato/static/**`, `app/briefato/templates/**`, `landing/**` | **WS-DESIGN** |
| `docs/compliance/**`, `docs/legal/**` (new) | **WS-COMPLIANCE** |
| `deploy/**`, `docs/runbooks/**` (new), `tools/backup-*.sh` (new) | **WS-OPS** |
| `app/briefato/brain/rule_checker.py`, `brain/standards/**`, `tools/eval/**`, `docs/05-qualitaetsmessung.md`, `app/tests/test_quality_closure.py` (new) | **WS-QUALITY** |
| everything else (`routes/**`, `models.py`, `pipeline/**`, `research/**`, `docs/01–04`, `docs/06–07`) | **frozen this wave** (parent) |

Rules: no workstream runs `git`, `ssh`, `docker` or edits another row. Each workstream may create new
files (tests, docs, css) but must not modify an existing file outside its row. Tests: existing suite must
stay green; new tests go into the workstream's own new file.

## Frozen interfaces (do not change)

- `POST /app/chat` (form: `message`, `patient_id`, optional `thread`, optional `doc_type_choice`) → renders
  the thread; one model call per turn; persisted in `chat_thread` / `chat_message`.
- `GET /app/chat?thread=<id>` renders a persisted case; foreign id → **404**.
- Letter output: **plain text**, copy-paste ready, `XXX` = open placeholder (the method's own convention:
  "Platzhalter XXX setzen statt zu raten") — must be visibly highlighted and counted wherever a letter is
  rendered.
- Document types (11): arztbrief, entlassbrief, operationsbericht, ambulant, zusammenfassung,
  verlegungsbericht, aufnahmebrief, entlassmedikationsplan, pflegebericht, ablehnungsbogen,
  weiterbildung-kv-nachweise.
- UI conventions: German copy, formal `Sie`, hand-rolled design system (no CSS framework, no build step,
  **zero external requests**, self-hosted font), WCAG AA, dark mode via `prefers-color-scheme`,
  responsive 360–1440 px, working empty/loading/error states.

## Definition of done (wave 1)

**WS-DESIGN** — the nizam design language (`docs/03-design-reference-nizam-margin.md`) applied as tokens
+ components to landing, shell, dashboard, chat, editor, method/library, auth pages; a `/styleguide`
route showing the tokens and components; screenshots (desktop 1440 + mobile 390, light **and** dark, forced
via CDP) for every key route with resolved URL + first heading printed per capture; landing self-check
(`landing/selfcheck.py`) green; **no behaviour change** (no route, field or query edits).

**WS-COMPLIANCE** — the pack becomes delivery-ready: `docs/compliance/12-beta-launch-checklist.md` (what
must be true before a paying customer), the AVV/DPA red-line list for the lawyer, retention & deletion
runnable procedure, the anonymisation-gateway requirement, the third-party licence remediation plan
(DocCheck/MSD/AWMF/PubMed text in 4 templates → replace or remove before sale), the MDR boundary statement,
and German **draft texts** for Impressum / Datenschutz / AGB / AVV marked "Entwurf – juristische Prüfung
ausstehend" with every fill-in field left as a field. Docs only — no HTML (WS-DESIGN owns the pages).

**WS-OPS** — the clinical data can survive a disk/container loss: an encrypted-volume backup job
(age or gpg/pass-based, verify a real restore, document the drill), a restore runbook, a health/monitoring
hook (Healthchecks ping + `healthz`), a deploy rollback note, and a written capacity/latency statement from
measured numbers. Prove it: run the backup, restore into a scratch dir, and diff a row.

**WS-QUALITY** — close the 3 residual defects with evidence: R6 autofix map completed for the failing word
(capture the actual word from the scorecard/run.json first), the 2 surviving `R-INVENT` passages
reproduced deterministically and fixed (better retry instruction or a targeted autofix), then re-run the
14-case gate on the **real model** and record before/after per case. The suite must stay green; new tests in
`app/tests/test_quality_closure.py`.

## What only the owner can decide (not blocked by us, but blocking money)

1. **Custom domain for paid traffic** (the LAN domain stays for staging) + DNS.
2. **Stripe live mode**: KYC, live keys, real prices, tax/VAT handling, invoice texts.
3. **Model provider AVV/DPA** signed (DeepSeek) or a switch to a provider with an EU DPA.
4. **Lawyer review** of the legal drafts + the licence-tainted templates.
5. **Beta testers** (3–5 practices) and their onboarding route.
6. Voice input v1: yes/no, and which STT path (local Whisper vs provider).
