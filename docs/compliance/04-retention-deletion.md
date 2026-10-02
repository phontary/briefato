# 04 — Aufbewahrung und Löschung

Status: **Entwurf — muss bestätigt werden.** Grundlagen: Art. 5 Abs. 1 lit. e, Art. 17 DSGVO,
https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); § 630f Abs. 3 BGB,
https://www.gesetze-im-internet.de/bgb/__630f.html (abgerufen 2026-10-02).

## 1. Grundregel (Rollen)

Aufbewahrungsfristen für **Behandlungsdokumentation** treffen den **Verantwortlichen (die Praxis)**.
§ 630f Abs. 3 BGB: Der Behandelnde bewahrt die Behandlungsakte **10 Jahre nach Abschluss der
Behandlung** auf. Briefato ist Verarbeiter und speichert **so lange, wie die Praxis es weisungsgemäß
vorgibt**. Der Briefato-**Default** ist ein Konfigurationswert; er darf die Praxis nicht zu einer
kürzeren als ihrer eigenen Frist zwingen.

> Merksatz: Nicht Briefato „behält 10 Jahre“ — die **Praxis** muss 10 Jahre; Briefato richtet die
> technische Frist danach aus und protokolliert die Löschung.

## 2. Aufbewahrungsmatrix

| Kategorie | Tabelle / Ort | Aufbewahrung (Default-Vorschlag) | Rechtsgrund | Löschauslöser |
|---|---|---|---|---|
| Patienten-Stammdaten | `patients` | solange Kontobeziehung besteht; nach Kündigung Löschung gem. Weisung (Default 30 Tage Karenz) | Weisung der Praxis | Kontolöschung oder Einzelanweisung |
| Behandlungsakte-ähnliche Inhalte (Briefe) | `letters` (`content_enc`, `dictation_enc`) | **konfigurierbar, Default 10 Jahre gedeckelt** (an § 630f BGB angelehnt) | § 630f Abs. 3 BGB (Praxis) | Praxis-Weisung / Fristablauf |
| Diktat-Rohtext | `letters.dictation_enc` | **kürzer als der Brief möglich** (Default: mit dem Brief) | Datenminimierung Art. 5(1)(c) | nach Freigabe/Weisung |
| Generierungs-Metadaten | `generations` | 12 Monate (Kosten/Nachweis), danach Anonymisierung oder Löschung | Art. 6(1)(f) | Fristablauf |
| Konto-/Abrechnungsdaten | `users`, `subscriptions` | Vertragsdauer + steuerrechtliche Fristen (AO/HGB: **6 bzw. 10 Jahre** für Rechnungsdaten) | Art. 6(1)(b)/(c), § 147 AO | gesetzliche Frist |
| Sessions | `auth_sessions` | bis Ablauf (`session_ttl_hours` = 336 h) bzw. `revoked_at` + kurze Karenz | Sicherheit | Ablauf/Logout |
| Audit-Log | `audit_events` | 12 Monate (Vorschlag); IP ggf. früher kürzen | Art. 5(1)(c), § 22(2) BDSG | Fristablauf |
| Container-Logs | Docker json-file | 3 × 10 MB Rolling (Logrotate im Treiber) | Sicherheit | Rotation |
| Off-host-Backups | Backup-Ziel | **Rotationsfenster 30 Tage** (Vorschlag) | Verfügbarkeit Art. 32(1)(c) | Backup-Rotation |
| Stripe-Daten | Stripe-System | außerhalb Briefato; Stripe-eigene Fristen | Stripe als Verantwortlicher | — |

**Wichtig für Löschzusagen:** Backups sind **kein** separater Aufbewahrungstatbestand mit
„Unverletzlichkeit“. Ein gelöschter Datensatz ist im **Rotationsfenster (30 Tage)** ggf. noch im
Backup; danach endgültig weg. Diese Fenstergröße muss im AVV/Löschprotokoll genannt werden.

## 3. Backup-Fenster (verbindlich zu dokumentieren)

| Parameter | Wert (Vorschlag) | Status |
|---|---|---|
| Backup-Frequenz | täglich (cron/systemd, S1/S5) | geplant |
| Verschlüsselung | Fernet/age mit pass-verwaltetem Key, off-host Kopie | geplant (D7) |
| Rotation / Aufbewahrung | 30 Tage (konfigurierbar) | **muss bestätigt werden** |
| Restore-Test | mindestens 1× vor Beta, dann quartalsweise, protokolliert | **fehlt (M12)** |

## 4. Lösch-Workflow (Mitglied weist an)

1. **Anweisung** geht ein: über `GET /app/konto` (delete-account) oder schriftlich/E-Mail.
2. **Identitätsprüfung**: eingeloggte Session; bei E-Mail zusätzlich Bestätigung.
3. **Vorprüfung**: Hinweis an die Praxis, ob gesetzliche Aufbewahrung (§ 630f BGB/OAO) der Löschung
   entgegensteht. Briefato **rät nicht rechtlich** — die Entscheidung trifft die Praxis.
4. **Ausführung**: kaskadierender Delete über `ON DELETE CASCADE` (`patients`, `letters`,
   `generations`, `subscriptions`, `auth_sessions`) — Schema: `models.py` FK-Ketten.
5. **Export vorher** (optional, Art. 20): JSON + DOCX, siehe `05`.
6. **Verifikation**: Query-Nachweis „0 rows“ für die betroffenen `user_id`s; `audit_events`-Eintrag
   `data.deleted` mit Anzahl.
7. **Backup-Realität**: Datensatz bleibt bis zu **30 Tage** im Backup; das wird der Praxis
   mitgeteilt (kein „sofort überall weg“).
8. **Löschprotokoll** an die Praxis (Datum, Umfang, Ausnahmen mit Grund).

## 5. Konto-Löschung (Selbstbedienung des Mitglieds)

| Schritt | Inhalt | Status |
|---|---|---|
| 1 | Kündigung/„Konto löschen“ in `/app/konto` | geplant |
| 2 | Warnung + exportierbarer Datenexport (JSON/DOCX) | geplant |
| 3 | Aktive Stripe-Subscription kündigen (`cancel_at_period_end`) | geplant (Billing-Stub) |
| 4 | Grace-Period (Default 30 Tage) vor endgültiger Löschung | **muss bestätigt werden** |
| 5 | Kaskadierende Löschung + Audit-Event | geplant |
| 6 | Bestätigung per E-Mail an das Mitglied | geplant |

## 6. Einzelanweisungen (selektive Löschung)

- Einzelpatient löschen: `POST /app/patienten/{id}/archivieren` = **Archivierung**, nicht Löschung.
  Echte Löschung ist ein separater Prozess — **offen**, in der UI zu benennen.
- Einzelbrief löschen: `POST /app/briefe/{id}/loeschen` (vorgesehen).
- „Archiviert“ darf **nicht** mit „gelöscht“ gleichgesetzt werden (Art. 17 vs. Aufbewahrung).

## 7. Offene Punkte

- **offen:** Default-Aufbewahrungswert im Code (`04` ist Dokumentation; die echte Steuerung fehlt).
- **offen:** Anonymisierung nach Fristablauf statt harter Löschung (Statistik/Kosten) — datenschutz-
  freundlich zu prüfen.
- **muss bestätigt werden:** Backup-Rotationsfenster (30 Tage) und Grace-Period (30 Tage).
- **offen:** Prozess, wenn die Praxis eine **kürzere** Frist als 10 Jahre weist (zulässig, aber
  berufsrechtlich/steuerlich von der Praxis zu verantworten).
- **muss bestätigt werden:** steuerliche Aufbewahrungsfristen für Abrechnungsdaten (M3, Steuerberatung).
