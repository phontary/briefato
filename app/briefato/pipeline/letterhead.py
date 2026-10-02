"""DOCX letterhead rendering (python-docx, DIN 5008 oriented).

OWNER: WORKSTREAM-PIPELINE. Frozen API (docs/02-spec-interfaces.md §6)::

    def render_docx(letter_text: str, letterhead: dict, patient_ctx: dict,
                    out_path: Path, kind: str) -> Path

Layout (A4, 2.5 cm left/right margins): optional logo, sender block, DIN-5008-style
return-address line ("Rücksendeangabe"), right-aligned place/date, patient data block,
bold subject line, body paragraphs at 1.15 line spacing, a signature area and a footer
carrying the practice name. Every field is optional — an empty ``letterhead`` (or
``patient_ctx``) still produces a valid, openable document.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

from .prompts import KIND_LABELS

_GREY = RGBColor(0x60, 0x60, 0x60)
_SIGNATURE_RULE = "_" * 40


def _first(data: dict, *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _city_line(zip_code: str, city: str) -> str:
    return " ".join(part for part in (zip_code, city) if part).strip()


def _para(
    doc: Document,
    text: str = "",
    *,
    size: Pt | None = None,
    bold: bool = False,
    align: WD_ALIGN_PARAGRAPH | None = None,
    space_after: Pt | None = None,
    line_spacing: float | None = None,
    color: RGBColor | None = None,
):
    paragraph = doc.add_paragraph()
    if text:
        run = paragraph.add_run(text)
        run.bold = bold
        if size is not None:
            run.font.size = size
        if color is not None:
            run.font.color.rgb = color
    if align is not None:
        paragraph.alignment = align
    if space_after is not None:
        paragraph.paragraph_format.space_after = space_after
    if line_spacing is not None:
        paragraph.paragraph_format.line_spacing = line_spacing
    return paragraph


def _split_letter(text: str) -> tuple[str | None, list[str]]:
    """Split plain letter text into an optional bold subject and body paragraphs."""
    subject: str | None = None
    body: list[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if subject is None and re.match(r"(?i)^betreff\b", line):
            subject = re.sub(r"(?i)^betreff\s*:?\s*", "", line).strip() or line
            continue
        body.append(line)
    return subject, body


def render_docx(
    letter_text: str,
    letterhead: dict,
    patient_ctx: dict,
    out_path: Path,
    kind: str,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    letterhead = dict(letterhead or {})
    patient_ctx = dict(patient_ctx or {})

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(11)

    label = KIND_LABELS.get(kind, KIND_LABELS["sonstiges"])
    practice = _first(letterhead, "practice_name", "company")
    doctor = _first(letterhead, "full_name", "doctor_name", "signature_name")
    street = _first(letterhead, "street")
    zip_code = _first(letterhead, "zip")
    city = _first(letterhead, "city")
    phone = _first(letterhead, "phone")
    email = _first(letterhead, "email")
    tax_id = _first(letterhead, "tax_id", "tax_number")
    address = " · ".join(part for part in (street, _city_line(zip_code, city)) if part)

    # -- optional logo ---------------------------------------------------------
    logo = _first(letterhead, "logo_path", "logo")
    if logo:
        try:
            logo_path = Path(logo)
            if logo_path.exists():
                doc.add_picture(str(logo_path), width=Cm(4.0))
        except Exception:  # pragma: no cover - never fail rendering over a logo
            pass

    # -- sender block ----------------------------------------------------------
    if practice:
        _para(doc, practice, size=Pt(13), bold=True, space_after=Pt(0))
    if doctor and doctor != practice:
        _para(doc, doctor, size=Pt(10), space_after=Pt(0))
    if address:
        _para(doc, address, size=Pt(9), space_after=Pt(0))
    contact = " · ".join(part for part in (phone, email) if part)
    if contact:
        _para(doc, contact, size=Pt(8), space_after=Pt(0))
    if tax_id:
        _para(doc, f"Steuernummer: {tax_id}", size=Pt(8), space_after=Pt(0))

    # -- return-address line (Rücksendeangabe) ---------------------------------
    return_line = " · ".join(part for part in (practice, street, _city_line(zip_code, city)) if part)
    if return_line:
        _para(doc, return_line, size=Pt(8), color=_GREY, space_after=Pt(2))

    # -- place / date, right aligned under the sender block --------------------
    date_str = _first(letterhead, "date") or date.today().strftime("%d.%m.%Y")
    dateline = f"{city}, {date_str}" if city else date_str
    _para(doc, dateline, size=Pt(10), align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=Pt(10))

    # -- patient data block ----------------------------------------------------
    last = _first(patient_ctx, "last_name")
    first = _first(patient_ctx, "first_name")
    patient_name = f"{last}, {first}".strip(", ") if (last or first) else ""
    if patient_name:
        _para(doc, f"Patient/in: {patient_name}", size=Pt(10), space_after=Pt(0))
    birth_date = _first(patient_ctx, "birth_date")
    if birth_date:
        _para(doc, f"Geburtsdatum: {birth_date}", size=Pt(9), space_after=Pt(0))
    insurance_number = _first(patient_ctx, "insurance_number")
    if insurance_number:
        _para(doc, f"Versicherungsnummer: {insurance_number}", size=Pt(9), space_after=Pt(8))
    elif patient_name:
        _para(doc, "", size=Pt(6), space_after=Pt(6))

    # -- subject line (bold) ---------------------------------------------------
    subject, body = _split_letter(letter_text)
    if not subject:
        subject = f"{label}{(' – ' + patient_name) if patient_name else ''}"
    _para(doc, subject, size=Pt(11), bold=True, space_after=Pt(10))

    # -- body ------------------------------------------------------------------
    if not body and (letter_text or "").strip():
        body = [letter_text.strip()]
    for paragraph_text in body:
        _para(doc, paragraph_text, size=Pt(11), line_spacing=1.15, space_after=Pt(6))

    # -- signature area --------------------------------------------------------
    _para(doc, "", space_after=Pt(6))
    has_greeting = any("grüßen" in (line or "").lower() for line in body)
    if not has_greeting:
        _para(doc, "Mit freundlichen Grüßen", size=Pt(11), space_after=Pt(12))
    else:
        _para(doc, "", space_after=Pt(12))
    _para(doc, _SIGNATURE_RULE, size=Pt(11), space_after=Pt(0))
    signer = doctor or practice
    if signer:
        _para(doc, signer, size=Pt(9), space_after=Pt(0))

    # -- footer with practice name --------------------------------------------
    footer = section.footer
    footer_paragraph = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    footer_bits = " · ".join(
        part for part in (practice, street, _city_line(zip_code, city), phone) if part
    )
    footer_paragraph.text = footer_bits or practice
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in footer_paragraph.runs:
        run.font.size = Pt(8)

    doc.save(str(out_path))
    return out_path


__all__ = ["render_docx"]
