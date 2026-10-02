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
| `retrieval.py` | diagnose keyword matching against the 152 Musterbriefe |
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

## Self-check

```bash
cd /workspace/briefato
.venv/bin/python -m pytest app/tests/test_brain.py app/tests/test_pipeline.py -q
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
5. **Retrieval self-test: 14/15 exact.** The 15th query ("Gallensteine mit Kolik")
   expects `Cholezystolithiasis.md`, which is scrub-pending and must never be
   retrieved. The next-best hit is still a biliary template; the exclusion is asserted
   explicitly in `test_brain.py`.
6. **Mock output is now brain-faithful.** `MockProvider` echoes the dictation instead
   of inventing a salutation and a `Betreff:` heading (both anti-patterns), so the
   end-to-end test can produce a compliant letter and the checker sees intact blocks.
7. **Retrieval scorer.** The `brain/musterbriefe/retrieval_selftest.py` scorer is
   reused, with the per-query `len(query)` division dropped (ranking-preserving) so
   long free-text dictations are usable, plus German synonym expansion.

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

