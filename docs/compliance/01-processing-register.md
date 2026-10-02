# 01 — Verzeichnis von Verarbeitungstätigkeiten (Art. 30 DSGVO)

Status: **Entwurf — muss bestätigt werden.** Owner lt. M7 zu benennen (siehe `README.md`).
Grundlage: Art. 30 DSGVO, https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02);
DSK Kurzpapier Nr. 1 „Verzeichnis von Verarbeitungstätigkeiten“, https://www.datenschutzkonferenz-online.de/media/kp/dsk_kpnr_1.pdf (abgerufen 2026-10-02).

## 0. Rollen und warum zwei Register nötig sind

Briefato ist **Auftragsverarbeiter**. Nach Art. 30 Abs. 2 DSGVO führt der Verarbeiter ein *eigenes*
Verzeichnis **aller Kategorien von im Auftrag durchgeführten Verarbeitungstätigkeiten**. Die
verantwortliche Praxis führt ihrerseits ein Verzeichnis nach Art. 30 Abs. 1 und nimmt Briefato dort
als Empfänger/Verarbeiter auf. Beide Register sind zu führen.

> Hinweis Unternehmen < 250 Personen: Die Ausnahme des Art. 30 Abs. 5 DSGVO greift **nicht** —
> die Verarbeitung ist nicht nur gelegentlich, birgt Risiken und betrifft besondere Kategorien
> (Art. 9). Ein Verzeichnis ist also zwingend.

## 1. Teil A — Briefato als Auftragsverarbeiter (Art. 30 Abs. 2 DSGVO)

| Feld | Inhalt |
|---|---|
| Verantwortlicher je Auftrag | die jeweilige Arztpraxis / das Mitgliedskonto |
| Auftragsverarbeiter | Mohamed Sabry (Briefato), Anschrift muss bestätigt werden (M4) |
| Vertreter / DSB | zu benennen — offen (M10) |
| Kategorien der Verarbeitungen | (V1) Patientenverwaltung, (V2) Diktat-/Briefgenerierung, (V3) Dokumentenablage & Suche, (V4) Konto-/Abrechnungsverwaltung, (V5) Betriebs-/Sicherheitsprotokollierung (Audit), (V6) Systembetrieb & Backup, (V7) Referenzbibliothek Musterbriefe (Produkt-Brain) |
| Datenarten (real, aus `models.py`) | siehe Tabelle 1.2 |
| Betroffene Personen | Patienten der Praxis, Mitglieder/Praxispersonal (Nutzerkonten) |
| Empfänger / Drittland | siehe Tabelle 1.3 |
| Löschfristen | siehe `04-retention-deletion.md` |
| TOM | siehe `03-tom.md` |

### 1.2 Datenarten je Verarbeitung (gemappt auf echte Tabellen/Spalten)

Architektur: `app/briefato/models.py`, `docs/02-spec-interfaces.md §3`. „_enc“ = Fernet-verschlüsselt
(`security.encrypt_field`).

| ID | Verarbeitung | Tabelle / Spalten | Personenbezug | Kategorie | Zweck |
|---|---|---|---|---|---|
| V1 | Patientenverwaltung | `patients`: `first_name`, `last_name`, `birth_date`, `sex`, `insurance`, `insurance_number`, `street`, `zip`, `city`, `phone`, `email`, `referring_doctor`, `external_ref`, `notes_enc` | ja | **Art. 9** (Gesundheit), Identifikationsdaten | Stammdaten & Zuordnung zum Brief |
| V2 | Diktat & Generierung | `letters`: `dictation_enc`, `content_enc`, `title`, `kind`, `model`, `tokens_in/out`, `cost_usd`; `generations`: `provider`, `model`, `tokens_*`, `latency_ms`, `pseudonymised`, `error` | ja | **Art. 9** (freier klinischer Text) | Erzeugen des Dokuments; **Ausgabe = reiner Text** (Copy-Paste ins KIS), DOCX optional; Kostenmetrik |
| V3 | Ablage & Suche | `letters` (Inhalt), Volltextsuche über `/app/suche` | ja | **Art. 9** | Verlauf, Wiederfinden |
| V4 | Konto & Abrechnung | `users`: `email`, `password_hash`, `full_name`, `practice_name`, `street/zip/city`, `phone`, `tax_id`, `letterhead_json`, `ui_lang`; `subscriptions`: `stripe_customer_id`, `stripe_subscription_id`, `plan_code`, `status`, `letters_quota/used`, `current_period_*` | ja | Art. 6, teils USt/AO | Vertrag, Login, Quota, Abrechnung |
| V5 | Audit | `audit_events`: `event`, `target_type/id`, `ip`, `user_agent`, `meta_json`; `auth_sessions`: `token_hash`, `ip`, `user_agent`, `expires_at`, `revoked_at` | ja | Art. 6 (Sicherheit) | Sicherheit, Nachvollziehbarkeit (§ 22 Abs. 2 Nr. 2 BDSG) |
| V6 | Betrieb & Backup | DB-Snapshot, verschlüsseltes Backup off-host (geplant), Container-Logs (json-file, 3×10 MB) | ja (Backup) / nein (Healthcheck) | Art. 9 (Backup) | Verfügbarkeit/Wiederherstellung |
| V7 | **Referenzbibliothek Musterbriefe** (Produkt-Brain) | `brain/musterbriefe/manifest.json` + `index.md` (Metadaten, **kein** Volltext); Volltext im Quellarchiv `/workspace/schreibdienst/musterbriefe/` | **nein** nach Anonymisierung; **ja** für 3 Templates mit Patientenspuren + das Quellarchiv selbst | überwiegend keine personenbezogenen Daten; Art. 9 nur für die 3 belasteten Templates | Struktur-/Formatreferenz für die Briefgenerierung; siehe `10`, `11` |

### 1.3 Empfänger / Übermittlungen

| Empfänger | Rolle | Was | Ort / Drittland | Rechtsinstitut | Status |
|---|---|---|---|---|---|
| Modell-Provider (Ziel: Mistral EU / Azure EU) | Unterauftragsverarbeiter | pseudonymisierter Diktat-/Prompttext, Modelloutput | EU (bei Mistral FR / Azure EU) | AVV (Art. 28) + ggf. Art. 28 Abs. 7 | **offen — M1** |
| DeepSeek (falls gewählt) | Unterauftragsverarbeiter | pseudonymisierter Text | **China = Drittland** | AVV + SCC (Art. 46 Abs. 2 lit. c) + Transfer Impact Assessment; faktisch schwer tragfähig | nicht empfohlen |
| Stripe | eigener Verantwortlicher für Zahlungsdaten / sonst Verarbeiter | E-Mail, Kundennr., Zahlungsvorgang | Stripe Payments Europe (IE) bzw. USA | Vertrag + ggf. DPF/SCC | **offen — M2** |
| Hoster (N305/Betreiber `phontary`, später EU-VPS) | Unterauftragsverarbeiter (Hosting) | alle Portal-Daten physisch | DE | AVV | **offen — M9/M11** |
| Backup-Ziel (off-host) | Unterauftragsverarbeiter | verschlüsselte DB-Kopien | DE/EU (zu bestätigen) | AVV | **offen — M11** |
| E-Mail-Versand (Registrierung/Reset) | Unterauftragsverarbeiter | E-Mail-Adresse, Token | zu wählen | AVV | **offen** |
| Caddy/CrowdSec (Betrieb) | Betriebsmittel, kein Auftragsverarbeiter für Inhalte | Laufzeit-Logs, IPs | DE (Host) | — | — |

**Wichtig:** Die Pseudonymisierung vor dem Model-Provider (D4) reduziert, beseitigt aber nicht den
Personenbezug — Pseudonyme bleiben personenbezogene Daten (Erwägungsgrund 26; Art. 4 Nr. 5 DSGVO).
Der Provider bleibt daher Empfänger von Art. 9-Daten-Kontext und braucht einen AVV.

### 1.4 Ausgabeformat des Produkts (Plain Text)

Die primäre Produktausgabe ist **reiner Text** (kein Markdown, keine Formatierung, kein PDF) —
das Mitglied kopiert ihn in sein KIS. Ein **DOCX mit Briefkopf ist eine optionale Sekundärausgabe**
(`GET /app/briefe/{id}/export.docx`). Für die MDR-/KI-VO-Abgrenzung ist das relevant: die Klartext-
Ausgabe ist eine **Schreibhilfe**, der Empfänger einer Kundenbrief-Ausgabe bleibt die verantwortliche
Praxis (siehe `08`). Konsequenz im Register: Die Ausgabeform ist Teil von V2; es entsteht **kein**
neuer Verarbeitungsgegenstand durch den optionalen DOCX-Export.

## 2. Teil B — Verantwortlicher-Sicht (Vorlage für die Praxis, Art. 30 Abs. 1)

Diese Vorlage liegt dem Kundenpaket bei; die Praxis bleibt für ihre Eintragungen verantwortlich.

| Feld | Vorlage / Empfehlung für die Praxis |
|---|---|
| Verantwortlicher | Praxisname, Inhaber, Anschrift |
| Zweck | Schreiben von Arztbriefen/Attesten/Befunden mit technischer Schreibhilfe |
| Rechtsgrundlage | Art. 9 Abs. 2 lit. h DSGVO i. V. m. § 22 Abs. 1 Nr. 1 lit. b BDSG (Gesundheitsvorsorge/Behandlung), https://www.gesetze-im-internet.de/bdsg_2018/__22.html (abgerufen 2026-10-02) |
| Betroffene | eigene Patienten |
| Empfänger | Briefato als Auftragsverarbeiter + Sub-Prozessoren (Liste in `02-avv-checklist.md`) |
| Fristen | § 630f Abs. 3 BGB — 10 Jahre (§ 630f BGB, https://www.gesetze-im-internet.de/bgb/__630f.html (abgerufen 2026-10-02)) |
| TOM | Verweis auf `03-tom.md` und den AVV |

## 3. Abweichungen / offene Punkte

- **offen:** Anschrift/Rechtsform des Verantwortlichen Briefato (M3/M4).
- **offen:** DSB-Benennung (M10). Ein DSB ist nicht automatisch Pflicht, aber wahrscheinlich, da
  die Kerntätigkeit in umfangreicher Verarbeitung besonderer Daten besteht (Art. 37 Abs. 1 lit. c
  DSGVO i. V. m. § 38 BDSG).
- **offen:** Rechtsgrundlage für Briefatos **eigene** Verarbeitungen (Rechnung/Konto) — eigene
  Verantwortlichkeit, nicht nur Auftragsverarbeitung; Rechtsgrundlage Art. 6 Abs. 1 lit. b/c.
- **offen:** ob `ip`/`user_agent` in `audit_events`/`auth_sessions` über die Aufbewahrungsfrist
  hinaus gekürzt werden (Datensparsamkeit, Art. 5 Abs. 1 lit. c).
- **muss bestätigt werden:** ob Kleinunternehmer Konto-/Rechnungsdaten mit eigenen Fristen (AO/HGB: 6/10 Jahre) führt (M3).
- **offen:** Rechtsgrundlage des privaten Quellarchivs `/workspace/schreibdienst/musterbriefe/` (nicht durch den Kunden-AVV gedeckt; siehe `10` § 3.3).
- **offen (V7):** Anonymisierungs-Gate und Inhaltslizenz-Prüfprozess für die Bibliothek fehlen (`10`, `11`; M13/M14).
