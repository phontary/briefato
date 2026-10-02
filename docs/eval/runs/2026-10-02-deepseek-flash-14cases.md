# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-195804-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T19:58:04+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** — (nicht konfiguriert)
- **Fälle:** 14/14 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.520 |
| Mean Token-Jaccard | 0.785 |
| **Echo-Fälle** | **2/14** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 8/14 |
| Harte Regel-Findings (Summe) | 1 |
| Weiche Regel-Findings (Summe) | 3 |
| Fälle mit harten Findings | 1 |
| must_contain-Abdeckung | 1.000 (94/94) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 0 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | — |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `ambulant-01` | ambulant | ✓ | 0 | 1 | 4/4 | 0.226 | 0.889 | C-ECHO | ok |
| `ambulant-02` | ambulant | ✓ | 0 | 0 | 4/4 | 1.000 | 1.000 | ECHO | ok |
| `aufnahmebrief-01` | arztbrief | ✓ | 0 | 0 | 3/3 | 0.437 | 0.673 | — | ok |
| `entlassbrief-01` | arztbrief | ✓ | 0 | 0 | 8/8 | 0.738 | 0.802 | — | ok |
| `entlassbrief-02` | arztbrief | ✓ | 0 | 0 | 7/7 | 0.800 | 1.000 | C-ECHO | ok |
| `entlassbrief-03` | arztbrief | ✓ | 1 | 0 | 8/8 | 0.786 | 0.895 | C-ECHO | ok |
| `entlassbrief-04` | arztbrief | ✓ | 0 | 0 | 7/7 | 0.954 | 0.925 | ECHO | ok |
| `entlassbrief-05` | arztbrief | ✓ | 0 | 0 | 6/6 | 0.780 | 0.870 | C-ECHO | ok |
| `entlassmedikationsplan-01` | entlassmedikationsplan | ✓ | 0 | 0 | 8/8 | 0.015 | 0.746 | — | ok |
| `opbericht-01` | operationsbericht | ✓ | 0 | 1 | 13/13 | 0.468 | 0.250 | — | ok |
| `opbericht-02` | operationsbericht | ✓ | 0 | 1 | 11/11 | 0.301 | 0.231 | — | ok |
| `pflegebericht-01` | pflegebericht | ✓ | 0 | 0 | 5/5 | 0.034 | 0.939 | C-ECHO | ok |
| `verlegungsbericht-01` | arztbrief | ✓ | 0 | 0 | 5/5 | 0.715 | 0.936 | C-ECHO | ok |
| `zusammenfassung-01` | zusammenfassung | ✓ | 0 | 0 | 5/5 | 0.021 | 0.829 | — | ok |

## Details

### `ambulant-01` — Ambulanter/tageschirurgischer Brief — Leistenhernie

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 4/4
- Echo: similarity=0.226, token_ratio=0.898, jaccard=0.889 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Hinweis: R58: KEIN 'stationär aufnehmen'-Satz, KEINE Therapie-Maßnahmen-Liste. Ambulante Empfehlungen sind Fließtext, kein Label.

### `ambulant-02` — Ambulanter Brief — NFA-Vorstellung, Kopfplatzwunde eines Kindes

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 4/4
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: Rein konservative NFA-Vorstellung ohne OP. Keine stationären Blöcke, kein Aufnahmesatz.

### `aufnahmebrief-01` — Aufnahmebrief — akute Appendizitis, OP ausstehend

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 3/3
- Echo: similarity=0.437, token_ratio=0.742, jaccard=0.673 → eigene Formulierung (kein Echo)
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- Hinweis: Aufnahmebrief: Verlauf läuft weiter (OP am Folgetag). KEIN Empfehlungsblock, KEINE stationäre Therapieliste (R30/R31-Analogon).

### `entlassbrief-01` — Stationärer Entlassbrief — akute Cholezystitis, laparoskopische Cholezystektomie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.738, token_ratio=0.821, jaccard=0.802 → eigene Formulierung (kein Echo)
- Hinweis: Kernfall: 12 KIS-Quellen, alle Blöcke diktiert. Prüft Blockreihenfolge und vollständige Diagnoseliste. Hinweis: 'Nachweis'-Wortlaut vermeiden — der bestehende Triage-Treffer '\bnachweis' würde sonst fälschlich auf Weiterbildungs-Nachweise routen (vom Harness als Typ-Fehlschlag erkannt).

### `entlassbrief-02` — Stationärer Entlassbrief — mediale Schenkelhalsfraktur, Hüft-TEP

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=0.800, token_ratio=0.889, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Hinweis: 16 KIS-Quellen. Enthält eine Z.n.-Zeile im Diagnosenblock (R23) und Komorbiditäten.

### `entlassbrief-03` — Stationärer Entlassbrief — ambulant erworbene Pneumonie mit Delir

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 0 weich — hart: R6
- must_contain: 8/8
- Echo: similarity=0.786, token_ratio=0.854, jaccard=0.895 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Hinweis: Internistischer Fall. Pflege-/Verlaufsinformationen müssen eingewoben, nicht als Block zitiert werden.

### `entlassbrief-04` — Stationärer Entlassbrief — Rektumkarzinom, anteriore Rektumresektion

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=0.954, token_ratio=0.969, jaccard=0.925 → ECHO (keine eigene Formulierung)
- Hinweis: Onkologischer Fall. Prüft, ob Tumorstadium und OPS-freie Therapieliste korrekt übernommen werden.

### `entlassbrief-05` — Stationärer Entlassbrief — akute Divertikulitis, konservative Therapie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 6/6
- Echo: similarity=0.780, token_ratio=0.803, jaccard=0.870 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Hinweis: Konservativ behandelter Fall ohne OP — Therapieblock enthält keine OP-Zeile. Nebenerkrankungen = keine.

### `entlassmedikationsplan-01` — Entlassmedikationsplan anpassen — Dosisabweichungen und bedingter Verabreichungsplan

- Erwarteter Typ: `entlassmedikationsplan` · tatsächlich: `entlassmedikationsplan` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.015, token_ratio=0.860, jaccard=0.746 → eigene Formulierung (kein Echo)
- Hinweis: R63: nur Text im Chat. Dosisabweichung NICHT stillschweigend korrigieren, sondern Prüfhinweis (R45/AP-15). Kein PDF/HTML-Export.

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 13/13
- Echo: similarity=0.468, token_ratio=0.409, jaccard=0.250 → eigene Formulierung (kein Echo)
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `opbericht-02` — OP-Bericht — Narbenhernie, Sublay-Netzimplantation (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 11/11
- Echo: similarity=0.301, token_ratio=0.350, jaccard=0.231 → eigene Formulierung (kein Echo)
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['Präparat:']
- Hinweis: Zweiter Enrichment-Fall. Fehlhörer 'Sableb-Technik' → 'Sublay-Technik' (R44) im Quellmaterial angedeutet.

### `pflegebericht-01` — Pflegebericht-Integration — umfangreiche Pflegedokumentation zu einem Verlauf

- Erwarteter Typ: `pflegebericht` · tatsächlich: `pflegebericht` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.034, token_ratio=0.954, jaccard=0.939 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Hinweis: Pflegejargon filtern (AP-16): 'zur Nacht versorgt', 'laut AO', 'SK' dürfen NICHT übernommen werden; klinisch Relevantes (Wundzustand, Stuhlgang, Schmerz, SpO2) wird eingewoben.

### `verlegungsbericht-01` — Verlegungsbericht — zur dringenden operativen Versorgung, Zielklinik XXX

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.715, token_ratio=0.800, jaccard=0.936 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- Hinweis: Verlegungsbrief: KEIN Empfehlungsblock (R31), Zielklinik bleibt Platzhalter XXX (R32).

### `zusammenfassung-01` — Zusammenfassung — mehrzeitiger Verlauf

- Erwarteter Typ: `zusammenfassung` · tatsächlich: `zusammenfassung` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.021, token_ratio=0.864, jaccard=0.829 → eigene Formulierung (kein Echo)
- Hinweis: R24: keine Diagnoseliste und keine Therapie-Maßnahmen-Liste — auch wenn das Diktat eine Diagnosen-Zeile enthält. Datum abgekürzt als Monat.
