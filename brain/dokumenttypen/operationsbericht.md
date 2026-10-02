---
asset: briefato-brain/dokumenttypen/operationsbericht
brain_version: 1.0.0
typ: operationsbericht
aliases: [op-bericht, op, operationsbericht]
language: de (meta: en)
---

# Playbook: Operationsbericht

## Trigger
- Der Nutzer fordert einen „OP-Bericht" / „OP-Bericht" — die **ausführliche Schritt-für-Schritt-Darstellung**
  (nicht die knappe OP-Kompression aus `arztbrief`).
- Rohmaterial einer Operation (Diktat oder KIS-OP-Protokoll) liegt vor; Indikation + konkreter Eingriff bekannt.

Abgrenzung: Der OP-Absatz innerhalb eines Arztbriefs wird knapp gehalten (K3.6); dieser Typ ist ausführlich.

## Erforderliche Abschnitte IN DIESER REIHENFOLGE
Erzählabsätze mit Plain-Text-Labels „Indikation:", „OP:", „Präparat:"; Diagnosen/Operation ans Dokumentende.

1. **Indikation** (1. Absatz): Vorstellung des Patienten (Alter, Geschlecht, ggf. relevante
   Vorerkrankungen); Beschwerdebild/Diagnose; Begründung des Eingriffs. Keine Einleitungssätze.
   - Beispiel: „Bei dem 54-jährigen Patienten besteht eine symptomatische Cholezystolithiasis ohne
     Anhalt für eine Gallenwegsobstruktion. Bei symptomatischem Steinleiden erfolgte am 23.09.2026 in
     Intubationsnarkose die geplante laparoskopische Cholezystektomie."
   - Beispiel (KIS-Protokoll): „Bei dem 68-jährigen Patienten wurde am 08.09.2026 die geplante
     Zehenstrahlamputation durchgeführt. Der Patient ist betreut, der Betreuer wurde telefonisch aufgeklärt."
2. **OP** (2. Absatz, ausführlich, chronologisch) — Schritte in dieser Logik, Telegrammstil, Passiv:
   Lagerung & Vorbereitung → Team-Time-out → Zugang → Exploration/Befund → Präparation → Kernschritt →
   Kontrolle & Verschluss.
   - Beispiel: „Die OP erfolgt in Rückenlage. Nach Team-Time-out erfolgt die Hautdesinfektion gefärbt
     sowie die sterile Abdeckung des Abdomens."
   - Beispiel: „Transumbilikaler Hautschnitt und Einbringen des 10-mm-Trokars. Über diesen Trokar Aufbau
     des Capnoperitoneums mit einem Druck bis 12 mmHg."
   - Beispiel: „Abschließende Kontrolle auf intraabdominelle Bluttrockenheit, welche besteht. Wundverschluss
     durch Einzelknopfintrakutannähte mit Caprosyn 4-0, darüber Steri-Strips und sterile Pflaster."
3. **Präparat** (3. Absatz, falls vorhanden): Art des Präparats, Versandart, ggf. Schnellschnittdiagnose.
   - Beispiel: „Gallenblase, Präparat ad Histologie."
4. **Schlussblöcke** — nach dem Schlusssatz die Blöcke „Diagnosen:" (ein Eintrag pro Zeile) und
   „Operation:" anhängen.
   - Beispiel:
     „Diagnosen:
     Symptomatische Cholezystolithiasis
     Umbilikalhernie

     Operation:
     Laparoskopische Cholezystektomie
     Umbilikale Herniotomie und Direktnaht"

## Pflichtinhalte
- Sprachstil: formell-medizinischer Fachjargon, Telegrammstil (Artikel vermeiden, wo möglich), Präferenz
  für Passiv („wird durchgeführt", „erfolgt", „wird dargestellt").
- Standardisierte OP-Schritte ergänzen, wenn sie medizinischer Standard sind (Desinfektion, sterile
  Abdeckung, Team-Time-out, Blutstillung, Wundverschluss, Pflasterverband; bei Laparoskopie zusätzlich
  Capnoperitoneum, Optikeinführung, Trokarplatzierung unter Sicht, Gasablassen).
- Präzise Material-/Instrumentenangaben (Stärken, Fadenmaterial, Trokardurchmesser) — soweit belegt oder
  aus dem Musterbrief ableitbar.
- OP-Datum in der Indikation nennen.
- Diagnosen + Operation am Dokumentende.

## Verbotene Inhalte
- Kein Patientenname im Bericht.
- Keine subjektiven Bewertungen, keine Füllwörter.
- Keine Einleitungssätze wie „Wir stellten den Patienten vor".
- Keine erfundenen patientenindividuellen Situsdetails (Bruchsackgrößen, Lipome, Adhäsionen), wenn nicht belegt.
- Keine Vermischung mit dem knappen Arztbrief-OP-Absatz (K3.6) — der OP-Bericht ist ausführlich.
- Semikolon höchstens einmal, im Zweifel keines.
- Kein Markdown.

## Ausgabeformat
- Reiner Plain-Text, copy-paste-fähig.
- Absätze mit Labels „Indikation:", „OP:", „Präparat:".
- Diagnosen-/Operationsliste am Ende (nicht am Anfang).
- Keine Datumsangaben im OP-Verlauf (außer OP-Datum in der Indikation).

## Pitfalls
- **Kein Veress-Nadel-Zugang** bei laparoskopischer Cholezystektomie (auch nicht, wenn die KIS-Materialliste
  sie als Standardartikel führt) — transumbilikaler 10-mm-Trokar, darüber Capnoperitoneum.
- **Lückenhaftes Rohmaterial:** Technik/Materialien aus dem Musterbrief-Archiv der Abteilung ableiten,
  nicht ad hoc erfinden; Konsistenz mit Entlassbrief/Vorbefunden prüfen (OP-Datum, stationär/ambulant,
  resorbierbares Nahtmaterial → intrakutane Naht, Drainagen).
- **KIS-OP-Protokoll ohne diktiertes Diktat:** Eingriffsart aus dem ICPM-Kode bestimmen (nicht aus dem
  Kurztitel raten); Felddaten übernehmen statt erfinden; Präparat-Text wörtlich; bei fehlender Drainage
  „Auf eine Drainage wird verzichtet."
- **Rückfrage ohne Antwort (Popups erreichen den Nutzer nicht):** Klinikstandard aus dem Musterbrief wählen
  und den Bericht verfassen, statt abzubrechen.
- **Diktatfehlhörer stillschweigend korrigieren** (z. B. „Sableb-Technik"→Sublay-Technik,
  „Artesiolyse"→Adhäsiolyse, „Kumferental"→zirkumferent).

## Provenienz
- `skills/medizin/operationsbericht/SKILL.md` (Struktur, Sprachstil, Qualitätskriterien, Standardschritte,
  Abteilungsstandards lap. CHE / Narbenhernie, Ablauf inkl. Endplatzierung der Listen).
- `skills/medizin/operationsbericht/references/standard-che-laparoskopisch.md` (Nutzerstandard lap. CHE).
- `skills/medizin/operationsbericht/references/standard-narbenhernie-sublay.md` (Nutzerstandard Sublay).
- `skills/medizin/stolperfallen/SKILL.md` (OP auf Wesentliches reduzieren, Diktatfehler OP).
