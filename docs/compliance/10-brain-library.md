# 10 — Referenzbibliothek Musterbriefe (Verarbeitungstätigkeit & Anonymisierungsstandard)

Status: **Entwurf — muss bestätigt werden.** Bestandsaufnahme am 2026-10-02 gegen die realen
Dateien in `/workspace/schreibdienst/musterbriefe/` und den Produkt-Abzug
`/workspace/briefato/brain/musterbriefe/` verifiziert (Manifest `count = 152`).
Grundlage: Art. 4 Nr. 1, Art. 5 Abs. 1 lit. c, Art. 9, Art. 28 DSGVO,
https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); Erwägungsgrund 26
(Anonymisierung/Pseudonymisierung), https://gdpr-info.eu/recitals/no-26/ (abgerufen 2026-10-02);
§ 203 StGB, https://www.gesetze-im-internet.de/stgb/__203.html (abgerufen 2026-10-02).

> **KEIN RECHTSRAT.** Rollen- und Rechtsgrundlagen-Aussagen hier sind Vorarbeiten für die
> anwaltliche Prüfung. Die Bewertung des Quellarchivs (Abschnitt 3.3) ist ausdrücklich offen.

## 0. Kurzfassung

Mit dem „Briefato Brain v1“ (Commit `ba65a09`) ist **Mohameds eigene medizinische
Referenzbibliothek** — 152 Musterbriefe — als neue Verarbeitungstätigkeit/Asset in das Produkt
eingezogen. Das ist eine **neue Datenquelle**, die im Verzeichnis von Verarbeitungstätigkeiten
(`01`), in den TOM (`03`) und im Threat Model (`06`) bisher fehlte. Drei Templates enthalten
Patientenspuren, vier Templates enthalten lizenzierte Fremdprosa; beide Gruppen sind **vor jedem
Einsatz zu bereinigen** und bis dahin über die Pipeline ausgeschlossen. Die Ausgabegrundlage des
Produkts bleibt **reiner Text** (Copy-Paste ins KIS); ein DOCX mit Briefkopf ist eine optionale
Sekundärausgabe.

## 1. Inhalt der Bibliothek

| Merkmal | Wert (verifiziert 2026-10-02) |
|---|---|
| Anzahl Musterbriefe | **152** (Quelle: `manifest.json` → `count`; die Datei `index.md` der Quelle zählt nicht mit) |
| Ablage | Fachlich gruppiert (Orthopädie/Unfallchirurgie, Hämatologie/Onkologie, Dermatologie/Infektiologie, Gastro, Kardio/Angio, … und `Sonstiges`) |
| Referenzsektionen | `Klinik`, `KU`, `Diagnostik`, `Therapie`, `Verlauf`, `Nachsorge`, `Therapieempfehlungen bei Entlassung`, `Diagnosen` |
| Optionale Sektionen | `Anamnese`, `OP`, `Quellen`, `Sonstiges` |
| Mit `## Quellen` | 4 Dateien (`has_quellen = 4`) |
| Lizenz-Review nötig | 4 Dateien (`licence_review = 4`) |
| Scrub-Flags | 8 (davon **3 manuell bestätigte Patientenspuren**, 5 False Positives) |
| Duplikat-Paare (Titelähnlichkeit ≥ 0,75) | 11 |

### 1.1 Sektionsabdeckung (aus `sectionstats.md`)

| Sektion | vorhanden | fehlt | Abdeckung |
|---|---|---|---|
| Klinik | 144 | 8 | 95 % |
| KU | 12 | 140 | 8 % |
| Diagnostik | 140 | 12 | 92 % |
| Therapie | 146 | 6 | 96 % |
| Verlauf | 20 | 132 | 13 % |
| Nachsorge | 115 | 37 | 76 % |
| Therapieempfehlungen bei Entlassung | 16 | 136 | 11 % |
| Diagnosen | 15 | 137 | 10 % |

Die Bibliothek taugt als **Struktur-/Formatreferenz** (welche Sektionen ein Brief welcher
Indikation typischerweise trägt), ist aber noch **keine konsistente Vorlagensammlung**: `KU`,
`Verlauf`, `Diagnosen` und Entlass-Empfehlungen fehlen in den meisten Briefen.

## 2. Wo die Bibliothek liegt

Es gibt **zwei getrennte Orte**. Das ist der zentrale Punkt für Compliance und Betrieb.

| Ort | Inhalt | Versionierung | Rolle |
|---|---|---|---|
| **Quellarchiv** `/workspace/schreibdienst/musterbriefe/` | 152 Musterbriefe als Volltext (Markdown) + `index.md` | **keine** — kein Git, kein Backend, kein Snapshot (verifiziert: kein `.git`) | Single Source of Truth (Volltext) |
| **Produkt-Abzug** `/workspace/briefato/brain/musterbriefe/` | `manifest.json` (Metadaten der 152 Briefe), `index.md`, `sectionstats.md`, `scrub-report.md`, `licence-review.md`, `build_library.py`, `retrieval_selftest.py` | Git (Repo `/workspace/briefato`, Commit `ba65a09`) | Produktseitige Karte/Katalog (**kein** Brieftext) |

**Verifiziert:** Der Produkt-Abzug enthält **keinen** Musterbrief-Volltext. Pro Template stehen im
Manifest nur `file`, `title`, `group`, `indication_keywords`, `sections_present`, `sections_missing`,
`headings_raw`, `has_quellen`, `licence_risk`, `chars`, `body_chars` — **kein** `body`/`content`/
`text`-Feld. Die Prosa bleibt ausschließlich im Quellarchiv.

## 3. Rollen und Rechtsgrundlage

### 3.1 Zwei Verarbeitungskontexte

| Kontext | Verantwortlicher | Briefato-Rolle | Personenbezug |
|---|---|---|---|
| **Aufbau/Pflege der Referenzbibliothek** (Mohameds eigene Fachbibliothek) | **Mohamed (Briefato-Inhaber)** als Urheber/Eigentümer des Archivs | eigenverantwortlich, **nicht** Auftragsverarbeitung | nach Anonymisierung: **nein**; aktuell bei 3 Templates: **ja** (Art. 9) |
| **Erzeugung eines Kundenbriefs** mit der Bibliothek als Struktur-/Formatreferenz | die **Praxis / das Mitglied** | **Auftragsverarbeiter** (Art. 28 DSGVO; § 203 Abs. 3 StGB mitwirkende Person) | ja (Patient der Praxis, Art. 9) |

**Konsequenz:** Der Kunden-AVV deckt **nicht** Mohameds eigene Bibliotheks-Pflege. Sobald die
Bibliothek keine patientenbezogenen Inhalte mehr trägt (Abschnitt 4), ist das Speichern/Wiederverwenden
der Vorlagen **keine Verarbeitung personenbezogener Daten** mehr und braucht dafür keine eigene
Rechtsgrundlage (ErwGr 26; Art. 4 Nr. 1 DSGVO). Bis dahin gilt das Gegenteil für die drei belasteten
Dateien.

### 3.2 Rechtsgrundlage im Kundengeschäft

Die Generierung des Briefes stützt sich auf die Rechtsgrundlage der **Praxis**
(Art. 9 Abs. 2 lit. h DSGVO i. V. m. § 22 Abs. 1 Nr. 1 lit. b BDSG). Briefato verarbeitet nur auf
dokumentierte Weisung. Die Bibliothek selbst trägt dazu **keine** Patientendaten bei, sobald sie
bereinigt ist.

### 3.3 Offen — Quellarchiv als personenbezogene Daten

- **muss bestätigt werden:** Rechtsgrundlage dafür, dass Mohamed die drei belasteten Dateien in einem
  **privaten** Archiv (`/workspace/schreibdienst/`) hält. Behandlungsdokumentation unterliegt der
  Aufbewahrungspflicht der **Praxis** (§ 630f BGB), nicht des Dienstleisters. Das Quellarchiv ist
  **nicht** durch den Kunden-AVV gedeckt.
- **muss bestätigt werden:** ob weitere, vom Scrub noch nicht erfasste Dateien verkettbare
  Patientenspuren tragen (z. B. seltene Diagnose + exakte Zeitangabe + ITS-Fenster).

## 4. Anonymisierungsstandard für Templates

**Ziel:** Jede Vorlage drückt **patientenunabhängige, generische Aussagen** aus. Sie darf weder
allein noch durch Verkettung mit einer anderen Datei (Visitenliste, Log, Verlaufsdatei) eine Person
bestimmbar machen (Art. 4 Nr. 1 DSGVO, ErwGr 26).

### 4.1 Erlaubt / Verboten

| Erlaubt (generisch) | Verboten (identifizierend / fallbezogen) |
|---|---|
| „Bei symptomatischer Cholezystolithiasis erfolgte die laparoskopische Cholezystektomie.“ | Klarname, Initialenkombination, „Herr/Frau <Name>“ |
| Sektionen `Klinik`, `Diagnostik`, `Therapie`, `Nachsorge` (+ ggf. `Quellen` als reine Lese-Referenz) | Fall-/Aufnahme-/Versicherungsnummer, `Fall <Nachname>`-Kennungen |
| Relative Zeitangaben („postoperativ“, „im Verlauf“) | Exakte Datumsangaben (Geburts-, Aufnahme-, OP-, Entlassdatum) |
| Beschreibung des typischen Vorgehens bei einer Indikation | Fallnarrativ eines konkreten Behandlungsverlaufs („die Patientin stellte sich am … vor“) |
| Offene Platzhalter für ein beliebiges Datum (kein echtes Datum) | Einzelmerkmale, die eine Person in Kombination singulär machen (seltene Diagnose + Alter + Ort + Zeitfenster) |

### 4.2 Definitions of Clean (Vorlage)

Eine Vorlage gilt als **clean**, wenn:

1. **kein** Identifier der Kategorien Name / Geburtsdatum / exaktes Behandlungs- oder OP-Datum /
   Fall-, Aufnahme- oder Versicherungsnummer / Anschrift / Telefonnummer im Text steht;
2. kein **Fallnarrativ** enthalten ist, das einen konkreten Einzelverlauf nacherzählt;
3. kein Merkmalsbündel bleibt, das allein oder per Verkettung mit einer anderen Datei eine Person
   bestimmbar macht (Verkettungstest gegen die Visitenliste);
4. ausschließlich generische Fachaussagen zur Indikation stehen (Sektionsstandard siehe 4.1);
5. im Register (`manifest.json`) kein `scrub_pending` mehr für die Datei gesetzt ist.

## 5. Wie die Bibliothek ins Produkt gelangt

1. `brain/musterbriefe/build_library.py` liest das Quellarchiv **read-only** und schreibt
   `manifest.json`, `index.md`, `sectionstats.md`, `scrub-report.md`, `licence-review.md` in den
   Produkt-Abzug. **Kein Volltext wird kopiert** (Docstring und verifiziertes Manifest belegen das).
2. `manifest.json` trägt `source` (Pfad) und `generated` (ISO-Zeitstempel) — Nachvollziehbarkeit der
   Herkunft, nicht der Integrität.
3. `retrieval_selftest.py` prüft die **Retrieval-Qualität** des Katalogs (Keyword-Scorer, 15
   Testanfragen, Top-1-Trefferquote). Sie arbeitet nur gegen `manifest.json`.
4. Der eigentliche Volltext wird bei der Briefgenerierung **nicht** aus dem Produkt-Abzug gelesen —
   er liegt im Quellarchiv. Damit ist der Produkt-Abzug heute ein **Katalog, keine Auslieferungs-
   quelle**.

**Offen:** Der Pfad, über den der Volltext eines ausgewählten Templates zur Laufzeit ins Produkt
gelangt, ist **noch nicht implementiert** (Wiedergabe des Templates/der Struktur an das Modell).
Vor Inbetriebnahme braucht dieser Pfad denselben Gate wie in Abschnitt 7.

## 6. Versionierungs- und Sync-Modell

| Aspekt | Ist-Zustand | Bewertung / Empfehlung |
|---|---|---|
| Source of Truth | Quellarchiv `/workspace/schreibdienst/musterbriefe/` | **nicht versioniert, kein Backup** → Single Point of Failure (siehe `06`, D5) |
| Produkt-Abzug | Git-Repo, Commit `ba65a09` | versioniert; Änderungen sind nachvollziehbar |
| Rebuild | `build_library.py` liest Quelle, schreibt Abzug | idempotent, aber **ohne** Checksumme/Version-Feld im Manifest → Rebuild-Drift nicht erkennbar |
| Herkunftsnachweis | `manifest.json` → `source`, `generated` | **fehlt:** Content-Hash je Template, `library_version`, `reviewed_by`, `reviewed_at` |

**Empfehlung (offen, nicht umgesetzt):**
- Quellarchiv in Versionskontrolle + Off-host-Backup überführen (mindestens verschlüsselt, eine Kopie
  außerhalb des Hosts).
- `manifest.json` um je Template `sha256`, `library_version`, `anonymisation_status`
  (`clean`/`pending`), `licence_status` (`free`/`review`), `duplicate_group`, `reviewed_by`,
  `reviewed_at` erweitern.
- Rebuild-Schritt an einen **Anonymisierungs- und Lizenz-Gate** koppeln (Abschnitt 7 / `11`).

## 7. Neues Template aus einem Kundenbrief (Proposal → Freigabe)

Wenn ein generierter Kundenbrief eine Indikation zeigt, für die es noch keine Vorlage gibt, gilt
**ausschließlich** dieser Weg — kein automatisches Anlernen aus Kundendaten:

1. **Proposal** (menschlich ausgelöst): Ein Bearbeiter schlägt eine neue Vorlage/Indikation vor.
2. **Abstraktion, nicht Übernahme:** Es wird **nur** die generische Struktur (Sektionen, typischer
   Ablauf, Formulierungsmuster ohne Patientendaten) abgeleitet — **keine** Kundentexte, keine
   Namen, keine Daten, keine Fallnarrative (Art. 5 Abs. 1 lit. c DSGVO).
3. **Anonymisierungs-Prüfung** gegen den Standard aus Abschnitt 4 (Verkettungstest).
4. **Lizenzprüfung**: keine Übernahme lizenzierter Fremdprosa (UrhG § 2/§ 15/§ 51/§ 44b; siehe `11` B).
5. **Menschliche Freigabe** durch den Inhaber (Content-Owner); Eintrag `reviewed_by`/`reviewed_at`.
6. Erst dann Aufnahme in Katalog und Retrieval. **Kein** Weg, auf dem Model-Output ungeprüft zu
   einer Vorlage wird.

## 8. Offene Punkte / Blocker

- **offen (Blocker):** Anonymisierungs-Gate nicht implementiert — es gibt **kein** automatisiertes
  Verfahren, das ein Template mit Patientenspur am Ingest hindert (heute nur manueller Scrub +
  Pipeline-Ausschluss, siehe `11`).
- **offen (Blocker):** Inhaltslizenz-Prüfprozess für Fremdprosa fehlt — 4 Templates sind markiert,
  aber es gibt **keinen** formalen Paraphrase-/Freigabeprozess.
- **offen:** Quellarchiv nicht versioniert und ohne Backup → Datenverlust-/Integritätsrisiko (D5 in `06`).
- **offen:** Volltext-Retrieval-Pfad ins Produkt nicht implementiert.
- **offen:** per-Template `sha256`/`library_version` fehlen im Manifest → Rebuild-Drift nicht messbar.
- **muss bestätigt werden:** Rechtsgrundlage des privaten Quellarchivs (Abschnitt 3.3).

## 9. Quellen

- DSGVO (VO (EU) 2016/679), https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); Art. 4 (Begriffe, u. a. personenbezogene Daten), https://gdpr-info.eu/art-4-gdpr/ (abgerufen 2026-10-02).
- Erwägungsgrund 26 (Identifizierbarkeit, Anonymisierung), https://gdpr-info.eu/recitals/no-26/ (abgerufen 2026-10-02).
- Art. 28 DSGVO (Auftragsverarbeitung), https://gdpr-info.eu/art-28-gdpr/ (abgerufen 2026-10-02).
- § 203 StGB (Verletzung von Privatgeheimnissen), https://www.gesetze-im-internet.de/stgb/__203.html (abgerufen 2026-10-02).
- § 630f BGB (Dokumentation der Behandlung — Aufbewahrung liegt bei der Praxis), https://www.gesetze-im-internet.de/bgb/__630f.html (abgerufen 2026-10-02).
- UrhG § 2 (geschützte Werke / Sprachwerke), https://www.gesetze-im-internet.de/urhg/__2.html (abgerufen 2026-10-02).
- UrhG § 15 (Verwertungsrechte), https://www.gesetze-im-internet.de/urhg/__15.html (abgerufen 2026-10-02).
- UrhG § 44b (Text und Data Mining, inkl. Nutzungsvorbehalt), https://www.gesetze-im-internet.de/urhg/__44b.html (abgerufen 2026-10-02).
- UrhG § 51 (Zitate), https://www.gesetze-im-internet.de/urhg/__51.html (abgerufen 2026-10-02).
- Interne Belege: `brain/musterbriefe/manifest.json`, `index.md`, `sectionstats.md`, `scrub-report.md`, `licence-review.md` (Stand 2026-10-02T18:37:42Z).
