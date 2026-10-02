# Stolperfallen – Schreibdienst (Briefato Brain)

Quelle: geerntet aus dem Hermes-Schreibdienst-Profil (Skills `stolperfallen`, `schreibdienst`,
`entlassmedikationsplan`, `diktat-tippfehler`, `operationsbericht`, `ambulant`, `zusammenfassung`,
`pflegeberichte-integration`, `op-iterationen`, `ablehnungsbogen-thieme-compliance`,
`klinische-pharmakologie`, `dokumentation/tagebuch-system`), aus `memories/MEMORY.md`/`USER.md`,
aus `/workspace/schreibdienst/log.md` und `/workspace/schreibdienst/index.md`.

Jede Stolperfalle ist als **Symptom → Ursache → Sollverhalten des Produkts → Provenienz** notiert.
Keine Patientendaten: Eigennamen sind durch `[anonymisiert]` ersetzt.

Lesbarkeit: `Sollverhalten` ist die Regel, die das SaaS (Prompt-Policy + Ausgabeformat) erzwingen muss.

---

## A. Ausgabeformat und Struktur

### PIT-01 — Der Brief hat eine Einleitung / einen Schluss
- **Symptom:** Der generierte Text beginnt mit „Wir berichten über o. g. Patienten…" oder endet mit
  einer Zusammenfassung/Floskel.
- **Ursache:** Generisches LLM-Verhalten; die Vorlage verbietet Einleitung und Schluss explizit.
- **Sollverhalten:** Keine Einleitung, keine Schlussfloskel; direkt mit Aufnahmesituation/Anamnese
  beginnen. Der Rückmelde-Text an den Nutzer darf ebenfalls keinen Smalltalk enthalten.
- **Provenienz:** `SOUL.md` — „Kein Einleitung oder Schluss"; `skills/medizin/schreibdienst/SKILL.md`
  (Stil) — „Keine Einleitung oder Schlussfloskel."

### PIT-02 — Markdown / Formatierung im Ausgabetext
- **Symptom:** Der Brief enthält `**fett**`, `#`-Überschriften, Aufzählungszeichen oder Codeblöcke;
  im WebUI ist der Copy-Button nicht direkt am Text.
- **Ursache:** LLMs formatieren standardmäßig in Markdown.
- **Sollverhalten:** Reiner Plain-Text, keine Fettung/Kursivsetzung/Überschriften/Aufzählungszeichen
  im Fließtext; die letzte Ausgabe enthält NUR den Text (kein Tool-Aufruf, kein Kommentar danach).
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Formatierungsregel 1) — „Reiner Text -
  keine Fettung, keine Kursivsetzung, keine Ueberschriften".

### PIT-03 — Textbegriffe / Sektions-Labels mitten im Fließtext
- **Symptom:** „KU:", „Labor:", „Sono:", „Anamnese:", „Therapie:" als Labels im Brief.
- **Ursache:** LLMs neigen zu strukturierten Abschnitten.
- **Sollverhalten:** Alle Informationen fließen als durchgehender Erzähltext ineinander; keine
  Kategorie-Labels. (Ausnahme: die Plain-Text-Labels der Listenblöcke am Ende, siehe PIT-04.)
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Formatierungsregel 2).

### PIT-04 — Keine Beschriftung der Listenblöcke (oder falsche Beschriftung)
- **Symptom:** Diagnoseliste ohne „Diagnosen:". Oder Beschriftung „Therapie-Maßnahmen:" statt
  „Therapie-Maßnahmen auf der Station:".
- **Ursache:** Zwei historische Nutzerfassungen widersprachen sich (eine zwischenzeitliche Fassung
  ohne Label, spätere Nutzerfassungen mit Label).
- **Sollverhalten:** Diagnoseliste wird durch die Zeile „Diagnosen:" eingeleitet; Therapieblock durch
  „Therapie-Maßnahmen auf der Station:"; Empfehlungsblock durch „ambulante Therapieempfehlungen nach
  der Entlassung:". Kein „Dg.:"-Präfix, keine Nummerierung, keine Aufzählungszeichen.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Regeln 4/9) — „die Listen werden wieder
  beschriftet"; `/workspace/schreibdienst/log.md` — „Diagnoseliste und Therapieblock wieder MIT
  Beschriftung".

### PIT-05 — Reihenfolge des Schlussblocks vertauscht
- **Symptom:** Diagnoseliste steht vor den Therapieempfehlungen, oder „Nebenerkrankungen:" fehlt.
- **Ursache:** Mehrere überholte Fassungen.
- **Sollverhalten:** Entlasssatz → „ambulante Therapieempfehlungen nach der Entlassung:" (ein
  Absatz) → „Diagnosen:" → „Nebenerkrankungen:" → „Therapie-Maßnahmen auf der Station:".
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Regel 4); `stolperfallen/SKILL.md`
  („Nutzerfassung 15.09.2026, Fall [anonymisiert]").

### PIT-06 — Gehäufter Semikolon-Gebrauch
- **Symptom:** Mehrere `;` pro Brief.
- **Ursache:** LLM-Standardstil.
- **Sollverhalten:** Höchstens ein Semikolon pro Brief, im Zweifel keines; Aussagen per Punkt trennen
  oder mit „und/mit/bei/unter" verbinden. Kein Nachtragen in bereits gelieferte Texte.
- **Provenienz:** `stolperfallen/SKILL.md` („Kein gehäufter Semikolon-Gebrauch", Nutzerkorrektur
  28.09.2026) — „bitte den NUR SELTEN nutzen".

### PIT-07 — Datumsangaben im Verlaufstext
- **Symptom:** „am 03.09.2026 wurde …" im Verlauf.
- **Ursache:** KIS-Exporte sind datumsgesteuert; LLMs übernehmen das Datum.
- **Sollverhalten:** Keine Datumsangaben im Verlauf; konnektive Zeitangaben („postoperativ", „im
  Verlauf", „am Folgetag"). Ausnahme: OP-Datum und Entlassdatum ausdrücklich nennen. Der Platzhalter
  `XXX` ersetzt ein fehlendes Datum (nach EINER Rückfrage nicht weiter nachfragen).
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Regel 7).

### PIT-08 — Umlaute falsch (ae/oe/ue/ss)
- **Symptom:** Der Brief schreibt „Hypertonie" korrekt, aber „Ruecken"/„Gefaess".
- **Ursache:** ASCII-Transliteration der Skill-Texte wird in die Ausgabe kopiert.
- **Sollverhalten:** Ausgabetexte immer mit korrekten Umlauten und ß; nur die Skill-Texte selbst
  transliterieren.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Regel 0).

### PIT-09 — Abkürzungen ausgeschrieben oder mit Klammer-Erstnennung
- **Symptom:** „Computertomographie (CT)", „Abwehrspannung".
- **Ursache:** Übersetzungswunsch des LLM.
- **Sollverhalten:** Abkürzungen aus dem Verzeichnis IMMER verwenden, direkt (keine ausgeschriebene
  Erstnennung mit Klammer); gelernte Nutzer-Abkürzungen sind verbindlich, nicht glätten:
  NFA (ersetzt ZNA), ITS, OSAS, ABW (nicht AWS), Nausea (nicht Übelkeit), HWI, HÄ, ged. perf., Miktion.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Regel 5 + Abkürzungsverzeichnis);
  `/workspace/schreibdienst/log.md` — „Abkürzungen der Nutzerkorrektur verbindlich … ‚muss immer
  genutzt werden'".

---

## B. Medizinische Kompression und Befundlogik

### PIT-10 — Bildgebung nicht komprimiert
- **Symptom:** Der Brief paraphrasiert den Radiologiebefund (Wanddicken, EDD, E/A, jedes
  Gefäßsegment, Nebenbefunde).
- **Ursache:** „Befund wiedergeben" statt „Diagnose komprimieren".
- **Sollverhalten:** Jede Untersuchung max. 2 Sätze: (1) diagnoseführende Kernaussage, (2) ein Satz
  fallrelevante Nebenbefunde. Echo nur EF/Kinetik, relevante Klappen, PASP/TAPSE. MRA nur führende
  Verschlüsse/Stenosen + Beurteilbarkeit. Keine Normalbefunde (außer sie schließen relevante DD aus).
- **Provenienz:** `stolperfallen/SKILL.md` („Untersuchungsbefunde radikal komprimieren").

### PIT-11 — Untersuchungen ohne Indikation/Fragestellung/Antwort
- **Symptom:** Nur der Befund, nicht warum untersucht wurde und ob die Frage beantwortet ist.
- **Ursache:** Rohbefund wird übernommen.
- **Sollverhalten:** Pro Untersuchung: Indikation/Fragestellung → Modalität → auffällige Befunde →
  explizite Antwort („Cholestase ausgeschlossen"). Chronologisch nach Untersuchungsdatum, mehrere
  Untersuchungen derselben Modalität einzeln.
- **Provenienz:** `stolperfallen/SKILL.md` („Untersuchungsabschnitte: Indikation–Fragestellung-Format").

### PIT-12 — Widersprüchliche Befunde werden doppelt geführt
- **Symptom:** Der Brief enthält sowohl die fehlerhafte Erstangabe als auch den späteren Befund.
- **Ursache:** LLM versucht zu harmonisieren.
- **Sollverhalten:** Es gilt „präziserer, späterer, konsiliarisch bestätigter Befund"; die unklare
  Erstangabe entfällt ersatzlos, die Erstbildgebung wird nur allgemein umschrieben.
- **Provenienz:** `stolperfallen/SKILL.md` (Fall [anonymisiert], 08.09.2026); `references/kis-export-luecken.md`
  — „Dieselbe Logik wie ‚präziserer, späterer Befund'".

### PIT-13 — Nachbefundung kippt den Befund, aber nur ein Satz wird geflickt
- **Symptom:** Nach einer radiologischen Nachbefundung passt nur der Bildgebungssatz, die
  Diagnoseliste/Leitsache bleibt falsch.
- **Ursache:** Lokale statt globale Korrektur.
- **Sollverhalten:** Leitsache neu bestimmen, Verlegungsgrund/Prozedere/Diagnoseliste neu ableiten,
  ausgeschlossene Diagnosen ersatzlos streichen, Laborwert-Deutungen neu rahmen, Archiv mitkorrigieren.
- **Provenienz:** `stolperfallen/SKILL.md` (Präzedenz 19.09.2026, Pat. [anonymisiert]).

### PIT-14 — Pharmakologisch unmögliche Dosierung wird „korrigiert"
- **Symptom:** „7,5 g Piritramid" wird stillschweigend zu 7,5 mg geraten.
- **Ursache:** LLM glättet scheinbare Tippfehler.
- **Sollverhalten:** Substanz ohne Dosis nennen, Unstimmigkeit einmalig inline melden, auf Wunsch
  Platzhalter `XXX` setzen — Dosis nur vom Nutzer bestätigt übernehmen. (Abgrenzung: offensichtliche
  Substanznamen-Fehlhörer werden weiter stillschweigend korrigiert.)
- **Provenienz:** `stolperfallen/SKILL.md` (Präzedenz 19.09.2026).

### PIT-15 — Falsche COPD-GOLD-Klassifikation
- **Symptom:** FEV1 27–29 % wird als GOLD 3 geschrieben.
- **Ursache:** Verwechslung.
- **Sollverhalten:** GOLD 4 bei FEV1 < 30 % des Solls; FEV1-Soll-Prozent prüfen und gegen die Tabelle
  verifizieren.
- **Provenienz:** `stolperfallen/SKILL.md` („GOLD-Klassifikation der COPD").

### PIT-16 — Sauerstoffsättigung als pO2 missverstanden
- **Symptom:** „pO2 auf 85 %".
- **Ursache:** Verwechslung SpO2 (Prozent) / pO2 (mmHg).
- **Sollverhalten:** 85 % Sättigung = SpO2 bzw. „Abfall der Sauerstoffsättigung auf 85 %";
  stillschweigend korrigieren.
- **Provenienz:** `stolperfallen/SKILL.md` („Nutzer-Straffung", Fall [anonymisiert], 05.09.2026).

### PIT-17 — Fehlgeschlagener Eingriff wird verschwiegen
- **Symptom:** Eine nicht passierbare PTA fehlt im Text.
- **Ursache:** „erfolglos" wird als irrelevant gewertet.
- **Sollverhalten:** Als Versuch formulieren („PTA-Versuch") und in der Diagnoseliste als „Z.n. PTA
  rechts (Verschluss interventionell nicht passierbar)" führen — auch ein fehlgeschlagener Eingriff
  ist dokumentationsrelevant.
- **Provenienz:** `stolperfallen/SKILL.md` („Fehlgeschlagene Intervention").

### PIT-18 — Histologie-Status fehlt
- **Symptom:** Nach PE/Biopsie steht nichts zur Histologie.
- **Ursache:** Ergebnis noch nicht im Material.
- **Sollverhalten:** Histologie-Status zwingend nennen („Die Histologie steht noch aus."), unmittelbar
  an der Stelle des Eingriffs.
- **Provenienz:** `stolperfallen/SKILL.md` („Histologie-Status immer benennen").

### PIT-19 — Geplante Maßnahme wird zur Diagnose
- **Symptom:** „diabetologische Einstellung" (geplant) erscheint als Diagnose „DM".
- **Ursache:** LLM schließt medizinisch naheliegend.
- **Sollverhalten:** Geplante Maßnahme nur im Verlaufstext; keine Diagnose erfinden, wenn die
  Grunderkrankung nicht belegt ist.
- **Provenienz:** `stolperfallen/SKILL.md` („Geplante Maßnahmen nicht als Diagnose festschreiben").

### PIT-20 — Ausgeschlossene Diagnose in der Diagnoseliste
- **Symptom:** Radiologisch ausgeschlossene Fraktur erscheint als Diagnose.
- **Ursache:** Stichwort-Treffer wird übernommen.
- **Sollverhalten:** Ausgeschlossene Diagnose höchstens als verneinter Ausschlusssatz im Verlauf, nie
  in der Diagnoseliste; in der Liste steht die tatsächliche Entität (z. B. Prellung).
- **Provenienz:** `stolperfallen/SKILL.md` („Ausgeschlossene Diagnosen beim Musterbrief-Lookup",
  Fall [anonymisiert]); `references/kis-export-lueken.md`.

### PIT-21 — Pflegeberichte wörtlich oder mit Rauschen übernommen
- **Symptom:** „Pat. zur Nacht versorgt", „wirkt schlafend bei SK" stehen im Brief.
- **Ursache:** Massendaten aus KIS-Export werden ungefiltert übernommen.
- **Sollverhalten:** Nur klinisch relevante Beobachtungen (Wundverhältnisse, Mobilität, Schmerzniveau,
  Vitalparameter-Veränderungen, besondere Vorkommnisse) in den Verlauf weben, nicht als „Pflege"-Abschnitt.
- **Provenienz:** `stolperfallen/SKILL.md` („Pflegeberichte aus Upload-Dateien filtern");
  `skills/medizin/pflegeberichte-integration/SKILL.md`.

### PIT-22 — KIS-/Pflegejargon wird nicht entschlüsselt
- **Symptom:** Relevantes wird als Rauschen verworfen (oder unverständlich übernommen).
- **Ursache:** Hausinterne Kürzel unbekannt.
- **Sollverhalten:** Erst entschlüsseln, dann filtern: Viggo = Venenverweilkanüle, SK = Sichtkontrolle,
  Lasche = durchgezogene Drainage, Nutriflex = parenterale Ernährung, CA-Visite = Chefarztvisite,
  GKW = Ganzkörperwäsche, „z. N. versorgt" = zur Nacht (Routine).
- **Provenienz:** `stolperfallen/SKILL.md` („KIS-/Pflegejargon entschlüsseln", belegt 10.09.2026).

### PIT-23 — OP-Bericht nicht auf das Wesentliche reduziert
- **Symptom:** Nahtmaterialstärken, Instrumentenzählungen, Lagerungsdetails stehen im Entlassbrief.
- **Ursache:** Rohbericht wird paraphrasiert.
- **Sollverhalten:** Nur OP-Indikation (1 Satz) + Zugang/Vorgehen (max. 2 Sätze: Befund, Maßnahme,
  Drainagen). Keine sterilen Abdeckungen, Nahttechniken, Desinfektion.
- **Provenienz:** `stolperfallen/SKILL.md` („OP-Bericht auf Wesentliches reduzieren");
  `skills/medizin/schreibdienst/SKILL.md` (Regel 6).

### PIT-24 — Mehrfacheingriffe zeitlich falsch eingeordnet
- **Symptom:** ERCP und Intervall-CHE als ein Eingriff oder in falscher Reihenfolge.
- **Ursache:** Mehrere OPs im selben Aufenthalt.
- **Sollverhalten:** Beide Eingriffe korrekt zeitlich einordnen, verbindende Sätze nutzen, beide als
  separate Diagnoselisten-Einträge, keine Datumsangaben im Verlauf.
- **Provenienz:** `stolperfallen/SKILL.md` („Mehrfacheingriffe im selben stationären Aufenthalt").

---

## C. Diktat- und Spracherkennungsfehler

### PIT-25 — Fehlhörer werden markiert statt stillschweigend korrigiert
- **Symptom:** „[sic]", Anführungszeichen oder Kommentare am korrigierten Wort.
- **Ursache:** LLM will transparent sein.
- **Sollverhalten:** Diktat-/Tippfehler STILLSCHWEIGEND korrigieren — nicht markieren, nicht in
  Anführungszeichen, keine „[sic]"-Kommentare. Unverständliche Phrasen ersatzlos weglassen statt raten.
- **Provenienz:** `stolperfallen/SKILL.md` („Diktat-/Spracherkennungsfehler stillschweigend
  korrigieren"); `skills/medizin/diktat-tippfehler/SKILL.md` („Grundregel").

### PIT-26 — Bekannte OP-Fehlhörer nicht erkannt
- **Symptom:** „Ceroximum", „Potrite Peritonitis", „Transverso-Rectus-Tumie" bleiben stehen.
- **Ursache:** Fehlhörer-Muster unbekannt.
- **Sollverhalten:** Bewährte Muster anwenden: „Ceroximum/Medronidazol" → Cefuroxim/Metronidazol;
  „Potrite Peritonitis" → eitrige Peritonitis; „Endogier/Stäblergerät" → Stapler;
  „Transverso-Rectus-Tumie" → transverso-rektale Anastomose; „Omentum Marius" → Omentum majus.
- **Provenienz:** `stolperfallen/SKILL.md` (Fall [anonymisiert], OP-Bericht Hemikolektomie links).

### PIT-27 — Gallenwege-/Cholezystektomie-Fehlhörer nicht erkannt
- **Symptom:** „geile Blase", „Schölle Cysstolytiasis", „Gedeckterforierte Scholle Zistittis".
- **Ursache:** Verrauschte Viszeralchirurgie-Diktate.
- **Sollverhalten:** „geile Blase/Geilenwege" → Gallenblase/Gallenwege; „Scholle Cysstolytiasis" →
  Cholezystolithiasis; „Gedeckterforierte Scholle Zistittis" → gedeckte perforierte Cholezystitis;
  „Gewisskirurgie" → Viszeralchirurgie; DHC/Ductus hepatocholedochus-Fehlhörer auflösen.
- **Provenienz:** `stolperfallen/SKILL.md` („Diktat-… Gallenwege/Cholezystektomie", 10.09.2026).

### PIT-28 — Neuro-/SHT-Fehlhörer nicht erkannt
- **Symptom:** „subfaszial Herniation", „Schwer Schwindel", „wurde nicht aufgeklärt".
- **Ursache:** Traumadiktate.
- **Sollverhalten:** „subfaszial Herniation" → subfalcinäre Herniation; „Schwer Schwindel" →
  Schwankschwindel; „wurde nicht aufgeklärt" → wurde nicht abgeklärt; Kasus/Kongruenz glätten.
- **Provenienz:** `stolperfallen/SKILL.md` („Diktat-… Neuro-/Schädel-Hirn-Trauma", 10.09.2026).

### PIT-29 — Fuß-/Abszess-/DFS-Fehlhörer nicht erkannt
- **Symptom:** „Fußabstess", „Osziumylitis", „Gewöckkabsel", „Preparator Pathologie Marburg".
- **Ursache:** extrem verrauschte DFS-Diktate.
- **Sollverhalten:** „Fußabstess/Obsessöle" → Fußabszess/Abszesshöhle; „Osziumylitis" → Osteomyelitis;
  „prohibitiv" → präoperativ; „spinnenförmig" → spindelförmig; „Gewöckkabsel" → Gewebsmantel;
  „Preparator Pathologie Marburg" → Präparat ad Pathologie Marburg (nie als Person/Institut deuten).
- **Provenienz:** `stolperfallen/references/diktat-fehlhoerer-fuss-abszess-dfs.md`.

### PIT-30 — „Wurstfraktur" bleibt stehen (kindliches Trauma)
- **Symptom:** „Wurstfraktur" im Text.
- **Ursache:** „Wurstfraktur" ist kein medizinischer Begriff, sondern Spracherkennungs-Rauschen.
- **Sollverhalten:** Immer zu Wulstfraktur (Torusfraktur) korrigieren; bei kindlichem
  Handgelenkstrauma Bildgebungsaussage in den Verlauf, bei Ausschluss nicht in die Diagnoseliste.
- **Provenienz:** `stolperfallen/SKILL.md` (Fall [anonymisiert], kindliche Handgelenksprellung).

### PIT-31 — Fachbegriffe falsch gedeutet (Fuß-/Venenbefunde)
- **Symptom:** „Hornhaut" als Kornea, „Blow-out der C3" als CVI-Stadium C3.
- **Ursache:** Kontext fehlt.
- **Sollverhalten:** Kontextinterpretation: „Hornhaut" bei Fußpflege = Hyperkeratose; „Blow-out der C3"
  im phlebologischen Kontext = insuffiziente C3-Perforansvene (Cockett III); „hintere Bogenvene" =
  V. arcuata posterior (Leonardo-Vene).
- **Provenienz:** `skills/medizin/diktat-tippfehler/SKILL.md`.

### PIT-32 — Widersprüchliche Lokalisationsangaben derselben Verletzung
- **Symptom:** Dieselbe Wunde einmal okzipital, einmal temporal links — beide Angaben im Brief.
- **Ursache:** Anamnese und KU widersprechen sich.
- **Sollverhalten:** Regel „präziserer, späterer Befund": die KU-Lokalisation führt (auch in der
  Diagnoseliste), die Anamnese bleibt ohne Lokalisation; keine Wunde erfinden.
- **Provenienz:** `stolperfallen/SKILL.md` („Widersprüchliche Lokalisationsangaben derselben Verletzung").

### PIT-33 — Unklare Patientendaten: Geschlecht/Name wird geraten
- **Symptom:** Diktat schwankt zwischen „Herr" und „die Patientin"; LLM wählt ein Geschlecht.
- **Ursache:** Widersprüchliches Rohmaterial.
- **Sollverhalten:** Geschlechtsneutral formulieren („das Kind"); Diagnoseliste braucht kein Geschlecht.
  Unlesbarer Name → keine Identität raten, ohne Namensnennung formulieren.
- **Provenienz:** `stolperfallen/SKILL.md` („Unklare Patientendaten im Diktat"); Fall Koriath im log.

### PIT-34 — Namensgleichheit wird als Identität gewertet
- **Symptom:** Alt-Diagnosen/Allergien aus einem früheren Archivfall werden in den neuen Brief
  übernommen, weil der Nachname passt.
- **Ursache:** Fallbeispiele führen oft nur den Nachnamen.
- **Sollverhalten:** Nachname allein ist kein Identitätsnachweis. Default: nur der gelieferte Text;
  inline nachfragen; keine fremden Diagnosen/Allergien einbauen (bei Exitus-Fällen gravierend).
- **Provenienz:** `stolperfallen/SKILL.md` („Namensgleichheit ≠ gleiche Patientin").

### PIT-35 — Belegte Identität wird nicht ausgewertet
- **Symptom:** Bei bestätigtem „selben Pat." fehlen klinisch tragende Archivfakten (z. B. Antikoagulation).
- **Ursache:** Übervorsicht.
- **Sollverhalten:** Bei belegter Identität (identisches OP-Datum UND identische OP) den Voraufenthalt
  auswerten, Archivfakten übernehmen, im Chat transparent benennen und zum Veto anbieten.
- **Provenienz:** `stolperfallen/SKILL.md` (Präzedenz 19.09.2026, Pat. [anonymisiert]).

### PIT-36 — Nicht auflösbare Abkürzung im Kontext Patientenwille wird gestrichen
- **Symptom:** „im Falle einer Verschlechterung legte sie für sich einen RDI fest" — der Wille fehlt.
- **Ursache:** Abkürzung unklar, LLM verwirft die Aussage.
- **Sollverhalten:** Betrifft die Abkürzung den erklärten Patientenwillen/Therapierahmen, die Aussage
  inhaltsgleich ausformulieren (nicht die Abkürzung übernehmen); bei rechtlich tragendem Willen
  zusätzlich inline nachfragen. Rein diagnostisches Kürzel („SK-Erweiterung") wie dokumentiert
  übernehmen, nur in der Diagnoseliste.
- **Provenienz:** `stolperfallen/SKILL.md` („Nicht auflösbare Abkürzung im Kontext Patientenwille").

### PIT-37 — Untersuchungsergebnis erfunden, wenn nur die Durchführung belegt ist
- **Symptom:** „Das CCT zeigte keinen Anhalt für…", obwohl im Material nur „CCT wiederholt" steht.
- **Ursache:** LLM vervollständigt.
- **Sollverhalten:** Nur die Durchführung nennen, keinen Befund erfinden, keine Lücke markieren.
- **Provenienz:** `stolperfallen/SKILL.md` („Untersuchungsergebnis fehlt im Material").

### PIT-38 — Konsil-/Untersuchungsstatus überinterpretiert
- **Symptom:** „Internistisches Konsil: …" obwohl nur die Anforderung dokumentiert ist.
- **Ursache:** Anordnung ≠ Ergebnis.
- **Sollverhalten:** Nur so weit wie belegt: „ein internistisches Konsil wurde angefordert"; kein
  Konsilergebnis erfinden. Offene Anordnung („Termin für Kolo vereinbaren") als eingeleitet formulieren,
  nicht als durchgeführt.
- **Provenienz:** `stolperfallen/references/kis-export-luecken.md` („Konsil-/Untersuchungsstatus nur
  so weit wie belegt").

### PIT-39 — Fehlender KU wird erfunden
- **Symptom:** Ein KU-Absatz, obwohl der Export keinen Untersuchungsbefund enthält.
- **Ursache:** Briefschema erwartet einen KU.
- **Sollverhalten:** Keinen KU erfinden; der Pflichtsatz „Wir nahmen den Pat. … stationär auf." rückt
  direkt hinter die Aufnahme-Anamnese; ein Stationsbefund wird in den Verlauf gewoben.
- **Provenienz:** `stolperfallen/references/kis-export-luecken.md` („KU fehlt im Rohmaterial").

---

## D. Auftrags-/Briefart- und Nutzerinteraktion

### PIT-40 — Falsche Briefart (Aufnahme statt Entlassung oder umgekehrt)
- **Symptom:** Material endet mit Entlassreife, es wird aber ein Aufnahmebrief geliefert (Therapie-
  Maßnahmen-Liste fehlt).
- **Ursache:** Fehlendes Entlassdatum verleitet zum Aufnahmebrief.
- **Sollverhalten:** Endet das Rohmaterial mit klinischer Entlassreife → ENTLASSBRIEF (auch ohne
  Entlassdatum). Läuft der Verlauf erkennbar weiter → Aufnahmebrief. Bei Unsicherheit inline fragen,
  im Zweifel Entlassbrief mit Therapie-Maßnahmen-Liste. Nutzerwortlaut „stationäre Entlassung" sticht.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Regel 10);
  `skills/medizin/entlassbrief-triage/SKILL.md`.

### PIT-41 — Rückfragen per clarify-Popup
- **Symptom:** Der Nutzer antwortet nie; der Turn läuft in den Timeout.
- **Ursache:** Der Nutzer hat clarify-Popups blockiert.
- **Sollverhalten:** Rückfragen IMMER inline im Chat, kurz, mit konkreten Optionen; kommt im selben
  Turn keine Antwort, mit sicherem Default weiterarbeiten, nicht nachfassen. Ausnahme: rechtlich
  tragende Aussage (Therapieverzicht/Reanimationsverzicht).
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` („Rueckfragen: inline im Chat, nie Popup");
  `memories/MEMORY.md` — „Nutzer hat clarify-Popups blockiert".

### PIT-42 — Widersprüchliche Nutzerantwort wird sofort umgesetzt
- **Symptom:** Knappe Antwort im Widerspruch zum klaren Material („verlegung" vs. Entlassung am OP-Tag)
  stellt die Briefart um.
- **Ursache:** Antwort kann Fehleingabe sein.
- **Sollverhalten:** Kurze Bestätigungs-Rückfrage mit Optionen; die letzte Nutzeraussage ist maßgeblich.
  Kein Datum geliefert („lass es XXX") → Platzhalter `XXX`, nicht weiter nachfragen.
- **Provenienz:** `stolperfallen/SKILL.md` („Missverständliche Nutzerantworten auf Rückfragen",
  Fall [anonymisiert], 09.09.2026).

### PIT-43 — Anamnese/KU nicht als distilled insights
- **Symptom:** Aufnahmeanamnese und KU sind lang und enthalten Negativ-Anamnese ohne Verlaufskonsequenz.
- **Ursache:** Vollständigkeit statt Destillat.
- **Sollverhalten:** Anamnese max. 2 Sätze, KU 1–2 Sätze (diagnoseführender Befund + wegweisende
  Ausschlussbefunde), Pflichtsatz bleibt; nicht aufnehmen: Negativ-Anamnese ohne Konsequenz,
  Vorbehandlungsdetails, normale Einzelbefunde.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` („Aufnahme-Anamnese und KU als distilled
  insights", Nutzeranweisung 10.09.2026) — „das ist sehr gut".

### PIT-44 — Nutzerfassung wird nicht als maßgeblich übernommen
- **Symptom:** Der Nutzer strafft den Brief; das System regeneriert die Langfassung oder fügt
  Gestrichenes wieder ein.
- **Ursache:** LLM „verbessert" zurück.
- **Sollverhalten:** Schickt der Nutzer eine überarbeitete Fassung zurück, ist diese maßgeblich;
  gestrichene Inhalte nicht wieder einfügen; Feinschliff nur auf der Nutzerversion; bereits gelieferte
  Fassung nicht nachträglich regenerieren („diesmal nicht wieder regenerieren").
- **Provenienz:** `stolperfallen/SKILL.md` („Humanizer-Feinschliff"); log — „Gestrichene Inhalte …
  nicht wieder einfügen".

### PIT-45 — Nutzer-Straffung wird als Regel übernommen (Ausnahmen missverstanden)
- **Symptom:** Ein einmalig weggelassener KU wird dauerhaft weggelassen.
- **Ursache:** Einzelfall-Streichung wird verallgemeinert.
- **Sollverhalten:** Einzelne Streichungen sind AUSNAHMEN, keine Regeln; KU bleibt Regelbestandteil,
  Empfehlungs-/Diagnose-/Nebenerkrankungen-/Therapieblöcke bleiben.
- **Provenienz:** `stolperfallen/SKILL.md` (Fall [anonymisiert], 28.09.2026) — „es tut mir leid die
  verwirrung".

### PIT-46 — Antwort an den Nutzer zu lang / mit Sonderzeichen
- **Symptom:** Tabelle, Emojis, Häkchen-/Warnsymbole, gedruckte Gedankenstriche in einer Rückfrage.
- **Ursache:** LLM-Standardantwort.
- **Sollverhalten:** Nicht-Brief-Ausgaben: einfache Prosa-Zeilen, Ergebnis zuerst, maximal drei
  Begründungszeilen; keine Tabellen, keine Emojis, keine Sonderzeichen; Antwortsprache = Sprache des
  Nutzers (ägyptisches Arabisch), deutsche Fachbegriffe in Lateinschrift. Auf „kürzer" sofort kurze
  Prosa-Fassung liefern.
- **Provenienz:** `stolperfallen/SKILL.md` („Antworten an den Nutzer: kurz und ohne Sonderzeichen",
  Nutzerkorrektur 14.09.2026) — „اختصري الرد".

### PIT-47 — Nutzer beanstandet „zu viel": einzelne Sätze werden gestrichen
- **Symptom:** Der Brief wird als „zu viel" beanstandet; das System kürzt punktuell.
- **Ursache:** Falsche Kürzungsstrategie.
- **Sollverhalten:** Brief neu auf das Destillat verdichten (5 kurze Absätze → Diagnoseliste/
  Therapie-Maßnahmen), nicht einzelne Sätze streichen; Langfassung nicht erneut ausgeben.
- **Provenienz:** `stolperfallen/SKILL.md` („Kurzfassung auf Nutzerwunsch", Präzedenz 10.09.2026).

### PIT-48 — Fachlich fragliche Nutzerformulierung wird stillschweigend im Archiv „korrigiert"
- **Symptom:** Der Nutzer schreibt „ABI 1,0, damit pAVK ausgeschlossen"; das System ändert das im Archiv.
- **Ursache:** Klinische Korrektur an falscher Stelle.
- **Sollverhalten:** Nutzerformulierung im Archiv belassen; die Richtigstellung (ABI bei Mediasklerose
  nicht verwertbar) gehört als kurze Prosa in die Chat-Antwort.
- **Provenienz:** `stolperfallen/SKILL.md` („Nutzerfassung einer Zusammenfassung ist maßgeblich").

### PIT-49 — Empfehlungsblock bei Verlegungsbrief ausgegeben
- **Symptom:** Ein Verlegungsbrief endet mit „ambulante Therapieempfehlungen nach der Entlassung:".
- **Ursache:** Entlassbrief-Struktur blind angewandt.
- **Sollverhalten:** Verlegungsbrief: keine Therapie-Maßnahmen-Liste, kein Empfehlungsblock; Verlegungs-
  satz statt Entlasssatz; Zielklinik `XXX`, wenn nicht genannt.
- **Provenienz:** `stolperfallen/SKILL.md` („Verlegungsbrief mit ungenannter Zielklinik");
  `skills/medizin/schreibdienst/SKILL.md` (Verlegungsbericht-Präzedenz 19.09.2026).

---

## E. Medikationsplan, Musterbrief-Archiv, Sonstiges

### PIT-50 — Medikationsplan wird als PDF/Datei ausgegeben
- **Symptom:** Ein PDF- oder HTML/Markdown-Export der Entlassmedikation.
- **Ursache:** LLM will „exportieren" wörtlich nehmen.
- **Sollverhalten:** KEIN PDF und KEIN Dateiexport — nur die zu ändernden Zeilen als Text im Chat
  (knapp, zeilenweise, copy-paste-fähig); ein Druck-PDF auch nicht „nur zur Ansicht" anbieten.
- **Provenienz:** `skills/medizin/entlassmedikationsplan/SKILL.md` (Nutzerpräferenz/Präzedenz
  10.09.2026, Fall [anonymisiert]) — „keine pdfs". `memories/MEMORY.md` bestätigt die Präzedenz.

### PIT-51 — Dosisabweichung im Medikationsplan stillschweigend aufgelöst
- **Symptom:** Eine der zwei Zahlenwerte wird kommentarlos gewählt.
- **Ursache:** Harmonisierungswunsch.
- **Sollverhalten:** NIE stillschweigend wählen; inline rückfragen, sonst dokumentierten Verlaufswert
  übernehmen und die Abweichung sichtbar als Prüfhinweis in die Zeile schreiben.
- **Provenienz:** `skills/medizin/entlassmedikationsplan/SKILL.md` (Ablaufschritt 3).

### PIT-52 — Musterbriefe werden erst nach dem Schreiben geprüft
- **Symptom:** Nutzer fragt: „Hast du vor dem Schreiben die Musterbriefe gelesen?"
- **Ursache:** Falsche Reihenfolge.
- **Sollverhalten:** Musterbriefe VOR dem Textentwurf prüfen (Rohtext analysieren → Diagnosen →
  Musterbriefe suchen → fehlende anlegen → Text schreiben → danach Sektionen ergänzen).
- **Provenienz:** `stolperfallen/SKILL.md` („Musterbriefe vor dem Schreiben prüfen").

### PIT-53 — Fallbeispiel wird im Musterbrief angelegt
- **Symptom:** Ein neuer Abschnitt „## Fallbeispiel" mit Patientennamen erscheint im Musterbrief.
- **Ursache:** Überholte Archiv-Gewohnheit.
- **Sollverhalten:** Musterbriefe enthalten ausschließlich Klinik/Diagnostik/Therapie/Nachsorge (bei
  Neuanlagen zusätzlich `## Quellen`); keine Fallbeispiele, keine Patientennamen/-daten, kein Fallnarrativ.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` (Nutzerentscheidung 02.10.2026, verbindlich).

### PIT-54 — Duplikat-Musterbrief durch engen Datei-Glob
- **Symptom:** `Bridenileus*` liefert 0 Treffer, obwohl `Duennndarmileus_Bridenileus.md` existiert.
- **Ursache:** Zusammengesetzte Dateinamen; search_files-Limit schneidet Liste ab.
- **Sollverhalten:** Vor Neuanlage `index.md` konsultieren und/oder breit suchen (`*ileus*`); bei 80+
  Musterbriefen gezielt nach Stichwort suchen statt Gesamtliste scannen; Synonyme/Oberbegriffe prüfen.
- **Provenienz:** `stolperfallen/SKILL.md` („Achtung zusammengesetzte Dateinamen").

### PIT-55 — Umlaut-/Truncation-Fallen bei der Archivpflege
- **Symptom:** `grep "entwurf"` findet „Entwürfe" nicht; `read_file` kürzt lange Einzelzeilen.
- **Ursache:** ASCII vs. Umlaute; read_file-Truncation trotz `truncated: false`.
- **Sollverhalten:** Bei deutschen Begriffen beide Formen suchen (`entwurf\|entwürf`); lange Einzelzeilen
  vor einem write_file per `sed -n '<Zeile>p'` sichern; Sektions-Anhang per patch mit Anker.
- **Provenienz:** `stolperfallen/SKILL.md` („Lange Einzeiler im Quellmaterial vollständig sichern");
  `references/musterbrief-patch-technik.md`.

### PIT-56 — Zähler-Drift in index.md / Bundle-Index
- **Symptom:** Frontmatter-Zähler passt nicht zu den Listeneinträgen.
- **Ursache:** Zähler an zwei Stellen, eine nicht nachgezogen.
- **Sollverhalten:** Zähler doppelt pflegen (musterbriefe/index.md-Frontmatter UND Bundle-Index);
  nach jeder Änderung beide synchron; Einträge real zählen statt „alter Wert + 1".
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` („Musterbrief-Zaehler doppelt pflegen");
  `references/musterbrief-archiv-pflege.md` („Index-Zaehler-Drift").

### PIT-57 — Neuer Musterbrief ohne `## Quellen`
- **Symptom:** Neuanlage ohne Quellenliste.
- **Ursache:** Recherche-Schritt übersprungen.
- **Sollverhalten:** Bei Neuanlage Web-Recherche (AMBOSS/DocCheck/PubMed/AWMF) und die benutzten
  Quellen als Linkliste in `## Quellen` am Dateiende führen; nichts erfinden.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` („Web-Recherche bei Neuanlage",
  Nutzerwunsch 02.10.2026); `memories/MEMORY.md`.

### PIT-58 — log.md wird fortgeschrieben
- **Symptom:** Ein neuer Änderungsprotokoll-Eintrag in `/workspace/schreibdienst/log.md`.
- **Ursache:** Überholte Anweisung aus älteren Skills.
- **Sollverhalten:** KEINE Log-Einträge — die Datei bleibt unangetastet; Archiv-Pflege = Musterbrief-
  Sektionen + index.md.
- **Provenienz:** `skills/medizin/schreibdienst/SKILL.md` („Kein Aenderungsprotokoll mehr",
  Nutzerentscheidung 15.09.2026, verbindlich).

### PIT-59 — Rote-Hand-Brief-Behauptung aus dem Gedächtnis
- **Sollverhalten:** Nie aus dem Gedächtnis bejahen/verneinen; vorher verifizieren (BfArM + Gelbe Liste).
  Beispiel: Clindamycin hat KEIN Rote-Hand-Brief (Stand 08/2026); häufig mit Fluorchinolon- oder
  Tigecyclin-RHB verwechselt.
- **Provenienz:** `skills/medizin/klinische-pharmakologie/SKILL.md`.

### PIT-60 — Ablehnungsbogen: ganzes Formular nachgebaut statt Feldtexte
- **Symptom:** Output enthält Seitenaufteilung, Kopf-/Patientendaten-/Unterschriftsblöcke.
- **Ursache:** Formular wird rekonstruiert.
- **Sollverhalten:** Nur die Textbausteine in Feldreihenfolge als Plain-Text (Maßnahme, Dringlichkeit,
  Komplikationen, finanzielle Folgen, Zustand, sonstige Anmerkungen); Komplikationen diagnose-spezifisch
  (nicht „Verschlechterung"); Standardformulierung der finanziellen Folgen nie weglassen; keine
  erfundenen Diagnosen, Platzhalter setzen; Druckdatum nie überschreiben.
- **Provenienz:** `skills/medizin/ablehnungsbogen-thieme-compliance/SKILL.md` (Nutzerkorrektur
  04.09.2026, Fall [anonymisiert]).
