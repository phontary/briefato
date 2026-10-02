# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-204614-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T20:48:16+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** deepseek-flash
- **Fälle:** 2/2 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.193 |
| Mean Token-Jaccard | 0.143 |
| Echo-Schwelle | 0.85 (Standard); entlassmedikationsplan 0.92, zusammenfassung 0.92 |
| **Echo-Fälle** | **0/2** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 0/2 |
| Harte Regel-Findings (Summe) | 1 |
| Weiche Regel-Findings (Summe) | 4 |
| Fälle mit harten Findings | 1 |
| must_contain-Abdeckung | 1.000 (24/24) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 0 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | 5.000 |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `opbericht-01` | operationsbericht | ✓ | 0 | 2 | 13/13 | 0.188 | 0.143 | — | ok |
| `opbericht-02` | operationsbericht | ✓ | 1 | 2 | 11/11 | 0.198 | 0.144 | — | ok |

## Details

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 2 weich
- must_contain: 13/13
- Echo: similarity=0.188, token_ratio=0.237, jaccard=0.143 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-01.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Blockfolge Indikation → OP → Präparat → Diagnosen → Operation entspricht exakt dem vorgegebenen Nutzerstandard und dem Diktataufbau; Nachblöcke (Präparat, Diagnosen, Operation) korrekt am Ende.
    - completeness: Alle Diktatfakten sind abgebildet: 54-jährige Patientin, symptomatische Cholezystolithiasis ohne Anhalt für Gallenwegsobstruktion, symptomatisches Steinleiden, geplantes Vorgehen, OP-Datum 23.09.2026, chronisch entzündete Gallenblase mit multiplen Konkrementen, Präparatangabe ad Histologie, Diagnose und Operationsbezeichnung.
    - no_invention: Keine patientenbezogene Erfindung; die über das Diktat hinausgehenden Operationsschritte (Team-Time-out, gefärbte Hautdesinfektion, steriles Abdecken, transumbilikaler 10-mm-Trokar mit Capnoperitoneum bis 12 mmHg, fußtiefe Linkslagerung, epigastrischer 10-mm- sowie zwei 5-mm-Trokare, Metall-Clips zentral doppelt/peripher einfach, monopolare Präparation, Extraktionsbeutel, Faszienschluss mit Novosyn 0) sind aus Referenz gedeckt; die Angaben zur Narkoseform, Nüchternheit sowie Aufklärung und Einwilligung stammen aus Referenz (verbindliches Nutzer-Gerüst). — „Bei symptomatischem Steinleiden erfolgte am 23.09.2026 in Allgemeinanästhesie mit Intubation die geplante laparoskopische Cholezystektomie. Die Patientin ist nüchtern, Aufklärung und Einwilligung liegen vor. [aus Referenz]“
    - register: Sachlich-fachlicher Stil, gängige Abkürzungen (mmHg, mm) direkt verwendet, keine Füllwörter; die Blockbezeichnungen stehen als Überschriften, nicht als Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, durchgehend korrekte Umlaute und Sonderzeichen, kein Semikolon im Text.
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `opbericht-02` — OP-Bericht — Narbenhernie, Sublay-Netzimplantation (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 2 weich — hart: R-INVENT
- must_contain: 11/11
- Echo: similarity=0.198, token_ratio=0.239, jaccard=0.144 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-02.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Reihenfolge Indikation, OP, Präparat, Diagnosen, Operation exakt nach Playbook; Abschlussblöcke am Dokumentende.
    - completeness: Alle Diktatfakten sind enthalten: 68-jähriger Patient, Narbenhernie nach Medianlaparotomie, zunehmende Größe und Beschwerden, OP-Datum 29.09.2026, Sublay-Technik, Netzimplantation 15 x 20 cm, intraoperativ ca. 6 cm große Narbenhernie ohne Inkarzeration, Diagnosen und Operation.
    - no_invention: Keine ungedeckten patientenbezogenen Angaben. Rückenlage, Intubationsnarkose, Hautdesinfektion, sterile Abdeckung, Team-Time-out, Bruchsackresektion mit Histologie, Monomax der Stärke 0 in Small-bite-Technik, Redon-Drainagen, Bauchgurt und Abschlusssatz sind aus Referenz gedeckt; die Netzgröße 15 x 20 cm stammt aus dem Diktat. — „Präparat: Bruchsack, Präparat ad Histologie.“
    - register: Sachlicher fachsprachlicher Stil, korrekte Abkürzungen, keine Füllwörter; die Labels entsprechen der geforderten Berichtstruktur.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon.
- Hinweis: Zweiter Enrichment-Fall. Fehlhörer 'Sableb-Technik' → 'Sublay-Technik' (R44) im Quellmaterial angedeutet.
