# Briefato brain package

`briefato.brain` makes the generation pipeline use Mohamed's harvested method
(`/workspace/briefato/brain`, 436 KB of markdown extracted from the Schreibdienst
profile) instead of the previous invented generic prompt. The markdown under
`<repo>/brain` is an **input** and is never modified by code.

## Modules

| module | responsibility |
|---|---|
| `brain_loader.py` | cached loaders for `kern.md`, `regelwerk.md`, `ANTI-PATTERNS.md`, the 9 `dokumenttypen/*.md` playbooks and `musterbriefe/manifest.json` |
| `triage.py` | Auftragsart → Dokumenttyp (the `kern.md` routing table), incl. combined orders → two documents |
| `retrieval.py` | indication-keyword scoring against the merged Musterbrief manifest (144 entries) |
| `stopwords.py` | German stopwords + generic clinical qualifiers (akut/chronisch/…) used by the scorer |
| `muster_merge.py` | near-duplicate merge builder (reads `brain/merges/merge-map.json`) used by the packer and tests |
| `prompt_assembly.py` | builds the system + user prompt from kern/regelwerk/anti-patterns/playbook/structure; mandates plain text |
| `rule_checker.py` | deterministic checks enforcing R1–R67 + the ANTI-PATTERNS with a rule id per finding |
| `demo_brain.py` | runnable self-check demo (see below) |

## Brain directory resolution

`brain_loader.brain_root()` resolves the brain in this order:

1. `BRIEFATO_BRAIN_DIR` — **authoritative**: if set and invalid it raises
   `BrainNotFound` (no silent fallback);
2. `<repo>/brain`, where `<repo>` is three levels above this package
   (`app/briefato/brain/brain_loader.py` → `/workspace/briefato`);
3. the nearest ancestor of this package that contains `brain/kern.md`.

The Musterbrief markdown lives outside the app (read-only Schreibdienst archive).
It is resolved from `BRIEFATO_MUSTERBRIEFE_DIR`, else the manifest's `source`
(`/workspace/schreibdienst/musterbriefe`).

## Governance gates

* **Scrub-pending templates are never retrievable** — `Cholezystolithiasis.md`,
  `Acne-inversa.md`, `Struma_nodosa_Hyperthyreose.md` carry patient traces
  (`brain/musterbriefe/scrub-report.md`). They are dropped before scoring and can
  never appear in a result.
* **Licence-review templates are returned `reference_only=True`** —
  `Coxarthrose_Exsikkose_Sturz.md`, `Pangastritis.md`, `Papillaere_Pankreatitis.md`,
  `Proktitis.md` (`licence_risk == "review"`). Only their **section structure** is
  passed to the prompt; their licensed prose is never shipped
  (`brain/musterbriefe/licence-review.md`).

## Retrieval scoring (precision fix, WORKSTREAM-BRAIN-V2)

`retrieval.retrieve()` separates indication signal from noise:

* an exact `indication_keywords` hit scores **6.0**; a title token **5.0**; the
  filename stem **4.0**; a conservative substring overlap (both tokens ≥ 6 chars)
  **1.2**;
* German stopwords (`stopwords.STOPWORDS`) are ignored; generic clinical
  qualifiers (`stopwords.QUALIFIERS`/`QUALIFIER_PREFIXES`: akut*, chronisch*,
  links/rechts*, stationär*, aufgenommen, Patient/in, …) are down-weighted to
  **0.15**, so three adjectives can never beat one indication keyword;
* multi-word phrase hits add **4.0** (keyword phrase) / **3.0** (title phrase);
* umlauts/ß are normalised on both sides;
* every hit carries a German `reason` such as `Stichwort: Divertikulitis`.

Regression coverage: the 15 self-test queries must rank 1
(`test_retrieval_selftest_queries_rank_first`) and 10 adversarial queries — incl.
the staging diverticulitis dictation, `Subduralhämatom`, `Gallensteine`,
`Leistenhernie … TAPP`, `TVT` — must beat any template that only shares a generic
adjective (`test_retrieval_adversarial_generic_adjective_never_wins`,
`test_diverticulitis_dictation_beats_subdural_template`).

## Near-duplicate merges (product copy only)

The read-only archive `/workspace/schreibdienst/musterbriefe` is **never modified**.
Near-duplicates are merged only in the packaged product copy:

* `brain/merges/merge-map.json` lists 7 groups (11 absorbed source files) and the
  deliberate non-merges with reasons;
* `briefato.brain.muster_merge` builds one deterministic template per group (four
  clinical sections merged, `## Quellen` preserved, all remaining statements kept,
  only exact/near-identical duplicate lines dropped);
* `tools/pack-brain.py` generates the merged files, deletes the superseded files in
  `brain/musterbriefe/templates/`, and rewrites `manifest.json` (one entry per kept
  template, absorbed synonyms folded into `indication_keywords`, `merged_from`
  recorded); `--check` regenerates and byte-compares.

`brain/merges/REPORT.md` documents every group and non-merge.

## Mock provider

`MockProvider` (dev/staging) no longer echoes the dictation. It composes a
method-shaped draft from the dictation: plain text, no markdown, no category
labels, prose first, then the labelled blocks in the document-type order
(`ambulante Therapieempfehlungen nach der Entlassung:` → `Diagnosen:` →
`Nebenerkrankungen:` → `Therapie-Maßnahmen auf der Station:` for a stationary
discharge letter). It states only diagnoses present in the dictation (else
`keine Angabe im Diktat`) and never invents clinical facts; for method-shaped
input it passes the R1–R67 checker with no hard findings.

## Self-check

```bash
cd /workspace/briefato
.venv/bin/python -m pytest app/tests -q
.venv/bin/python tools/pack-brain.py --check
.venv/bin/python brain/musterbriefe/retrieval_selftest.py          # 15/15
.venv/bin/python brain/selfcheck_kern.py && .venv/bin/python brain/selfcheck_praxis.py
.venv/bin/python app/briefato/brain/demo_brain.py
```

The demo prints, for a realistic German ward dictation: the triage decision, the
retrieved Musterbriefe with scores, the generated text (offline `MockProvider`) and
the checker findings — then the checker on a compliant hand-written Arztbrief.

## Design decisions & deviations (reported, not silent)

These are the points where the workstream had to make a call the frozen contract did
not spell out. Each is a **report item**, not a change to a frozen artefact.

1. **"setting" without touching `config.py`.** `config.Settings` is frozen and owned
   by SYSADMIN, so the brain path is read from the `BRIEFATO_BRAIN_DIR` environment
   variable (with the repo-relative default). No `config.py` edit was made.
2. **`Letter.kind` now carries the resolved document type.** The pipeline stores the
   real type (`zusammenfassung`, `operationsbericht`, …). `entlassmedikationsplan`
   (21 chars) and `weiterbildung-kv-nachweise` (25 chars) exceed the frozen
   `Letter.kind` `String(20)`. SQLite (dev/staging) tolerates this; a strict DB would
   truncate/reject. Recommend widening the column — `models.py` was not touched.
3. **Legacy portal kinds.** The frozen `letters.kind` dropdown still submits
   `arztbrief|attest|befund|ueberweisung|sonstiges`. Triage treats `arztbrief` as the
   default hint and lets a specific dictation order win; the other four have no brain
   playbook and fall through to dictation routing. `routes/` was not touched.
4. **Audit detail without a schema change.** The `Generation` row has no JSON column,
   so the per-letter retrieval/check detail is persisted via `security.audit(...)`
   (event `letter.generated`) and returned on the `Letter` as the runtime attribute
   `letter.last_check`. `Generation.error` carries a compact JSON diagnostics string
   **only on failure**.
5. **Retrieval self-test: 15/15 top-1.** `brain/musterbriefe/retrieval_selftest.py`
   keeps its own (unchanged) scorer and still hits 15/15 against the merged manifest.
   The app-side scorer deliberately never returns the scrub-pending
   `Cholezystolithiasis.md` for "Gallensteine mit Kolik"; the next-best hit is still a
   biliary template and this is asserted explicitly in `test_brain.py`.
6. **Mock output is now method-shaped (V2).** `MockProvider` composes prose + the
   document-type labels from the dictation (never inventing clinical facts) instead of
   echoing it, so dev/staging demos show the real product shape and method-shaped input
   passes R1–R67 with no hard findings.
7. **Retrieval scorer rewritten (V2).** Indication keywords/title phrases dominate;
   generic clinical adjectives are down-weighted via `stopwords.py`; substring matching
   needs ≥ 6 characters on both sides; every hit returns a German `reason`.
8. **Near-duplicates merged in the product copy (V2).** `brain/merges/merge-map.json` +
   `muster_merge.py` + `tools/pack-brain.py` produce one template per group in
   `brain/musterbriefe/templates/` and rewrite `manifest.json`; the archive is untouched.

## Runtime / deployment requirement (reported, not applied)

The pipeline now needs `<repo>/brain` at runtime. `app/Dockerfile` (SYSADMIN-owned)
currently copies only `app/` and `landing/`, so the staging image must add

```dockerfile
COPY brain /srv/briefato/brain
```

or the Portainer stack must set `BRIEFATO_BRAIN_DIR` and mount the brain. Without it,
generation raises `BrainNotFound` (by design — the loader fails loudly, it never
silently degrades to the old generic prompt).

The Musterbrief **markdown archive** is not needed at runtime: retrieval and prompt
assembly read only `brain/musterbriefe/manifest.json` (titles, keywords, section
lists, licence/scrub flags). `BRIEFATO_MUSTERBRIEFE_DIR` / the manifest `source` are
only used if a caller reads a template file explicitly via
`brain_loader.read_template()`.

No new third-party dependency was introduced, so no `app/requirements.pipeline.txt`
was created.

