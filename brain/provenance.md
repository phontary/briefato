---
asset: briefato-brain/provenance
brain_version: 1.0.0
source_profile: /home/hermeswebui/.hermes/profiles/schreibdienst/
extraction_date: 2026-10-02
language: en (content de)
---

# Provenance — what was taken, from where, and what was deliberately left out

Source profile (READ-ONLY, never modified): `/home/hermeswebui/.hermes/profiles/schreibdienst/`.
Deliverable root: `/workspace/briefato/brain/`.
Legend: `SOUL` = SOUL.md · `MEM` = memories/MEMORY.md · `USER` = memories/USER.md ·
Skill paths are under `skills/medizin/<name>/`.

## 1. Asset → source → taken → left out

| Asset | Source file(s) | What was taken | Deliberately left out (and why) |
|---|---|---|---|
| `kern.md` K0–K1 (purpose, 5 SOUL rules) | `SOUL.md` | Faithful reproduction of the 5 output rules + the "rewrite, don't invent" task | Nothing; reproduced verbatim-true in German |
| `kern.md` K2 (routing) | SOUL.md, `schreibdienst/SKILL.md` | Routing table incl. default, OP-Bericht, Zusammenfassung, ambulant, combined orders | Hermes-specific run mechanics (skill_view, delegate_task, parallel tool blocks) — agent-runtime detail, not part of the writing method |
| `kern.md` K3 (formatting 0–11) | `schreibdienst/SKILL.md`, `stolperfallen/SKILL.md`, `zusammenfassung`, `ambulant`, `pflegeberichte-integration` | All mandatory output-shape rules, abbreviations policy, block order, death formula, therapy list, KIS defaults, semicolon rule | Concrete patient case narratives (Lemke, Jauk, Guist, Ridder, Grunwald, Lang, Hannig, Westburg, Decher…) used as precedent evidence — replaced by generic example lines; the case names are patient data |
| `kern.md` K4 (dictation correction) | `diktat-tippfehler/SKILL.md`, `stolperfallen/SKILL.md`, `stolperfallen/references/*` | Silent-correction rule, genus/typo/grammar rules, boundaries, impossible-dose exception, phoneme lists | The full raw phoneme lists are summarised; individual patient identifiers inside them removed |
| `kern.md` K5 (language/register) | `schreibdienst`, `stolperfallen`, `MEM`, `USER` | Register, user term preferences, humanizer scope, "user version wins" | Gym/fitness and learning-session notes from USER.md (unrelated to the writing method) |
| `kern.md` K6–K7 (structure, prohibitions) | `schreibdienst`, `stolperfallen`, `operationsbericht`, `references/kis-export-luecken.md` | Musterbrief structure logic, chain order, all "never invent" rules | Internal archive-maintenance mechanics (patch vs. write_file, dedupe scripts, index counters, grep pitfalls) — Hermes tooling, not product output |
| `kern.md` K8 (user-facing replies) | `schreibdienst`, `stolperfallen`, `entlassmedikationsplan`, `MEM`, `USER` | Inline-question rule, brevity, no tables/emoji, no PDF export, user language | clarify-tool internals; cron/gateway/watchdog infrastructure notes from MEM |
| `dokumenttypen/arztbrief.md` | `schreibdienst/SKILL.md`, `stolperfallen/SKILL.md`, `entlassbrief-triage`, `references/kis-export-lueken.md`, SOUL | Section order, blocks, mandatory content, pitfalls | Session/precedent case names, archive-update steps, pipeline phases (parse/fan-out/weave) |
| `dokumenttypen/operationsbericht.md` | `operationsbericht/SKILL.md` + `references/standard-che-laparoskopisch.md`, `references/standard-narbenhernie-sublay.md` | Structure, style, standards, house standards (sublay, lap CHE) as technique rules | The verbatim user template wording containing "der 35-jährigen Patientin"/"82-jährigen Patienten" — rewritten as generic example lines |
| `dokumenttypen/zusammenfassung.md` | `zusammenfassung/SKILL.md`, `auftragskombinationen-und-fallrecherche.md` | Sentence/episode rules, date style, block exclusion | Case examples (Littig, Lang) only as genericised examples |
| `dokumenttypen/ambulant.md` | `ambulant/SKILL.md`, `entlassbrief-triage/SKILL.md`, `schreibdienst` | Trigger, section order, phrase variants, OP-compression, exclusions | The concrete child case (eyebrow laceration) reduced to a generic NFA example |
| `dokumenttypen/entlassbrief.md` | `entlassbrief-triage/SKILL.md`, `schreibdienst`, `stolperfallen` | Routing decision, kurzstationär exception, sub-type decision | Precedent patient names |
| `dokumenttypen/entlassmedikationsplan.md` | `entlassmedikationsplan/SKILL.md`, `MEM` | Output order, parsing rules, pitfalls, no-PDF rule | The full precedent case (Guist: name, DOB, weight, height, exact medication rows) — patient data, removed |
| `dokumenttypen/pflegebericht.md` | `pflegeberichte-integration/SKILL.md`, `stolperfallen`, `staging-workup-integration.md` | Extraction rules, jargon decoding, weaving rules | Case-specific nursing quotes with identifiers |
| `dokumenttypen/ablehnungsbogen.md` | `ablehnungsbogen-thieme-compliance/SKILL.md` | Field order, mandatory content, style, pitfalls | Both case examples (patient names, DOB, FallNr) — patient data, removed |
| `dokumenttypen/weiterbildung-kv-nachweise.md` | `weiterbildung-kv-nachweise/SKILL.md` + references, `kv-genehmigung-und-weiterbildung/SKILL.md` | Answer structure, three-level separation, pitfalls, form/law facts | Landesland-specific raw figures kept as structure only; no licensed prose copied |
| `regelwerk.md` | all of the above | 67 numbered, testable rules | Nothing additional |
| `selfcheck_kern.py` | — | Self-contained check (stdlib only) | — |

## 2. Scrubbing required (real patient data found in sources — NOT copied)

These source files contained real patient-identifying data. The data was **not** copied into the brain;
example lines are generic. Flagged for a data-protection review of the source profile itself.

| Source file | Patient data found | Action taken |
|---|---|---|
| `skills/medizin/ablehnungsbogen-thieme-compliance/SKILL.md` | Full name, date of birth, FallNr, clinic (two case examples) | Omitted entirely; replaced with generic example lines |
| `skills/medizin/entlassmedikationsplan/SKILL.md` | Full name, date of birth, weight, height, full medication list (one case) | Omitted entirely; generic example lines only |
| `skills/medizin/stolperfallen/SKILL.md` | Multiple patient surnames (case precedents) | Omitted; rules kept without names |
| `skills/medizin/zusammenfassung/SKILL.md` | Surname in worked example | Omitted; genericised |
| `skills/medizin/schreibdienst/SKILL.md` | Surnames + one DOB in precedent narratives | Omitted; rules kept without names/DOB |
| `skills/medizin/operationsbericht/SKILL.md` + `references/standard-narbenhernie-sublay.md` | Age + hernia size + OP date of a specific patient (template wording) | Omitted; generic example lines |
| `skills/medizin/kv-genehmigung-und-weiterbildung/SKILL.md` | DOB/weight of one case | Omitted |
| `skills/medizin/stolperfallen/references/diktat-fehlhoerer-fuss-abszess-dfs.md` | One patient DOB + clinical course | Omitted; only the phoneme-correction rules kept |

## 3. Licence review needed

Material researched from AMBOSS / DocCheck / PubMed / Springer / MSD Manual / AWMF / AO Surgery Reference
(see the `## Quellen` sections and the web-research instructions in the sources). No licensed prose was
copied — only structure/rules were extracted in our own words. Sources to review:

| Source file | Licensed/third-party source | What was used | Status |
|---|---|---|---|
| `skills/medizin/schreibdienst/references/icd-10-und-frakturklassifikationen.md` | AO Surgery Reference, medcode.ch, springermedizin.de/emedpedia, online-oup.de | ICD/AO/OTA/Lisfranc classification structure (own words) | licence review needed |
| `skills/medizin/schreibdienst/references/musterbrief-bereinigung-und-validierung.md` | DocCheck Flexikon, MSD Manual, PubMed/NCBI, AWMF, AMBOSS (public access only) | Web-research allowed-source list | licence review needed |
| `skills/medizin/schreibdienst/SKILL.md` (§ „Web-Recherche bei Neuanlage") | AMBOSS, DocCheck, PubMed/Medline, AWMF-Leitlinien | Research policy for new Musterbriefe | licence review needed |
| `skills/medizin/klinische-pharmakologie/references/antibiotika-weichteilinfektionen.md` | Fachinfo/BfArM/Gelbe-Liste | Antibiotic first-line + Rote-Hand-Brief status facts | licence review needed |
| `skills/medizin/weiterbildung-kv-nachweise/references/kbv-ultraschallvereinbarung.md` | KBV/GKV QS-Vereinbarung (public legal text) | § structure and Anlage-I numbers | low risk (public law) — flagged for completeness |
| `skills/medizin/weiterbildung-kv-nachweise/references/wbo-richtzahlen.md` | Landesärztekammer Hessen WBO (public legal text) | Richtzahlen structure | low risk (public law) — flagged for completeness |

## 4. Left out for other reasons

| Category | Examples | Why |
|---|---|---|
| Infrastructure / system | server paths inside rules, `/workspace/schreibdienst/...` paths, gateway/cron/watchdog notes, container restart notes, `log.md` handling | Machine-/instance-specific; not product content |
| Personal data (not patient) | Mohamed's private gym notes, learning-session structure, personal DOB handling rules | Unrelated to the writing method |
| Hermes runtime mechanics | `skill_view`/`skill_manage`, `delegate_task`, parallel tool blocks, curator passes, state-db/FTS recovery | Agent-runtime details; the product calls a stateless model |
| Archive maintenance tooling | patch-vs-write_file, dedupe scripts, index counters, grep umlaut pitfalls, fan-out cleanup playbooks | Operational; the product owns its own store |
| Raw Musterbrief archive | `/workspace/schreibdienst/musterbriefe/` (153 files) | Out of scope for the *method* extraction; may be a separate workstream |

## 5. Known gaps / could not determine

- The source does **not** define the exact current spoken instruction for the entlassmedikationsplan output
  line order beyond the KIS-adaptation flow; reproduced from the one authoritative description.
- Several "Nutzerfassung" rules reference dates and case names whose full context (raw input) is not in the
  profile; the rule text was taken as canonical, the underlying case was not.
- "op-iterationen" is referenced as a sibling skill but no `op-iterationen/SKILL.md` exists in the source
  tree; its behaviour could not be extracted.
- Two advisory skills (`klinische-pharmakologie`, and the WBO/KV material) are knowledge banks, not
  document types; distilled into rules + playbooks but their deep content is intentionally not duplicated.
