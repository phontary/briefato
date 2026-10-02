"""Deterministic rule checker — enforces R1-R67 + the ANTI-PATTERNS in code.

OWNER: WORKSTREAM-BRAIN-WIRING.

This is the code-side half of the brain: every finding carries the rule id it
violates so the pipeline can retry with targeted corrections and the UI can show
exactly which rule was broken.

    check(text, doc_type, dictation) -> CheckResult

Findings are ``hard`` (trigger a retry; if still failing, the letter is stored with
the findings attached) or ``soft`` (recorded, never blocking).

Covered here (the deterministic subset of R1-R67 + AP-01..AP-25):

* R4/AP-02  no markdown                       * R5/AP-03  no category labels
* R2/AP-01  no intro                          * R3/AP-01  no closing floskel
* R21/AP-05 'Diagnosen:' present and last      * R22       no 'Dg.:' prefix
* R23       no 'Z.n.' entries in the list      * R24       zusammenfassung: no lists
* R25-R27   stationary block order             * R30       no station blocks elsewhere
* R10/AP-10 no 'am TT.MM.' dates in the course * R8/AP-13  max one semicolon
* R6        correct umlauts                    * R46       no invented ICD codes
* AP-06     no KI/disclaimer text              * R13/AP-21 no repeated findings
* R14       stationary admission sentence      * R58       ambulant: no 'stationär auf'
* R-INVENT  source grounding (anti-invention)  * R6-AUTOFIX (soft) umlaut auto-correction log
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .stopwords import QUALIFIERS as _GENERIC_QUALIFIERS, STOPWORDS as _GRAMMAR_STOPWORDS

# Rules whose violation blocks the letter (pipeline retries once, then attaches).
HARD_RULES: frozenset[str] = frozenset(
    {"R2", "R3", "R4", "R5", "R6", "R21", "R22", "R23", "R24", "R25", "R26", "R27", "R30", "R46", "R58", "AP-06", "R-INVENT"}
)

# Anti-pattern cross-reference for the UI/audit.
ANTI_PATTERN_OF: dict[str, str] = {
    "R2": "AP-01",
    "R3": "AP-01",
    "R4": "AP-02",
    "R5": "AP-03",
    "R10": "AP-10",
    "R8": "AP-13",
    "R21": "AP-05",
    "AP-06": "AP-06",
    "R13": "AP-21",
}

DOC_TYPES_REQUIRING_DIAGNOSEN = frozenset({"arztbrief", "operationsbericht", "ambulant"})

# The only labels that may stand at line start (playbook-sanctioned block labels).
ALLOWED_LABELS = {
    "diagnosen",
    "nebenerkrankungen",
    "therapie-maßnahmen auf der station",
    "ambulante therapieempfehlungen nach der entlassung",
    "therapieempfehlungen bei entlassung",
}
ALLOWED_OPS_LABELS = {"indikation", "op", "präparat", "operation"}

FORBIDDEN_LABEL_WORDS = {
    "ku", "sono", "sonografie", "sonographie", "labor", "laborwerte", "ct", "mrt",
    "anamnese", "befund", "therapie", "diagnostik", "klinik", "verlauf", "aufnahme",
    "entlassung", "ekg", "röntgen", "roentgen", "endoskopie", "histologie", "medikation",
    "procedere", "aufnahmebefund", "untersuchung", "diagnose", "vorgeschichte",
    "mikrobiologie", "virologie",
}

INTRO_PATTERNS = (
    "hiermit berichten wir",
    "wir berichten über",
    "wir berichten ueber",
    "hiermit möchten wir",
    "hiermit moechten wir",
    "im folgenden berichten wir",
    "wir stellen ihnen",
)
CLOSING_PATTERNS = (
    "zusammenfassend lässt sich sagen",
    "zusammenfassend laesst sich sagen",
    "zusammenfassend kann man sagen",
    "abschließend lässt sich sagen",
    "abschliessend laesst sich sagen",
    "abschließend möchten wir",
    "wir hoffen, ihnen",
    "wir hoffen ihnen",
)

DISCLAIMER_PATTERNS = (
    r"ki[-\s]?generiert",
    r"k(?:ü|ue)nstliche intelligenz",
    r"von einer ki\b",
    r"ersetzt keine",
    r"keine (?:ä|ae)rztliche beratung",
    r"ohne gew(?:ä|ae)hr",
    r"haftungsausschluss",
    r"haftung ausgeschlossen",
    r"bitte (?:ä|ae)rztlich pr(?:ü|ue)fen",
)

# Legitimate German words containing the ae/oe trigram (avoid false positives).
# Note: any other 'ae'/'oe' word is treated as an ASCII transliteration.
UMLAUT_ALLOW = {
    "aerosol",
    "aerob",
    "aerobier",
    "aerobes",
    "aachen",
    "oesophagus",
    "oesophagitis",
    "oesophag",
    "oesophage",
    "oocyte",
    "koeffizient",
    "poesie",
    "poet",
    "poetisch",
    "michael",
    "rafael",
    "raffael",
    "israel",
}

# Curated transliterations for the 'ue' trigram (ue is otherwise common and legit,
# e.g. "neue", "zuerst", "Quelle", "Sauerstoff").
UE_TRANSLITERATIONS = {
    "ueber", "ueberweisung", "uebernahme", "uebergeben", "ueberpruefung", "ueberpruefen",
    "ueberwachung", "uebersicht", "ueberleben", "uebungen", "uebung", "uebel", "uebelkeit",
    "durchfuehrung", "durchgefuehrt", "durchfuehren", "fuehrung", "fuehren", "fuehrte",
    "gefuehl", "zufuehren", "zurueck", "zustaendig", "verfuegung", "ausfuehren", "aufuehren",
    "unterstuetzung", "unterstuetzen", "begruendung", "verkuerzung", "zustaende", "zustaenden",
}

# Curated 'ss' transliterations (generic 'ss' is legitimate German, e.g. "Fluss").
SS_TRANSLITERATIONS = {"strasse", "groesse", "groessere", "groesste", "ausserdem", "schliessen", "schliesslich", "spaeter"}

_ICD_RE = re.compile(r"(?<![A-Za-z0-9])[A-TV-Z]\d{2}(?:\.\d{1,2})?(?![0-9])")
_ICD_ALLOW = {"B12"}
_LABEL_RE = re.compile(r"^\s*([A-Za-zÄÖÜäöüß][\wÄÖÜäöüß./\- ]{0,60}?)\s*:\s*(.*)$")
_TOKEN_RE = re.compile(r"\{\{\s*[A-Za-z0-9_]+\s*\}\}")
_WORD_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")

TERMINAL_BLOCKS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "arztbrief": ("Nebenerkrankungen:", "Therapie-Maßnahmen auf der Station:"),
    "operationsbericht": ("Operation:",),
    "ambulant": (),
}

STATION_BLOCKS = (
    "ambulante Therapieempfehlungen nach der Entlassung:",
    "Nebenerkrankungen:",
    "Therapie-Maßnahmen auf der Station:",
)


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str  # "hard" | "soft"
    message: str
    evidence: str = ""
    anti_pattern: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "anti_pattern": self.anti_pattern,
        }


@dataclass
class CheckResult:
    findings: list[Finding] = field(default_factory=list)
    doc_type: str = ""
    rule_count: int = 0

    @property
    def hard(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "hard"]

    @property
    def soft(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "soft"]

    @property
    def ok(self) -> bool:
        return not self.hard

    @property
    def summary(self) -> str:
        if not self.findings:
            return "keine Regelverstöße"
        return f"{len(self.hard)} harte, {len(self.soft)} weiche Hinweise"

    def correction_instructions(self) -> list[str]:
        return [
            f"{finding.rule_id}: {finding.message}"
            + (f" (Fundstelle: {finding.evidence!r})" if finding.evidence else "")
            for finding in self.hard
        ]

    def as_dict(self) -> dict[str, object]:
        return {
            "doc_type": self.doc_type,
            "ok": self.ok,
            "summary": self.summary,
            "hard": [finding.as_dict() for finding in self.hard],
            "soft": [finding.as_dict() for finding in self.soft],
        }


def _finding(rule_id: str, message: str, evidence: str = "", *, severity: str | None = None) -> Finding:
    sev = severity or ("hard" if rule_id in HARD_RULES else "soft")
    return Finding(rule_id=rule_id, severity=sev, message=message, evidence=evidence[:200], anti_pattern=ANTI_PATTERN_OF.get(rule_id, ""))


def _strip_tokens(text: str) -> str:
    return _TOKEN_RE.sub(" ", text or "")


# --------------------------------------------------------------------------- checks


def _check_markdown(text: str) -> list[Finding]:
    found: list[Finding] = []
    if "**" in text or re.search(r"(?<!\w)__(?!\w)", text):
        found.append(_finding("R4", "Markdown-Fettung/Kursivsetzung (**, __) im Text", "**/_"))
    if re.search(r"^\s{0,3}#{1,6}\s", text, re.MULTILINE):
        found.append(_finding("R4", "Markdown-Überschrift (#) im Text", "#"))
    if "`" in text:
        found.append(_finding("R4", "Markdown-Codeblock/Backtick im Text", "`"))
    if re.search(r"^\s*[-*•·]\s+\S", text, re.MULTILINE):
        found.append(_finding("R4", "Aufzählungszeichen im Text", "- "))
    if re.search(r"^\s*\d+[.)]\s+\S", text, re.MULTILINE):
        found.append(_finding("R4", "Nummerierte Liste im Text", "1. "))
    if re.search(r"^\s*\|.*\|", text, re.MULTILINE):
        found.append(_finding("R4", "Tabelle (|) im Text", "|"))
    return found


def _check_labels(text: str, doc_type: str) -> list[Finding]:
    found: list[Finding] = []
    stripped = _strip_tokens(text)
    for line in stripped.splitlines():
        match = _LABEL_RE.match(line)
        if not match:
            continue
        label = match.group(1).strip()
        first = label.split()[0].lower().strip("-")
        full = label.lower()
        if full in ALLOWED_LABELS:
            continue
        if full in ALLOWED_OPS_LABELS:
            if doc_type != "operationsbericht":
                found.append(_finding("R5", f"Kategorie-Label „{label}:“ im Fließtext", label))
            continue
        if first in FORBIDDEN_LABEL_WORDS:
            found.append(_finding("R5", f"Kategorie-Label „{label}:“ im Fließtext", label))

    # Inline labels ("… Befund: …", "Sonographie: …") — after removing the sanctioned
    # block labels so "… nach der Entlassung:" / "Therapie-Maßnahmen …" stay allowed.
    allowed = {f"{label}:" for label in ALLOWED_LABELS}
    if doc_type == "operationsbericht":
        allowed |= {f"{label}:" for label in ALLOWED_OPS_LABELS}
    masked = stripped
    for label in sorted(allowed, key=len, reverse=True):
        masked = re.sub(re.escape(label), " ", masked, flags=re.IGNORECASE)
    pattern = re.compile(
        r"(?<![A-Za-zÄÖÜäöüß])("
        + "|".join(sorted(FORBIDDEN_LABEL_WORDS, key=len, reverse=True))
        + r")\s*:",
        re.IGNORECASE,
    )
    for match in pattern.finditer(masked):
        found.append(_finding("R5", f"Kategorie-Label „{match.group(1)}:“ im Fließtext", match.group(1)))
    return found


def _check_dg_prefix(text: str) -> list[Finding]:
    match = re.search(r"(?<![A-Za-zÄÖÜäöüß])Dg\.?\s*:", text or "")
    if match:
        return [_finding("R22", "„Dg.:“-Präfix in der Liste (verboten)", match.group(0))]
    return []


def _check_intro_closing(text: str) -> list[Finding]:
    low = (text or "").lower()
    found: list[Finding] = []
    for pattern in INTRO_PATTERNS:
        if pattern in low:
            found.append(_finding("R2", "Einleitungssatz im Brief", pattern))
    for pattern in CLOSING_PATTERNS:
        if pattern in low:
            found.append(_finding("R3", "Schlussfloskel im Brief", pattern))
    for pattern in DISCLAIMER_PATTERNS:
        match = re.search(pattern, low)
        if match:
            found.append(_finding("AP-06", "KI-/Disclaimer-Text im Brief", match.group(0)))
    return found


def _check_semicolon(text: str) -> list[Finding]:
    count = (text or "").count(";")
    if count > 1:
        return [_finding("R8", f"{count} Semikolons im Text (maximal eines erlaubt)")]
    return []


def _check_umlauts(text: str) -> list[Finding]:
    found: list[Finding] = []
    seen: set[str] = set()
    for word in _WORD_RE.findall(_strip_tokens(text)):
        low = word.lower()
        if low in seen:
            continue
        seen.add(low)
        if low in UMLAUT_ALLOW or low in SS_TRANSLITERATIONS:
            continue
        if _looks_transliterated(low):
            found.append(_finding("R6", f"ASCII-Umlaut/ß statt ä/ö/ü: „{word}“", word))
    return found


def _looks_transliterated(low: str) -> bool:
    """Conservative heuristic for ae/oe/ue/ss transliterations."""
    if re.search(r"ae", low) or re.search(r"oe", low):
        return True
    if low in UE_TRANSLITERATIONS:
        return True
    if low.endswith("ss") and low in SS_TRANSLITERATIONS:
        return True
    return False


def _check_icd(text: str, dictation: str) -> list[Finding]:
    dictation_codes = {match.group(0).upper() for match in _ICD_RE.finditer(dictation or "")}
    found: list[Finding] = []
    for match in _ICD_RE.finditer(text or ""):
        code = match.group(0)
        if code.upper() in dictation_codes or code.upper() in _ICD_ALLOW:
            continue
        found.append(_finding("R46", f"ICD-Code „{code}“ steht nicht im Diktat (erfunden)", code))
    return found


def _find_line_index(lines: list[str], label: str) -> int | None:
    wanted = label.lower()
    for index, line in enumerate(lines):
        if line.strip().lower().startswith(wanted):
            return index
    return None


def _check_blocks(text: str, doc_type: str) -> list[Finding]:
    found: list[Finding] = []
    lines = _strip_tokens(text).splitlines()
    positions = {label: _find_line_index(lines, label) for label in STATION_BLOCKS}
    present = {label: pos for label, pos in positions.items() if pos is not None}

    if doc_type not in ("arztbrief",) and present:
        wrong = ", ".join(label for label in present)
        found.append(_finding("R30", f"Stationäre Blöcke in Dokumenttyp „{doc_type}“: {wrong}"))

    if doc_type == "arztbrief":
        order = [
            label
            for label in (
                "ambulante Therapieempfehlungen nach der Entlassung:",
                "Diagnosen:",
                "Nebenerkrankungen:",
                "Therapie-Maßnahmen auf der Station:",
            )
            if label in present or _find_line_index(lines, label) is not None
        ]
        order_positions = {label: _find_line_index(lines, label) for label in order}
        ordered = [order_positions[label] for label in order]
        if ordered != sorted(ordered):
            found.append(_finding("R25", "Blockreihenfolge verletzt (ambulante Empfehlungen → Diagnosen → Nebenerkrankungen → Therapie-Maßnahmen)"))
    return found


def _check_diagnosen(text: str, doc_type: str) -> list[Finding]:
    found: list[Finding] = []
    stripped = _strip_tokens(text)
    has_diag = "Diagnosen:" in stripped

    if doc_type == "zusammenfassung":
        if has_diag:
            found.append(_finding("R24", "Zusammenfassung darf keine Diagnoseliste enthalten", "Diagnosen:"))
        if "Therapie-Maßnahmen auf der Station:" in stripped:
            found.append(_finding("R24", "Zusammenfassung darf keine Therapie-Maßnahmen-Liste enthalten"))
        return found

    if doc_type in DOC_TYPES_REQUIRING_DIAGNOSEN and not has_diag:
        found.append(_finding("R21", "Pflichtblock „Diagnosen:“ fehlt am Dokumentende"))
        return found

    if has_diag:
        # Diagnoseliste must come after the narrative (not at the very top).
        diag_index = stripped.index("Diagnosen:")
        if len(stripped) > 400 and diag_index < len(stripped) * 0.2:
            found.append(_finding("R21", "Diagnoseliste steht am Dokumentanfang statt am Ende"))
        found.extend(_check_diagnosen_tail(stripped, doc_type))
        found.extend(_check_zn_lines(stripped))
    return found


def _check_diagnosen_tail(text: str, doc_type: str) -> list[Finding]:
    """No narrative/excluded paragraph may follow the Diagnosen block."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    diag_para: int | None = None
    for index, paragraph in enumerate(paragraphs):
        if paragraph.strip().startswith("Diagnosen:"):
            diag_para = index
    if diag_para is None:
        return []
    terminal_words = {
        label.rstrip(":").split()[0].lower() for label in TERMINAL_BLOCKS_BY_TYPE.get(doc_type, ())
    }
    for paragraph in paragraphs[diag_para + 1 :]:
        head = paragraph.strip()
        if not head:
            continue
        first = head.split()[0].lower().rstrip(":")
        if first in terminal_words:
            continue
        return [
            _finding(
                "R21",
                "Inhalt nach der Diagnoseliste (Diagnosen müssen am Ende stehen)",
                head[:80],
            )
        ]
    return []


def _check_zn_lines(text: str) -> list[Finding]:
    lines = text.splitlines()
    diag = next((i for i, line in enumerate(lines) if line.strip().startswith("Diagnosen:")), None)
    if diag is None:
        return []
    for line in lines[diag + 1 :]:
        stripped = line.strip()
        if stripped.lower().startswith("z.n."):
            return [
                _finding(
                    "R23",
                    "„Z.n. <OP>“-Zeile in der Diagnoseliste (Eingriffe gehören in den Therapieblock)",
                    stripped,
                )
            ]
        # Stop at the next labelled block — the Diagnoseliste ended.
        if stripped.endswith(":") and len(stripped) < 60 and not stripped.lower().startswith("z.n."):
            if re.match(r"^[A-ZÄÖÜ][\wÄÖÜäöüß\- ]{2,}:$", stripped):
                break
    return []


def _check_dates(text: str) -> list[Finding]:
    found: list[Finding] = []
    for line in text.splitlines():
        low = line.lower()
        for match in re.finditer(r"\bam\s+\d{1,2}\.\d{1,2}\.?(?:\d{2,4})?", low):
            # OP date and discharge/transfer date are the sanctioned exceptions.
            if "op am" in low or any(word in low for word in ("entließen", "entlassen", "verlegten", "verlegung", "entlassung", "aufnahme am")):
                continue
            found.append(_finding("R10", f"Datum „{match.group(0)}“ im Verlauf (erlaubt nur OP-/Entlassdatum)", line.strip()[:80]))
    return found


def _check_repeats(text: str) -> list[Finding]:
    stripped = _strip_tokens(text)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", stripped) if len(s.strip()) >= 40]
    seen: set[str] = set()
    duplicates: list[str] = []
    for sentence in sentences:
        key = re.sub(r"\s+", " ", sentence.lower())
        if key in seen:
            duplicates.append(sentence)
        seen.add(key)
    if duplicates:
        return [_finding("R13", "Wiederholte Aussage/Befund (jeder Befund nur einmal)", duplicates[0][:80])]
    return []


def _check_pflichtsatz(text: str, doc_type: str) -> list[Finding]:
    low = (text or "").lower()
    if doc_type == "arztbrief" and "stationär auf" not in low and "stationaer auf" not in low:
        return [_finding("R14", "Pflichtsatz zur stationären Aufnahme fehlt („Wir nahmen die Pat. … stationär auf.“)")]
    if doc_type == "ambulant" and "stationär auf" in low:
        return [_finding("R58", "Ambulanter Brief darf keinen „stationär aufnehmen“-Satz enthalten")]
    return []


# --------------------------------------------------------------------------- R5 phrases
#
# The judge flagged label-style *openers* that carry no colon (e.g. a list item
# rendered as „Abschließende Kontrolle auf intraabdominelle Bluttrockenheit …“).
# These are the same register violation as a category label and are detected
# separately, at line/sentence start, so ordinary prose that merely mentions the
# phrase mid-sentence is not touched.
LABEL_PHRASE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?im)(?:^|(?<=[.!?]\s))\s*ab(?:schließende|schliessende|schliessend)\s+kontrolle\b"
    ),
)


def _check_label_phrases(text: str) -> list[Finding]:
    stripped = _strip_tokens(text)
    found: list[Finding] = []
    for pattern in LABEL_PHRASE_PATTERNS:
        for match in pattern.finditer(stripped):
            found.append(
                _finding("R5", "Kategorie-/Listenlabel im Fließtext („Abschließende Kontrolle …“)", match.group(0)[:120])
            )
    return found


# --------------------------------------------------------------------------- R6 autofix
#
# A real-model run showed an ASCII transliteration could survive even the automatic
# retry (R6). This is a deterministic post-processing step: an explicit, curated
# German/medical word map rewrites known transliterations to ä/ö/ü/ß. A word is
# changed only when it is an exact, case-insensitive key of the map and not on the
# deny-list — so words where "ae/oe/ue/ss" is genuinely correct (Aerosol, Oesophagus,
# Museum, neue, Quelle, Fluss, Prozess …) are never altered.
UMLAUT_AUTOFIX_DENY: frozenset[str] = frozenset(UMLAUT_ALLOW) | frozenset(
    {
        "museum", "museen", "museal", "diurese", "diuresis", "influenza",
        "neue", "neuen", "neuer", "neues", "neuem", "quelle", "quellen", "steuer",
        "steuern", "sauer", "sauerstoff", "treue", "feuer", "teuer", "euere",
        "fluss", "prozess", "prozesse", "prozessen", "muss", "dass", "schluss",
        "bewusst", "gewiss", "sonstig", "sonstiges", "kasse", "essen", "lassen", "wissen",
    }
)

UMLAUT_AUTOFIX: dict[str, str] = {
    # --- ä ---
    "stationaer": "stationär", "stationaere": "stationäre", "stationaerer": "stationärer",
    "stationaeres": "stationäres", "stationaeren": "stationären", "stationaerem": "stationärem",
    "haeuslich": "häuslich", "haeusliche": "häusliche", "haeuslichen": "häuslichen",
    "haeuslicher": "häuslicher", "haeusliches": "häusliches",
    "hausaerztlich": "hausärztlich", "hausaerztliche": "hausärztliche",
    "hausaerztlichen": "hausärztlichen", "hausaerztlicher": "hausärztlicher",
    "aerztlich": "ärztlich", "aerztliche": "ärztliche", "aerztlichen": "ärztlichen",
    "aerztlicher": "ärztlicher", "aerztliches": "ärztliches", "aerztin": "Ärztin", "aerzte": "Ärzte",
    "regelmaessig": "regelmäßig", "regelmaessige": "regelmäßige", "regelmaessigen": "regelmäßigen",
    "regelmaessiger": "regelmäßiger", "regelmaessiges": "regelmäßiges",
    "ruecklaeufig": "rückläufig", "ruecklaeufige": "rückläufige", "ruecklaeufigen": "rückläufigen",
    "ruecklaeufiger": "rückläufiger",
    "entzuendet": "entzündet", "entzuendete": "entzündete", "entzuendeten": "entzündeten",
    "entzuendeter": "entzündeter", "entzuendung": "Entzündung", "entzuendungen": "Entzündungen",
    "entzuendlich": "entzündlich", "entzuendliche": "entzündliche", "entzuendlichen": "entzündlichen",
    "anaemie": "Anämie", "anaemisch": "anämisch",
    "naechste": "nächste", "naechsten": "nächsten", "naechster": "nächster", "naechstes": "nächstes",
    "spaeter": "später", "spaetere": "spätere", "spaeteren": "späteren", "spaeterhin": "späterhin",
    "taeglich": "täglich", "taegliche": "tägliche", "taeglichen": "täglichen",
    "waehrend": "während",
    "haematom": "Hämatom", "haematome": "Hämatome", "haemoglobin": "Hämoglobin",
    "haematurie": "Hämaturie", "haemodynamisch": "hämodynamisch",
    "praeoperativ": "präoperativ", "praeparat": "Präparat", "praeparate": "Präparate",
    "geraet": "Gerät", "geraete": "Geräte", "naehte": "Nähte", "erkaeltung": "Erkältung",
    "aufklaerung": "Aufklärung", "aufklaerungen": "Aufklärungen", "aufklaerend": "aufklärend",
    "aufgeklaert": "aufgeklärt", "aufklaert": "aufklärt", "aufklaeren": "aufklären",
    "abklaerung": "Abklärung", "abklaerungen": "Abklärungen", "klaerung": "Klärung",
    "erklaerung": "Erklärung", "gelaende": "Gelände", "geschaetzt": "geschätzt",
    "schaetzung": "Schätzung", "gefaess": "Gefäß", "gefaesse": "Gefäße", "aetzung": "Ätzung",
    "baender": "Bänder", "gefaehrlich": "gefährlich", "gefaehrdet": "gefährdet",
    "schlaegt": "schlägt", "flaeche": "Fläche", "flaechen": "Flächen",
    "staerke": "Stärke", "staerker": "stärker", "verlaesslich": "verlässlich",
    "faellig": "fällig", "faelle": "Fälle", "faellen": "Fällen",
    # --- ö ---
    "oedem": "Ödem", "oedeme": "Ödeme", "oedemen": "Ödemen", "oedematos": "ödematös",
    "koennen": "können", "koennte": "könnte", "koennten": "könnten", "koenne": "könne",
    "moeglich": "möglich", "moegliche": "mögliche", "moeglichen": "möglichen",
    "moeglicher": "möglicher", "moeglicherweise": "möglicherweise",
    "moeglichkeit": "Möglichkeit", "moeglichkeiten": "Möglichkeiten",
    "noetig": "nötig", "noetige": "nötige", "noetigen": "nötigen", "noetigenfalls": "nötigenfalls",
    "erhoeht": "erhöht", "erhoehte": "erhöhte", "erhoehten": "erhöhten", "erhoehter": "erhöhter",
    "hoehe": "Höhe", "hoeher": "höher",
    "roentgen": "Röntgen", "roentgenaufnahme": "Röntgenaufnahme", "roentgenbild": "Röntgenbild",
    "roentgenuntersuchung": "Röntgenuntersuchung", "roentgenthorax": "Röntgen-Thorax",
    "koerper": "Körper", "koerperlich": "körperlich", "koerperliche": "körperliche",
    "koerperlichen": "körperlichen", "koerpertemperatur": "Körpertemperatur",
    "oertlich": "örtlich", "oertliche": "örtliche", "oertlichen": "örtlichen",
    "woechentlich": "wöchentlich",
    "loesung": "Lösung", "loesungen": "Lösungen", "loest": "löst", "loeste": "löste", "loesen": "lösen",
    "boesartig": "bösartig", "boesartige": "bösartige", "boesartigen": "bösartigen",
    "roetung": "Rötung", "roetungen": "Rötungen", "roetlich": "rötlich",
    "verzoegerung": "Verzögerung", "verzoegert": "verzögert", "oeffnung": "Öffnung",
    "oeffnen": "öffnen", "hoerbar": "hörbar", "stoerung": "Störung", "stoerungen": "Störungen",
    # --- ü ---
    "ueber": "über", "ueberweisung": "Überweisung", "ueberweisungen": "Überweisungen",
    "uebernahme": "Übernahme", "uebergeben": "übergeben", "ueberpruefung": "Überprüfung",
    "ueberpruefen": "überprüfen", "ueberprueft": "überprüft", "ueberwachung": "Überwachung",
    "ueberwachen": "überwachen", "uebersicht": "Übersicht", "ueberleben": "überleben",
    "uebungen": "Übungen", "uebung": "Übung", "uebel": "übel", "uebelkeit": "Übelkeit",
    "ueberhaupt": "überhaupt", "ueberdosis": "Überdosis", "uebertragung": "Übertragung",
    "ueberempfindlichkeit": "Überempfindlichkeit",
    "durchfuehrung": "Durchführung", "durchgefuehrt": "durchgeführt", "durchfuehren": "durchführen",
    "fuehrung": "Führung", "fuehren": "führen", "fuehrte": "führte", "fuehrt": "führt",
    "gefuehl": "Gefühl", "zufuehren": "zuführen", "zurueck": "zurück",
    "zustaendig": "zuständig", "zustaendige": "zuständige", "verfuegung": "Verfügung",
    "ausfuehren": "ausführen", "aufuehren": "aufführen",
    "unterstuetzung": "Unterstützung", "unterstuetzen": "unterstützen", "unterstuetzt": "unterstützt",
    "begruendung": "Begründung", "verkuerzung": "Verkürzung", "zustaende": "Zustände",
    "zustaenden": "Zuständen",
    "fluessigkeit": "Flüssigkeit", "fluessigkeiten": "Flüssigkeiten", "fluessig": "flüssig",
    "pruefen": "prüfen", "pruefung": "Prüfung", "pruefungen": "Prüfungen", "geprueft": "geprüft",
    "prueft": "prüft",
    "ueblich": "üblich", "uebliche": "übliche", "ueblichen": "üblichen", "ueblicherweise": "üblicherweise",
    "zukuenftig": "zukünftig", "natuerlich": "natürlich", "kuerzlich": "kürzlich",
    "duenn": "dünn", "fuellen": "füllen", "frueh": "früh", "fruehe": "frühe", "fruehen": "frühen",
    "kuehl": "kühl", "wuenschen": "wünschen", "wuerde": "würde", "wuensche": "Wünsche",
    "muessen": "müssen", "muesse": "müsse", "duerfen": "dürfen", "duerfte": "dürfte",
    "ueberlebenszeit": "Überlebenszeit",
    # --- ß ---
    "gross": "groß", "grosse": "große", "grosser": "großer", "grosses": "großes",
    "grossen": "großen", "grossem": "großem", "groesse": "Größe", "groessen": "Größen",
    "groesser": "größer", "groessere": "größere", "groesseren": "größeren",
    "groesste": "größte", "groessten": "größten",
    "strasse": "Straße", "strassen": "Straßen",
    "ausser": "außer", "ausserdem": "außerdem", "aeusserst": "äußerst", "aeussere": "äußere",
    "aeusseren": "äußeren",
    "schliessen": "schließen", "schliesslich": "schließlich", "schliessende": "schließende",
    "schliessend": "schließend", "abschliessend": "abschließend", "abschliessende": "abschließende",
    "abschliessenden": "abschließenden",
    "massnahme": "Maßnahme", "massnahmen": "Maßnahmen", "massgeblich": "maßgeblich",
    "weiss": "weiß", "weisses": "weißes", "weisse": "weiße", "weissen": "weißen",
    "geniessen": "genießen", "vergroessern": "vergrößern", "vergroessert": "vergrößert",
}


def autofix_umlauts(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Rewrite curated ASCII transliterations to ä/ö/ü/ß; return (text, replacements).

    ``replacements`` is the ordered list of ``(before, after)`` pairs so the caller can
    log every substitution into the rule-check detail. Words are matched whole and
    case-insensitively; the initial letter's case is preserved.
    """
    replacements: list[tuple[str, str]] = []

    def _fix(match: re.Match[str]) -> str:
        word = match.group(0)
        low = word.lower()
        if low in UMLAUT_AUTOFIX_DENY:
            return word
        replacement = UMLAUT_AUTOFIX.get(low)
        if not replacement:
            return word
        fixed = replacement[:1].upper() + replacement[1:] if word[:1].isupper() else replacement
        if fixed != word:
            replacements.append((word, fixed))
            return fixed
        return word

    return _WORD_RE.sub(_fix, text or ""), replacements


# --------------------------------------------------------------------------- R-INVENT
#
# Source grounding (the method's „nichts erfinden“). The generated text is split
# into claims; for every claim its substantive clinical terms (numbers, findings,
# diagnoses, procedures, anatomical/medication/follow-up terms) are checked against
# the dictation's vocabulary. A claim is flagged when it carries **≥2** novel terms,
# or when it is an advice/recommendation sentence with no counterpart at all in the
# sources. Legitimate rephrasing is tolerated via a small German medical synonym map,
# light morphological stems and compound containment; generic words are ignored.
_RINVENT_FOLD = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"))
_RINVENT_UNIT_RE = re.compile(r"[a-z0-9]+")
_RINVENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_RINVENT_MIN_SOURCE_TERMS = 12
# Below this many substantive source terms the dictation is a pure stub (e.g. "Ulcus cruris
# venosum"): grounding cannot be judged at all, so the check stays silent. Between this and
# _RINVENT_MIN_SOURCE_TERMS only invented *recommendations* are flagged — the one case the LLM
# judge caught in production, where a short letter gained a complete follow-up recommendation.
_RINVENT_MIN_STUB_TERMS = 6
_RINVENT_MAX_FINDINGS = 8

# Small German medical synonym map: variant → canonical token (applied on both sides).
_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"unterbauchschmerzen", "unterbauchbeschwerden", "unterbauch"}),
    frozenset({"aufnahme", "aufgenommen", "aufnahm", "aufnahmen"}),
    frozenset({"entlassung", "entlassen", "entlassmanagement"}),
    frozenset({"notaufnahme", "notfallaufnahme", "nfa"}),
    frozenset({"kind", "junge", "maedchen", "maedchen", "saeugling", "baby"}),
    frozenset({"arzt", "aerztin", "doktor"}),
    frozenset({"medikament", "medikamente", "medikation", "arzneimittel"}),
    frozenset({"nachsorge", "nachuntersuchung", "wiedervorstellung"}),
    frozenset({"kontrolle", "ueberwachung", "nachkontrolle"}),
)
_RINVENT_SYNONYMS: dict[str, str] = {}
for _group in _SYNONYM_GROUPS:
    _canon = sorted(_group)[0]
    for _term in _group:
        _RINVENT_SYNONYMS[_term] = _canon

# Generic words that carry no clinical signal and must never count as "invented".
_RINVENT_GENERIC: frozenset[str] = frozenset(
    {
        "wir", "nahmen", "pat", "patientin", "patienten", "patientinnen", "zur", "zum",
        "weiteren", "weiterer", "diagnostik", "schmerztherapie", "keine", "kein",
        "angabe", "diktat", "xxx", "sowie", "werden", "wird", "wurde", "wurden",
        "erfolgt", "erfolgte", "erfolgten", "erfolgen", "ist", "sind", "war", "waren",
        "hat", "hatte", "haben", "kann", "konnte", "sollen", "sollte", "muss",
        "empfohlen", "empfehlen", "empfahl", "empfahlen", "empfehlung", "empfehlungen",
        "regelmaessig", "regelmaessige", "regelmaessigen", "regelmaessiger", "regelmaessiges",
        "regelmassig", "regelmaßig", "regelmäßig", "regelmäßige", "regelmäßigen",
        "zunehmend", "zunehmende", "zunehmenden", "zunehmender", "zunehmendes",
        "ausreichend", "ausreichende", "ausreichenden", "ausreichender", "ausreichendes",
        "bereits", "dabei", "hierbei", "zudem", "weiterhin", "insbesondere",
        "gegebenenfalls", "etwa", "circa", "ca", "ggf", "evtl", "bzw", "usw", "etc",
        "vielen", "dank", "weiterbetreuung", "zeigt", "zeigte", "zeigten", "besteht",
        "bestand", "bestehende", "bestehender", "vorlag", "lag", "lagen", "hier",
    }
) | frozenset(_GRAMMAR_STOPWORDS) | frozenset(_GENERIC_QUALIFIERS)

_RINVENT_RECO_CUES = (
    "empfehl", "empfahl", "wiedervorstellung", "nachsorge", "nachkontrolle",
    "kontrolle", "raten", "ratsam", "sollte", "wiedervorstellen",
)


def _rinvent_fold(text: str) -> str:
    low = (text or "").lower()
    for source, target in _RINVENT_FOLD:
        low = low.replace(source, target)
    return low


def _rinvent_canonical(token: str) -> str:
    return _RINVENT_SYNONYMS.get(token, token)


def _rinvent_ignored(token: str) -> bool:
    return token in _RINVENT_GENERIC


def _rinvent_stem(token: str) -> str:
    if len(token) > 5 and token[-2:] in {"en", "er", "es", "em"}:
        return token[:-2]
    if len(token) > 4 and token[-1] in {"e", "n", "s"}:
        return token[:-1]
    return token


def _rinvent_supported(token: str, vocab: frozenset[str], stems: frozenset[str], long_tokens: tuple[str, ...]) -> bool:
    if token in vocab:
        return True
    if any(character.isdigit() for character in token):
        return token in vocab
    canonical = _rinvent_canonical(token)
    if canonical != token and canonical in vocab:
        return True
    stem = _rinvent_stem(token)
    if stem in stems:
        return True
    canonical_stem = _rinvent_stem(canonical)
    if canonical_stem in stems:
        return True
    if len(token) >= 5:
        # German compounding: "Wunde" ⊂ "Wunddesinfektion", "Kontrolle" ⊂ "Wundkontrolle".
        # Without this, a faithful rewrite of a compound noun is reported as invention.
        for source in long_tokens:
            if source in token or token in source:
                return True
    return False


def _rinvent_skip_claim(claim: str, doc_type: str) -> tuple[bool, str]:
    """Return (skip, remainder). Sanctioned block labels are skipped / unwrapped."""
    stripped = (claim or "").strip()
    if not stripped:
        return True, ""
    match = _LABEL_RE.match(stripped)
    if not match:
        return False, stripped
    label = match.group(1).strip().lower()
    remainder = match.group(2).strip()
    if label in ALLOWED_LABELS or (label in ALLOWED_OPS_LABELS and doc_type == "operationsbericht"):
        return (True, "") if not remainder else (False, remainder)
    return False, stripped


def _check_invention(text: str, dictation: str, doc_type: str, reference: str = "") -> list[Finding]:
    """R-INVENT: flag claims whose substantive content is not grounded in the sources.

    ``reference`` is the reference knowledge that was actually put into the prompt (retrieved
    Musterbrief sections + grounded enrichment from the archive / web research). Terms that come
    from there are **not** inventions — the method explicitly allows standard technique/material
    details to be derived from the archive. Such a claim is reported as a SOFT finding
    ("aus Referenzwissen ergänzt – bitte prüfen") instead of a hard violation, so the member sees
    it without triggering a corrective retry.
    """
    source_tokens = _RINVENT_UNIT_RE.findall(_rinvent_fold(dictation or ""))
    if not source_tokens:
        return []
    ref_tokens = _RINVENT_UNIT_RE.findall(_rinvent_fold(reference or ""))
    ref_vocab = set(ref_tokens) | {_rinvent_canonical(token) for token in ref_tokens}
    ref_stems = frozenset(stem for token in ref_tokens if len(stem := _rinvent_stem(token)) >= 4)

    def _in_reference(token: str) -> bool:
        if not ref_vocab:
            return False
        if token in ref_vocab or _rinvent_canonical(token) in ref_vocab:
            return True
        stem = _rinvent_stem(token)
        return len(stem) >= 4 and stem in ref_stems

    vocab = set(source_tokens)
    vocab |= {_rinvent_canonical(token) for token in source_tokens}
    substantive_source = {token for token in vocab if len(token) >= 3 and not _rinvent_ignored(token)}
    # Too little material to judge grounding of ordinary claims — never guess invention from a stub.
    # Exception: an invented *recommendation* in a thin dictation is exactly the dangerous case
    # (measured: a complete follow-up recommendation appeared in a 450-char ambulant letter), so the
    # recommendation check stays active; every other claim is left alone for thin inputs.
    thin = len(substantive_source) < _RINVENT_MIN_SOURCE_TERMS
    if thin:
        if len(substantive_source) < _RINVENT_MIN_STUB_TERMS:
            return []  # pure stub — nothing to judge
        if not any(cue in _rinvent_fold(text or "") for cue in _RINVENT_RECO_CUES):
            return []
    stems = frozenset(
        stem for token in vocab if len(stem := _rinvent_stem(token)) >= 4
    )
    vocab_frozen = frozenset(vocab)
    long_tokens = tuple(sorted(token for token in vocab if len(token) >= 6))

    findings: list[Finding] = []
    seen: set[str] = set()
    for raw_claim in _RINVENT_SPLIT_RE.split(_strip_tokens(text)):
        skip, claim = _rinvent_skip_claim(raw_claim, doc_type)
        if skip:
            continue
        low = _rinvent_fold(claim)
        tokens = list(dict.fromkeys(_RINVENT_UNIT_RE.findall(low)))
        substantive = [token for token in tokens if len(token) >= 3 and not _rinvent_ignored(token)]
        if not substantive:
            continue
        novel = [
            token for token in substantive
            if not _rinvent_supported(token, vocab_frozen, stems, long_tokens)
        ]
        supported = [token for token in substantive if token not in novel]
        recommendation = any(cue in low for cue in _RINVENT_RECO_CUES)
        if thin and not recommendation:
            continue
        fires = len(novel) >= 2 or (recommendation and novel and not supported)
        if not fires:
            continue
        evidence = claim.strip()[:200]
        if evidence in seen:
            continue
        seen.add(evidence)
        from_reference = [token for token in novel if _in_reference(token)]
        if from_reference and len(from_reference) >= max(2, len(novel) - 1):
            findings.append(
                _finding(
                    "R-REFERENZ",
                    "Aus Referenzwissen ergänzt (nicht im Diktat) – bitte prüfen: "
                    + ", ".join(from_reference[:8]),
                    evidence,
                    severity="soft",
                )
            )
            if len(findings) >= _RINVENT_MAX_FINDINGS:
                break
            continue
        findings.append(
            _finding(
                "R-INVENT",
                "Unbelegte/erfundene Angabe (nicht im Diktat): " + ", ".join(novel[:8]),
                evidence,
            )
        )
        if len(findings) >= _RINVENT_MAX_FINDINGS:
            break
    return findings


# --------------------------------------------------------------------------- entry point


def check(
    text: str,
    doc_type: str,
    dictation: str = "",
    *,
    autofix: list[tuple[str, str]] | None = None,
    reference: str = "",
) -> CheckResult:
    """Run every deterministic rule against ``text`` and return a :class:`CheckResult`.

    ``autofix`` is the list of ``(before, after)`` umlaut substitutions already applied
    by :func:`autofix_umlauts`; each is recorded as a soft ``R6-AUTOFIX`` finding so the
    correction stays visible in the UI/audit.

    ``reference`` is the reference knowledge that was in the prompt (retrieved Musterbrief
    sections + grounded enrichment): terms from it count as supported and are reported as a soft
    ``R-REFERENZ`` note instead of a hard invention finding.
    """
    text = text or ""
    findings: list[Finding] = []
    findings.extend(_check_markdown(text))
    findings.extend(_check_labels(text, doc_type))
    findings.extend(_check_label_phrases(text))
    findings.extend(_check_intro_closing(text))
    findings.extend(_check_dg_prefix(text))
    findings.extend(_check_semicolon(text))
    findings.extend(_check_umlauts(text))
    findings.extend(_check_icd(text, dictation))
    findings.extend(_check_blocks(text, doc_type))
    findings.extend(_check_diagnosen(text, doc_type))
    findings.extend(_check_dates(text))
    findings.extend(_check_repeats(text))
    findings.extend(_check_pflichtsatz(text, doc_type))
    findings.extend(_check_invention(text, dictation, doc_type, reference))

    if autofix:
        for before, after in dict.fromkeys((str(b), str(a)) for b, a in autofix):
            findings.append(
                _finding("R6-AUTOFIX", f"Umlaut-Autokorrektur: „{before}“ → „{after}“", f"{before}->{after}", severity="soft")
            )

    # De-duplicate identical (rule_id, evidence) findings for a stable count.
    unique: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (finding.rule_id, finding.evidence)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)

    # Hard first, then by rule id (deterministic).
    unique.sort(key=lambda f: (0 if f.severity == "hard" else 1, f.rule_id))
    return CheckResult(findings=unique, doc_type=doc_type, rule_count=67)


__all__ = [
    "ALLOWED_LABELS",
    "ANTI_PATTERN_OF",
    "CheckResult",
    "Finding",
    "HARD_RULES",
    "LABEL_PHRASE_PATTERNS",
    "UMLAUT_AUTOFIX",
    "UMLAUT_AUTOFIX_DENY",
    "autofix_umlauts",
    "check",
]
