# Wie Briefato funktioniert — Schritt für Schritt

Für Mohamed (und als Textbasis für FAQ / Onboarding). Bewusst einfach, ohne Fachjargon.
Stand: 2026-10-02. Alles hier Beschriebene ist im Code vorhanden und auf der Staging-Instanz geprüft.

## 1. Der Weg einer Anfrage (vom Browser bis zur Datenbank)

1. **Browser → Internet → Caddy.** Der Nutzer öffnet `https://briefato.sabry.io`. Caddy (der
   Webserver davor) macht drei Dinge: TLS-Verschlüsselung, Zugriffsprotokoll, und er leitet die
   Anfrage an den Container weiter (`127.0.0.1:8085`). Der Container ist **nicht** direkt aus dem
   Internet erreichbar.
2. **Die Anwendung (FastAPI).** Ein Python-Programm beantwortet die Anfrage. Es entscheidet, was
   angezeigt wird: Startseite, Login, oder die Anwendung hinter dem Login.
3. **Anmeldung.** Beim Registrieren wird das Passwort **nie** im Klartext gespeichert, sondern mit
   `argon2` gehasht (Einweg). Danach bekommt der Browser ein signiertes Sitzungs-Cookie; jede
   schreibende Anfrage braucht zusätzlich ein CSRF-Token (Schutz gegen fremde Seiten).
4. **Patient/in anlegen.** Der Nutzer speichert einmal Name, Geburtsdatum, Kostenträger,
   Versicherungsnummer, Adresse. Diese Zeile gehört **seinem** Konto (`user_id`) — jede Abfrage im
   Code filtert danach. Ein fremder Datensatz ist für ihn unsichtbar (404, nicht 403).
5. **Diktat + Dokumenttyp.** Der Nutzer fügt den Rohtext ein und wählt den Dokumenttyp — oder lässt
   „Automatisch erkennen“ stehen. Das Diktat wird sofort **verschlüsselt** (AES-Fernet) in der
   Datenbank abgelegt. Bis hierher hat noch nichts die Maschine verlassen.

## 2. Was beim Klick auf „erzeugen“ passiert (der Kern)

6. **Methode laden.** Die Anwendung holt aus dem Gehirn (`brain/`): die Kernregeln (`kern.md`), das
   Playbook für diesen Dokumenttyp, die Anti-Pattern-Liste und die Regelprüfung R1–R67.
7. **Vorlage suchen.** Aus dem Diktat werden Diagnose-Stichworte gezogen (`Divertikulitis`,
   `Gallensteine`, `TVK` …) und dazu die passende(n) Musterbrief-Vorlage(n) aus der Bibliothek
   gesucht — sie liefern die **Struktur** (Klinik/Diagnostik/Therapie/Nachsorge), nicht den Text.
8. **Pseudonymisieren (der wichtigste Schritt für den Datenschutz).** Bevor irgendetwas an das
   KI-Modell geht, werden die Patientendaten **lokal** durch Platzhalter ersetzt:
   `Müller, Anna, geboren 02.03.1974, Versicherungsnummer A123…` → `{{LAST_NAME}}`,
   `{{FIRST_NAME}}`, `{{BIRTH_DATE}}`, `{{INSURANCE_NUMBER}}` usw. Der Regel-Check stellt sicher,
   dass im Text, der das Haus verlässt, kein echter Name mehr steht.
9. **Modell fragen.** Der zusammengebaute Auftrag (Regeln + Playbook + Vorlagenstruktur +
   anonymisiertes Diktat) geht per HTTPS an das Sprachmodell. Es antwortet mit einem Text, in dem
   noch die Platzhalter stehen.
10. **Namen zurückholen.** Die Platzhalter werden **lokal** wieder durch die echten Werte ersetzt.
    Der fertige Brief mit echten Namen existiert also nur auf unserem Server.
11. **Regelprüfung.** Der Text wird gegen die Methode geprüft: kein Markdown, keine Kategorie-Labels
    (`Labor:`, `Sono:`), keine Einleitung/kein Schluss, `Diagnosen:` am Ende, Blockreihenfolge,
    keine erfundenen Daten/ICD-Codes, höchstens ein Semikolon, korrekte Umlaute. Bei harten
    Verstößen: **ein** automatischer Neuversuch mit den Verstößen als Korrekturhinweis — danach wird
    das Ergebnis mit den gefundenen Hinweisen angezeigt (nie stillschweigend „schöngefärbt“).
12. **Speichern + Protokoll.** Brieftext (verschlüsselt), Modell, Tokens, Kosten, Dauer und ein
    Audit-Eintrag (wer, was, wann) landen in der Datenbank.
13. **Ausgabe.** Der Nutzer kopiert den Text mit einem Klick (`Text kopieren`) und fügt ihn in sein
    KIS ein. DOCX mit Briefkopf ist optional, nicht der Standardweg.

## 3. Die Bibliothek wächst mit

14. Findet die Suche keine Vorlage, kann der Nutzer eine **vorschlagen**. Der Vorschlag landet in
    einer Warteschlange; Mohamed (Admin) entscheidet. Angenommen wird nur **generisches,
    patientenunabhängiges** Wissen — nie Falldaten, nie Namen. So wird das Produkt mit jedem
    eingereichten Brief ein Stück besser, kontrolliert von einem Menschen.

## 4. Wo die Daten liegen

- **Ein Container** auf dem N305 (`briefato`, Portainer Stack 69), Daten unter
  `/mnt/fast/docker/briefato/data` (SQLite-Datei + `letters/`).
- **Kryptografie:** Master-Schlüssel (`BRIEFATO_FIELD_KEY`) und App-Secret liegen in Stack-Env/`pass`,
  nicht im Code. **Achtung:** Schlüsselrotation macht gespeicherte Texte unlesbar (Dokumentiert).
- **Backup:** Skript erzeugt einen konsistenten SQLite-Abzug + GPG-verschlüsseltes Archiv; die
  Off-Host-Kopie ist noch offen (eine Zeile im Skript, siehe `deploy/backup-briefato.sh`).
- **Kein Patientendatensatz verlässt das Haus im Klartext:** entweder läuft das Modell lokal
  (`BRIEFATO_LLM_MOCK`, wie im Staging), oder es sind nur Platzhalter unterwegs.

## 5. AVV — in einem Satz und dann in Klartext

**AVV = Auftragsverarbeitungsvertrag** (englisch DPA). Ein Vertrag, in dem steht: *wir dürfen die
Daten des Kunden ausschließlich nach seinen Anweisungen verarbeiten — nicht für eigene Zwecke, nicht
weitergeben, gut gesichert, und wir löschen sie, wenn er es verlangt.*

**Analogie:** Die Praxis gibt uns ihr Auto zur Reparatur. Wir dürfen es reparieren — nicht damit
spazierenfahren, nicht verkaufen, nicht verleihen. Der AVV ist der Zettel, auf dem das steht.

Konkret für uns:

| Mit wem | Warum ein AVV nötig ist | Stand |
|---|---|---|
| **Kunde (Praxis/Klinik)** | Er bleibt Herr der Daten (Verantwortlicher), wir sind Auftragsverarbeiter. Ohne AVV darf keine Praxis uns Patientendaten geben. | Text muss noch erstellt/anwaltlich geprüft werden → `docs/compliance/02-avv-checklist.md` |
| **Modell-Anbieter** | Die (anonymisierten) medizinischen Texte laufen über **seine** Server — auch das ist Verarbeitung. | offen; Empfehlung EU-Anbieter mit AVV (`09-provider-dpa-briefing.md`) |
| **Stripe** | Zahlungsdaten des Kunden. | Standard-DPA von Stripe, ergänzen |
| **Hosting/Backup-Ziel** | Wenn wir später auf einen VPS/andere Maschine gehen. | offen (heute: eigene Hardware, kein Dritter) |

Zwei Dinge, die oft verwechselt werden:
- **Pseudonymisierung** (Schritt 8) ist eine **technische Schutzmaßnahme** — sie ersetzt keinen AVV.
- Der **Drittland-Transfer** (z. B. Anbieter außerhalb der EU) braucht zusätzlich eine
  Rechtsgrundlage (Standardvertragsklauseln + Transfer Impact Assessment). Deshalb ist der
  EU-Anbieter der einfachere Weg.
