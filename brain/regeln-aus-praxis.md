# Regeln aus der Praxis (P1…Pn) – Briefato

Abgeleitet aus dem Hermes-Schreibdienst-Profil: Skills, `memories/MEMORY.md`/`USER.md`,
`/workspace/schreibdienst/log.md`, `/workspace/schreibdienst/index.md`. Jede Regel ist EIN Satz und
trägt eine Provenienz (Datei + kurzes Zitat). Keine erfundenen Regeln — nur belegbare.
`[anonymisiert]` = Patientennamen entfernt. Querverweis in Klammern auf die Stolperfalle in
`stolperfallen.md`.

---

## A. Ausgabe (jeder Brief)

**P1.** Ausgabetexte werden als reiner Plain-Text ohne Markdown, Überschriften, Fettung oder
Aufzählungszeichen geliefert; die letzte Antwort enthält nur den fertigen Text. (PIT-02)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „Reiner Text - keine Fettung, keine
Kursivsetzung, keine Ueberschriften".

**P2.** Der Brief beginnt ohne Einleitung und endet ohne Schlussfolgerung/Floskel. (PIT-01)
Provenienz: `SOUL.md` — „Kein Einleitung oder Schluss".

**P3.** Diagnosen stehen am Ende als einfache Liste, eingeleitet durch die Plain-Text-Zeile
„Diagnosen:". (PIT-04)
Provenienz: `SOUL.md` — „am Ende bitte deine Diagnosen einlisten"; `schreibdienst/SKILL.md` —
„Diagnoseliste am Ende".

**P4.** Bei stationären Entlassbriefen steht VOR der Diagnoseliste der Empfehlungsblock
„ambulante Therapieempfehlungen nach der Entlassung:" in EINEM Absatz, darunter „Nebenerkrankungen:"
und danach „Therapie-Maßnahmen auf der Station:". (PIT-05)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 4) — „der mit ‚ambulante
Therapieempfehlungen nach der Entlassung:' beschriftete Empfehlungsblock".

**P5.** Bei fehlenden Komorbiditäten führt der Block „Nebenerkrankungen:" nur das Wort „keine".
(PIT-05)
Provenienz: `stolperfallen/SKILL.md` — „führt der Block nur das Wort ‚keine'".

**P6.** Aufgabenhöfe „Z.n. <OP>" entfallen in der Diagnoseliste; Operationen erscheinen ausschließlich
als „OP am TT.MM.JJJJ: <Eingriff>"-Zeilen im Therapieblock. (PIT-04/PIT-05)
Provenienz: `stolperfallen/SKILL.md` — „Die ‚Z.n. <OP>'-Zeilen entfallen in der Diagnoseliste".

**P7.** Das Semikolon wird höchstens einmal pro Brief verwendet, im Zweifel gar nicht. (PIT-06)
Provenienz: `stolperfallen/SKILL.md` — „Richtwert höchstens ein Semikolon pro Brief".

**P8.** Im Verlaufstext stehen keine Datumsangaben, nur konnektive Zeitangaben; OP- und Entlassdatum
sind die einzigen Datums-Ausnahmen, fehlende Daten werden als `XXX` gesetzt. (PIT-07)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 7) — „Keine Datumsangaben im Verlauf".

**P9.** Ausgaben tragen korrekte deutsche Umlaute und ß; ae/oe/ue/ss sind unzulässig. (PIT-08)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 0) — „immer mit korrekten deutschen
Umlauten und ß".

**P10.** Medizinische Abkürzungen aus dem Verzeichnis werden direkt verwendet, ohne ausgeschriebene
Erstnennung mit Klammerabkürzung. (PIT-09)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 5) — „Keine ausgeschriebene Erstnennung
mit Klammerabkuerzung".

**P11.** Gelernte Nutzer-Abkürzungen sind verbindlich und werden immer genutzt, nicht geglättet oder
ausgeschrieben: NFA (statt ZNA), ABW, Nausea, ITS, OSAS, HWI, HÄ, ged. perf., Miktion.
(PIT-09)
Provenienz: `/workspace/schreibdienst/log.md` — „muss immer genutzt werden".

**P12.** Exitus-letalis-Briefe enden nach dem klinischen Verlauf, vor der Diagnoseliste, mit der
vorgegebenen Schlussformel. (PIT-01)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 8) — „Der Tod trat im Rahmen von … ein".

---

## B. Struktur / Briefart / Triage

**P13.** Rohmaterial ohne Auftragskennung erzeugt den stationären Brief (schreibdienst, Default);
„Zusammenfassung" den Zusammenfassung-Skill; „OP-Bericht" den Operationsbericht; ambulant/tages-
chirurgisch den ambulant-Skill. (PIT-40)
Provenienz: `SOUL.md` — „Rohmaterial / ‚nichts' gesagt → schreibdienst (Default)";
`schreibdienst/SKILL.md` (Skill-Auswahl).

**P14.** Endet das Rohmaterial mit klinischer Entlassreife, wird ein ENTLASSBRIEF geschrieben — auch
ohne Entlassungseintrag/Entlassdatum. (PIT-40)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 10) — „ist der Fall als ENTLASSBRIEF zu
schreiben".

**P15.** Läuft der Verlauf erkennbar weiter (geplante OP, ausstehende Diagnostik, keine Auflösung der
Akutsymptomatik), bleibt der Fall ein Aufnahmebrief — Verlauf, CT-Befund und Entlasszustand dürfen
nicht erfunden werden. (PIT-40)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 10).

**P16.** Bei Unsicherheit zur Briefart wird inline im Chat gefragt; kommt keine Antwort, im Zweifel
der Entlassbrief mit Therapie-Maßnahmen-Liste. (PIT-40/PIT-41)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 10) — „im Zweifel den ENTLASSBRIEF … waehlen".

**P17.** Die Reihenfolge Beschwerde → Untersuchung → Diagnose/DD → Behandlung → Verlauf muss im Text
klar durchlaufen, jeder Abschnitt mindestens einen Satz. (PIT-03)
Provenienz: `stolperfallen/SKILL.md` — „Die Kette Beschwerde → Untersuchung → Diagnose/DD →
Behandlung → Verlauf".

**P18.** Wenn der Skill eine Struktur vorgibt, wird sie exakt befolgt; keine eigenen
Gliederungsideen. (PIT-03)
Provenienz: `stolperfallen/SKILL.md` — „Kein Abweichen vom etablierten Schema".

**P19.** Aufnahme-Anamnese und KU werden IMMER auf das Destillat verdichtet (Anamnese max. 2 Sätze,
KU 1–2 Sätze). (PIT-43)
Provenienz: `stolperfallen/SKILL.md` — „IMMER auf das Destillat verdichtet".

**P20.** Der Satz „Wir nahmen den Pat. zur weiteren Diagnostik bzw. Schmerztherapie stationär auf."
ist Pflicht und steht unmittelbar nach dem KU (bzw. nach der Anamnese, wenn kein KU vorliegt). (PIT-39)
Provenienz: `stolperfallen/SKILL.md` — „Dieser Satz … ist nicht optional."

**P21.** Bei ambulanten Fällen entfallen Aufnahmesatz, Therapie-Maßnahmen-Liste und Nebenerkrankungen-
Block ersatzlos. (PIT-40)
Provenienz: `skills/medizin/ambulant/SKILL.md` — „KEIN ‚stationär aufnehmen'-Satz".

**P22.** Bei Verlegung/Übernahme an eine andere Abteilung/Klinik gilt der Verlegungsbrief: kein
Empfehlungsblock, Verlegungssatz statt Entlasssatz, Zielklinik `XXX` wenn nicht genannt. (PIT-49)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „keine Therapie-Massnahmen-Liste, der Verlauf
laeuft in der Zielklinik weiter".

---

## C. Befund-Kompression

**P23.** Alle Untersuchungsbefunde werden auf maximal 2 Sätze reduziert (Kernaussage + ein Satz
fallrelevante Nebenbefunde); keine Normalbefunde. (PIT-10)
Provenienz: `stolperfallen/SKILL.md` — „auf maximal 2 Sätze reduziert".

**P24.** Jede Untersuchung wird im Format Indikation/Fragestellung → Modalität → auffällige Befunde →
explizite Antwort dargestellt, in chronologischer Reihenfolge des Untersuchungsdatums. (PIT-11)
Provenienz: `stolperfallen/SKILL.md` — „Untersuchungsabschnitte: Indikation–Fragestellung-Format
(zwingend)".

**P25.** Bei widersprüchlichen Angaben zwischen Erst- und Folge-Bildgebung folgt der Text dem
präziseren, späteren und konsiliarisch bestätigten Befund; die Erstangabe entfällt ersatzlos. (PIT-12)
Provenienz: `stolperfallen/SKILL.md` — „folgt der Text der präziseren, späteren und konsiliarisch
bestätigten Diagnose".

**P26.** OP-Berichte werden geäußert knapp gehalten: nur die distilled insights (Indikation 1 Satz,
Zugang/Befund/Maßnahme/Drainagen in max. 2 Sätzen). (PIT-23)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Regel 6) — „Aeusserst knapp halten."

**P27.** Echo- und MRA-Befunde werden auf die diagnoseführenden Kernaussagen reduziert (Echo: EF/
Kinetik, Klappen, PASP/TAPSE; MRA: führende Verschlüsse/Stenosen + Beurteilbarkeit). (PIT-10)
Provenienz: `stolperfallen/SKILL.md` — „Echokardiographie-Beispiel: NUR übernehmen: EF/Kernbefund".

**P28.** Pflegeberichte: nur klinisch relevante Beobachtungen werden in den Verlaufstext eingewoben,
nicht als eigener „Pflege"-Abschnitt zitiert. (PIT-21)
Provenienz: `stolperfallen/SKILL.md` — „in den klinischen Verlaufstext eingewoben".

**P29.** KIS-/Pflegejargon wird erst entschlüsselt, dann gefiltert (Viggo, SK, Lasche, Nutriflex,
CA-Visite usw.). (PIT-22)
Provenienz: `stolperfallen/SKILL.md` — „Erst entschlüsseln, dann filtern".

**P30.** Bei „Fieber ohne Fokus" werden die Untersuchungen einzeln in Datumsreihenfolge mit Fragestellung
geführt, nicht zu einem Satz verschmolzen. (PIT-11)
Provenienz: `stolperfallen/SKILL.md` — „Bildgebende Fokussuche bei unklarer Infektion".

**P31.** Ist eine Maßnahme nur geplant, wird sie als geplante Diagnostik/Therapie formuliert — nie als
durchgeführt, nie als Diagnose. (PIT-19/PIT-38)
Provenienz: `stolperfallen/SKILL.md` — „Geplante Maßnahmen nicht als Diagnose festschreiben".

---

## D. Korrektheit / Nicht-Erfinden

**P32.** Nicht belegte Angaben werden nicht erfunden: fehlender KU, Konsilergebnis, Befund einer nur
durchgeführten Untersuchung, Datum, Name, Diagnose. (PIT-37/PIT-38/PIT-39)
Provenienz: `stolperfallen/references/kis-export-luecken.md` — „Lücken werden nicht mit Erfundenem
gefüllt."

**P33.** Ausgeschlossene Diagnosen erscheinen nur als verneinter Ausschlusssatz im Verlauf, niemals in
der Diagnoseliste. (PIT-20)
Provenienz: `stolperfallen/SKILL.md` — „Die ausgeschlossene Diagnose erscheint nur im Verlaufstext".

**P34.** Wird eine V.a.-Diagnose nicht bestätigt und tritt eine andere Genese in den Vordergrund,
bleiben beide in der Diagnoseliste (die V.a.-Diagnose als solche), und beide Musterbriefe werden
ergänzt. (PIT-20)
Provenienz: `stolperfallen/SKILL.md` — „Beide Diagnosen bleiben in der Diagnoseliste".

**P35.** Pharmakologisch unmögliche Dosierungen werden NICHT hochgerechnet — Substanz ohne Dosis,
einmaliger Inline-Hinweis, auf Wunsch `XXX`. (PIT-14)
Provenienz: `stolperfallen/SKILL.md` — „die richtige Zahl ist nicht belegt, jede Umrechnung wäre
geraten".

**P36.** FEV1 < 30 % des Solls = GOLD 4 (nicht GOLD 3). (PIT-15)
Provenienz: `stolperfallen/SKILL.md` — „FEV1 < 30 % des Solls = GOLD 4".

**P37.** 85 % Sättigung ist SpO2, nicht pO2 (mmHg). (PIT-16)
Provenienz: `stolperfallen/SKILL.md` — „niemals ‚pO2 auf 85 %' schreiben".

**P38.** Diktat-/Spracherkennungsfehler werden stillschweigend korrigiert, nicht markiert;
unverständliche Passagen werden ersatzlos weggelassen, nicht geraten. (PIT-25)
Provenienz: `stolperfallen/SKILL.md` — „Nicht auflösbare Passagen ersatzlos weglassen statt raten".

**P39.** Der erklärte Patientenwille darf NICHT ersatzlos entfallen, auch wenn die Abkürzung unklar
ist — inhaltsgleich ausformulieren und bei rechtlich tragendem Willen inline nachfragen. (PIT-36)
Provenienz: `stolperfallen/SKILL.md` — „darf der Inhalt NICHT ersatzlos entfallen".

**P40.** Histologie-Status wird zwingend genannt (bei ausstehendem Ergebnis „Die Histologie steht noch
aus."). (PIT-18)
Provenienz: `stolperfallen/SKILL.md` — „muss der Histologie-Status zwingend im Text erwähnt werden".

**P41.** Bei widersprüchlichen Lokalisationsangaben führt die präzisere, spätere (KU-)Angabe; die
Anamnese bleibt ohne Lokalisation. (PIT-32)
Provenienz: `stolperfallen/SKILL.md` — „die KU-Angabe führt die Lokalisation".

---

## E. Archiv / Musterbriefe

**P42.** Die Musterbriefe werden VOR dem Textentwurf geprüft, nicht nachträglich „eingepflegt".
(PIT-52)
Provenienz: `stolperfallen/SKILL.md` — „Die Musterbriefe werden VOR dem Textentwurf geprüft".

**P43.** Musterbriefe enthalten ausschließlich die Sektionen Klinik, Diagnostik, Therapie und Nachsorge
(bei Neuanlagen zusätzlich `## Quellen`); Abschnitte „Fallbeispiel" werden NICHT mehr angelegt.
(PIT-53)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „ausschliesslich die Sektionen Klinik,
Diagnostik, Therapie und Nachsorge".

**P44.** Neue klinische Erkenntnisse aus einem Fall werden als generische, patientenunabhängige
Aussage in die passende Sektion einsortiert — nur wenn dort noch nicht vorhanden, nichts erfinden.
(PIT-53)
Provenienz: `stolperfallen/SKILL.md` — „als generische, patientenunabhängige Aussage".

**P45.** Bei der Neuanlage eines Musterbriefs wird der Inhalt per Web-Recherche ergänzt/geprüft
(AMBOSS, DocCheck, PubMed/AWMF) und die benutzten Quellen in `## Quellen` geführt. (PIT-57)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „Recherchiert werden Klinik, Diagnostik, Therapie
und Nachsorge der konkreten Entitaet".

**P46.** Vor der Neuanlage eines Musterbriefs wird auf Duplikate geprüft (index.md + breite
Stichwortsuche inkl. Synonyme/Oberbegriffe; deckt ein vorhandener Musterbrief die Entität ab, wird
DIESER erweitert). (PIT-54)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „DEDUPE-CHECK VOR Neuanlage (zwingend)".

**P47.** Der Musterbrief-Zähler wird an BEIDEN Stellen gepflegt (Frontmatter musterbriefe/index.md und
Bundle-Index). (PIT-56)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „Zaehler doppelt pflegen".

**P48.** `/workspace/schreibdienst/log.md` wird nicht mehr fortgeschrieben; kein Log-Eintrag in
irgendeinem Skill. (PIT-58)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „Der Nutzer will KEINE Log-Eintraege".

**P49.** Bei einem bereits gelieferten Brief, der nachträglich korrigiert/komplettiert wird, werden
die Archivsektion und der Brief mitkorrigiert; die überholte Fassung darf nicht stehen bleiben.
(PIT-13)
Provenienz: `stolperfallen/SKILL.md` — „die überholte Fassung darf nicht im Musterbrief stehen bleiben".

---

## F. Nutzerinteraktion / Aufträge

**P50.** Rückfragen werden IMMER inline im Chat gestellt, nie per clarify-Popup; ohne Antwort im
selben Turn wird mit dem sicheren Default weitergearbeitet. (PIT-41)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „Rueckfragen immer als Text im Chat stellen";
`memories/MEMORY.md` — „Rückfragen immer inline im Chat stellen".

**P51.** Bei widersprüchlicher knapper Nutzerantwort wird eine Bestätigungsrückfrage mit konkreten
Optionen gestellt; die letzte Nutzeraussage ist maßgeblich. (PIT-42)
Provenienz: `stolperfallen/SKILL.md` — „Eine kurze Bestätigungs-Rückfrage mit konkreten Optionen
stellen".

**P52.** Eine vom Nutzer selbst überarbeitete Fassung ist maßgeblich; gestrichene Inhalte werden nicht
wieder eingefügt und die bereits gelieferte Fassung nicht nachträglich regeneriert. (PIT-44)
Provenienz: `stolperfallen/SKILL.md` — „ist diese maßgeblich".

**P53.** Nicht-Brief-Antworten (Rückfragen, Erklärungen, Recherche) werden kurz, in einfacher Prosa,
ergebnisorientiert und ohne Tabellen/Emojis/Sonderzeichen gegeben — in der Sprache des Nutzers.
(PIT-46)
Provenienz: `stolperfallen/SKILL.md` — „Keine Tabellen, keine Emojis, keine Sonderzeichen-Girlanden".

**P54.** Beanstandet der Nutzer einen Brief als „zu viel", wird der Brief neu auf das Destillat
verdichtet statt punktuell gekürzt; die Langfassung wird nicht erneut ausgegeben. (PIT-47)
Provenienz: `stolperfallen/SKILL.md` — „NICHT einzelne Sätze streichen und den Rest stehen lassen".

**P55.** Ein kombinierter Auftrag (z. B. „OP-Bericht + Zusammenfassung") liefert BEIDE Fassungen aus
demselben Rohmaterial — nicht eine auswählen, nicht nachfragen. (PIT-40)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` — „beide Fassungen aus demselben Rohmaterial
liefern".

**P56.** Folgt auf einen Zusammenfassungs-Auftrag der Brief zum SELBEN Aufenthalt, wird die bereits
angelegte Musterbrief-Sektion erweitert (kein neuer Musterbrief, kein Zähler-Update). (PIT-52)
Provenienz: `stolperfallen/SKILL.md` — „Sektion erweitern, nicht doppelt anlegen".

**P57.** Fehlt dem Folge-Export ein Baustein aus einem früheren Turn (z. B. das OP-Diktat), wird er
aus dem früheren Turn selbst eingewoben — nicht als Lücke stehen lassen, nicht erfinden, nicht an
einen Subagenten delegieren. (PIT-13)
Provenienz: `skills/medizin/schreibdienst/SKILL.md` (Phase 2) — „diesen Baustein aus dem früheren Turn
selbst in Phase 2 einweben".

---

## G. Sondermodi

**P58.** Ein Medikationsplan-Auftrag liefert KEINE PDF-/Datei-Exporte, sondern nur die zu ändernden
Zeilen als Text im Chat. (PIT-50)
Provenienz: `skills/medizin/entlassmedikationsplan/SKILL.md` — „KEIN PDF und KEIN Dateiexport".

**P59.** Eine Zusammenfassung ist extrem komprimiert (3–4 Sätze, vom Nutzer vorgegebene Satzzahl
bindend) mit abgekürzten Monatsangaben und OHNE Diagnoseliste/Therapieblock. (PIT-19)
Provenienz: `skills/medizin/zusammenfassung/SKILL.md` — „Maximal 4 Sätze … Keine Diagnoseliste am Ende".

**P60.** Der Operationsbericht wird in vollständiger, chronologischer Schritt-für-Schritt-Darstellung
mit Telegrammstil/Passiv und Standard-OP-Schritten geliefert; Diagnosen und Operation stehen am
Dokumentende. (PIT-23)
Provenienz: `skills/medizin/operationsbericht/SKILL.md` — „verbindlich ans Dokumentende".

**P61.** Bei iterativen OP-Korrekturen wird die alte Passage ersetzt, nicht angehängt (keine zwei
Fassungen nebeneinander). (PIT-24)
Provenienz: `skills/op-iterationen/SKILL.md` — „Die entsprechende Passage ersetzen – nicht anhängen".

**P62.** Rote-Hand-Brief-Behauptungen werden nie aus dem Gedächtnis beantwortet, sondern verifiziert
(BfArM + Gelbe Liste). (PIT-59)
Provenienz: `skills/medizin/klinische-pharmakologie/SKILL.md` — „Rote-Hand-Brief-Behauptungen NIE aus
dem Gedächtnis bejahen oder verneinen".

**P63.** Der Ablehnungsbogen wird als reine Feldtexte in Feldreihenfolge ausgegeben (kein
Formular-Nachbau) mit diagnose-spezifischen Komplikationen und der Standardformulierung der
finanziellen Folgen. (PIT-60)
Provenienz: `skills/medizin/ablehnungsbogen-thieme-compliance/SKILL.md` — „NICHT das gesamte Formular
im Output nachbauen".

**P64.** Fachlich fragliche Nutzerformulierungen werden nicht stillschweigend im Archiv „korrigiert";
die Richtigstellung geht als kurze Prosa in die Chat-Antwort. (PIT-48)
Provenienz: `stolperfallen/SKILL.md` — „Fachlich fragliche Nutzer-Formulierungen NICHT stillschweigend
im Archiv korrigieren".
