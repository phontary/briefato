# Scrub-Report – Prüfung auf echte Patientendaten

Geprüft: alle 152 Musterbriefe in `/workspace/schreibdienst/musterbriefe`.
Methodik: Regex-Scan auf Geburtsdaten, Klarnamen nach „Herr/Frau“, Fall-/Aufnahme-/
Versicherungsnummern, Postleitzahlen/Anschriften, Telefonnummern und konkrete Daten
im Fließtext; zusätzlich manuelle Sichtung der Treffer und Abgleich der Namen mit
`visitenliste-2026-09-22.md`.

**Ergebnis: 3 Dateien mit Auffälligkeiten, davon 1 mit echtem Klarnamen.**

## Manuell bestätigte Treffer

| Datei | Art des Identifikators | Empfehlung / Aktion |
|---|---|---|
| `Cholezystolithiasis.md` | personenbezogene Fallkennung / Klarname | Enthält im Abschnitt `## Nachsorge` eine Fallkennung der Form „(Nutzerfassung TT.MM.JJJJ, Fall <Nachname>)“ mit einem **realen Patienten-Nachnamen** (hier maskiert als `K***au`). Derselbe Nachname erscheint in `/workspace/schreibdienst/visitenliste-2026-09-22.md` mit Vorname, Alter und Fallcode. Empfehlung: **vor Ingest entfernen** — Fallkennung + Datum löschen, nur den generischen Empfehlungs-Wortlaut behalten. **Der Klarname ist in diesem Report absichtlich nicht ausgeschrieben.** |
| `Struma_nodosa_Hyperthyreose.md` | Fallnarrativ aus echtem Fall (bereits mit Platzhaltern) | Der Text ist ein echter Entlassbrief, jedoch mit Platzhaltern `[Name]`, `[Datum]`, `[Wert]`, `[Zeitraum]`, `[Uhrzeit]` bereinigt. Kein Klarname mehr sichtbar. Empfehlung: **nach Ingest zulässig**, aber als „de-identifiziertes Fallbeispiel“ kennzeichnen und prüfen, dass keine residualen Identifier (genaue Daten, ITS-Zeitfenster) verbleiben. |
| `Acne-inversa.md` | konkretes OP-Datum | Enthält „Z.n. Exzision in toto am re. Schambein (TT.MM.2026)“ — ein konkretes Eingriffsdatum (hier maskiert). Kein Name, aber datierbar. Empfehlung: **Datum entfernen/generisch** machen („Z.n. Exzision in toto …“). |

## Automatischer Scan – weitere Treffer (geprüft, unkritisch)

- `Baker_Zyste.md` — Telefonnummer (im Text generisch/Platzhalter, kein personenbezogener Klarname)
- `Coxarthrose_Exsikkose_Sturz.md` — konkretes Datum im Fließtext (im Text generisch/Platzhalter, kein personenbezogener Klarname)
- `Distorsion_Daumen_Grundgelenk.md` — Telefonnummer (im Text generisch/Platzhalter, kein personenbezogener Klarname)
- `Dorsale_Spondylodese_LWS.md` — Telefonnummer (im Text generisch/Platzhalter, kein personenbezogener Klarname)
- `Kontusion_Grosszehe.md` — Telefonnummer (im Text generisch/Platzhalter, kein personenbezogener Klarname)

## Bekannte False Positives (erklärt)

- `Nadelstichverletzung.md` — „(Fall-Nr.)“ ist ein Dokumentations-Platzhalter, keine Nummer.
- `Lumboischialgie_…md`, `AC-Gelenk-…md`, `Patellafraktur.md` — „Tel.: 1777“ / „telefonische Terminvereinbarung“ sind generische Institutionsangaben ohne Person.
- `Coxarthrose_Exsikkose_Sturz.md` — Datum `08.07.2019` ist ein AWMF-Leitlinien-Stand, kein Patientendatum.
- `Diabetes_mellitus_Typ1.md` — „1986 (seit 40 Jahren)“ ist ein generisches Erkrankungsalter, kein Geburtsdatum.

## Regel für die Pipeline

**Kein Musterbrief mit einem Treffer der Kategorie „Manuell bestätigte Treffer“
darf ingestiert werden, bevor er anonymisiert wurde.** Die drei Dateien oben sind
bis dahin auf `licence_risk`-unabhängig als `scrub_pending` zu behandeln.
