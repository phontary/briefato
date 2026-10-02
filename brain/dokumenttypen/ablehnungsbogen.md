---
asset: briefato-brain/dokumenttypen/ablehnungsbogen
brain_version: 1.0.0
typ: ablehnungsbogen (Thieme Compliance Dok 1)
aliases: [ablehnungsbogen, thieme, ablehnung, verweigerung, dok 1]
language: de (meta: en)
---

# Playbook: Ablehnungsbogen (Thieme Compliance Dok 1)

## Trigger
- Der Nutzer reicht Bild/Scan des Bogens „Ablehnung einer Untersuchung und/oder Behandlung gegen
  ausdrücklichen ärztlichen Rat und eindringlichen ärztlichen Rat" (Thieme Compliance GmbH, Dok 1) ein,
  ggf. mit Patientendaten und Aufnahmediktat.
- Auch ohne Bild: „Ablehnungsbogen ausfüllen" + Diagnose + abgelehnte Maßnahme.

## Erforderliche Bausteine IN DIESER REIHENFOLGE (als Feldbausteine, nicht als Formularnachbau)
1. **Abgelehnte Maßnahme** (konkret mit Diagnosebezug, 1–2 Sätze).
   - Beispiel: „Stationäre Aufnahme zur parenteralen Schmerztherapie und Labor-/Sonokontrolle bei V.a.
     Nierenkolik rechts."
2. **Dringlichkeit** (Angabe im Text, nicht als Kästchen).
   - Beispiel: „Die abgelehnte Maßnahme muss unverzüglich erfolgen." / „… muss innerhalb von Tagen erfolgen."
3. **Vermerke zur Notwendigkeit/Dringlichkeit** (Begründung).
   - Beispiel: „Bei fortgeschrittenem Harnstau besteht der Verdacht auf eine Schienendysfunktion; die
     Nierenfunktion ist beidseits eingeschränkt, eine Harnableitung ist dringlich."
4. **Mögliche behandlungsbedürftige Komplikationen und Gesundheitsschäden** (mind. 3, diagnosespezifisch).
   - Beispiel: „Urosepsis mit Lebensgefahr, pyelonephritischer Abszess, akutes Nierenversagen, irreversibler
     Nierenfunktionsverlust bis Dialysepflicht."
5. **Mögliche finanzielle Folgen** (Standardformulierung).
   - Beispiel: „Kosten einer außerhalb der empfohlenen Behandlung entstehenden Folgebehandlung, eines erneuten
     Notfalltransports sowie einer späteren, aufwendigeren Versorgung können von der Krankenkasse
     möglicherweise nicht oder nur teilweise übernommen werden; ein Kostenübernahmeanspruch gegenüber
     Krankenhaus/Ärzten besteht insoweit nicht."
6. **Zustand des Patienten** (Einwilligungsfähigkeit, Orientierung, Bewusstseinslage, Intoxikationshinweise,
     kognitive Einschränkung; bei sedierender Medikation Hinweis auf eingeschränkte Straßenverkehrstauglichkeit
     und Heimtransport).
   - Beispiel: „Wach, orientiert, einwilligungs- und einsichtsfähig, kein Hinweis auf Intoxikation; nach
     Analgesie nicht straßenverkehrstauglich, Begleitung erforderlich."
7. **Sonstige ärztliche Anmerkungen** (inkl. Verhalten bei Verschlechterung).
   - Beispiel: „Bei Fieber, Schüttelfrost oder anhaltender Anurie sofortige Wiedervorstellung; bei akuter
     Verschlechterung Notruf 112."

## Pflichtinhalte
- Die abgelehnte Maßnahme immer konkret benennen (mit Diagnosebezug).
- Dringlichkeit nie offen lassen (Notaufnahme/Klinik i.d.R. „unverzüglich"; Sprechstunde „innerhalb von
  Tagen/Wochen").
- Komplikationen mind. 3, diagnosespezifisch (nicht generisch „Verschlechterung").
- Finanzielle Folgen nie weglassen.
- Zustand des Patienten dokumentieren (bei sedierender Medikation immer Straßenverkehrstauglichkeit).
- Bei mehreren abgelehnten Maßnahmen jede einzeln benennen.
- Nicht sicher Belegbares als Platzhalter in eckigen Klammern setzen.

## Verbotene Inhalte
- **Kein Nachbau des Formulars** (keine Seitenaufteilung „Seite 1/Seite 2", keine Kopf-/Patientendaten-/
  Unterschriftsblöcke, keine Ankreuzfeld-Nachbildung) — nur die Textbausteine in Feldreihenfolge.
- Druckdatum/-uhrzeit des Bogens NICHT überschreiben.
- Keine erfundenen Diagnosen (Platzhalter setzen).
- Keine generischen Komplikationen.
- Keine Entwurfsdateien anlegen.

## Ausgabeformat
- Nur die auszufüllenden Feldinhalte als Plain-Text in Feldreihenfolge.
- Der Nutzer überträgt die Bausteine selbst in den Bogen.
- Kein Markdown.

## Pitfalls
- **Unterschriftenfeld Pat. vs. Verweigerung:** unterschreibt der Patient → obere Felder; verweigert er →
  Zeuge + Arzt komplett (sonst nicht beweisfähig).
- **Vorauswahl-Häkchen „Zustand des Patienten":** nur setzen, wenn sicher belegbar, sonst im Freitext.
- **Schwerwiegende inhaltliche Unklarheit** → inline nachfragen (kein Popup).

## Provenienz
- `skills/medizin/ablehnungsbogen-thieme-compliance/SKILL.md` (Formularstruktur, Pflichtinhalte, Stil,
  Ablauf, Stolperfallen).
