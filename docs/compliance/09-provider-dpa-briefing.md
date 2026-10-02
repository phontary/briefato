# 09 — Briefing: Anforderungen an den Modell-Provider (DPA/AVV)

Status: **Entwurf — muss bestätigt werden.** Kurzdokument. Grundlagen: Art. 28 + Art. 44–46 DSGVO,
https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); SCC für Verantwortlicher-zu-
Verarbeiter: Durchführungsbeschluss (EU) 2021/915, https://eur-lex.europa.eu/eli/dec_impl/2021/915/oj (abgerufen 2026-10-02).

## 1. Was vom Modell-Provider zu verlangen ist

| # | Anforderung | Warum |
|---|---|---|
| P1 | **AVV/DPA nach Art. 28** unterschriftsreif; Briefato als Verarbeiter, Provider als Unterauftragsverarbeiter | ohne AVV keine rechtmäßige Verarbeitung |
| P2 | **EU-Region** für Verarbeitung und Speicherung (Mistral FR / Azure EU) | vermeidet Drittlandübermittlung |
| P3 | **Kein Training / keine Modellverbesserung** auf unseren Daten; kein „Zurücklernen“ | DSK-KI-TOM; Kern des Vertrauens |
| P4 | **Keine dauerhafte Speicherung** der Prompts (Zero/Low Retention); Löschfristen nennen | Datenminimierung |
| P5 | **Sub-Prozessor-Liste** + Änderungsmitteilung + Widerspruchsrecht | Art. 28 Abs. 2/4 |
| P6 | **Löschung** der Daten nach Auftragsende | Art. 28 Abs. 3 lit. g |
| P7 | **Logs/Audit** transparent (welche Metadaten werden geloggt, wie lange) | Nachweispflicht |
| P8 | **Sicherheitsnachweise** (ISO 27001/SOC 2), Verschlüsselung transit/at rest | TOM-Anlage |
| P9 | **Kein Einsatz von Resellern/Weiterverkauf**; klare Vertragskette | Rollenklarheit |
| P10 | **Benachrichtigung bei Datenschutzverletzungen** an Briefato | Art. 33 Abs. 2 |

## 2. Optionsvergleich

| Option | Drittland? | AVV verfügbar | No-Training | Aufwand | Empfehlung |
|---|---|---|---|---|---|
| **Mistral AI (EU, FR)** | nein | ja | vertraglich zusicherbar | gering | ✅ **erste Wahl** |
| **Azure OpenAI (EU-Region)** | faktisch EU / MS mit US-Bezug | ja (+ EU Data Boundary, SCC/DPF) | zusicherbar | mittel | ✅ tragfähig, mehr Papier |
| **DeepSeek** | **ja (China)** | DPA nur eingeschränkt belastbar | unklar | hoch (SCC + TIA) | ❌ **nicht empfohlen** für Art. 9-Daten |
| **Lokale Inferenz** (eigener Container) | nein | entfällt | voll | hoch (GPU/Betrieb) | 🟡 v1-Non-Goal, Zielbild |

**Realitätscheck DeepSeek:** China hat kein Angemessenheitsbeschluss; es braucht SCC (Art. 46 Abs. 2
lit. c) **und** ein Transfer Impact Assessment. Für besondere Kategorien (Art. 9) ist das
Risiko-/Aufwandsverhältnis schlecht. Die erzwungene Pseudonymisierung (D4) hilft, ist aber **kein
Ersatz** für ein Transferinstrument und derzeit ohnehin **nicht implementiert** (T5).

## 3. Empfehlung

1. **Produktions-Provider: Mistral AI (EU)** mit AVV, No-Training-Zusage, Sub-Prozessor-Liste
   (Default in `config.py`: `llm_base_url=https://api.mistral.ai/v1`, `llm_model=mistral-large-latest`).
2. **Pseudonymisierung vor jedem Call** technisch erzwingen und testen (T5) — unabhängig vom Provider.
3. **Alternative Azure EU** nur, wenn ein TIA und die MS-SCC/DPF-Papiere vorliegen.
4. **DeepSeek** nur mit expliziter anwaltlicher TIA-Freigabe; für den Default **ausschließen**.
5. Provider-Schicht provider-agnostisch halten (bereits so: OpenAI-kompatibles Interface,
   `pipeline/providers.py`) → Wechsel ohne Codeänderung möglich.

## 4. Offene Punkte

- **offen:** AVV des gewählten Providers tatsächlich beschaffen/einholen (M1).
- **offen:** Sub-Prozessor-Liste des Providers in unsere Liste übernehmen (`02`, Anlage).
- **offen:** No-Training-Zusage schriftlich fixieren.
- **muss bestätigt werden:** ob ein TIA für einen Nicht-EU-Provider je wirtschaftlich vertretbar ist.
