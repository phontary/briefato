---
asset: briefato-brain/dokumenttypen/zusammenfassung
brain_version: 1.0.0
typ: zusammenfassung
aliases: [zusammenfassung, verlaufszusammenfassung]
language: de (meta: en)
---

# Playbook: Zusammenfassung

## Trigger
- Der Nutzer fordert eine kurze, maximal komprimierte **Zusammenfassung** eines stationären oder
  mehrzeitigen Verlaufs: „Zusammenfassung", „kürzer", „noch kürzer", „zusammenfassen in X Sätzen".
- Auch ein EINZELNES Rohmaterial (typisch OP-Diktat) mit Auftrag „Op am TT.MM. bitte nur die zusammenfassung".
- Der Verlauf erstreckt sich über mehrere Episoden (Wochen bis Monate auseinander).

Abgrenzung/Vorrang: Der Auftrag „Zusammenfassung" schließt die Diagnoseliste und die Therapie-Maßnahmen-Liste
aus — auch wenn die Basisanweisung sonst eine Diagnoseliste am Briefende verlangt (Skill-Vorrang).

## Erforderliche Abschnitte IN DIESER REIHENFOLGE
Kein Abschnitt, kein Label — **3–4 Sätze reiner Fließtext** (oder exakt die vom Nutzer vorgegebene Satzzahl),
chronologisch verdichtet.

1. **Satzfolge = Episodenkomprimierung.** Satz 1 = älteste Episode, dann je Satz die nächste Episode; der
   letzte Satz fasst Gesamtergebnis/Entlassung zusammen.
   - Beispiel (mehrere Episoden): „Der Patient wurde nach Zustand nach Glutealabszess-Operation im Juni 2025
     notfallmäßig mit Exzision einer chronischen Fistel und radikalem Débridement versorgt, postoperativ
     kam es zu einem Hb-Abfall mit Transfusion von 2 EK."
   - Beispiel (zweite Episode): „Im Nov. 2025 erfolgte bei akuten Rückenschmerzen eine erneute Aufnahme, die
     CT zeigte osteochondrotische Veränderungen, unter Analgesie und Mobilisation bildeten sich die
     Beschwerden zurück."
   - Beispiel (OP-Diktat, 3–4 Sätze): „Im Sep. 2026 wurde der Patient bei gedeckter Gallenblasenperforation
     operativ versorgt. Nach der Aufnahme erfolgte die Umfelddiagnostik mit sonografischem und
     computertomographischem Nachweis der Perforation. Anschließend erfolgte die laparoskopische
     Cholezystektomie. Der postoperative Verlauf gestaltete sich ohne wesentliche Komplikationen."
2. **Datumsangaben abgekürzt als Monat** (kein „03.11.2025", sondern „Nov. 2025"; Monatsnamen ohne Punkt:
   Jan., Feb., März, Apr., Mai, Juni, Juli, Aug., Sep., Okt., Nov., Dez.).

## Pflichtinhalte
- Exakt die vom Nutzer vorgegebene Satzzahl; ohne Vorgabe 3–4 Sätze, orientiert an der Zahl der Episoden.
- Chronologische Verdichtung; jeder Satz eine Episode/ein Themenkomplex.
- Abgekürzter Monatsstil bei Datumsangaben.
- Medizinisches Abkürzungssystem (AB, i.v., s.c., AZ, Z.n., EK, CT, VAC, OP, NRS, Hb).
- Konnektive Zeitangaben („postoperativ", „im Verlauf", „daraufhin", „bei erneuter Aufnahme").
- Nach erster Nennung „der Patient" (nicht in jedem Satz namentlich).

## Verbotene Inhalte
- **Keine Diagnoseliste am Ende.**
- **Keine Therapie-Maßnahmen-Liste.**
- Keine Gliederungselemente (Aufzählung, Absatzumbrüche zwischen den Sätzen, Nummerierung).
- Kein Markdown; keine Einleitung oder Schlussfloskel.
- Keine überflüssigen Details (Nahttechniken, Dosierungen, Visiten-Daten, Instrumente).
- Semikolon höchstens einmal, im Zweifel keines.

## Ausgabeformat
- Reiner Plain-Text, Fließtext, keine Absatzumbrüche zwischen den Sätzen.
- Bei kombinierter Ausgabe (z. B. „OP-Bericht + Zusammenfassung"): eine Leerzeile Trennung, keine Überschrift
  (Zusammenfassung nach dem OP-Bericht).
- Folgeauftrag „noch kürzer": sofort eine dichtere Fassung DERSELBEN Zusammenfassung liefern — nichts neu
  herleiten, keine Rückfrage, die Langfassung nicht erneut ausgeben.

## Pitfalls
- **Falsche Satzzahl:** Nennt der Nutzer eine Zahl („in 2 Sätzen"), ist sie bindend — nicht auf 3–4 aufrunden.
- **Name im Diktat nicht sicher lesbar:** keine Identität raten; ohne Namensnennung formulieren.
- **Falsche Erwartung an die Blöcke:** keine Diagnoseliste/kein Therapieblock — auch wenn ein Begleit-Arztbrief
  sie hätte.
- **Folgeauftrag zum selben Fall** (danach der Entlassbrief): keine Abweichung, aber Musterbrief-Sektion
  erweitern statt neu anlegen.

## Provenienz
- `skills/medizin/zusammenfassung/SKILL.md` (Satzregeln, Datumsstil, Ausschluss Diagnoseliste, Episodenlogik,
  Beispiele).
- `skills/medizin/operationsbericht/SKILL.md` (Kombiauftrag „OP-Bericht + Zusammenfassung").
- `skills/medizin/schreibdienst/references/auftragskombinationen-und-fallrecherche.md` (Kombinationsregeln).
