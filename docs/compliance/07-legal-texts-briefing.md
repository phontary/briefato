# 07 — Briefing für Anwalt/Inhaber: Rechtstexte der Website

Status: **Entwurf / Briefing — kein fertiger Rechtstext.** Dieses Dokument sagt, *was* die Texte
leisten müssen; es liefert **keine** finalen Formulierungen. Die auf der Website verwendeten
Platzhalter (Stage S3: „Impressum/Datenschutz/AGB placeholders marked for legal review“) sind
**nicht rechtsgültig** und müssen anwaltlich erstellt bzw. freigegeben werden.

Grundlagen: § 5 DDG, https://www.gesetze-im-internet.de/ddg/__5.html (abgerufen 2026-10-02);
§ 6 PAngV, https://www.gesetze-im-internet.de/pangv_2022/__6.html (abgerufen 2026-10-02);
§ 356 BGB, https://www.gesetze-im-internet.de/bgb/__356.html (abgerufen 2026-10-02);
§ 25 TDDDG, https://www.gesetze-im-internet.de/ttdsg/__25.html (abgerufen 2026-10-02);
§ 19 UStG, https://www.gesetze-im-internet.de/ustg_1980/__19.html (abgerufen 2026-10-02).

## 1. Impressum (§ 5 DDG)

Muss **leicht erkennbar, unmittelbar erreichbar, ständig verfügbar** sein. Erforderlich:

- [ ] **Name und Anschrift** des Diensteanbieters (bei Einzelunternehmen: Vor- und Nachname,
      ladungsfähige Anschrift — nicht nur Postfach). → offen M4.
- [ ] **Rechtsform** und **Vertretungsberechtigter** (bei juristischer Person). → hängt an M3.
- [ ] **Schnelle elektronische Kontaktaufnahme + unmittelbare Kommunikation**, d. h. **E-Mail-Adresse**
      (und Telefon, sofern vorhanden).
- [ ] **USt-IdNr. oder Wirtschafts-Identifikationsnummer**, falls vorhanden (§ 5 Abs. 1 Nr. 6 DDG).
      → bei Kleinunternehmerschaft § 19 UStG ggf. keine USt-IdNr. (M3, steuerlich klären).
- [ ] **Handelsregister/ähnliches Register + Registernummer**, falls eingetragen.
- [ ] **Zuständige Aufsichtsbehörde**, nur falls die Tätigkeit behördlicher Zulassung bedarf
      (bei reinem SaaS **nicht** einschlägig — anwaltlich bestätigen).
- [ ] **Berufsrechtliche Angaben** (Kammer, Berufsbezeichnung, Regelungen) nur bei reglementiertem
      Beruf — bei Briefato **nicht** einschlägig; anwaltlich bestätigen.
- [ ] Hinweis **Verbraucherstreitbeilegung / OS-Plattform**: **anwaltlich prüfen** — die
      EU-Online-Streitbeilegungsplattform wurde zum 20.07.2025 eingestellt; die frühere Pflicht nach
      § 36 VSBG zur Nennung ist entfallen. Keine veralteten Klauseln übernehmen.
- [ ] **Jugendschutz / § 18 MStV**-Angaben nur falls journalistisch-redaktionelles Angebot — hier
      nicht einschlägig.

## 2. Datenschutzerklärung (Art. 13/14 DSGVO + § 25 TDDDG)

- [ ] **Verantwortlicher** + Anschrift + Kontakt; **Datenschutzbeauftragter** (Name/Kontakt), falls
      benannt (M10).
- [ ] **Zwecke und Rechtsgrundlagen** je Verarbeitung: Vertrag (Art. 6 Abs. 1 lit. b),
      berechtigtes Interesse/Betrieb (lit. f), **Art. 9 Abs. 2 lit. h DSGVO i. V. m. § 22 BDSG**
      für Gesundheitsdaten, gesetzliche Pflichten (lit. c).
- [ ] **Wichtige Klarstellung:** Briefato ist **Auftragsverarbeiter**; Patient:innen sind
      Betroffene der **Praxis**. Hinweis, dass sich Patient:innen **an ihre Praxis** wenden.
- [ ] **Empfänger / Kategorien**: Modell-Provider, Stripe, Hoster, Backup-Ziel, E-Mail-Versand —
      benannte Sub-Prozessoren (siehe `02-avv-checklist.md §4`).
- [ ] **Drittlandübermittlung**: ob ja/nein, betroffenes Land, Schutzmaßnahmen (SCC/DPF).
- [ ] **Speicherdauer/Löschkriterien** (Verweis auf `04-retention-deletion.md`).
- [ ] **Betroffenenrechte** Art. 15–21 + **Beschwerderecht** bei der Aufsichtsbehörde.
- [ ] **Keine automatisierte Entscheidungsfindung im Einzelfall** (Art. 22) — klarstellen, da eine
      KI beteiligt ist, aber das **Mitglied** entscheidet.
- [ ] **Cookies / § 25 TDDDG:** Es werden **ausschließlich technisch notwendige Cookies** (Session
      `briefato_session`, CSRF `briefato_csrf`) gesetzt; § 25 Abs. 2 Nr. 2 TDDDG-Ausnahme greift →
      **kein Einwilligungsbanner erforderlich**. Diese Feststellung ist **anwaltlich zu bestätigen**
      und im Text zu dokumentieren. Kein Analytics/Marketing-Cookie ohne Consent.
- [ ] Hinweis auf **KI-Einsatz** (Transparenz) und dass Eingaben pseudonymisiert verarbeitet werden.

## 3. AGB (B2B-SaaS für Praxen)

- [ ] **Vertragsgegenstand**: Bereitstellung des Portals als SaaS (Nutzung, nicht Eigentum);
      Schreib-/Formatierhilfe, **kein Medizinprodukt** (Verweis `08-mdr-boundary.md`).
- [ ] **Rollen**: Kunde ist **Verantwortlicher** und sichert zu, eine **Rechtsgrundlage** für die
      Verarbeitung der Patientendaten zu haben; Briefato ist **Auftragsverarbeiter** (AVV als Anlage).
- [ ] **§ 203 StGB / Verschwiegenheit**: Klausel zur Rolle der „mitwirkenden Person“ und zur
      Geheimhaltungsverpflichtung (siehe `02-avv-checklist.md §3`).
- [ ] **Preise, Abrechnungsperiode, Quoten** (Pläne free/starter/praxis/klinik; siehe `config.py`
      `PLAN_CATALOG`: 0/19/39/89 €, Quoten 10/40/120/400). Klarstellen: Preise **inkl. USt** oder
      **Kleinunternehmer-Hinweis** (§ 19 UStG) → M3/M4.
- [ ] **Zahlung über Stripe** (Checkout/Portal), Laufzeit, Kündigung, `cancel_at_period_end`.
- [ ] **Verfügbarkeit/Wartung** — realistische SLA-Formulierung (Host hat aktuell Swap-Problem).
- [ ] **Mitwirkungspflichten** des Kunden (korrekte Daten, Zugangsdaten geheim halten, Export vor
      Kündigung).
- [ ] **Haftung**: keine medizinische Richtigkeit; Mitglied gibt jeden Brief frei; Haftungsbegrenzung
      (anwaltlich!).
- [ ] **Datenschutz**: Verweis auf Datenschutzerklärung + AVV.
- [ ] **Änderungen der AGB**, **anwendbares Recht**, **Gerichtsstand** (B2B).
- [ ] **Streitbeilegung** (B2B: kein Verbraucher-Widerruf; anwaltlich prüfen).

## 4. Widerrufsbelehrung (§§ 312g, 355, 356 BGB)

Prüfen, ob der Kunde **Verbraucher** ist (eine Praxis handelt meist **unternehmerisch**, aber der
Einzelarzt als Privatperson kann Verbraucher sein). Wenn Widerrufsrecht greift:

- [ ] **Muster-Widerrufsbelehrung** nach Anlage 1 zu Art. 246a EGBGB (anwaltlich).
- [ ] **Widerrufsfrist**: 14 Tage (§ 355 BGB); Beginn bei Dienstleistungen/Digitalinhalten (§ 356
      Abs. 2 Nr. 2/§ 356 Abs. 3 BGB).
- [ ] **Erlöschen bei vollständiger Erbringung** (§ 356 Abs. 5 BGB): Nur wenn der Verbraucher
      **vorher ausdrücklich zugestimmt** hat, dass vor Ablauf der Frist begonnen wird, **und** seine
      **Kenntnis vom Erlöschen** bei vollständiger Erfüllung bestätigt hat.
- [ ] Umsetzung im Checkout: **ausdrückliche Zustimmung + Kenntnisnahme-Checkbox** vor
      Leistungsbeginn; **keine Vorauswahl**.
- [ ] **§ 312j BGB**: Beschriftung des Bestellbuttons „**zahlungspflichtig bestellen**“ (kein
      bloßes „Weiter“).
- [ ] **§ 312f BGB**: Bestätigung des Vertrags auf **dauerhaftem Datenträger** (E-Mail/PDF).
- [ ] **Muster-Widerrufsformular** (Anlage 2 zu Art. 246a EGBGB) bereitstellen.
- [ ] **Fernabsatz-Pflichtinformationen** (Art. 246a EGBGB): alle Preis- und Vertragsangaben vor
      Vertragsschluss (inkl. Kosten, Laufzeit, Kündigung).

## 5. Preisangaben (PAngV)

- [ ] **Gesamtpreise inkl. USt.** und aller Bestandteile (§ 6 Abs. 1 Nr. 1 PAngV) — **oder** bei
      Kleinunternehmerschaft (§ 19 UStG) **klarer Hinweis**, dass keine USt. ausgewiesen wird
      (Formulierung anwaltlich/steuerlich klären, M3/M4).
- [ ] **Monatlich wiederkehrende Preise** deutlich als **pro Monat** kennzeichnen.
- [ ] Keine versteckten Zusatzkosten; Zusatzkosten benennen (§ 6 Abs. 1 Nr. 2/2 PAngV).

## 6. Was Mohamed liefern muss (anwaltliche/steuerliche Freigabe)

- M3 Unternehmensstatus / USt.
- M4 Impressumsangaben + wer zeichnet.
- M5 Beauftragung der Kanzlei für Impressum, Datenschutz, AGB, Widerruf.
- M10 ggf. DSB-Angabe.
- Realistische SLA-/Verfügbarkeitsaussage (kein Overclaim).
