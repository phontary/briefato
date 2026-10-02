---
asset: briefato-brain/dokumenttypen/pflegebericht-integration
brain_version: 1.0.0
typ: pflegebericht-integration (Quellmaterial-Filter)
aliases: [pflegebericht, pflegeberichte, pflegedokumentation]
language: de (meta: en)
---

# Playbook: Pflegeberichte-Integration (Quellmaterial-Filter)

Pflegeberichte sind in der Regel **Quellmaterial** für einen Arztbrief/eine Zusammenfassung, kein eigener
Ausgabetyp. Dieses Playbook definiert, was aus Pflegeberichten übernommen wird und wie es eingewoben wird.

## Trigger
- Rohmaterial enthält umfangreiche Pflegeberichte (Schichteinträge, „Pflegebericht"-Blöcke).
- Rohmaterial enthält wiederkehrende Pflegeprosa („Pat. laut AO versorgt", „meldet sich bei Bedarf",
  „Pat. im Zimmer und etwas auf Stationsebene mobil").

## Übernahme-Regeln (Was wird übernommen)
Nur klinisch relevante Beobachtungen:
1. **Wundzustand/-heilung** — Verbandwechsel, Sekretion, Wundgröße, Wundauflage.
2. **Stuhlfrequenz/-konsistenz** — dünnflüssig, wässrig, geformt, hellgelb, Frequenz.
3. **Flüssigkeitsbilanz/Trinkmenge** — Trinkverweigerung, parenterale Ernährung, i.v.-Flüssigkeit.
4. **Schmerzangaben** — Schmerzangaben, NRS, Bedarfsmedikation.
5. **Medikamentengabe** — AB-Gabe, Analgesie.
6. **Mobilisation** — mobil auf Stationsebene, Rollator, Bettlägerigkeit.
7. **Vorbereitung auf Untersuchungen** — Abführeinnahme, Einwilligung.
8. **Transfusionen/Kreislauf** — EK-/Blutproduktgabe, Elektrolytsubstitution, Hb-Verlauf.
9. **Vitalparameter-Veränderungen** — SpO2-Abfall, RR-Abfall.
10. **Besondere Vorkommnisse** — Blutung, Sturz, Verwirrtheit.

## Beispielzeilen (eingewoben in den Verlaufstext, nicht als eigener Abschnitt)
- „Im Verlauf klagte der Patient über zunehmende Bauchschmerzen, worunter eine Bedarfsmedikation verabreicht
  wurde."
- „Nach erstmaligem Stuhlgang besserte sich die Beschwerdesymptomatik, der Kostaufbau wurde vertragen."
- „Die Wunde zeigte sich trocken und reizlos, der Verband wurde regelmäßig gewechselt."
- „Bei einem Abfall der Sauerstoffsättigung wurde eine Sauerstoffgabe über Nasenbrille eingeleitet."

## Pflichtinhalte
- Die Pflegeinformationen werden **in den klinischen Verlaufstext eingewoben**, nicht als separater
  „Pflege"-Abschnitt zitiert.
- KIS-/Pflegejargon vor dem Filtern entschlüsseln (z. B. „Viggo" = Venenverweilkanüle; „GKW" =
  Ganzkörperwäsche; „SK" = Sichtkontrolle; „Lasche" = durchgezogene Drainage; „Nutriflex" = parenterale
  Ernährung; „CA Visite" = Chefarztvisite).
- Wiederholungen aus verschiedenen Schichten zu **einer** Aussage zusammenführen (z. B. „blutiger Stuhl"
  nicht mehrfach, sondern einmal mit „wiederholt").
- Datumsstil: konnektive Zeitangaben („bei Aufnahme", „postoperativ", „im Verlauf", „am Folgetag", „nach
  Entfernung der Drainage").

## Verbotene Inhalte (nicht übernehmen)
- Routineversorgungen („Pat. wurde zur Nacht versorgt", „Pat. laut AO versorgt").
- Sichtkontrollen ohne Befund („wirkt schlafend bei SK", „meldet sich bei Bedarf", „keine Wünsche").
- Inkontinenzversorgung ohne Komplikation.
- „Sonst keine Besonderheiten", „keine besonderen Vorkommnisse".
- Identische Einträge in Wiederholung über mehrere Tage.
- „Infusionen lt. Plan/AO" ohne nähere Angabe.
- Datumsformat „am TT.MM." im Verlauf.

## Ausgabeformat
- Der Filter speist den Zielbrief (arztbrief/zusammenfassung); kein eigenständiges Ausgabeformat.
- Reiner Plain-Text, kein Markdown, keine „Pflege:"-Überschrift.

## Pitfalls
- **Schlaf-/Befindlichkeitsvermerke doch übernehmen**, wenn sie einen klinischen Verlauf stützen (z. B.
  „Patient schläft bei allen Kontrollen" als Beleg für eine stabile nächtliche Stoffwechsellage).
- **Erst entschlüsseln, dann filtern** — sonst wird Relevantes als Rauschen verworfen.
- **Widersprüchliche KIS-Einträge:** das dokumentierte Outcome ist maßgeblich.

## Provenienz
- `skills/medizin/pflegeberichte-integration/SKILL.md` (Extraktionsregeln, Datumsstil).
- `skills/medizin/stolperfallen/SKILL.md` (Pflegefilter, KIS-/Pflegejargon-Entschlüsselung).
- `skills/medizin/schreibdienst/references/staging-workup-integration.md` (Pflegeberichte destillieren).
