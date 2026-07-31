from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from importlib import import_module
from io import BytesIO, StringIO
import logging
import os
import re
from typing import BinaryIO

from alfred_ai.services import apply_parser_learning, extract_document_text
import pdfplumber
from pypdf import PdfReader

DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
)

VEHICLE_NUMBER_RE = re.compile(r"\b([A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4}|\d{2}BH\d{4}[A-Z]{2})\b")
CURRENCY_TOKEN_RE = r"(?:INR|RS\.?|\u20b9|â‚¹)"
MONEY_RE = re.compile(rf"{CURRENCY_TOKEN_RE}\s*([0-9,]+(?:\.\d{{1,2}})?)", re.IGNORECASE)
NUMERIC_TOKEN_RE = re.compile(rf"^(?:{CURRENCY_TOKEN_RE}\s*)?([0-9,]+(?:\.\d{{1,2}})?)$", re.IGNORECASE)
TABLE_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9/-]{0,30}$")

DOCUMENT_KEYWORDS = {
    "invoice": ["invoice", "pre-invoice", "service bill", "job card", "work order", "labour", "gst invoice", "work note"],
    "insurance": ["insurance", "policy no", "policy number", "insured declared value", "third party"],
    "puc": ["pollution under control", "pucc", "emission", "pollution certificate"],
    "registration": ["certificate of registration", "registration certificate", "registering authority", "owner serial"],
    "license": ["driving licence", "driving license"],
}

KNOWN_LABELS = {
    "customer name",
    "service consultant",
    "address",
    "model code",
    "registration number",
    "job card number",
    "job card no",
    "model name",
    "job card date",
    "invoice date",
    "odometer reading",
    "service centre",
    "service center",
    "engine number",
    "supplier gstin",
    "recipient gstin",
    "chassis number",
    "customer voice",
    "contact number",
    "mobile",
    "email",
    "website",
    "total amount",
    "total customer amount",
    "parts description",
    "labour description",
    "terms and condition",
    "customer signature and date",
    "authorised signatory",
}

TABLE_HEADER_LABELS = {
    "code",
    "description",
    "qty",
    "price",
    "discount",
    "amount",
    "cgst sgst",
    "cgst",
    "sgst",
    "igst",
    "customer amount",
    "hrs",
}

logger = logging.getLogger(__name__)


def _normalize_vehicle_value(value: str) -> str:
    return re.sub(r"[\s-]+", "", (value or "")).upper()


@lru_cache(maxsize=1)
def _load_ocr_dependencies():
    output = StringIO()
    try:
        with redirect_stdout(output), redirect_stderr(output):
            pytesseract = import_module("pytesseract")
            image_module = import_module("PIL.Image")
    except Exception:
        return None, None
    configured_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if configured_cmd:
        pytesseract.pytesseract.tesseract_cmd = configured_cmd
    return pytesseract, image_module


@lru_cache(maxsize=1)
def _ocr_enabled() -> bool:
    pytesseract, _ = _load_ocr_dependencies()
    if not pytesseract:
        return False
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


@dataclass
class ParsedDocument:
    document_type: str
    title: str
    confidence: float
    fields: dict
    parser_status: str
    parser_notes: str
    source_text: str
    service_payload: dict
    review_payload: dict = field(default_factory=dict)


class BikeDocumentAI:
    def parse(self, upload, filename: str = "", user=None) -> ParsedDocument:
        raw_bytes = self._read_bytes(upload)
        name = filename or getattr(upload, "name", "") or "document"
        extraction = extract_document_text(raw_bytes, name)
        text = self._clean_extracted_text(extraction.text or self._extract_text(raw_bytes, name))
        normalized_text = text.upper()

        document_type, confidence = self._guess_document_type(normalized_text, name)
        invoice_fields = self._extract_invoice_fields(text) if document_type == "invoice" else {}
        fields = self._extract_common_fields(text)
        if invoice_fields:
            fields.update(invoice_fields)
        fields.update(self._extract_type_specific_fields(document_type, text, invoice_fields))
        fields = self._drop_empty_values(fields)
        service_payload = self._extract_service_payload(text, invoice_fields) if document_type == "invoice" else {}
        confidence = max(confidence, min(0.78, extraction.confidence * 0.85 if text.strip() else 0))
        confidence, learning_notes = apply_parser_learning(
            user=user,
            scope="vehicle_document",
            filename=name,
            detected_type=document_type,
            text=text,
            field_names=[*fields.keys(), *service_payload.keys()],
            confidence=confidence,
        )

        parser_notes = []
        if not text.strip():
            parser_notes.append("No machine-readable text was extracted from the file.")
        elif extraction.method:
            parser_notes.append(f"Primary extraction path: {extraction.method.replace('_', ' ')}.")
        if fields.get("vehicle_number"):
            parser_notes.append(f"Vehicle number {fields['vehicle_number']} detected.")
        if document_type == "invoice" and service_payload:
            parser_notes.append("Service bill/work note fields were detected and can be imported as a service log.")
            part_count = len(service_payload.get("parts_items") or [])
            labour_count = len(service_payload.get("labour_items") or [])
            if part_count or labour_count:
                parser_notes.append(f"Extracted {part_count} parts line item(s) and {labour_count} labour line item(s).")
            recovered_edge_rows = sum(
                1
                for item in [*(service_payload.get("parts_items") or []), *(service_payload.get("labour_items") or [])]
                if self._is_degraded_invoice_item(item)
            )
            if recovered_edge_rows:
                parser_notes.append(f"Recovered {recovered_edge_rows} invoice line item(s) from degraded OCR rows.")
        elif document_type == "invoice":
            parser_notes.append("Invoice detected, but work-summary extraction is weak. Review the imported log before relying on it.")
        if confidence < 0.65:
            parser_notes.append("Document type confidence is low. Review the extracted details.")
        parser_notes.extend(extraction.notes[:2])
        parser_notes.extend(learning_notes)

        parser_status = "parsed" if text.strip() and confidence >= 0.65 else ("needs_review" if text.strip() else "failed")
        title = self._build_title(document_type, fields, name)

        return ParsedDocument(
            document_type=document_type,
            title=title,
            confidence=round(confidence, 2),
            fields=fields,
            parser_status=parser_status,
            parser_notes=" ".join(parser_notes).strip(),
            source_text=text[:12000],
            service_payload=service_payload,
            review_payload={
                "extraction_method": extraction.method,
                "extraction_notes": extraction.notes[:6],
                "raw_text_excerpt": " ".join(text.split())[:600],
                "extraction_review": extraction.review_payload,
                "invoice_review": self._invoice_review_payload(invoice_fields, service_payload),
            },
        )

    def verify_relevance(self, profile, parsed: ParsedDocument, override_type: str = "") -> dict:
        reasons = []
        related = True
        score = parsed.confidence
        normalized_source = parsed.source_text.lower()
        normalized_profile_number = _normalize_vehicle_value(getattr(profile, "vehicle_number", ""))
        normalized_doc_number = _normalize_vehicle_value(parsed.fields.get("vehicle_number", ""))
        effective_type = override_type or parsed.document_type

        if not parsed.source_text.strip():
            return {"accepted": False, "score": 0, "reasons": ["No readable text was extracted from the file."]}

        if effective_type == "other" and parsed.confidence < 0.58:
            related = False
            reasons.append("The uploaded file does not look like a vehicle document or service note.")

        if normalized_profile_number and normalized_doc_number and normalized_profile_number != normalized_doc_number:
            related = False
            reasons.append("Vehicle number in the document does not match the selected vehicle profile.")
        elif normalized_doc_number:
            score += 0.18
            reasons.append("Vehicle number matched the uploaded document.")

        searchable_tokens = [
            getattr(profile, "make", ""),
            getattr(profile, "model_name", ""),
            getattr(profile, "display_name", ""),
            getattr(profile, "vehicle_type", ""),
        ]
        if any(token and token.lower() in normalized_source for token in searchable_tokens):
            score += 0.1
            reasons.append("Vehicle make/model cues were found in the document text.")

        if effective_type == "invoice" and not parsed.service_payload:
            score -= 0.18
            reasons.append("The file looks like an invoice, but service details were weak.")

        if effective_type in {"insurance", "puc", "registration"} and not parsed.fields.get("document_number"):
            score -= 0.12
            reasons.append("Key document number was not extracted.")

        return {"accepted": related and score >= 0.5, "score": round(max(min(score, 1.0), 0), 2), "reasons": reasons}

    def _read_bytes(self, upload: BinaryIO) -> bytes:
        current = upload.tell() if hasattr(upload, "tell") else None
        if hasattr(upload, "seek"):
            upload.seek(0)
        content = upload.read()
        if current is not None and hasattr(upload, "seek"):
            upload.seek(current)
        return content

    def _extract_text(self, raw_bytes: bytes, filename: str) -> str:
        extension = os.path.splitext(filename.lower())[1]
        if extension == ".pdf":
            text = self._extract_pdf_text(raw_bytes)
            if text.strip():
                return text
        pytesseract, image_module = _load_ocr_dependencies()
        if extension in {".png", ".jpg", ".jpeg", ".webp"} and _ocr_enabled() and pytesseract and image_module:
            try:
                image = image_module.open(BytesIO(raw_bytes))
                return pytesseract.image_to_string(image)
            except Exception:
                logger.warning("Vehicle document OCR extraction failed for image upload.", exc_info=True)
                return ""
        return ""

    def _clean_extracted_text(self, text: str) -> str:
        return (text or "").replace("\ufeff", "").replace("\xa0", " ").replace("â‚¹", "\u20b9").strip()

    def _extract_pdf_text(self, raw_bytes: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(raw_bytes))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text
        except Exception:
            logger.warning("Vehicle document PDF extraction via pypdf failed.", exc_info=True)

        text_chunks = []
        try:
            with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                for page in pdf.pages:
                    text_chunks.append(page.extract_text() or "")
        except Exception:
            logger.warning("Vehicle document PDF extraction via pdfplumber failed.", exc_info=True)

        if "".join(text_chunks).strip():
            return "\n".join(text_chunks)
        return ""

    def _guess_document_type(self, text: str, filename: str) -> tuple[str, float]:
        filename_normalized = filename.lower()
        scores = {}
        for document_type, keywords in DOCUMENT_KEYWORDS.items():
            score = 0.0
            for keyword in keywords:
                if keyword.upper() in text:
                    score += 0.22
                if keyword in filename_normalized:
                    score += 0.18
            if document_type == "invoice" and re.search(r"(invoice no|job card no|job card number|service cent(?:er|re)|grand total|total customer amount|pre-invoice)", text, re.IGNORECASE):
                score += 0.24
            if document_type == "insurance" and re.search(r"(policy no|insured declared value|third party)", text, re.IGNORECASE):
                score += 0.24
            if document_type == "puc" and re.search(r"(pucc|pollution under control|emission)", text, re.IGNORECASE):
                score += 0.24
            scores[document_type] = score
        if not scores:
            return "other", 0.0
        document_type = max(scores, key=scores.get)
        confidence = min(scores[document_type], 0.98)
        return (document_type, confidence) if confidence > 0 else ("other", 0.35)

    def _extract_common_fields(self, text: str) -> dict:
        return self._drop_empty_values(
            {
                "vehicle_number": self._find_first(VEHICLE_NUMBER_RE, text),
                "document_number": self._find_by_labels(text, ["policy no", "policy number", "certificate no", "registration no", "registration number", "invoice no", "job card no", "job card number"]),
                "issuer": self._extract_issuer(text),
                "issue_date": self._extract_date_by_labels(text, ["issue date", "invoice date", "job card date", "date of issue", "date"], allow_generic=True),
                "expiry_date": self._extract_date_by_labels(text, ["expiry", "valid upto", "valid till", "policy end date", "policy period"], allow_generic=False),
                "amount": self._extract_amount_by_labels(text, ["total customer amount", "customer payable", "net amount", "grand total", "total amount", "premium", "total"]),
            }
        )

    def _extract_type_specific_fields(self, document_type: str, text: str, invoice_fields: dict | None = None) -> dict:
        fields = {}
        if document_type == "insurance":
            fields["document_number"] = self._find_by_labels(text, ["policy no", "policy number"])
            fields["issuer"] = self._extract_issuer(text)
        elif document_type == "puc":
            fields["document_number"] = self._find_by_labels(text, ["certificate no", "pucc no", "puc no"])
            fields["issuer"] = self._find_by_labels(text, ["testing center", "center name", "issuer"]) or self._extract_issuer(text)
            fields["expiry_date"] = self._extract_date_by_labels(text, ["valid upto", "valid till", "expiry"], allow_generic=False)
        elif document_type == "registration":
            fields["document_number"] = self._find_by_labels(text, ["registration no", "regn. no", "registration number"])
            fields["issuer"] = self._find_by_labels(text, ["registering authority", "rto"]) or self._extract_issuer(text)
        elif document_type == "invoice":
            invoice_fields = invoice_fields or {}
            fields["document_number"] = invoice_fields.get("job_card_number") or self._find_by_labels(text, ["invoice no", "job card no", "job card number", "bill no", "work order"])
            fields["issuer"] = invoice_fields.get("service_center_name") or self._find_by_labels(text, ["service centre", "service center", "dealer", "workshop"]) or self._extract_issuer(text)
            fields["issue_date"] = invoice_fields.get("invoice_date") or invoice_fields.get("job_card_date")
            fields["amount"] = invoice_fields.get("total_customer_amount") or invoice_fields.get("total_amount") or fields.get("amount")
        return self._drop_empty_values(fields)

    def _extract_service_payload(self, text: str, invoice_fields: dict | None = None) -> dict:
        invoice_fields = invoice_fields or self._extract_invoice_fields(text)
        service_date = invoice_fields.get("invoice_date") or invoice_fields.get("job_card_date") or self._extract_date_by_labels(text, ["invoice date", "service date", "job card date", "date"], allow_generic=True)
        total_amount = invoice_fields.get("total_customer_amount") or invoice_fields.get("total_amount") or self._extract_amount_by_labels(text, ["total customer amount", "customer payable", "grand total", "net amount", "total amount", "total"])
        odometer = invoice_fields.get("odometer_km") or self._extract_odometer(text)
        service_center = invoice_fields.get("service_center_name") or self._find_by_labels(text, ["service centre", "service center", "dealer", "workshop"]) or self._extract_issuer(text)
        summary = self._extract_work_summary(text, invoice_fields)
        next_service_date = self._extract_date_by_labels(text, ["next service date", "recommended next service"], allow_generic=False)
        next_service_km = self._extract_next_service_km(text)
        service_type = self._infer_service_type(summary)

        return self._drop_empty_values(
            {
                "service_date": service_date,
                "cost": total_amount,
                "odometer_km": odometer,
                "service_center": service_center,
                "next_service_date": next_service_date,
                "next_service_km": next_service_km,
                "service_type": service_type,
                "extracted_work_summary": summary,
                "customer_name": invoice_fields.get("customer_name", ""),
                "service_consultant": invoice_fields.get("service_consultant", ""),
                "service_advisor_name": invoice_fields.get("service_advisor_name", ""),
                "service_advisor_contact": invoice_fields.get("service_advisor_contact", ""),
                "job_card_number": invoice_fields.get("job_card_number", ""),
                "invoice_kind": invoice_fields.get("invoice_kind", ""),
                "parts_items": invoice_fields.get("parts_items", []),
                "labour_items": invoice_fields.get("labour_items", []),
                "customer_voice_items": invoice_fields.get("customer_voice_items", []),
                "customer_voice_summary": invoice_fields.get("customer_voice_summary", ""),
                "replaced_parts": invoice_fields.get("replaced_parts", []),
                "service_operations": invoice_fields.get("service_operations", []),
                "systems_impacted": invoice_fields.get("systems_impacted", []),
                "parts_item_count": invoice_fields.get("parts_item_count") or 0,
                "labour_item_count": invoice_fields.get("labour_item_count") or 0,
                "line_item_count": invoice_fields.get("line_item_count") or 0,
                "parts_total_amount": invoice_fields.get("parts_total_amount") or 0,
                "parts_customer_amount": invoice_fields.get("parts_customer_amount") or 0,
                "labour_total_amount": invoice_fields.get("labour_total_amount") or 0,
                "labour_customer_amount": invoice_fields.get("labour_customer_amount") or 0,
                "parts_tax_total": invoice_fields.get("parts_tax_total") or 0,
                "labour_tax_total": invoice_fields.get("labour_tax_total") or 0,
                "total_tax_amount": invoice_fields.get("total_tax_amount") or 0,
                "parts_taxable_amount": invoice_fields.get("parts_taxable_amount") or 0,
                "labour_taxable_amount": invoice_fields.get("labour_taxable_amount") or 0,
                "total_taxable_amount": invoice_fields.get("total_taxable_amount") or 0,
                "total_amount": invoice_fields.get("total_amount") or 0,
                "total_customer_amount": invoice_fields.get("total_customer_amount") or 0,
            }
        )

    def _build_title(self, document_type: str, fields: dict, filename: str) -> str:
        label = {
            "invoice": "Service Invoice",
            "insurance": "Insurance Policy",
            "puc": "PUC Certificate",
            "registration": "Registration / RC",
            "license": "Driving License",
            "other": "Bike Document",
        }.get(document_type, "Bike Document")
        number = fields.get("document_number")
        return f"{label} {number}".strip() if number else f"{label} | {os.path.basename(filename)}"

    def _extract_issuer(self, text: str) -> str:
        direct = self._find_by_labels(text, ["service centre", "service center", "dealer", "workshop", "insurer", "company", "issuer"])
        if direct:
            return direct
        lines = self._split_lines(text)
        for line in lines[:12]:
            lowered = line.lower()
            if "invoice" in lowered:
                continue
            if len(line) > 4 and any(token in lowered for token in ["insurance", "motors", "automobiles", "service", "dealer", "workshop", "rto", "testing center"]):
                return line[:160]
        return ""

    def _find_first(self, pattern: re.Pattern, text: str) -> str:
        match = pattern.search(text.upper())
        return match.group(1).strip() if match else ""

    def _find_by_labels(self, text: str, labels: list[str]) -> str:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*([A-Z0-9/._ -]{{3,80}})", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return match.group(1).strip(" .:-")
        return self._extract_label_value(self._split_lines(text), labels, max_lines=2)

    def _extract_date_by_labels(self, text: str, labels: list[str], allow_generic: bool = False) -> str:
        for label in labels:
            pattern = re.compile(
                rf"{re.escape(label)}\s*[:#-]?\s*([0-9]{{1,2}}[/-][0-9]{{1,2}}[/-][0-9]{{2,4}}(?:\s+[0-9]{{1,2}}:[0-9]{{2}})?|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}|[0-9]{{1,2}}\s+[A-Za-z]{{3,9}}\s+[0-9]{{4}})",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                parsed = self._parse_date(match.group(1))
                if parsed:
                    return parsed

        value = self._extract_label_value(self._split_lines(text), labels, max_lines=2)
        if value:
            parsed = self._parse_date(value)
            if parsed:
                return parsed

        if allow_generic:
            generic_match = re.search(r"\b([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b", text)
            if generic_match:
                return self._parse_date(generic_match.group(1))
        return ""

    def _parse_date(self, value: str) -> str:
        cleaned = " ".join((value or "").strip().split())
        date_match = re.search(r"([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})", cleaned)
        if date_match:
            cleaned = date_match.group(1)
        cleaned = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", cleaned).strip(" ,:-")
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _extract_amount_by_labels(self, text: str, labels: list[str]) -> float:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*(?:{CURRENCY_TOKEN_RE})?\s*([0-9,]+(?:\.\d{{1,2}})?)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return self._amount_string_to_float(match.group(1))
        value = self._extract_label_value(self._split_lines(text), labels, max_lines=2)
        amount = self._parse_amount_token(value)
        if amount:
            return amount
        generic = MONEY_RE.search(text)
        return self._amount_string_to_float(generic.group(1)) if generic else 0.0

    def _extract_odometer(self, text: str) -> int:
        pattern = re.compile(r"(?:odometer|kms?|km reading)\s*[:#-]?\s*([0-9,]{3,8})", re.IGNORECASE)
        match = pattern.search(text)
        if match:
            return int(match.group(1).replace(",", ""))
        value = self._extract_label_value(self._split_lines(text), ["odometer", "odometer reading", "km reading"], max_lines=1)
        amount = self._parse_amount_token(value)
        return int(amount) if amount else 0

    def _extract_next_service_km(self, text: str) -> int:
        pattern = re.compile(r"(?:next service(?: due)?(?: at)?|recommended next service)\s*[:#-]?\s*([0-9,]{3,8})\s*km", re.IGNORECASE)
        match = pattern.search(text)
        return int(match.group(1).replace(",", "")) if match else 0

    def _extract_work_summary(self, text: str, invoice_fields: dict | None = None) -> str:
        invoice_fields = invoice_fields or {}
        structured_bits = []
        structured_bits.extend(
            entry.get("note", "")
            for entry in (invoice_fields.get("customer_voice_items") or [])
            if entry.get("note")
        )
        structured_bits.extend(
            item.get("description", "")
            for item in (invoice_fields.get("parts_items") or [])
            if item.get("description")
        )
        structured_bits.extend(
            item.get("description", "")
            for item in (invoice_fields.get("labour_items") or [])
            if item.get("description")
        )
        if structured_bits:
            unique_bits = []
            seen = set()
            for bit in structured_bits:
                cleaned = bit.strip(" .")
                if cleaned and cleaned.lower() not in seen:
                    unique_bits.append(cleaned)
                    seen.add(cleaned.lower())
            return " | ".join(unique_bits)[:800]

        interesting = []
        keywords = ["oil", "filter", "brake", "chain", "pad", "coolant", "battery", "spark plug", "tyre", "service", "labour", "wash"]
        for line in text.splitlines():
            compact = " ".join(line.split())
            if not compact:
                continue
            lowered = compact.lower()
            if any(keyword in lowered for keyword in keywords) and len(compact) <= 180:
                interesting.append(compact)
        return " | ".join(dict.fromkeys(interesting))[:800]

    def _infer_service_type(self, summary: str) -> str:
        lowered = (summary or "").lower()
        if any(token in lowered for token in ["scheduled", "paid service", "periodic service", "routine service"]):
            return "routine"
        if "tyre" in lowered or "wheel" in lowered:
            return "tyres"
        if any(token in lowered for token in ["repair", "fault", "replace", "replacement", "brake pad", "cable check"]):
            return "repair"
        if "chain" in lowered or "oil" in lowered:
            return "oil_chain"
        return "routine"

    def _extract_invoice_fields(self, text: str) -> dict:
        lines = self._split_lines(text)
        parts_items, parts_totals = self._extract_invoice_table(lines, "parts")
        labour_items, labour_totals = self._extract_invoice_table(lines, "labour")
        customer_voice_items = self._extract_customer_voice_items(lines)
        advisor_contact, advisor_name = self._extract_customer_voice_contact(lines)
        total_customer_amount = self._extract_amount_by_labels(text, ["total customer amount", "customer payable"])
        total_amount = self._extract_amount_by_labels(text, ["total amount", "grand total", "net amount"])
        service_center_name = self._extract_label_value(lines, ["service centre", "service center", "dealer", "workshop"], max_lines=2)
        job_card_number = self._extract_label_value(lines, ["job card number", "job card no", "invoice no", "bill no"], max_lines=1)
        registration_number = self._extract_label_value(lines, ["registration number", "registration no", "regn. no", "regn no"], max_lines=1)
        invoice_enrichment = self._derive_invoice_enrichment(parts_items, labour_items, customer_voice_items)

        return self._drop_empty_values(
            {
                "document_number": job_card_number,
                "job_card_number": job_card_number,
                "customer_name": self._extract_label_value(lines, ["customer name"], max_lines=1),
                "service_consultant": self._extract_label_value(lines, ["service consultant"], max_lines=1),
                "customer_address": self._extract_label_value(lines, ["address"], max_lines=4, multi_line=True, occurrence="first"),
                "model_code": self._extract_label_value(lines, ["model code"], max_lines=1),
                "registration_number": registration_number,
                "vehicle_number": registration_number,
                "model_name": self._extract_label_value(lines, ["model name"], max_lines=1),
                "job_card_date": self._extract_date_by_labels(text, ["job card date"], allow_generic=False),
                "invoice_date": self._extract_date_by_labels(text, ["invoice date"], allow_generic=False),
                "service_center_name": service_center_name,
                "issuer": service_center_name,
                "engine_number": self._extract_label_value(lines, ["engine number"], max_lines=1),
                "supplier_gstin": self._extract_label_value(lines, ["supplier gstin"], max_lines=1),
                "recipient_gstin": self._extract_label_value(lines, ["recipient gstin"], max_lines=1),
                "chassis_number": self._extract_label_value(lines, ["chassis number"], max_lines=1),
                "invoice_kind": self._detect_invoice_kind(lines),
                "service_center_contact": self._extract_label_value(lines, ["contact number"], max_lines=1, occurrence="last"),
                "service_center_mobile": self._extract_label_value(lines, ["mobile"], max_lines=1, occurrence="last"),
                "service_center_email": self._extract_label_value(lines, ["email"], max_lines=1, occurrence="last"),
                "service_center_website": self._extract_label_value(lines, ["website"], max_lines=1, occurrence="last"),
                "service_center_address": self._clean_address(self._extract_label_value(lines, ["address"], max_lines=8, multi_line=True, occurrence="last")),
                "odometer_km": self._extract_odometer(text),
                "customer_voice_items": customer_voice_items,
                "customer_voice_summary": " | ".join(entry.get("note", "") for entry in customer_voice_items if entry.get("note"))[:500],
                "service_advisor_contact": advisor_contact,
                "service_advisor_name": advisor_name,
                "parts_items": parts_items,
                "labour_items": labour_items,
                "parts_total_amount": parts_totals.get("amount"),
                "parts_customer_amount": parts_totals.get("customer_amount"),
                "labour_total_amount": labour_totals.get("amount"),
                "labour_customer_amount": labour_totals.get("customer_amount"),
                "total_amount": total_amount,
                "total_customer_amount": total_customer_amount or total_amount,
                "amount": total_customer_amount or total_amount,
                **invoice_enrichment,
            }
        )

    def _extract_customer_voice_items(self, lines: list[str]) -> list[dict]:
        start_index = self._find_line_index(lines, ["customer voice"])
        if start_index < 0:
            return []

        stop_markers = {"service pre invoice", "service invoice", "tax invoice", "parts description", "labour description"}
        block = []
        for line in lines[start_index + 1:]:
            normalized = self._normalize_token(line)
            if normalized in stop_markers:
                break
            if line:
                block.append(line)

        entries = []
        previous_was_phone = False
        for line in block:
            cleaned = line.lstrip(". ").strip()
            if not cleaned or re.fullmatch(r"\d{1,2}", cleaned):
                continue
            if re.fullmatch(r"\d{10,}", cleaned):
                previous_was_phone = True
                continue
            numeric_value = self._parse_amount_token(cleaned)
            if numeric_value and entries and "estimated_amount" not in entries[-1]:
                entries[-1]["estimated_amount"] = numeric_value
                previous_was_phone = False
                continue
            if previous_was_phone and re.fullmatch(r"[A-Za-z]{2,30}", cleaned):
                previous_was_phone = False
                continue
            previous_was_phone = False
            entries.append({"note": cleaned})
        return entries

    def _extract_customer_voice_contact(self, lines: list[str]) -> tuple[str, str]:
        start_index = self._find_line_index(lines, ["customer voice"])
        if start_index < 0:
            return "", ""

        stop_markers = {"service pre invoice", "service invoice", "tax invoice", "parts description", "labour description"}
        advisor_contact = ""
        advisor_name = ""
        block = []
        for line in lines[start_index + 1:]:
            normalized = self._normalize_token(line)
            if normalized in stop_markers:
                break
            if line:
                block.append(line)

        for index, line in enumerate(block):
            cleaned = line.strip()
            if re.fullmatch(r"\d{10,}", cleaned):
                advisor_contact = cleaned
                for follow_up in block[index + 1:index + 3]:
                    follow_up_clean = follow_up.strip(" .")
                    if re.fullmatch(r"[A-Za-z][A-Za-z .]{1,40}", follow_up_clean):
                        advisor_name = follow_up_clean
                        break
                break
        return advisor_contact, advisor_name

    def _derive_invoice_enrichment(self, parts_items: list[dict], labour_items: list[dict], customer_voice_items: list[dict]) -> dict:
        part_tax_total = round(sum(self._item_tax_total(item) for item in parts_items), 2)
        labour_tax_total = round(sum(self._item_tax_total(item) for item in labour_items), 2)
        part_taxable_total = round(sum(self._item_taxable_amount(item) for item in parts_items), 2)
        labour_taxable_total = round(sum(self._item_taxable_amount(item) for item in labour_items), 2)
        replaced_parts = [item.get("description", "") for item in parts_items if item.get("description")]
        service_operations = [item.get("description", "") for item in labour_items if item.get("description")]
        systems_impacted = self._extract_systems_impacted(replaced_parts + service_operations + [entry.get("note", "") for entry in customer_voice_items])

        return self._drop_empty_values(
            {
                "parts_item_count": len(parts_items),
                "labour_item_count": len(labour_items),
                "line_item_count": len(parts_items) + len(labour_items),
                "parts_codes": [item.get("code", "") for item in parts_items if item.get("code")],
                "labour_codes": [item.get("code", "") for item in labour_items if item.get("code")],
                "replaced_parts": replaced_parts,
                "service_operations": service_operations,
                "systems_impacted": systems_impacted,
                "parts_tax_total": part_tax_total,
                "labour_tax_total": labour_tax_total,
                "total_tax_amount": round(part_tax_total + labour_tax_total, 2),
                "parts_taxable_amount": part_taxable_total,
                "labour_taxable_amount": labour_taxable_total,
                "total_taxable_amount": round(part_taxable_total + labour_taxable_total, 2),
            }
        )

    def _extract_invoice_table(self, lines: list[str], section: str) -> tuple[list[dict], dict]:
        if section == "parts":
            start_labels = ["parts description", "service pre invoice", "service invoice", "tax invoice"]
            stop_labels = {"labour description"}
        else:
            start_labels = ["labour description"]
            stop_labels = {"total amount", "address", "customer signature and date"}

        start_index = self._find_line_index(lines, start_labels)
        if start_index < 0:
            return [], {}

        index = start_index + 1
        items = []
        totals = {}

        while index < len(lines):
            line = self._clean_line(lines[index])
            normalized = self._normalize_token(line)
            if not line or normalized in TABLE_HEADER_LABELS:
                index += 1
                continue
            if self._is_total_line(line):
                totals = self._extract_table_totals(lines, index)
                break
            if normalized in stop_labels and section == "parts":
                break
            compact_item = self._build_compact_invoice_item(section, line)
            if compact_item:
                items.append(compact_item)
                index += 1
                continue
            if not self._is_code_token(line):
                index += 1
                continue

            code_parts = [line]
            index += 1
            while index < len(lines):
                candidate = self._clean_line(lines[index])
                if not candidate:
                    index += 1
                    continue
                if self._is_code_token(candidate) and (code_parts[-1].endswith(("/", "-")) or len(candidate) <= 6):
                    code_parts.append(candidate)
                    index += 1
                    continue
                break

            description_parts = []
            while index < len(lines):
                candidate = self._clean_line(lines[index])
                normalized_candidate = self._normalize_token(candidate)
                if not candidate:
                    index += 1
                    continue
                if normalized_candidate == "total" or self._looks_numeric_token(candidate) or normalized_candidate in stop_labels:
                    break
                description_parts.append(candidate)
                index += 1

            numeric_values = []
            while index < len(lines):
                candidate = self._clean_line(lines[index])
                normalized_candidate = self._normalize_token(candidate)
                if not candidate:
                    index += 1
                    continue
                if self._is_total_line(candidate) and numeric_values:
                    break
                if self._looks_numeric_token(candidate):
                    numeric_values.append(self._parse_amount_token(candidate))
                    index += 1
                    if len(numeric_values) >= 10:
                        break
                    continue
                if numeric_values and (self._is_code_token(candidate) or normalized_candidate in stop_labels):
                    break
                if not numeric_values:
                    index += 1
                    continue
                break

            item = self._build_invoice_item(section, self._combine_code_parts(code_parts), description_parts, numeric_values)
            if item:
                items.append(item)

        return items, totals

    def _build_compact_invoice_item(self, section: str, line: str) -> dict:
        tokens = [token.strip(" ,;") for token in self._clean_line(line).split() if token.strip(" ,;")]
        if len(tokens) < 4 or not self._is_code_token(tokens[0]):
            return {}

        code = tokens[0]
        description_parts = []
        numeric_values = []
        numeric_started = False
        index = 1
        while index < len(tokens):
            token = tokens[index].strip("()[]")
            if re.fullmatch(CURRENCY_TOKEN_RE, token, re.IGNORECASE) and index + 1 < len(tokens):
                next_token = tokens[index + 1].strip("()[]")
                if self._looks_numeric_token(next_token):
                    token = f"{token} {next_token}"
                    index += 1

            if self._looks_numeric_token(token):
                amount = self._parse_amount_token(token)
                if amount:
                    numeric_values.append(amount)
                    numeric_started = True
            elif numeric_started:
                if re.search(r"[A-Za-z]", token):
                    return {}
            else:
                cleaned = token.strip(":-")
                if cleaned and not self._looks_like_known_label(cleaned):
                    description_parts.append(cleaned)
            index += 1

        if len(numeric_values) < 2 or not description_parts:
            return {}
        item = self._build_invoice_item(section, code, description_parts, numeric_values)
        if item:
            item["parse_mode"] = "compact_ocr_row"
        return item

    def _extract_table_totals(self, lines: list[str], start_index: int) -> dict:
        totals = []
        index = start_index
        while index < len(lines) and len(totals) < 3:
            candidate = self._clean_line(lines[index])
            normalized = self._normalize_token(candidate)
            if not candidate:
                index += 1
                continue
            inline_totals = self._inline_totals_from_line(candidate) if self._is_total_line(candidate) else []
            if inline_totals:
                totals.extend(inline_totals[:3 - len(totals)])
                if len(inline_totals) >= 2:
                    break
                index += 1
                continue
            if normalized in KNOWN_LABELS and normalized != "total":
                break
            amount = self._parse_amount_token(candidate)
            if amount:
                totals.append(round(amount, 2))
            elif totals:
                break
            index += 1
        if not totals:
            return {}
        return self._drop_empty_values({"customer_amount": totals[0], "amount": totals[-1]})

    def _build_invoice_item(self, section: str, code: str, description_parts: list[str], numeric_values: list[float]) -> dict:
        if not code or not description_parts or len(numeric_values) < 2:
            return {}

        first_value = numeric_values[0]
        second_value = numeric_values[1] if len(numeric_values) > 1 else 0.0
        parse_mode = "full"
        if first_value > 20 and 0 < second_value <= 20:
            quantity = second_value
            unit_price = first_value
        else:
            quantity = first_value
            unit_price = second_value

        if len(numeric_values) >= 8:
            return self._drop_empty_values(
                {
                    "section": section,
                    "code": code,
                    "description": " ".join(description_parts).strip(),
                    "quantity": round(quantity, 2) if quantity else 0,
                    "unit_price": round(unit_price, 2) if unit_price else 0,
                    "discount_amount": round(numeric_values[2], 2) if len(numeric_values) > 2 else 0,
                    "tax_rate": round(numeric_values[3], 2) if len(numeric_values) > 3 else 0,
                    "cgst_amount": round(numeric_values[4], 2) if len(numeric_values) > 4 else 0,
                    "sgst_amount": round(numeric_values[5], 2) if len(numeric_values) > 5 else 0,
                    "igst_rate": round(numeric_values[6], 2) if len(numeric_values) > 6 else 0,
                    "igst_amount": round(numeric_values[7], 2) if len(numeric_values) > 7 else 0,
                    "customer_amount": round(numeric_values[8], 2) if len(numeric_values) > 8 else 0,
                    "line_total_amount": round(numeric_values[9], 2) if len(numeric_values) > 9 else round(numeric_values[8], 2) if len(numeric_values) > 8 else 0,
                }
            )

        parse_mode = "edge_recovered"
        customer_amount = round(numeric_values[-1], 2)
        if len(numeric_values) == 2 and first_value > 20:
            quantity = 1
            unit_price = round(first_value, 2)
        elif len(numeric_values) == 2 and first_value <= 20:
            unit_price = round(customer_amount / quantity, 2) if quantity else 0
        elif len(numeric_values) >= 3:
            unit_price = round(second_value, 2) if second_value else unit_price

        return self._drop_empty_values(
            {
                "section": section,
                "code": code,
                "description": " ".join(description_parts).strip(),
                "quantity": round(quantity, 2) if quantity else 0,
                "unit_price": round(unit_price, 2) if unit_price else 0,
                "customer_amount": customer_amount,
                "line_total_amount": customer_amount,
                "parse_mode": parse_mode,
            }
        )

    def _extract_label_value(
        self,
        lines: list[str],
        labels: list[str],
        max_lines: int = 1,
        multi_line: bool = False,
        occurrence: str = "first",
    ) -> str:
        matches = []
        ordered_labels = sorted(labels, key=len, reverse=True)
        normalized_labels = [self._normalize_token(label) for label in ordered_labels]

        for index, raw_line in enumerate(lines):
            line = self._clean_line(raw_line)
            normalized_line = self._normalize_token(line.rstrip(":"))
            for label, normalized_label in zip(ordered_labels, normalized_labels):
                direct_match = re.match(rf"^{re.escape(label)}\s*[:#-]?\s*(.+)$", line, re.IGNORECASE)
                if direct_match:
                    remainder = direct_match.group(1).strip(" :-")
                    if remainder:
                        matches.append(remainder)
                        break
                if normalized_line == normalized_label:
                    values = []
                    pointer = index + 1
                    while pointer < len(lines) and len(values) < max_lines:
                        candidate = self._clean_line(lines[pointer])
                        pointer += 1
                        if not candidate or candidate == ":":
                            continue
                        if self._looks_like_known_label(candidate):
                            break
                        values.append(candidate)
                        if not multi_line:
                            break
                    if values:
                        matches.append(" ".join(values).strip())
                    break
        if not matches:
            return ""
        return matches[-1] if occurrence == "last" else matches[0]

    def _find_line_index(self, lines: list[str], labels: list[str]) -> int:
        normalized_labels = {self._normalize_token(label) for label in labels}
        for index, line in enumerate(lines):
            normalized_line = self._normalize_token(line)
            if normalized_line in normalized_labels:
                return index
            if any(normalized_line.startswith(label) for label in normalized_labels):
                return index
        return -1

    def _is_total_line(self, value: str) -> bool:
        normalized = self._normalize_token(value)
        if normalized in {"total amount", "total customer amount"}:
            return False
        return normalized == "total" or normalized.startswith("total ")

    def _inline_totals_from_line(self, value: str) -> list[float]:
        cleaned = self._clean_line(value)
        if not self._is_total_line(cleaned):
            return []
        tokens = re.findall(rf"(?:{CURRENCY_TOKEN_RE}\s*)?[0-9,]+(?:\.\d{{1,2}})?", cleaned, re.IGNORECASE)
        amounts = []
        for token in tokens:
            amount = self._parse_amount_token(token)
            if amount:
                amounts.append(round(amount, 2))
        return amounts

    def _invoice_review_payload(self, invoice_fields: dict, service_payload: dict) -> dict:
        parts_items = invoice_fields.get("parts_items") or []
        labour_items = invoice_fields.get("labour_items") or []
        degraded_items = [item for item in [*parts_items, *labour_items] if self._is_degraded_invoice_item(item)]
        compact_ocr_rows = sum(1 for item in degraded_items if item.get("parse_mode") == "compact_ocr_row")
        return self._drop_empty_values(
            {
                "parts_item_count": len(parts_items),
                "labour_item_count": len(labour_items),
                "line_item_count": service_payload.get("line_item_count") or invoice_fields.get("line_item_count") or 0,
                "recovered_edge_rows": len(degraded_items),
                "compact_ocr_rows": compact_ocr_rows,
                "invoice_kind": invoice_fields.get("invoice_kind", ""),
                "systems_impacted": invoice_fields.get("systems_impacted") or [],
            }
        )

    def _is_degraded_invoice_item(self, item: dict) -> bool:
        return item.get("parse_mode") in {"edge_recovered", "compact_ocr_row"}

    def _split_lines(self, text: str) -> list[str]:
        return [line for line in (self._clean_line(raw) for raw in (text or "").splitlines()) if line]

    def _clean_line(self, value: str) -> str:
        return " ".join((value or "").replace("\xa0", " ").replace("â‚¹", "\u20b9").split()).strip()

    def _clean_address(self, value: str) -> str:
        cleaned = re.sub(r"\s*,\s*", ", ", (value or "").strip())
        cleaned = re.sub(r"(,\s*){2,}", ", ", cleaned)
        return cleaned.strip(" ,")

    def _normalize_token(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

    def _looks_like_known_label(self, line: str) -> bool:
        normalized = self._normalize_token(line.rstrip(":"))
        return normalized in KNOWN_LABELS or normalized in TABLE_HEADER_LABELS

    def _parse_amount_token(self, value: str) -> float:
        if not value:
            return 0.0
        cleaned = self._clean_line(value)
        direct_match = NUMERIC_TOKEN_RE.match(cleaned)
        if direct_match:
            return self._amount_string_to_float(direct_match.group(1))
        money_match = MONEY_RE.search(cleaned)
        if money_match:
            return self._amount_string_to_float(money_match.group(1))
        return 0.0

    def _looks_numeric_token(self, value: str) -> bool:
        cleaned = self._clean_line(value)
        return bool(NUMERIC_TOKEN_RE.match(cleaned)) and any(char.isdigit() for char in cleaned)

    def _amount_string_to_float(self, value: str) -> float:
        cleaned = re.sub(r"[^0-9.]", "", value or "")
        if not any(char.isdigit() for char in cleaned):
            return 0.0
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _is_code_token(self, value: str) -> bool:
        cleaned = self._clean_line(value)
        if not cleaned or " " in cleaned:
            return False
        return bool(TABLE_CODE_RE.match(cleaned))

    def _combine_code_parts(self, parts: list[str]) -> str:
        if not parts:
            return ""
        combined = parts[0]
        for part in parts[1:]:
            combined = f"{combined}{part}" if combined.endswith(("/", "-")) else f"{combined} {part}"
        return combined

    def _item_tax_total(self, item: dict) -> float:
        return round(
            float(item.get("cgst_amount") or 0)
            + float(item.get("sgst_amount") or 0)
            + float(item.get("igst_amount") or 0),
            2,
        )

    def _item_taxable_amount(self, item: dict) -> float:
        gross = float(item.get("line_total_amount") or item.get("customer_amount") or 0)
        return round(max(gross - self._item_tax_total(item), 0), 2)

    def _extract_systems_impacted(self, texts: list[str]) -> list[str]:
        joined = " ".join(text.lower() for text in texts if text)
        systems = []
        mapping = {
            "engine": ["oil", "filter", "engine", "spark plug"],
            "chain_drive": ["chain", "sprocket"],
            "brakes": ["brake", "pad", "shoe"],
            "consumables": ["consumable", "cleaner", "lube"],
            "periodic_service": ["paid service", "scheduled", "service"],
        }
        for label, keywords in mapping.items():
            if any(keyword in joined for keyword in keywords):
                systems.append(label)
        return systems

    def _detect_invoice_kind(self, lines: list[str]) -> str:
        for line in lines[:80]:
            lowered = line.lower()
            if "pre-invoice" in lowered:
                return "pre_invoice"
            if "tax invoice" in lowered:
                return "tax_invoice"
            if "service invoice" in lowered:
                return "service_invoice"
        return "invoice"

    def _drop_empty_values(self, payload: dict) -> dict:
        return {key: value for key, value in payload.items() if value not in (None, "", [], {})}


bike_document_ai = BikeDocumentAI()
