# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-204121-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T20:42:54+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** deepseek-flash
- **Fälle:** 2/2 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.173 |
| Mean Token-Jaccard | 0.139 |
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
| Mean LLM-Judge (0–5) | 4.000 |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `opbericht-01` | operationsbericht | ✓ | 0 | 2 | 13/13 | 0.179 | 0.158 | — | ok |
| `opbericht-02` | operationsbericht | ✓ | 1 | 2 | 11/11 | 0.167 | 0.119 | — | ok |

## Details

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 2 weich
- must_contain: 13/13
- Echo: similarity=0.179, token_ratio=0.267, jaccard=0.158 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-01.txt`
- LLM-Judge (deepseek-flash): mean=4.2 {'structure': 4, 'completeness': 5, 'no_invention': 2, 'register': 5, 'plain_text': 5}
    - structure: Bericht folgt der Playbook-Logik (Indikation mit Diagnose, OP-Verlauf, dann Blöcke Präparat/Diagnosen/Operation am Ende); nur die Trennung von Indikation und Diagnose ist unscharf, kein echter Regelbruch.
    - completeness: Alle Diktatfakten sind enthalten: 54-jährige Patientin, symptomatische Cholezystolithiasis ohne Gallenwegsobstruktion, geplante laparoskopische Cholezystektomie, OP-Datum 23.09.2026, chronisch entzündete Gallenblase mit multiplen Konkrementen, Präparat, Diagnosen und Operation.
    - no_invention: Die routinemäßigen OP-Schritte (Team-Time-out, Hautdesinfektion, sterile Abdeckung, Capnoperitoneum, Clip-Versorgung von Ductus cysticus und A. cystica, Bergung, Trokarentfernung, Wundverschluss) sind aus Referenz gedeckt, jedoch sind Narkoseform, Nüchternheit sowie Aufklärung/Einwilligung patientenbezogene Fakten ohne Diktatgrundlage. — „in Allgemeinanästhesie mit Intubation“
    - register: Sachlicher fachlicher Stil, Abkürzungen (10-mm-Trokar, mmHg) direkt verwendet, keine Füllwörter und keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon vorhanden.
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `opbericht-02` — OP-Bericht — Narbenhernie, Sublay-Netzimplantation (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 2 weich — hart: R-INVENT
- must_contain: 11/11
- Echo: similarity=0.167, token_ratio=0.217, jaccard=0.119 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-02.txt`
- LLM-Judge (deepseek-flash): mean=3.8 {'structure': 4, 'completeness': 5, 'no_invention': 1, 'register': 4, 'plain_text': 5}
    - structure: Kopfblock mit Indikation, dann OP-Verlauf, Präparat, Diagnosen und Operation als Blöcke am Ende; die von der Blocklogik (Anamnese/Untersuchung) abweichende Reihung ist bei einem OP-Bericht sachgerecht, lediglich die Diagnosen stehen erst nach dem Präparat.
    - completeness: Alle im Diktat genannten Fakten sind enthalten: 68-jähriger Patient, Narbenhernie nach Medianlaparotomie mit zunehmender Größe und Beschwerden, OP am 29.09.2026, Sublay-Technik, Netz 15 x 20 cm, intraoperativ ca. 6 cm große Hernie ohne Inkarzeration.
    - no_invention: Zahlreiche patientenbezogene Angaben stehen weder im Diktat noch im Referenzwissen: Narkoseform und Lagerung, Anzahl der Hautdesinfektionen, perioperative Antibiotikaprophylaxe, Nahtmaterial und Stärke (Monomax 0), Small-bite-Technik, Drainagen mit Saugflasche, Bauchgurt, Steri-Strips und Einzelknopf-Intrakutannähte sowie der Versand zur Histologie; aus Referenz gedeckt sind dagegen Team-Time-out, Hautdesinfektion und steriles Abdecken, Zugang über die alte Narbe, Präparation und Resektion des Bruchsacks, Sublay-Netzplatzierung sowie Verschluss der Rektusscheide und Wundverschluss. — „"Die Operation erfolgt in Rückenlage in Intubationsnarkose. Nach 3-maliger Hautdesinfektion des OP-Gebiets und sterilem Abdecken mit selbstklebender Operationsfolie werden das Instrumentarium ausgelegt, die perioperative Antibiotikaprophylaxe durchgeführt und das Team-Time-out abgehalten." | "Einlage von Redon-Drainagen in die Subkutis" | "intraoperativ Anlage eines Bauchgurtes" | "Versand zur histopathologischen Untersuchung"“
    - register: Sachlicher fachlicher Stil mit üblichen Abkürzungen und ohne Füllwörter; die Narkoseangabe wird jedoch im Abschnitt Indikation und zu Beginn des OP-Blocks wiederholt, und die Geschlechtszuordnung bleibt durch die Abkürzung unklar. — „"Bei symptomatischem Befund erfolgte am 29.09.2026 in Intubationsnarkose die offene Narbenhernienreparation in Sublay-Technik." | "Die Operation erfolgt in Rückenlage in Intubationsnarkose."“
    - plain_text: Reiner Fließtext ohne Markdown, korrekte Umlaute und Eszett-Vermeidung, kein Semikolon im gesamten Text.
- Hinweis: Zweiter Enrichment-Fall. Fehlhörer 'Sableb-Technik' → 'Sublay-Technik' (R44) im Quellmaterial angedeutet.
