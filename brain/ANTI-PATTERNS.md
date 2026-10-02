# ANTI-PATTERNS – Was die generische LLM-Policy tut, die Mohamed NICHT will

Liste der konkreten Verhaltensweisen, die ein generisches LLM/Standard-Prompt produziert und die der
Arbeitgeber in der Schreibdienst-Praxis ausdrücklich abgelehnt hat. Jeder Eintrag nennt das
generische Fehlverhalten und die Regel, die es ersetzt (Verweis auf `regeln-aus-praxis.md` P… und
`stolperfallen.md` PIT-…). Nur belegte Anti-Patterns.

---

### AP-01 — Einleitung und Schluss anhängen
- **Was das generische LLM tut:** Beginnt mit „Wir berichten über o. g. Patienten…" und endet mit
  einer Zusammenfassung/Floskel („Zusammenfassend lässt sich sagen…").
- **Ersatzregel:** P2 / PIT-01 — keine Einleitung, kein Schluss; direkt mit der Situation beginnen.
- **Provenienz:** `SOUL.md` — „Kein Einleitung oder Schluss".

### AP-02 — Markdown-Formatierung
- **Was das generische LLM tut:** Setzt `**fett**`, `#`-Überschriften, Bullet-Listen, Codeblöcke.
- **Ersatzregel:** P1 / PIT-02 — reiner Plain-Text, copy-paste-fähig, letzte Antwort nur Text.
- **Provenienz:** `schreibdienst/SKILL.md` (Regel 1).

### AP-03 — Sektions-Labels im Fließtext
- **Was das generische LLM tut:** Gliedert den Brief in „Anamnese:", „KU:", „Diagnostik:", „Therapie:".
- **Ersatzregel:** P17 / PIT-03 — ein durchgehender Erzähltext, keine Kategorie-Labels.
- **Provenienz:** `schreibdienst/SKILL.md` (Regel 2).

### AP-04 — Betreffzeile / Titel über dem Brief
- **Was das generische LLM tut:** Stellt eine Überschrift wie „# Entlassbrief" oder „Betreff:" voran.
- **Ersatzregel:** P1 / PIT-02 — keine Überschrift; die einzige Ablage sind die Musterbriefe, keine
  Entwurfsdateien.
- **Provenienz:** `schreibdienst/SKILL.md` (Ablauf Schritt 7) — „ohne Ueberschrift".

### AP-05 — Diagnosen am Anfang oder ohne Beschriftung
- **Was das generische LLM tut:** Setzt die Diagnoseliste nach oben oder lässt die Zeile „Diagnosen:"
  weg.
- **Ersatzregel:** P3/P4/P6 / PIT-04 — Diagnosen am Ende, Zeile „Diagnosen:";
  „Z.n. <OP>"-Zeilen entfallen.
- **Provenienz:** `SOUL.md` — „am Ende bitte deine Diagnosen einlisten"; `schreibdienst/SKILL.md`
  (Regel 4).

### AP-06 — Erklär- und Disclaimer-Sätze einbauen
- **Was das generische LLM tut:** Ergänzt Hinweise wie „Bitte ärztlich prüfen" oder
  „Dies ersetzt keine ärztliche Beratung" im Dokument.
- **Ersatzregel:** P2 / PIT-01 — kein Zusatz im Ausgabetext; Rückfragen/Hinweise gehören als kurze
  Prosa in den Chat, nicht in den Brief.
- **Provenienz:** `schreibdienst/SKILL.md` (Stil) — „Keine ueberfluessigen Erklaerungen".

### AP-07 — Befunde ausschreiben statt komprimieren
- **Was das generische LLM tut:** Gibt den Radiologiebefund vollständig wieder (Wanddicken, EDD, E/A,
  jedes Gefäßsegment, Normalbefunde).
- **Ersatzregel:** P23/P27 / PIT-10 — max. 2 Sätze pro Untersuchung, Kernaussage + ein Nebenbefund.
- **Provenienz:** `stolperfallen/SKILL.md` — „Keine vollständige Befundwiedergabe".

### AP-08 — Findings erfinden / Lücken füllen
- **Was das generische LLM tut:** Vervollständigt fehlende Befunde („Das CCT zeigte keinen Anhalt…"),
  erfindet ein Konsilergebnis oder einen KU.
- **Ersatzregel:** P32 / PIT-37/PIT-38/PIT-39 — nur Belegtes; Lücken offen lassen, Placeholder `XXX`.
- **Provenienz:** `kis-export-luecken.md` — „Lücken werden nicht mit Erfundenem gefüllt."

### AP-09 — Diagnosen hinzufügen, die nicht belegt sind
- **Was das generische LLM tut:** Leitet aus einer geplanten Maßnahme eine Diagnose ab oder übernimmt
  eine radiologisch ausgeschlossene Diagnose in die Liste.
- **Ersatzregel:** P31/P33 / PIT-19/PIT-20 — keine Diagnose erfinden; ausgeschlossene Diagnosen nur
  im Verlauf.
- **Provenienz:** `stolperfallen/SKILL.md` — „Keine Diagnosen erfinden".

### AP-10 — Datumsgesteuertes Aufzählen statt Erzählung
- **Was das generische LLM tut:** Listet Visiten mit Datum auf („Am 03.09.: … Am 04.09.: …").
- **Ersatzregel:** P8 / PIT-07 — Visiten in den Verlauf einweben, konnektive Zeitangaben.
- **Provenienz:** `schreibdienst/SKILL.md` (Regel 3 und 7).

### AP-11 — Diktatfehler markieren
- **Was das generische LLM tut:** Schreibt „[sic]", setzt das korrigierte Wort in Anführungszeichen
  oder kommentiert den Fehler.
- **Ersatzregel:** P38 / PIT-25 — stillschweigend korrigieren; unverständliche Passagen weglassen.
- **Provenienz:** `diktat-tippfehler/SKILL.md` — „Niemals auf den Fehler hinweisen oder ‚sic'
  vermerken."

### AP-12 — Umgangssprache / „humanisieren" als Tonwechsel
- **Was das generische LLM tut:** Macht den Brief bei „/humanizer" umgangssprachlich/persönlich.
- **Ersatzregel:** P2/P1 — nur de-AI-Feinschliff: Doppelungen/Passiv glätten, Floskeln streichen; kein
  Umgangston.
- **Provenienz:** `stolperfallen/SKILL.md` — „wird dabei NICHT umgangssprachlich oder persönlich".

### AP-13 — Semikolons als Standard-Verbindung
- **Was das generische LLM tut:** Verkettet mehrere Aussagen mit `;`.
- **Ersatzregel:** P7 / PIT-06 — höchstens ein Semikolon pro Brief.
- **Provenienz:** `stolperfallen/SKILL.md` — „Richtwert höchstens ein Semikolon pro Brief".

### AP-14 — Abkürzungen ausschreiben oder glätten
- **Was das generische LLM tut:** Schreibt „Computertomographie (CT)", macht aus „ABW"
  „Abwehrspannung" oder aus „NFA" „Notaufnahme"/„ZNA".
- **Ersatzregel:** P10/P11 / PIT-09 — Verzeichnis-Abkürzungen direkt, Nutzer-Abkürzungen verbindlich.
- **Provenienz:** `schreibdienst/SKILL.md` (Abkürzungsverzeichnis); log — „muss immer genutzt werden".

### AP-15 — Vorsichts-Dosierungsanpassung
- **Was das generische LLM tut:** „Korrigiert" eine unmögliche Dosis (7,5 g → 7,5 mg) stillschweigend.
- **Ersatzregel:** P35 / PIT-14 — Substanz ohne Dosis, Inline-Hinweis, `XXX`.
- **Provenienz:** `stolperfallen/SKILL.md` — „jede Umrechnung wäre geraten".

### AP-16 — Pflege-Rauschen übernehmen
- **Was das generische LLM tut:** Übernimmt „zur Nacht versorgt", „meldet sich bei Bedarf", „sonst
  keine Besonderheiten".
- **Ersatzregel:** P28/P29 / PIT-21/PIT-22 — auf klinisch Relevantes filtern, Jargon entschlüsseln.
- **Provenienz:** `pflegeberichte-integration/SKILL.md` (Nicht übernehmen).

### AP-17 — Formulare/Dokumente nachbauen
- **Was das generische LLM tut:** Baut beim Ablehnungsbogen das ganze Formular (Seite 1/2,
  Unterschriftsblöcke) oder beim Medikationsplan eine PDF/Datei nach.
- **Ersatzregel:** P58/P63 / PIT-50/PIT-60 — nur die auszufüllenden Textbausteine als Plain-Text.
- **Provenienz:** `ablehnungsbogen-thieme-compliance/SKILL.md`; `entlassmedikationsplan/SKILL.md` —
  „keine pdfs".

### AP-18 — Nutzer-Formatwünsche nicht als verbindlich behandeln
- **Was das generische LLM tut:** Regeneriert eine bereits gelieferte Fassung oder fügt gestrichene
  Inhalte wieder ein.
- **Ersatzregel:** P52 / PIT-44 — Nutzerfassung ist maßgeblich; nicht nachträglich regenerieren.
- **Provenienz:** `stolperfallen/SKILL.md` — „Gestrichene Inhalte … nicht wieder einfügen".

### AP-19 — Rückfrage-Popup statt Chat
- **Was das generische LLM tut:** Stellt Rückfragen, die im Popup/Timeout versanden.
- **Ersatzregel:** P50 / PIT-41 — inline im Chat, knapp, mit Optionen; sonst sicherer Default.
- **Provenienz:** `memories/MEMORY.md` — „Nutzer hat clarify-Popups blockiert".

### AP-20 — Lange, dekorierte Chat-Antworten
- **Was das generische LLM tut:** Antwortet auf Rückfragen mit Tabellen, Emojis, Häkchen/Warnsymbolen
  und langen Erklärungen.
- **Ersatzregel:** P53 / PIT-46 — kurze Prosa, Ergebnis zuerst, keine Sonderzeichen, Nutzersprache.
- **Provenienz:** `stolperfallen/SKILL.md` — „اختصري الرد".

### AP-21 — Ausgeschlossenes mit Bestätigtem mischen
- **Was das generische LLM tut:** Führt dieselbe Diagnose einmal als V.a./ausgeschlossen und einmal
  als bestätigt, oder lokalisiert widersprüchlich.
- **Ersatzregel:** P25/P33/P41 / PIT-12/PIT-20/PIT-32 — präziserer, späterer Befund führt; keine
  Doppelführung.
- **Provenienz:** `stolperfallen/SKILL.md` — „eine fehlerhafte Erstangabe wird ersetzt, nicht doppelt
  geführt".

### AP-22 — Fallbeispiele mit Patientennamen im Archiv anlegen
- **Was das generische LLM tut:** Legt im Musterbrief einen Abschnitt „## Fallbeispiel" mit Namen und
  Falldaten an.
- **Ersatzregel:** P43/P44 / PIT-53 — nur generische Sektionen Klinik/Diagnostik/Therapie/Nachsorge
  (+Quellen), keine Fallbeispiele.
- **Provenienz:** `schreibdienst/SKILL.md` — „Abschnitte ‚Fallbeispiel' werden NICHT mehr angelegt".

### AP-23 — Identität aus dem Nachnamen annehmen
- **Was das generische LLM tut:** Übernimmt Alt-Diagnosen/Allergien aus einem früheren Fall mit
  demselben Nachnamen.
- **Ersatzregel:** P32 / PIT-34 — Nachname allein ist kein Nachweis; nur der gelieferte Text, inline
  nachfragen.
- **Provenienz:** `stolperfallen/SKILL.md` — „ist das KEIN Identitätsnachweis".

### AP-24 — Änderungsprotokoll / Diagnose-Extradateien schreiben
- **Was das generische LLM tut:** Legt Entwurfsdateien an oder ergänzt `log.md`.
- **Ersatzregel:** P48 / PIT-58 + PIT-52 — keine Log-Einträge, keine Entwurfsdateien; die einzige
  Ablage sind die Musterbriefe.
- **Provenienz:** `schreibdienst/SKILL.md` — „Es werden KEINE Entwurfsdateien angelegt";
  „Der Nutzer will KEINE Log-Eintraege".

### AP-25 — Rote-Hand-Brief aus dem Gedächtnis beantworten
- **Was das generische LLM tut:** Behauptet/verneint einen Rote-Hand-Brief ohne Prüfung.
- **Ersatzregel:** P62 / PIT-59 — immer verifizieren (BfArM + Gelbe Liste).
- **Provenienz:** `klinische-pharmakologie/SKILL.md` — „NIE aus dem Gedächtnis bejahen oder verneinen".
