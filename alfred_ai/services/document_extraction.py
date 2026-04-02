from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser
from importlib import import_module
from io import BytesIO, StringIO
import html
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from typing import BinaryIO
from xml.etree import ElementTree
import zipfile

from pypdf import PdfReader

from alfred_ai.services.pdf_recovery import rebuild_orphaned_pdf

try:
    import pdfplumber
except Exception:  # pragma: no cover - optional runtime dependency
    pdfplumber = None

try:
    import fitz
except Exception:  # pragma: no cover - optional runtime dependency
    fitz = None


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
TEXTISH_EXTENSIONS = {".txt", ".md", ".csv", ".log"}
RICH_TEXT_EXTENSIONS = {".rtf", ".html", ".htm", ".xml"}
ARCHIVE_TEXT_EXTENSIONS = {".docx", ".odt"}

WORD_RE = re.compile(r"[A-Za-z]{3,}")
DATE_RE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
MONEY_RE = re.compile(r"(?:INR|RS\.?|₹)\s*[0-9,]+(?:\.\d{1,2})?", re.IGNORECASE)
TABLE_SPLIT_RE = re.compile(r"\s{2,}|\t+")
ISOLATED_OCR_TIMEOUT_SECONDS = max(30, int(os.getenv("DOCUMENT_ISOLATED_OCR_TIMEOUT_SECONDS", "60")))
ISOLATED_PDF_OCR_WORKER = textwrap.dedent(
    """
    import json
    import sys
    from io import BytesIO

    import fitz
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR

    def normalize(value):
        return " ".join(str(value or "").replace("\\uFF1A", ":").replace("₹", "Rs ").split())

    def group_rows(results):
        grouped = []
        for item in results or []:
            if len(item) < 2:
                continue
            box = item[0]
            text = normalize(item[1])
            if not text:
                continue
            top = min(float(point[1]) for point in box)
            left = min(float(point[0]) for point in box)
            if grouped and abs(grouped[-1][0] - top) <= 10:
                grouped[-1][1].append((left, text))
            else:
                grouped.append((top, [(left, text)]))
        lines = []
        for _, row in grouped:
            ordered = [text for _, text in sorted(row, key=lambda item: item[0])]
            line = normalize(" ".join(ordered))
            if line:
                lines.append(line)
        return lines

    pdf_path = sys.argv[1]
    page_limit = max(int(sys.argv[2]), 1)
    ocr = RapidOCR(no_cls=True, det_limit_side_len=1024, max_side_len=2048)
    document = fitz.open(pdf_path)
    pages = []
    try:
        for index in range(min(document.page_count, page_limit)):
            page = document.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png")))
            result, _ = ocr(image)
            lines = group_rows(result)
            if lines:
                pages.append("\\n".join(lines))
    finally:
        document.close()

    print(json.dumps({"text": "\\n\\n".join(part for part in pages if part).strip()}, ensure_ascii=False))
    """
)

logger = logging.getLogger(__name__)


class _HTMLTextStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        if data and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


@dataclass
class ExtractedDocumentText:
    text: str
    method: str
    confidence: float
    notes: list[str]


def extract_document_text(raw_bytes: bytes, filename: str, *, ocr_page_limit: int = 6) -> ExtractedDocumentText:
    extension = os.path.splitext((filename or "").lower())[1]
    notes: list[str] = []

    if extension == ".pdf":
        return _extract_pdf_text(raw_bytes, filename, ocr_page_limit=ocr_page_limit)
    if extension == ".docx":
        text = _extract_docx_text(raw_bytes)
        return _finalize_text(text, "docx_xml", notes)
    if extension == ".odt":
        text = _extract_odt_text(raw_bytes)
        return _finalize_text(text, "odt_xml", notes)
    if extension == ".rtf":
        text = _extract_rtf_text(raw_bytes)
        return _finalize_text(text, "rtf_text", notes)
    if extension in {".html", ".htm"}:
        text = _extract_html_text(raw_bytes)
        return _finalize_text(text, "html_text", notes)
    if extension in TEXTISH_EXTENSIONS:
        text = _decode_text(raw_bytes)
        return _finalize_text(text, "plain_text", notes)
    if extension in IMAGE_EXTENSIONS:
        text, method, method_notes = _extract_image_text(raw_bytes)
        return _finalize_text(text, method, notes + method_notes)

    text = _decode_text_fallback(raw_bytes)
    return _finalize_text(text, "binary_fallback", notes)


def _extract_pdf_text(raw_bytes: bytes, filename: str, *, ocr_page_limit: int) -> ExtractedDocumentText:
    notes: list[str] = []
    candidates: list[tuple[str, str]] = []

    pypdf_text = _extract_pdf_with_pypdf(raw_bytes, layout=False)
    if pypdf_text:
        candidates.append(("pypdf_text", pypdf_text))
    else:
        notes.append("pypdf plain-text extraction was empty.")

    pypdf_layout = _extract_pdf_with_pypdf(raw_bytes, layout=True)
    if pypdf_layout:
        candidates.append(("pypdf_layout", pypdf_layout))
    else:
        notes.append("pypdf layout extraction was empty.")

    plumber_text = _extract_pdf_with_pdfplumber(raw_bytes)
    if plumber_text:
        candidates.append(("pdfplumber_text_tables", plumber_text))
    else:
        notes.append("pdfplumber text/table extraction was empty.")

    fitz_text = _extract_pdf_with_fitz(raw_bytes)
    if fitz_text:
        candidates.append(("pymupdf_text", fitz_text))
    else:
        notes.append("PyMuPDF text extraction was empty.")

    fitz_blocks = _extract_pdf_with_fitz_blocks(raw_bytes)
    if fitz_blocks:
        candidates.append(("pymupdf_blocks", fitz_blocks))
    else:
        notes.append("PyMuPDF block extraction was empty.")

    repaired = rebuild_orphaned_pdf(raw_bytes)
    if repaired:
        notes.append(f"Recovered a structurally broken PDF ({repaired.page_count} page(s)).")
        for method, text in (
            ("repaired_pypdf_text", _extract_pdf_with_pypdf(repaired.repaired_bytes, layout=False)),
            ("repaired_pypdf_layout", _extract_pdf_with_pypdf(repaired.repaired_bytes, layout=True)),
            ("repaired_pdfplumber_text_tables", _extract_pdf_with_pdfplumber(repaired.repaired_bytes)),
            ("repaired_pymupdf_text", _extract_pdf_with_fitz(repaired.repaired_bytes)),
            ("repaired_pymupdf_blocks", _extract_pdf_with_fitz_blocks(repaired.repaired_bytes)),
        ):
            if text:
                candidates.append((method, text))
    else:
        notes.append("No repairable orphaned PDF structure was found.")

    if not candidates:
        ocr_text, ocr_method, ocr_notes = _extract_pdf_with_ocr(raw_bytes, page_limit=ocr_page_limit)
        if repaired and not ocr_text:
            ocr_text, ocr_method, ocr_notes = _extract_pdf_with_ocr(repaired.repaired_bytes, page_limit=ocr_page_limit)
        if ocr_text:
            return _finalize_text(ocr_text, ocr_method, notes + ocr_notes)
        return _finalize_text("", "pdf_failed", notes + ocr_notes)

    method, text = max(candidates, key=lambda item: _text_quality_score(item[1]))
    finalized = _finalize_text(text, method, notes)

    if finalized.confidence < 0.6:
        ocr_text, ocr_method, ocr_notes = _extract_pdf_with_ocr(raw_bytes, page_limit=min(ocr_page_limit, 4))
        if ocr_text and _text_quality_score(ocr_text) > _text_quality_score(finalized.text):
            return _finalize_text(ocr_text, ocr_method, notes + ocr_notes + [f"OCR outperformed {method}."])
        finalized.notes.extend(ocr_notes)

    return finalized


def _extract_pdf_with_pypdf(raw_bytes: bytes, *, layout: bool) -> str:
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            reader = PdfReader(BytesIO(raw_bytes))
        pages = []
        for page in reader.pages:
            if layout:
                pages.append(page.extract_text(extraction_mode="layout") or "")
            else:
                pages.append(page.extract_text() or "")
        return _clean_text("\n".join(pages))
    except Exception:
        return ""


def _extract_pdf_with_pdfplumber(raw_bytes: bytes) -> str:
    if not pdfplumber:
        return ""
    try:
        with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
            parts = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    parts.append(text)
                parts.extend(_flatten_tables(page.extract_tables() or []))
        return _clean_text("\n".join(parts))
    except Exception:
        return ""


def _extract_pdf_with_fitz(raw_bytes: bytes) -> str:
    if not fitz:
        return ""
    try:
        document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception:
        return ""
    try:
        pages = [document.load_page(index).get_text("text", sort=True) or "" for index in range(document.page_count)]
    finally:
        document.close()
    return _clean_text("\n".join(pages))


def _extract_pdf_with_fitz_blocks(raw_bytes: bytes) -> str:
    if not fitz:
        return ""
    try:
        document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception:
        return ""
    parts: list[str] = []
    try:
        for index in range(document.page_count):
            page = document.load_page(index)
            blocks = page.get_text("blocks") or []
            ordered = sorted(blocks, key=lambda item: (round(item[1], 1), round(item[0], 1)))
            parts.extend(str(block[4]).strip() for block in ordered if len(block) > 4 and str(block[4]).strip())
    finally:
        document.close()
    return _clean_text("\n".join(parts))


def _extract_pdf_with_ocr(raw_bytes: bytes, *, page_limit: int) -> tuple[str, str, list[str]]:
    if not fitz:
        isolated_text = _extract_pdf_with_isolated_ocr(raw_bytes, page_limit=page_limit)
        if isolated_text:
            return isolated_text, "isolated_rapidocr_pdf", ["OCR fallback recovered text using isolated_rapidocr_pdf."]
        return "", "ocr_unavailable", ["PyMuPDF is not available for OCR rendering."]
    try:
        document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception:
        return "", "ocr_unavailable", ["PDF could not be opened for OCR."]

    rapid_ocr, pytesseract, image_module = _load_ocr_dependencies()
    notes: list[str] = []
    parts: list[tuple[str, str]] = []
    try:
        for index in range(min(document.page_count, page_limit)):
            page = document.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            if not image_module:
                continue
            image = image_module.open(BytesIO(pix.tobytes("png")))
            if rapid_ocr:
                text = _extract_image_with_rapidocr(rapid_ocr, image)
                if text:
                    parts.append(("rapidocr_pdf", text))
            if pytesseract:
                try:
                    text = pytesseract.image_to_string(image)
                except Exception:
                    text = ""
                if text:
                    parts.append(("tesseract_pdf", text))
    finally:
        document.close()

    if not parts:
        isolated_text = _extract_pdf_with_isolated_ocr(raw_bytes, page_limit=page_limit)
        if isolated_text:
            notes.append("OCR fallback recovered text using isolated_rapidocr_pdf.")
            return _clean_text(isolated_text), "isolated_rapidocr_pdf", notes
        notes.append("OCR fallback did not recover readable text.")
        return "", "ocr_failed", notes

    method, text = max(parts, key=lambda item: _text_quality_score(item[1]))
    notes.append(f"OCR fallback recovered text using {method}.")
    return _clean_text(text), method, notes


def _extract_image_text(raw_bytes: bytes) -> tuple[str, str, list[str]]:
    rapid_ocr, pytesseract, image_module = _load_ocr_dependencies()
    if not image_module:
        return "", "ocr_unavailable", ["Image OCR dependencies are not available."]
    try:
        image = image_module.open(BytesIO(raw_bytes))
    except Exception:
        return "", "ocr_unavailable", ["Image file could not be opened for OCR."]

    parts: list[tuple[str, str]] = []
    notes: list[str] = []
    if rapid_ocr:
        text = _extract_image_with_rapidocr(rapid_ocr, image)
        if text:
            parts.append(("rapidocr_image", text))
    if pytesseract:
        try:
            text = pytesseract.image_to_string(image)
        except Exception:
            text = ""
        if text:
            parts.append(("tesseract_image", text))
    if not parts:
        notes.append("OCR did not recover readable image text.")
        return "", "ocr_failed", notes
    method, text = max(parts, key=lambda item: _text_quality_score(item[1]))
    notes.append(f"Image OCR recovered text using {method}.")
    return _clean_text(text), method, notes


def _extract_image_with_rapidocr(rapid_ocr, image) -> str:
    try:
        result, _ = rapid_ocr(image)
    except Exception:
        return ""
    lines = []
    for item in result or []:
        if len(item) < 2:
            continue
        text = _clean_text(str(item[1]))
        if text:
            lines.append(text)
    return "\n".join(lines)


def _extract_pdf_with_isolated_ocr(raw_bytes: bytes, *, page_limit: int) -> str:
    if len(raw_bytes) < 2048:
        return ""
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(raw_bytes)
            temp_path = handle.name

        completed = subprocess.run(
            [sys.executable, "-c", ISOLATED_PDF_OCR_WORKER, temp_path, str(max(page_limit, 1))],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=ISOLATED_OCR_TIMEOUT_SECONDS,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if completed.returncode != 0:
            return ""
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return ""
        payload = json.loads(lines[-1])
        return _clean_text(str(payload.get("text") or ""))
    except Exception:
        logger.warning("Isolated OCR extraction failed for document upload.", exc_info=True)
        return ""
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning("Temporary OCR cleanup failed for %s.", temp_path, exc_info=True)


def _flatten_tables(tables: list) -> list[str]:
    lines: list[str] = []
    for table in tables:
        for row in table or []:
            cleaned = [str(cell).strip() for cell in (row or []) if cell not in (None, "")]
            if cleaned:
                lines.append("\t".join(cleaned))
    return lines


def _extract_docx_text(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
            document = archive.read("word/document.xml")
    except Exception:
        return ""
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError:
        return ""
    text_parts = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
    return _clean_text(html.unescape("\n".join(text_parts)))


def _extract_odt_text(raw_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
            document = archive.read("content.xml")
    except Exception:
        return ""
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError:
        return ""
    text_parts = [node.text.strip() for node in root.iter() if node.text and node.text.strip()]
    return _clean_text(html.unescape("\n".join(text_parts)))


def _extract_rtf_text(raw_bytes: bytes) -> str:
    text = _decode_text(raw_bytes)
    if not text:
        return ""
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\par[d]?", "\n", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return _clean_text(html.unescape(text))


def _extract_html_text(raw_bytes: bytes) -> str:
    text = _decode_text(raw_bytes)
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
    parser = _HTMLTextStripper()
    try:
        parser.feed(text)
        return _clean_text(html.unescape(parser.text()))
    except Exception:
        return _clean_text(html.unescape(re.sub(r"<[^>]+>", " ", text)))


def _decode_text(raw_bytes: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1", errors="ignore")


def _decode_text_fallback(raw_bytes: bytes) -> str:
    text = _decode_text(raw_bytes)
    printable = sum(1 for char in text if char.isprintable() or char.isspace())
    ratio = printable / max(len(text), 1)
    return _clean_text(text) if ratio >= 0.82 else ""


def _finalize_text(text: str, method: str, notes: list[str]) -> ExtractedDocumentText:
    cleaned = _clean_text(text)
    confidence = round(min(_text_quality_score(cleaned), 0.97), 2)
    return ExtractedDocumentText(text=cleaned[:30000], method=method, confidence=confidence, notes=notes[:8])


def _text_quality_score(text: str) -> float:
    if not text.strip():
        return 0.0
    normalized = text.strip()
    confidence = 0.2
    char_count = len(normalized)
    word_count = len(WORD_RE.findall(normalized))
    line_count = len([line for line in normalized.splitlines() if line.strip()])
    if char_count >= 120:
        confidence += 0.15
    if char_count >= 900:
        confidence += 0.15
    if word_count >= 25:
        confidence += 0.12
    if line_count >= 8:
        confidence += 0.08
    if DATE_RE.search(normalized):
        confidence += 0.06
    if MONEY_RE.search(normalized):
        confidence += 0.06
    if "\t" in normalized or TABLE_SPLIT_RE.search(normalized):
        confidence += 0.08
    alpha_ratio = sum(char.isalpha() for char in normalized) / max(len(normalized), 1)
    if 0.2 <= alpha_ratio <= 0.92:
        confidence += 0.07
    return confidence


def _clean_text(text: str) -> str:
    return (text or "").replace("\ufeff", "").replace("\xa0", " ").replace("Ã¢â€šÂ¹", "₹").strip()


@lru_cache(maxsize=1)
def _load_ocr_dependencies():
    rapid_ocr = None
    pytesseract = None
    image_module = None
    try:
        rapid_ocr = import_module("rapidocr_onnxruntime").RapidOCR(no_cls=True)
    except Exception:
        rapid_ocr = None
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            pytesseract = import_module("pytesseract")
            image_module = import_module("PIL.Image")
    except Exception:
        pytesseract = None
        image_module = None
    configured_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if pytesseract and configured_cmd:
        pytesseract.pytesseract.tesseract_cmd = configured_cmd
    return rapid_ocr, pytesseract, image_module
