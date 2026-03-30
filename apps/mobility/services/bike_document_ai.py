from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import os
import re
from typing import BinaryIO

import pdfplumber
from pypdf import PdfReader

try:
    import pytesseract
    from PIL import Image
except Exception:  # pragma: no cover - optional runtime dependency
    pytesseract = None
    Image = None


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
MONEY_RE = re.compile(r"(?:INR|RS\.?|₹)\s*([0-9,]+(?:\.\d{1,2})?)", re.IGNORECASE)

DOCUMENT_KEYWORDS = {
    "invoice": ["invoice", "service bill", "job card", "work order", "labour", "gst invoice", "work note"],
    "insurance": ["insurance", "policy no", "policy number", "insured declared value", "third party"],
    "puc": ["pollution under control", "pucc", "emission", "pollution certificate"],
    "registration": ["certificate of registration", "registration certificate", "registering authority", "owner serial"],
    "license": ["driving licence", "driving license"],
}


def _normalize_vehicle_value(value: str) -> str:
    return re.sub(r"[\s-]+", "", (value or "")).upper()


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


class BikeDocumentAI:
    def parse(self, upload, filename: str = "") -> ParsedDocument:
        raw_bytes = self._read_bytes(upload)
        name = filename or getattr(upload, "name", "") or "document"
        text = self._extract_text(raw_bytes, name)
        normalized_text = text.upper()

        document_type, confidence = self._guess_document_type(normalized_text, name)
        fields = self._extract_common_fields(text)
        fields.update(self._extract_type_specific_fields(document_type, text))
        service_payload = self._extract_service_payload(text) if document_type == "invoice" else {}

        parser_notes = []
        if not text.strip():
            parser_notes.append("No machine-readable text was extracted from the file.")
        if fields.get("vehicle_number"):
            parser_notes.append(f"Vehicle number {fields['vehicle_number']} detected.")
        if document_type == "invoice" and service_payload:
            parser_notes.append("Service bill/work note fields were detected and can be imported as a service log.")
        elif document_type == "invoice":
            parser_notes.append("Invoice detected, but work-summary extraction is weak. Review the imported log before relying on it.")
        if confidence < 0.65:
            parser_notes.append("Document type confidence is low. Review the extracted details.")

        parser_status = "parsed" if text.strip() and confidence >= 0.65 else ("needs_review" if text.strip() else "failed")
        title = self._build_title(document_type, fields, name)

        return ParsedDocument(
            document_type=document_type,
            title=title,
            confidence=round(confidence, 2),
            fields=fields,
            parser_status=parser_status,
            parser_notes=" ".join(parser_notes).strip(),
            source_text=text[:4000],
            service_payload=service_payload,
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
            return {
                "accepted": False,
                "score": 0,
                "reasons": ["No readable text was extracted from the file."],
            }

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

        return {
            "accepted": related and score >= 0.5,
            "score": round(max(min(score, 1.0), 0), 2),
            "reasons": reasons,
        }

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
        if extension in {".png", ".jpg", ".jpeg", ".webp"} and pytesseract and Image:
            try:
                image = Image.open(BytesIO(raw_bytes))
                return pytesseract.image_to_string(image)
            except Exception:
                return ""
        return ""

    def _extract_pdf_text(self, raw_bytes: bytes) -> str:
        text_chunks = []
        try:
            with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                for page in pdf.pages:
                    text_chunks.append(page.extract_text() or "")
        except Exception:
            pass

        if "".join(text_chunks).strip():
            return "\n".join(text_chunks)

        try:
            reader = PdfReader(BytesIO(raw_bytes))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
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
            if document_type == "invoice" and re.search(r"(invoice no|job card no|service center|grand total)", text, re.IGNORECASE):
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
        return {
            "vehicle_number": self._find_first(VEHICLE_NUMBER_RE, text),
            "document_number": self._find_by_labels(text, ["policy no", "policy number", "certificate no", "registration no", "invoice no", "job card no"]),
            "issuer": self._extract_issuer(text),
            "issue_date": self._extract_date_by_labels(text, ["issue date", "invoice date", "date of issue", "date"], allow_generic=True),
            "expiry_date": self._extract_date_by_labels(text, ["expiry", "valid upto", "valid till", "policy end date", "policy period"], allow_generic=False),
            "amount": self._extract_amount_by_labels(text, ["premium", "total", "grand total", "net amount", "customer payable"]),
        }

    def _extract_type_specific_fields(self, document_type: str, text: str) -> dict:
        fields = {}
        if document_type == "insurance":
            fields["document_number"] = fields.get("document_number") or self._find_by_labels(text, ["policy no", "policy number"])
            fields["issuer"] = self._extract_issuer(text)
        elif document_type == "puc":
            fields["document_number"] = self._find_by_labels(text, ["certificate no", "pucc no", "puc no"]) or fields.get("document_number")
            fields["issuer"] = self._find_by_labels(text, ["testing center", "center name", "issuer"]) or self._extract_issuer(text)
            fields["expiry_date"] = self._extract_date_by_labels(text, ["valid upto", "valid till", "expiry"], allow_generic=False) or fields.get("expiry_date")
        elif document_type == "registration":
            fields["document_number"] = self._find_by_labels(text, ["registration no", "regn. no", "registration number"]) or fields.get("document_number")
            fields["issuer"] = self._find_by_labels(text, ["registering authority", "rto"]) or self._extract_issuer(text)
        elif document_type == "invoice":
            fields["document_number"] = self._find_by_labels(text, ["invoice no", "job card no", "bill no", "work order"]) or fields.get("document_number")
            fields["issuer"] = self._find_by_labels(text, ["service center", "dealer", "workshop"]) or self._extract_issuer(text)
        return {key: value for key, value in fields.items() if value not in {None, ""}}

    def _extract_service_payload(self, text: str) -> dict:
        service_date = self._extract_date_by_labels(text, ["invoice date", "service date", "job card date", "date"], allow_generic=True)
        total_amount = self._extract_amount_by_labels(text, ["grand total", "net amount", "customer payable", "total"])
        odometer = self._extract_odometer(text)
        service_center = self._find_by_labels(text, ["service center", "dealer", "workshop"]) or self._extract_issuer(text)
        summary = self._extract_work_summary(text)
        next_service_date = self._extract_date_by_labels(text, ["next service date", "recommended next service"], allow_generic=False)
        next_service_km = self._extract_next_service_km(text)
        service_type = self._infer_service_type(summary)

        payload = {
            "service_date": service_date,
            "cost": total_amount,
            "odometer_km": odometer,
            "service_center": service_center,
            "next_service_date": next_service_date,
            "next_service_km": next_service_km,
            "service_type": service_type,
            "extracted_work_summary": summary,
        }
        return {key: value for key, value in payload.items() if value not in {None, "", 0}}

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
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:6]:
            if len(line) > 4 and any(token in line.lower() for token in ["insurance", "motors", "service", "dealer", "workshop", "rto", "testing center"]):
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
        return ""

    def _extract_date_by_labels(self, text: str, labels: list[str], allow_generic: bool = False) -> str:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*([0-9]{{1,2}}[/-][0-9]{{1,2}}[/-][0-9]{{2,4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}|[0-9]{{1,2}}\s+[A-Za-z]{{3,9}}\s+[0-9]{{4}})", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                parsed = self._parse_date(match.group(1))
                if parsed:
                    return parsed

        if allow_generic:
            generic_match = re.search(r"\b([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b", text)
            if generic_match:
                return self._parse_date(generic_match.group(1))
        return ""

    def _parse_date(self, value: str) -> str:
        cleaned = " ".join((value or "").strip().split())
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _extract_amount_by_labels(self, text: str, labels: list[str]) -> float:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*(?:INR|RS\.?|₹)?\s*([0-9,]+(?:\.\d{{1,2}})?)", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return float(match.group(1).replace(",", ""))
        generic = MONEY_RE.search(text)
        return float(generic.group(1).replace(",", "")) if generic else 0.0

    def _extract_odometer(self, text: str) -> int:
        pattern = re.compile(r"(?:odometer|kms?|km reading)\s*[:#-]?\s*([0-9,]{3,8})", re.IGNORECASE)
        match = pattern.search(text)
        return int(match.group(1).replace(",", "")) if match else 0

    def _extract_next_service_km(self, text: str) -> int:
        pattern = re.compile(r"(?:next service(?: due)?(?: at)?|recommended next service)\s*[:#-]?\s*([0-9,]{3,8})\s*km", re.IGNORECASE)
        match = pattern.search(text)
        return int(match.group(1).replace(",", "")) if match else 0

    def _extract_work_summary(self, text: str) -> str:
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
        if "chain" in lowered or "oil" in lowered:
            return "oil_chain"
        if "tyre" in lowered or "wheel" in lowered:
            return "tyres"
        if any(token in lowered for token in ["repair", "fault", "replace", "replacement"]):
            return "repair"
        return "routine"


bike_document_ai = BikeDocumentAI()
