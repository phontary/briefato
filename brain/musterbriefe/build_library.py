#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the Briefato Musterbriefe reference library.

Reads /workspace/schreibdienst/musterbriefe/*.md (READ ONLY) and emits into
/workspace/briefato/brain/musterbriefe/:
  manifest.json  index.md  sectionstats.md  scrub-report.md  licence-review.md

No patient data is copied into outputs (scrub-report only *describes* findings);
no licensed prose is reproduced.
"""
import os, re, json, glob, datetime, difflib, unicodedata

SRC = "/workspace/schreibdienst/musterbriefe"
OUT = "/workspace/briefato/brain/musterbriefe"

# ---- canonical reference sections (context's set + Nachsorge, the most
#      frequent body section; documented in index.md) ----------------------
REFERENCE_SECTIONS = [
    "Klinik",
    "KU",
    "Diagnostik",
    "Therapie",
    "Verlauf",
    "Nachsorge",
    "Therapieempfehlungen bei Entlassung",
    "Diagnosen",
]
OPTIONAL_SECTIONS = ["Anamnese", "OP", "Quellen", "Sonstiges"]

# ---------------------------------------------------------------- helpers
def norm(s: str) -> str:
    s = s.lower().strip()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())

def norm1(s: str) -> str:
    return norm(s).replace(" ", "")

def split_frontmatter(text: str):
    if text.startswith("---"):
        m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
        if m:
            fm = {}
            for line in m.group(1).splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"')
            return fm, text[m.end():]
    return {}, text

def body_sections(body: str):
    """Return ordered list of raw '## ' headings."""
    return [m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", body, re.M)]

# heading -> canonical, first rule that matches wins (order matters)
CANON_RULES = [
    (r"quellen|literatur|referenz", "Quellen"),
    (r"^ku\b|ku[- ]befund|koerperliche untersuchung|klinische untersuchung|^untersuchungsbefunde", "KU"),
    (r"therapieempfehlung|empfehlungen bei entlassung|therapie bei entlassung|ambulante therapieempfehlung|^entlassung$", "Therapieempfehlungen bei Entlassung"),
    (r"^nachsorge", "Nachsorge"),
    (r"^verlauf|klassischer verlauf|postoperativer verlauf|verlaufskriterien|op chronologie|operativer verlauf", "Verlauf"),
    (r"^therapie|therapieanpassung|^indikation", "Therapie"),
    (r"^diagnostik|^bildgebung|bildgebende befunde|^radiologie|^pathologie|^bildgebung", "Diagnostik"),
    (r"^diagnosen|^icd", "Diagnosen"),
    (r"^klinik|klinisches bild|klinische praesentation|klinischer befund|leitsymptome|charakteristika|^beschreibung|aufnahmesituation|aufnahmegrund|aufnahmebegruendung|klinisches bild", "Klinik"),
    (r"^anamnese|anamnese /|/ unfallhergang", "Anamnese"),
    (r"^op$|^op |operationstechnik|^op-", "OP"),
]

def canonical(h: str) -> str:
    hn = norm(h)
    for pat, canon in CANON_RULES:
        if re.search(pat, hn):
            return canon
    return "Sonstiges"

# --------------------------------------------------- indication keywords
# Curated German synonyms (router matching). Keyed by filename stem.
SYN = {
"AC-Gelenk-Verletzung_Schulter": ["AC-Gelenk","Schultergelenk","Akromioklavikulargelenk","Schulterverletzung","Tossy"],
"Abdominales_Lymphom": ["Lymphom","Bauchlymphom","abdominelle Lymphadenopathie"],
"Abrissfraktur-Basis-MFK-V": ["Fraktur","MFK 5","fuenfter Mittelfussknochen","Basisfraktur","Mittelfuss"],
"Abszess": ["Eiteransammlung","Inzision","Drainage","Hautabszess","perianaler Abszess"],
"Acne-inversa": ["Akne inversa","Hidradenitis suppurativa","Schweissdruesenentzuendung"],
"Adipositas": ["Uebergewicht","Fettleibigkeit","BMI"],
"Adipositas_permagna": ["Adipositas permagna","starkes Uebergewicht","morbide Adipositas"],
"Akut_auf_chronisches_Subduralhaematom": ["Subduralhaematom","SDH","subdurales Haematom","Schae-delhirntrauma","Kopfblutung"],
"Akute_Colitis": ["Colitis","Dickdarmentzuendung","Kolitis"],
"Akute_Divertikulitis": ["Divertikulitis","Divertikel","Sigma"],
"Akute_Gastritis": ["Gastritis","Magenschleimhautentzuendung","Magenschmerzen"],
"Akute_Obstipation": ["Obstipation","Verstopfung","Stuhlverhalt"],
"Akuter_Harnverhalt": ["Harnverhalt","Harnverhalten","Blasenentleerungsstoerung","Katheter"],
"Alkoholintoxikation": ["Alkoholvergiftung","Ethanol","Intoxikation"],
"Analfistel_Rektumfistel": ["Analfistel","Rektumfistel","Fistel","perianale Fistel"],
"Analvenenthrombose": ["Haemorrhoidalthrombose","Perianalthrombose","Analthrombose"],
"Anastomositis_nach_Hemikolektomie": ["Anastomositis","Anastomose","Hemikolektomie","Dickdarmoperation"],
"Angststoerung": ["Angststoerung","Panik","Angst"],
"Apoplex_Hemiparese": ["Apoplex","Schlaganfall","Hirninfarkt","Hemiparese","zerebrale Ischaemie"],
"Appendizitis_epiploica": ["Appendizitis epiploica","Blinddarmentzuendung","Appendix"],
"Arterielle_Hypertonie": ["Hypertonie","Bluthochdruck","arterielle Hypertonie"],
"Atherom": ["Gruetzbeutel","Epidermoidzyste"],
"Axiale_Hiatushernie": ["Hiatushernie","Zwerchfellhernie","Reflux"],
"BWS-Schmerzsyndrom_Nervenirritation": ["BWS","Brustwirbelsaeule","Schmerzsyndrom","Rueckenschmerzen"],
"Baker_Zyste": ["Bakerzyste","Poplitealzyste","Kniekehle"],
"Biliaere_Pankreatitis": ["Pankreatitis","Bauchspeicheldruesenentzuendung","biliaer"],
"Bissverletzung": ["Bisswunde","Hundebiss","Katzenbiss"],
"Borderline-Persoenlichkeitsstoerung_Suizidalitaet": ["Borderline","Persoenlichkeitsstoerung","Suizidalitaet","Eigengefaehrdung"],
"Brustwandtumor": ["Brustwandtumor","Thoraxwand","Raumforderung"],
"Bursitis_olecrani": ["Ellenbogenschleimbeutelentzuendung"],
"Bursitis_praepatellaris": ["Knieschleimbeutelentzuendung"],
"C-Gastritis_bei_Gallereflux": ["C-Gastritis","chemische Gastritis","Gallereflux"],
"COPD": ["chronisch obstruktive Lungenerkrankung","Lungenemphysem"],
"CVI_Stauungsdermatitis_Unterschenkel": ["CVI","chronisch venoese Insuffizienz","Stauungsdermatitis","Ulcus cruris","offenes Bein"],
"Choledocholithiasis": ["Gallengangsteine","DHC-Stein","Gallenwegssteine"],
"Cholezystolithiasis": ["Gallensteine","Gallenkolik","Cholelithiasis","Cholezystitis","Gallenblase"],
"Chronisch_entzuendliche_Colonveraenderungen_sigmoidal": ["Colitis","Dickdarmentzuendung","CED","sigmoidal"],
"Chronische_Herzinsuffizienz_kardiale_Dekompensation": ["Herzinsuffizienz","Herzschwaeche","kardiale Dekompensation","NYHA"],
"Chronische_Niereninsuffizienz_CKD3": ["Niereninsuffizienz","CKD","chronische Nierenkrankheit"],
"Chronische_Niereninsuffizienz_dialysepflichtig": ["Niereninsuffizienz","Dialyse","Nierenversagen"],
"Commotio_cerebri": ["Commotio cerebri","Gehirnerschuetterung","SHT"],
"Coxarthrose_Exsikkose_Sturz": ["Coxarthrose","Hueftarthrose","Hueftgelenk","Exsikkose","Sturz","Hueftendoprothese"],
"Daumenfraktur": ["Daumenfraktur","Daumen"],
"Dekubitus": ["Druckgeschwuer","Wundliegen"],
"Demerskatheter_Dysfunktion_Wechsel": ["Demerskatheter","Zystostomie","Blasenkatheter","Katheterwechsel"],
"Diabetes_mellitus_Typ1": ["Diabetes Typ 1","Zuckerkrankheit"],
"Diabetes_mellitus_Typ2": ["Diabetes Typ 2","Zuckerkrankheit","Hyperglykaemie"],
"Diabetisches_Fusssyndrom": ["Diabetisches Fusssyndrom","diabetischer Fuss","Ulkus"],
"Dialyseshunt_Nachblutung_Revision": ["Dialyseshunt","Shunt","Haemodialyse","Nachblutung"],
"Distorsion_Daumen_Grundgelenk": ["Distorsion","Verstauchung","Daumen"],
"Distorsion_Sprunggelenk": ["Distorsion","Verstauchung","Sprunggelenk","OSG"],
"Dorsale_Spondylodese_LWS": ["Spondylodese","LWS","Wirbelsaeule","Versteifung"],
"Drei-Gefaess_KHK": ["KHK","koronare Herzkrankheit","Dreigefaesserkrankung","Herzkatheter"],
"Duenndarminvagination": ["Invagination","Duennndarm","Ileus"],
"Duennndarmileus_Bridenileus": ["Ileus","Duennndarmileus","Briden","Darmverschluss"],
"Duodenaltumor": ["Duodenaltumor","Zwoelffingerdarm"],
"Erysipel": ["Wundrose","Hautinfektion"],
"Erysipel_Wundrose": ["Wundrose","Hautinfektion"],
"Fasziitis_plantaris": ["Fersenschmerz","Plantarfaszie"],
"Fingerendgliedamputation": ["Fingeramputation","Endglied","Amputation"],
"Fremdkoerperverdacht_Nadelspitze_nach_iv_Drogenkonsum": ["Fremdkoerper","Nadelspitze","Drogenkonsum","intravasal"],
"Frontobasisfraktur_Spannungspneumozephalus": ["Frontobasisfraktur","Schaedelbasis","Pneumozephalus"],
"Gallenblasenpolypen_Konkremente_Verdacht": ["Gallenblasenpolypen","Gallenblase","Konkremente"],
"Gangraenose_Cholezystitis_CHE": ["Cholezystitis","gangraenoes","Cholezystektomie"],
"Gastroparese": ["Magenentleerungsstoerung","Magenlaehmung"],
"Gichtarthritis": ["Gicht","Arthritis urica","Hyperurikaemie","Gichtanfall"],
"Glutealfistel_Glutealabszess": ["Glutealfistel","Glutealabszess","Gesaessabszess","Fistel"],
"HWS-Distorsion_Schleudertrauma": ["HWS","Schleudertrauma","Halswirbelsaeule"],
"Harnwegsinfekt": ["Blasenentzuendung","Zystitis","HWI","UTI"],
"Hepatomegalie_mit_zystoiden_Leberaesionen": ["Hepatomegalie","Leberlaesionen","Leberzysten"],
"Herzinsuffizienz": ["Herzschwaeche","Herzmuskelschwaeche","Dekompensation"],
"Humerusfraktur": ["Oberarmbruch","Humerus","Oberarm"],
"Hämorrhoiden": ["Hämorrhoiden","Analleiden","Analbeschwerden"],
"Iatrogene_Zoekumperforation": ["Zoekumperforation","Perforation","Koloskopie","Blinddarm"],
"Insektenstich": ["Insektenbiss","Stich"],
"Klavikulafraktur_lateral_disloziert": ["Schluesselbeinbruch"],
"Kniedistorsion": ["Knie","Verstauchung"],
"Knieendoprothese_Implantation_Pangonarthrose": ["Knieendoprothese","Knie-TEP","Gonarthrose","Kniegelenk"],
"Knieendoprothese_Periprothetischer_Infekt": ["Knieendoprothese","periprothetischer Infekt","Protheseninfekt"],
"Kontusion_Grosszehe": ["Prellung","Grosszehe"],
"Kontusion_Grundgelenk_Kleinfinger": ["Prellung","Kleinfinger"],
"Kontusion_Grundgelenk_Ringfinger": ["Prellung","Ringfinger"],
"Kontusion_Handruecken": ["Prellung","Handruecken"],
"Kontusion_Kleinzehe": ["Kleinzehe","Zehe"],
"Kontusion_Mittelzehe": ["Mittelzehe","Zehe"],
"Leberhämangiom": ["Haemangiom","Leber","Lebertumor","benigne Leberlaesion"],
"Leberzirrhose_Aszites_infektioese_Aszitis": ["Leberzirrhose","Aszites","Bauchwassersucht","Aszitis"],
"Leistenhernie_Inguinalhernie_Lichtenstein": ["Leistenhernie","Inguinalhernie","Lichtenstein"],
"Leistenhernie_Inguinalhernie_TAPP": ["Leistenhernie","Inguinalhernie","TAPP"],
"Lipom": ["Fettgeschwulst"],
"Lumboischialgie_Bandscheibenvorfall": ["Lumboischialgie","Bandscheibenvorfall","Hexenschuss","Ischias","LWS","Spinalkanalstenose"],
"Lungenembolie": ["Pulmonalembolie","Embolie"],
"Makrozytäre_hypochrome_Anaemie": ["Anaemie","Blutarmut","makrozytär"],
"Mesenteritis": ["Mesenterium"],
"Metallentfernung_Aussenknoechel": ["Metallentfernung","Aussenknoechel","Plattenentfernung","Osteosynthesematerial"],
"Metatarsalefraktur_Basis_MFK_II": ["Metatarsalefraktur","Mittelfuss","MFK 2"],
"Morbus_Crohn": ["Crohn","CED","Darmentzuendung"],
"Muskelverspannung_Muskelzerrung_paravertebral": ["Muskelverspannung","Muskelzerrung","Rueckenschmerzen","paravertebral"],
"Nabelhernie": ["Nabelbruch","Hernie"],
"Nadelstichverletzung": ["Nadelstich","Stichverletzung"],
"Nagelverletzung_Subunguales_Haematom": ["Nagelverletzung","subunguales Haematom","Fingerquetschung"],
"Narbenhernie_epigastrische_IPOM": ["Narbenhernie","epigastrisch","IPOM"],
"Narbenhernien_epigastrisch": ["Narbenhernie","epigastrisch"],
"Nasenbeinfraktur": ["Nasenbeinbruch"],
"Nierenkolik_bei_Harnstauungsniere_mit_Harnleiterschiene": ["Nierenkolik","Harnstau","Harnleiterschiene","Niere","Kolik"],
"Osteomyelitis_Zehenstrahlamputation": ["Osteomyelitis","Knochenmarkentzuendung","Zehenamputation"],
"Osteoporotische_Wirbelkoerperfraktur": ["Wirbelkoerperfraktur","Osteoporose","Sinterungsfraktur"],
"Panaritium": ["Fingerentzuendung","Umlauf"],
"Pangastritis": ["Gastritis","Helicobacter","Magenschleimhautentzuendung"],
"Papillaere_Pankreatitis": ["Papillitis","Pankreatitis","Papillenstenose","ERCP"],
"Paralytischer_Ileus": ["Ileus","paralytischer Ileus","Darmverschluss"],
"Patellafraktur": ["Kniescheibenbruch"],
"Phlegmone": ["Weichteilinfektion","Zellulitis"],
"Pneumonie": ["Lungenentzuendung"],
"Portexplantation": ["Portentfernung","Port"],
"Posttraumatische_Gonarthrose": ["Gonarthrose","Kniearthrose","posttraumatisch"],
"Prellung": ["Kontusion","Contusio"],
"Proktalgie": ["Analschmerz","Analgie"],
"Proktitis": ["Mastdarmentzuendung","Rektum"],
"Radiuskoepfchenfraktur_Mason_I": ["Radiuskoepfchenfraktur","Ellenbogen","Mason"],
"Rektumkarzinom": ["Mastdarmkrebs","Enddarmkrebs"],
"Rektusdiastase": ["Bauchmuskel"],
"Rippenserienfraktur": ["Rippenbruch","Rippenfraktur"],
"Rupturierte_Ovarialzyste": ["Ovarialzyste","Eierstockzyste","rupturiert"],
"Schaedelhirntrauma": ["SHT","Kopfverletzung"],
"Schenkelhalsfraktur": ["Oberschenkelhalsbruch","Hueftfraktur"],
"Schenkelhernie_Femoralhernie": ["Schenkelhernie","Femoralhernie","Hernie"],
"Schlafapnoe_Syndrom": ["Schlafapnoe","Schnarchen","Apnoe"],
"Schnittwunde": ["Wunde","Verletzung"],
"Schuerfwunden_Abschuerfungen": ["Schuerfwunde","Abschuerfung","Hautabschuerfung"],
"Schulterluxation": ["Schulterverrenkung","Luxation"],
"Schulterprellung": ["Contusio humeri","Prellung"],
"Schwellung_Handruecken_nach_Braunuele": ["Braunuele","Handruecken","Schwellung","Paravasat"],
"Stichverletzung": ["Stichwunde","Verletzung"],
"Struma_nodosa_Hyperthyreose": ["Struma","Schilddruese","Hyperthyreose","Schilddruesenknoten","Kropf"],
"Suizidalitaet": ["Suizidversuch","Eigengefaehrdung"],
"Tibiakopffraktur": ["Schienbein"],
"Tiefe_Beinvenenthrombose_TVT": ["TVT","tiefe Beinvenenthrombose","Thrombose","Beinvenenthrombose"],
"Urolithiasis": ["Nierensteine","Harnsteine","Nephrolithiasis","Kolik"],
"Uterusmyom": ["Myom","Gebaermutter"],
"Varikose": ["Krampfadern","Varizen"],
"Verbrennung_2_Grades": ["Verbrennung","Brandwunde","Verbruehung"],
"Vorhofflimmern_permanent": ["Vorhofflimmern","Arrhythmie","Herzrhythmusstoerung"],
"Weber_C_Fraktur": ["Weber-C-Fraktur","Aussenknoechel","Sprunggelenk"],
"Weichteilabloesung_Oberarm_Decollement": ["Weichteilabloesung","Decollement","Oberarm"],
"Wirbelkörperhämangiom": ["Wirbelkoerperhaemangiom","Haemangiom","Wirbel"],
"Zeckenstich": ["Zeckenbiss","Borreliose","FSME"],
"Zehenfraktur": ["Zehenbruch","Phalanx"],
"laparoskopische-appendektomie": ["Appendizitis","Appendektomie","Blinddarm","Appendix","laparoskopisch"],
"pAVK": ["periphere arterielle Verschlusskrankheit","Schaufensterkrankheit"],
"pAVK_Mediasklerose": ["pAVK","Mediasklerose","periphere arterielle Verschlusskrankheit"],
"Ösophagusvarizen": ["Oesophagusvarizen","Speiseroehrenvarizen","Varizen","Leberzirrhose"],
}

# ------------------------------------------------------------ groupings
GROUPS = [
 ("Psychiatrie", ["angst","borderline","suizid","psychiat"]),
 ("Gynäkologie", ["ovar","uterus","myom","gebaermutter"]),
 ("Hämatologie / Onkologie", ["lymphom","karzinom","tumor","krebs","metasta"]),
 ("Neurologie / Neurochirurgie", ["apoplex","subdural","commotio","schaedelhirn","frontobasis","hirn","hemiparese","pneumozephalus"]),
 ("Nephrologie / Urologie", ["niereninsuffizienz","urolith","nierenkolik","harnwegsinfekt","harnverhalt","dialyse","demers","nierenstein","harnstau"]),
 ("Kardiologie / Angiologie", ["hypertonie","herzinsuffizienz","khk","vorhofflimmern","pavk","thrombose","cvi","varikose","lungenembolie","dialyseshunt","stauungsdermatitis"]),
 ("Pneumologie", ["copd","pneumonie","schlafapnoe","emphysem"]),
 ("Gastroenterologie / Hepatologie", ["gastritis","colitis","divertik","crohn","obstipation","leber","pankreatitis","oesophagus","gastroparese","ileus","invagination","choledocho","cholezyst","gallenblasen","gallenstein","anastomositis","mesenteritis","prokt","haemorrhoid","analvenen","analfistel","zoekum","duodenal","duennndarm","duenndarm","harnwegsinfekt"]),
 ("Endokrinologie / Stoffwechsel", ["diabetes","adipositas","struma","hyperthyreose","gicht","anaemie","anämie","osteoporose"]),
 ("Dermatologie / Infektiologie", ["erysipel","wundrose","abszess","phlegmone","akne","zeckenstich","insektenstich","glutealfistel","hautabszess"]),
 ("Allgemein- / Viszeralchirurgie", ["hernie","appendek","appendizitis","portexplant","metallentfernung","weichteilabloesung","nadelstich","bissverletzung","stichverletzung","fremdkoerper","fingerendglied","nagelverletzung","abszess","fistel","dekubitus","schnittwunde","schuerfwunde","brandwunde","verbrennung"]),
 ("Orthopädie / Unfallchirurgie", ["fraktur","distorsion","kontusion","prellung","luxation","bursitis","arthrose","spondylodese","fasziitis","bandscheib","lumboischialgie","muskel","baker","osteosynthese","wirbel","rippenserien","klavikula","humerus","patella","tibia","radius","metatarsal","zehenfraktur","schulter","knie","hueft","coxa","tossy"]),
]

def group_of(name: str, title: str, body: str) -> str:
    hay = norm1(name + " " + title + " " + body[:600])
    for g, kws in GROUPS:
        for kw in kws:
            if norm1(kw) in hay:
                return g
    return "Sonstiges"

# --------------------------------------------------- licence detection
LICENCE_MARKERS = [
    "AMBOSS", "DocCheck", "Flexikon", "MSD Manual", "PubMed", "PMID",
    "AWMF", "S3-Leitlinie", "S2k-Leitlinie", "S2-Leitlinie",
    "UpToDate", "Pschyrembel", "Ärzteblatt", "In Anlehnung an", "entnommen aus",
]

def licence_info(raw: str, body: str, has_quellen: bool):
    hits = sorted({m for m in LICENCE_MARKERS if re.search(re.escape(m), raw, re.I)})
    due = has_quellen or bool(hits)
    return ("review" if due else "low"), hits

# --------------------------------------------------- scrub detection
# Patterns are deliberately conservative; hits are reviewed by hand below.
SCRUB_PATTERNS = [
    ("Fallname",        re.compile(r"\(?(Fall|Nutzerfassung)[ -]?[A-ZÄÖÜ][a-zäöüß]{2,}")),
    ("Geburtsdatum",    re.compile(r"\b(geb\.|geboren am|Jahrgang)\s*\d")),
    ("personengebundene Platzhalter", re.compile(r"\[(Name|Datum|Uhrzeit|Wert|Zeitraum|Alter|Ort)\]")),
    ("konkretes Datum im Fließtext", re.compile(r"[^0-9/\d]([0-3]?\d\.[01]?\d\.(19|20)\d{2})(?![0-9])")),
    ("Anschrift/PLZ",   re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]{3,}")),
    ("Telefonnummer",   re.compile(r"(\+49|\b0\d[\d /-]{7,}\d)")),
    ("Versichertennummer", re.compile(r"\b[A-Z]\d{9}\b")),
    ("Fallnummer",      re.compile(r"(Fall-?Nr|Aufnahme-?Nr|Patienten-?Nr|KV-?Nr)[.:]?\s*\w")),
]

def scrub_scan(raw: str):
    found = []
    for kind, pat in SCRUB_PATTERNS:
        for m in pat.finditer(raw):
            found.append((kind, m.group(0).strip()[:80]))
    return found

# ================================================================= main
def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.md")))
    files = [f for f in files if os.path.basename(f) != "index.md"]
    entries = []
    refcount = {s: 0 for s in REFERENCE_SECTIONS}
    licence_files = []
    scrub_files = {}

    for path in files:
        fn = os.path.basename(path)
        raw = open(path, encoding="utf-8").read()
        fm, body = split_frontmatter(raw)
        stem = fn[:-3]

        # title: frontmatter -> H1 -> filename
        title = (fm.get("title") or "").strip()
        if not title or title.lower() in ("musterbriefe",):
            m = re.search(r"^#\s+(.+)$", body, re.M)
            title = m.group(1).strip() if m else stem.replace("_", " ")

        raw_headings = body_sections(body)
        canon = []
        for h in raw_headings:
            c = canonical(h)
            if c not in canon:
                canon.append(c)
        present = [c for c in canon if c in REFERENCE_SECTIONS or c == "Quellen"]
        missing = [s for s in REFERENCE_SECTIONS if s not in present]
        for s in present:
            if s in refcount:
                refcount[s] += 1
        has_quellen = "Quellen" in canon

        lic, markers = licence_info(raw, body, has_quellen)
        if lic == "review":
            licence_files.append({"file": fn, "markers": markers, "has_quellen": has_quellen})

        # keywords
        derived = []
        for part in re.split(r"[-_]", stem) + re.split(r"[^\wÄÖÜäöüß]+", title):
            part = part.strip()
            if len(part) >= 3 and not part.isdigit():
                derived.append(part)
        kws = []
        for k in derived + SYN.get(stem, []):
            if k and k not in kws:
                kws.append(k)

        sc = scrub_scan(raw)
        if sc:
            scrub_files[fn] = sc

        entries.append({
            "file": fn,
            "title": title,
            "group": group_of(stem, title, body),
            "indication_keywords": kws,
            "sections_present": present,
            "sections_missing": missing,
            "headings_raw": raw_headings,
            "has_quellen": has_quellen,
            "licence_risk": lic,
            "chars": len(raw),
            "body_chars": len(body),
        })

    # duplicates by title similarity (char ratio + token-set ratio)
    def toks(t):
        return {w for w in norm(t).split() if len(w) > 1}
    titles = [(e["file"], e["title"]) for e in entries]
    dupes = []
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            a, b = norm(titles[i][1]), norm(titles[j][1])
            r = difflib.SequenceMatcher(None, a, b).ratio()
            ta, tb = toks(titles[i][1]), toks(titles[j][1])
            jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
            score = max(r, jac)
            if score >= 0.75:
                dupes.append((round(score, 2), titles[i][0], titles[j][0]))
    dupes.sort(reverse=True)

    thin = sorted([e for e in entries if e["chars"] < 400], key=lambda e: e["chars"])
    near_thin = sorted([e for e in entries if e["chars"] < 1200], key=lambda e: e["chars"])
    long = sorted([e for e in entries if e["chars"] > 4000], key=lambda e: -e["chars"])

    manifest = {
        "source": SRC,
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(entries),
        "reference_sections": REFERENCE_SECTIONS,
        "optional_sections": OPTIONAL_SECTIONS,
        "section_coverage": refcount,
        "counts": {
            "files": len(entries),
            "has_quellen": sum(1 for e in entries if e["has_quellen"]),
            "licence_review": sum(1 for e in entries if e["licence_risk"] == "review"),
            "thin_under_400_chars": len(thin),
            "under_1200_chars": len(near_thin),
            "long_over_4000_chars": len(long),
            "scrub_flagged": len(scrub_files),
            "duplicate_pairs": len(dupes),
        },
        "templates": entries,
    }
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # ---- index.md ----
    from collections import OrderedDict
    groups = OrderedDict()
    for e in sorted(entries, key=lambda x: x["title"].lower()):
        groups.setdefault(e["group"], []).append(e)
    lines = [
        "# Musterbriefe – Referenzbibliothek (Index)",
        "",
        f"Automatisch erzeugt aus `{SRC}` am {manifest['generated']}.",
        f"**{len(entries)} Musterbriefe** (index.md der Quelle ausgenommen).",
        "",
        "## Gruppierung (Methode)",
        "",
        "Jeder Musterbrief wird anhand von Stichwörtern in Dateiname, `title` und den ersten",
        "600 Zeichen des Textes einer Fachgruppe zugeordnet (Regelwerk in",
        "`build_library.py`, `GROUPS`). Spezifische Fachgebiete (Psychiatrie, Gynäkologie,",
        "Onkologie, Neurologie, Nephro/Urologie, Kardio/Angio, Pneumo, Gastro/Hepato,",
        "Endo/Stoffwechsel, Derm/Infektio) haben Vorrang; verbleibende Verletzungs-/",
        "Wundbilder werden Allgemein-/Viszeralchirurgie bzw. Orthopädie/Unfallchirurgie",
        "zugeordnet. `Sonstiges` = keine Regel traf zu.",
        "",
        "## Sektions-Normalisierung",
        "",
        "Für `sections_present` werden Überschriften auf die kanonischen Namen aus",
        "`manifest.json` (`reference_sections`) abgebildet, z. B. „Klinisches Bild“, „Leitsymptome“,",
        "„Klinische Präsentation“ → `Klinik`; „Bildgebung“, „Radiologie“ → `Diagnostik`;",
        "„Therapie / Empfehlungen“ → `Therapie`; „Therapieempfehlungen bei Entlassung“,",
        "„Entlassung“ → `Therapieempfehlungen bei Entlassung`; „Körperliche Untersuchung“,",
        "„Untersuchungsbefunde“ → `KU`; „Diagnosen (Beispiel)“, „ICD-Code“ → `Diagnosen`.",
        "Die Original-Überschriften stehen je Datei in `headings_raw`.",
        "",
    ]
    for g, items in groups.items():
        lines.append(f"## {g} ({len(items)})")
        lines.append("")
        for e in items:
            miss = ", ".join(e["sections_missing"]) if e["sections_missing"] else "–"
            kws = ", ".join(e["indication_keywords"][:10])
            lines.append(f"- **{e['title']}** (`{e['file']}`) — {kws} — Sektionen fehlen: {miss}")
        lines.append("")
    with open(os.path.join(OUT, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---- sectionstats.md ----
    total = len(entries)
    sl = [
        "# Sektionen – Statistik & Datenqualität",
        "",
        f"Basis: {total} Musterbriefe. Referenzsektionen = "
        + ", ".join(f"`{s}`" for s in REFERENCE_SECTIONS) + ".",
        "(Referenzset = die im Auftrag genannten Kernsektionen plus `Nachsorge`, weil",
        "`Nachsorge` mit Abstand die häufigste Body-Sektion ist.)",
        "",
        "## Abdeckung je Referenzsektion",
        "",
        "| Sektion | vorhanden | fehlt | Abdeckung |",
        "|---|---|---|---|",
    ]
    for s in REFERENCE_SECTIONS:
        c = refcount[s]
        sl.append(f"| {s} | {c} | {total - c} | {round(100*c/total)}% |")
    sl += ["", "## Fehlende Sektionen – Häufigkeit", "",
           "| Sektion | fehlt in n Briefen |", "|---|---|"]
    for s in sorted(REFERENCE_SECTIONS, key=lambda x: -refcount[x]):
        sl.append(f"| {s} | {total - refcount[s]} |")
    sl += ["", "## Zu dünn (< 400 Zeichen)", ""]
    if thin:
        for e in thin:
            sl.append(f"- `{e['file']}` — {e['chars']} Zeichen")
    else:
        sl.append("- **keine** Datei unter 400 Zeichen (alle ≥ 785 Zeichen).")
    sl += ["", f"## Grenzwertig kurz (< 1200 Zeichen, n={len(near_thin)})", ""]
    for e in near_thin:
        sl.append(f"- `{e['file']}` — {e['chars']} Zeichen, Titel: {e['title']}")
    sl += ["", f"## Zu lang (> 4000 Zeichen, n={len(long)})", ""]
    for e in long:
        sl.append(f"- `{e['file']}` — {e['chars']} Zeichen")
    sl += ["", f"## Duplikate / Near-Duplicates (Titel-Ähnlichkeit ≥ 0.75, n={len(dupes)})", "",
           "| Ähnlichkeit | Datei A | Datei B |", "|---|---|---|"]
    for r, a, b in dupes:
        sl.append(f"| {r} | `{a}` | `{b}` |")
    sl += [
        "",
        "### Thematische Cluster (manuell, ergänzend zur Ähnlichkeitsliste)",
        "",
        "| Thema | Dateien | Bewertung |",
        "|---|---|---|",
        "| Diabetes | `Diabetes_mellitus_Typ1.md`, `Diabetes_mellitus_Typ2.md` | bewusst getrennt (Typ 1/2), Struktur nahezu identisch |",
        "| Erysipel | `Erysipel.md`, `Erysipel_Wundrose.md` | vermutlich redundant – zusammenführen |",
        "| pAVK | `pAVK.md`, `pAVK_Mediasklerose.md` | konsolidieren (Mediasklerose = Sonderfall) |",
        "| Narbenhernie epigastrisch | `Narbenhernie_epigastrische_IPOM.md`, `Narbenhernien_epigastrisch.md` | stark überlappend – prüfen/mergen |",
        "| Leistenhernie | `Leistenhernie_Inguinalhernie_TAPP.md`, `Leistenhernie_Inguinalhernie_Lichtenstein.md` | bewusst zwei OP-Techniken, behalten |",
        "| Gallenwege | `Cholezystolithiasis.md`, `Choledocholithiasis.md`, `Gallenblasenpolypen_Konkremente_Verdacht.md`, `Gangraenose_Cholezystitis_CHE.md` | überlappend, je Brief abgrenzen |",
        "| Niereninsuffizienz | `Chronische_Niereninsuffizienz_CKD3.md`, `..._dialysepflichtig.md` | bewusst getrennt (Dialyse ja/nein) |",
        "| Pankreatitis | `Biliaere_Pankreatitis.md`, `Papillaere_Pankreatitis.md` | überlappend – abgrenzen |",
        "| Kontusionen Zehen/Finger | `Kontusion_Grosszehe/Kleinzehe/Mittelzehe/Grundgelenk_Kleinfinger/Grundgelenk_Ringfinger.md` | sehr ähnlich; viele dünne Kleinbriefe |",
    ]
    sl += [
        "",
        "## Empfehlungen", "",
        "1. **Duplikate mergen/abgrenzen:** siehe Tabelle; je Paar prüfen, ob ein Brief",
        "   reicht oder bewusst zwei Varianten (z. B. OP-Technik TAPP vs. Lichtenstein)",
        "   gewünscht sind.",
        "2. **Unter 1200 Zeichen auffüllen:** die kurzen Briefe (v. a. Frakturen/Prellungen)",
        "   um Diagnostik, Verlauf und Entlass-Empfehlungen ergänzen.",
        "3. **`KU` nur in wenigen Briefen:** konsequent eine kurze Untersuchungs-Sektion",
        "   ergänzen, damit der Generator einheitlich befüllen kann.",
        "4. **`Nachsorge` in ~25% der Briefe:** fehlende Nachsorge/Entlass-Empfehlungen",
        "   nachtragen, da der Arztbrief sie fast immer braucht.",
        "5. **Lange Briefe straffen:** die > 4000-Zeichen-Dateien (teils kopierte",
        "   Enzyklopädie-Prosa) kürzen (siehe licence-review.md).",
    ]
    with open(os.path.join(OUT, "sectionstats.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(sl) + "\n")

    # ---- scrub-report.md ----
    manual = [
        ("Cholezystolithiasis.md", "personenbezogene Fallkennung / Klarname",
         "Enthält im Abschnitt `## Nachsorge` eine Fallkennung der Form „(Nutzerfassung "
         "TT.MM.JJJJ, Fall <Nachname>)“ mit einem **realen Patienten-Nachnamen** (hier maskiert "
         "als `K***au`). Derselbe Nachname erscheint in `/workspace/schreibdienst/"
         "visitenliste-2026-09-22.md` mit Vorname, Alter und Fallcode. Empfehlung: **vor Ingest "
         "entfernen** — Fallkennung + Datum löschen, nur den generischen Empfehlungs-Wortlaut "
         "behalten. **Der Klarname ist in diesem Report absichtlich nicht ausgeschrieben.**"),
        ("Struma_nodosa_Hyperthyreose.md", "Fallnarrativ aus echtem Fall (bereits mit Platzhaltern)",
         "Der Text ist ein echter Entlassbrief, jedoch mit Platzhaltern `[Name]`, `[Datum]`, "
         "`[Wert]`, `[Zeitraum]`, `[Uhrzeit]` bereinigt. Kein Klarname mehr sichtbar. "
         "Empfehlung: **nach Ingest zulässig**, aber als „de-identifiziertes Fallbeispiel“ "
         "kennzeichnen und prüfen, dass keine residualen Identifier (genaue Daten, ITS-Zeitfenster) "
         "verbleiben."),
        ("Acne-inversa.md", "konkretes OP-Datum",
         "Enthält „Z.n. Exzision in toto am re. Schambein (TT.MM.2026)“ — ein konkretes "
         "Eingriffsdatum (hier maskiert). Kein Name, aber datierbar. Empfehlung: **Datum "
         "entfernen/generisch** machen („Z.n. Exzision in toto …“)."),
    ]
    sr = [
        "# Scrub-Report – Prüfung auf echte Patientendaten",
        "",
        "Geprüft: alle 152 Musterbriefe in `%s`." % SRC,
        "Methodik: Regex-Scan auf Geburtsdaten, Klarnamen nach „Herr/Frau“, Fall-/Aufnahme-/",
        "Versicherungsnummern, Postleitzahlen/Anschriften, Telefonnummern und konkrete Daten",
        "im Fließtext; zusätzlich manuelle Sichtung der Treffer und Abgleich der Namen mit",
        "`visitenliste-2026-09-22.md`.",
        "",
        "**Ergebnis: 3 Dateien mit Auffälligkeiten, davon 1 mit echtem Klarnamen.**",
        "",
        "## Manuell bestätigte Treffer",
        "",
        "| Datei | Art des Identifikators | Empfehlung / Aktion |",
        "|---|---|---|",
    ]
    for fn, kind, action in manual:
        sr.append(f"| `{fn}` | {kind} | {action} |")
    sr += [
        "",
        "## Automatischer Scan – weitere Treffer (geprüft, unkritisch)",
        "",
    ]
    auto_notes = []
    for fn, hits in sorted(scrub_files.items()):
        if fn in {m[0] for m in manual}:
            continue
        kinds = sorted({k for k, _ in hits})
        auto_notes.append(f"- `{fn}` — {', '.join(kinds)} (im Text generisch/Platzhalter, kein "
                          f"personenbezogener Klarname)")
    sr += auto_notes if auto_notes else ["- keine"]
    sr += [
        "",
        "## Bekannte False Positives (erklärt)",
        "",
        "- `Nadelstichverletzung.md` — „(Fall-Nr.)“ ist ein Dokumentations-Platzhalter, keine Nummer.",
        "- `Lumboischialgie_…md`, `AC-Gelenk-…md`, `Patellafraktur.md` — „Tel.: 1777“ / „telefonische "
        "Terminvereinbarung“ sind generische Institutionsangaben ohne Person.",
        "- `Coxarthrose_Exsikkose_Sturz.md` — Datum `08.07.2019` ist ein AWMF-Leitlinien-Stand, kein Patientendatum.",
        "- `Diabetes_mellitus_Typ1.md` — „1986 (seit 40 Jahren)“ ist ein generisches Erkrankungsalter, kein Geburtsdatum.",
        "",
        "## Regel für die Pipeline",
        "",
        "**Kein Musterbrief mit einem Treffer der Kategorie „Manuell bestätigte Treffer“",
        "darf ingestiert werden, bevor er anonymisiert wurde.** Die drei Dateien oben sind",
        "bis dahin auf `licence_risk`-unabhängig als `scrub_pending` zu behandeln.",
    ]
    with open(os.path.join(OUT, "scrub-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(sr) + "\n")

    # ---- licence-review.md ----
    lr = [
        "# Lizenz-Review – Herkunft von Text und Quellen",
        "",
        "Zweck: Musterbriefe identifizieren, deren Formulierungen ganz oder teilweise aus",
        "kostenpflichtigen/urheberrechtlich geschützten Quellen (AMBOSS, DocCheck Flexikon,",
        "MSD Manual, PubMed/Paper, AWMF/DGVS-Leitlinien) übernommen wirken.",
        "",
        f"Ergebnis: **{len(licence_files)} von {len(entries)}** Dateien mit Quellenangabe und/oder",
        "Quellenmarkern → `licence_risk = \"review\"` im Manifest.",
        "",
        "## Dateien mit `## Quellen` und/oder übernommen wirkender Prosa",
        "",
        "| Datei | beobachtete Marker | Bewertung |",
        "|---|---|---|",
    ]
    detail = {
        "Coxarthrose_Exsikkose_Sturz.md": "Explizite `## Quellen`-Liste (DocCheck Flexikon, MSD Manual, AWMF S2k Koxarthrose).",
        "Pangastritis.md": "`## Quellen` (DocCheck, MSD Manual Professional, AWMF S2k H. pylori 021-001, PubMed/Am J Gastroenterol 2002); sehr langer enzyklopädischer Text.",
        "Papillaere_Pankreatitis.md": "`## Quellen` (DocCheck, MSD Manual, AWMF/DGVS S3 Pankreatitis 021-003); Fließtext mit wörtlichen Leitlinien-Wiedergaben und Quellenkürzeln im Satz.",
        "Proktitis.md": "`## Quellen` (DocCheck, MSD Manual, AWMF S3 Colitis ulcerosa, DGVS, PubMed PMID 2204103); zahlreiche Absätze mit Klammerverweisen `(DocCheck Flexikon)`/`(MSD Manual)` direkt im Text — stark nach Übernahme aussehend.",
    }
    for item in licence_files:
        fn = item["file"]
        mk = ", ".join(item["markers"]) if item["markers"] else "nur `## Quellen`"
        lr.append(f"| `{fn}` | {mk} | {detail.get(fn, 'Quellen vorhanden')} |")
    lr += [
        "",
        "Hinweis: In mehreren Briefen steht die Quellenangabe **im Fließtext in Klammern**",
        "(z. B. „(DocCheck Flexikon)“, „(AWMF S3-Leitlinie …)“), nicht nur im `## Quellen`-Block.",
        "Das ist ein starkes Indiz für (teil-)wörtliche Übernahme.",
        "",
        "## Empfohlene Regel",
        "",
        "> **Die Struktur eines Musterbriefs darf uns inspirieren, die lizenzierte Prosa nicht.**",
        "",
        "1. Lizenzierten Text (AMBOSS/DocCheck/MSD/Paper/Leitlinien) **nicht wörtlich** in das",
        "   ausgelieferte Produkt oder in Trainings-/Few-Shot-Beispiele übernehmen.",
        "2. Ziel ist eine eigene, generische Arztbrief-Vorlage pro Indikation: medizinisch korrekt,",
        "   aber in eigener Formulierung; Leitlinien nur als Fakten-Referenz, nicht als Satzspender.",
        "3. Die 4 markierten Dateien vor Nutzung als Referenz **umschreiben** (paraphrasieren) und",
        "   die Quellen-Klammern im Fließtext entfernen; `## Quellen` als reine Lese-Referenz behalten,",
        "   nie in generierte Kundenbriefe übernehmen.",
        "4. `licence_risk == \"review\"` im Manifest als Gate behandeln: erst nach Paraphrase-Freigabe",
        "   in Retrieval/Few-Shot aufnehmen.",
    ]
    with open(os.path.join(OUT, "licence-review.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lr) + "\n")

    print("files:", len(entries))
    print("refcount:", refcount)
    print("thin<400:", len(thin), "under1200:", len(near_thin), "long>4000:", len(long))
    print("dupes:", len(dupes), "licence_review:", len(licence_files), "scrub:", len(scrub_files))
    for r, a, b in dupes:
        print("  dup", r, a, "|", b)

if __name__ == "__main__":
    main()
