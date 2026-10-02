---
asset: briefato-brain/dokumenttypen/arztbrief
brain_version: 1.0.0
typ: arztbrief (stationär — Entlassbrief / Aufnahmebrief / Verlegungsbrief)
aliases: [schreibdienst, entlassbrief, entlassungsbrief, arztbrief, aufnahmebrief, verlegungsbrief]
language: de (meta: en)
---

# Playbook: Arztbrief (stationär)

## Trigger
- Rohmaterial ohne speziellen Auftrag, oder der Nutzer sagt „nichts" / nennt keinen Typ → **dieser Typ (Default)**.
- „Entlassbrief" / „Entlassungsbrief" / „Arztbrief" und der Verlauf ist stationär (Patient übernachtet, mehrtägig).
- Innerhalb dieses Typs drei Unterarten, unterschieden am Materialende:
  - **Entlassbrief** — Rohmaterial endet mit klinischer Entlassreife (Behandlungserfolg, vertragener Kost,
    beschwerdefrei, Beratungsgespräch) auch ohne Entlassungseintrag/-datum.
  - **Aufnahmebrief** — Verlauf läuft erkennbar weiter (geplante OP am Folgetag, ausstehende Diagnostik,
    keine Auflösung der Akutsymptomatik).
  - **Verlegungsbrief** — Verlegung/Übernahme in eine andere Abteilung/Klinik; bei „Verlegungsbericht,
    quasi Entlassbrief" wird die Entlassbrief-Struktur mit Verlegungssatz verwendet.
- **Kombinierte Aufträge** (z. B. „OP-Bericht + Zusammenfassung"): dieser Typ nur, wenn er Teil des Auftrags ist.

Abgrenzung: keine stationäre Aufnahme → `ambulant`; nur „Zusammenfassung" → `zusammenfassung`;
„OP-Bericht" → `operationsbericht`.

## Erforderliche Abschnitte IN DIESER REIHENFOLGE
Alle Abschnitte sind Fließtext ohne Überschriften (Regel K3.2). Kein Einleitungssatz (K1.3).

1. **Aufnahme-Anamnese / Vorgeschichte** (destilliert, max. 2 Sätze): Vorstellungsweg, Dauer/Art der
   Beschwerde, relevante Vorbehandlung, Aufnahmegrund mit Schmerzangabe.
   - Beispiel: „Die Patientin stellte sich mit dem Rettungsdienst bei seit vier Wochen bestehender
     atraumatischer Ulzeration am rechten Unterschenkel vor."
   - Beispiel: „Der Patient wurde wegen seit zwei Tagen zunehmender rechtsseitiger Unterbauchschmerzen
     mit Übelkeit und subfebrilen Temperaturen aufgenommen."
2. **Körperliche Untersuchung (KU)** (destilliert, 1–2 Sätze): nur der diagnoseführende Befund plus die
   wegweisenden Ausschlussbefunde.
   - Beispiel: „In der KU zeigte sich eine ca. 3 × 3 cm große Ulzeration mit fibrinbelegtem Wundgrund,
     die peripheren Pulse waren tastbar, der pDMS intakt."
   - Beispiel: „Das Abdomen war druckschmerzhaft im rechten Unterbauch mit LLS und lokaler ABW, die
     Darmgeräusche waren erhalten."
3. **Stationäre Aufnahmebegründung** (Pflichtsatz, unmittelbar nach KU; entfällt, wenn KU fehlt → dann
   direkt nach der Anamnese).
   - Beispiel: „Wir nahmen die Patientin zur weiteren Diagnostik bzw. Schmerztherapie stationär auf."
4. **Diagnostik / Bildgebung** (chronologisch, je Untersuchung 2–3 Sätze im Indikation–Fragestellung-Format;
   auffällige Befunde, Fragestellung explizit beantwortet; Bildgebung auf max. 2 Sätze).
   - Beispiel: „Zur Abklärung der Beschwerden erfolgte eine MRT des Beckens, wobei sich eine gedeckt
     perforierte Divertikulitis zeigte, eine Passagestörung bestand nicht und eine Appendizitis wurde
     ausgeschlossen."
   - Beispiel (Sono → CT, Fokussuche): „Bei persistierend hohen Entzündungsparametern und V.a. ein
     Gallenblasenempyem sonografisch führten wir eine CT Abdomen/Becken durch."
5. **OP / Eingriff im Verlauf** (äußerst knapp, K3.6): Indikation in 1 Satz, Zugang + Kernbefund +
   entscheidende Maßnahme + Drainagen in max. 2 Sätzen; Histologie an der Stelle des Eingriffs.
   - Beispiel: „Bei symptomatischer Cholezystolithiasis erfolgte die laparoskopische Cholezystektomie;
     intraoperativ zeigte sich eine gedeckt perforierte Cholezystitis."
   - Beispiel: „Die Histologie bestätigte eine sekundäre Osteomyelitis, eine Malignität lag nicht vor."
6. **Klinischer Verlauf** (datumsfrei, konnektive Zeitangaben, Visiten/Pflege eingewoben, jeder Befund
   einmal).
   - Beispiel: „Postoperativ gestaltete sich der Verlauf zunächst regelrecht, unter kalkulierter parenteraler
     Antibiose kam es nach laborchemischer Besserung zur klinischen Stabilisierung."
7. **Entlassung / Verlegung** (mit explizitem Datum, falls bekannt; sonst XXX).
   - Beispiel: „Nach klinischer Besserung entließen wir den Patienten am 07.05.2026 in die häusliche Pflege."
   - Beispiel (Verlegung): „Da eine operative Versorgung in unserem Hause nicht möglich war, verlegten wir
     den Patienten am 17.04.2026 zur weiteren Behandlung und dringenden operativen Versorgung in die Klinik
     für Allgemein- und Viszeralchirurgie des XXX. Wir bitten um Übernahme."

**Schlussblöcke (nur stationärer Entlassbrief), in dieser Reihenfolge:**
8. Plain-Text-Zeile „ambulante Therapieempfehlungen nach der Entlassung:" → Empfehlungen in EINEM Absatz,
   erste Zeile die Terminvereinbarung (z. B. Koloskopie). **Fehlt bei Verlegungsbriefen.**
   - Beispiel: „ambulante Therapieempfehlungen nach der Entlassung:
     Wir empfahlen die klinische und laborchemische Verlaufskontrolle, ausreichende Trinkmenge und
     regelmäßige Mobilisation; bei Bedarf Wiedervorstellung in der chirurgischen Sprechstunde
     (Tel. 06631 98-1227 [institutionell]) zur Wundkontrolle. Vielen Dank für die Weiterbetreuung."
9. Plain-Text-Zeile „Diagnosen:" + ein Eintrag pro Zeile, Hauptdiagnose zuerst.
   - Beispiel: „Diagnosen:
     Schwergradig ausgeprägte ulzero-phlegmonöse Cholezystitis mit gedeckter Perforation bei
     Cholezystolithiasis
     Harnwegsinfekt
     Hypokaliämie"
10. Plain-Text-Zeile „Nebenerkrankungen:" + eine Komorbidität pro Zeile; ohne Komorbiditäten nur „keine".
11. Plain-Text-Zeile „Therapie-Maßnahmen auf der Station:" + jeder Eingriff als „OP am TT.MM.JJJJ:
    <Eingriff>", danach die übrigen tatsächlich durchgeführten Maßnahmen (eine pro Zeile, ohne OPS-Kodes).
    - Beispiel: „Therapie-Maßnahmen auf der Station:
      OP am 17.04.2026: Laparoskopische Cholezystektomie
      Kalkulierte antibiotische Therapie i.v.
      Thromboseprophylaxe s.c."

**Sonderfall Exitus letalis:** nach Abschnitt 6, VOR der Diagnoseliste, eine Schlussformel
- Beispiel: „Der Tod trat im Rahmen einer schweren Sepsis ein und ließ sich trotz aller medizinischen
  Bemühungen nicht mehr aufhalten. Unser tiefes Mitgefühl und unsere aufrichtige Anteilnahme gelten in
  diesen schweren Stunden seiner Familie."

## Pflichtinhalte
- Aufnahmebegründungssatz „Wir nahmen die Pat. zur weiteren Diagnostik bzw. Schmerztherapie stationär auf."
- Diagnoseliste mit „Diagnosen:"-Beschriftung, ein Eintrag pro Zeile, keine „Dg.:"-Präfixe.
- Histologie-Status (ausstehend oder Ergebnis), sobald PEs/Biopsien entnommen wurden.
- Bei stationärem Entlassbrief: Empfehlungsblock + „Nebenerkrankungen:" + „Therapie-Maßnahmen auf der
  Station:".
- Klinische Spezialtests bei entsprechendem V.a. (z. B. Thompson-Test).
- Korrekte Umlaute und ß (K3.0); Abkürzungen direkt (K3.5).

## Verbotene Inhalte
- Keine Einleitung/Schlussfloskel („Hiermit berichten wir", „Wir berichten über o. g. Pat.") — außer der
  Exitus-Formel und dem Empfehlungsblock.
- Kein Markdown, keine Überschriften, keine Kategorie-Labels („KU:", „Labor:", „CT:") im Fließtext.
- Keine Datumsangaben im Verlauf (außer OP-/Entlassdatum).
- Keine ausgeschriebenen Befunddetails/Normalbefunde; keine Doppelnennungen.
- Keine erfundenen Diagnosen, Patientendaten, Befunde, Konsilergebnisse, Laborwerte.
- Keine „Z.n. <OP>"-Zeilen in der Diagnoseliste (Operationen stehen als „OP am …:"-Zeilen im Therapieblock).
- Therapie-Maßnahmen-Liste NICHT bei Aufnahme-/Verlegungsbriefen.
- Semikolon höchstens einmal, im Zweifel keines (K3.11).

## Ausgabeformat
- Reiner Plain-Text, copy-paste-fähig, keine Markdown-Formatierung (K1.4/K3.1).
- Der fertige Text ist die LETZTE Ausgabe; kein Kommentar, keine Fortschrittsmeldung danach.
- Ambulante Empfehlungen als EIN Absatz; Diagnosen/Nebenerkrankungen/Therapie-Maßnahmen als Zeilenlisten
  mit Beschriftungszeile.

## Pitfalls
- **KIS-Export ohne Entlassdokumentation:** bei Entlassreife → Entlassbrief wählen (nicht Aufnahmebrief),
  sonst geht die Therapie-Maßnahmen-Liste verloren (K3.10).
- **Fehlendes Entlassdatum:** einmal gezielt fragen; ohne Antwort XXX setzen, nicht erneut nachfragen.
- **Fehlender KU im Export:** keinen KU erfinden; Pflichtsatz hinter die Anamnese rücken.
- **Widersprüchlicher KIS-Eintrag am Entlasstag:** das dokumentierte Outcome (ärztliche Entlassung) ist
  maßgeblich; keinen Widerspruch abbilden, den der Verlauf nicht trägt.
- **„Entlassbrief" getippt, Material ist aber Aufnahme:** nicht konstruieren, was nicht belegt ist (kein
  erfundener Verlauf/Entlasszustand).
- **Verwechslung mit ambulant:** keine stationäre Aufnahme → `ambulant` (kein Aufnahmebegründungssatz,
  keine Therapie-Maßnahmen-Liste).
- **Vorgeschichte/Komorbiditäten nicht im Fließtext auflisten** — nur im Block „Nebenerkrankungen:".

## Provenienz
- `SOUL.md` (Kernauftrag, Diagnoseliste am Ende, Routing-Default).
- `skills/medizin/schreibdienst/SKILL.md` (Formatierungsregeln 0–11, Abkürzungsverzeichnis, Aufnahme-Anamnese/
  KU-Destillat, Musterbrief-Logik, Empfehlungs-/Diagnose-/Therapieblock, Exitus-Formel).
- `skills/medizin/stolperfallen/SKILL.md` (Kettenstruktur, Pflichtsatz, Histologie, Nutzerstraffung,
  Diagnose-/Therapieblock-Format).
- `skills/medizin/entlassbrief-triage/SKILL.md` (Unterart-Entscheidung).
- `skills/medizin/schreibdienst/references/KIS-export-lücken.md` (Lücken, kein Erfinden).
