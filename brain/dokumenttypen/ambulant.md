---
asset: briefato-brain/dokumenttypen/ambulant
brain_version: 1.0.0
typ: ambulant (ambulant / tageschirurgisch)
aliases: [ambulant, tageschirurgisch, nfa, ambulante vorstellung]
language: de (meta: en)
---

# Playbook: Ambulanter / Tageschirurgischer Brief

## Trigger
- Keine stationäre Aufnahme: Sprechstundenvorstellung → geplanter ambulanter/tageschirurgischer Eingriff →
  Entlassung am OP-Tag.
- Vorstellung in der NFA/Notaufnahme OHNE stationäre Aufnahme — auch OHNE Operation (reine Wundversorgung,
  Abszessspaltung, konservative Behandlung).
- Entscheidend allein: **keine stationäre Aufnahme**.

Abgrenzung: stationärer Verlauf → `arztbrief`. Unklar → `entlassbrief`-Triage.

## Erforderliche Abschnitte IN DIESER REIHENFOLGE
Fließtext, keine Überschriften, keine Einleitung/Schlussfloskel.

1. **Vorstellung / Einleitung** (eine der Nutzer-Varianten, um Wiederholungen zu vermeiden).
   - Beispiel: „Der Patient stellte sich in unserer chirurgischen Sprechstunde vor. In der Folge wurde die
     Indikation zur Leistenhernienversorgung gestellt, die am 12.09.2026 in Intubationsnarkose erfolgte."
   - Beispiel (NFA ohne OP): „Das Kind stellte sich in Begleitung seiner Mutter in der NFA vor, nachdem es
     sich den Kopf gestoßen hatte."
2. **KU / Befund** (1–2 Sätze, diagnoseführend).
   - Beispiel: „In der KU zeigte sich an der Stirn oberhalb der linken Augenbraue eine ca. 0,5 cm große
     Kopfplatzwunde; neurologisch war das Kind unauffällig."
3. **Durchgeführte Maßnahme / OP-Absatz** (kurz):
   - Konservativ ohne OP: die Maßnahme (Wunddesinfektion, Adaptation mit Fibrinkleber, Pflasterverband).
     Beispiel: „Die Wunde wurde desinfiziert, mit Fibrinkleber adaptiert und mit Pflaster verbunden."
   - Mit OP: intraoperativer Befund + Vorgehen in **maximal EINEM Satz (max. 30 Wörter)**.
     Beispiel: „Intraoperativ zeigte sich beidseits eine große indirekte Leistenhernie, die beidseits mittels
     Netzeinlage 10 × 15 cm versorgt wurde."
4. **Aufklärung / postoperativer Verlauf** (eine Variante).
   - Beispiel (mit OP): „Postoperativ wurde der Patient über den Aufwachraum auf die Tagesklinik verlegt;
     die Wunde zeigte sich reizlos, noch am OP-Tag erfolgte die Entlassung in die häusliche Pflege."
   - Beispiel (ohne OP): „Die Mutter wurde über das weitere Vorgehen aufgeklärt; der Hautkleber löst sich
     nach etwa 3 Tagen von selbst."
5. **Ambulante Therapieempfehlungen** (allgemein + diagnose-/OP-spezifisch aus dem Musterbrief).
   - Beispiel: „Empfohlen werden die regelmäßige ambulante Wundkontrolle sowie die Fortsetzung der
     Schmerztherapie bei Bedarf; bei Fieber, Rötung oder zunehmenden Schmerzen bitten wir um sofortige
     Wiedervorstellung."
6. **Diagnoseliste am Ende** (ohne „Dg.:"-Präfix).
   - Beispiel: „Diagnosen:
     Platzwunde der Stirn
     Commotio cerebri ausgeschlossen"

## Pflichtinhalte
- Korrekte Umlaute (ä, ö, ü) — zwingend.
- Abkürzungen aus dem Schreibdienst-Abkürzungsverzeichnis.
- Diagnoseliste am Ende ohne „Dg.:"-Präfix.
- Diagnose-/OP-spezifische Nachsorgeempfehlungen aus dem jeweiligen Musterbrief.
- Bei NFA-Vorstellung ohne OP: OP-Absatz, Aufwachraum-/Tagesklinik-Baustein und postoperative
  Nachsorgeempfehlungen entfallen; stattdessen Aufklärung und Empfehlungen.

## Verbotene Inhalte
- **KEIN** „Wir nahmen den Pat. … stationär auf."-Satz.
- **KEINE** Therapie-Maßnahmen-Liste des stationären Schreibdienst-Skills.
- Keine „Wir berichten über o. g. Pat."-Formulierung.
- Kein Markdown; keine Einleitung/Schlussfloskel.
- OP-Beschreibung nicht auf mehrere Sätze aufteilen (max. 1 Satz, max. 30 Wörter).
- Semikolon höchstens einmal, im Zweifel keines.

## Ausgabeformat
- Reiner Plain-Text, copy-paste-fähig.
- Schluss: Diagnoseliste (eine Zeile pro Eintrag).
- Datumsangaben: OP-Datum nennen (Ausnahme von der Datumsfreiheit).

## Pitfalls
- **Verwechslung mit stationär:** sobald eine Übernachtung/mehrtägiger Verlauf vorliegt → `arztbrief`.
- **Kurzstationäre Fälle:** der Nutzerwortlaut entscheidet — sagt er explizit „stationäre Entlassung"/
  „Entlassbrief", bleibt es ein stationärer Entlassbrief (inkl. Therapie-Maßnahmen-Liste), auch wenn die
  Entlassung am OP-Tag erfolgt.
- **Rein konservative NFA-Vorstellung:** keine OP-Bausteine erzwingen.
- **Fehlende Fäden-/Nachsorgeangabe:** aus dem Musterbrief übernehmen, nicht erfinden.

## Provenienz
- `skills/medizin/ambulant/SKILL.md` (Formulierungsvarianten, Abgrenzung stationär, OP-Kompressionsregel).
- `skills/medizin/entlassbrief-triage/SKILL.md` (Übernachtungs-Anhalt, kurzstationäre Ausnahme).
- `skills/medizin/schreibdienst/SKILL.md` (Abkürzungen, kein Markdown, Diagnoseliste ohne Präfix).
