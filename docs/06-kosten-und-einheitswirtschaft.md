# Kosten & Einheitswirtschaft (gemessen, nicht geschätzt)

Stand 2026-10-02. Preisquelle: offizielle DeepSeek-API-Preise, von Mohamed übermittelt
(10/2026); Modell `deepseek-flash` (DeepSeek-V4.1-Flash).

## 1. Preisliste (USD pro 1 Mio. Token)

| Position | Off-Peak | Peak (×2) |
|---|---|---|
| Input (Cache-Miss) | 0,15 $ | 0,30 $ |
| Input (Cache-Hit) | 0,003 $ | 0,006 $ |
| Output | 0,60 $ | 1,20 $ |
| *Vergleich `deepseek-v4-pro`* | *0,66 $ / 1,98 $* | *1,32 $ / 3,96 $* |

**Peak-/Off-Peak-Fenster verdoppeln den Preis**; Cache-Hits senken den Input-Preis um Faktor 50.
Im Produkt sind die **Peak-Werte** als Default gesetzt (konservativ):
`BRIEFATO_LLM_COST_IN_PER_1K=0.0003`, `BRIEFATO_LLM_COST_OUT_PER_1K=0.0012`.
Der Zähler in der Datenbank ist damit eine **Schätzung** (er kennt weder Cache-Hits noch das
Tageszeit-Fenster) — für die Abrechnung mit Kunden zählt die Kundenkalkulation, nicht der Zähler.

## 2. Gemessene Kosten (echte Läufe, 2026-10-02)

| Lauf | Fälle | Tokens in/out | Ø pro Dokument (off-peak) | Ø pro Dokument (peak) |
|---|---|---|---|---|
| 14 synthetische Fälle, DeepSeek | 14 | 112.414 / 18.115 | **0,00198 $** (≈ 0,0018 €) | 0,00396 $ (≈ 0,0036 €) |
| 5 Fälle inkl. LLM-Judge | 5 | 39.894 / 6.070 | 0,00193 $ | 0,00385 $ |

Schwerster Einzelfall: `entlassbrief-03` (Fan-out, ~9.000 Token Input) = **0,002 $** off-peak.
Ein Fan-out-Entlassbrief mit 14 Quellen kostet also rund **einen Fünftel Cent**.

## 3. Was am Preis zieht (und was nicht)

- **Fan-out** ist der Kostentreiber Nr. 1 (14 Kompressions-Calls + 1 Weave statt 1 Call) — kostet
  aber gemessen nur ~0,002 $ pro Brief, weil die Segmente kurz sind.
- **Retry nach harter Regelverletzung**: maximal einer pro Dokument → +~100 % im Fehlerfall.
- **Anreicherung/Recherche** (`BRIEFATO_ENRICH_DEFAULT`): zusätzliche Calls; im Testlauf mit
  Archiv-Anreicherung keine Web-Calls (SearXNG nur bei aktivierter Recherche).
- **LLM-Judge** ist ein QA-Werkzeug, nicht Teil der Produktion: er verdoppelt die Kosten des
  jeweiligen Laufs und läuft nur in der Auswertung.
- Cache-Hits (identische Prompt-Präfixe wie das Regelwerk) würden den Input-Anteil deutlich senken;
  die aktuelle Messung enthält diesen Effekt nicht getrennt.

## 4. Einheitswirtschaft (gemessen × Planpreise)

| Plan | Preis/Monat | Inklusiv-Dokumente | Modellkosten (peak, worst case) | Anteil am Umsatz |
|---|---|---|---|---|
| Test | 0 € | 10 | ≤ 0,04 € | — (Akquise) |
| Starter | 19 € | 40 | ≤ 0,15 € | 0,8 % |
| Praxis | 39 € | 120 | ≤ 0,44 € | 1,1 % |
| Klinik | 89 € | 400 | ≤ 1,50 € | 1,7 % |

**Folgerung:** Modellkosten sind irrelevant für die Marge — der Kostentreiber ist Support,
Betrieb und Recht (vgl. `docs/compliance/`) sowie die Hosting-Entscheidung. Stripe nimmt pro
Transaktion mehr als der ganze Modellverbrauch eines Monats (0,25 € + 1,5 % Karte, 0,35 € SEPA).

## 5. Offene Punkte

- Peak/Off-Peak-Zeitfenster offiziell verifizieren und — falls relevant — den Zähler darauf
  umstellen (aktuell konservativ Peak).
- Cache-Hit-Quote messen (Input-Präfixe sind stabil → Potenzial).
- Kosten pro Kunde im Admin sichtbar machen (Summe `generations.cost_usd` pro Monat).
