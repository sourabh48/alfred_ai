from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
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
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")
VEHICLE_NUMBER_RE = re.compile(r"\b(?:[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}|\d{2}[\s-]?BH[\s-]?\d{4}[\s-]?[A-Z]{2})\b", re.IGNORECASE)
REFERENCE_NUMBER_RE = re.compile(
    r"\b(?:account|acct|loan|policy|invoice|bill|application|report|document|rc|registration)\s*(?:number|no\.?|id|#)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]{4,28})",
    re.IGNORECASE,
)
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
        regions = []
        for item in results or []:
            if len(item) < 2:
                continue
            box = item[0]
            raw = item[1]
            if isinstance(raw, (list, tuple)):
                text = normalize(raw[0] if raw else "")
                score = float(raw[1]) if len(raw) > 1 else 0
            else:
                text = normalize(raw)
                score = float(item[2]) if len(item) > 2 and item[2] not in ("", None) else 0
            if not text:
                continue
            top = min(float(point[1]) for point in box)
            left = min(float(point[0]) for point in box)
            regions.append({
                "text": text[:120],
                "confidence": round(score, 2),
                "bbox": [[round(float(point[0]), 1), round(float(point[1]), 1)] for point in box[:4]],
                "origin": "isolated_rapidocr_pdf",
            })
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
        return lines, regions

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
            lines, regions = group_rows(result)
            if lines:
                pages.append({
                    "page": index + 1,
                    "width": image.width,
                    "height": image.height,
                    "preview": " ".join(lines[:3])[:220],
                    "line_count": len(lines),
                    "regions": regions[:10],
                    "text": "\\n".join(lines),
                })
    finally:
        document.close()

    print(json.dumps({
        "text": "\\n\\n".join(part["text"] for part in pages if part.get("text")).strip(),
        "pages": [{key: value for key, value in part.items() if key != "text"} for part in pages],
    }, ensure_ascii=False))
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
    review_payload: dict = field(default_factory=dict)


def _document_hint_from_filename(filename: str) -> str:
    lowered = (filename or "").lower()
    if any(token in lowered for token in ("resume", "cv", "curriculum")):
        return "resume_document"
    if any(token in lowered for token in ("cibil", "credit", "experian", "equifax", "crif")):
        return "credit_report"
    if any(token in lowered for token in ("portfolio", "holding", "broker", "mutual", "zerodha", "groww")):
        return "investment_document"
    if any(token in lowered for token in ("closure", "foreclosure", "no-due", "noc")):
        return "loan_closure_document"
    if any(token in lowered for token in ("loan", "sanction", "emi", "repayment")):
        return "loan_document"
    if any(token in lowered for token in ("invoice", "service", "bike", "vehicle", "insurance", "puc", "rc")):
        return "vehicle_document"
    return "general_document"


def extract_document_text(raw_bytes: bytes, filename: str, *, ocr_page_limit: int = 6) -> ExtractedDocumentText:
    extension = os.path.splitext((filename or "").lower())[1]
    notes: list[str] = []
    document_hint = _document_hint_from_filename(filename)

    if extension == ".pdf":
        return _extract_pdf_text(raw_bytes, filename, ocr_page_limit=ocr_page_limit, document_hint=document_hint)
    if extension == ".docx":
        text = _extract_docx_text(raw_bytes)
        return _finalize_text(text, "docx_xml", notes, {"document_hint": document_hint})
    if extension == ".odt":
        text = _extract_odt_text(raw_bytes)
        return _finalize_text(text, "odt_xml", notes, {"document_hint": document_hint})
    if extension == ".rtf":
        text = _extract_rtf_text(raw_bytes)
        return _finalize_text(text, "rtf_text", notes, {"document_hint": document_hint})
    if extension in {".html", ".htm"}:
        text = _extract_html_text(raw_bytes)
        return _finalize_text(text, "html_text", notes, {"document_hint": document_hint})
    if extension in TEXTISH_EXTENSIONS:
        text = _decode_text(raw_bytes)
        return _finalize_text(text, "plain_text", notes, {"document_hint": document_hint})
    if extension in IMAGE_EXTENSIONS:
        text, method, method_notes, review_payload = _extract_image_text(raw_bytes, extension_hint=extension, document_hint=document_hint)
        return _finalize_text(text, method, notes + method_notes, review_payload)

    text = _decode_text_fallback(raw_bytes)
    return _finalize_text(text, "binary_fallback", notes, {"document_hint": document_hint})


def _extract_pdf_text(raw_bytes: bytes, filename: str, *, ocr_page_limit: int, document_hint: str) -> ExtractedDocumentText:
    notes: list[str] = []
    candidates: list[tuple[str, str]] = []
    review_payload = {
        "document_hint": document_hint,
        "recovery_steps": [],
        "attempts": [],
    }

    pypdf_text = _extract_pdf_with_pypdf(raw_bytes, layout=False)
    if pypdf_text:
        candidates.append(("pypdf_text", pypdf_text))
        review_payload["attempts"].append({"method": "pypdf_text", "quality": round(_text_quality_score(pypdf_text), 2)})
    else:
        notes.append("pypdf plain-text extraction was empty.")
        review_payload["attempts"].append({"method": "pypdf_text", "quality": 0.0, "state": "empty"})

    pypdf_layout = _extract_pdf_with_pypdf(raw_bytes, layout=True)
    if pypdf_layout:
        candidates.append(("pypdf_layout", pypdf_layout))
        review_payload["attempts"].append({"method": "pypdf_layout", "quality": round(_text_quality_score(pypdf_layout), 2)})
    else:
        notes.append("pypdf layout extraction was empty.")
        review_payload["attempts"].append({"method": "pypdf_layout", "quality": 0.0, "state": "empty"})

    plumber_text = _extract_pdf_with_pdfplumber(raw_bytes)
    if plumber_text:
        candidates.append(("pdfplumber_text_tables", plumber_text))
        review_payload["attempts"].append({"method": "pdfplumber_text_tables", "quality": round(_text_quality_score(plumber_text), 2)})
    else:
        notes.append("pdfplumber text/table extraction was empty.")
        review_payload["attempts"].append({"method": "pdfplumber_text_tables", "quality": 0.0, "state": "empty"})

    fitz_text = _extract_pdf_with_fitz(raw_bytes)
    if fitz_text:
        candidates.append(("pymupdf_text", fitz_text))
        review_payload["attempts"].append({"method": "pymupdf_text", "quality": round(_text_quality_score(fitz_text), 2)})
    else:
        notes.append("PyMuPDF text extraction was empty.")
        review_payload["attempts"].append({"method": "pymupdf_text", "quality": 0.0, "state": "empty"})

    fitz_blocks = _extract_pdf_with_fitz_blocks(raw_bytes)
    if fitz_blocks:
        candidates.append(("pymupdf_blocks", fitz_blocks))
        review_payload["attempts"].append({"method": "pymupdf_blocks", "quality": round(_text_quality_score(fitz_blocks), 2)})
    else:
        notes.append("PyMuPDF block extraction was empty.")
        review_payload["attempts"].append({"method": "pymupdf_blocks", "quality": 0.0, "state": "empty"})

    repaired = rebuild_orphaned_pdf(raw_bytes)
    if repaired:
        notes.append(f"Recovered a structurally broken PDF ({repaired.page_count} page(s)).")
        review_payload["recovery_steps"].append(
            {"step": "rebuild_orphaned_pdf", "status": "recovered", "page_count": int(repaired.page_count)}
        )
        for method, text in (
            ("repaired_pypdf_text", _extract_pdf_with_pypdf(repaired.repaired_bytes, layout=False)),
            ("repaired_pypdf_layout", _extract_pdf_with_pypdf(repaired.repaired_bytes, layout=True)),
            ("repaired_pdfplumber_text_tables", _extract_pdf_with_pdfplumber(repaired.repaired_bytes)),
            ("repaired_pymupdf_text", _extract_pdf_with_fitz(repaired.repaired_bytes)),
            ("repaired_pymupdf_blocks", _extract_pdf_with_fitz_blocks(repaired.repaired_bytes)),
        ):
            if text:
                candidates.append((method, text))
                review_payload["attempts"].append({"method": method, "quality": round(_text_quality_score(text), 2)})
            else:
                review_payload["attempts"].append({"method": method, "quality": 0.0, "state": "empty"})
    else:
        notes.append("No repairable orphaned PDF structure was found.")
        review_payload["recovery_steps"].append({"step": "rebuild_orphaned_pdf", "status": "not_applicable"})

    if not candidates:
        ocr_text, ocr_method, ocr_notes, ocr_review = _extract_pdf_with_ocr(
            raw_bytes,
            page_limit=ocr_page_limit,
            document_hint=document_hint,
        )
        if repaired and not ocr_text:
            ocr_text, ocr_method, ocr_notes, ocr_review = _extract_pdf_with_ocr(
                repaired.repaired_bytes,
                page_limit=ocr_page_limit,
                document_hint=document_hint,
            )
            if ocr_text:
                ocr_review = _merge_review_payloads(
                    ocr_review,
                    {"recovery_steps": [{"step": "ocr_on_repaired_pdf", "status": "recovered"}]},
                )
        if not ocr_text:
            image_text, image_method, image_notes, image_review = _extract_image_text(
                raw_bytes,
                extension_hint=".pdf",
                document_hint=document_hint,
                allow_rotation=True,
            )
            if image_text:
                merged_notes = notes + ocr_notes + image_notes + ["Recovered text from image bytes despite the .pdf extension."]
                image_review = _merge_review_payloads(
                    review_payload,
                    image_review,
                    {"recovery_steps": [{"step": "image_bytes_fallback", "status": "recovered"}]},
                )
                return _finalize_text(image_text, image_method, merged_notes, image_review)
        if ocr_text:
            return _finalize_text(
                ocr_text,
                ocr_method,
                notes + ocr_notes,
                _merge_review_payloads(review_payload, ocr_review),
            )
        return _finalize_text("", "pdf_failed", notes + ocr_notes, _merge_review_payloads(review_payload, ocr_review))

    method, text = max(candidates, key=lambda item: _text_quality_score(item[1]))
    finalized = _finalize_text(
        text,
        method,
        notes,
        _merge_review_payloads(review_payload, {"best_method": method}),
    )

    if finalized.confidence < 0.6:
        ocr_text, ocr_method, ocr_notes, ocr_review = _extract_pdf_with_ocr(
            raw_bytes,
            page_limit=min(ocr_page_limit, 4),
            document_hint=document_hint,
        )
        if ocr_text and _text_quality_score(ocr_text) > _text_quality_score(finalized.text):
            return _finalize_text(
                ocr_text,
                ocr_method,
                notes + ocr_notes + [f"OCR outperformed {method}."],
                _merge_review_payloads(review_payload, ocr_review, {"best_method": ocr_method}),
            )
        finalized.notes.extend(ocr_notes)
        finalized.review_payload = _merge_review_payloads(finalized.review_payload, ocr_review)

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


def _extract_pdf_with_ocr(raw_bytes: bytes, *, page_limit: int, document_hint: str) -> tuple[str, str, list[str], dict]:
    if not fitz:
        isolated = _extract_pdf_with_isolated_ocr(raw_bytes, page_limit=page_limit)
        if isolated["text"]:
            return isolated["text"], "isolated_rapidocr_pdf", ["OCR fallback recovered text using isolated_rapidocr_pdf."], isolated["review_payload"]
        return "", "ocr_unavailable", ["PyMuPDF is not available for OCR rendering."], isolated["review_payload"]
    try:
        document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception:
        isolated = _extract_pdf_with_isolated_ocr(raw_bytes, page_limit=page_limit)
        if isolated["text"]:
            review_payload = _merge_review_payloads(
                isolated["review_payload"],
                {"recovery_steps": [{"step": "open_pdf_for_ocr", "status": "failed"}, {"step": "isolated_ocr", "status": "recovered"}]},
            )
            return isolated["text"], "isolated_rapidocr_pdf", ["PDF could not be opened for OCR, but isolated OCR recovered readable text."], review_payload
        return "", "ocr_unavailable", ["PDF could not be opened for OCR."], {"document_hint": document_hint, "recovery_steps": [{"step": "open_pdf_for_ocr", "status": "failed"}]}

    rapid_ocr, pytesseract, image_module, image_ops, image_filter = _load_ocr_dependencies()
    notes: list[str] = []
    method_pages: dict[str, list[str]] = {}
    ocr_pages: list[dict] = []
    recovery_steps = [{"step": "render_pdf_pages", "status": "started"}]
    try:
        for index in range(min(document.page_count, page_limit)):
            page = document.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            if not image_module:
                continue
            try:
                image = _open_image_bytes(pix.tobytes("png"), image_module=image_module, image_ops=image_ops)
            except Exception:
                continue

            best_rapid_text = ""
            best_rapid_score = 0.0
            best_review_page = {}
            for variant_name, variant_image, metadata in _prepare_image_variants(
                image,
                image_ops=image_ops,
                image_filter=image_filter,
                allow_rotation=True,
            ):
                if rapid_ocr:
                    rapid_text, review_page = _extract_image_with_rapidocr(
                        rapid_ocr,
                        variant_image,
                        origin="rapidocr_pdf",
                        page_number=index + 1,
                        variant_name=variant_name,
                        rotation=int(metadata.get("rotation") or 0),
                    )
                    rapid_score = _text_quality_score(rapid_text)
                    if rapid_text and rapid_score > best_rapid_score:
                        best_rapid_text = rapid_text
                        best_rapid_score = rapid_score
                        best_review_page = review_page
                if pytesseract:
                    try:
                        tesseract_text = pytesseract.image_to_string(variant_image)
                    except Exception:
                        tesseract_text = ""
                    if tesseract_text:
                        current = method_pages.setdefault("tesseract_pdf", [])
                        if len(current) <= index:
                            current.extend([""] * (index + 1 - len(current)))
                        if _text_quality_score(tesseract_text) > _text_quality_score(current[index]):
                            current[index] = _clean_text(tesseract_text)
            if best_rapid_text:
                current = method_pages.setdefault("rapidocr_pdf", [])
                if len(current) <= index:
                    current.extend([""] * (index + 1 - len(current)))
                current[index] = _clean_text(best_rapid_text)
            if best_review_page:
                ocr_pages.append(best_review_page)
    finally:
        document.close()

    candidates = [
        (method, _clean_text("\n\n".join(part for part in pages if part).strip()))
        for method, pages in method_pages.items()
    ]
    candidates = [(method, text) for method, text in candidates if text]
    recovery_steps[0]["status"] = "completed"
    review_payload = {
        "document_hint": document_hint,
        "ocr_pages": ocr_pages,
        "recovery_steps": recovery_steps,
        "attempts": [{"method": method, "quality": round(_text_quality_score(text), 2)} for method, text in candidates],
    }

    if not candidates:
        isolated = _extract_pdf_with_isolated_ocr(raw_bytes, page_limit=page_limit)
        if isolated["text"]:
            notes.append("OCR fallback recovered text using isolated_rapidocr_pdf.")
            return _clean_text(isolated["text"]), "isolated_rapidocr_pdf", notes, _merge_review_payloads(review_payload, isolated["review_payload"])
        notes.append("OCR fallback did not recover readable text.")
        return "", "ocr_failed", notes, _merge_review_payloads(review_payload, isolated["review_payload"])

    method, text = max(candidates, key=lambda item: _text_quality_score(item[1]))
    notes.append(f"OCR fallback recovered text using {method}.")
    return _clean_text(text), method, notes, _merge_review_payloads(review_payload, {"best_method": method})


def _extract_image_text(
    raw_bytes: bytes,
    *,
    extension_hint: str = "",
    document_hint: str = "",
    allow_rotation: bool = True,
) -> tuple[str, str, list[str], dict]:
    rapid_ocr, pytesseract, image_module, image_ops, image_filter = _load_ocr_dependencies()
    if not image_module:
        return "", "ocr_unavailable", ["Image OCR dependencies are not available."], {"document_hint": document_hint}
    try:
        image = _open_image_bytes(raw_bytes, image_module=image_module, image_ops=image_ops)
    except Exception:
        return "", "ocr_unavailable", ["Image file could not be opened for OCR."], {"document_hint": document_hint}

    notes: list[str] = []
    candidates: list[tuple[str, str, dict]] = []
    rapid_overlay = {}
    attempted_variants: list[dict] = []
    for variant_name, variant_image, metadata in _prepare_image_variants(
        image,
        image_ops=image_ops,
        image_filter=image_filter,
        allow_rotation=allow_rotation,
    ):
        attempted_variants.append({"variant": variant_name, "rotation": int(metadata.get("rotation") or 0)})
        if rapid_ocr:
            rapid_text, review_page = _extract_image_with_rapidocr(
                rapid_ocr,
                variant_image,
                origin="rapidocr_image",
                page_number=1,
                variant_name=variant_name,
                rotation=int(metadata.get("rotation") or 0),
            )
            if rapid_text:
                review_payload = {"ocr_pages": [review_page], "best_variant": variant_name}
                candidates.append(("rapidocr_image", rapid_text, review_payload))
                if not rapid_overlay or _text_quality_score(rapid_text) > _text_quality_score((rapid_overlay.get("ocr_pages") or [{}])[0].get("preview", "")):
                    rapid_overlay = review_payload
        if pytesseract:
            try:
                tesseract_text = pytesseract.image_to_string(variant_image)
            except Exception:
                tesseract_text = ""
            if tesseract_text:
                candidates.append(("tesseract_image", _clean_text(tesseract_text), {"best_variant": variant_name}))
    if not candidates:
        notes.append("OCR did not recover readable image text.")
        return "", "ocr_failed", notes, {"document_hint": document_hint, "attempted_variants": attempted_variants}
    method, text, method_review = max(candidates, key=lambda item: _text_quality_score(item[1]))
    notes.append(f"Image OCR recovered text using {method}.")
    review_payload = _merge_review_payloads(
        {
            "document_hint": document_hint,
            "attempted_variants": attempted_variants,
            "embedded_extension": extension_hint,
        },
        rapid_overlay,
        method_review,
        {"best_method": method},
    )
    return _clean_text(text), method, notes, review_payload


def _extract_image_with_rapidocr(
    rapid_ocr,
    image,
    *,
    origin: str,
    page_number: int,
    variant_name: str,
    rotation: int = 0,
) -> tuple[str, dict]:
    try:
        result, _ = rapid_ocr(image)
    except Exception:
        return "", {}
    regions: list[dict] = []
    grouped: list[tuple[float, list[tuple[float, str]]]] = []
    for item in result or []:
        parsed = _normalize_rapidocr_item(item)
        text = parsed["text"]
        box = parsed["bbox"]
        if not text or not box:
            continue
        top = min(float(point[1]) for point in box)
        left = min(float(point[0]) for point in box)
        confidence = float(parsed["confidence"] or 0)
        regions.append(
            {
                "text": text[:120],
                "confidence": round(confidence, 2),
                "bbox": [[round(float(point[0]), 1), round(float(point[1]), 1)] for point in box[:4]],
                "origin": origin,
            }
        )
        if grouped and abs(grouped[-1][0] - top) <= 10:
            grouped[-1][1].append((left, text))
        else:
            grouped.append((top, [(left, text)]))
    lines = []
    for _, row in grouped:
        ordered = [text for _, text in sorted(row, key=lambda value: value[0])]
        line = _clean_text(" ".join(ordered))
        if line:
            lines.append(line)
    review_page = {
        "page": int(page_number),
        "width": int(getattr(image, "width", 0) or 0),
        "height": int(getattr(image, "height", 0) or 0),
        "variant": variant_name,
        "rotation": int(rotation or 0),
        "preview": " ".join(lines[:3])[:220],
        "line_count": len(lines),
        "regions": regions[:10],
    }
    return "\n".join(lines), review_page


def _extract_pdf_with_isolated_ocr(raw_bytes: bytes, *, page_limit: int) -> dict:
    if len(raw_bytes) < 2048:
        return {"text": "", "review_payload": {}}
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
            return {"text": "", "review_payload": {}}
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return {"text": "", "review_payload": {}}
        payload = json.loads(lines[-1])
        return {
            "text": _clean_text(str(payload.get("text") or "")),
            "review_payload": {
                "ocr_pages": list(payload.get("pages") or [])[:6],
                "best_method": "isolated_rapidocr_pdf",
                "recovery_steps": [{"step": "isolated_ocr_worker", "status": "completed"}],
            },
        }
    except Exception:
        logger.warning("Isolated OCR extraction failed for document upload.", exc_info=True)
        return {"text": "", "review_payload": {"recovery_steps": [{"step": "isolated_ocr_worker", "status": "failed"}]}}
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


def _finalize_text(text: str, method: str, notes: list[str], review_payload: dict | None = None) -> ExtractedDocumentText:
    cleaned = _clean_text(text)
    confidence = round(min(_text_quality_score(cleaned), 0.97), 2)
    normalized_review = _normalize_review_payload(review_payload, cleaned, method)
    return ExtractedDocumentText(
        text=cleaned[:30000],
        method=method,
        confidence=confidence,
        notes=notes[:8],
        review_payload=normalized_review,
    )


def _normalize_review_payload(review_payload: dict | None, text: str, method: str) -> dict:
    payload = dict(review_payload or {})
    payload.setdefault("best_method", method)
    payload.setdefault("raw_text_excerpt", _build_text_excerpt(text))
    if payload.get("ocr_pages"):
        normalized_pages = []
        for page in list(payload.get("ocr_pages") or [])[:6]:
            normalized_pages.append(
                {
                    "page": int(page.get("page") or len(normalized_pages) + 1),
                    "width": int(page.get("width") or 0),
                    "height": int(page.get("height") or 0),
                    "variant": str(page.get("variant") or ""),
                    "rotation": int(page.get("rotation") or 0),
                    "preview": str(page.get("preview") or "")[:220],
                    "line_count": int(page.get("line_count") or 0),
                    "regions": [
                        {
                            "text": str(region.get("text") or "")[:120],
                            "confidence": round(float(region.get("confidence") or 0), 2),
                            "bbox": [[round(float(point[0]), 1), round(float(point[1]), 1)] for point in list(region.get("bbox") or [])[:4]],
                            "origin": str(region.get("origin") or ""),
                        }
                        for region in list(page.get("regions") or [])[:10]
                    ],
                }
            )
        payload["ocr_pages"] = normalized_pages
    if payload.get("attempts"):
        payload["attempts"] = [
            {
                "method": str(item.get("method") or ""),
                "quality": round(float(item.get("quality") or 0), 2),
                "state": str(item.get("state") or ""),
            }
            for item in list(payload.get("attempts") or [])[:10]
        ]
    if payload.get("attempted_variants"):
        payload["attempted_variants"] = [
            {
                "variant": str(item.get("variant") or ""),
                "rotation": int(item.get("rotation") or 0),
            }
            for item in list(payload.get("attempted_variants") or [])[:8]
        ]
    if payload.get("recovery_steps"):
        payload["recovery_steps"] = [
            {
                "step": str(item.get("step") or ""),
                "status": str(item.get("status") or ""),
                "page_count": int(item.get("page_count") or 0) if item.get("page_count") not in ("", None) else 0,
            }
            for item in list(payload.get("recovery_steps") or [])[:10]
        ]
    field_candidates = _normalize_field_candidates(
        [
            *list(payload.get("field_candidates") or []),
            *_build_field_candidates(text, list(payload.get("ocr_pages") or [])),
        ]
    )
    if field_candidates:
        payload["field_candidates"] = field_candidates
    return {key: value for key, value in payload.items() if value not in ("", None, [], {})}


def _build_text_excerpt(text: str) -> str:
    normalized = " ".join((text or "").split())
    return normalized[:600]


def _build_field_candidates(text: str, ocr_pages: list[dict] | None = None) -> list[dict]:
    candidates: list[dict] = []
    normalized_text = text or ""
    for field_type, field_name, label, regex, confidence in (
        ("amount", "amount", "Amount", MONEY_RE, 0.62),
        ("date", "document_date", "Date", DATE_RE, 0.6),
        ("email", "email", "Email", EMAIL_RE, 0.7),
        ("phone", "phone", "Phone", PHONE_RE, 0.66),
        ("vehicle_number", "vehicle_number", "Vehicle Number", VEHICLE_NUMBER_RE, 0.74),
    ):
        for match in regex.finditer(normalized_text):
            _append_field_candidate(
                candidates,
                field_type=field_type,
                field_name=field_name,
                label=label,
                value=_candidate_value(match.group(0), field_type),
                confidence=confidence,
                source="raw_text",
                context=_candidate_context(normalized_text, match.start(), match.end()),
            )

    for match in REFERENCE_NUMBER_RE.finditer(normalized_text):
        context = _candidate_context(normalized_text, match.start(), match.end())
        label_text = context.lower()
        if "report" in label_text:
            field_type, field_name, label = "report_number", "report_number", "Report Number"
        elif "policy" in label_text:
            field_type, field_name, label = "policy_number", "document_number", "Policy Number"
        elif "invoice" in label_text or "bill" in label_text:
            field_type, field_name, label = "invoice_number", "document_number", "Invoice Number"
        elif "registration" in label_text or "rc" in label_text:
            field_type, field_name, label = "registration_number", "document_number", "Registration Number"
        else:
            field_type, field_name, label = "account_number", "account_number", "Account Number"
        _append_field_candidate(
            candidates,
            field_type=field_type,
            field_name=field_name,
            label=label,
            value=_candidate_value(match.group(1), field_type),
            confidence=0.64,
            source="raw_text_label",
            context=context,
        )

    for page in ocr_pages or []:
        for region in list(page.get("regions") or [])[:16]:
            region_text = str(region.get("text") or "").strip()
            if not region_text:
                continue
            for field_type, field_name, label, regex, base_confidence in (
                ("amount", "amount", "Amount", MONEY_RE, 0.68),
                ("date", "document_date", "Date", DATE_RE, 0.64),
                ("email", "email", "Email", EMAIL_RE, 0.72),
                ("phone", "phone", "Phone", PHONE_RE, 0.68),
                ("vehicle_number", "vehicle_number", "Vehicle Number", VEHICLE_NUMBER_RE, 0.78),
            ):
                for match in regex.finditer(region_text):
                    region_confidence = float(region.get("confidence") or 0)
                    _append_field_candidate(
                        candidates,
                        field_type=field_type,
                        field_name=field_name,
                        label=label,
                        value=_candidate_value(match.group(0), field_type),
                        confidence=max(base_confidence, min(region_confidence, 0.98)),
                        source=region.get("origin") or "ocr_region",
                        context=region_text[:160],
                        page=page.get("page"),
                        bbox=region.get("bbox"),
                    )
            region_confidence = float(region.get("confidence") or 0)
            if 0 < region_confidence < 0.55 and len(region_text) >= 4:
                _append_field_candidate(
                    candidates,
                    field_type="low_confidence_text",
                    field_name="review_note",
                    label="Low Confidence OCR Text",
                    value=region_text[:80],
                    confidence=region_confidence,
                    source=region.get("origin") or "ocr_region",
                    context=region_text[:160],
                    page=page.get("page"),
                    bbox=region.get("bbox"),
                )
    return candidates


def _candidate_value(value: str, field_type: str) -> str:
    normalized = " ".join(str(value or "").split()).strip(" :-#")
    if field_type == "vehicle_number":
        return re.sub(r"[^A-Z0-9]", "", normalized.upper())
    return normalized


def _candidate_context(text: str, start: int, end: int) -> str:
    left = max(start - 70, 0)
    right = min(end + 70, len(text))
    return " ".join(text[left:right].split())[:180]


def _append_field_candidate(candidates: list[dict], **candidate) -> None:
    if candidate.get("value"):
        candidates.append(candidate)


def _normalize_field_candidates(candidates: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    seen = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        value = _candidate_value(str(item.get("value") or ""), str(item.get("field_type") or ""))
        if not value:
            continue
        key = (
            str(item.get("field_type") or ""),
            str(item.get("field_name") or ""),
            value.lower(),
            int(item.get("page") or 0),
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(
            {
                "field_type": str(item.get("field_type") or "unknown")[:40],
                "field_name": str(item.get("field_name") or "")[:60],
                "label": str(item.get("label") or item.get("field_type") or "Candidate")[:80],
                "value": value[:140],
                "confidence": round(float(item.get("confidence") or 0), 2),
                "source": str(item.get("source") or "")[:80],
                "context": str(item.get("context") or "")[:180],
                "page": int(item.get("page") or 0) if item.get("page") not in ("", None) else 0,
                "bbox": [
                    [round(float(point[0]), 1), round(float(point[1]), 1)]
                    for point in list(item.get("bbox") or [])[:4]
                    if isinstance(point, (list, tuple)) and len(point) >= 2
                ],
            }
        )
    normalized.sort(key=lambda item: (item["field_type"] == "low_confidence_text", -item["confidence"], item["field_type"], item["value"]))
    return normalized[:14]


def _merge_review_payloads(*payloads: dict | None) -> dict:
    merged: dict = {}
    list_keys = {"ocr_pages", "attempts", "recovery_steps", "attempted_variants", "field_candidates"}
    for payload in payloads:
        for key, value in (payload or {}).items():
            if value in ("", None, [], {}):
                continue
            if key in list_keys:
                existing = list(merged.get(key) or [])
                existing.extend(list(value or []))
                merged[key] = existing
                continue
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = _merge_review_payloads(merged[key], value)
                continue
            merged[key] = value
    return merged


def _open_image_bytes(raw_bytes: bytes, *, image_module, image_ops):
    image = image_module.open(BytesIO(raw_bytes))
    image.load()
    if image_ops:
        image = image_ops.exif_transpose(image)
    return image


def _prepare_image_variants(image, *, image_ops, image_filter, allow_rotation: bool) -> list[tuple[str, object, dict]]:
    prepared = []
    base = image.convert("RGB") if getattr(image, "mode", "") not in {"RGB", "L"} else image.copy()
    if min(getattr(base, "width", 0) or 0, getattr(base, "height", 0) or 0) and min(base.width, base.height) < 900:
        scale = min(max(900 / max(min(base.width, base.height), 1), 1.0), 2.4)
        base = base.resize((max(int(base.width * scale), 1), max(int(base.height * scale), 1)))
    prepared.append(("original", base, {"rotation": 0}))

    if image_ops:
        gray = image_ops.autocontrast(base.convert("L"))
        prepared.append(("grayscale_autocontrast", gray, {"rotation": 0}))
        threshold = gray.point(lambda value: 255 if value >= 165 else 0, mode="L")
        prepared.append(("threshold", threshold, {"rotation": 0}))
        if image_filter:
            prepared.append(("sharpened", gray.filter(image_filter.SHARPEN), {"rotation": 0}))

    if allow_rotation and base.width > base.height * 1.15:
        for angle in (90, 270):
            prepared.append((f"rotated_{angle}", base.rotate(angle, expand=True), {"rotation": angle}))

    seen = set()
    deduped = []
    for name, variant, metadata in prepared:
        identity = (name, getattr(variant, "width", 0), getattr(variant, "height", 0), int(metadata.get("rotation") or 0))
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append((name, variant, metadata))
    return deduped


def _normalize_rapidocr_item(item) -> dict:
    if not isinstance(item, (list, tuple)) or len(item) < 2:
        return {"text": "", "confidence": 0.0, "bbox": []}
    bbox = list(item[0] or [])
    raw_text = item[1]
    if isinstance(raw_text, (list, tuple)):
        text = raw_text[0] if raw_text else ""
        confidence = raw_text[1] if len(raw_text) > 1 else 0
    else:
        text = raw_text
        confidence = item[2] if len(item) > 2 else 0
    try:
        confidence_value = float(confidence or 0)
    except Exception:
        confidence_value = 0.0
    return {
        "text": _clean_text(str(text or "")),
        "confidence": confidence_value,
        "bbox": bbox,
    }


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
    image_ops = None
    image_filter = None
    try:
        rapid_ocr = import_module("rapidocr_onnxruntime").RapidOCR(no_cls=True)
    except Exception:
        rapid_ocr = None
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            pytesseract = import_module("pytesseract")
            image_module = import_module("PIL.Image")
            image_ops = import_module("PIL.ImageOps")
            image_filter = import_module("PIL.ImageFilter")
            image_file = import_module("PIL.ImageFile")
            image_file.LOAD_TRUNCATED_IMAGES = True
    except Exception:
        pytesseract = None
        image_module = None
        image_ops = None
        image_filter = None
    configured_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if pytesseract and configured_cmd:
        pytesseract.pytesseract.tesseract_cmd = configured_cmd
    return rapid_ocr, pytesseract, image_module, image_ops, image_filter
