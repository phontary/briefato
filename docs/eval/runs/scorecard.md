# Briefato — Qualitäts-Scorecard

> ⚠️ **MOCK — misst KEINE Schreibqualität**
>
> Dieser Lauf nutzt den Mock-Provider. Er misst die **Maschinerie** (Routing, Retrieval, Block-/Regelkonformität, Speicherung) — **nicht** die Schreibqualität eines Modells. Ein Echtheits-Urteil erfordert `--provider openai` mit einem echten Modell und der freigegebenen (lawyer/DSGVO-Approved) Route.

## Lauf

- **Run-ID:** `20261002-192730-mock-briefato-mock-de-1`
- **Zeit (UTC):** 2026-10-02T19:27:30+00:00
- **Provider:** `mock` · **Modell:** `briefato-mock-de-1`
- **Base-URL:** —
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** — (nicht konfiguriert)
- **Fälle:** 14/14 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.936 |
| Mean Token-Jaccard | 0.962 |
| **Echo-Fälle** | **11/14** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 13/14 |
| Harte Regel-Findings (Summe) | 0 |
| Weiche Regel-Findings (Summe) | 2 |
| Fälle mit harten Findings | 0 |
| must_contain-Abdeckung | 0.872 (82/94) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 2 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | — |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `ambulant-01` | ambulant | ✓ | 0 | 0 | 4/4 | 1.000 | 1.000 | ECHO | ok |
| `ambulant-02` | ambulant | ✓ | 0 | 0 | 4/4 | 1.000 | 1.000 | ECHO | ok |
| `aufnahmebrief-01` | arztbrief | ✓ | 0 | 0 | 3/3 | 1.000 | 1.000 | ECHO | ok |
| `entlassbrief-01` | arztbrief | ✓ | 0 | 0 | 8/8 | 1.000 | 1.000 | ECHO | ok |
| `entlassbrief-02` | arztbrief | ✓ | 0 | 0 | 7/7 | 0.953 | 1.000 | ECHO | ok |
| `entlassbrief-03` | arztbrief | ✓ | 0 | 0 | 8/8 | 1.000 | 1.000 | ECHO | ok |
| `entlassbrief-04` | arztbrief | ✓ | 0 | 0 | 7/7 | 1.000 | 1.000 | ECHO | ok |
| `entlassbrief-05` | arztbrief | ✓ | 0 | 0 | 6/6 | 1.000 | 1.000 | ECHO | ok |
| `entlassmedikationsplan-01` | entlassmedikationsplan | ✓ | 0 | 0 | 8/8 | 1.000 | 1.000 | ECHO | ok |
| `opbericht-01` | operationsbericht | ✓ | 0 | 1 | 8/13 | 0.784 | 1.000 | C-ECHO | ✗ |
| `opbericht-02` | operationsbericht | ✓ | 0 | 1 | 7/11 | 0.760 | 1.000 | C-ECHO | ✗ |
| `pflegebericht-01` | pflegebericht | ✓ | 0 | 0 | 5/5 | 1.000 | 1.000 | ECHO | ok |
| `verlegungsbericht-01` | arztbrief | ✓ | 0 | 0 | 5/5 | 1.000 | 1.000 | ECHO | ok |
| `zusammenfassung-01` | zusammenfassung | ✓ | 0 | 0 | 2/5 | 0.604 | 0.474 | — | ok |

## Details

### `ambulant-01` — Ambulanter/tageschirurgischer Brief — Leistenhernie

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 4/4
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
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
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- Hinweis: Aufnahmebrief: Verlauf läuft weiter (OP am Folgetag). KEIN Empfehlungsblock, KEINE stationäre Therapieliste (R30/R31-Analogon).

### `entlassbrief-01` — Stationärer Entlassbrief — akute Cholezystitis, laparoskopische Cholezystektomie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: Kernfall: 12 KIS-Quellen, alle Blöcke diktiert. Prüft Blockreihenfolge und vollständige Diagnoseliste. Hinweis: 'Nachweis'-Wortlaut vermeiden — der bestehende Triage-Treffer '\bnachweis' würde sonst fälschlich auf Weiterbildungs-Nachweise routen (vom Harness als Typ-Fehlschlag erkannt).

### `entlassbrief-02` — Stationärer Entlassbrief — mediale Schenkelhalsfraktur, Hüft-TEP

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=0.953, token_ratio=0.963, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: 16 KIS-Quellen. Enthält eine Z.n.-Zeile im Diagnosenblock (R23) und Komorbiditäten.

### `entlassbrief-03` — Stationärer Entlassbrief — ambulant erworbene Pneumonie mit Delir

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: Internistischer Fall. Pflege-/Verlaufsinformationen müssen eingewoben, nicht als Block zitiert werden.

### `entlassbrief-04` — Stationärer Entlassbrief — Rektumkarzinom, anteriore Rektumresektion

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: Onkologischer Fall. Prüft, ob Tumorstadium und OPS-freie Therapieliste korrekt übernommen werden.

### `entlassbrief-05` — Stationärer Entlassbrief — akute Divertikulitis, konservative Therapie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 6/6
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: Konservativ behandelter Fall ohne OP — Therapieblock enthält keine OP-Zeile. Nebenerkrankungen = keine.

### `entlassmedikationsplan-01` — Entlassmedikationsplan anpassen — Dosisabweichungen und bedingter Verabreichungsplan

- Erwarteter Typ: `entlassmedikationsplan` · tatsächlich: `entlassmedikationsplan` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: R63: nur Text im Chat. Dosisabweichung NICHT stillschweigend korrigieren, sondern Prüfhinweis (R45/AP-15). Kein PDF/HTML-Export.

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 8/13 — fehlt: Indikation:, Team-Time-out, Desinfektion, Capnoperitoneum, Wundverschluss
- Echo: similarity=0.784, token_ratio=0.838, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Struktur: fehlende Blöcke ['Indikation:'], Reihenfolge ok, kanonisch fehlend ['Indikation:']
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `opbericht-02` — OP-Bericht — Narbenhernie, Sublay-Netzimplantation (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 7/11 — fehlt: Indikation:, Team-Time-out, Desinfektion, Wundverschluss
- Echo: similarity=0.760, token_ratio=0.778, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Struktur: fehlende Blöcke ['Indikation:'], Reihenfolge ok, kanonisch fehlend ['Indikation:', 'Präparat:']
- Hinweis: Zweiter Enrichment-Fall. Fehlhörer 'Sableb-Technik' → 'Sublay-Technik' (R44) im Quellmaterial angedeutet.

### `pflegebericht-01` — Pflegebericht-Integration — umfangreiche Pflegedokumentation zu einem Verlauf

- Erwarteter Typ: `pflegebericht` · tatsächlich: `pflegebericht` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Hinweis: Pflegejargon filtern (AP-16): 'zur Nacht versorgt', 'laut AO', 'SK' dürfen NICHT übernommen werden; klinisch Relevantes (Wundzustand, Stuhlgang, Schmerz, SpO2) wird eingewoben.

### `verlegungsbericht-01` — Verlegungsbericht — zur dringenden operativen Versorgung, Zielklinik XXX

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- Hinweis: Verlegungsbrief: KEIN Empfehlungsblock (R31), Zielklinik bleibt Platzhalter XXX (R32).

### `zusammenfassung-01` — Zusammenfassung — mehrzeitiger Verlauf

- Erwarteter Typ: `zusammenfassung` · tatsächlich: `zusammenfassung` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 2/5 — fehlt: Rückenschmerzen, Nov. 2025, Sep. 2026
- Echo: similarity=0.604, token_ratio=0.600, jaccard=0.474 → eigene Formulierung (kein Echo)
- Hinweis: R24: keine Diagnoseliste und keine Therapie-Maßnahmen-Liste — auch wenn das Diktat eine Diagnosen-Zeile enthält. Datum abgekürzt als Monat.
