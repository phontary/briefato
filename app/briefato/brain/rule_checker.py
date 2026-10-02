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
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Rules whose violation blocks the letter (pipeline retries once, then attaches).
HARD_RULES: frozenset[str] = frozenset(
    {"R2", "R3", "R4", "R5", "R6", "R21", "R22", "R23", "R24", "R25", "R26", "R27", "R30", "R46", "R58", "AP-06"}
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
    "entlassung", "ekg", "röntgen", "endoskopie", "histologie", "medikation",
    "procedere", "aufnahmebefund", "untersuchung", "diagnose", "vorgeschichte",
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


# --------------------------------------------------------------------------- entry point


def check(text: str, doc_type: str, dictation: str = "") -> CheckResult:
    """Run every deterministic rule against ``text`` and return a :class:`CheckResult`."""
    text = text or ""
    findings: list[Finding] = []
    findings.extend(_check_markdown(text))
    findings.extend(_check_labels(text, doc_type))
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
    "check",
]
