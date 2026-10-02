# 02 — AVV-Checkliste (Auftragsverarbeitung, Art. 28 DSGVO)

Status: **Entwurf — muss bestätigt werden.** Grundlage: Art. 28 DSGVO,
https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02) (Text gegengeprüft:
https://gdpr-info.eu/art-28-gdpr/ , abgerufen 2026-10-02); DSK Kurzpapier Nr. 13 „Auftragsverarbeitung“
(Stand: in Überarbeitung), https://www.datenschutzkonferenz-online.de/media/kp/dsk_kpnr_13.pdf (abgerufen 2026-10-02).

## 1. Was ein AVV nach Art. 28 Abs. 3 DSGVO enthalten MUSS

Der Vertrag wird **schriftlich (auch elektronisch, Art. 28 Abs. 9)** geschlossen und muss
mindestens regeln:

| # | Pflichtinhalt (Art. 28 Abs. 3) | Umsetzung im Briefato-AVV |
|---|---|---|
| A1 | Verarbeitung **nur auf dokumentierte Weisung** des Verantwortlichen (inkl. Drittlandübermittlung) | Standardklausel + Weisungsprozess (E-Mail an Support) |
| A2 | **Vertraulichkeitsverpflichtung** aller zugriffsberechtigten Personen | NDA + § 203 Abs. 4 StGB-Verpflichtung (siehe § 3 unten) |
| A3 | **Art. 32-Maßnahmen** werden umgesetzt | Verweis auf `03-tom.md` als Anlage |
| A4 | **Unterauftragsverarbeiter** nur mit Genehmigung + gleiche Pflichten (Art. 28 Abs. 2/4) | Sub-Processor-Liste (§ 4) + Genehmigungsmechanik |
| A5 | **Unterstützung bei Betroffenenrechten** (Kapitel III) | Verweis auf `05-data-subject-rights.md` |
| A6 | **Unterstützung bei Art. 32–36** (Sicherheit, Meldungen, DPIA) | Meldeprozess (`06`), TOM (`03`) |
| A7 | **Löschung/Rückgabe** nach Vertragsende; Löschung von Kopien | `04-retention-deletion.md` |
| A8 | **Nachweis & Audits/Durchsicht** durch Verantwortlichen oder beauftragten Prüfer | Auditrechte + Berichtsvorlage |
| A9 | **Unverzügliche Information** bei rechtswidriger Weisung | Prozess |
| A10 | **Meldung von Verletzungen** an den Verantwortlichen (Art. 33 Abs. 2) | Frist im AVV konkretisieren (empfohlen: **≤ 24 h** an die Praxis) |
| A11 | Gegenstand, Dauer, Art/Zweck, Datenarten, Betroffenenkategorien | aus `01-processing-register.md` |
| A12 | Pflichten & Rechte des Verantwortlichen | Standardteil |
| A13 | Rückgabe-/Löschformat + Fristen | JSON/DOCX-Export + Löschprotokoll |
| A14 | Haftung/Unterauftragsverarbeiter-Regress | Standardteil |

Art. 28 Abs. 4: Bei Unterauftragsverarbeitung müssen dem Sub-Prozessor **dieselben Pflichten**
auferlegt werden; Briefato haftet gegenüber der Praxis für dessen Erfüllung. Art. 28 Abs. 2 erlaubt
**spezifische oder allgemeine schriftliche Genehmigung** — Briefato sollte die *allgemeine*
Genehmigung mit **Widerspruchsrecht + Änderungsmitteilung** wählen und die Liste als Anlage führen.

## 2. Was wir dem Kunden (der Praxis) liefern müssen

- [x] **AVV-Template** (Anlage zum SaaS-Vertrag/AGB) mit A1–A14.
- [x] **Sub-Processor-Liste** als Anlage, versioniert, mit Änderungsbenachrichtigung.
- [x] **TOM-Anlage** (= `03-tom.md` als Kundendokument).
- [x] **Kurzbeschreibung des Verarbeitungsgegenstands** (= Teil B aus `01-processing-register.md`).
- [x] **Lösch-/Rückgabeprozess** und Aufbewahrungsmatrix (`04`).
- [x] **Drittland-Mitteilung** (falls zutreffend) inkl. Schutzmaßnahmen.
- [x] **Vorlage für den Nachweis** der § 203-Abs. 4-Verpflichtung des Dienstleisters.
- [ ] **AVV für die Praxis zum Ausfüllen** — als editierbare Datei bereitzustellen (offen).

## 3. § 203 StGB — die Besonderheit, die über den AVV hinausgeht

AVV ≠ Geheimhaltungspflicht. § 203 StGB schützt das Berufsgeheimnis der Ärzt:innen/Psychotherapeut:innen
und Heilberufe; die Offenbarung an Briefato ist nur als „mitwirkende Person“ privilegiert.

- § 203 Abs. 3 StGB erlaubt, Geheimnisse gegenüber **sonstigen Personen, die an der beruflichen
  Tätigkeit mitwirken**, offenzulegen, **soweit dies für die Inanspruchnahme erforderlich ist**;
  das gilt auch für deren weitere Hilfspersonen.
- § 203 Abs. 4 Nr. 1 StGB stellt es **unter Strafe**, wenn der Geheimnisträger nicht dafür sorgt,
  dass die mitwirkende Person **zur Geheimhaltung verpflichtet** wurde.

**Konsequenz für den AVV / das Onboarding:** Der Dienstleister (Briefato) und **jede bei ihm
zugriffsberechtigte Person** (inkl. Sub-Prozessoren) müssen auf Geheimhaltung verpflichtet werden.
Empfehlung: eine Klausel im AVV, mit der Briefato der Praxis die Verschwiegenheitsverpflichtung
seiner Mitarbeiter nachweist, plus eine **formale Verschwiegenheitserklärung** für Admins.
Offen (M6): ob eine **Berufshaftpflicht/Strafrechtsschutz** das Deckungsrisiko aus § 203 StGB abbildet.

Quelle: § 203 StGB, https://www.gesetze-im-internet.de/stgb/__203.html (abgerufen 2026-10-02).

## 4. Unterauftragsverarbeiter-Liste (Entwurf)

| Kategorie | Anbieter | Land | Vertrag | Status |
|---|---|---|---|---|
| Hosting | N305 `phontary` / Betreiber (später EU-VPS) | DE (EU) | AVV Hosting | **offen M11** |
| Modell-Inferenz | Mistral AI (EU) | FR | AVV + Sub-Processor-Liste + No-Training | **offen M1** |
| Modell-Inferenz (Alternative) | Microsoft Azure OpenAI (EU-Region) | EU-Region / MS US | AVV + EU Data Boundary + SCC/DPF | **offen M1** |
| Modell-Inferenz (nicht empfohlen) | DeepSeek | CN | AVV + SCC + TIA | nicht empfohlen |
| Modell-Inferenz (max. Schutz) | lokale Inferenz im eigenen Container | DE (Host) | kein Drittland | v1-Non-Goal |
| Zahlungen | Stripe | IE/US | eigenständig + AVV soweit Verarbeiter | **offen M2** |
| E-Mail-Versand | noch nicht gewählt | DE/EU | AVV | **offen M11** |
| Backup-Ziel | noch nicht gewählt | DE/EU | AVV | **offen M11** |
| Fehler-/Uptime-Monitoring | Healthchecks (self-hosted, falls eigener Dienst) | DE | kein externes Drittland | geplant |

## 5. Drittlandfrage (Art. 44–49 DSGVO)

**Ausgangslage:** Pseudonymisierung (D4) senkt das Risiko, aber Übermittlungen an einen
Nicht-EU-Provider bleiben Übermittlungen i. S. d. Art. 44 ff. DSGVO.

| Szenario | Drittland? | Erforderliches Instrument | Empfehlung |
|---|---|---|---|
| Mistral (FR) | nein | nur AVV (Art. 28) | ✅ **empfohlen** — kein Transfer, EU-Recht |
| Azure OpenAI EU-Region | faktisch EU-Verarbeitung, **aber** US-Mutter mit potenziellem Support-/Telemetriezugriff | AVV + SCC + Transfer Impact Assessment; EU Data Boundary prüfen | ✅ tragfähig, mehr Aufwand |
| DeepSeek (CN) | ja | AVV + **SCC (Art. 46 Abs. 2 lit. c)** + TIA; kein Angemessenheitsbeschluss | ❌ **nicht empfohlen** für Art. 9-Daten |
| Lokale Inferenz | nein | keine | 🟡 technisch ideal, für v1 Non-Goal |

SCC-Fundstelle für Verantwortlicher-zu-Verarbeiter: Kommissions-Durchführungsbeschluss (EU) 2021/915,
https://eur-lex.europa.eu/eli/dec_impl/2021/915/oj (abgerufen 2026-10-02). Für
Verarbeiter-zu-Verarbeiter-Übermittlungen (Briefato → Sub-Prozessor) gelten die SCC-Module
(Modul 3). Art. 46 DSGVO: https://gdpr-info.eu/art-46-gdpr/ (abgerufen 2026-10-02).

**Klare Empfehlung:** Modell-Provider **EU-gehostet mit AVV** wählen (Mistral EU oder Azure EU).
Die erzwungene Pseudonymisierung bleibt als zweite Verteidigungslinie bestehen, ersetzt aber
**keinen** AVV. DeepSeek nur, wenn (a) Pseudonymisierung technisch erzwungen und getestet ist und
(b) nach anwaltlicher TIA das Restrisiko vertretbar ist — für besondere Kategorien nicht empfohlen.

## 6. Offene Punkte

- **offen:** AVV-Vertragstext selbst (Kanzlei oder Standardvorlage des Anbieters).
- **offen:** Meldepflicht-Frist Briefato → Praxis (Vorschlag 24 h) im AVV festschreiben.
- **offen:** Verfahren, wie Kunden über Wechsel von Sub-Prozessoren informiert werden.
- **muss bestätigt werden:** ob Hosting (N305, privat betrieben) als „Auftragsverarbeitung“ oder
  als eigene Verantwortlichkeit des Betreibers ausgestaltet ist — Rollenklärung nötig.
