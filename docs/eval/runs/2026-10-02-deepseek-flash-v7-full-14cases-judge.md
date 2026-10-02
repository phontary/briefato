# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-204837-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T20:52:54+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** deepseek-flash
- **Fälle:** 14/14 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.632 |
| Mean Token-Jaccard | 0.825 |
| Echo-Schwelle | 0.85 (Standard); entlassmedikationsplan 0.92, zusammenfassung 0.92 |
| **Echo-Fälle** | **4/14** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 9/14 |
| Harte Regel-Findings (Summe) | 3 |
| Weiche Regel-Findings (Summe) | 5 |
| Fälle mit harten Findings | 3 |
| must_contain-Abdeckung | 1.000 (94/94) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 0 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | 4.730 |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `ambulant-01` | ambulant | ✓ | 0 | 1 | 4/4 | 0.952 | 0.962 | ECHO | ok |
| `ambulant-02` | ambulant | ✓ | 0 | 0 | 4/4 | 1.000 | 1.000 | ECHO | ok |
| `aufnahmebrief-01` | arztbrief | ✓ | 0 | 0 | 3/3 | 0.667 | 1.000 | C-ECHO | ok |
| `entlassbrief-01` | arztbrief | ✓ | 0 | 0 | 8/8 | 0.780 | 0.833 | — | ok |
| `entlassbrief-02` | arztbrief | ✓ | 0 | 0 | 7/7 | 0.800 | 1.000 | C-ECHO | ok |
| `entlassbrief-03` | arztbrief | ✓ | 1 | 0 | 8/8 | 0.916 | 1.000 | ECHO | ok |
| `entlassbrief-04` | arztbrief | ✓ | 1 | 0 | 7/7 | 0.954 | 0.925 | ECHO | ok |
| `entlassbrief-05` | arztbrief | ✓ | 0 | 0 | 6/6 | 0.723 | 0.830 | — | ok |
| `entlassmedikationsplan-01` | entlassmedikationsplan | ✓ | 0 | 0 | 8/8 | 0.011 | 0.848 | — | ok |
| `opbericht-01` | operationsbericht | ✓ | 0 | 2 | 13/13 | 0.188 | 0.143 | — | ok |
| `opbericht-02` | operationsbericht | ✓ | 1 | 2 | 11/11 | 0.184 | 0.145 | — | ok |
| `pflegebericht-01` | pflegebericht | ✓ | 0 | 0 | 5/5 | 0.034 | 0.939 | C-ECHO | ok |
| `verlegungsbericht-01` | arztbrief | ✓ | 0 | 0 | 5/5 | 0.722 | 1.000 | C-ECHO | ok |
| `zusammenfassung-01` | zusammenfassung | ✓ | 0 | 0 | 5/5 | 0.913 | 0.923 | C-ECHO | ok |

## Details

### `ambulant-01` — Ambulanter/tageschirurgischer Brief — Leistenhernie

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 4/4
- Echo: similarity=0.952, token_ratio=0.940, jaccard=0.962 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `ambulant`): 0.850 | Text: `cases/ambulant-01.txt`
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 5, 'completeness': 4, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Der Text folgt der Playbook-Reihenfolge (Anamnese/Indikation → OP → intraoperativer Befund → postoperativer Verlauf → Empfehlungen) und stellt die Diagnosen als eigenen Block an das Ende.
    - completeness: Alle klinisch relevanten Fakten sind enthalten, jedoch entfällt bei der Zusammenfassung des Eingriffs die im Diktat genannte Seitenangabe 'rechts' zur Leistenhernienversorgung. — „die am 12.09.2026 in Intubationsnarkose erfolgte“
    - no_invention: Es werden keine zusätzlichen Diagnosen, Codes, Daten, Werte oder Maßnahmen genannt, die nicht im Diktat stehen.
    - register: Sachlicher fachlicher Stil, Patient wird durchgängig als 'Pat.' abgekürzt, keine Füllwörter und keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Fließtext ohne Markdown, Umlaute korrekt gesetzt (große, über, häusliche, regelmäßige) und kein Semikolon verwendet.
- Hinweis: R58: KEIN 'stationär aufnehmen'-Satz, KEINE Therapie-Maßnahmen-Liste. Ambulante Empfehlungen sind Fließtext, kein Label.

### `ambulant-02` — Ambulanter Brief — NFA-Vorstellung, Kopfplatzwunde eines Kindes

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 4/4
- Echo: similarity=1.000, token_ratio=1.000, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `ambulant`): 0.850 | Text: `cases/ambulant-02.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Reihenfolge und Blocklogik entsprechen dem Diktat; Diagnosen stehen als Block am Ende.
    - completeness: Alle klinisch relevanten Angaben aus dem Diktat sind vollständig enthalten.
    - no_invention: Keine zusätzlichen Diagnosen, Daten, Werte, Medikamente oder Konsile erfunden.
    - register: Sachlicher fachlicher Stil, Abkürzungen korrekt verwendet, keine Füllwörter oder Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon und keine Formatierungsartefakte.
- Hinweis: Rein konservative NFA-Vorstellung ohne OP. Keine stationären Blöcke, kein Aufnahmesatz.

### `aufnahmebrief-01` — Aufnahmebrief — akute Appendizitis, OP ausstehend

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 3/3
- Echo: similarity=0.667, token_ratio=0.884, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/aufnahmebrief-01.txt`
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Blocklogik weitgehend eingehalten (Aufnahme/Anamnese, Untersuchung, Diagnostik, Therapieplanung, Diagnosen am Ende), jedoch ist der Aufnahmesatz inkl. stationärer Aufnahme vor die Sonographie/CT-Befunde gezogen, während er im Diktat danach steht. — „Wir nahmen die Patientin zur weiteren Diagnostik bzw. Schmerztherapie stationär auf.“
    - completeness: Sämtliche im Diktat genannten Fakten (Aufnahmeweg NFA, Schmerzdauer 10 Stunden, Nausea, subfebrile Temperaturen, Untersuchungsbefund, Sono/CT-Befund, stationäre Aufnahme, OP-Planung, Aufklärung, Diagnose) sind vollständig abgebildet.
    - no_invention: Es wurden keine zusätzlichen Diagnosen, Codes, Daten, Laborwerte, Medikamente oder Konsile ergänzt; alle Angaben sind durch das Diktat gedeckt.
    - register: Sachlicher fachlicher Stil, gängige Abkürzungen (NFA, KU, CT) direkt verwendet, keine Füllwörter und keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, Umlaute korrekt gesetzt, kein Semikolon verwendet.
- Hinweis: Aufnahmebrief: Verlauf läuft weiter (OP am Folgetag). KEIN Empfehlungsblock, KEINE stationäre Therapieliste (R30/R31-Analogon).

### `entlassbrief-01` — Stationärer Entlassbrief — akute Cholezystitis, laparoskopische Cholezystektomie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.780, token_ratio=0.840, jaccard=0.833 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-01.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Der Text folgt der Playbook-Logik: Anamnese/Aufnahme, Befunde (Sonographie/CT), Therapie (OP, Histologie), Verlauf und Entlassung; die Blöcke Ambulante Empfehlungen, Diagnosen, Nebenerkrankungen und Therapie-Maßnahmen stehen gesammelt am Ende.
    - completeness: Sämtliche im Diktat genannten klinischen Fakten sind enthalten: Beschwerden, Aufnahmeweg, Diagnostik, Aufnahmegrund, OP mit intraoperativem und histologischem Befund, postoperativer Verlauf, Entlassdatum und -art, Empfehlungen sowie Diagnosen, Nebenerkrankung und stationäre Maßnahmen.
    - no_invention: Es finden sich keine Zusätze wie ICD-Codes, Laborwerte, zusätzliche Medikamente, Konsile oder Daten; alle Angaben einschließlich der Daten 14.09.2026 und 17.09.2026 stammen unverändert aus dem Diktat.
    - register: Sachlicher fachlicher Stil, Abkürzungen (NFA, CT, OP) werden direkt verwendet, keine Füllwörter; die Blockbezeichnungen stehen nur in den Abschlussblöcken und nicht im Fließtext.
    - plain_text: Reiner Text ohne Markdown, durchgehend korrekte Umlaute und Orthographie, kein Semikolon verwendet.
- Hinweis: Kernfall: 12 KIS-Quellen, alle Blöcke diktiert. Prüft Blockreihenfolge und vollständige Diagnoseliste. Hinweis: 'Nachweis'-Wortlaut vermeiden — der bestehende Triage-Treffer '\bnachweis' würde sonst fälschlich auf Weiterbildungs-Nachweise routen (vom Harness als Typ-Fehlschlag erkannt).

### `entlassbrief-02` — Stationärer Entlassbrief — mediale Schenkelhalsfraktur, Hüft-TEP

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 7/7
- Echo: similarity=0.800, token_ratio=0.889, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-02.txt`
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 5, 'completeness': 4, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Die Blocklogik (Anamnese/Diagnostik, Aufnahme, Therapie/OP, Verlauf, Entlassung, Empfehlungen, Diagnosen, Nebenerkrankungen, Maßnahmen) ist eingehalten, die Blöcke stehen am Ende; die Röntgen-/CT-Angabe ist lediglich in einen eigenen Absatz nach der Aufnahme gerückt, was die Reihenfolge nicht verletzt.
    - completeness: Alle klinischen Angaben des Diktats sind übernommen, jedoch fehlt die zweite im Diktat genannte Diagnose 'Z.n. Implantation einer Huefttotalendoprothese rechts' vollständig. — „Z.n. Implantation einer Huefttotalendoprothese rechts“
    - no_invention: Es erscheinen keine zusätzlichen Diagnosen, Codes, Daten, Werte oder Maßnahmen; alle Angaben (Datum 21.09.2026, 24.09.2026, NFA, Unterarmgehstützen) stammen aus dem Diktat.
    - register: Sachlicher fachlicher Stil, Abkürzungen (NFA, CT) direkt verwendet, keine Füllwörter, keine erläuternden Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon und kein sonstiges unzulässiges Sonderzeichen.
- Hinweis: 16 KIS-Quellen. Enthält eine Z.n.-Zeile im Diagnosenblock (R23) und Komorbiditäten.

### `entlassbrief-03` — Stationärer Entlassbrief — ambulant erworbene Pneumonie mit Delir

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 0 weich — hart: R6
- must_contain: 8/8
- Echo: similarity=0.916, token_ratio=0.900, jaccard=1.000 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-03.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Fließtext folgt der Playbook-Logik (Aufnahme/Anamnese, Untersuchungsbefund, Therapie, Verlauf, Entlassung), alle Blöcke stehen gesammelt am Ende; die gegenüber dem Diktat vertauschten Sätze zur stationären Aufnahme und zur Bildgebung bleiben inhaltlich schlüssig.
    - completeness: Sämtliche klinisch relevanten Angaben des Diktats sind enthalten: Symptome und Dauer, Bildgebung mit Infiltrat und fehlendem Pleuraerguss, Aufnahmegrund Diagnostik/Schmerztherapie, Antibiose, Delir mit Therapie, komplikationsloser Verlauf, Entlassdatum und -ort, Empfehlungen, alle Diagnosen, Nebenerkrankungen und Stationsmaßnahmen.
    - no_invention: Keine zusätzlichen Diagnosen, ICD-Codes, Datumsangaben, Laborwerte, Medikamente oder Konsile; einzige Abweichung sind orthografische Korrekturen (Umlaute) ohne Faktenänderung.
    - register: Sachlicher fachlicher Stil, korrekte Fachbegriffe (Dyspnoe, Infiltratbildung, parenterale Antibiose, Delirtherapie), keine Füllwörter und keine erläuternden Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, durchgängig korrekte Umlaute (Röntgenaufnahme, stationär, häusliche, hausärztliche, für) und kein Semikolon im gesamten Dokument.
- Hinweis: Internistischer Fall. Pflege-/Verlaufsinformationen müssen eingewoben, nicht als Block zitiert werden.

### `entlassbrief-04` — Stationärer Entlassbrief — Rektumkarzinom, anteriore Rektumresektion

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 0 weich — hart: R-INVENT
- must_contain: 7/7
- Echo: similarity=0.954, token_ratio=0.969, jaccard=0.925 → ECHO (keine eigene Formulierung)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-04.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Reihenfolge Vorstellung/Diagnostik → Therapie/Histologie → Verlauf → Entlassung → Empfehlungen, danach die Blöcke Diagnosen, Nebenerkrankungen, Therapie-Maßnahmen am Ende; entspricht der Playbook-Logik und der Diktatvorlage.
    - completeness: Alle im Diktat genannten klinisch relevanten Fakten sind enthalten: Raumforderung mittleres Rektumdrittel, fehlende Fernmetastasierung, stationäre Aufnahme, OP-Art mit TME und protektivem Ileostoma, Histologie pT3 pN1 R0 G2, regelrechter Verlauf, Kostaufbau, Entlassdatum 22.08.2026, Empfehlungen, Diagnose, Hypertonie, OP-Datum 15.08.2026, Thromboseprophylaxe.
    - no_invention: Keine zusätzlichen Diagnosen, Codes, Daten, Laborwerte oder Medikamente; die Umformulierung 'Zur Abklärung erfolgten' ist eine zulässige Paraphrase ohne neuen Faktgehalt.
    - register: Sachlicher fachlicher Stil, Abkürzungen (MRT, pT3 pN1, R0, G2, OP) direkt verwendet, keine Füllwörter, keine erläuternden Einschübe im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute (stationär, bestätigte, häusliche, für), kein Semikolon im gesamten Text, damit die Vorgabe höchstens ein Semikolon eingehalten.
- Hinweis: Onkologischer Fall. Prüft, ob Tumorstadium und OPS-freie Therapieliste korrekt übernommen werden.

### `entlassbrief-05` — Stationärer Entlassbrief — akute Divertikulitis, konservative Therapie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 6/6
- Echo: similarity=0.723, token_ratio=0.793, jaccard=0.830 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/entlassbrief-05.txt`
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Blocklogik und Schlussblöcke (Diagnosen, Nebenerkrankungen, Maßnahmen) korrekt, jedoch wurde die Reihenfolge von Aufnahme und CT-Befund gegenüber dem Diktat vertauscht (CT vor Aufnahme) und der Verlauf steht vor den Empfehlungen, was der Vorlage entspricht.
    - completeness: Alle im Diktat genannten Fakten sind enthalten: Symptome mit Dauer und Seite, Fieber, CT-Befund mit Ausschluss von Abszess und Perforation, Aufnahmegrund, Antibiotikatherapie mit klinischer Besserung, vertragener Kostaufbau, Beschwerdefreiheit, Entlassdatum und -art, Empfehlungen, Diagnosen, Nebenerkrankungen und alle drei Maßnahmen.
    - no_invention: Keine erfundenen Angaben; keine ICD-Codes, Laborwerte, zusätzlichen Medikamente oder Konsile. Die Umformulierung 'stellte sich vor' gibt nur den im Diktat genannten Sachverhalt wieder.
    - register: Sachlicher fachlicher Stil, korrekte Umlaute, keine Füllwörter, keine erläuternden Kategorie-Labels im Fließtext; die Blocküberschriften entsprechen der Diktatvorgabe.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute und kein Semikolon.
- Hinweis: Konservativ behandelter Fall ohne OP — Therapieblock enthält keine OP-Zeile. Nebenerkrankungen = keine.

### `entlassmedikationsplan-01` — Entlassmedikationsplan anpassen — Dosisabweichungen und bedingter Verabreichungsplan

- Erwarteter Typ: `entlassmedikationsplan` · tatsächlich: `entlassmedikationsplan` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.011, token_ratio=0.909, jaccard=0.848 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `entlassmedikationsplan`): 0.920 | Text: `cases/entlassmedikationsplan-01.txt`
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Reihenfolge der Blöcke entspricht dem Diktat, aber die Blocküberschriften „Geänderte Zeilen:“ und „Verabreichungsplan:“ fehlen, wodurch die Blocklogik leicht abnimmt.
    - completeness: Alle klinisch relevanten Angaben zu Insulin glargin, Insulin glulisin, Begründung, unveränderten Medikamenten und nicht zur Entlassmedikation gehörender Antibiose sind übernommen.
    - no_invention: Es werden keine zusätzlichen Diagnosen, Medikamente, Laborwerte oder sonstigen Fakten ergänzt; alle Angaben stammen aus dem Diktat.
    - register: Sachlicher fachlicher Stil, Abkürzungen wie IE und i.v. werden direkt verwendet, keine Füllwörter oder unpassenden Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon und damit die Vorgabe von höchstens einem Semikolon eingehalten.
- Hinweis: R63: nur Text im Chat. Dosisabweichung NICHT stillschweigend korrigieren, sondern Prüfhinweis (R45/AP-15). Kein PDF/HTML-Export.

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 2 weich
- must_contain: 13/13
- Echo: similarity=0.188, token_ratio=0.240, jaccard=0.143 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-01.txt`
- LLM-Judge (deepseek-flash): mean=4.6 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 4, 'plain_text': 5}
    - structure: Blocklogik eingehalten (Indikation → OP-Verlauf → Präparat → Diagnosen → Operation), alle Sammelblöcke am Ende; kleinere Unschärfe, weil die Verlaufsebene mit 'OP:' und die Zusammenfassung mit 'Operation:' zwei ähnlich benannte Überschriften verwendet.
    - completeness: Alle klinisch relevanten Diktatfakten sind abgebildet: 54-jährige Patientin, symptomatische Cholezystolithiasis ohne Obstruktionshinweis, geplantes Vorgehen bei symptomatischem Steinleiden, OP-Datum 23.09.2026, laparoskopische Cholezystektomie, intraoperativ chronisch entzündete Gallenblase mit multiplen Konkrementen sowie Präparatangabe 'Gallenblase, Präparat ad Histologie'.
    - no_invention: Keine patientenbezogenen Fremdfakten (keine ICD, kein Name, kein Laborwert, keine Drainage, keine ASA-Angabe, kein Stationssatz). Alle über das Diktat hinausgehenden Angaben sind durch das Referenzwissen gedeckt: Anästhesieform, Nüchternheit und Aufklärung aus Referenz (Nutzerstandard zur Indikation), ebenso Team-Time-out, Hautdesinfektion, steriles Abdecken, Capnoperitoneum bis 12 mmHg, Trokaranordnung, Clipping mit Metall-Clips, Bergung, Zählkontrolle, Faszienschluss mit Novosyn 0 und Wundverschluss aus Referenz (Abteilungsstandard). — „in Allgemeinanästhesie mit Intubation die geplante laparoskopische Cholezystektomie. Die Patientin ist nüchtern, Aufklärung und Einwilligung liegen vor.“
    - register: Sachlicher fachlicher Stil, korrekte Abkürzungen (10-mm-Trokar, mmHg), keine Füllwörter; leichte Doppelung im Kontrollsatz ('ergibt Bluttrockenheit, die Zählkontrolle ist vollständig') und mehrfach wiederholtes 'welche besteht' mindern die Prägnanz. — „Die abschließende Kontrolle auf intraabdominelle Bluttrockenheit ergibt Bluttrockenheit, die Zählkontrolle ist vollständig.“
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute (für, entzündet, Präparat) und kein Semikolon; Abschnittsüberschriften mit Doppelpunkt sind berichtstypisch und kein Markup.
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `opbericht-02` — OP-Bericht — Narbenhernie, Sublay-Netzimplantation (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 2 weich — hart: R-INVENT
- must_contain: 11/11
- Echo: similarity=0.184, token_ratio=0.232, jaccard=0.145 → eigene Formulierung (kein Echo)
- Echo-Schwelle (Typ `operationsbericht`): 0.850 | Text: `cases/opbericht-02.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Playbook-Reihenfolge eingehalten: Erzählabsätze mit Indikation, OP, Präparat, danach am Dokumentende die Blöcke Diagnosen und Operation; keine Blockdurchmischung.
    - completeness: Alle Diktatfakten sind abgebildet: 68-jähriger Patient, Narbenhernie nach Medianlaparotomie mit zunehmender Größe und Beschwerden, OP-Datum 29.09.2026, Sublay-Technik, Netzimplantation 15 x 20 cm, intraoperativ ca. 6 cm große Hernie ohne Inkarzeration sowie beide Abschlussblöcke.
    - no_invention: Die über das Diktat hinausgehenden Angaben (Rückenlage, Intubationsnarkose, 3-malige Hautdesinfektion, selbstklebende Operationsfolie, Instrumentarium, perioperative Antibiotikaprophylaxe, Team-Time-out, Ausschneiden der alten Narbe, Freipräparation bis zur peritonealen Umschlagfalte, zirkumferente Präparation, Resektion und histopathologische Untersuchung des Bruchsacks, Blutstillung, M. rectus abdominis, Monomax Stärke 0 in Small-bite-Technik, Ausmessen/Zuschneiden des Netzes, keine Nahtfixierung, Verschluss der vorderen Rektusscheide, Nachresektion, Redon-Drainagen, subkutane Naht und Einzelknopf-Intrakutannähte, Steri-Strips, Pflasterverband, Bauchgurt, Ausleitung über den Aufwachraum) sind aus Referenz gedeckt; die Netzgröße 15 x 20 cm stammt aus dem Diktat und überschreibt korrekt die Standardgröße.
    - register: Sachlich-fachlicher Stil, gängige Abkürzung (Pat.), keine Füllwörter, keine Kategorie-Labels im Fließtext; der OP-Ablauf wird in korrekter Zeitform und ohne Ausschmückung geschildert.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute und Eszett, kein Semikolon im gesamten Text verwendet.
- Hinweis: Zweiter Enrichment-Fall. Fehlhörer 'Sableb-Technik' → 'Sublay-Technik' (R44) im Quellmaterial angedeutet.

### `pflegebericht-01` — Pflegebericht-Integration — umfangreiche Pflegedokumentation zu einem Verlauf

- Erwarteter Typ: `pflegebericht` · tatsächlich: `pflegebericht` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.034, token_ratio=0.892, jaccard=0.939 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `pflegebericht`): 0.850 | Text: `cases/pflegebericht-01.txt`
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Der Pflegebericht ist als zusammenhängender Verlaufsblock in der Reihenfolge des Diktats (Beschwerden/Bedarfsmedikation → Stuhlgang/Kostaufbau → Wunde/Verband → Sauerstoffgabe → Mobilisation) abgebildet; keine Blockumstellungen oder Brüche.
    - completeness: Alle im Diktat genannten Fakten sind enthalten: Bauchschmerzen, Bedarfsmedikation, erstmaliger Stuhlgang mit Besserung, vertragener Kostaufbau, trockene reizlose Wunde, regelmäßiger Verbandwechsel, Sauerstoffabfall mit Nasenbrillengabe, sichere Mobilisation mit Rollator.
    - no_invention: Keine zusätzlichen Diagnosen, ICD-Codes, Daten, Laborwerte, Medikamentennamen oder Konsile; ausschließlich diktiertes Geschehen.
    - register: Sachlicher pflegerischer Fachstil, korrekte Umlaute, keine Füllwörter und keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Fließtext ohne Markdown, Umlaute korrekt gesetzt (über, Sättigung, regelmäßig), kein Semikolon verwendet.
- Hinweis: Pflegejargon filtern (AP-16): 'zur Nacht versorgt', 'laut AO', 'SK' dürfen NICHT übernommen werden; klinisch Relevantes (Wundzustand, Stuhlgang, Schmerz, SpO2) wird eingewoben.

### `verlegungsbericht-01` — Verlegungsbericht — zur dringenden operativen Versorgung, Zielklinik XXX

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.722, token_ratio=0.835, jaccard=1.000 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `arztbrief`): 0.850 | Text: `cases/verlegungsbericht-01.txt`
- Struktur: fehlende Blöcke —, Reihenfolge ok, kanonisch fehlend ['ambulante Therapieempfehlungen nach der Entlassung:', 'Nebenerkrankungen:', 'Therapie-Maßnahmen auf der Station:']
- LLM-Judge (deepseek-flash): mean=4.6 {'structure': 4, 'completeness': 5, 'no_invention': 5, 'register': 4, 'plain_text': 5}
    - structure: Grundordnung mit Aufnahme, Endoskopie, Verlegung und Diagnosen am Ende ist eingehalten, doch die doppelte Erwähnung der stationären Aufnahme stört die Blocklogik. — „Wir nahmen die Patientin zur weiteren Diagnostik bzw. Schmerztherapie stationär auf.“
    - completeness: Alle im Diktat genannten relevanten Fakten inklusive Ösophagogastroduodenoskopie, fehlgeschlagener Blutstillung, Verlegung am 01.10.2026 und Diagnosen sind enthalten.
    - no_invention: Keine zusätzlichen Diagnosen, Daten, Werte oder Maßnahmen; alle Angaben lassen sich aus dem Diktat ableiten.
    - register: Sachlicher Stil, keine Füllwörter, aber die redundante Wiederholung der stationären Aufnahme ist stilistisch unsauber. — „Wir nahmen die Patientin zur weiteren Diagnostik bzw. Schmerztherapie stationär auf.“
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon.
- Hinweis: Verlegungsbrief: KEIN Empfehlungsblock (R31), Zielklinik bleibt Platzhalter XXX (R32).

### `zusammenfassung-01` — Zusammenfassung — mehrzeitiger Verlauf

- Erwarteter Typ: `zusammenfassung` · tatsächlich: `zusammenfassung` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.913, token_ratio=0.914, jaccard=0.923 → eigene Formulierung (kein Echo) (Content-Echo: alle Inhaltswörter geteilt)
- Echo-Schwelle (Typ `zusammenfassung`): 0.920 | Text: `cases/zusammenfassung-01.txt`
- LLM-Judge (deepseek-flash): mean=3.0 {'structure': 2, 'completeness': 3, 'no_invention': 1, 'register': 4, 'plain_text': 5}
    - structure: Die Verlaufsprosa ist in sich schlüssig, aber die im Playbook vorgesehenen Blöcke fehlen vollständig: weder die Überschrift 'Zusammenfassung' noch der abschließende Diagnosenblock sind umgesetzt. — „Diagnosen:
Z.n. Glutealabszess mit Fistel“
    - completeness: Alle Verlaufsfakten (Notfallversorgung Juni 2025, Hb-Abfall mit 2 EK, Aufnahme Nov. 2025, CT-Befund, Beschwerderückbildung, Vorstellung Sep. 2026) sind enthalten; nicht übernommen wurden die Überschrift 'Zusammenfassung' und die explizite Diagnosenzeile 'Z.n. Glutealabszess mit Fistel'. — „Diagnosen:
Z.n. Glutealabszess mit Fistel“
    - no_invention: Das Geschlecht des Patienten wurde ohne Grundlage im Diktat vertauscht: das Diktat spricht durchgehend von 'Der Patient', der Text von 'Die Patientin' – dies ist eine inhaltliche Falschangabe. — „Die Patientin wurde nach Z.n. Glutealabszess-Operation im Juni 2025“
    - register: Sachlicher fachlicher Stil, Abkürzungen (Z.n., EK, CT) korrekt direkt verwendet, keine Füllwörter und keine Kategorie-Labels im Fließtext; einzige Abweichung ist die verdeutschte Schreibweise 'notfallmäßig' statt der diktierten Schreibweise.
    - plain_text: Reiner Fließtext ohne Markdown, Umlaute korrekt gesetzt, kein Semikolon verwendet.
- Hinweis: R24: keine Diagnoseliste und keine Therapie-Maßnahmen-Liste — auch wenn das Diktat eine Diagnosen-Zeile enthält. Datum abgekürzt als Monat.
