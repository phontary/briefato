# Briefato — marketing site (`landing/`)

Static German marketing site for **Briefato**, a SaaS portal for medical practices
(raw dictation in → finished, letterhead-correct Arztbrief / Attest / Befund out).
Plain HTML5 + hand-written CSS + inline/self-made SVG. **No build step, no framework,
no CDN, no external request of any kind.**

Owner of this directory: **WORKSTREAM-LANDING**. Frozen contracts it must respect:
`docs/01-architecture.md` and `docs/02-spec-interfaces.md` (esp. §1 ownership map, §7 design system).

---

## 1. Files

```
landing/
├─ index.html          Startseite: Hero (Vorher/Nachher), 3 Schritte, Zielgruppen,
│                       Funktionen, Datenschutz/Vertrauen, Preis-Teaser, FAQ, CTA
├─ preise.html         Tarife, Vergleichstabelle, FAQ zu Abrechnung/Vertrag/Kündigung
├─ impressum.html      DRAFT — § 5 DDG
├─ datenschutz.html    DRAFT — Art. 13 DSGVO
├─ agb.html            DRAFT — Vertrags-, Preis-, Kündigungs- und Widerrufsregeln
├─ 404.html            Fehlerseite
├─ selfcheck.py        stdlib-Validator für alle Seiten (siehe §8)
├─ README.md           diese Datei
└─ assets/
   ├─ css/briefato.css  Design-System (Tokens, Layout, Dark Mode) — ~18 KB
   ├─ js/site.js        Progressive Enhancement (Mobile-Nav, Footer-Jahr) — ~1.7 KB
   └─ img/
      ├─ logo.svg         Wortmarke „Briefato" (Marke + Schriftzug)
      ├─ logo-mark.svg    nur die Bildmarke
      ├─ favicon.svg      Favicon (SVG)
      ├─ illu-dictation.svg  Diktataufnahme
      ├─ illu-letter.svg     fertiger Brief mit Freigabe-Häkchen
      └─ illu-privacy.svg    Pseudonymisierung (Schild + Tokens)
```

Alle Grafiken sind selbst erstellt (SVG, keine Stockfotos). Die drei Illustrationen
sind Linienzeichnungen in Mittelton-Teal, die auf hellem wie dunklem Grund ≥ 3:1
Kontrast halten (WCAG 1.4.11 für Nicht-Text-Inhalte).

## 2. Wie die Seite ausgeliefert wird

Der Portal-Server (WORKSTREAM-PORTAL) liefert statische Dateien aus diesem Verzeichnis:

| Route | Datei |
|---|---|
| `GET /` | `landing/index.html` |
| `GET /preise` | `landing/preise.html` |
| `GET /impressum` · `/datenschutz` · `/agb` | `…/<name>.html` |
| `GET /assets/…` | `landing/assets/…` |

Deshalb sind **alle** internen Verweise absolut (`/assets/css/briefato.css`, `/preise`,
`/anmelden`, `/registrieren`) und nicht relativ. `/anmelden` und `/registrieren` sind
Portal-Routen ohne lokale Datei; `selfcheck.py` kennt sie als erlaubte Ausnahmen
(siehe `PORTAL_ROUTES` in `selfcheck.py`, passend zu `docs/02-spec-interfaces.md` §5).

Kein JavaScript nötig für Inhalte: Die Navigation ist ohne JS vollständig sichtbar; JS
klappt sie auf kleinen Bildschirmen hinter einen „Menü"-Knopf und setzt das Jahr im
Footer. Nichts wird per JS geladen, keine Tracking-Skripte.

## 3. Struktur & Conversion (Recherche)

Die Startseite folgt dem für SaaS/Healthcare üblichen Aufbau: Nutzenversprechen über der
Falz, konkretes Vorher/Nachher-Beispiel statt Adjektive, dann Ablauf, Zielgruppen,
Funktionsumfang, Vertrauen/Datenschutz, Preis-Teaser, FAQ, Abschluss-CTA. Jede Sektion
hat einen eigenen Handlungsaufruf bzw. führt zum Abschluss-CTA (`/registrieren`).

## 4. Design-System

- Tokens im CSS (`:root`): eine Akzentfarbe (Teal), Typo- und Abstandsskalen, Radien,
  Schatten, Dark-Mode-Variablen. Bewusst als Kopie der Portal-Tokens
  (`app/briefato/static/css/tokens.css`) — kein Build-Schritt, Duplikat erlaubt (§ 7).
- System-Font-Stack, keine Webfonts ⇒ kein externer Abruf, kein Font-Flackern.
- Responsiv 360–1440 px; Breakpoints bei 620/640/720/860/900/960/1000/1024 px,
  Mobile-Nav unter 900 px.
- `prefers-color-scheme: dark` und `prefers-reduced-motion`, `@media print`.
- Semantisches HTML5 (`header/main/section/article/nav/footer`), ein `<h1>` je Seite,
  Skip-Link, sichtbare `:focus-visible`-Ringe, `aria-current` in der Navigation,
  `alt`-Texte, `width`/`height` an allen Bildern (kein Layout-Shift).
- Kontrast: alle Text/Hintergrund-Paare erfüllen WCAG AA (geprüft, siehe §8).
- Es gibt auf der Marketingseite **keine Formulare** (Registrierung/Anmeldung liegen im
  Portal). Deshalb gibt es keine `<label>`-Prüfung an echten Feldern; die Formular-Label-
  Regel greift automatisch, sobald ein Formular ergänzt wird.

## 5. Vertrauensaussagen — nur Belegtes

Es werden ausschließlich Aussagen verwendet, die im Produkt angelegt sind. Keine
Aussage zu Serverstandort, keine Zertifizierungen, keine erfundenen Kennzahlen.

| Aussage auf der Seite | Beleg im Produkt |
|---|---|
| Pseudonymisierung vor dem Modellaufruf | ADR **D4**, `Pseudonymizer`/`mask`/`restore` (`pipeline/pseudonym.py`), Spalte `generations.pseudonymised` |
| Verschlüsselte Speicherung von Diktat und Brief | ADR **D7**, `security.encrypt_field/decrypt_field` (Fernet), Spalten `dictation_enc`/`content_enc` |
| Löschen und Export auf Anfrage | S5 (DSGVO-Paket), Konto-Route `/app/konto` |
| AVV nach Art. 28 DSGVO verfügbar | S5, D5 (EU-Anbieter mit AVV angestrebt) |
| Kein Training mit Kundendaten | Vertragliche Zusage zum Modelleinsatz (D5) — vor Launch im AVV/Anbieter-Setting zu sichern |

> **HOSTING — vor dem öffentlichen Start mit dem Eigentümer festzulegen.**
> Es wird bewusst **nicht** behauptet, dass in Deutschland gehostet wird. Auf `index.html`
> und `datenschutz.html` steht stattdessen ein sichtbarer Hinweis, dass Hosting und
> Modellanbieter noch nicht final gewählt sind. Sobald das entschieden ist, sind zu
> ergänzen: Impressum (Hosting-/Vertretungsangabe), Datenschutzerklärung § 8/§ 9
> (Empfänger, Drittlandübermittlung), `index.html`-Hinweisbox.

## 6. Was eine Rechtsanwältin / ein Rechtsanwalt bestätigen muss

Alle drei Rechtstexte sind **Entwürfe** und tragen oben ein sichtbares Banner
„Entwurf – juristische Prüfung ausstehend". Im Quelltext steht jeweils ein Kommentar
`RECHTSPRÜFUNG …` mit der Prüfliste. Kurzfassung:

- **Impressum:** vollständiger Anbietername + ladungsfähige Anschrift, Rechtsform und
  Vertretungsberechtigte, Register + Nummer, USt-IdNr., E-Mail **und** Telefon,
  ggf. § 18 Abs. 2 MStV, § 36 VSBG, Abgrenzung „kein Medizinprodukt"
  (§ 5 Abs. 1 DDG; IHK/eRecht24).
- **Datenschutz:** Verantwortlicher, DSB, Verzeichnis der Verarbeitungen mit
  Rechtsgrundlagen, Empfänger + AVV, Drittlandübermittlung, Art. 9/Art. 35-Bewertung
  (Gesundheitsdaten!), Löschfristen, § 25 TDDDG (nur technisch notwendige Cookies).
- **AGB:** Einbeziehung, Preisangaben nach PAngV (Endpreis inkl. 19 % MwSt.), Laufzeit
  und Kündigung (§ 309 Nr. 9 BGB), **Widerrufsbelehrung + Muster-Widerrufsformular** und
  die Ausnahme für digitale Inhalte nach § 356 Abs. 5 BGB, Klauselkontrolle
  §§ 305 ff. BGB, Haftung, anwendbares Recht.
- **Preise:** `index.html`/`preise.html` tragen den Kommentar
  `PREISE VORLÄUFIG`. Die Werte stammen aus `PLAN_CATALOG` (`app/briefato/config.py`)
  und sind vor Veröffentlichung zu bestätigen.

## 7. Was der Eigentümer (Mohamed) festlegen muss

1. **Hosting & Modellanbieter** (siehe §5) — Freigabe der Formulierungen.
2. **Preise und Kontingente** — `PLAN_CATALOG` bestätigen (Test 0 €/10, Starter 19 €/40,
   Praxis 39 €/120, Klinik 89 €/400). Anzeige überall „inkl. 19 % MwSt."
   und bei den kostenpflichtigen Tarifen „monatlich kündbar".
3. **Abrechnungstext** — die Seite beschreibt monatliche Abrechnung über einen
   Zahlungsdienstleister (Stripe, ADR D6). Wortlaut mit der Billing-Workstream abstimmen.
4. **Anbieterdaten** fürs Impressum und die Datenschutzerklärung.
5. **Freigabe der Texte** durch die juristische Prüfung, dann Banner entfernen.

## 8. Selbst-Check (exakter Befehl)

```bash
cd /workspace/briefato
.venv/bin/python landing/selfcheck.py
```

Das Skript ist reine Standardbibliothek (`html.parser`) und prüft für **jede** der sechs
Seiten: parst als HTML (Doctype, schließendes `</html>`, ausbalancierte Container-Tags),
`<title>`, `<meta charset=utf-8>`, `<meta name="viewport">`, meta description,
`<html lang="de">`, genau eine `<h1>`, `alt` an jedem `<img>` und `<label>` je
Formularfeld; ferner: **jeder** interne `href`/`src` löst auf eine existierende Datei auf
(Portal-Routen ausgenommen), **null** externe http(s)-Referenzen, keine Wörter
`TODO`/`Lorem`/`Platzhalter`, Stylesheet verlinkt und vorhanden. Ausgabe: eine
`PASS`/`FAIL`-Zeile je Seite plus Gesamtergebnis; Exit-Code 1 bei Fehlern.

Zusätzlich manuell geprüft (nicht Teil von `selfcheck.py`):

- CSS-Größe 18 008 Byte (< 40 KB), Gesamt-Assets 24 684 Byte.
- WCAG-Kontrast aller Farbpaare in Light und Dark: 6,1:1 bis 16,8:1 — alle ≥ AA (4,5:1).
- Alle Bilder tragen `width`/`height` (kein Layout-Shift).
- Nur `xmlns="http://www.w3.org/2000/svg"` in den SVG-Dateien: das ist eine
  Namespace-Deklaration, kein Netzwerkabruf — kein externer Request.

**Einschränkung:** In dieser Session war **kein Browser-Rendering möglich**
(kein `agent-browser`, kein Node/Chromium, kein CDP-Endpunkt erreichbar). Die
Darstellung bei 1440 px und 390 px wurde daher **nicht** visuell gegengeprüft; geprüft
wurden nur Struktur, Referenzen, Kontrast, Größen und die Breakpoints im CSS.

## 9. Quellen (Recherche)

Primärquellen wurden direkt über HTTPS geladen und geprüft (der `web_extract`-Backend
war in dieser Session nicht verfügbar, `web_search` lieferte teils unscharfe Treffer).

**Recht (Deutschland):**

1. Digitale-Dienste-Gesetz (DDG), § 5 Allgemeine Informationspflichten —
   https://www.gesetze-im-internet.de/ddg/BJNR0950B0024.html
2. Preisangabenverordnung (PAngV 2022), § 1/§ 3/§ 6 — Gesamtpreis inkl. USt. —
   https://www.gesetze-im-internet.de/pangv_2022/BJNR492110021.html
3. Bürgerliches Gesetzbuch, § 356 (Widerrufsrecht, Abs. 5 digitale Inhalte) —
   https://www.gesetze-im-internet.de/bgb/__356.html
4. Bürgerliches Gesetzbuch, § 312g (Ausnahmen vom Widerrufsrecht) —
   https://www.gesetze-im-internet.de/bgb/__312g.html
5. IHK Regensburg, „Pflichtangaben im Internet-Impressum" —
   https://www.ihk.de/regensburg/fachthemen/recht/online-recht-und-datenschutz/online-recht/pflichtangaben-im-internet-impressum-1394836
6. eRecht24, „Impressum: Pflichtangaben, Generator & mehr" —
   https://www.e-recht24.de/impressum/
7. fachanwalt.de, „Was muss ins Impressum?" (weiterführend) —
   https://www.fachanwalt.de/magazin/impressum-recht/impressum-inhalt

**Landing-Page-Struktur / Conversion:**

8. Nielsen Norman Group, „Trustworthy Design" (Vertrauenssignale) und
   „F-Shaped Pattern" (Leseverhalten) —
   https://www.nngroup.com/articles/trustworthy-design/ ·
   https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/
9. Unbounce, „Landing Page Best Practices" (weiterführend) —
   https://unbounce.com/landing-page-articles/landing-page-best-practices/
