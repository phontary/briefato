# 05 — Unterstützung der Betroffenenrechte (Art. 15/16/17/20 DSGVO)

Status: **Entwurf — muss bestätigt werden.** Grundlage: Art. 12–20 DSGVO,
https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02) (gegengeprüft:
https://gdpr-info.eu/art-15-gdpr/ , abgerufen 2026-10-02); Art. 28 Abs. 3 lit. e DSGVO
(Verarbeiter unterstützt Betroffenenrechte).

## 1. Der zentrale Satz: Betroffene wenden sich an die Praxis

Briefato ist **Verarbeiter**. Auskunft, Berichtigung, Löschung und Übertragbarkeit richten Betroffene
**an die verantwortliche Praxis**. Die Praxis ist Adressat und Entscheider; Briefato **bedient die
Anfrage technisch im Auftrag** und leitet nicht selbst an Patienten. Deshalb:

- Auf der Datenschutzerklärung/Kontaktseite steht der **Hinweis**, dass sich Patient:innen an ihre
  Praxis wenden müssen, nicht an Briefato.
- Anfragen, die trotzdem bei Briefato eingehen, werden **an die zugehörige Praxis** weitergeleitet
  (kein Briefato-eigener Bescheid).
- Die gesetzliche Frist (Art. 12 Abs. 3: **1 Monat**, verlängerbar) liegt bei der Praxis.

## 2. Wie Briefato die Praxis unterstützt

| Recht | Was die Praxis von Briefato bekommt | Umsetzung / Ort | Status |
|---|---|---|---|
| **Art. 15 Auskunft** | vollständige Kopie aller zur betroffenen Person gespeicherten Daten + Verarbeitungsinfos | Datenexport (JSON) je Patient aus `patients` + zugehörige `letters`/`generations` | geplant |
| **Art. 16 Berichtigung** | Änderung von `patients`-Feldern und Brieftexten; Änderungshistorie | `GET|POST /app/patienten/{id}/bearbeiten`, `POST /app/briefe/{id}/speichern`; `updated_at` aus `TimestampMixin` | geplant |
| **Art. 17 Löschung** | Löschung der betroffenen Datensätze; Nachweis + Backup-Hinweis | siehe `04-retention-deletion.md §4` | geplant |
| **Art. 18 Einschränkung** | Verarbeitung aussetzen, ohne zu löschen | **fehlt** — es gibt kein „Sperrflag“ am Patient/Datensatz | **offen** |
| **Art. 20 Übertragbarkeit** | strukturierter, maschinenlesbarer Export (JSON) + Dokument (DOCX) | JSON-Export (folgt unten), DOCX aus `pipeline/letterhead.py` | geplant |
| **Art. 19 Mitteilung** | Liste der Empfänger, an die übermittelt wurde | aus `generations`/`audit_events` rekonstruierbar | teilweise |

## 3. Exportformat (Vorschlag, maschinenlesbar)

```json
{
  "format": "briefato.patient.export/1",
  "exported_at": "2026-10-02T00:00:00Z",
  "practice": { "name": "...", "controller": "..." },
  "patient": {
    "external_ref": "...",
    "first_name": "<entschlüsselt>",
    "last_name": "<entschlüsselt>",
    "birth_date": "YYYY-MM-DD",
    "insurance_number": "...",
    "notes": "<entschlüsselt aus notes_enc>"
  },
  "letters": [
    { "kind": "arztbrief", "status": "approved", "approved_at": "...",
      "title": "...", "content": "<entschlüsselt aus content_enc>",
      "model": "...", "generated_at": "..." }
  ]
}
```

Regeln:
- `_enc`-Felder werden beim Export **serverseitig entschlüsselt** (`security.decrypt_field`) — nie
  Fernet-Token roh ausgeben (`docs/02-spec-interfaces.md §3`).
- Zusätzlich je Brief ein **DOCX** (`render_docx(...)`), damit Art. 20 „gängiges Format“ erfüllt ist.
- Export wird über die eingeloggte Session + CSRF (`security.check_csrf`) abgesichert; Download
  läuft über den authentifizierten Nutzer, nicht über eine erratbare URL.

## 4. Löschung vs. Aufbewahrung — Konflikt richtig auflösen

- Ein Betroffener verlangt Löschung, die Praxis hat aber eine 10-jährige Aufbewahrungspflicht
  (§ 630f BGB). Der Konflikt wird **von der Praxis** entschieden (Aufbewahrung kann der Löschung
  entgegenstehen, Art. 17 Abs. 3 lit. b).
- Briefato setzt nur um, was die Praxis weist, und **dokumentiert** die Weisung.

## 5. Antwort-Templates für die Praxis (Entwurf)

Für die Praxis bereitstellen (nicht final — Anwalt prüfen lassen):
- [ ] Auskunftsantwort (Art. 15) mit Datenexport-Anhang.
- [ ] Löschbestätigung mit Backup-Fenster-Hinweis.
- [ ] Berichtigungsbestätigung mit Änderungsnachweis.
- [ ] Zwischennachricht bei Fristverlängerung (Art. 12 Abs. 3).

## 6. Offene Punkte

- **offen:** Art. 18 (Einschränkung der Verarbeitung) — Sperrmechanismus fehlt im Datenmodell.
- **offen:** Export-/Löschfunktionen sind im Portal-Code noch nicht implementiert (`/app/konto`
  nur als Route spezifiziert).
- **offen:** Fristenmonitor für Anfragen (1-Monats-Frist).
- **muss bestätigt werden:** Formulierung des „wenden Sie sich an Ihre Praxis“-Hinweises in der
  Datenschutzerklärung (`07`).
