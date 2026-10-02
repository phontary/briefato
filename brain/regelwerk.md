---
asset: briefato-brain/regelwerk
brain_version: 1.0.0
language: de (meta: en)
---

# Regelwerk — nummerierte, prüfbare Regeln (R1…Rn)

Destillat aus `kern.md` + `dokumenttypen/*.md` + MEMORY.md/USER.md. Jede Regel ist EIN Satz und so
formuliert, dass sie als automatisierte Prüfung umsetzbar ist. Provenienz steht in jeder Zeile.
Format: `R<n>: <Regel> — Provenienz: <Herkunft>`.

## A. Ausgabeform und Stil

R1: Der Ausgabetext ist durchgehender Fließtext ohne Aufzählungszeichen im Erzählteil. — Provenienz: SOUL.md („Fließender Text"), schreibdienst/SKILL.md (Regel 1).
R2: Der Brief enthält keine Einleitung wie „Hiermit berichten wir" oder „Wir berichten über o. g. Pat.". — Provenienz: SOUL.md („Kein Einleitung oder Schluss"), ambulant/SKILL.md.
R3: Der Brief enthält keine Schlussfolgerung/Floskel, außer der Exitus-Formel und dem Empfehlungsblock. — Provenienz: SOUL.md („Kein Einleitung oder Schluss"), schreibdienst/SKILL.md (Regel 8/9).
R4: Die Ausgabe enthält kein Markdown (keine Fettung, Kursivsetzung, Überschrift, Codeblock). — Provenienz: schreibdienst/SKILL.md (Regel 1).
R5: Die Ausgabe enthält keine Kategorie-Labels wie „KU:", „Labor:", „Sono:", „CT:", „Therapie:", „Befund:" im Fließtext. — Provenienz: schreibdienst/SKILL.md (Regel 2).
R6: Ausgabetexte verwenden korrekte deutsche Umlaute (ä, ö, ü) und ß, NICHT ae/oe/ue/ss. — Provenienz: schreibdienst/SKILL.md (Regel 0), ambulant/SKILL.md.
R7: Der Ton ist sachlich, professionell und medizinisch korrekt, ohne Füllwörter. — Provenienz: schreibdienst/SKILL.md (Stil).
R8: Es werden höchstens EIN Semikolon pro Brief verwendet, im Zweifel keines. — Provenienz: schreibdienst/SKILL.md (Regel 11), stolperfallen/SKILL.md (Semikolon-Regel).

## B. Struktur und Reihenfolge

R9: Die Informationskette Beschwerde → Untersuchung → Diagnose/DD → Behandlung → Verlauf läuft im Text klar durch. — Provenienz: stolperfallen/SKILL.md („Struktur muss für den Leser erkennbar sein").
R10: Der Verlauf enthält keine Datumsangaben im Format „am TT.MM.", außer OP-Datum und Entlassdatum. — Provenienz: schreibdienst/SKILL.md (Regel 7), pflegeberichte-integration/SKILL.md.
R11: Fehlt ein vom Nutzer nicht festgelegtes Datum, steht der Platzhalter XXX im Text. — Provenienz: schreibdienst/SKILL.md (Regel 7).
R12: Visiteneinträge sind in den Verlaufstext eingewoben und nicht einzeln mit Datum aufgelistet. — Provenienz: schreibdienst/SKILL.md (Regel 3).
R13: Jeder Befund wird im Text nur einmal genannt (keine Doppelnennungen). — Provenienz: schreibdienst/SKILL.md (Regel 3), diktat-tippfehler/SKILL.md.
R14: Bei jedem stationären Brief steht der Satz „Wir nahmen die Pat. zur weiteren Diagnostik bzw. Schmerztherapie stationär auf." unmittelbar nach der Anamnese bzw. KU. — Provenienz: stolperfallen/SKILL.md, schreibdienst/SKILL.md.
R15: Die Aufnahme-Anamnese ist auf maximal 2 Sätze destilliert. — Provenienz: schreibdienst/SKILL.md (Aufnahme-Anamnese/KU-Destillat).
R16: Der KU ist auf 1–2 Sätze destilliert (diagnoseführender Befund + wegweisende Ausschlussbefunde). — Provenienz: schreibdienst/SKILL.md (Aufnahme-Anamnese/KU-Destillat).
R17: Bei entnommenen PEs/Biopsien ist der Histologie-Status benannt (Ergebnis oder „Die Histologie steht noch aus."). — Provenienz: stolperfallen/SKILL.md (Histologie-Status).
R18: Bei V.a. eine Verletzung mit etabliertem klinischem Test ist der Test samt Ergebnis benannt (z. B. Thompson-Test). — Provenienz: stolperfallen/SKILL.md (klinische Spezialtests).
R19: Untersuchungen stehen in chronologischer Reihenfolge ihres Datums und je in 2–3 Sätzen im Indikation–Fragestellung-Format. — Provenienz: stolperfallen/SKILL.md (Indikation–Fragestellung-Format).
R20: Bildgebungsbefunde sind auf maximal 2 Sätze komprimiert (Kernaussage + höchstens ein Nebenbefund). — Provenienz: stolperfallen/SKILL.md (Untersuchungsbefunde radikal komprimieren).

## C. Diagnosen- und Therapieblöcke

R21: Die Diagnosen stehen am Ende des Dokuments als Liste, eingeleitet durch die Plain-Text-Zeile „Diagnosen:". — Provenienz: SOUL.md („am Ende bitte deine Diagnosen einlisten"), schreibdienst/SKILL.md (Regel 4).
R22: Die Diagnoseliste enthält kein „Dg.:"-Präfix, keine Nummerierung und keine Aufzählungszeichen. — Provenienz: schreibdienst/SKILL.md (Regel 4).
R23: In der Diagnoseliste stehen keine „Z.n. <OP>"-Zeilen (Eingriffe erscheinen als „OP am …:"-Zeilen im Therapieblock). — Provenienz: stolperfallen/SKILL.md (Diagnose-/Therapieblock-Format).
R24: Eine „Zusammenfassung" enthält keine Diagnoseliste und keine Therapie-Maßnahmen-Liste. — Provenienz: zusammenfassung/SKILL.md, schreibdienst/SKILL.md (Triage).
R25: Bei einem stationären Entlassbrief steht vor der Diagnoseliste der mit „ambulante Therapieempfehlungen nach der Entlassung:" beschriftete Empfehlungsblock. — Provenienz: schreibdienst/SKILL.md (Regel 4/9).
R26: Bei einem stationären Entlassbrief folgt nach der Diagnoseliste der Block „Nebenerkrankungen:"; ohne Komorbiditäten nur das Wort „keine". — Provenienz: schreibdienst/SKILL.md (Regel 4), stolperfallen/SKILL.md.
R27: Bei einem stationären Entlassbrief steht als letzter Block „Therapie-Maßnahmen auf der Station:" mit einer dokumentierten Maßnahme pro Zeile. — Provenienz: schreibdienst/SKILL.md (Regel 9).
R28: In der Therapie-Maßnahmen-Liste steht nur tatsächlich durchgeführte und dokumentierte Maßnahmen (keine Standardmaßnahmen ohne Doku-Beleg). — Provenienz: schreibdienst/SKILL.md (Regel 9).
R29: Operative Eingriffe in der Therapie-Maßnahmen-Liste stehen als Zeile „OP am TT.MM.JJJJ: <Eingriff>". — Provenienz: schreibdienst/SKILL.md (Regel 9).
R30: Aufnahme-, Verlegungs-, ambulante Briefe, OP-Berichte und Zusammenfassungen enthalten keine Therapie-Maßnahmen-Liste. — Provenienz: schreibdienst/SKILL.md (Regel 9).
R31: Ein Verlegungsbrief endet ohne den Block „ambulante Therapieempfehlungen nach der Entlassung:". — Provenienz: stolperfallen/SKILL.md (Verlegungsbrief), schreibdienst/SKILL.md.
R32: Ein Verlegungsbrief ohne genannte Zielklinik enthält den Platzhalter XXX statt eines erfundenen Kliniknamens. — Provenienz: stolperfallen/SKILL.md.
R33: Bei Exitus letalis endet der Brief vor der Diagnoseliste mit einer Schlussformel des Mitgefühls. — Provenienz: schreibdienst/SKILL.md (Regel 8).

## D. Abkürzungen und Begriffe

R34: Medizinische Abkürzungen werden direkt verwendet, ohne ausgeschriebene Erstnennung mit Klammerabkürzung. — Provenienz: schreibdienst/SKILL.md (Regel 5, Stil).
R35: Es wird „Nausea" statt „Übelkeit" verwendet. — Provenienz: stolperfallen/SKILL.md (Fall Ridder/Begriffspräferenzen).
R36: Es wird „Miktion" statt „Wasserlassen" verwendet. — Provenienz: stolperfallen/SKILL.md (Fall Jauk).
R37: Es wird „Koloskopie" statt „Darmspiegelung" verwendet. — Provenienz: stolperfallen/SKILL.md (Fall Jauk).
R38: Es wird „NFA" statt „ZNA" und „ABW" statt „AWS" verwendet. — Provenienz: stolperfallen/SKILL.md (Fall Ridder).
R39: Im Verlaufstext wird „parenteral" statt „i.v." bevorzugt. — Provenienz: schreibdienst/SKILL.md (Abkürzungsverzeichnis, Nutzerfassung 28.09.2026).
R40: Zahlen werden als Ziffern geschrieben („6 Wochen", nicht „sechs Wochen"). — Provenienz: stolperfallen/SKILL.md (Fall Jauk).

## E. Diktat- und Spracherkennungsfehler

R41: Tipp- und Diktatfehler werden stillschweigend korrigiert, ohne „sic"-Vermerk oder Anmerkung. — Provenienz: diktat-tippfehler/SKILL.md, stolperfallen/SKILL.md.
R42: Widersprüchliches Geschlecht im Rohmaterial führt zu geschlechtsneutraler Formulierung, nicht zu einer geratenen Zuordnung. — Provenienz: diktat-tippfehler/SKILL.md, stolperfallen/SKILL.md.
R43: Inhaltlich mehrdeutige oder nicht auflösbare Passagen bleiben unkorrigiert bzw. werden ersatzlos weggelassen. — Provenienz: diktat-tippfehler/SKILL.md (Grenzen), stolperfallen/SKILL.md.
R44: Belegte Fehlhörer werden stillschweigend ersetzt (z. B. „Wurstfraktur" → Wulstfraktur, „Sableb-Technik" → Sublay-Technik). — Provenienz: stolperfallen/SKILL.md (Diktatfehler), references/standard-narbenhernie-sublay.md.
R45: Pharmakologisch unmögliche Dosierungen werden NICHT stillschweigend korrigiert, sondern ohne Dosis genannt und inline gemeldet. — Provenienz: stolperfallen/SKILL.md (pharmakologisch unmögliche Dosierungen).

## F. Verbote (nichts erfinden)

R46: Es werden keine Diagnosen in die Diagnoseliste aufgenommen, die nicht belegt sind (auch nicht aus einer nur geplanten Maßnahme). — Provenienz: stolperfallen/SKILL.md, schreibdienst/SKILL.md.
R47: Es werden keine Patientendaten (Name, Geburtsdatum, Geschlecht, Fallnummer) erfunden oder geraten. — Provenienz: schreibdienst/SKILL.md (Regel 10), stolperfallen/SKILL.md.
R48: Namensgleichheit mit einem archivierten Fall wird nicht als Identitätsnachweis behandelt. — Provenienz: stolperfallen/SKILL.md (Namensgleichheit).
R49: Wird nur die Durchführung einer Untersuchung ohne Befund genannt, wird nur die Durchführung dokumentiert (kein Befund erfinden). — Provenienz: stolperfallen/SKILL.md (KIS-Export-Lücken).
R50: Ein Konsilergebnis wird nur benannt, wenn es dokumentiert ist (sonst nur „ein Konsil wurde angefordert"). — Provenienz: stolperfallen/references/kis-export-luecken.md.
R51: Als „geplant" genannte Maßnahmen werden nie als bereits durchgeführt formuliert. — Provenienz: schreibdienst/references/auftragskombinationen-und-fallrecherche.md.
R52: Bei lückenhaftem OP-Rohmaterial werden nur standardgemäße Schritte und Musterbrief-Materialien ergänzt, keine patientenindividuellen Situsdetails. — Provenienz: operationsbericht/SKILL.md.
R53: Das Rohmaterial wird nicht mit erfundenen Laborwerten, Temperaturen oder Vorbefunden angereichert. — Provenienz: stolperfallen/SKILL.md („selber Befund", ohne erfundene Zahlenwerte).

## G. Routing und Antwortverhalten

R54: Ohne speziellen Auftrag ist der Dokumenttyp der stationäre Arztbrief (schreibdienst). — Provenienz: SOUL.md (Routing), schreibdienst/SKILL.md.
R55: Der Auftrag „OP-Bericht" erzeugt den ausführlichen Operationsbericht, nicht die knappe OP-Kompression. — Provenienz: SOUL.md, operationsbericht/SKILL.md.
R56: Der Auftrag „Zusammenfassung" wählt den Typ Zusammenfassung mit Vorrang vor der Diagnoselisten-Regel. — Provenienz: SOUL.md, zusammenfassung/SKILL.md.
R57: Ambulante/tageschirurgische Fälle (keine stationäre Aufnahme) folgen dem Typ ambulant. — Provenienz: entlassbrief-triage/SKILL.md, ambulant/SKILL.md.
R58: Der ambulante Brief enthält keinen „stationär aufnehmen"-Satz und keine Therapie-Maßnahmen-Liste. — Provenienz: ambulant/SKILL.md.
R59: Bei zwei in EINEM Auftrag genannten Formaten werden beide Fassungen geliefert (nicht eine auswählen, nicht nachfragen). — Provenienz: schreibdienst/SKILL.md (Triage), auftragskombinationen-und-fallrecherche.md.
R60: Rückfragen werden inline im Chat gestellt, nie als clarify-Popup. — Provenienz: schreibdienst/SKILL.md (Rückfragen-Regel), MEMORY.md.
R61: Kommt im selben Turn keine Antwort auf eine Rückfrage, wird mit dem sicheren Default weitergearbeitet (nicht nachfassen). — Provenienz: schreibdienst/SKILL.md (Rückfragen-Regel).
R62: Antworten an den Nutzer sind kurz, Ergebnis zuerst, ohne Tabellen, Emojis oder Sonderzeichen-Girlanden. — Provenienz: stolperfallen/SKILL.md (Antworten), weiterbildung-kv-nachweise/SKILL.md.
R63: Medikationsplan-Aufträge werden ausschließlich als Text im Chat ausgegeben, nie als PDF/Datei. — Provenienz: entlassmedikationsplan/SKILL.md, MEMORY.md.

## H. Musterbriefe / Archiv (produktseitig)

R64: Musterbriefe enthalten ausschließlich die Sektionen Klinik, Diagnostik, Therapie und Nachsorge (bei Neuanlagen zusätzlich Quellen). — Provenienz: schreibdienst/SKILL.md, stolperfallen/SKILL.md.
R65: Musterbriefe enthalten keine Patientennamen, keine Falldaten und keine „Fallbeispiel"-Abschnitte. — Provenienz: schreibdienst/SKILL.md (Musterbrief-Pflege 02.10.2026).
R66: Es werden keine Entwurfs-/Exportdateien angelegt; die einzige Ablage sind die Musterbriefe. — Provenienz: schreibdienst/SKILL.md (Ablauf 7), ablehnungsbogen/SKILL.md.
R67: Der fertige Brieftext ist die letzte Ausgabe, ohne nachfolgenden Kommentar oder Fortschrittsmeldung. — Provenienz: schreibdienst/SKILL.md (Phase 4/Ablauf).
