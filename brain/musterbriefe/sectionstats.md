# Sektionen – Statistik & Datenqualität

Basis: 152 Musterbriefe. Referenzsektionen = `Klinik`, `KU`, `Diagnostik`, `Therapie`, `Verlauf`, `Nachsorge`, `Therapieempfehlungen bei Entlassung`, `Diagnosen`.
(Referenzset = die im Auftrag genannten Kernsektionen plus `Nachsorge`, weil
`Nachsorge` mit Abstand die häufigste Body-Sektion ist.)

## Abdeckung je Referenzsektion

| Sektion | vorhanden | fehlt | Abdeckung |
|---|---|---|---|
| Klinik | 144 | 8 | 95% |
| KU | 12 | 140 | 8% |
| Diagnostik | 140 | 12 | 92% |
| Therapie | 146 | 6 | 96% |
| Verlauf | 20 | 132 | 13% |
| Nachsorge | 115 | 37 | 76% |
| Therapieempfehlungen bei Entlassung | 16 | 136 | 11% |
| Diagnosen | 15 | 137 | 10% |

## Fehlende Sektionen – Häufigkeit

| Sektion | fehlt in n Briefen |
|---|---|
| Therapie | 6 |
| Klinik | 8 |
| Diagnostik | 12 |
| Nachsorge | 37 |
| Verlauf | 132 |
| Therapieempfehlungen bei Entlassung | 136 |
| Diagnosen | 137 |
| KU | 140 |

## Zu dünn (< 400 Zeichen)

- **keine** Datei unter 400 Zeichen (alle ≥ 785 Zeichen).

## Grenzwertig kurz (< 1200 Zeichen, n=21)

- `Daumenfraktur.md` — 778 Zeichen, Titel: Daumenfraktur
- `Adipositas.md` — 947 Zeichen, Titel: Adipositas
- `Schenkelhalsfraktur.md` — 960 Zeichen, Titel: Schenkelhalsfraktur
- `Leberhämangiom.md` — 1027 Zeichen, Titel: Leberhämangiom
- `Wirbelkörperhämangiom.md` — 1029 Zeichen, Titel: Wirbelkörperhämangiom
- `Rippenserienfraktur.md` — 1047 Zeichen, Titel: Rippenserienfraktur (Z.n., konsolidiert)
- `C-Gastritis_bei_Gallereflux.md` — 1051 Zeichen, Titel: C-Gastritis bei Gallereflux
- `Chronisch_entzuendliche_Colonveraenderungen_sigmoidal.md` — 1072 Zeichen, Titel: Chronisch-entzündliche Veränderungen des Colon descendens und rektosigmoidal
- `Kontusion_Grundgelenk_Ringfinger.md` — 1076 Zeichen, Titel: Kontusion Grundgelenk Ringfinger
- `Angststoerung.md` — 1100 Zeichen, Titel: Angststörung
- `Axiale_Hiatushernie.md` — 1105 Zeichen, Titel: Axiale Hiatushernie
- `Insektenstich.md` — 1115 Zeichen, Titel: Insektenstich
- `Kontusion_Mittelzehe.md` — 1121 Zeichen, Titel: Kontusion der Mittelzehe (Contusio digiti pedis)
- `Kontusion_Kleinzehe.md` — 1131 Zeichen, Titel: Kontusion der Kleinzehe (Contusio digiti minimi pedis)
- `Akute_Colitis.md` — 1144 Zeichen, Titel: Akute Colitis
- `Hämorrhoiden.md` — 1163 Zeichen, Titel: Hämorrhoiden
- `Appendizitis_epiploica.md` — 1164 Zeichen, Titel: Appendizitis epiploica
- `Klavikulafraktur_lateral_disloziert.md` — 1166 Zeichen, Titel: Klavikulafraktur (lateral, disloziert)
- `Akute_Gastritis.md` — 1192 Zeichen, Titel: Akute Gastritis
- `Fasziitis_plantaris.md` — 1197 Zeichen, Titel: Fasziitis plantaris
- `Hepatomegalie_mit_zystoiden_Leberaesionen.md` — 1197 Zeichen, Titel: Hepatomegalie mit zystoiden Leberläsionen

## Zu lang (> 4000 Zeichen, n=4)

- `Papillaere_Pankreatitis.md` — 8887 Zeichen
- `Pangastritis.md` — 8757 Zeichen
- `Proktitis.md` — 6105 Zeichen
- `Coxarthrose_Exsikkose_Sturz.md` — 4767 Zeichen

## Duplikate / Near-Duplicates (Titel-Ähnlichkeit ≥ 0.75, n=11)

| Ähnlichkeit | Datei A | Datei B |
|---|---|---|
| 1.0 | `Diabetes_mellitus_Typ1.md` | `Diabetes_mellitus_Typ2.md` |
| 0.92 | `Kontusion_Grundgelenk_Kleinfinger.md` | `Kontusion_Grundgelenk_Ringfinger.md` |
| 0.9 | `Chronische_Niereninsuffizienz_CKD3.md` | `Chronische_Niereninsuffizienz_dialysepflichtig.md` |
| 0.86 | `Nadelstichverletzung.md` | `Stichverletzung.md` |
| 0.86 | `Biliaere_Pankreatitis.md` | `Papillaere_Pankreatitis.md` |
| 0.84 | `Kontusion_Kleinzehe.md` | `Kontusion_Mittelzehe.md` |
| 0.79 | `Choledocholithiasis.md` | `Cholezystolithiasis.md` |
| 0.76 | `Bissverletzung.md` | `Stichverletzung.md` |
| 0.75 | `Insektenstich.md` | `Zeckenstich.md` |
| 0.75 | `Distorsion_Daumen_Grundgelenk.md` | `Distorsion_Sprunggelenk.md` |
| 0.75 | `Abrissfraktur-Basis-MFK-V.md` | `Metatarsalefraktur_Basis_MFK_II.md` |

### Thematische Cluster (manuell, ergänzend zur Ähnlichkeitsliste)

| Thema | Dateien | Bewertung |
|---|---|---|
| Diabetes | `Diabetes_mellitus_Typ1.md`, `Diabetes_mellitus_Typ2.md` | bewusst getrennt (Typ 1/2), Struktur nahezu identisch |
| Erysipel | `Erysipel.md`, `Erysipel_Wundrose.md` | vermutlich redundant – zusammenführen |
| pAVK | `pAVK.md`, `pAVK_Mediasklerose.md` | konsolidieren (Mediasklerose = Sonderfall) |
| Narbenhernie epigastrisch | `Narbenhernie_epigastrische_IPOM.md`, `Narbenhernien_epigastrisch.md` | stark überlappend – prüfen/mergen |
| Leistenhernie | `Leistenhernie_Inguinalhernie_TAPP.md`, `Leistenhernie_Inguinalhernie_Lichtenstein.md` | bewusst zwei OP-Techniken, behalten |
| Gallenwege | `Cholezystolithiasis.md`, `Choledocholithiasis.md`, `Gallenblasenpolypen_Konkremente_Verdacht.md`, `Gangraenose_Cholezystitis_CHE.md` | überlappend, je Brief abgrenzen |
| Niereninsuffizienz | `Chronische_Niereninsuffizienz_CKD3.md`, `..._dialysepflichtig.md` | bewusst getrennt (Dialyse ja/nein) |
| Pankreatitis | `Biliaere_Pankreatitis.md`, `Papillaere_Pankreatitis.md` | überlappend – abgrenzen |
| Kontusionen Zehen/Finger | `Kontusion_Grosszehe/Kleinzehe/Mittelzehe/Grundgelenk_Kleinfinger/Grundgelenk_Ringfinger.md` | sehr ähnlich; viele dünne Kleinbriefe |

## Empfehlungen

1. **Duplikate mergen/abgrenzen:** siehe Tabelle; je Paar prüfen, ob ein Brief
   reicht oder bewusst zwei Varianten (z. B. OP-Technik TAPP vs. Lichtenstein)
   gewünscht sind.
2. **Unter 1200 Zeichen auffüllen:** die kurzen Briefe (v. a. Frakturen/Prellungen)
   um Diagnostik, Verlauf und Entlass-Empfehlungen ergänzen.
3. **`KU` nur in wenigen Briefen:** konsequent eine kurze Untersuchungs-Sektion
   ergänzen, damit der Generator einheitlich befüllen kann.
4. **`Nachsorge` in ~25% der Briefe:** fehlende Nachsorge/Entlass-Empfehlungen
   nachtragen, da der Arztbrief sie fast immer braucht.
5. **Lange Briefe straffen:** die > 4000-Zeichen-Dateien (teils kopierte
   Enzyklopädie-Prosa) kürzen (siehe licence-review.md).
