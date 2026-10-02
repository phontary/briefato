# Musterbriefe – Referenzbibliothek (Index)

Automatisch erzeugt aus `/workspace/schreibdienst/musterbriefe` am 2026-10-02T18:37:42Z.
**152 Musterbriefe** (index.md der Quelle ausgenommen).

## Gruppierung (Methode)

Jeder Musterbrief wird anhand von Stichwörtern in Dateiname, `title` und den ersten
600 Zeichen des Textes einer Fachgruppe zugeordnet (Regelwerk in
`build_library.py`, `GROUPS`). Spezifische Fachgebiete (Psychiatrie, Gynäkologie,
Onkologie, Neurologie, Nephro/Urologie, Kardio/Angio, Pneumo, Gastro/Hepato,
Endo/Stoffwechsel, Derm/Infektio) haben Vorrang; verbleibende Verletzungs-/
Wundbilder werden Allgemein-/Viszeralchirurgie bzw. Orthopädie/Unfallchirurgie
zugeordnet. `Sonstiges` = keine Regel traf zu.

## Sektions-Normalisierung

Für `sections_present` werden Überschriften auf die kanonischen Namen aus
`manifest.json` (`reference_sections`) abgebildet, z. B. „Klinisches Bild“, „Leitsymptome“,
„Klinische Präsentation“ → `Klinik`; „Bildgebung“, „Radiologie“ → `Diagnostik`;
„Therapie / Empfehlungen“ → `Therapie`; „Therapieempfehlungen bei Entlassung“,
„Entlassung“ → `Therapieempfehlungen bei Entlassung`; „Körperliche Untersuchung“,
„Untersuchungsbefunde“ → `KU`; „Diagnosen (Beispiel)“, „ICD-Code“ → `Diagnosen`.
Die Original-Überschriften stehen je Datei in `headings_raw`.

## Hämatologie / Onkologie (7)

- **Abdominales Lymphom** (`Abdominales_Lymphom.md`) — Abdominales, Lymphom, Bauchlymphom, abdominelle Lymphadenopathie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Atherom (Grützbeutel)** (`Atherom.md`) — Atherom, Grützbeutel, Gruetzbeutel, Epidermoidzyste — Sektionen fehlen: Diagnostik, Nachsorge, Therapieempfehlungen bei Entlassung
- **Brustwandtumor** (`Brustwandtumor.md`) — Brustwandtumor, Thoraxwand, Raumforderung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Duodenaltumor** (`Duodenaltumor.md`) — Duodenaltumor, Zwoelffingerdarm — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Mesenteritis** (`Mesenteritis.md`) — Mesenteritis, Mesenterium — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Papilläre Pankreatitis** (`Papillaere_Pankreatitis.md`) — Papillaere, Pankreatitis, Papilläre, Papillitis, Papillenstenose, ERCP — Sektionen fehlen: Diagnosen
- **Rektumkarzinom** (`Rektumkarzinom.md`) — Rektumkarzinom, Mastdarmkrebs, Enddarmkrebs — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Orthopädie / Unfallchirurgie (35)

- **Abrissfraktur Basis MFK V** (`Abrissfraktur-Basis-MFK-V.md`) — Abrissfraktur, Basis, MFK, Fraktur, MFK 5, fuenfter Mittelfussknochen, Basisfraktur, Mittelfuss — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung
- **AC-Gelenk-Verletzung / Schultergelenksbeschwerden** (`AC-Gelenk-Verletzung_Schulter.md`) — Gelenk, Verletzung, Schulter, Schultergelenksbeschwerden, AC-Gelenk, Schultergelenk, Akromioklavikulargelenk, Schulterverletzung, Tossy — Sektionen fehlen: Nachsorge
- **Baker-Zyste (popliteale Zyste)** (`Baker_Zyste.md`) — Baker, Zyste, popliteale, Bakerzyste, Poplitealzyste, Kniekehle — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Bursitis präpatellaris** (`Bursitis_praepatellaris.md`) — Bursitis, praepatellaris, präpatellaris, Knieschleimbeutelentzuendung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Coxarthrose, Exsikkose, Sturzereignis** (`Coxarthrose_Exsikkose_Sturz.md`) — Coxarthrose, Exsikkose, Sturz, Sturzereignis, Hueftarthrose, Hueftgelenk, Hueftendoprothese — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Daumenfraktur** (`Daumenfraktur.md`) — Daumenfraktur, Daumen — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Distorsion Daumen Grundgelenk** (`Distorsion_Daumen_Grundgelenk.md`) — Distorsion, Daumen, Grundgelenk, Verstauchung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Distorsion des oberen Sprunggelenks** (`Distorsion_Sprunggelenk.md`) — Distorsion, Sprunggelenk, des, oberen, Sprunggelenks, Verstauchung, OSG — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Dorsale Spondylodese LWS (Cage-Dislokation, Revision)** (`Dorsale_Spondylodese_LWS.md`) — Dorsale, Spondylodese, LWS, Cage, Dislokation, Revision, Wirbelsaeule, Versteifung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Fasziitis plantaris** (`Fasziitis_plantaris.md`) — Fasziitis, plantaris, Fersenschmerz, Plantarfaszie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **HWS-Distorsion / Schleudertrauma nach Auffahrunfall** (`HWS-Distorsion_Schleudertrauma.md`) — HWS, Distorsion, Schleudertrauma, nach, Auffahrunfall, Halswirbelsaeule — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung
- **Klavikulafraktur (lateral, disloziert)** (`Klavikulafraktur_lateral_disloziert.md`) — Klavikulafraktur, lateral, disloziert, Schluesselbeinbruch — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kniedistorsion** (`Kniedistorsion.md`) — Kniedistorsion, Knie, Verstauchung — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung
- **Knieendoprothese Periprothetischer Infekt** (`Knieendoprothese_Periprothetischer_Infekt.md`) — Knieendoprothese, Periprothetischer, Infekt, periprothetischer Infekt, Protheseninfekt — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kontusion der Kleinzehe (Contusio digiti minimi pedis)** (`Kontusion_Kleinzehe.md`) — Kontusion, Kleinzehe, der, Contusio, digiti, minimi, pedis, Zehe — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kontusion der Mittelzehe (Contusio digiti pedis)** (`Kontusion_Mittelzehe.md`) — Kontusion, Mittelzehe, der, Contusio, digiti, pedis, Zehe — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kontusion Grundgelenk Kleinfinger** (`Kontusion_Grundgelenk_Kleinfinger.md`) — Kontusion, Grundgelenk, Kleinfinger, Prellung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kontusion Grundgelenk Ringfinger** (`Kontusion_Grundgelenk_Ringfinger.md`) — Kontusion, Grundgelenk, Ringfinger, Prellung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kontusion Handrücken** (`Kontusion_Handruecken.md`) — Kontusion, Handruecken, Handrücken, Prellung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Kontusion und Distorsion der Großzehe (Contusio/Distorsio hallucis)** (`Kontusion_Grosszehe.md`) — Kontusion, Grosszehe, und, Distorsion, der, Großzehe, Contusio, Distorsio, hallucis, Prellung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Lipom** (`Lipom.md`) — Lipom, Fettgeschwulst — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Lumboischialgie / Bandscheibenvorfall / Bandscheibenvorwölbung / lumbale Spinalkanalstenose LWS** (`Lumboischialgie_Bandscheibenvorfall.md`) — Lumboischialgie, Bandscheibenvorfall, Bandscheibenvorwölbung, lumbale, Spinalkanalstenose, LWS, Hexenschuss, Ischias — Sektionen fehlen: Klinik, Verlauf, Nachsorge
- **Metatarsalefraktur Basis MFK II** (`Metatarsalefraktur_Basis_MFK_II.md`) — Metatarsalefraktur, Basis, MFK, Mittelfuss, MFK 2 — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Muskelverspannung / Muskelzerrung paravertebral** (`Muskelverspannung_Muskelzerrung_paravertebral.md`) — Muskelverspannung, Muskelzerrung, paravertebral, Rueckenschmerzen — Sektionen fehlen: Klinik, Verlauf, Therapieempfehlungen bei Entlassung
- **Musterbrief – BWS-Schmerzsyndrom / Nervenirritation** (`BWS-Schmerzsyndrom_Nervenirritation.md`) — BWS, Schmerzsyndrom, Nervenirritation, Musterbrief, Brustwirbelsaeule, Rueckenschmerzen — Sektionen fehlen: KU, Diagnostik, Verlauf, Nachsorge
- **Posttraumatische Gonarthrose** (`Posttraumatische_Gonarthrose.md`) — Posttraumatische, Gonarthrose, Kniearthrose, posttraumatisch — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Prellung (Contusio)** (`Prellung.md`) — Prellung, Contusio, Kontusion — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Radiusköpfchenfraktur (Mason I)** (`Radiuskoepfchenfraktur_Mason_I.md`) — Radiuskoepfchenfraktur, Mason, Radiusköpfchenfraktur, Ellenbogen — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Rippenserienfraktur (Z.n., konsolidiert)** (`Rippenserienfraktur.md`) — Rippenserienfraktur, konsolidiert, Rippenbruch, Rippenfraktur — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schenkelhalsfraktur** (`Schenkelhalsfraktur.md`) — Schenkelhalsfraktur, Oberschenkelhalsbruch, Hueftfraktur — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schulterluxation / V.a. Schulterluxation** (`Schulterluxation.md`) — Schulterluxation, Schulterverrenkung, Luxation — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schulterprellung / Contusio humeri** (`Schulterprellung.md`) — Schulterprellung, Contusio, humeri, Contusio humeri, Prellung — Sektionen fehlen: Verlauf, Nachsorge
- **Tibiakopffraktur** (`Tibiakopffraktur.md`) — Tibiakopffraktur, Schienbein — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Weber-C-Fraktur des oberen Sprunggelenks (ältere, nicht dislozierte Fraktur – konservativ)** (`Weber_C_Fraktur.md`) — Weber, Fraktur, des, oberen, Sprunggelenks, ältere, nicht, dislozierte, konservativ, Weber-C-Fraktur — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Wirbelkörperhämangiom** (`Wirbelkörperhämangiom.md`) — Wirbelkörperhämangiom, Wirbelkoerperhaemangiom, Haemangiom, Wirbel — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Dermatologie / Infektiologie (5)

- **Abszess** (`Abszess.md`) — Abszess, Eiteransammlung, Inzision, Drainage, Hautabszess, perianaler Abszess — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Bursitis olecrani** (`Bursitis_olecrani.md`) — Bursitis, olecrani, Ellenbogenschleimbeutelentzuendung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Insektenstich** (`Insektenstich.md`) — Insektenstich, Insektenbiss, Stich — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Panaritium** (`Panaritium.md`) — Panaritium, Fingerentzuendung, Umlauf — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Zeckenstich** (`Zeckenstich.md`) — Zeckenstich, Zeckenbiss, Borreliose, FSME — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Sonstiges (3)

- **Acne inversa – Musterbrief** (`Acne-inversa.md`) — Acne, inversa, Musterbrief, Akne inversa, Hidradenitis suppurativa, Schweissdruesenentzuendung — Sektionen fehlen: Klinik, KU, Diagnostik, Therapie, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Diabetisches Fußsyndrom (DFS)** (`Diabetisches_Fusssyndrom.md`) — Diabetisches, Fusssyndrom, Fußsyndrom, DFS, Diabetisches Fusssyndrom, diabetischer Fuss, Ulkus — Sektionen fehlen: KU, Diagnostik, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schwellung Handrücken nach Braunüle** (`Schwellung_Handruecken_nach_Braunuele.md`) — Schwellung, Handruecken, nach, Braunuele, Handrücken, Braunüle, Paravasat — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Kardiologie / Angiologie (19)

- **Adipositas** (`Adipositas.md`) — Adipositas, Uebergewicht, Fettleibigkeit, BMI — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Adipositas permagna** (`Adipositas_permagna.md`) — Adipositas, permagna, Adipositas permagna, starkes Uebergewicht, morbide Adipositas — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Analvenenthrombose** (`Analvenenthrombose.md`) — Analvenenthrombose, Haemorrhoidalthrombose, Perianalthrombose, Analthrombose — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Biliäre Pankreatitis** (`Biliaere_Pankreatitis.md`) — Biliaere, Pankreatitis, Biliäre, Bauchspeicheldruesenentzuendung, biliaer — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Chronische Herzinsuffizienz / Kardiale Dekompensation** (`Chronische_Herzinsuffizienz_kardiale_Dekompensation.md`) — Chronische, Herzinsuffizienz, kardiale, Dekompensation, Kardiale, Herzschwaeche, kardiale Dekompensation, NYHA — Sektionen fehlen: Klinik, KU, Diagnostik, Therapie, Nachsorge, Diagnosen
- **COPD (Chronisch obstruktive Lungenerkrankung)** (`COPD.md`) — COPD, Chronisch, obstruktive, Lungenerkrankung, chronisch obstruktive Lungenerkrankung, Lungenemphysem — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **CVI / Stauungsdermatitis / Ulcus cruris venosum** (`CVI_Stauungsdermatitis_Unterschenkel.md`) — CVI, Stauungsdermatitis, Unterschenkel, Ulcus, cruris, venosum, chronisch venoese Insuffizienz, Ulcus cruris, offenes Bein — Sektionen fehlen: Klinik, KU, Diagnostik, Therapie, Nachsorge, Diagnosen
- **Dekubitus** (`Dekubitus.md`) — Dekubitus, Druckgeschwuer, Wundliegen — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Diabetes mellitus Typ 1** (`Diabetes_mellitus_Typ1.md`) — Diabetes, mellitus, Typ1, Typ, Diabetes Typ 1, Zuckerkrankheit — Sektionen fehlen: Klinik, KU, Diagnostik, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Drei-Gefäß-KHK (Koronare Herzkrankheit)** (`Drei-Gefaess_KHK.md`) — Drei, Gefaess, KHK, Gefäß, Koronare, Herzkrankheit, koronare Herzkrankheit, Dreigefaesserkrankung, Herzkatheter — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Erysipel** (`Erysipel.md`) — Erysipel, Wundrose, Hautinfektion — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Herzinsuffizienz** (`Herzinsuffizienz.md`) — Herzinsuffizienz, Herzschwaeche, Herzmuskelschwaeche, Dekompensation — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Knieendoprothese Implantation Pangonarthrose** (`Knieendoprothese_Implantation_Pangonarthrose.md`) — Knieendoprothese, Implantation, Pangonarthrose, Knie-TEP, Gonarthrose, Kniegelenk — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Lungenembolie** (`Lungenembolie.md`) — Lungenembolie, Pulmonalembolie, Embolie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Osteomyelitis mit Zehenstrahl-Amputation (Fuß)** (`Osteomyelitis_Zehenstrahlamputation.md`) — Osteomyelitis, Zehenstrahlamputation, mit, Zehenstrahl, Amputation, Fuß, Knochenmarkentzuendung, Zehenamputation — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **pAVK** (`pAVK.md`) — pAVK, periphere arterielle Verschlusskrankheit, Schaufensterkrankheit — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Phlegmone (infizierte Weichteilphlegmone)** (`Phlegmone.md`) — Phlegmone, infizierte, Weichteilphlegmone, Weichteilinfektion, Zellulitis — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Tiefe Beinvenenthrombose (TVT)** (`Tiefe_Beinvenenthrombose_TVT.md`) — Tiefe, Beinvenenthrombose, TVT, tiefe Beinvenenthrombose, Thrombose — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Varikose** (`Varikose.md`) — Varikose, Krampfadern, Varizen — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Neurologie / Neurochirurgie (10)

- **Akut auf chronisches Subduralhämatom** (`Akut_auf_chronisches_Subduralhaematom.md`) — Akut, auf, chronisches, Subduralhaematom, Subduralhämatom, SDH, subdurales Haematom, Schae-delhirntrauma, Kopfblutung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Arterielle Hypertonie** (`Arterielle_Hypertonie.md`) — Arterielle, Hypertonie, Bluthochdruck, arterielle Hypertonie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Commotio cerebri (Gehirnerschütterung)** (`Commotio_cerebri.md`) — Commotio, cerebri, Gehirnerschütterung, Commotio cerebri, Gehirnerschuetterung, SHT — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Frontobasisfraktur mit Spannungspneumozephalus** (`Frontobasisfraktur_Spannungspneumozephalus.md`) — Frontobasisfraktur, Spannungspneumozephalus, mit, Schaedelbasis, Pneumozephalus — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Nasenbeinfraktur** (`Nasenbeinfraktur.md`) — Nasenbeinfraktur, Nasenbeinbruch — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Permanentes Vorhofflimmern** (`Vorhofflimmern_permanent.md`) — Vorhofflimmern, permanent, Permanentes, Arrhythmie, Herzrhythmusstoerung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schlafapnoe-Syndrom / Adipositas-Hyperventilation** (`Schlafapnoe_Syndrom.md`) — Schlafapnoe, Syndrom, Adipositas, Hyperventilation, Schnarchen, Apnoe — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schädelhirntrauma (SHT)** (`Schaedelhirntrauma.md`) — Schaedelhirntrauma, Schädelhirntrauma, SHT, Kopfverletzung — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schürfwunden (Abschürfungen) nach Sturz** (`Schuerfwunden_Abschuerfungen.md`) — Schuerfwunden, Abschuerfungen, Schürfwunden, Abschürfungen, nach, Sturz, Schuerfwunde, Abschuerfung, Hautabschuerfung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **V.a. zerebrale Ischämie / brachofaziale Hemiparese** (`Apoplex_Hemiparese.md`) — Apoplex, Hemiparese, zerebrale, Ischämie, brachofaziale, Schlaganfall, Hirninfarkt, zerebrale Ischaemie — Sektionen fehlen: Nachsorge, Diagnosen

## Gastroenterologie / Hepatologie (27)

- **Akute Colitis** (`Akute_Colitis.md`) — Akute, Colitis, Dickdarmentzuendung, Kolitis — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Akute Gastritis** (`Akute_Gastritis.md`) — Akute, Gastritis, Magenschleimhautentzuendung, Magenschmerzen — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Akute Obstipation** (`Akute_Obstipation.md`) — Akute, Obstipation, Verstopfung, Stuhlverhalt — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Analfistel / Rektumfistel (extrasphinktär)** (`Analfistel_Rektumfistel.md`) — Analfistel, Rektumfistel, extrasphinktär, Fistel, perianale Fistel — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **C-Gastritis bei Gallereflux** (`C-Gastritis_bei_Gallereflux.md`) — Gastritis, bei, Gallereflux, C-Gastritis, chemische Gastritis — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Choledocholithiasis** (`Choledocholithiasis.md`) — Choledocholithiasis, Gallengangsteine, DHC-Stein, Gallenwegssteine — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Cholezystolithiasis** (`Cholezystolithiasis.md`) — Cholezystolithiasis, Gallensteine, Gallenkolik, Cholelithiasis, Cholezystitis, Gallenblase — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Chronisch-entzündliche Veränderungen des Colon descendens und rektosigmoidal** (`Chronisch_entzuendliche_Colonveraenderungen_sigmoidal.md`) — Chronisch, entzuendliche, Colonveraenderungen, sigmoidal, entzündliche, Veränderungen, des, Colon, descendens, und — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Dünndarminvagination** (`Duenndarminvagination.md`) — Duenndarminvagination, Dünndarminvagination, Invagination, Duennndarm, Ileus — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Epigastrische Narbenhernie – IPOM-Plastik** (`Narbenhernie_epigastrische_IPOM.md`) — Narbenhernie, epigastrische, IPOM, Epigastrische, Plastik, epigastrisch — Sektionen fehlen: KU, Nachsorge, Therapieempfehlungen bei Entlassung
- **Gangränöse Cholezystitis / Z.n. offener CHE** (`Gangraenose_Cholezystitis_CHE.md`) — Gangraenose, Cholezystitis, CHE, Gangränöse, offener, gangraenoes, Cholezystektomie — Sektionen fehlen: Nachsorge, Diagnosen
- **Gastroparese** (`Gastroparese.md`) — Gastroparese, Magenentleerungsstoerung, Magenlaehmung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Hepatomegalie mit zystoiden Leberläsionen** (`Hepatomegalie_mit_zystoiden_Leberaesionen.md`) — Hepatomegalie, mit, zystoiden, Leberaesionen, Leberläsionen, Leberlaesionen, Leberzysten — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Hämorrhoiden** (`Hämorrhoiden.md`) — Hämorrhoiden, Analleiden, Analbeschwerden — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Iatrogene Zökumperforation nach Koloskopie** (`Iatrogene_Zoekumperforation.md`) — Iatrogene, Zoekumperforation, Zökumperforation, nach, Koloskopie, Perforation, Blinddarm — Sektionen fehlen: KU, Therapieempfehlungen bei Entlassung, Diagnosen
- **Leberhämangiom** (`Leberhämangiom.md`) — Leberhämangiom, Haemangiom, Leber, Lebertumor, benigne Leberlaesion — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Leberzirrhose mit Aszites – V.a. infektiöse Aszitis** (`Leberzirrhose_Aszites_infektioese_Aszitis.md`) — Leberzirrhose, Aszites, infektioese, Aszitis, mit, infektiöse, Bauchwassersucht — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Morbus Crohn** (`Morbus_Crohn.md`) — Morbus, Crohn, CED, Darmentzuendung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Musterbrief: Dünndarmileus / Bridenileus** (`Duennndarmileus_Bridenileus.md`) — Duennndarmileus, Bridenileus, Musterbrief, Dünndarmileus, Ileus, Briden, Darmverschluss — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Musterbrief: Paralytischer Ileus** (`Paralytischer_Ileus.md`) — Paralytischer, Ileus, Musterbrief, paralytischer Ileus, Darmverschluss — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Nabelhernie** (`Nabelhernie.md`) — Nabelhernie, Nabelbruch, Hernie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Pangastritis / Antrumbetonte Gastritis** (`Pangastritis.md`) — Pangastritis, Antrumbetonte, Gastritis, Helicobacter, Magenschleimhautentzuendung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Proktalgie / Analschmerz** (`Proktalgie.md`) — Proktalgie, Analschmerz, Analgie — Sektionen fehlen: Nachsorge, Diagnosen
- **Proktitis** (`Proktitis.md`) — Proktitis, Mastdarmentzuendung, Rektum — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schenkelhernie / Femoralhernie** (`Schenkelhernie_Femoralhernie.md`) — Schenkelhernie, Femoralhernie, Hernie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **V.a. Gallenblasenpolypen/-konkremente** (`Gallenblasenpolypen_Konkremente_Verdacht.md`) — Gallenblasenpolypen, Konkremente, Verdacht, konkremente, Gallenblase — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Ösophagusvarizen** (`Ösophagusvarizen.md`) — Ösophagusvarizen, Oesophagusvarizen, Speiseroehrenvarizen, Varizen, Leberzirrhose — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Psychiatrie (7)

- **Akute Divertikulitis** (`Akute_Divertikulitis.md`) — Akute, Divertikulitis, Divertikel, Sigma — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Akute Suizidalität / Suizidversuch** (`Suizidalitaet.md`) — Suizidalitaet, Akute, Suizidalität, Suizidversuch, Eigengefaehrdung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Anastomositis / entzündliche Schleimhautreaktion nach Hemikolektomie** (`Anastomositis_nach_Hemikolektomie.md`) — Anastomositis, nach, Hemikolektomie, entzündliche, Schleimhautreaktion, Anastomose, Dickdarmoperation — Sektionen fehlen: Nachsorge, Diagnosen
- **Angststörung** (`Angststoerung.md`) — Angststoerung, Angststörung, Panik, Angst — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Borderline-Persönlichkeitsstörung / Suizidalität / Eigengefährdung** (`Borderline-Persoenlichkeitsstoerung_Suizidalitaet.md`) — Borderline, Persoenlichkeitsstoerung, Suizidalitaet, Persönlichkeitsstörung, Suizidalität, Eigengefährdung, Eigengefaehrdung — Sektionen fehlen: KU, Diagnostik, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Fremdkörperverdacht Nadelspitze nach i.v. Drogenkonsum** (`Fremdkoerperverdacht_Nadelspitze_nach_iv_Drogenkonsum.md`) — Fremdkoerperverdacht, Nadelspitze, nach, Drogenkonsum, Fremdkörperverdacht, Fremdkoerper, intravasal — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Stichverletzung** (`Stichverletzung.md`) — Stichverletzung, Stichwunde, Verletzung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Nephrologie / Urologie (12)

- **Akuter Harnverhalt** (`Akuter_Harnverhalt.md`) — Akuter, Harnverhalt, Harnverhalten, Blasenentleerungsstoerung, Katheter — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Chronische Niereninsuffizienz (CKD, nicht dialysepflichtig)** (`Chronische_Niereninsuffizienz_CKD3.md`) — Chronische, Niereninsuffizienz, CKD3, CKD, nicht, dialysepflichtig, chronische Nierenkrankheit — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Chronische Niereninsuffizienz (dialysepflichtig)** (`Chronische_Niereninsuffizienz_dialysepflichtig.md`) — Chronische, Niereninsuffizienz, dialysepflichtig, Dialyse, Nierenversagen — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Demers-Katheter (Dysfunktion, Wechsel)** (`Demerskatheter_Dysfunktion_Wechsel.md`) — Demerskatheter, Dysfunktion, Wechsel, Demers, Katheter, Zystostomie, Blasenkatheter, Katheterwechsel — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Diabetes mellitus Typ 2** (`Diabetes_mellitus_Typ2.md`) — Diabetes, mellitus, Typ2, Typ, Diabetes Typ 2, Zuckerkrankheit, Hyperglykaemie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Dialyseshunt (postoperative Nachblutung, Revisions-OP)** (`Dialyseshunt_Nachblutung_Revision.md`) — Dialyseshunt, Nachblutung, Revision, postoperative, Revisions, Shunt, Haemodialyse — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Harnwegsinfekt (V.a.)** (`Harnwegsinfekt.md`) — Harnwegsinfekt, Blasenentzuendung, Zystitis, HWI, UTI — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Makrozytäre hypochrome Anämie** (`Makrozytäre_hypochrome_Anaemie.md`) — Makrozytäre, hypochrome, Anaemie, Anämie, Blutarmut, makrozytär — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Nierenkolik bei Harnstauungsniere mit einliegender Harnleiterschiene** (`Nierenkolik_bei_Harnstauungsniere_mit_Harnleiterschiene.md`) — Nierenkolik, bei, Harnstauungsniere, mit, Harnleiterschiene, einliegender, Harnstau, Niere, Kolik — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **pAVK / Mediasklerose** (`pAVK_Mediasklerose.md`) — pAVK, Mediasklerose, periphere arterielle Verschlusskrankheit — Sektionen fehlen: KU, Diagnostik, Therapie, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Portexplantation (Portentfernung)** (`Portexplantation.md`) — Portexplantation, Portentfernung, Port — Sektionen fehlen: KU, Diagnostik, Verlauf, Therapieempfehlungen bei Entlassung
- **Urolithiasis – Musterbrief / Template** (`Urolithiasis.md`) — Urolithiasis, Musterbrief, Template, Nierensteine, Harnsteine, Nephrolithiasis, Kolik — Sektionen fehlen: Nachsorge

## Allgemein- / Viszeralchirurgie (17)

- **Alkoholintoxikation** (`Alkoholintoxikation.md`) — Alkoholintoxikation, Alkoholvergiftung, Ethanol, Intoxikation — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Appendizitis epiploica** (`Appendizitis_epiploica.md`) — Appendizitis, epiploica, Appendizitis epiploica, Blinddarmentzuendung, Appendix — Sektionen fehlen: Nachsorge, Diagnosen
- **Axiale Hiatushernie** (`Axiale_Hiatushernie.md`) — Axiale, Hiatushernie, Zwerchfellhernie, Reflux — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Bissverletzung** (`Bissverletzung.md`) — Bissverletzung, Bisswunde, Hundebiss, Katzenbiss — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Fingerendgliedamputation (Fingerspitzenamputation)** (`Fingerendgliedamputation.md`) — Fingerendgliedamputation, Fingerspitzenamputation, Fingeramputation, Endglied, Amputation — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **laparoskopische-appendektomie** (`laparoskopische-appendektomie.md`) — laparoskopische, appendektomie, Appendizitis, Appendektomie, Blinddarm, Appendix, laparoskopisch — Sektionen fehlen: KU, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen
- **Leistenhernie / Inguinalhernie – Lichtenstein (offene, anterior/epifaszial) Technik** (`Leistenhernie_Inguinalhernie_Lichtenstein.md`) — Leistenhernie, Inguinalhernie, Lichtenstein, offene, anterior, epifaszial, Technik — Sektionen fehlen: KU, Nachsorge, Therapieempfehlungen bei Entlassung
- **Metallentfernung am Außenknöchel (Z.n. Fraktur des Außenknöchels)** (`Metallentfernung_Aussenknoechel.md`) — Metallentfernung, Aussenknoechel, Außenknöchel, Fraktur, des, Außenknöchels, Plattenentfernung, Osteosynthesematerial — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Nadelstichverletzung** (`Nadelstichverletzung.md`) — Nadelstichverletzung, Nadelstich, Stichverletzung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Nagelverletzung mit subungualem Hämatom (Fingerquetschung)** (`Nagelverletzung_Subunguales_Haematom.md`) — Nagelverletzung, Subunguales, Haematom, mit, subungualem, Hämatom, Fingerquetschung, subunguales Haematom — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Narbenhernien (epigastrisch)** (`Narbenhernien_epigastrisch.md`) — Narbenhernien, epigastrisch, Narbenhernie — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Patellafraktur** (`Patellafraktur.md`) — Patellafraktur, Kniescheibenbruch — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Rektusdiastase** (`Rektusdiastase.md`) — Rektusdiastase, Bauchmuskel — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Schnittwunde** (`Schnittwunde.md`) — Schnittwunde, Wunde, Verletzung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Verbrennung 2. Grades** (`Verbrennung_2_Grades.md`) — Verbrennung, Grades, Brandwunde, Verbruehung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Weichteilablösung Oberarm (Decollement)** (`Weichteilabloesung_Oberarm_Decollement.md`) — Weichteilabloesung, Oberarm, Decollement, Weichteilablösung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Zehenfraktur (Fraktur einer Phalanx digitorum pedis)** (`Zehenfraktur.md`) — Zehenfraktur, Fraktur, einer, Phalanx, digitorum, pedis, Zehenbruch — Sektionen fehlen: KU, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen

## Endokrinologie / Stoffwechsel (6)

- **Erysipel (Wundrose)** (`Erysipel_Wundrose.md`) — Erysipel, Wundrose, Hautinfektion — Sektionen fehlen: KU, Nachsorge
- **Gichtarthritis (Arthritis urica)** (`Gichtarthritis.md`) — Gichtarthritis, Arthritis, urica, Gicht, Arthritis urica, Hyperurikaemie, Gichtanfall — Sektionen fehlen: KU, Nachsorge, Diagnosen
- **Glutealfistel / Glutealabszess (superinfiziert)** (`Glutealfistel_Glutealabszess.md`) — Glutealfistel, Glutealabszess, superinfiziert, Gesaessabszess, Fistel — Sektionen fehlen: Klinik, KU, Diagnostik, Therapie, Nachsorge, Diagnosen
- **Humerusfraktur** (`Humerusfraktur.md`) — Humerusfraktur, Oberarmbruch, Humerus, Oberarm — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Musterbrief: Osteoporotische Wirbelkörperfraktur** (`Osteoporotische_Wirbelkoerperfraktur.md`) — Osteoporotische, Wirbelkoerperfraktur, Musterbrief, Wirbelkörperfraktur, Osteoporose, Sinterungsfraktur — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Musterbrief: Struma nodosa / Hyperthyreose** (`Struma_nodosa_Hyperthyreose.md`) — Struma, nodosa, Hyperthyreose, Musterbrief, Schilddruese, Schilddruesenknoten, Kropf — Sektionen fehlen: Klinik, KU, Diagnostik, Therapie, Verlauf, Nachsorge, Therapieempfehlungen bei Entlassung, Diagnosen

## Pneumologie (2)

- **Leistenhernie / Inguinalhernie – TAPP (Transabdominelle Präperitoneale Plastik)** (`Leistenhernie_Inguinalhernie_TAPP.md`) — Leistenhernie, Inguinalhernie, TAPP, Transabdominelle, Präperitoneale, Plastik — Sektionen fehlen: KU, Nachsorge, Therapieempfehlungen bei Entlassung
- **Pneumonie** (`Pneumonie.md`) — Pneumonie, Lungenentzuendung — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

## Gynäkologie (2)

- **Rupturierte Ovarialzyste** (`Rupturierte_Ovarialzyste.md`) — Rupturierte, Ovarialzyste, Eierstockzyste, rupturiert — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen
- **Uterusmyom** (`Uterusmyom.md`) — Uterusmyom, Myom, Gebaermutter — Sektionen fehlen: KU, Verlauf, Therapieempfehlungen bei Entlassung, Diagnosen

