---
asset: briefato-brain/dokumenttypen/weiterbildung-kv-nachweise
brain_version: 1.0.0
typ: weiterbildung-kv-nachweise (Rechts-/Nachweisberatung)
aliases: [wbo, kv-genehmigung, weiterbildung, logbuch, qs-vereinbarung, ultraschallvereinbarung, nachweise]
language: de (meta: en)
---

# Playbook: Weiterbildung / KV-Nachweise (Rechtsauuskunft)

Kein Brieftext — dies ist ein **Auskunftstyp**. Die Antwort ist eine kurze Prosa-Beratung in der Sprache
des Nutzers.

## Trigger
- Fragen zu Weiterbildungsnachweisen, Fallzahlen, Logbuch/eLogbuch, WBO-Richtzahlen.
- Fragen zu KV-Genehmigung, QS-Vereinbarungen (§ 135 Abs. 2 SGB V, z. B. Ultraschalldiagnostik),
  Antragsunterlagen, Vordrucken, Kolloquium.
- „Was ist dieses KBV-/KV-Dokument?" / „Was muss ich tun, damit das zählt?"
- Dokumentationspflichten bei Befunden.

## Erforderliche Bausteine IN DIESER REIHENFOLGE
1. **Einordnung** — WAS ist das Dokument (Rechtsquelle / Vordruck / Bescheid), für wen gilt es, wer prüft es.
   - Beispiel: „Die KBV-Ultraschallvereinbarung ist Rechtstext, kein Formular; die Vordrucke kommen von deiner KV."
2. **Fundstelle** (§, Abs., Anlage, Name des KV-Vordrucks).
   - Beispiel: „§ 14 Abs. 3 Buchst. d der Ultraschall-Vereinbarung nennt vier Zeugnis-Pflichtinhalte."
3. **Konkrete Handlungsliste** (nummeriert, „was du ab heute tust").
   - Beispiel: „1. Pro Sono Datum, Patienten-ID, Anwendungsbereich und Modus mitschreiben. 2. Zeugnis mit
     Zahlen je Anwendungsbereich UND Modus einholen. 3. Ausbilderqualifikation nach § 8 verifizieren."
4. **Offene Variable am Ende klar benennen** (z. B. Bundesland), statt sie stillschweigend anzunehmen.

## Pflichtinhalte
- Drei Ebenen strikt trennen: (1) Weiterbildung/Landesärztekammer (WBO), (2) KV-Genehmigung (ambulant),
  (3) Klinikdokumentation (§ 630f BGB).
- Nur belegte Zahlen/Fristen/Formularnamen nennen; Primärquellen zitieren (§, Abs., Anlage).
- WBO-Richtzahl ≠ KV-Mindestzahl — beide vergleichen, nicht unterstellen.
- Sammelzahlen sind unbrauchbar („keine >, und, einschließlich, oder-Auflistungen"); Zahlen je
  Anwendungsbereich UND Anwendungsmodus getrennt.
- Zeugnis-Pflichtinhalte nach § 14 Abs. 3 Buchst. d (inkl. Zahl der pathologischen Befunde).

## Verbotene Inhalte
- Keine Zahlen/Fristen/Formularnamen erfinden.
- Keine Tabellen/Emojis/Sonderzeichen-Girlanden in der Chat-Antwort.
- Keine Architektur-Vorlesung; der Nutzer ist Chirurg.
- Kein Vermischen der drei Ebenen.
- Keine Mermaid-Diagramme ohne Auftrag.

## Ausgabeformat
- Kurze Prosa-Zeilen, Ergebnis zuerst, höchstens drei Begründungszeilen.
- Sprache des Nutzers (ägyptisches Arabisch); Paragrafen/Gesetzesnamen/Formularnamen/Fachbegriffe Deutsch in
  Lateinschrift.
- Nummerierte Handlungsliste am Ende.
- Lokal vorhandene Vordrucke/PDFs als MEDIA-Pfad anhängen.

## Pitfalls
- **„Datei gefunden = Formular gefunden"** — amtliche Rechtsquelle ist oft kein Vordruck; Dokumenttyp zuerst
  benennen und sagen, was es *nicht* ist.
- **Logbuch-Zahl ungeprüft als KV-Nachweis verkaufen** (WBO-Zahl kann unter der Anlage-I-Zahl liegen).
- **Fassungsstand ignorieren** — QS-Vereinbarungen werden neu gefasst.
- **Vordrucke bei der falschen Stelle suchen** — immer bei der KV des Nutzers (Landesrecht).

## Provenienz
- `skills/medizin/weiterbildung-kv-nachweise/SKILL.md` + references (kbv-ultraschallvereinbarung, wbo-richtzahlen,
  kv-hessen-formulare).
- `skills/medizin/kv-genehmigung-und-weiterbildung/SKILL.md` (Wissensbank, Antwortformat).
