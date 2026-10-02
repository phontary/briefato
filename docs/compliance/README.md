# Briefato — Compliance-Paket (DSGVO / Recht / Threat Model)

Owner: Mohamed Sabry. Erstellt von WORKSTREAM-COMPLIANCE am 2026-10-02.
Scope: nur `docs/compliance/**`. Dieses Verzeichnis ist **Dokumentation, kein Code**.

> **KEIN RECHTSRAT.** Kein Dokument in diesem Verzeichnis ist Rechtsberatung. Alle Texte sind
> technische und organisatorische Vorarbeiten für die anwaltliche Prüfung. Jede als „Entwurf“
> markierte Vorlage muss von einem zugelassenen Rechtsanwalt (IT-/Datenschutzrecht) geprüft und
> freigegeben werden, bevor sie gegenüber Kunden, Betroffenen oder Behörden verwendet wird.
> Ebenso ersetzt nichts hier eine Steuerberatung oder eine versicherungsfachliche Auskunft.

## 1. Zweck und Kontext

Briefato ist ein SaaS-Portal für deutsche Arztpraxen: Mitglieder erfassen Patientenstammdaten und
diktieren/tippen klinischen Text; Briefato gibt einen fertig formatierten Arztbrief/Attest/Befund
zurück. Verarbeitete Daten sind **Gesundheitsdaten (Art. 9 DSGVO)** und unterliegen dem
**Berufsgeheimnis (§ 203 StGB)**.

Rollenverteilung (die zentrale Prüffrage des gesamten Pakets):

| Rolle | Wer | Konsequenz |
|---|---|---|
| **Verantwortlicher** (Art. 4 Nr. 7 DSGVO) | die **Praxis / das Mitglied** | entscheidet über Zwecke, Rechtsgrundlage, Aufbewahrung; ist Adressat der Betroffenenrechte |
| **Auftragsverarbeiter** (Art. 4 Nr. 8 DSGVO) | **Briefato (Mohamed Sabry)** | verarbeitet nur auf dokumentierte Weisung, schließt AVV (Art. 28) ab |
| **mitwirkende Person** (§ 203 Abs. 3 StGB) | **Briefato** und dessen Erfüllungsgehilfen | Offenbarung ist nur zulässig, solange sie zur Inanspruchnahme erforderlich ist; der Geheimnisträger muss **Briefato zur Geheimhaltung verpflichten** (§ 203 Abs. 4 Nr. 1 StGB) |
| **Unterauftragsverarbeiter** (Art. 28 Abs. 2/4) | Modell-Provider, Stripe, Hoster, Backup-Ziel | brauchen eigenen AVV-Kette; siehe `02-avv-checklist.md` |

## 2. Index

| Datei | Inhalt | Status |
|---|---|---|
| `README.md` | Index, Statuslegende, offene Punkte, Self-Check | verifiziert (Dokument) |
| `01-processing-register.md` | Verzeichnis von Verarbeitungstätigkeiten, Art. 30 DSGVO | Entwurf — muss bestätigt werden |
| `02-avv-checklist.md` | AVV-Pflichten ggü. Kunden, Unterauftragsverarbeiter-Liste, Drittlandfrage | Entwurf — muss bestätigt werden |
| `03-tom.md` | Art. 32 TOM, gemappt auf den echten Code | verifiziert (Code-Mapping) / offen (fehlende TOM) |
| `04-retention-deletion.md` | Aufbewahrungsmatrix, Löschworkflow, Konto-Löschung | Entwurf — muss bestätigt werden |
| `05-data-subject-rights.md` | Unterstützung für Art. 15/16/17/20 im Verarbeiter-Setting | Entwurf — muss bestätigt werden |
| `06-threat-model.md` | STRIDE-Threat-Model über die reale Architektur | verifiziert (Architektur) / offen (Residuen) |
| `07-legal-texts-briefing.md` | Briefing für Anwalt/Inhaber zu Impressum, Datenschutz, AGB, Widerruf | Entwurf — muss bestätigt werden |
| `08-mdr-boundary.md` | MDR-/KI-VO-Abgrenzung + „Do not do“-Produktregeln | Entwurf — muss bestätigt werden |
| `09-provider-dpa-briefing.md` | Anforderungen an den Modell-Provider, Optionsvergleich | Entwurf — muss bestätigt werden |
| `scripts/selfcheck.py` | Selbsttest (Existenz, keine Platzhalter, URLs mit Abrufdatum, offene Punkte) | verifiziert (läuft) |

## 3. Statuslegende

| Label | Bedeutung |
|---|---|
| **verifiziert** | gegen eine am 2026-10-02 abgerufene offizielle Quelle oder gegen den echten Repo-Code geprüft |
| **offen** | bekannt, aber noch nicht umgesetzt/entschieden; Maßnahme benannt |
| **muss bestätigt werden** | benötigt eine Entscheidung/Zulieferung von Mohamed oder eine anwaltliche/steuerliche Freigabe |
| **Entwurf** | Textvorlage, ausdrücklich nicht final, für Anwalt/Steuerberater |

## 4. Offene Punkte, die Mohamed liefern oder entscheiden muss

| # | Punkt | Warum nötig | Referenz |
|---|---|---|---|
| M1 | **AVV-Partnerwahl Modell-Provider** (Mistral EU / Azure EU / DeepSeek / lokal) | Ohne AVV kein rechtmäßiger Einsatz; Drittlandfrage hängt daran | `02`, `09` |
| M2 | **Stripe-Konto + KYC abschließen** | Zahlungsabwicklung; Stripe ist eigener Verantwortlicher für Zahlungsdaten | `01`, `07` |
| M3 | **Unternehmensstatus / Rechtsform** (Einzelunternehmer? Kleinunternehmer § 19 UStG?) | Bestimmt USt-Ausweis, Impressumsangaben, Rechnungsstellung | `07` |
| M4 | **Wer zeichnet das Impressum** (Name, ladungsfähige Anschrift, ggf. USt-IdNr.) | Pflichtangaben § 5 DDG | `07` |
| M5 | **Anwaltliche Prüfung** von Impressum, Datenschutzerklärung, AGB, Widerrufsbelehrung | Haftung; die Website-Platzhalter sind nicht final | `07` |
| M6 | **Versicherung / Cyber-Police** (Berufshaftung/Vermögensschaden, Cyber) | Deckungsfrage bei Datenpanne/Berufsgeheimnisverletzung | `06` |
| M7 | **Owner des Verzeichnisses von Verarbeitungstätigkeiten** (Name, Aufbewahrungsort, Pflegezyklus) | Art. 30 Abs. 1/3 DSGVO; Nachweispflicht | `01` |
| M8 | **Öffentliche Domain** (statt LAN-only `briefato.sabry.io`) | Voraussetzung für echten Betrieb/Let's-Encrypt-TLS | `03`, `06` |
| M9 | **Hosting für zahlende Kunden** (N305 vs. EU-VPS) | Verfügbarkeit/Exit; N305 hat dokumentiertes Swap-Problem (S5) | `06` |
| M10 | **DSB-Benennung** – ob ein Datenschutzbeauftragter zu benennen ist (§ 38 BDSG / Art. 37 DSGVO) | Kernaktivität ist umfangreiche Verarbeitung besonderer Daten | `01` |
| M11 | **Sub-Processor-Verträge abschließen** (Hosting, Backup-Ziel, E-Mail-Versand) | Art. 28 Abs. 4 DSGVO | `02` |
| M12 | **Backup-Restore-Test + Verschlüsselung off-host** durchführen und protokollieren | Art. 32 Abs. 1 lit. c DSGVO | `03`, `04` |

## 5. Quellenverzeichnis (Kurzform)

Vollständige Einzelnachweise stehen in den jeweiligen Dokumenten. Kanonische Fundstellen:

- DSGVO (VO (EU) 2016/679) — EUR-Lex CELEX 32016R0679, https://eur-lex.europa.eu/eli/reg/2016/679/oj (abgerufen 2026-10-02); Artikeltext gegengeprüft über https://gdpr-info.eu/ (abgerufen 2026-10-02).
- KI-VO (VO (EU) 2024/1689) — EUR-Lex CELEX 32024R1689, https://eur-lex.europa.eu/eli/reg/2024/1689/oj (abgerufen 2026-10-02); Zeitleiste/Analyse: https://artificialintelligenceact.eu/implementation-timeline/ (abgerufen 2026-10-02).
- MDR (VO (EU) 2017/745) — https://eur-lex.europa.eu/eli/reg/2017/745/oj (abgerufen 2026-10-02); MDCG 2019-11: https://health.ec.europa.eu/system/files/2020-09/md_mdcg_2019_11_guidance_en_0.pdf (abgerufen 2026-10-02).
- § 22 BDSG — https://www.gesetze-im-internet.de/bdsg_2018/__22.html (abgerufen 2026-10-02).
- § 203 StGB — https://www.gesetze-im-internet.de/stgb/__203.html (abgerufen 2026-10-02).
- § 630f BGB — https://www.gesetze-im-internet.de/bgb/__630f.html (abgerufen 2026-10-02).
- § 5 DDG — https://www.gesetze-im-internet.de/ddg/__5.html (abgerufen 2026-10-02).
- § 356 BGB — https://www.gesetze-im-internet.de/bgb/__356.html (abgerufen 2026-10-02).
- § 19 UStG — https://www.gesetze-im-internet.de/ustg_1980/__19.html (abgerufen 2026-10-02).
- § 6 PAngV — https://www.gesetze-im-internet.de/pangv_2022/__6.html (abgerufen 2026-10-02).
- § 25 TDDDG — https://www.gesetze-im-internet.de/ttdsg/__25.html (abgerufen 2026-10-02).
- DSK Orientierungshilfe TOM für KI-Systeme (Juni 2025) — https://www.datenschutzkonferenz-online.de/media/oh/DSK-OH_KI-Systeme.pdf (abgerufen 2026-10-02).
- DSK Orientierungshilfe für Anbieter:innen digitaler Dienste (Nov. 2024) — https://www.datenschutzkonferenz-online.de/media/oh/OH_Digitale_Dienste.pdf (abgerufen 2026-10-02).
- DSK Kurzpapier Nr. 13 „Auftragsverarbeitung“ (in Überarbeitung) — https://www.datenschutzkonferenz-online.de/media/kp/dsk_kpnr_13.pdf (abgerufen 2026-10-02).
- DSK Kurzpapier Nr. 1 „Verzeichnis von Verarbeitungstätigkeiten“ — https://www.datenschutzkonferenz-online.de/media/kp/dsk_kpnr_1.pdf (abgerufen 2026-10-02).

## 6. Self-Check (reproduzierbarer Befehl)

```bash
cd /workspace/briefato && python3 docs/compliance/scripts/selfcheck.py
```

Der Self-Check prüft:
1. **Existenz**: alle erwarteten Dateien vorhanden und nicht leer.
2. **Platzhalter**: keine Markierungen `TO`+`DO` oder `lo`+`rem` in den Markdown-Dateien.
3. **Quellen-Integrität**: jede zitierte `http(s)://`-URL steht in einer Zeile bzw. einem
   Aufzählungspunkt mit einem Abrufdatum (`abgerufen YYYY-MM-DD`) — sonst Fehler.
4. **Offene Punkte**: druckt die Checkliste der `muss bestätigt werden`/`offen`-Einträge.

Exit-Code 0 = alle harten Checks grün; Exit-Code 1 = mindestens ein Fehler.

## 7. Reihenfolge für die Freigabe (empfohlen)

1. M1/M11 entscheiden → AVV-Template (Anlage zum Produkt) erzeugen.
2. M5 beauftragen → Rechtstexte finalisieren.
3. `03-tom.md` offene Maßnahmen abarbeiten (MFA, Key-Rotation, Restore-Test, Rate-Limits).
4. `01-processing-register.md` von M7 als Owner bestätigen.
5. Erst danach (Compliance-Gate S5, siehe `docs/01-architecture.md`) an echte Mitglieder ausliefern.
