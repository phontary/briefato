# tools/eval — Briefato Qualitätsmessung

Der Qualitäts-Gate: macht **Schreibqualität messbar statt behauptet**.

Ausgangspunkt war Mohameds Einwand: *„in every test you write the whole letter
yourself precisely, and the output is just a copy of what you wrote — there is no
craft in it; I don't understand how you call that success."* Er hat recht: mit
`BRIEFATO_LLM_MOCK=true` erzeugt der Mock-Provider einen formrichtigen Entwurf, der
die Eingabe weitgehend spiegelt. Die bestehenden Tests beweisen damit die
**Maschinerie** (Routing, Retrieval, Regelprüfung, Speicherung, Isolation) — nicht
die Schreibqualität. Dieses Harness trennt beides.

## Bestandteile

| Datei | Zweck |
|---|---|
| `run_eval.py` | CLI-Runner: fährt jeden Fall durch die echte `generate_letter`-Pipeline und schreibt `run.json` + `scorecard.md`. |
| `eval_echo.py` | Echo-Erkennung: `difflib.SequenceMatcher`-Similarity + Token-Jaccard, Verdikt `ECHO (keine eigene Formulierung)` > 0.85; Schwellen je Dokumenttyp (0.92 für `zusammenfassung`/`entlassmedikationsplan`, weil Kompression naturgemäß mehr überlappt). |
| `eval_checks.py` | Deterministische Erwartungen: `must_contain` / `must_not_contain` / Blockpräsenz + -reihenfolge. |
| `eval_corpus.py` | Lädt und validiert die Fälle aus `cases/*.json`. |
| `eval_judge.py` | Optionaler LLM-Judge (0–5-Rubrik, fünf Achsen, mit Begründung + Zitat). **Referenz-bewusst**: die `no_invention`-Achse bekommt `allowed_reference` des Falls mitgeliefert; durch die Referenz gedecktes Standardwissen (Routine-OP-Schritte, Standardtechnik) zählt als belegt („aus Referenz"), nur patientenbezogene unbelegte Angaben als Erfindung. |
| `cases/*.json` | 14 synthetische, realistische deutsche Fälle (keine echten Patientendaten). |

Die R1–R67-Regelprüfung wird **nicht** neu implementiert — sie kommt read-only aus
`briefato.brain.rule_checker` (Aufruf innerhalb der Pipeline; das Harness liest das
Ergebnis aus `letter.last_check`).

## Benutzung

```bash
# Offline-Selbstprüfung mit dem Mock (misst NUR die Maschinerie)
tools/eval/run_eval.py --provider mock --out /tmp/eval-mock

# Nur einzelne Fälle
tools/eval/run_eval.py --provider mock --only entlassbrief-01 --only opbericht-01 --out /tmp/eval-a

# Echter Modelllauf (A) — OpenAI-kompatibler Endpoint, Key über BRIEFATO_LLM_API_KEY
tools/eval/run_eval.py --provider openai --model mistral-large-latest \
    --base-url https://api.mistral.ai/v1 --out tools/eval/runs

# Modell B
tools/eval/run_eval.py --provider openai --model gpt-4o-mini \
    --base-url https://api.openai.com/v1 --out tools/eval/runs

# Optional: unabhängiger LLM-Judge (andere Achsen als die deterministischen Checks)
tools/eval/run_eval.py --provider openai --model gpt-4o-mini \
    --out tools/eval/runs --judge-model mistral-large-latest

# Einzel-Läufe sind verrauscht (ein Fall schwankte zwischen 0.021 und 0.957):
# jeden Fall N-mal laufen und Echo als Median + Bereich ausweisen
tools/eval/run_eval.py --provider openai --model gpt-4o-mini \
    --out tools/eval/runs --repeat 3

# A/B-Vergleich zweier fertiger Läufe
tools/eval/run_eval.py --compare runs/A/run.json runs/B/run.json
```

Optionen: `--enrich` (siehe unten), `--model`, `--base-url`, `--judge-model`,
`--judge-base-url`, `--repeat N` (Echo-Median + Bereich), `--only` (mehrfach),
`--cases-dir`, `--tmp-dir`, `--out`, `--compare`.

Ausgabe je Lauf: `<out>/<run-id>/run.json` + `scorecard.md` **plus** `cases/<id>.txt`
(der erzeugte Text jedes Falls; bei `--repeat N` zusätzlich `<id>.run1.txt` … `<id>.runN.txt`)
— so lässt sich ein Defekt nach dem Lauf diffen, statt ihn nur als Zahl zu sehen.

Voraussetzung: Repo-Venv (`/workspace/briefato/.venv`), nur stdlib + App-Abhängigkeiten.
Ohne Netz nur im `mock`-Modus. Der Runner ist ein Single-Shot-Prozess: Settings und
SQLAlchemy-Engine werden beim Import aus der Umgebung gebunden (die DB wird in einem
temporären Verzeichnis angelegt).

## Fälle lesen / hinzufügen

Ein Fall (`cases/<id>.json`):

```json
{
  "id": "entlassbrief-01",
  "doc_type": "arztbrief",
  "title": "Stationärer Entlassbrief — …",
  "sources": [{"label": "Sono", "text": "…"}],
  "dictation": "…",
  "must_contain": ["stationär auf", "Diagnosen:"],
  "must_not_contain": ["Dg.:", "**"],
  "expected_blocks": ["Diagnosen:", "Therapie-Maßnahmen auf der Station:"],
  "allowed_reference": "Generisches Standardwissen (Routine-OP-Schritte, Standardtechnik), das der Judge als gedeckt ansehen muss",
  "notes": "…"
}
```

* `sources` — die unaufgeräumten KIS-Bausteine (Formular-Labels, Tippfehler,
  Abkürzungen, ASCII-Umlaute). Sie dokumentieren das Rohmaterial und sind die Eingabe
  für `--enrich`.
* `dictation` — der Text, der standardmäßig an die Pipeline geht.
* `must_contain` — was ein **guter** Output enthalten muss (Substring-Match,
  umlautgefaltet; deutsche Flexion toleriert: „Rektumkarzinom" matcht
  „Rektumkarzinoms").
* `must_not_contain` — was nie erscheinen darf (strikter Ganzwort-Match; mit
  Doppelpunkt wird ein echtes Label verlangt: `"CT:"` matcht nicht das Wort „CT").
* `expected_blocks` — erwartete Blockbeschriftungen in Reihenfolge.
* `allowed_reference` — optionales, **generisches** Standardwissen (z. B. die
  Routine-Schritte eines OP-Berichts), das der Judge als legitime Referenz ansieht.
  Kein Patientenfakt; nur für die Judge-Achse `no_invention`, nicht als Pipeline-Eingabe.
* `--enrich` hängt den vollständigen `sources`-Block an die `dictation` an (der
  un-verdichtete KIS-Export) — der Fall wird dann auf dem Rohmaterial statt auf dem
  kuratierten Diktat gefahren. Unabhängig davon ist die **Referenz-Anreicherung**
  (`REFERENZWISSEN`) pro Dokumenttyp geschaltet: `operationsbericht` ist
  standardmäßig **AN** (`BRIEFATO_ENRICH_DEFAULT_OPERATIONSBERICHT=false` schaltet sie
  ab, `BRIEFATO_ENRICH_DEFAULT` bleibt der globale Default) — sonst fehlten die
  Routine-Schritte.

### Regeln beim Schreiben von Fällen

* **Keine echten Patientendaten.** Namen wie „Muster, Anna" oder Platzhalter `XXX`.
* `must_contain`-Einträge ohne Doppelpunkt werden als Substring geprüft — wähle
  aussagekräftige Fachbegriffe.
* Vermeide im Diktat Wörter, die die Triage fälschlich umleiten (`pflegebericht`,
  `medikationsplan`, `OP-Bericht`, `Zusammenfassung` nur in den passenden Fällen). Das
  Harness erkennt eine Fehlleitung als `doc_type_match: false`. Der `\bnachweis`-Fehlpfad
  ist behoben: nur mit echtem KV/WBO/Weiterbildung/Logbuch/QZ/QS-Kontext routet er auf
  `weiterbildung-kv-nachweise`; „Malignitätsnachweis“ bleibt klinisch.
* Lauf `tools/eval/run_eval.py --provider mock` nach dem Anlegen, um die
  Baseline-Zahlen zu aktualisieren.

## Scorecard lesen

Der Gesamt-Block enthält:

* **Mean Echo-Similarity / Mean Token-Jaccard** — Kopiergrad.
* **Echo-Fälle** (`similarity > 0.85`) und **Content-Echo-Fälle** (Token-Jaccard
  > 0.85). Das zweite Signal fängt reine Umsortierungen ab, die die
  Zeichenketten-Similarity unterschätzt.
* **Harte/weiche Regel-Findings** aus `rule_checker` und die Fallanzahl.
* **must_contain-Abdeckung**, **must_not_contain-Verstöße**, **strukturelle
  Fehlschläge**, **Typ-Triage-Fehlschläge**, **Mean LLM-Judge**.

Der Pro-Fall-Block listet dieselben Werte je Fall; die Detailabschnitte nennen
fehlende Erwartungen, verletzte Verbote, die Echo-Zahlen und (falls konfiguriert) die
Judge-Begründungen.

## Was das Harness NICHT beweist

* Im **Mock-Lauf** (Banner `MOCK — misst KEINE Schreibqualität`) misst es
  ausschließlich die Maschinerie. Ein niedriger Echo-Wert im Mock ist sogar ein
  **Warnsignal**, kein Qualitätsbeweis: der Mock produziert ihn durch fehlenden
  Inhalt (Truncation, fehlende Enrichment-Schritte), nicht durch Formulierungskunst.
* Ein belastbares Schreibqualitäts-Urteil gibt es nur mit einem **echten
  Modellanbieter** (`--provider openai`) und der freigegebenen
  (lawyer/DSGVO-Approved) Route — siehe `docs/05-qualitaetsmessung.md`.
* `must_contain`/`must_not_contain` sind **handgeschriebene** Erwartungen; sie sind
  nur so gut wie der Fallautor.

## Selbstprüfung

```bash
cd /workspace/briefato
.venv/bin/python -m pytest app/tests/test_eval_harness.py -q
.venv/bin/python tools/eval/run_eval.py --provider mock --out /tmp/eval-mock
```
