# 05 — Qualitätsmessung (Briefato Eval-Harness)

> Diese Datei beantwortet eine einzige Frage: **Wie weiß man, dass der Text gut ist —
> statt es nur zu behaupten?**
>
> Anlass: Mohameds Einwand, dass die Tests den Brief quasi selbst schreiben und die
> Ausgabe nur eine Kopie der Eingabe ist („there is no craft in it"). Das ist für den
> Mock-Lauf korrekt und wird hier zu einer **Zahl** gemacht, die man gegen jeden
> Modellkandidaten messen kann.

Owner dieses Dokuments: `tools/eval/**`, `docs/05-qualitaetsmessung.md`,
`app/tests/test_eval_harness.py`. Die R1–R67-Regelprüfung selbst gehört
`app/briefato/brain/rule_checker.py` und wird hier nur **gelesen**.

---

## 1. Warum ein eigenes Harness

Die bestehende Testsuite (`app/tests/`) prüft mit `BRIEFATO_LLM_MOCK=true` die
**Maschinerie**: Triage/Routing, Retrieval, Pseudonymisierung, Regel-Enforcement,
Verschlüsselung, Mandanten-Isolation, Fehlerpfade. Das ist wichtig — aber der
Mock-Provider **stellt den Brief aus dem Diktat zusammen**. Er beweist daher nichts
über die *Formulierungskunst* eines echten Modells. Dieses Harness trennt beides
sichtbar und messbar.

## 2. Was gemessen wird

Jeder Fall wird durch die **echte** Pipeline (`pipeline.generate.generate_letter`)
gefahren — dieselbe Funktion, die auch die App benutzt. Pro Fall entstehen fünf
Messblöcke:

### 2.1 Deterministische Regel-Findings
Der bestehende `rule_checker` (R1–R67 + AP-01..AP-25) liefert harte und weiche
Findings mit Regel-IDs. Das Harness reimplementiert ihn nicht, sondern liest das
Ergebnis der Pipeline (`letter.last_check`).

Seit dem ersten Echt-Modelllauf (02.10.2026) enthält der Checker zusätzlich:
* **`R-INVENT` (hart) — Quellenbindung / Anti-Erfindung.** Der Text wird in Aussagen
  zerlegt; die substantiellen klinischen Terme je Aussage (Zahlen, Daten, Befunde,
  Diagnosen, Maßnahmen, anatomische/Medikamenten-/Nachsorgebegriffe) werden gegen das
  Diktat geprüft. Eine Aussage wird geflaggt, wenn sie **≥ 2 ungestützte Terme** enthält
  oder ein Empfehlungssatz ganz ohne Gegenstück in den Quellen ist. Legitime
  Umformulierungen bleiben unbeanstandet (kleine medizinische Synonymkarte,
  Stammformen, Komposita-Toleranz, Stopword-/Generik-Filter). Jeder Treffer zitiert die
  beanstandete Stelle (für die UI) und nennt die neuen Terme (für den Retry).
* **`R6-AUTOFIX` (weich) — deterministische Umlaut-Korrektur.** Bekannte ASCII-Umschreibungen
  (stationaer→stationär, Fluessigkeit→Flüssigkeit, …) werden vor der Prüfung über eine
  explizite, kuratierte Wortkarte normalisiert; korrekte Wörter (Aerosol, Oesophagus,
  Museum, neue, Quelle, Fluss, Prozess …) bleiben über eine Deny-List unangetastet. Jede
  Ersetzung wird als weiches Finding protokolliert (sichtbar in `letter.last_check`). Ein
  verbleibender, nicht gelisteter ASCII-Umlaut fällt weiterhin als hartes `R6` auf.
* **`R5` erweitert — Kategorie-Labels.** Neben den Colon-Labels (Labor:, KU:, Sono:, CT:,
  Anamnese:, Befund:, Therapie:, Diagnostik:, Mikrobiologie:, …) werden auch label-artige
  Listen-Opener ohne Colon erkannt (z. B. „Abschließende Kontrolle auf …“).

### 2.2 Echo-Erkennung (die Antwort auf den Einwand)
`tools/eval/eval_echo.py` normalisiert Diktat und Ausgabe (Umlaut-Faltung,
Kleinschreibung, Satzzeichen weg) und **entfernt vorher die Struktur-Labels**
(`Diagnosen:`, `Nebenerkrankungen:`, `Therapie-Maßnahmen auf der Station:`,
`Indikation:`, `OP:`, `Präparat:`, `Operation:` …), weil diese legitim in beiden
Texten stehen. Danach:

* **`similarity`** — `difflib.SequenceMatcher`-Ratio auf den Zeichenketten
  (die im Auftrag genannte Kennzahl),
* **`token_ratio`** — Ratio auf der Token-Folge,
* **`jaccard`** — Token-Mengen-Überlappung.

Verdikt: **`ECHO (keine eigene Formulierung)`**, wenn `similarity > 0.85`.
Zusätzlich wird ein **Content-Echo** ausgewiesen (`jaccard > 0.85`): eine reine
Umsortierung teilt alle Inhaltswörter, kann aber die Zeichenketten-Similarity unter
die Schwelle drücken — siehe §5.

**Schwelle je Dokumenttyp.** Für `zusammenfassung` und `entlassmedikationsplan` gilt eine
erhöhte Schwelle (0.92 statt 0.85): beide sind Kompressionsaufträge, deren korrekte Ausgabe
per Definition ein kondensierter Teil des Diktats ist — die Zeichenketten-Überlappung ist
dadurch von Natur aus höher. Die Standardschwelle 0.85 würde eine korrekte Kurzfassung
fälschlich als Echo markieren. `echo_threshold_for(doc_type)` liefert die Schwelle; sie
erscheint im `run.json` (`echo.threshold`) und in der Scorecard.

**Echo-Streuung.** Ein einzelner Lauf ist kein belastbares Echo-Urteil: derselbe Fall
lieferte im Echt-Modelllauf `similarity` **0.021** in einem Lauf und **0.957** im nächsten.
Deshalb gibt es `--repeat N`: jeder Fall läuft N-mal, ausgewiesen werden **Median und
Bereich** (der Median bestimmt den repräsentativen Lauf und fließt in die Aggregate ein).
Siehe §5.

### 2.3 `must_contain` / `must_not_contain`
Handgeschriebene Qualitätserwartungen je Fall. `must_contain` matcht als
umlautgefalteter Substring (deutsche Flexion/ Komposita toleriert); `must_not_contain`
matcht strikt als Ganzwort und ist label-scharf (ein Eintrag mit Doppelpunkt verlangt
ein echtes Label: `"CT:"` matcht nicht das bloße Wort „CT").

### 2.4 Strukturelle Prüfung
Blockpräsenz **und** -reihenfolge je Dokumenttyp (`expected_blocks` + kanonische
Reihenfolge). Beispiele: stationärer Entlassbrief = Empfehlungsblock → `Diagnosen:`
→ `Nebenerkrankungen:` → `Therapie-Maßnahmen auf der Station:`; Zusammenfassung = gar
keine Blöcke.

### 2.5 Optionaler LLM-Judge (`--judge-model`)
Ein unabhängiges, OpenAI-kompatibles Modell bewertet fünf Achsen 0–5 — Struktur &
Reihenfolge, Vollständigkeit, **keine Erfindung** (Diktat als einzige Faktenquelle),
Register & Abkürzungen, Plain-Text-Konformität — je mit einzeiliger Begründung und
wörtlichem Zitat der beanstandeten Stelle. Der Judge ist optional und
fehlertolerant: ein Judge-Fehler bricht keinen Lauf ab.

## 3. Was ausdrücklich NICHT gemessen wird (Ehrlichkeitshinweis)

* **Der Mock-Lauf misst keine Schreibqualität.** Er ist laut gebannert
  (`MOCK — misst KEINE Schreibqualität`) und darf nie als Qualitätsergebnis
  präsentiert werden. Er misst die Maschinerie auf einem realistischen Korpus.
* **Ein Echt-Urteil erfordert einen echten Modellanbieter** (`--provider openai`)
  **und die freigegebene Route** (lawyer/DSGVO-approved, DPA für den Anbieter,
  Pseudonymisierung aktiv). Solange die Freigabe fehlt, bleibt jede Qualitätsaussage
  eine Aussage über die Maschinerie — nicht über das Schreiben.
* **`must_contain`/`must_not_contain` sind handgeschrieben.** Coverage sagt „die
  erwarteten Fakten sind da", nicht „der Text ist schön". Genau dafür existiert der
  optionale Judge.
* **Der Judge ist ein Modell.** Er kann irren; seine Begründungen sind Belegmaterial,
  kein Urteil. Zwei Modelle, die sich gegenseitig bewerten, sind kein Ersatz für
  einen menschlichen Reviewer (Mohamed) — sondern ein Vortest, der die Auswahl
  eingrenzt.
* **Echo-Score allein ist kein Qualitätsmaß.** Ein niedriger Echo-Wert kann auch
  durch *fehlenden* Inhalt entstehen (siehe §5), nicht nur durch gelungene
  Umformulierung. Deshalb immer zusammen mit Coverage und Regel-Findings lesen.

## 4. Benutzung

```bash
# Offline-Selbstprüfung (Mock, alle Fälle)
cd /workspace/briefato
.venv/bin/python tools/eval/run_eval.py --provider mock --out /tmp/eval-mock

# Echter Modelllauf (A) — Key über BRIEFATO_LLM_API_KEY in der Umgebung, nie als Flag
.venv/bin/python tools/eval/run_eval.py --provider openai \
    --model mistral-large-latest --base-url https://api.mistral.ai/v1 \
    --out tools/eval/runs

# Modelllauf B
.venv/bin/python tools/eval/run_eval.py --provider openai \
    --model gpt-4o-mini --base-url https://api.openai.com/v1 \
    --out tools/eval/runs

# Optional: unabhängiger Judge im selben Lauf
.venv/bin/python tools/eval/run_eval.py --provider openai --model gpt-4o-mini \
    --out tools/eval/runs --judge-model mistral-large-latest

# Rauschen beherrschen: jeden Fall N-mal laufen, Echo als Median + Bereich
.venv/bin/python tools/eval/run_eval.py --provider openai --model gpt-4o-mini \
    --out tools/eval/runs --repeat 3

# A/B-Diff-Tabelle aus zwei fertigen Läufen
.venv/bin/python tools/eval/run_eval.py --compare \
    tools/eval/runs/<RUN_A>/run.json tools/eval/runs/<RUN_B>/run.json
```

Jeder Lauf schreibt `<out>/<run-id>/run.json` (Maschinenlesbar) und
`<out>/<run-id>/scorecard.md` (Menschenlesbar). Die Run-ID ist zeitgestempelt
(`YYYYmmdd-HHMMSS-provider-modell`). Zusätzlich wird **je Fall der erzeugte Text** unter
`<out>/<run-id>/cases/<id>.txt` abgelegt (bei `--repeat N` für den repräsentativen Lauf
plus `<id>.run1.txt` … `<id>.runN.txt`), damit ein Defekt nach dem Lauf diffbar ist; die
Scorecard verweist auf den Pfad.

### A/B zwischen zwei Modellen
1. Lauf A und Lauf B wie oben erzeugen.
2. `--compare RUN_A/run.json RUN_B/run.json` → Markdown-Diff-Tabelle
   (`compare-<A>__vs__<B>.md`) plus Konsolenausgabe.
3. Entscheidend für die Modellwahl: **Echo-Ratio sinkt** (echte Umformulierung),
   **must_contain-Abdeckung steigt** (nichts verloren), **harte Findings sinken**,
   **Judge-Mean steigt** — und der Judge begründet es mit Zitaten. Liegt ein Lauf im
   Mock-Modus, wird er in der Vergleichstabelle ausdrücklich als solcher markiert.

## 5. Scorecard lesen — die Mock-Baseline (ehrlich)

Realer Lauf vom 02.10.2026 (`--provider mock`, alle 14 Fälle):

| Metrik | Wert |
|---|---|
| Mean Echo-Similarity | 0.936 |
| Mean Token-Jaccard | 0.962 |
| **Echo-Fälle** (`similarity > 0.85`) | **11/14** |
| **Content-Echo-Fälle** (`jaccard > 0.85`) | **13/14** |
| Harte Regel-Findings (Summe) | 0 |
| Fälle mit harten Findings | 0 |
| must_contain-Abdeckung | 87.2 % (82/94) |
| must_not_contain-Verstöße | 0 |
| Strukturelle Fehlschläge | 2 (beide OP-Enrichment-Fälle) |
| Typ-Triage-Fehlschläge | 0 |

**Lesart.** Unter dem Mock sind **11 von 14** Fällen wörtliche Echos
(`similarity > 0.85`), und **13 von 14** teilen praktisch alle Inhaltswörter
(Content-Echo). Das ist die ehrliche Ausgangsbasis und genau Mohameds Punkt: der
Mock schreibt nichts, er kopiert und etikettiert um. Die drei nicht als „ECHO"
markierten Fälle sind **kein** Gegenbeweis — zwei OP-Berichte liegen nur deshalb
unter der Zeichenketten-Schwelle (0.78 / 0.76), weil der Mock die geforderte
Routine-Enrichment (Team-Time-out, Desinfektion, Capnoperitoneum, Wundverschluss) und
`Indikation:`-Struktur **weglässt** (Jaccard bleibt 1.000 → Content-Echo); die
Zusammenfassung liegt bei 0.60, weil der Mock auf vier Sätze kürzt und dabei Fakten
verliert (Coverage 2/5). Niedriger Echo-Wert heißt hier also **fehlender Inhalt**,
nicht gelungene Formulierung.

**Die zwei strukturellen Fehlschläge** sind die Enrichment-Fälle `opbericht-01/02`:
das Rohmaterial enthält absichtlich keine Routine-Schritte und kein
`Indikation:`-Label; ein echtes Modell soll sie standardgemäß aus dem Musterbrief
ergänzen (R52). Der Mock tut das nicht — genau der Pfad, den ein echtes Modell
beweisen muss.

**Zur Vorsicht bei Echt-Läufen.** Der erste Echt-Modelllauf (02.10.2026, DeepSeek
`deepseek-flash`) zeigte, dass die Echo-Similarity desselben Falls zwischen Läufen stark
schwankt: `zusammenfassung-01` lag bei **0.021** im 14er-Lauf und bei **0.957** im
Judge-Lauf; `ambulant-02` bei 1.000 bzw. 0.811. Ein Einzel-Lauf-Wert ist daher
**Rauschen** — belastbar ist nur der **Median über `--repeat N`** samt Bereich. Aus demselben
Grund wird der erzeugte Text je Fall unter `cases/<id>.txt` gespeichert, damit ein Befund
nachträglich diffbar ist statt nur als Zahl zu existieren.

## 6. Einen Fall hinzufügen

1. Datei `tools/eval/cases/<id>.json` anlegen; Felder siehe
   `tools/eval/README.md` (`id`, `doc_type`, `title`, `sources`, `dictation`,
   `must_contain`, `must_not_contain`, `expected_blocks`, `notes`).
2. **Keine echten Patientendaten** — erfundene Namen („Muster, Anna") oder `XXX`.
3. Erwartungen fachlich aus `brain/regelwerk.md` und
   `brain/dokumenttypen/<typ>.md` ableiten.
4. Vermeide Triage-Trigger-Wörter im falschen Fall (`pflegebericht`,
   `medikationsplan`, `OP-Bericht`, `Zusammenfassung`); eine Fehlleitung erscheint
   als `doc_type_match: false` und wird so sichtbar statt still. Der frühere
   `\bnachweis`-Fehlpfad ist behoben: ein klinisches „Malignitätsnachweis“ bleibt beim
   klinischen Dokument, nur ein echter KV-/WBO-/Weiterbildungs-/Logbuch-/QZ-/QS-Kontext
   routet auf `weiterbildung-kv-nachweise`.
5. `tools/eval/run_eval.py --provider mock --only <id>` laufen lassen und die
   Baseline-Zahlen prüfen.

## 7. Tests

```bash
cd /workspace/briefato
.venv/bin/python -m pytest app/tests/test_eval_harness.py -q
```

Deckt ab (offline, Mock): Echo-Erkennung (wörtliches Echo wird markiert, echte
Umformulierung passiert, Label-Überlappung allein zählt nicht), die Schwellen je
Dokumenttyp, `must_contain`/`must_not_contain`-Logik inkl. Label-Schärfe und
Flexionstoleranz, Struktur/Reihenfolge, Judge-Parsing, Corpus-Validierung, `--enrich`,
`--repeat` mit Median/Bereich und persistiertem Text, Subprozess-Lauf über eine
Zwei-Fall-Teilmenge mit Scorecard + Banner sowie der `--compare`-Modus.

Die neuen deterministischen Achsen (`R-INVENT`, `R6-AUTOFIX`, erweitertes `R5`) und die
Triage-Härtung sind zusätzlich in `app/tests/test_brain.py` bzw.
`app/tests/test_pipeline.py` abgedeckt: die beiden vom Judge beanstandeten Sätze werden
als `R-INVENT` gefangen, eine Synonym-Umformulierung nicht; die Umlaut-Karte korrigiert
`stationaer`/`Fluessigkeit`, lässt `Aerosol`/`Oesophagus`/`Museum`/`Prozess`/`Fluss`
unangetastet und protokolliert jede Ersetzung.

## 8. Grenzen (Zusammenfassung)

Das Harness kann **beweisen**: Routing/Block/Regel-Konformität auf einem realistischen
Korpus, Kopiergrad (Echo/Content-Echo), Erwartungsabdeckung, Struktur, Tokenverbrauch
und — mit einem echten Modell — eine A/B-Entscheidung samt Begründung.

Es kann **nicht beweisen**: dass ein Modell „gut schreibt", ohne dass ein echtes
Modell und die freigegebene DSGVO-Route im Einsatz sind; dass die Erwartungen selbst
vollständig sind; oder dass der Judge recht hat. Ein menschliches Urteil bleibt der
letzte Schritt — das Harness sorgt dafür, dass davor nichts mehr behauptet, sondern
gemessen wird.
