# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-201629-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T20:18:38+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** — (nicht konfiguriert)
- **Fälle:** 14/14 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.652 |
| Mean Token-Jaccard | 0.918 |
| Echo-Schwelle | 0.85 (Standard); entlassmedikationsplan 0.92, zusammenfassung 0.92 |
| **Echo-Fälle** | **3/14** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 11/14 |
| Harte Regel-Findings (Summe) | 1 |
| Weiche Regel-Findings (Summe) | 3 |
| Fälle mit harten Findings | 1 |
| must_contain-Abdeckung | 0.925 (87/94) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 0 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | — |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `ambulant-01` | ambulant | ✓ | 0 | 1 | 4/4 | 0.940 | 0.962 | ECHO | ok |
| `ambulant-02` | ambulant | ✓ | 0 | 0 | 4/4 | 1.000 | 1.000 | ECHO | ok |
| `aufnahmebrief-01` | arztbrief | ✓ | 0 | 0 | 3/3 | 0.672 | 0.975 | C-ECHO | ok |
| `entlassbrief-01` | arztbrief | ✓ | 0 | 0 | 8/8 | 0.800 | 0.883 | C-ECHO | ok |
| `entlassbrief-02` | arztbrief | ✓ | 0 | 0 | 7/7 | 0.800 | 1.000 | C-ECHO | ok |
| `entlassbrief-03` | arztbrief | ✓ | 1 | 0 | 8/8 | 0.424 | 0.944 | C-ECHO | ok |
| `entlassbrief-04` | arztbrief | ✓ | 0 | 0 | 7/7 | 0.821 | 1.000 | C-ECHO | ok |
| `entlassbrief-05` | arztbrief | ✓ | 0 | 0 | 6/6 | 0.414 | 0.786 | — | ok |
| `entlassmedikationsplan-01` | entlassmedikationsplan | ✓ | 0 | 0 | 8/8 | 0.005 | 0.872 | — | ok |
| `opbericht-01` | operationsbericht | ✓ | 0 | 1 | 9/13 | 0.917 | 0.958 | ECHO | ok |
| `opbericht-02` | operationsbericht | ✓ | 0 | 1 | 8/11 | 0.665 | 0.615 | — | ok |
| `pflegebericht-01` | pflegebericht | ✓ | 0 | 0 | 5/5 | 0.034 | 0.939 | C-ECHO | ok |
| `verlegungsbericht-01` | arztbrief | ✓ | 0 | 0 | 5/5 | 0.728 | 1.000 | C-ECHO | ok |
| `zusammenfassung-01` | zusammenfassung | ✓ | 0 | 0 | 5/5 | 0.913 | 0.923 | C-ECHO | ok |

## Details

### `ambulant-01` — Ambulanter/tageschirurgischer Brief — Leistenhernie

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 4/4
- Echo: similarity=0.940, token_ratio=0.940, jaccard=0.962 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `ambulant`): 0.850 | Text: `cases/ambulant-01.txt`
- Hinweis: R58: KEIN 'stationär aufnehmen'-Satz, KEINE Therapie-Maßnahmen-Liste. Ambulante Empfehlungen sind Fließtext, kein Label.

### `ambulant-02` — Ambulanter Brief — NFA-Vorstellung, Kopfplatzwunde eines Kindes

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 0 weich
- must_contain: 4/4
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `ambulant`): 0.850 | Text: `cases/ambulant-02.txt`
- Hinweis: Rein konservative NFA-Vorstellung ohne OP. Keine stationären Blöcke, kein Aufnahmesatz.

### `aufnahmebrief-01` — Aufnahmebrief — akute Appendizitis, OP ausstehend

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 0 weich
- must_contain: 3/3
- Echo: similarity=0.672, token_ratio=0.871, jaccard=0.975 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/aufnahmebrief-01.txt`
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- Hinweis: Aufnahmebrief: Verlauf läuft weiter (OP am Folgetag). KEIN Empfehlungsblock, KEINE stationäre Therapieliste (R30/R31-Analogon).

### `entlassbrief-01` — Stationärer Entlassbrief — akute Cholezystitis, laparoskopische Cholezystektomie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.800, token_ratio=0.854, jaccard=0.883 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-01.txt`
- Hinweis: Kernfall: 12 KIS-Quellen, alle Blöcke diktiert. Prüft Blockreihenfolge und vollständige Diagnoseliste. Hinweis: 'Nachweis'-Wortlaut vermeiden — der bestehende Triage-Treffer '\bnachweis' würde sonst fälschlich auf Weiterbildungs-Nachweise routen (vom Harness als Typ-Fehlschlag erkannt).

### `entlassbrief-02` — Stationärer Entlassbrief — mediale Schenkelhalsfraktur, Hüft-TEP

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=0.800, token_ratio=0.889, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-02.txt`
- Hinweis: 16 KIS-Quellen. Enthält eine Z.n.-Zeile im Diagnosenblock (R23) und Komorbiditäten.

### `entlassbrief-03` — Stationärer Entlassbrief — ambulant erworbene Pneumonie mit Delir

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 0 weich — hart: R6
- must_contain: 8/8
- Echo: similarity=0.424, token_ratio=0.873, jaccard=0.944 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-03.txt`
- Hinweis: Internistischer Fall. Pflege-/Verlaufsinformationen müssen eingewoben, nicht als Block zitiert werden.

### `entlassbrief-04` — Stationärer Entlassbrief — Rektumkarzinom, anteriore Rektumresektion

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=0.821, token_ratio=0.897, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-04.txt`
- Hinweis: Onkologischer Fall. Prüft, ob Tumorstadium und OPS-freie Therapieliste korrekt übernommen werden.

### `entlassbrief-05` — Stationärer Entlassbrief — akute Divertikulitis, konservative Therapie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 6/6
- Echo: similarity=0.414, token_ratio=0.772, jaccard=0.786 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-05.txt`
- Hinweis: Konservativ behandelter Fall ohne OP — Therapieblock enthält keine OP-Zeile. Nebenerkrankungen = keine.

### `entlassmedikationsplan-01` — Entlassmedikationsplan anpassen — Dosisabweichungen und bedingter Verabreichungsplan

- Erwarteter Typ: `entlassmedikationsplan` · tatsächlich: `entlassmedikationsplan` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.005, token_ratio=0.935, jaccard=0.872 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `entlassmedikationsplan`): 0.920 | Text: `cases/entlassmedikationsplan-01.txt`
- Hinweis: R63: nur Text im Chat. Dosisabweichung NICHT stillschweigend korrigieren, sondern Prüfhinweis (R45/AP-15). Kein PDF/HTML-Export.

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 1 weich
- must_contain: 9/13 — fehlt: Team-Time-out, Desinfektion, Capnoperitoneum, Wundverschluss
- Echo: similarity=0.917, token_ratio=0.915, jaccard=0.958 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-01.txt`
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `opbericht-02` — OP-Bericht — Narbenhernie, Sublay-Netzimplantation (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 1 weich
- must_contain: 8/11 — fehlt: Team-Time-out, Desinfektion, Wundverschluss
- Echo: similarity=0.665, token_ratio=0.767, jaccard=0.615 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-02.txt`
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['Präparat:']
- Hinweis: Zweiter Enrichment-Fall. Fehlhörer 'Sableb-Technik' → 'Sublay-Technik' (R44) im Quellmaterial angedeutet.

### `pflegebericht-01` — Pflegebericht-Integration — umfangreiche Pflegedokumentation zu einem Verlauf

- Erwarteter Typ: `pflegebericht` · tatsächlich: `pflegebericht` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.034, token_ratio=0.954, jaccard=0.939 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `pflegebericht`): 0.850 | Text: `cases/pflegebericht-01.txt`
- Hinweis: Pflegejargon filtern (AP-16): 'zur Nacht versorgt', 'laut AO', 'SK' dürfen NICHT übernommen werden; klinisch Relevantes (Wundzustand, Stuhlgang, Schmerz, SpO2) wird eingewoben.

### `verlegungsbericht-01` — Verlegungsbericht — zur dringenden operativen Versorgung, Zielklinik XXX

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.728, token_ratio=0.843, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/verlegungsbericht-01.txt`
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- Hinweis: Verlegungsbrief: KEIN Empfehlungsblock (R31), Zielklinik bleibt Platzhalter XXX (R32).

### `zusammenfassung-01` — Zusammenfassung — mehrzeitiger Verlauf

- Erwarteter Typ: `zusammenfassung` · tatsächlich: `zusammenfassung` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.913, token_ratio=0.914, jaccard=0.923 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `zusammenfassung`): 0.920 | Text: `cases/zusammenfassung-01.txt`
- Hinweis: R24: keine Diagnoseliste und keine Therapie-Maßnahmen-Liste — auch wenn das Diktat eine Diagnosen-Zeile enthält. Datum abgekürzt als Monat.
