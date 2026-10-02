---
asset: briefato-brain/dokumenttypen/entlassbrief-triage
brain_version: 1.0.0
typ: entlassbrief-triage (Routing-Playbook)
aliases: [entlassbrief, entlassungsbrief, arztbrief]
language: de (meta: en)
---

# Playbook: Entlassbrief-Triage (Routing)

Dieses Playbook entscheidet **vor** dem Schreiben, welche Briefart gilt. Inhaltliche Struktur steht in
`arztbrief.md` (stationär) bzw. `ambulant.md` (tageschirurgisch).

## Trigger
- Der Nutzer gibt „Entlassbrief", „Entlassungsbrief" oder „Arztbrief" ein, ohne die Briefart zu klären.

## Entscheidungsregel (in dieser Reihenfolge)
1. **Stationär** (Patient übernachtet, mehrtägiger Verlauf) → `arztbrief` (schreibdienst).
2. **Ambulant / tageschirurgisch** (Sprechstundenvorstellung → OP → Entlassung am OP-Tag) → `ambulant`.
3. **Entscheidungshilfe:** Lag die Patientin mindestens eine Nacht im Krankenhaus? Ja → stationär; Nein →
   ambulant. Die Übernachtung ist nur ein Anhalt, kein Automatismus.
4. **Nutzerwortlaut schlägt Anhalt:** Sagt der Nutzer explizit „stationäre Entlassung"/„Entlassbrief", bleibt
   es ein stationärer Entlassbrief (inkl. Therapie-Maßnahmen-Liste) — nicht allein wegen Entlassung am OP-Tag
   auf ambulant umtriagieren (Präzedenz: TAPP re., Entlassung am OP-Tag).
5. **Unterart des stationären Briefs am Materialende** (siehe `arztbrief.md`):
   - Entlassreife am Ende → **Entlassbrief**.
   - Verlauf läuft weiter → **Aufnahmebrief**.
   - Verlegung/Übernahme → **Verlegungsbrief**.

## Beispielzeilen für die Unterscheidung
- Stationär (Entlassbrief): „Wir nahmen den Patienten zur weiteren Diagnostik stationär auf … nach klinischer
  Besserung entließen wir den Patienten am 15.09.2026 in die häusliche Pflege."
- Stationär (Aufnahmebrief-Ende): „Für den Folgetag ist die geplante operative Versorgung vorgesehen."
- Ambulant: „Noch am OP-Tag wurde der Patient nach Entscheidung des Operateurs in die häusliche Pflege
  entlassen."
- Verlegung: „Da eine operative Versorgung in unserem Hause nicht möglich war, verlegten wir den Patienten
  in die Klinik für Allgemein- und Viszeralchirurgie des XXX. Wir bitten um Übernahme."

## Pflichtinhalte
- Bei stationärem Entlassbrief: Empfehlungsblock + „Diagnosen:" + „Nebenerkrankungen:" + „Therapie-Maßnahmen
  auf der Station:".
- Bei ambulantem Brief: Diagnoseliste, keine stationäre Aufnahmebegründung, keine Therapie-Maßnahmen-Liste.
- Bei Verlegungsbrief: Verlegungssatz statt Entlasssatz; KEIN Empfehlungsblock (Patient geht nicht nach Hause).

## Verbotene Inhalte
- Kein Umbau der Briefart nur wegen fehlendem Entlassdatum (dann Entlassbrief mit XXX).
- Kein Erfinden eines Verlaufs/Entlasszustands, um eine gewünschte Briefart zu erfüllen.
- Keine Zielklinik erfinden (Platzhalter XXX).

## Ausgabeformat
- Wie der gewählte Zieltyp (`arztbrief` / `ambulant`) — reiner Plain-Text.

## Pitfalls
- **KIS-Export ohne Entlassdokumentation:** endet das Material mit Entlassreife → Entlassbrief (K3.10).
- **„Entlassbrief" getippt, Material endet mit der Aufnahme:** kein Entlassbrief konstruieren.
- **Widersprüchliche Nutzerantwort auf Rückfrage:** letzte Nutzeraussage ist maßgeblich; bei Unklarheit kurz
  mit konkreten Optionen nachfragen (inline, nicht Popup).

## Provenienz
- `skills/medizin/entlassbrief-triage/SKILL.md` (Triage, Entscheidungshilfe, kurzstationäre Ausnahme).
- `skills/medizin/schreibdienst/SKILL.md` (Regel 10 Briefart-Default, Verlegungsbrief-„quasi Entlassbrief").
- `skills/medizin/stolperfallen/SKILL.md` (Verlegungsbrief mit ungenannter Zielklinik).
