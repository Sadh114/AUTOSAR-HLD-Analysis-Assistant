"""
PDF ingestion: text/heading/table extraction with OCR fallback for
scanned pages, followed by heading-aware chunking.
"""
import io
import re
import uuid
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from backend import config

try:
    import pytesseract
    from PIL import Image
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    filename: str
    page: int
    section: str
    text: str


@dataclass
class IngestResult:
    doc_id: str
    filename: str
    pages: int
    ocr_pages: int
    chunks: list = field(default_factory=list)


def _is_heading(span: dict, body_size: float) -> bool:
    """Heuristic: a heading is bold and/or noticeably larger than body text."""
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    is_bold = bool(flags & 2 ** 4)
    text = span.get("text", "").strip()
    if not text or len(text) > 120:
        return False
    return size >= body_size + 1.5 or (is_bold and size >= body_size)


def _extract_page_text_and_headings(page: "fitz.Page"):
    """Return (plain_text, list_of_headings_in_order, needs_ocr)."""
    page_dict = page.get_text("dict")
    sizes = []
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip():
                    sizes.append(span.get("size", 0))
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 10.0

    lines_out = []
    headings = []
    for block in page_dict.get("blocks", []):
        for line in block.get("lines", []):
            line_text = "".join(s.get("text", "") for s in line.get("spans", [])).strip()
            if not line_text:
                continue
            lines_out.append(line_text)
            for span in line.get("spans", []):
                if _is_heading(span, body_size):
                    headings.append(line_text)
                    break

    plain_text = "\n".join(lines_out)
    needs_ocr = len(plain_text.strip()) < 20
    return plain_text, headings, needs_ocr


def _ocr_page(page: "fitz.Page") -> str:
    if not OCR_AVAILABLE:
        return ""
    try:
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _extract_tables_as_text(page: "fitz.Page") -> str:
    """Best-effort table extraction using PyMuPDF's built-in table finder."""
    try:
        tabs = page.find_tables()
        parts = []
        for t in tabs.tables:
            rows = t.extract()
            for row in rows:
                cells = [str(c).strip() if c is not None else "" for c in row]
                if any(cells):
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    except Exception:
        return ""


def _split_into_sections(page_text: str, headings: list, page_num: int, default_section: str):
    """Split a page's text into (section_title, text) segments using detected headings."""
    if not headings:
        return [(default_section, page_text)]

    segments = []
    remaining = page_text
    current_section = default_section
    # Walk headings in order they appear, splitting text around them.
    for heading in headings:
        idx = remaining.find(heading)
        if idx == -1:
            continue
        before = remaining[:idx].strip()
        if before:
            segments.append((current_section, before))
        current_section = heading
        remaining = remaining[idx + len(heading):]
    if remaining.strip():
        segments.append((current_section, remaining.strip()))
    return segments if segments else [(default_section, page_text)]


def _chunk_text(text: str, max_chars: int, overlap: int):
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks


def ingest_pdf(file_bytes: bytes, filename: str) -> IngestResult:
    doc_id = uuid.uuid4().hex[:12]
    pdf = fitz.open(stream=file_bytes, filetype="pdf")

    chunks: list[Chunk] = []
    ocr_page_count = 0
    current_section = "Document Start"
    seq = 0  # zero-padded into chunk ids so chunks sort back into document order

    for page_num, page in enumerate(pdf, start=1):
        plain_text, headings, needs_ocr = _extract_page_text_and_headings(page)
        table_text = _extract_tables_as_text(page)

        if needs_ocr:
            ocr_text = _ocr_page(page)
            if ocr_text.strip():
                plain_text = ocr_text
                ocr_page_count += 1
                headings = []  # heading detection not reliable on OCR text

        full_page_text = plain_text
        if table_text:
            full_page_text = f"{plain_text}\n\n[TABLE]\n{table_text}"

        if not full_page_text.strip():
            continue

        segments = _split_into_sections(full_page_text, headings, page_num, current_section)
        for section_title, seg_text in segments:
            current_section = section_title
            for piece in _chunk_text(seg_text, config.CHUNK_MAX_CHARS, config.CHUNK_OVERLAP_CHARS):
                if not piece.strip():
                    continue
                seq += 1
                chunks.append(
                    Chunk(
                        chunk_id=f"{doc_id}_{seq:05d}",
                        doc_id=doc_id,
                        filename=filename,
                        page=page_num,
                        section=section_title[:150],
                        text=piece,
                    )
                )

    result = IngestResult(
        doc_id=doc_id,
        filename=filename,
        pages=pdf.page_count,
        ocr_pages=ocr_page_count,
        chunks=chunks,
    )
    pdf.close()
    return result
