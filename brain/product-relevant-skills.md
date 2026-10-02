# Produkt-relevante Skills – Inventar und Entscheidung

Inventar der Skills des Schreibdienst-Profils mit Bewertung für die SaaS **Briefato**:
Ist der Skill inhaltlich für das Produkt relevant (yes/partly/no) und was damit tun
(Prompt-Regel portieren / als Playbook portieren / Architektur-Referenz / skip).

Maßstab: Briefato ist ein **stateless Web-Portal** (Dictation in → fertiger Brief out), KEIN
Per-Mitglied-Agent. Agenten-, Infra-, Hermes- und persönliche Skills sind daher grundsätzlich „no".
Die medizinischen Skills sind die eigentliche Produkt-Substanz.

Legende „Was tun": **Prompt-Regel** = wird Teil der Briefato-Prompt-Policy; **Playbook** = Vorlage/
Ablauf, der in Produktlogik (Musterbrief-/Formatlogik) überführt wird; **Quelle** = dient als
Fach-/Kontextquelle, nicht als Prompt; **Architektur-Referenz** = relevant für Design/Deploy, nicht
für die Textausgabe; **skip** = nicht übernehmen.

---

| Skill | Produkt-relevant? | Was tun | Begründung |
|---|---|---|---|
| `medizin/schreibdienst` | yes | Prompt-Regel | Kernkompetenz: Formatierungsregeln, Abkürzungsverzeichnis, Pipeline, Musterbrief-Check, Triage. Die zentrale Policy-Quelle. |
| `medizin/stolperfallen` | yes | Prompt-Regel | Die konkreten Fallstricke (Kompression, „präziserer späterer Befund", Diktatfehler, kein Erfinden) — direkt als Guard-Rules portierbar. |
| `medizin/zusammenfassung` | yes | Prompt-Regel | Eigener Ausgabemodus (max. 3–4 Sätze, keine Diagnoseliste). Als Modus im Produkt umsetzen. |
| `medizin/operationsbericht` | yes | Prompt-Regel | Eigener Ausgabemodus (Schritt-für-Schritt, Telegrammstil, Liste am Ende). Als Modus umsetzen. |
| `medizin/ambulant` | yes | Prompt-Regel | Briefart ambulant/tageschirurgisch mit eigenen Bausteinen und Auslassungen (kein Aufnahmesatz). |
| `medizin/entlassbrief-triage` | yes | Playbook | Entscheidungslogik stationär vs. ambulant; als Produkt-Routing nutzbar. |
| `medizin/entlassmedikationsplan` | yes | Prompt-Regel | Eigener Auftragstyp; kritische Regel „kein PDF, nur Text im Chat" + Dosis-Prüfhinweis. |
| `medizin/pflegeberichte-integration` | yes | Prompt-Regel | Filterregeln für Pflegeberichte (relevant vs. Rauschen) — Teil der Kompressions-Policy. |
| `medizin/diktat-tippfehler` | yes | Prompt-Regel | Stille Korrekturregeln inkl. Kontext-Fachbegriffe (Hornhaut, Blow-out C3). In die Fehlhörer-Policy. |
| `medizin/ablehnungsbogen-thieme-compliance` | partly | Playbook | Eigenes Formular-Dokument (Ablehnungsbogen) mit Pflichtinhalten — als Vorlage/Modus sinnvoll, aber nicht Kern der Brief-Generierung. |
| `medizin/klinische-pharmakologie` | partly | Quelle | Fachliche Arzneimittelantworten (Erstlinien, Allergie-Alternativen, RHB-Prüfung) — als Recherche-/Antwortmodus, nicht als Briefformat. |
| `medizin/weiterbildung-kv-nachweise` | no | skip | Rechts-/Nachweisfragen zur ärztlichen Weiterbildung (WBO, KV-Genehmigung) — persönliche Berufsverwaltung, kein Briefprodukt. |
| `medizin/kv-genehmigung-und-weiterbildung` | no | skip | Redundanter Vorgänger-Skill zu `weiterbildung-kv-nachweise`; dieselbe persönliche Domäne. |
| `op-iterationen` | partly | Playbook | Umgang mit nachgelieferten OP-Korrekturen (Passage ersetzen, nicht anhängen) — als Iterations-Logik im Editor nutzbar. |
| `pflegeberichte-integration` (Profil-Root) | no | skip | Dopplung des medizin-Skills (`skill_view` meldet „Ambiguous skill name"); im Produkt nur EINE Implementierung. |
| `dokumentation/tagebuch-system` | no | skip | Persönliches Tagebuch des Arztes (cron 07:00, poetischer Stil) — reine Privatfunktion des Nutzers, kein Produktfeature. |
| `productivity/ocr-and-documents` | yes | Playbook | Text-Extraktion aus PDFs/Scans — direkt nützlich für den Dictation-/Musterbrief-Import im Portal. |
| `productivity/nano-pdf` | partly | Playbook | PDF-Texteditur (typos/titles) — für Korrektur-Workflows denkbar; für Briefe gilt aber „kein PDF-Export". |
| `productivity/powerpoint` | no | skip | PPTX-Erstellung — kein Bezug zur Arztbrief-Domäne. |
| `productivity/notion` | no | skip | Notion-API/Vault — persönliches Notiz-Tooling, kein Produktfeature. |
| `productivity/airtable` | no | skip | Airtable-CRUD — persönliches Tooling/Datenbank-Spielwiese. |
| `productivity/google-workspace` | no | skip | Gmail/Calendar/Drive des Nutzers — persönliche Produktivität, nicht Briefato. |
| `productivity/maps` | no | skip | Geocoding/Routing (OSM/OSRM) — kein Bezug. |
| `productivity/petdex` | no | skip | Hermes-Maskottchen — reines Spielzeug. |
| `productivity/teams-meeting-pipeline` | no | skip | Microsoft-Graph-Meeting-Pipeline — Infrastruktur/Privat, nicht Briefato. |
| `creative/humanizer` | partly | Prompt-Regel | „/humanizer" = de-AI-Feinschliff (Passiv→Aktiv, Doppelungen glätten) — als optionaler Nachbearbeitungsschritt portierbar; NICHT Umgangston. |
| `software-development/session-store-recovery` | no | Architektur-Referenz | Reparatur der Hermes-Session-DB — nur für den Agentenbetrieb relevant, nicht fürs Produkt. |
| `software-development/bulk-refactor-mit-subagenten` | no | skip | Bulk-Refactor-Workflow des Agenten — Werkzeug des SYSADMIN, nicht Produkt. |
| `autonomous-ai-agents/*` (claude-code, codex, opencode, hermes-agent) | no | skip | Agenten-Delegation — Hermes-Betrieb. |
| `apple/*`, `media/*`, `social-media/*`, `smart-home/*`, `note-taking/obsidian` | no | skip | Persönliche Geräte-/Medien-/Konsum-Skills — kein Bezug zur medizinischen Textproduktion. |
| `devops/*` (portainer, kanban-*) | no | Architektur-Referenz | Deployment/Orchestrierung — nur für Betrieb der Briefato-Instanz, nicht für die Brief-Inhalte. |

---

## Konsequenz für die Prompt-Policy (Kurzfassung)

**Portieren als Prompt-Regel (Kern):** die Formatierungsregeln aus `schreibdienst`, die Kompressions-
und Korrektheitsregeln aus `stolperfallen`/`pflegeberichte-integration`/`diktat-tippfehler`, die drei
Sondermodi `zusammenfassung`/`operationsbericht`/`ambulant`, sowie `entlassmedikationsplan`.
Das `Abkürzungsverzeichnis` aus `schreibdienst` wird zur Lookup-Tabelle im Produkt.

**Als Modus/Playbook, nicht Prompt:** Briefart-Triage (`entlassbrief-triage`), OP-Iterationen
(`op-iterationen`), Ablehnungsbogen, Dokumenten-Import (`ocr-and-documents`).

**Skip:** alle Infra-, Agenten-, Apple-/Medien- und privaten Organisations-Skills; die Tagebuch-
Automatik; doppelte Skill-Kopien.

Es gibt KEINEN produktseitig relevanten Skill jenseits der `medizin/`-Familie, `op-iterationen`,
`pflegeberichte-integration`, `humanizer` und `ocr-and-documents` — die übrige Profil-Hälfte ist
persönliche Hermes-/Server-Bedienung des Doktors und gehört nicht in den SaaS.
