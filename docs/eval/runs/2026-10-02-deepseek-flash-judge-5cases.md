# Briefato — Qualitäts-Scorecard

> ✅ **Echter Modelllauf — Schreibqualität wird gemessen**

## Lauf

- **Run-ID:** `20261002-195939-openai-deepseek-flash`
- **Zeit (UTC):** 2026-10-02T19:59:39+00:00
- **Provider:** `openai` · **Modell:** `deepseek-flash`
- **Base-URL:** https://api.deepseek.com/v1
- **Enrich (Rohquellen einbezogen):** nein
- **LLM-Judge:** deepseek-flash
- **Fälle:** 5/5 erfolgreich

## Gesamt

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.716 |
| Mean Token-Jaccard | 0.772 |
| **Echo-Fälle** | **2/5** |
| Content-Echo-Fälle (Token-Jaccard > 0.85) | 2/5 |
| Harte Regel-Findings (Summe) | 1 |
| Weiche Regel-Findings (Summe) | 1 |
| Fälle mit harten Findings | 1 |
| must_contain-Abdeckung | 1.000 (38/38) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 0 |
| Typ-Triage-Fehlschläge | 0 |
| Mean LLM-Judge (0–5) | 4.320 |

## Pro Fall

| Fall | Typ | Typ✓ | Hard | Soft | must✓ | Echo-Sim | Jaccard | Echo? | Struktur |
|---|---|---|---|---|---|---|---|---|---|
| `ambulant-02` | ambulant | ✓ | 0 | 0 | 4/4 | 0.811 | 0.808 | — | ok |
| `entlassbrief-01` | arztbrief | ✓ | 0 | 0 | 8/8 | 0.394 | 0.797 | — | ok |
| `entlassbrief-03` | arztbrief | ✓ | 1 | 0 | 8/8 | 0.916 | 1.000 | ECHO | ok |
| `opbericht-01` | operationsbericht | ✓ | 0 | 1 | 13/13 | 0.503 | 0.282 | — | ok |
| `zusammenfassung-01` | zusammenfassung | ✓ | 0 | 0 | 5/5 | 0.957 | 0.974 | ECHO | ok |

## Details

### `ambulant-02` — Ambulanter Brief — NFA-Vorstellung, Kopfplatzwunde eines Kindes

- Erwarteter Typ: `ambulant` · tatsächlich: `ambulant` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 4/4
- Echo: similarity=0.811, token_ratio=0.900, jaccard=0.808 → eigene Formulierung (kein Echo)
- LLM-Judge (deepseek-flash): mean=4.2 {'structure': 5, 'completeness': 5, 'no_invention': 1, 'register': 5, 'plain_text': 5}
    - structure: Reihenfolge Vorstellung/Anamnese → Untersuchung → Therapie → Verlauf/Hinweis, Diagnoseblock am Ende; keine Überschriften oder Labels im Fließtext.
    - completeness: Alle klinisch relevanten Fakten des Diktats (Vorstellung in NFA mit Mutter, Kopfstoß beim Spielen, KU-Befund mit Lokalisation und Größe, neurologischer Befund, Desinfektion/Fibrinkleber/Pflaster, Aufklärung der Mutter, selbstständige Lösung des Hautklebers nach ca. 3 Tagen, keine stationäre Aufnahme, beide Diagnosen) sind enthalten.
    - no_invention: Ein vollständiger Empfehlungssatz mit Wundkontrolle und Wiedervorstellungskriterien (Rötung, Schwellung, Schmerzen, Fieber) steht nicht im Diktat und wurde frei ergänzt; damit werden mehrere nicht belegte Fakten hinzugefügt. — „Empfohlen werden die regelmäßige Wundkontrolle sowie die Wiedervorstellung bei Rötung, Schwellung, zunehmenden Schmerzen oder Fieber.“
    - register: Sachlicher fachlicher Stil, Abkürzungen (NFA, KU, ca.) korrekt direkt verwendet, keine Füllwörter, keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Fließtext ohne Markdown, korrekte Umlaute (gestoßen, große, unauffällig, aufgeklärt, stationäre), genau ein Semikolon.
- Hinweis: Rein konservative NFA-Vorstellung ohne OP. Keine stationären Blöcke, kein Aufnahmesatz.

### `entlassbrief-01` — Stationärer Entlassbrief — akute Cholezystitis, laparoskopische Cholezystektomie

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 8/8
- Echo: similarity=0.394, token_ratio=0.812, jaccard=0.797 → eigene Formulierung (kein Echo)
- LLM-Judge (deepseek-flash): mean=4.8 {'structure': 5, 'completeness': 4, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Die Reihenfolge des Diktats ist eingehalten: Aufnahmeanlass/Anamnese, Diagnostik (Sonographie, CT), Therapie (Operation, Histologie), postoperativer Verlauf, danach die Blöcke ambulante Empfehlungen, Diagnosen, Nebenerkrankungen und stationäre Maßnahmen am Ende.
    - completeness: Alle klinischen Fakten (Beschwerden, NFA, Sonographie/CT, Cholezystolithiasis ohne Gallewegsobstruktion, stationäre Aufnahme, OP, intraoperativer und histologischer Befund, Verlauf, Entlassdatum, Empfehlungen, Diagnosen, Nebenerkrankungen, Maßnahmen) sind enthalten; die im Diktat genannte Patientin "Muster, Anna" wird jedoch nicht erwähnt.
    - no_invention: Keine zusätzliche Diagnose, kein ICD, kein Laborwert, Medikament oder Konsil; alle Angaben (inkl. 14.09.2026 und 17.09.2026) stammen aus dem Diktat.
    - register: Sachlicher fachlicher Stil, Abkürzungen (NFA, CT) direkt verwendet, keine Füllwörter, die Blocklabels stehen nur als Überschriften und nicht im Fließtext.
    - plain_text: Reiner Text ohne Markdown, durchgängig korrekte Umlaute und ß, kein Semikolon enthalten.
- Hinweis: Kernfall: 12 KIS-Quellen, alle Blöcke diktiert. Prüft Blockreihenfolge und vollständige Diagnoseliste. Hinweis: 'Nachweis'-Wortlaut vermeiden — der bestehende Triage-Treffer '\bnachweis' würde sonst fälschlich auf Weiterbildungs-Nachweise routen (vom Harness als Typ-Fehlschlag erkannt).

### `entlassbrief-03` — Stationärer Entlassbrief — ambulant erworbene Pneumonie mit Delir

- Erwarteter Typ: `arztbrief` · tatsächlich: `arztbrief` ✓ (Retry ausgelöst)
- Regeln: 1 hart / 0 weich — hart: R6
- must_contain: 8/8
- Echo: similarity=0.916, token_ratio=0.900, jaccard=1.000 → ECHO (keine eigene Formulierung)
- LLM-Judge (deepseek-flash): mean=5.0 {'structure': 5, 'completeness': 5, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Reihenfolge und Blocklogik eingehalten: Aufnahmegrund, Diagnostik, Therapie/Verlauf, Empfehlungen, danach Diagnosen, Nebenerkrankungen und Maßnahmen.
    - completeness: Alle im Diktat genannten klinisch relevanten Fakten sind enthalten, einschließlich Diagnosen, Nebenerkrankungen und Therapiemaßnahmen.
    - no_invention: Keine zusätzlichen Diagnosen, Daten, Medikamente oder Konsile; nur diktierte Inhalte, orthographisch angepasst.
    - register: Sachlicher fachlicher Stil, Abkürzungen direkt verwendet, keine Füllwörter oder Kategorie-Labels im Fließtext.
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute, kein Semikolon.
- Hinweis: Internistischer Fall. Pflege-/Verlaufsinformationen müssen eingewoben, nicht als Block zitiert werden.

### `opbericht-01` — OP-Bericht — laparoskopische Cholezystektomie (lückenhafte Routineangaben)

- Erwarteter Typ: `operationsbericht` · tatsächlich: `operationsbericht` ✓
- Regeln: 0 hart / 1 weich
- must_contain: 13/13
- Echo: similarity=0.503, token_ratio=0.441, jaccard=0.282 → eigene Formulierung (kein Echo)
- LLM-Judge (deepseek-flash): mean=3.4 {'structure': 4, 'completeness': 5, 'no_invention': 0, 'register': 3, 'plain_text': 5}
    - structure: Die Blockfolge Indikation, OP, Präparat, Diagnosen, Operation entspricht der Diktatlogik und stellt die Zusatzblöcke ans Ende; die Indikation ist jedoch mit dem OP-Abschnitt inhaltlich doppelt besetzt.
    - completeness: Alle im Diktat genannten Fakten (54-jährige Patientin, symptomatische Cholezystolithiasis ohne Gallenwegsobstruktion, Datum 23.09.2026, chronisch entzündete Gallenblase mit multiplen Konkrementen, Präparat ad Histologie, Diagnose und Operation) sind enthalten.
    - no_invention: Der gesamte operative Ablauf ist frei erfunden und im Diktat nicht belegt, einschließlich Lagerung, Team-Time-out, Trokargrößen, Druckwerten, Nahtmaterial und Verbandsmaterial. — „Nach Team-Time-out erfolgt die Hautdesinfektion gefärbt sowie die sterile Abdeckung des Abdomens.“
    - register: Sachlicher Fachstil grundsätzlich gewahrt, jedoch Kategorie-Labels im Text sowie umgangssprachlich-schwache Formulierungen und Wiederholungen. — „Abschließende Kontrolle auf intraabdominelle Bluttrockenheit, welche besteht.“
    - plain_text: Reiner Text ohne Markdown, korrekte Umlaute und kein Semikolon.
- Hinweis: Enrichment-Pfad: das Rohmaterial enthält KEINE Routine-Schritte (Lagerung, Team-Time-out, Desinfektion, Capnoperitoneum, Verschluss). Ein echtes Modell ergänzt sie standardgemäß aus dem Musterbrief (R52); der Mock tut das NICHT → Abdeckung sinkt. Veress-Nadel bleibt verboten (Pitfall).

### `zusammenfassung-01` — Zusammenfassung — mehrzeitiger Verlauf

- Erwarteter Typ: `zusammenfassung` · tatsächlich: `zusammenfassung` ✓
- Regeln: 0 hart / 0 weich
- must_contain: 5/5
- Echo: similarity=0.957, token_ratio=0.963, jaccard=0.974 → ECHO (keine eigene Formulierung)
- LLM-Judge (deepseek-flash): mean=4.2 {'structure': 3, 'completeness': 3, 'no_invention': 5, 'register': 5, 'plain_text': 5}
    - structure: Der zusammenfassende Verlauf ist chronologisch korrekt wiedergegeben, der im Diktat am Ende stehende Diagnosenblock fehlt jedoch vollständig, sodass die Blocklogik (Blöcke am Ende) nicht eingehalten ist.
    - completeness: Alle Verlaufsfakten (Notfallversorgung Juni 2025, Hb-Abfall mit 2 EK, Aufnahme Nov. 2025 mit CT-Befund, Beschwerderückbildung, beschwerdefreie Vorstellung Sep. 2026) sind enthalten, die im Diktat aufgeführte Diagnose fehlt aber.
    - no_invention: Es werden ausschließlich Fakten aus dem Diktat verwendet; keine zusätzlichen Diagnosen, Codes, Daten, Werte oder Maßnahmen.
    - register: Sachlicher fachlicher Stil, gängige Abkürzungen (Z.n., EK, CT, Hb) direkt verwendet, keine Füllwörter und keine Kategorie-Labels im Fließtext.
    - plain_text: Reiner Fließtext ohne Markdown, korrekte Umlaute und kein Semikolon.
- Hinweis: R24: keine Diagnoseliste und keine Therapie-Maßnahmen-Liste — auch wenn das Diktat eine Diagnosen-Zeile enthält. Datum abgekürzt als Monat.
