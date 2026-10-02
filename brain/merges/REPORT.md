# Near-duplicate merge — product copy only (WORKSTREAM-BRAIN-V2)

**Date:** 2026-10-02 · **Scope:** `brain/musterbriefe/templates/` (product copy) and
`brain/musterbriefe/manifest.json` · **Archive:** `/workspace/schreibdienst/musterbriefe`
is **read-only and untouched** (verified by sha256 before/after — see *Verification*).

Driven by Mohamed's 2026-10-02 decision that the near-duplicate Musterbriefe must be
merged, and executed only in the packaged copy produced by `tools/pack-brain.py`.

## Detection rule

Near-duplicate = **(a)** title token-set Jaccard ≥ 0.75, **OR (b)** title difflib ratio
≥ 0.75, **OR (c)** Klinik-section token-set Jaccard ≥ 0.90. The automated pass over the
152 manifest entries yields **11 candidate pairs** (matching the manifest's own
`duplicate_pairs: 11`). Each candidate was then reviewed against the manifest: pairs that
describe clinically **distinct** entities are deliberately *not* merged (see below), and
the groups Mohamed named explicitly were confirmed. The final set is 7 groups covering
11 absorbed files.

## Merged groups

| # | Group | Kept (product file) | Absorbed | Distinct statements | Primary lines: source → merged / dropped |
|---|---|---|---|---|---|
| 1 | Erysipel | `Erysipel.md` | `Erysipel_Wundrose.md` | Identical keywords (Erysipel/Wundrose/Hautinfektion); the Wundrose file adds the admission picture + Verlauf | 28 → 28 / 0 |
| 2 | pAVK | `pAVK.md` | `pAVK_Mediasklerose.md` | Mediasklerose adds the unusable-ABI special case + CO2 angiography | 29 → 29 / 0 |
| 3 | Narbenhernie epigastrisch | `Narbenhernien_epigastrisch.md` | `Narbenhernie_epigastrische_IPOM.md` | IPOM file adds the concrete IPOM case + OP/Verlauf block | 17 → 17 / 0 |
| 4 | Pankreatitis (biliär/papillär) | `Biliaere_Pankreatitis.md` | `Papillaere_Pankreatitis.md` | Papillary file adds ERCP/papillotomy statements; `## Quellen` preserved | 27 → 27 / 0 |
| 5 | Diabetes mellitus Typ 1/2 | `Diabetes_mellitus.md` *(new)* | `Diabetes_mellitus_Typ1.md`, `Diabetes_mellitus_Typ2.md` | Both type-specific statements kept | 32 → 32 / 0 |
| 6 | Kontusion der Zehen | `Kontusion_Zehen.md` *(new)* | `Kontusion_Kleinzehe.md`, `Kontusion_Mittelzehe.md`, `Kontusion_Grosszehe.md` | Per-digit statements kept; only identical shared Klinik/Diagnostik lines dropped | 42 → 24 / **18** |
| 7 | Kontusion Grundgelenk Finger | `Kontusion_Grundgelenk_Finger.md` *(new)* | `Kontusion_Grundgelenk_Kleinfinger.md`, `Kontusion_Grundgelenk_Ringfinger.md` | Both finger statements kept | 8 → 8 / 0 |

**What moved where.** For every group the four clinical sections **(Klinik, Diagnostik,
Therapie, Nachsorge)** of all members are concatenated in source order and de-duplicated;
`## Quellen` is preserved verbatim when present (group 4); every remaining section
(KU, Verlauf, Diagnosen, OP, Anamnese, ICD-Code, …) is appended so no clinical statement
is lost. The merged file is generated deterministically by
`briefato.brain.muster_merge.build_merged_content` (no timestamps), so `pack-brain.py
--check` can regenerate and byte-compare.

**What was intentionally dropped.** Only exact or near-identical duplicate lines
(normalised containment ≥ 0.8) — 18 in group 6, 0 in the other groups. No distinct
clinical statement was removed.

## Deliberately NOT merged (with reason)

* `Chronische_Niereninsuffizienz_CKD3.md` ↔ `…_dialysepflichtig.md` — dialysis yes/no; clinically distinct.
* `Leistenhernie_Inguinalhernie_TAPP.md` ↔ `…_Lichtenstein.md` — two operative techniques.
* `Cholezystolithiasis.md` ↔ `Choledocholithiasis.md` — gallbladder vs bile-duct stones; the former is also scrub-pending/locked.
* `Nadelstichverletzung.md`, `Stichverletzung.md`, `Bissverletzung.md` — different injury aetiologies sharing only "Verletzung".
* `Insektenstich.md` ↔ `Zeckenstich.md` — different exposures/prophylaxis.
* `Abrissfraktur-Basis-MFK-V.md` ↔ `Metatarsalefraktur_Basis_MFK_II.md` — different metatarsals (V vs II).
* `Distorsion_Daumen_Grundgelenk.md` ↔ `Distorsion_Sprunggelenk.md` — different joints.
* `Kontusion_Handruecken.md`, `Prellung.md`, `Schulterprellung.md`, `Kniedistorsion.md`, `HWS-Distorsion_Schleudertrauma.md` — distinct regions/entities.

## Manifest + packaged-copy changes

* `manifest.json`: one entry per kept template. Absorbed synonyms and former titles are
  folded into `indication_keywords`, and the kept entry records `merged_from` (the list of
  absorbed files). `count` 152 → **144**; `counts.duplicate_pairs` → 0;
  `counts.merged_groups` = 7; `counts.files_absorbed` = 11.
* `brain/musterbriefe/templates/`: 149 → **141** packaged templates (3 locked excluded);
  the 11 absorbed files are deleted, the 7 kept/merged files are (re)generated. The
  Pankreatitis merge keeps `licence_risk = review` (Papillaere was review), so the
  licence-review set stays at 4.
* `packaged.json` records the sha256 of every file incl. merged ones; the README in the
  packaged dir lists the merged groups.

## Verification (real outputs)

```
$ .venv/bin/python tools/pack-brain.py
packaged 141 templates (7 merged, removed 11 stale), locked 3, licence-review 4, missing 0
$ .venv/bin/python tools/pack-brain.py --check
OK: 141 packaged templates match (7 merged groups, 3 locked)
$ sha256sum archive before/after → identical (ARCHIVE UNCHANGED)
```

## Retrieval before/after (the same dictation)

The staging defect: for the diverticulitis dictation the subdural template outranked the
correct one because the old scorer treated the title token `auf` as a match inside
`aufgenommen` and weighted generic adjectives (`akut`, `chronisch`) like indication
keywords.

Dictation: *"Die Patientin wurde mit akuter linksseitiger Unterbauchschmerzsymptomatik
und Fieber stationär aufgenommen. Sonographisch Nachweis einer entzündlich verdickten
Sigma-Schlinge. Bei bekannter chronischer Divertikulose. Wir nahmen die Patientin zur
i.v. Antibiotikatherapie stationär aufgenommen."*

| Rank | BEFORE (old scorer, 152-entry manifest) | AFTER (new scorer, merged manifest) |
|---|---|---|
| 1 | `Akut_auf_chronisches_Subduralhaematom.md` **1.978** | `Akute_Divertikulitis.md` **6.000** *(Stichwort: sigma)* |
| 2 | `Akute_Divertikulitis.md` 1.766 | `Chronisch_entzuendliche_Colonveraenderungen_sigmoidal.md` 1.380 |
| 3 | `Chronisch_entzuendliche_Colonveraenderungen_sigmoidal.md` 1.522 | `Anastomositis_nach_Hemikolektomie.md` 1.200 |

The subdural template is not returned at all for the diverticulitis dictation after the
fix. (The parent's staging figures 1.21 vs 1.03 were produced by the deployed pre-fix
revision; the exact numbers were not reproducible in-repo, but the failure mode is the
same and is now eliminated — asserted by
`test_diverticulitis_dictation_beats_subdural_template`.)

Other adversarial cases (after): `Subduralhämatom…` → `Akut_auf_chronisches_Subduralhaematom.md`
(6.0) · `Gallensteine…` → `Gallenblasenpolypen_Konkremente_Verdacht.md` (6.0) ·
`Leistenhernie … TAPP` → `…_TAPP.md` (12.0) · `TVT …` → `Tiefe_Beinvenenthrombose_TVT.md`
(7.2). All 15 self-test queries rank 1.
