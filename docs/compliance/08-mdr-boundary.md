# 08 — Medizinprodukt- und KI-VO-Abgrenzung + „Do not do“-Produktregeln

Status: **Entwurf — muss bestätigt werden** (anwaltliche/regulatorische Prüfung empfohlen).
Kernaussage: Briefato ist eine **Schreib-/Formatierhilfe**, **kein Medizinprodukt**, und die
KI-VO-Pflichten sind gering — aber nur, solange die Produktregeln (Abschnitt 4) eingehalten werden.

Quellen: MDR (VO (EU) 2017/745), https://eur-lex.europa.eu/eli/reg/2017/745/oj (abgerufen 2026-10-02);
MDCG 2019-11 „Guidance on Qualification and Classification of Software“, https://health.ec.europa.eu/system/files/2020-09/md_mdcg_2019_11_guidance_en_0.pdf (abgerufen 2026-10-02);
KI-VO Art. 4/6/50 + Anhang III, https://artificialintelligenceact.eu/article/50/ , https://artificialintelligenceact.eu/article/6/ , https://artificialintelligenceact.eu/annex/3/ (abgerufen 2026-10-02);
KI-VO-Zeitachse, https://artificialintelligenceact.eu/implementation-timeline/ (abgerufen 2026-10-02).

## 1. Warum Briefato kein Medizinprodukt ist (MDR)

Nach MDCG 2019-11 muss Software eine **eigene medizinische Zweckbestimmung** haben, um als
Medical Device Software (MDSW) zu gelten. Entscheidend ist der **vom Hersteller erklärte Zweck**
(„intended purpose“), nicht die bloße Nutzung im Gesundheitskontext.

Zitate aus MDCG 2019-11 (Z. 153–161):
- „not all software used within healthcare is qualified as a medical device. For example, ‘Simple
  search’ … does not qualify as medical device software.“
- „altering the representation of data for **embellishment/cosmetic or compatibility purposes does
  not readily qualify** the software as medical device software.“
- „A task such as e-mailing, web or voice messaging, data parsing, **word processing**, and back-up
  is **by itself not considered as having a medical purpose**.“
- „the risk of harm … is **not a criterion** on whether the software qualifies as a medical device.“

### 1.1 Einordnung von Briefato

| MDCG-Prüfschritt | Briefato | Ergebnis |
|---|---|---|
| Decision step 1: ist es Software? | ja | weiter |
| Decision step 2: Annex XVI / Zubehör / treibt Hardware? | nein | weiter |
| Decision step 3: „action on data“ beyond storage/search? | ja (Textumformung) | weiter → step 4 relevant |
| Decision step 4: **medizinischer Zweck?** | **nein** — die Software strukturiert **den vom Mitglied diktierten Text** in Brief-/Formularform und setzt den Briefkopf | **kein MDSW** |

Begründung: Briefato erzeugt **keine neue medizinische Information**, sondern **reformatiert und
strukturiert die Eingabe des Behandelnden**. Es liefert keine Diagnose, keine Bewertung, keine
Therapie-/Dosierungs-/Triageentscheidung. Der medizinische Inhalt stammt vom Behandelnden; das
Mitglied **gibt jeden Brief frei**.

## 2. KI-VO-Einordnung

| Frage | Bewertung |
|---|---|
| Ist Briefato ein „KI-System“ (Art. 3 Nr. 1)? | ja — wir setzen ein LLM ein |
| Rolle | Briefato ist **Anbieter** des KI-Systems (eigener Name) und **Betreiber** (deployer) ggü. der Praxis |
| **Hochrisiko (Art. 6 Abs. 1, Anhang III)?** | **nein** — kein Anhang-III-Fall (Biometrie, Kritische Infrastruktur, Bildung, Beschäftigung, Zugang zu Leistungen, Strafverfolgung, Migration, Justiz); **kein** Medizinprodukt-Requirement → keine automatische Hochrisiko-Einstufung |
| **Art. 50 Abs. 1** (Interaktion mit Personen) | **nicht einschlägig** — klassisches Webformular, keine „Interaktion mit einem KI-System“; zudem offensichtlich |
| **Art. 50 Abs. 2** (Markierung synthetischer Text) | **Ausnahme greift**: Pflicht gilt nicht, soweit das System „an **assistive function for standard editing**“ leistet bzw. die Eingaben **nicht wesentlich** verändert. Briefato editiert assistiv den eigenen Text des Mitglieds → Ausnahme naheliegend, **anwaltlich bestätigen** |
| **Art. 4 AI-Literacy** | **einschlägig** (seit 02.02.2025) → Schulung/Nachweis für Betreiber/Support nötig (offen, T30) |

### 2.1 Zeitachse (relevant)

| Datum | Ereignis | Bedeutung für Briefato |
|---|---|---|
| 02.02.2025 | Verbote + **Art. 4 AI-Literacy** gelten | Schulungspflicht umsetzen |
| 02.08.2025 | GPAI-Pflichten (Kap. V) gelten | betrifft **Modell-Provider**, nicht uns direkt — AVV/Unterlagen des Providers prüfen |
| 02.08.2026 | „übriger“ Teil gilt (u. a. Art. 50, Hochrisiko Art. 6(1)) | Art. 50-Ausnahme dokumentieren; kein Hochrisiko |
| 02.12.2026 | Art. 50(2) für **vor** 02.08.2026 in Verkehr gebrachte Textgeneratoren | relevant, falls wir Textgenerator sind — Ausnahme erneut prüfen |

> Hinweis: Es gab/gibt politische Diskussionen über Verschiebungen einzelner Hochrisiko-Fristen
> (Digital Omnibus). Da Briefato **nicht hochrisiko** ist, ist das für uns nachrangig — aber vor
> Launch noch einmal gegen die offizielle Kommissions-Seite prüfen.

## 3. Was wir dokumentieren müssen, um die Position zu verteidigen

- [ ] **Zweckbestimmungs-Erklärung** (intended purpose) schriftlich, eindeutig **nicht-medizinisch**.
- [ ] **Produktregeln** (Abschnitt 4) als veröffentlichte, versionierte Liste.
- [ ] **Change-Control**: Jede neue Funktion wird gegen die Produktregeln geprüft; Verstöße stoppen
      das Release. „Slack-Check“ als Pflicht-Gate.
- [ ] **Marketing-Review**: keine Claims zu Diagnose, Therapie, „Fehlerfreiheit“, „Arztbrief-
      Qualität“ oder medizinischer Korrektheit. Claims = Teil des „intended purpose“ und können die
      Einordnung kippen (MDCG Z. 197).
- [ ] **Prompt-/System-Prompt-Versionierung** (`pipeline/prompts.py`): Systemprompt darf keine
      medizinischen Empfehlungen verlangen.
- [ ] **Freigabe-Log** je Brief (`letters.approved_at`) als Nachweis der menschlichen Letztentscheidung.
- [ ] **KI-VO-Zeitachsen-Review** vor jedem Launch-Meilenstein.

## 4. „Do not do“ — Produktregeln, die uns aus dem MDR-Scope halten

**Verboten (nur mit vollständiger MDR-Konformitätsbewertung zulässig):**

| # | Verbot | Warum |
|---|---|---|
| V1 | **Keine Diagnosevorschläge / Differentialdiagnosen** | medizinische Zweckbestimmung → MDSW |
| V2 | **Keine Therapieempfehlungen** | dito |
| V3 | **Keine Dosierungsberechnung / -vorschläge** | dito |
| V4 | **Keine Triage / Priorisierung / Dringlichkeitseinschätzung** | dito (und Hochrisiko-Diskussion) |
| V5 | **Keine Interpretation von Befunden/Laborwerten/Bildern** („das EKG zeigt …“) | dito |
| V6 | **Keine Risikobewertung/Prognose** über den Patienten | dito |
| V7 | **Keine ICD-Codierung / Kodierungsvorschläge** | könnte medizinische Einordnung sein → anwaltlich prüfen, im Zweifel verboten |
| V8 | **Keine automatische Freigabe/Versand** ohne menschliche Bestätigung | die menschliche Letztentscheidung ist Teil der Abgrenzung |
| V9 | **Keine Werbung** mit „medizinisch geprüft“, „diagnoseunterstützend“, „Arztbrief-KI“ | Claims verschieben die Einordnung |

**Erlaubt (Kernprodukt):**
- Strukturieren/Formatieren des **vom Mitglied diktierten** Inhalts.
- Einsetzen von Briefkopf/Praxislogik, Rechtschreibung, Stil, Standardfloskeln, Layout.
- DOCX-Export, Verlauf, Suche, Mehrsprachigkeit der Ausgabe.

**Sicherung im Produkt:**
- Ein klarer **Disclaimer** im UI: „Schreibhilfe. Kein Medizinprodukt. Die medizinische
  Verantwortung liegt beim Behandelnden.“
- Jeder Brief muss **freigegeben** werden, bevor er genutzt/exportiert wird.
- Kein Feature-Flag darf die Verbote per Konfiguration umgehbar machen.

## 5. Offene Punkte

- **muss bestätigt werden:** anwaltliche MDR-/KI-VO-Einordnung (Kurzstellungnahme).
- **offen:** Systemprompt so formulieren, dass er keine medizinischen Empfehlungen provoziert
  (Artefakt `pipeline/prompts.py`).
- **offen:** AI-Literacy-Schulungsnachweis (T30).
- **offen:** Marketing-Claims gegen V9 prüfen.
- **muss bestätigt werden:** ob die Ausgabe-Mehrsprachigkeit oder „Verbesserung der Formulierungen“
  in Richtung „inhaltliche Bearbeitung“ kippt — Grenze anwaltlich ziehen.
