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
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests -q

# fan-out + research suites only
BRIEFATO_LLM_MOCK=true .venv/bin/python -m pytest app/tests/test_fanout.py app/tests/test_research.py -q

# real end-to-end smoke: one Arztbrief through the full flow
BRIEFATO_LLM_MOCK=true .venv/bin/python app/briefato/pipeline/scripts/smoke.py

# brain self-check demo: triage + retrieval + generated text + checker findings
.venv/bin/python app/briefato/brain/demo_brain.py

# ENGINE-V2 demo: a 14-source Entlassbrief through segmenter → fan-out → weave + enrichment
BRIEFATO_LLM_MOCK=true .venv/bin/python tools/demo_fanout.py --max-parallel 3 --enrich
```

## Fan-out pipeline + grounded enrichment (WORKSTREAM-ENGINE-V2)

Mohamed's decision (2026-10-02): a **stationary** letter (Entlass-/Aufnahme-/Verlegungsbrief)
with **more than five** source documents is processed as a fan-out — every source is summarised
separately, then the whole thing is rewritten (weave) into the final document.

| File | Responsibility |
|---|---|
| `segmenter.py` | Split a KIS-style multi-source input into labelled segments (Anamnese/KU, imaging, endoscopy, OP, Pathologie, Diabetologie, Pflege, Visiten, Labor, Konsile …) with a per-segment confidence. Robust to form-label noise, duplicate labels (adjacent merge, non-adjacent `duplicate_of`) and missing labels (one `rohtext` fallback). |
| `routing.py` | `decide_route(doc_type, source_count)` — stationary **and** `>5` sources → `fan-out`, else `single-pass`; emits reason + UI label `Route: Fan-out (14 Quellen)`. Threshold: `BRIEFATO_FANOUT_THRESHOLD` (default 5). |
| `fanout.py` | Bounded-parallel per-segment compression (**hard cap 3**, `BRIEFATO_MAX_PARALLEL`, clamped 1–8) with a `ConcurrencyTracker`, then ONE weave call. A segment that fails is retried once; a still-failing segment becomes a reported **gap** (never invented, never silently dropped). `TrackedProvider` counts calls and peak concurrency. |
| `../research/base.py` | `Enrichment` (statement + source), `ResearchProvider`, `NullEnricher`, and the generic-knowledge guardrail (`is_generic_statement`/`filter_generic`): blocks dates, dosings, ICD codes, patient identifiers, patient-possessives and verbatim dictation copies. |
| `../research/archive.py` | `ArchiveEnricher` — derives standard technique / materials / follow-up from the retrieved Musterbriefe (licence-review templates contribute structure only; their prose is never used). |
| `../research/web.py` | `WebEnricher` — optional SearXNG research (`BRIEFATO_RESEARCH_BASE_URL`), query restricted with `site:` operators to awmf.org, pubmed.ncbi.nlm.nih.gov, doccheck.com, msdmanuals.com, leitlinien.de, bfarm.de. |
| `../research/__init__.py` | `GroundedEnricher` (archive first, web only supplements) and `get_research_provider`. |

Enrichment is per-request opt-in (`generate_letter(..., enrich=True)`) with a per-document-type
default: `operationsbericht` is **on by default** (routine OP steps must be completed), every other
type follows the global `BRIEFATO_ENRICH_DEFAULT`; a per-type `BRIEFATO_ENRICH_DEFAULT_<DOC_TYPE>`
(e.g. `BRIEFATO_ENRICH_DEFAULT_OPERATIONSBERICHT=false`) overrides both. The decision and its source
(`request` / `per_type_env` / `global_env` / `doc_type_default`) are reported on
`letter.last_check['enrichment']`. Kept statements are injected into the prompt as
`REFERENZWISSEN (generisch, nicht patientenbezogen)`, returned on `letter.enrichments` and
`letter.last_check['enrichment']` (UI note „aus Referenz ergänzt – bitte prüfen“) and audited as
event `letter.enriched` with the sources. If research is off or unavailable the letter is still
produced without it.

`generate_letter` gained keyword-only parameters (`enrich`, `max_parallel`, `research_provider`); the
frozen signature and the single-pass behaviour are unchanged (≤5 sources, non-stationary types).

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
