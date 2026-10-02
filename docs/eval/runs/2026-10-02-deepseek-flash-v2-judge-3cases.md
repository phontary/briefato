# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-201840-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T20:19:28+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** deepseek-flash
- **Fälle:** 3/3 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.917 |
| Mean Token-Jaccard | 0.959 |
| Echo-Schwelle | 0.85 (Standard); entlassmedikationsplan 0.92, zusammenfassung 0.92 |
| **Echo-Fälle** | **3/3** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 3/3 |
| Harte Regel-Findings (Summe) | 1 |
| Weiche Regel-Findings (Summe) | 1 |
| Fälle mit harten Findings | 1 |
| must_contain-Abdeckung | 0.840 (21/25) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 0 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | 4.870 |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `ambulant-02` | ambulant | ✓ | 0 | 0 | 4/4 | 1.000 | 1.000 | ECHO | ok |
| `entlassbrief-03` | arztbrief | ✓ | 1 | 0 | 8/8 | 0.883 | 0.918 | ECHO | ok |
| `opbericht-01` | operationsbericht | ✓ | 0 | 1 | 9/13 | 0.869 | 0.958 | ECHO | ok |

## Details

### `ambulant-02` — Ambulanter Brief — NFA-Vorstellung, Kopfplatzwunde eines Kindes

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 4/4
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `ambulant`): 0.850 | Text: `cases/ambulant-02.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Playbook-Reihenfolge eingehalten: Anamnese/Untersuchung, dann Therapie, Diagnosen als Block am Ende.
    - completeness: Alle im Diktat genannten Fakten sind enthalten (Vorstellung mit Mutter, Sturz beim Spielen, 0,5 cm Platzwunde oberhalb der linken Augenbraue, Neurologie unauffällig, Desinfektion, Fibrinkleber, Pflaster, Aufklärung, Selbstabfall nach 3 Tagen, keine stationäre Aufnahme, beide Diagnosen).
    - no_invention: Keine zusätzlichen Diagnosen, Codes, Daten, Medikamente oder Konsile hinzugefügt.
    - register: Sachlicher fachlicher Stil, Abkürzungen (NFA, KU) direkt verwendet, keine Füllwörter, keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute und ß, nur ein Semikolon.
- Hinweis: Rein konservative NFA-Vorstellung ohne OP. Keine stationären Blöcke, kein Aufnahmesatz.

### `entlassbrief-03` — Stationärer Entlassbrief — ambulant erworbene Pneumonie mit Delir

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 0 weich — hart: R6
- must_contain: 8/8
- Echo: similarity=0.883, token_ratio=0.861, jaccard=0.918 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-03.txt`
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Grundreihenfolge (Anamnese, Diagnostik, Therapie/Verlauf, Empfehlungen) und Blockbildung am Ende sind eingehalten; der Aufnahme-Satz wurde jedoch entgegen der Diktatreihenfolge vor die Befundbeschreibung gezogen. — „Wir nahmen die Patientin zur weiteren Diagnostik bzw. Schmerztherapie stationär auf.“
    - completeness: Alle im Diktat genannten klinisch relevanten Fakten sind enthalten: Symptomkonstellation, Rö/CT-Befund inkl. fehlendem Pleuraerguss, Aufnahmegrund, Antibiose mit Besserung, Delirtherapie, komplikationslose Entlassung am 05.10.2026, Empfehlungen, Diagnosen, Nebenerkrankungen und Therapiemaßnahmen.
    - no_invention: Keine zusätzlichen Diagnosen, ICD-Codes, Daten, Laborwerte, Medikamentennamen oder Konsile; die Umformulierung 'stellte sich ... vor' fügt keinen neuen Fakt hinzu.
    - register: Durchgängig sachlicher fachlicher Stil, gängige Abkürzungen (CT, Rö-Befund) ohne Füllwörter; Kategoriebezeichnungen erscheinen nur als Blocküberschriften, nicht im Fließtext.
    - plain_text: Reiner Text ohne Markdown, Umlaute korrekt (Röntgen, stationär, häusliche, hausärztlich, für) und kein Semikolon verwendet.
- Hinweis: Internistischer Fall. Pflege-/Verlaufsinformationen müssen eingewoben, nicht als Block zitiert werden.

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 1 weich
- must_contain: 9/13 — fehlt: Team-Time-out, Desinfektion, Capnoperitoneum, Wundverschluss
- Echo: similarity=0.869, token_ratio=0.935, jaccard=0.958 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-01.txt`
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Blockfolge Indikation → OP → Präparat → Diagnosen → Operation ist nachvollziehbar und die Befundblöcke stehen am Ende; das OP-Datum wurde jedoch in den Indikationsblock gezogen und der Block 'Operation' wiederholt lediglich den Eingriff, was die Blocklogik leicht verwässert.
    - completeness: Alle im Diktat genannten Fakten sind enthalten: 54-jährige Patientin, symptomatische Cholezystolithiasis ohne Anhalt für Gallenwegsobstruktion, symptomatisches Steinleiden, geplante laparoskopische Cholezystektomie, Datum 23.09.2026, intraoperativer Befund mit chronisch entzündeter Gallenblase und multiplen Konkrementen, Präparat ad Histologie sowie Diagnose- und Operationsangabe.
    - no_invention: Es erscheinen keine zusätzlichen Diagnosen, Codes, Datumsangaben, Laborwerte, Medikamente oder Konsile; alle Angaben sind wörtlich aus dem Diktat ableitbar.
    - register: Sachlicher fachlicher Stil, korrekte direkte Verwendung der Fachbegriffe, keine Füllwörter; die vorangestellten Rubriken fungieren als Blocküberschriften und nicht als Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute (54-jährigen, Cholezystolithiasis, für, entzündete), kein Semikolon verwendet.
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).
