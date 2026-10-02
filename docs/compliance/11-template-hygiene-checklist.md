# 11 — Template-Hygiene-Checkliste (Patientenspuren, Lizenzprosa, Duplikate)

Status: **Entwurf — muss bestätigt werden.** Bestandsaufnahme am 2026-10-02 verifiziert gegen
`/workspace/briefato/brain/musterbriefe/manifest.json`, `scrub-report.md`, `licence-review.md` und
`sectionstats.md` sowie die realen Dateien in `/workspace/schreibdienst/musterbriefe/`.
Grundlage: Art. 4 Nr. 1, Art. 5 Abs. 1 lit. c, Art. 9 DSGVO,
https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); ErwGr 26,
https://gdpr-info.eu/recitals/no-26/ (abgerufen 2026-10-02).
UrhG § 2, https://www.gesetze-im-internet.de/urhg/__2.html (abgerufen 2026-10-02);
§ 15, https://www.gesetze-im-internet.de/urhg/__15.html (abgerufen 2026-10-02);
§ 51, https://www.gesetze-im-internet.de/urhg/__51.html (abgerufen 2026-10-02);
§ 44b, https://www.gesetze-im-internet.de/urhg/__44b.html (abgerufen 2026-10-02).

> **KEIN RECHTSRAT.** Die Lizenzbewertung (Abschnitt B) und die Archiv-Rechtsgrundlage (`10` § 3.3)
> sind Vorarbeiten; die endgültige urheber-/nutzungsrechtliche Bewertung muss eine Kanzlei treffen.

## 0. Wie diese Checkliste benutzt wird

Jede Zeile ist eine **abzuarbeitende Aufgabe** mit: Datei(en) → Maßnahme → wer entscheidet →
**Definition of Clean**. Die Pipeline darf eine Vorlage erst zur Briefgenerierung heranziehen, wenn
ihr `anonymisation_status = clean` **und** `licence_status = free` ist. Bis dahin sind die Dateien
`scrub_pending` / `licence_risk = review` und **vom Ingest ausgeschlossen**.

## A. Patientendaten in 3 Templates (Priorität 1)

Quelle: `scrub-report.md`, Abschnitt „Manuell bestätigte Treffer“. **Aktion bis zur Bereinigung: Datei
darf nicht ins Retrieval.**

- [ ] **A1 — `Cholezystolithiasis.md`**
  - **Fund:** Im Abschnitt `## Nachsorge` eine personenbezogene Fallkennung der Form
    „(Nutzerfassung TT.MM.JJJJ, Fall &lt;Nachname&gt;)“ mit einem **realen Patienten-Nachnamen**.
    Derselbe Nachname steht in `/workspace/schreibdienst/visitenliste-2026-09-22.md` mit Vorname,
    Alter und Fallcode — d. h. **direkt re-identifizierbar**. (Name hier absichtlich nicht
    ausgeschrieben.)
  - **Maßnahme:** Fallkennung **und** Datum löschen; nur den generischen Empfehlungs-Wortlaut der
    Sektion behalten.
  - **Entscheidet:** Inhaber (Content-Owner) redigiert; WORKSTREAM-PIPELINE setzt den Ausschluss um.
  - **Definition of Clean:** kein `<Nachname>`, keine `Fall …`-Kennung, kein Datum in der Sektion;
    Sektion nur generisch; Verkettungstest gegen `visitenliste-2026-09-22.md` ergibt **keinen**
    Treffer; `anonymisation_status = clean` gesetzt.

- [ ] **A2 — `Acne-inversa.md`**
  - **Fund:** konkretes OP-Datum „Z.n. Exzision in toto am 03.06.2026“ (real, datierbar; kein Name).
  - **Maßnahme:** Datum entfernen bzw. generisch machen (z. B. „Z.n. Exzision in toto am re.
    Schambein“ ohne Datum).
  - **Entscheidet:** Inhaber (Content-Owner).
  - **Definition of Clean:** keine Kalenderdaten im Text; nur relative/generische Zeitangaben oder
    Platzhalter; `anonymisation_status = clean`.

- [ ] **A3 — `Struma_nodosa_Hyperthyreose.md`**
  - **Fund:** de-identifiziertes **Fallnarrativ** (echter Entlassbrief) mit Platzhaltern
    `[Name]`, `[Datum]`, `[Wert]`, `[Zeitraum]`, `[Uhrzeit]`. Kein Klarname mehr sichtbar.
  - **Maßnahme:** als „de-identifiziertes Fallbeispiel“ kennzeichnen **und** auf residuale
    Identifier prüfen (exakte Daten, ITS-Zeitfenster, seltene Merkmalskombination).
  - **Entscheidet:** Inhaber (Content-Owner); im Zweifel (seltene Konstellation) nicht ausliefern.
  - **Definition of Clean:** kein residualer Identifier, der die Person (allein oder per Verkettung)
    bestimmbar macht; Narrativ ist generisch oder die Datei wird **nicht** ins Produkt übernommen.

### A.1 Weitere Scrub-Flags (geprüft, unkritisch — nur bestätigen)

- [ ] **A4 — False Positives bestätigen und unverändert lassen:** `Baker_Zyste.md` (Telefonnummer),
  `Coxarthrose_Exsikkose_Sturz.md` (Datum = AWMF-Leitlinienstand, kein Patientendatum),
  `Distorsion_Daumen_Grundgelenk.md` (Telefonnummer), `Dorsale_Spondylodese_LWS.md` (Telefonnummer),
  `Kontusion_Grosszehe.md` (Telefonnummer).
  - **Entscheidet:** Inhaber. **Definition of Clean:** Treffer als unkritisch bestätigt; kein Fallnarrativ.
- [ ] **A5 — `Nadelstichverletzung.md`:** „(Fall-Nr.)“ ist ein Dokumentations-Platzhalter, **keine**
  Nummer → unkritisch. **Definition of Clean:** als False Positive bestätigt.

## B. Lizenzierte Fremdprosa in 4 Templates (Priorität 2)

Quelle: `licence-review.md` (`licence_review = 4`). Marker: DocCheck Flexikon, MSD Manual,
AWMF/DGVS-Leitlinien, PubMed — teils **im Fließtext in Klammern** (starkes Indiz für (teil-)wörtliche
Übernahme).

- [ ] **B1 — `Coxarthrose_Exsikkose_Sturz.md`** — `## Quellen` (DocCheck Flexikon, MSD Manual, AWMF S2k Koxarthrose)
- [ ] **B2 — `Pangastritis.md`** — `## Quellen` (DocCheck, MSD Manual, AWMF S2k H. pylori, PubMed); langer enzyklopädischer Text
- [ ] **B3 — `Papillaere_Pankreatitis.md`** — `## Quellen` (DocCheck, MSD Manual, AWMF/DGVS S3 Pankreatitis); Fließtext mit wörtlichen Leitlinien-Wiedergaben und Quellenkürzeln
- [ ] **B4 — `Proktitis.md`** — `## Quellen` (DocCheck, MSD Manual, AWMF S3 Colitis ulcerosa, DGVS, PubMed PMID); Klammerverweise direkt im Fließtext

**Maßnahme je Datei:**

1. Fließtext **paraphrasieren** (eigene Formulierung, medizinisch korrekt, Leitlinie nur als
   Fakten-Referenz, nicht als Satzspender).
2. Quellen-Klammern **im Fließtext** entfernen.
3. `## Quellen` als **reine interne Lese-Referenz** behalten — **nie** in generierte Kundenbriefe,
   Few-Shot-Beispiele oder Trainingsdaten übernehmen.
4. `licence_risk` von `review` auf `free` setzen, erst nach dokumentierter Paraphrase-Freigabe.

- **Entscheidet:** Inhaber (Paraphrase); **Rechtsanwalt** (endgültige urheber-/nutzungsrechtliche
  Freigabe der 4 Dateien und der Quellen selbst). **Das braucht anwaltliche Prüfung.**
- **Definition of Clean:** kein wörtlicher Satz aus einer lizenzierten Quelle; keine Quellen-/
  Autoren-Klammern im Fließtext; `## Quellen` nur als interne Referenz; `licence_risk = free`.
- **Regel (aus `licence-review.md`):** *„Die Struktur eines Musterbriefs darf uns inspirieren, die
  lizenzierte Prosa nicht.“*

> Hinweis: `Papillaere_Pankreatitis.md` ist zusätzlich Teil der Duplikat-Prüfung (C, Paar C6) und
> `Coxarthrose_Exsikkose_Sturz.md` eines der „zu lang (> 4000 Zeichen)“-Dateien. Beide Maßnahmen
> zusammen abarbeiten.

## C. Near-Duplicate-Templates (Priorität 3)

Zwei Listen: **(C.1)** die 11 automatischen Titelähnlichkeits-Paare (≥ 0,75) aus `sectionstats.md`,
**(C.2)** zusätzliche manuelle Themencluster. Die Zählungen überschneiden sich fachlich — beide
Listen sind abzuarbeiten.

### C.1 Automatische Paare (n = 11)

| # | Datei A | Datei B | Empfehlung | Entscheidet | Definition of Clean |
|---|---|---|---|---|---|
| C1 | `Diabetes_mellitus_Typ1.md` | `Diabetes_mellitus_Typ2.md` | **behalten** (bewusst: Typ 1/2) | Inhaber | beide bleiben, Abgrenzung dokumentiert (`variant`-Feld) |
| C2 | `Kontusion_Grundgelenk_Kleinfinger.md` | `Kontusion_Grundgelenk_Ringfinger.md` | **mergen** zu einem Kontusions-Template | Inhaber | eine Datei (oder Slots statt Duplikat) |
| C3 | `Chronische_Niereninsuffizienz_CKD3.md` | `Chronische_Niereninsuffizienz_dialysepflichtig.md` | **behalten** (Dialyse ja/nein) | Inhaber | Abgrenzung dokumentiert |
| C4 | `Nadelstichverletzung.md` | `Stichverletzung.md` | **prüfen/mergen** | Inhaber | ein generisches Template oder klare Trennung |
| C5 | `Biliaere_Pankreatitis.md` | `Papillaere_Pankreatitis.md` | **abgrenzen** (plus B3) | Inhaber + Anwalt (B3) | nicht überlappend; B3 bereinigt |
| C6 | `Kontusion_Kleinzehe.md` | `Kontusion_Mittelzehe.md` | **mergen** zu einem Zehen-Template | Inhaber | eine Datei mit Varianten-Slot |
| C7 | `Choledocholithiasis.md` | `Cholezystolithiasis.md` | **abgrenzen** (plus A1) | Inhaber | nicht überlappend; A1 bereinigt |
| C8 | `Bissverletzung.md` | `Stichverletzung.md` | **mergen/abgrenzen** | Inhaber | ein Wund-/Verletzungstemplate oder klare Trennung |
| C9 | `Insektenstich.md` | `Zeckenstich.md` | **prüfen** (unterschiedliche Erreger) | Inhaber | Unterschied (Borreliose/FSME) benannt oder gemergt |
| C10 | `Distorsion_Daumen_Grundgelenk.md` | `Distorsion_Sprunggelenk.md` | **behalten** (verschiedene Gelenke) | Inhaber | Abgrenzung dokumentiert |
| C11 | `Abrissfraktur-Basis-MFK-V.md` | `Metatarsalefraktur_Basis_MFK_II.md` | **prüfen** (MFK V vs. MFK II) | Inhaber | Unterschied benannt oder gemergt |

### C.2 Zusätzliche manuelle Themencluster (`sectionstats.md`)

| Thema | Dateien | Empfehlung | Definition of Clean |
|---|---|---|---|
| Erysipel | `Erysipel.md`, `Erysipel_Wundrose.md` | **mergen** (redundant) | ein Template |
| pAVK | `pAVK.md`, `pAVK_Mediasklerose.md` | **konsolidieren** (Mediasklerose = Sonderfall) | ein Template mit Sonderfall-Hinweis |
| Narbenhernie epigastrisch | `Narbenhernie_epigastrische_IPOM.md`, `Narbenhernien_epigastrisch.md` | **mergen** | ein Template |
| Leistenhernie | `Leistenhernie_Inguinalhernie_TAPP.md`, `Leistenhernie_Inguinalhernie_Lichtenstein.md` | **behalten** (zwei OP-Techniken) | Abgrenzung dokumentiert |
| Gallenwege | `Cholezystolithiasis.md`, `Choledocholithiasis.md`, `Gallenblasenpolypen_Konkremente_Verdacht.md`, `Gangraenose_Cholezystitis_CHE.md` | **abgrenzen** | je Brief eigene Indikation |
| Pankreatitis | `Biliaere_Pankreatitis.md`, `Papillaere_Pankreatitis.md` | **abgrenzen** | siehe C5 |

- **Entscheidet:** Inhaber (Content-Owner) — Mergen vs. bewusst getrennt halten.
- **Definition of Clean (global C):** Für jedes Paar gilt **entweder** „gemergt“ (eine Datei, kein
  Near-Duplikat) **oder** „bewusst getrennt“ mit dokumentierter, nicht überlappender Abgrenzung im
  Manifest (`variant`/`intended_for`). Kein Paar bleibt undokumentiert.

## D. Freigabe-Gate (Definition of Done für die Bibliothek)

- [ ] `manifest.json` trägt je Template: `anonymisation_status` (`clean`/`pending`),
  `licence_status` (`free`/`review`), `duplicate_group`, `sha256`, `reviewed_by`, `reviewed_at`.
- [ ] Kein Template mit `anonymisation_status = pending` oder `licence_status = review` wird ins
  Retrieval/Few-Shot aufgenommen (Pipeline erzwingt das technisch).
- [ ] Die 3 Patientenspur-Dateien (A1–A3) und die 4 Lizenz-Dateien (B1–B4) sind abgearbeitet und
  dokumentiert.
- [ ] Die 11 automatischen Paare (C.1) und die manuellen Cluster (C.2) sind entschieden und im
  Manifest dokumentiert.
- [ ] Rebuild-Nachweis: `build_library.py` neu gelaufen, `scrub_pending = 0`, `licence_review = 0`.
- [ ] Rechtliche Freigabe durch die Kanzlei für die Lizenzfrage (B) und das Quellarchiv (`10` § 3.3).

## E. Offene Punkte

- **offen (Blocker):** kein automatisiertes Anonymisierungs-Gate (Auschluss heute nur manuell + Report).
- **offen (Blocker):** kein formaler Inhaltslizenz-Prüfprozess.
- **offen:** `manifest.json` hat noch keine per-Template-Statusfelder (Abschnitt D, erster Punkt).
- **muss bestätigt werden:** Inhaber-Freigabe A1–A3/C; **Anwalt**-Freigabe B.

## F. Quellen

- DSGVO Art. 4/5/9, https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); Art. 4 (Begriffe), https://gdpr-info.eu/art-4-gdpr/ (abgerufen 2026-10-02); ErwGr 26, https://gdpr-info.eu/recitals/no-26/ (abgerufen 2026-10-02).
- UrhG § 2 (Sprachwerke), https://www.gesetze-im-internet.de/urhg/__2.html (abgerufen 2026-10-02); § 15 (Verwertungsrechte), https://www.gesetze-im-internet.de/urhg/__15.html (abgerufen 2026-10-02); § 51 (Zitate), https://www.gesetze-im-internet.de/urhg/__51.html (abgerufen 2026-10-02); § 44b (Text und Data Mining), https://www.gesetze-im-internet.de/urhg/__44b.html (abgerufen 2026-10-02).
- Interne Belege: `brain/musterbriefe/scrub-report.md`, `licence-review.md`, `sectionstats.md`, `manifest.json` (Stand 2026-10-02T18:37:42Z).
