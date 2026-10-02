# Briefato — letter-generation pipeline (`WORKSTREAM-PIPELINE`)

Server-side function that turns a member's raw dictation into a finished, letterhead-correct
German letter. Implements the frozen API in `docs/02-spec-interfaces.md` §6 and decisions
D4–D7 in `docs/01-architecture.md`.

## Modules

| File | Responsibility |
|---|---|
| `pseudonym.py` | `Pseudonymizer` — tokenises patient identifiers before any model call, restores them afterwards. |
| `providers.py` | `LLMResult`, `LLMProvider`, `MockProvider` (offline), `OpenAICompatProvider` (httpx, retries), `get_provider`. |
| `prompts.py` | Versioned German prompt engineering (`PROMPT_VERSION = "de-1"`), per-kind structure, anti-hallucination rules. |
| `letterhead.py` | `render_docx(...)` — A4, DIN 5008 oriented DOCX with sender block, date, patient block, bold subject, body, signature, footer. |
| `generate.py` | `generate_letter(...)` — orchestration: triage → retrieve → prompt → model → restore → rule-check → encrypted store → Generation row → quota → audit. |
| `../brain/` | The harvested method (kern/regelwerk/anti-patterns/playbooks/manifest) with triage, retrieval, prompt assembly and the deterministic rule checker. See `app/briefato/brain/README.md`. |
| `scripts/smoke.py` | Reproducible end-to-end smoke check. |

## Brain wiring (WORKSTREAM-BRAIN-WIRING)

`generate_letter` is now driven by the harvested brain instead of an invented generic prompt:

1. **Triage** (`brain.triage.triage`) maps the dictation (+ the frozen `kind` hint) to a real
   document type per the `kern.md` routing table; combined orders ("OP-Bericht + Zusammenfassung")
   yield both documents.
2. **Retrieval** (`brain.retrieval.retrieve`) matches the masked dictation against the 152
   Musterbriefe. Scrub-pending templates are never returned; licence-review templates are flagged
   `reference_only` and contribute **structure only**.
3. **Prompt assembly** (`brain.prompt_assembly.build_prompt`) embeds kern/regelwerk/anti-patterns,
   the document-type playbook, the retrieved sections, the letterhead and the member's
   `letterhead_json['custom_rules']` — and mandates plain text (no markdown/labels/intro,
   `Diagnosen:` at the end, the labelled blocks in order).
4. **Rule check** (`brain.rule_checker.check`) enforces R1–R67 + the anti-patterns in code. Hard
   violations trigger one retry with the findings as correction instructions; if they persist, the
   letter is still delivered (`status="done"`) with a short summary in `Letter.error` and the full
   detail on the runtime attribute `letter.last_check` (also written to the `letter.generated`
   audit event).

`prompts.py` (`system_prompt`/`user_prompt`) is kept for the frozen API and used by `render_docx`
labels; the live generation path uses `brain.prompt_assembly`.

## Data-protection guarantee (D4)

`Pseudonymizer.from_patient()` maps each patient field to a stable uppercase token
(`{{LAST_NAME}}`, `{{FIRST_NAME}}`, `{{BIRTH_DATE}}`, `{{INSURANCE_NUMBER}}`, `{{STREET}}`,
`{{ZIP}}`, `{{CITY}}`, `{{PHONE}}`, `{{EMAIL}}`). `mask()` is case-insensitive on the raw value
(longest value first, umlauts/ß preserved) and idempotent — masking already-masked text cannot
corrupt a token. Both common birth-date renderings are covered (`02.03.1974` and `1974-03-02`);
`restore()` re-inserts the canonical German form.

`generate_letter()` masks **both** the dictation and the patient context before building the
prompt, and additionally asserts in code (guarded by `settings.env != "prod"`) that no strong
identifier reached the prompt. The API key lives only in the `Authorization` header and is
never logged or included in exceptions.

## Prompt design and its sources

The system prompt encodes: German only, formal register; the per-kind section order; an explicit
"no invented facts, dates, dosages, medications or diagnoses" rule (allow omission, never
fabrication); keep `{{TOKENS}}` verbatim; plain paragraphs, no markdown, no commentary, no
disclaimer inside the letter. The user prompt supplies sender data, the masked patient context
and the dictation as the *only* content source.

Per-kind structure:

* **Arztbrief** — Anrede → Betreff → Anamnese → Befund → Diagnose → Therapie/Procedere → Grußformel → Unterschrift
* **Attest** — Zweck → Befund → Beurteilung → Grußformel → Unterschrift
* **Befund** — Fragestellung → Methode → Befund → Beurteilung → Grußformel → Unterschrift
* **Überweisung** — Fragestellung → bisherige Befunde → Auftrag → Grußformel → Unterschrift

Research sources (retrieved 2026-10-02):

1. Wikipedia (de), *Arztbrief* — content and purpose of a transfer letter: diagnoses, anamnesis,
   findings, therapy/course, epicrisis, recommendations; "kurz und prägnant". https://de.wikipedia.org/wiki/Arztbrief
2. praktischArzt.de, *Stiefkind Arztbrief – Wie schreibe ich einen Arztbrief richtig?* — clarity,
   brevity, no filler ("Floskeln"), recommendations phrased as recommendations. https://www.praktischarzt.de/magazin/arztbrief/
3. Scribamed, *Arztbrief Muster: Aufbau, Pflichtangaben und Beispieltext* — mandatory fields and the
   canonical section order (Briefkopf → Diagnosen → Anamnese → Befund → Diagnostik → Therapie/Verlauf
   → Epikrise → Empfehlung/Procedere → Schlussformel + Unterschrift). https://scribamed.de/ratgeber/arztbrief-muster-aufbau
4. Wikipedia (de), *DIN 5008* — letter layout essentials: sender/return-address line ("Rücksendeangabe"),
   §17 Briefgestaltung, subject line un-underlined and emphasizable (*bold*), greeting on the left margin,
   date notation, section spacing. https://de.wikipedia.org/wiki/DIN_5008
5. Anthropic Docs, *Reduce hallucinations* — allow omission instead of guessing ("say I don't know"),
   ground every statement in the provided text, keep claims auditable. https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/reduce-hallucinations
6. praktischArzt.de, *Ärztliches Attest – Fristen, Inhalte und Kosten* — an Attest is a written
   attestation of a health state tied to a stated purpose. https://www.praktischarzt.de/ratgeber/aerztliches-attest/

## Self-check (reproducible)

```bash
cd /workspace/briefato

# unit + integration tests (offline, mock provider)
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_pipeline.py app/tests/test_brain.py -q

# real end-to-end smoke: one Arztbrief through the full flow
BRIEFATO_LLM_MOCK=true .venv/bin/python app/briefato/pipeline/scripts/smoke.py

# brain self-check demo: triage + retrieval + generated text + checker findings
.venv/bin/python app/briefato/brain/demo_brain.py
```

The smoke script prints the letter status, token counts, the encrypted-storage prefix, the DOCX
path and the first 400 characters of the restored German letter.

## Notes / boundaries

* No new dependencies: `httpx` and `python-docx` are already in `app/requirements.txt`, so no
  `app/requirements.pipeline.txt` was needed. The brain workstream added no third-party dependency
  either (stdlib + the existing deps).
* **Deployment requirement (SYSADMIN-owned files, not edited here):** the pipeline now needs
  `<repo>/brain` at runtime. `app/Dockerfile` currently copies only `app/` and `landing/`, so the
  image must also `COPY brain /srv/briefato/brain` (or the compose stack must set
  `BRIEFATO_BRAIN_DIR` and mount the brain). Without it, generation raises `BrainNotFound`. The
  Musterbrief markdown archive is **not** needed at runtime — retrieval and prompt assembly read
  only `brain/musterbriefe/manifest.json`.
* `MockProvider` is deterministic and offline; it now echoes the (masked) dictation verbatim
  (preserving block structure) instead of inventing a salutation and a `Betreff:` heading — those
  are anti-patterns the brain forbids.
* On failure the letter is marked `failed` with a German-safe error string, a failed `Generation`
  row is recorded for observability, the quota is left untouched and a `PipelineGenerationError`
  is raised — the letter is never left in `generating`.
