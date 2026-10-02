---
asset: briefato-brain/dokumenttypen/entlassmedikationsplan
brain_version: 1.0.0
typ: entlassmedikationsplan (MoP)
aliases: [entlassmedikation, medikationsplan, mop, verabreichungsplan, mediks plan]
language: de (meta: en)
---

# Playbook: Entlassmedikationsplan anpassen

## Trigger
- Der Nutzer reicht einen Medikationsplan ein (KIS-Export, ausgedruckter Plan, kopierter Text) und will ihn
  „für diesen Fall anpassen" bzw. „exportieren".
- Stichwörter: Entlassmedikation, Medikationsplan, MoP, Verabreichungsplan, „mediks plan".

## Erforderliche Abschnitte IN DIESER REIHENFOLGE (Ausgabereihenfolge)
1. **Geänderte Zeilen mit alt → neu.**
   - Beispiel: „Insulin glargin (Lantus): zur Nacht 10 IE → 18 IE um 21:00 Uhr (Prüfhinweis: KIS-Plan nicht
     nachgezogen, letzte diabetologische Anpassung)."
2. **Bedingungs-/Verabreichungspläne** (eigene Zeile „siehe Verabreichungsplan mit Bedingungen" + Bereichsliste).
   - Beispiel: „Insulin glulisin: siehe Verabreichungsplan mit Bedingungen — 161–200 mg/dl: 2 IE; > 401
     Arztinfo: 8 IE."
3. **Zu ergänzende Spalte „Grund"** (nur dokumentierte Diagnosen des Aufenthalts).
   - Beispiel: „Grund ergänzt: DM Typ 2 (Insuline), Hypokaliämie (Kaliumpräparat), Demenz mit
     Aggressivitätsneigung (Risperidon)."
4. **Unverändert zu übernehmende Zeilen.**
   - Beispiel: „Unverändert: ASS 100 mg (0-1-0-0), Eisen(II) 50 mg (2-2-2-0), Simvastatin 20 mg (0-0-1-0)."
5. **Was NICHT Teil der Entlassmedikation ist** (Hinweiszeile).
   - Beispiel: „Nicht Teil der Entlassmedikation: die i.v. Antibiose des Aufenthalts (abgeschlossen)."

## Pflichtinhalte
- Spalten des bundeseinheitlichen Medikationsplans berücksichtigen: Wirkstoff | Handelsname | Stärke | Form |
  morgens | mittags | abends | zur Nacht | Einheit | Hinweise | Grund.
- Patientenkopf übernehmen (Name, Vorname, Geburtsdatum, Geschlecht, Gewicht, Größe, Einrichtung, Station,
  Ausdruckdatum).
- Pausierte Medikamente sichtbar als „pausiert – nicht verordnet" führen (nicht löschen, nicht in die
  Entlassmedikation übernehmen).
- Bei Dosisabweichung zwischen KIS-Plan und Verlaufsdokumentation: NIE stillschweigend wählen — inline
  rückfragen; ohne Antwort den dokumentierten Verlaufswert übernehmen und die Abweichung als Prüfhinweis
  sichtbar in die Zeile schreiben.
- Spalte „Grund" nur mit dokumentierten Diagnosen füllen; ohne Doku leer lassen.
- Bedarfsmedikation samt Maximum vollständig übernehmen (das Maximum ist verordnungskritisch).

## Verbotene Inhalte
- **KEIN PDF, KEIN HTML/Markdown-Export, keine Datei** — auch nicht „nur zur Ansicht".
- Keine stillschweigende Korrektur einer Dosisabweichung.
- Keine erfundenen Diagnosen in der Spalte „Grund".
- Kein log.md-Eintrag; Musterbriefe bleiben patientenunabhängig (keine Patientendaten dort führen).

## Ausgabeformat
- Ausschließlich Text im Chat: knapp, zeilenweise, copy-paste-fähig.
- Reihenfolge wie oben (geänderte Zeilen → Verabreichungspläne → „Grund" → unveränderte Zeilen → Nicht-Teil).
- Rückfragen inline im Chat, nicht als Popup.

## Pitfalls
- **„Anfangsdatum 07:00 des Folgetags"** bei Brause-/Vitaminpräparaten ist normal (nächste Morgendosis nach
  der Entlassung), kein Fehler.
- **KIS-Plan kann veraltet sein** (Verordnung nicht nachgezogen) → Prüfhinweis statt stiller Korrektur.
- **Diktat-Geburtsdaten oft falsch gehört:** ein Dokument mit Name + Geburtsdatum schlägt das Diktat.
- **Zuordnung eines zuvor anonymen Falls** über Station + Ausdruckdatum + Verordnungsprofil prüfen, nicht nur
  über den Nachnamen.
- **Mehrzeilige KIS-Kopie:** Handelsname/Stärke/Form pro Zeile rekonstruieren, Einheiten einzeln prüfen.

## Provenienz
- `skills/medizin/entlassmedikationsplan/SKILL.md` (Ausgabeformat, Ablauf, Fallstricke, Parsing).
- `memories/MEMORY.md` („Nutzer will KEINE PDF-/Datei-Exporte — nur die zu ändernden Zeilen als Text").
