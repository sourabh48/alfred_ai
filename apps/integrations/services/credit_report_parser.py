from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from importlib import import_module
from io import BytesIO, StringIO
import os
import re
from typing import BinaryIO

from alfred_ai.services import apply_parser_learning, extract_document_text
from pypdf import PdfReader

try:
    import fitz
except Exception:  # pragma: no cover - optional runtime dependency
    fitz = None

try:
    import pdfplumber
except Exception:  # pragma: no cover - optional runtime dependency
    pdfplumber = None

DATE_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y-%m-%d",
    "%d %b %Y",
    "%d %B %Y",
)

BUREAU_KEYWORDS = {
    "CIBIL": ("CIBIL", "TRANSUNION CIBIL", "TU CIBIL"),
    "EXPERIAN": ("EXPERIAN",),
    "EQUIFAX": ("EQUIFAX",),
    "CRIF": ("CRIF", "CRIF HIGH MARK", "HIGH MARK"),
}

SCORE_PATTERNS = [
    re.compile(r"your\s*(?:credit|cibil|bureau)\s*score\s*(?:is|:)?\s*(?<!\d)([3-9]\d{2})(?!\d)", re.IGNORECASE),
    re.compile(r"(?:credit|cibil|bureau)\s*score[^0-9]{0,40}(?<!\d)([3-9]\d{2})(?!\d)", re.IGNORECASE),
    re.compile(r"\bscore\b[^0-9]{0,20}(?<!\d)([3-9]\d{2})(?!\d)", re.IGNORECASE),
]
MONEY_PATTERN = re.compile(r"(?:INR|RS\.?|₹)\s*([0-9,]+(?:\.\d{1,2})?)", re.IGNORECASE)


TRADE_LINE_START_LABELS = (
    "member name",
    "subscriber name",
    "lender name",
    "lender",
    "institution",
    "bank name",
)


@lru_cache(maxsize=1)
def _ocr_enabled() -> bool:
    pytesseract, _ = _load_ocr_dependencies()
    if not pytesseract or not fitz:
        return False
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


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


@dataclass
class ParsedCreditReport:
    parser_status: str
    confidence: float
    bureau: str
    extracted_text: str
    payload: dict
    factors: list[dict]
    summary: str
    parser_notes: str


class CreditReportParser:
    def parse(self, upload: BinaryIO, filename: str = "", user=None) -> ParsedCreditReport:
        raw_bytes = self._read_bytes(upload)
        effective_name = filename or getattr(upload, "name", "credit_report")
        metadata = self._extract_pdf_metadata(raw_bytes, effective_name)
        extraction = extract_document_text(
            raw_bytes,
            effective_name,
            ocr_page_limit=self._preferred_ocr_page_limit(effective_name, metadata),
        )
        text = extraction.text
        extraction_notes = list(extraction.notes)
        if extraction.method:
            extraction_notes.append(f"Primary extraction path: {extraction.method}.")
        bureau = self._detect_bureau(text, effective_name, metadata)
        payload = self._extract_payload(text)
        if bureau and not payload.get("bureau"):
            payload["bureau"] = bureau
        if metadata.get("title") and not payload.get("document_title"):
            payload["document_title"] = metadata["title"]
        payload["extraction_method"] = extraction.method
        payload["extraction_notes"] = extraction.notes[:6]
        payload["raw_text_excerpt"] = " ".join(text.split())[:600]
        payload["extraction_review"] = extraction.review_payload
        factors = self._build_factors(payload, bureau)

        confidence = max(0.18 if (text.strip() or metadata) else 0.0, extraction.confidence * 0.7 if text.strip() else 0.0)
        if len(text.strip()) >= 300:
            confidence += 0.18
        if len(text.strip()) >= 1200:
            confidence += 0.12
        for key in ("score", "report_date", "report_number", "applicant_name", "bureau"):
            if payload.get(key):
                confidence += 0.1
        for key in ("total_accounts", "active_accounts", "closed_accounts", "delinquent_accounts", "credit_utilization"):
            if payload.get(key) not in ("", None):
                confidence += 0.04
        confidence, learning_notes = apply_parser_learning(
            user=user,
            scope="credit_report",
            filename=effective_name,
            detected_type=bureau or payload.get("bureau") or "credit_report",
            text=text,
            field_names=[key for key, value in payload.items() if value not in ("", None, 0)],
            confidence=confidence,
        )
        confidence = round(max(0.0, min(float(confidence or 0), 0.99)), 2)

        parser_notes = list(extraction_notes)
        if payload.get("score"):
            parser_notes.append(f"Detected score {payload['score']}.")
        if bureau:
            parser_notes.append(f"Detected bureau {bureau}.")
        if not text.strip():
            parser_notes.append("No machine-readable text layer was found in the uploaded report.")
            if not _ocr_enabled():
                parser_notes.append("OCR fallback is not configured on this server, so printed/scanned bureau reports may require review.")
        if confidence < 0.65:
            parser_notes.append("Parsing confidence is low. Review the extracted details before relying on them.")
        parser_notes.extend(learning_notes)

        parser_status = "parsed" if payload.get("score") and bureau and confidence >= 0.65 and text.strip() else (
            "needs_review" if (text.strip() or bureau or metadata) else "failed"
        )

        return ParsedCreditReport(
            parser_status=parser_status,
            confidence=confidence,
            bureau=bureau,
            extracted_text=text[:20000],
            payload=payload,
            factors=factors,
            summary=self._build_summary(payload, bureau, parser_status),
            parser_notes=" ".join(parser_notes).strip(),
        )

    def _read_bytes(self, upload: BinaryIO) -> bytes:
        current = upload.tell() if hasattr(upload, "tell") else None
        if hasattr(upload, "seek"):
            upload.seek(0)
        content = upload.read()
        if current is not None and hasattr(upload, "seek"):
            upload.seek(current)
        return content

    def _extract_pdf_metadata(self, raw_bytes: bytes, filename: str) -> dict:
        if not filename.lower().endswith(".pdf"):
            return {}
        try:
            metadata = PdfReader(BytesIO(raw_bytes)).metadata or {}
        except Exception:
            return {}
        return {
            "title": str(metadata.get("/Title") or "").strip(),
            "author": str(metadata.get("/Author") or "").strip(),
        }

    def _extract_text(self, raw_bytes: bytes, filename: str) -> tuple[str, list[str]]:
        notes: list[str] = []
        extension = os.path.splitext(filename.lower())[1]
        if extension != ".pdf":
            return "", notes

        for extractor in (self._extract_with_pypdf, self._extract_with_pdfplumber, self._extract_with_fitz):
            text = extractor(raw_bytes)
            if text.strip():
                return text, notes

        if fitz and _ocr_enabled():
            ocr_text = self._extract_with_ocr(raw_bytes)
            if ocr_text.strip():
                notes.append("Text was recovered through OCR fallback.")
                return ocr_text, notes

        return "", notes

    def _extract_with_pypdf(self, raw_bytes: bytes) -> str:
        try:
            reader = PdfReader(BytesIO(raw_bytes))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if text.strip():
                return text
            return "\n".join((page.extract_text(extraction_mode="layout") or "") for page in reader.pages)
        except Exception:
            return ""

    def _extract_with_pdfplumber(self, raw_bytes: bytes) -> str:
        if not pdfplumber:
            return ""
        try:
            with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                return "\n".join((page.extract_text() or "") for page in pdf.pages)
        except Exception:
            return ""

    def _extract_with_fitz(self, raw_bytes: bytes) -> str:
        if not fitz:
            return ""
        try:
            document = fitz.open(stream=raw_bytes, filetype="pdf")
            return "\n".join(document.load_page(index).get_text("text") or "" for index in range(document.page_count))
        except Exception:
            return ""

    def _extract_with_ocr(self, raw_bytes: bytes) -> str:
        pytesseract, image_module = _load_ocr_dependencies()
        if not fitz or not pytesseract or not image_module:
            return ""
        try:
            document = fitz.open(stream=raw_bytes, filetype="pdf")
        except Exception:
            return ""
        ocr_parts = []
        for index in range(min(document.page_count, 6)):
            try:
                page = document.load_page(index)
                pix = page.get_pixmap(matrix=fitz.Matrix(2.4, 2.4), alpha=False)
                image = image_module.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_parts.append(pytesseract.image_to_string(image))
            except Exception:
                continue
        return "\n".join(part for part in ocr_parts if part)

    def _detect_bureau(self, text: str, filename: str, metadata: dict) -> str:
        normalized = " ".join(
            filter(
                None,
                [
                    text.upper(),
                    filename.upper(),
                    str(metadata.get("title", "")).upper(),
                    str(metadata.get("author", "")).upper(),
                ],
            )
        )
        for bureau, keywords in BUREAU_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return bureau
        return ""

    def _extract_payload(self, text: str) -> dict:
        score = self._extract_score(text)
        loan_accounts = self._extract_trade_lines(text)
        payload = {
            "bureau": "",
            "score": score,
            "report_date": self._extract_date(text, ["report date", "date generated", "generated on", "date"]),
            "report_number": self._extract_label_value(text, ["report number", "control number", "controlnumber", "reference number", "report no", "report id"]),
            "applicant_name": self._normalize_name(
                self._extract_label_value(text, ["consumer name", "name", "customer name", "applicant name", "member name", "hello"])
            ),
            "total_accounts": self._extract_int(text, ["total accounts", "total trades", "accounts total", "total facilities"]),
            "active_accounts": self._extract_int(text, ["active accounts", "open accounts", "active trades"]),
            "closed_accounts": self._extract_int(text, ["closed accounts", "closed trades", "settled accounts"]),
            "delinquent_accounts": self._extract_int(text, ["delinquent accounts", "overdue accounts", "written off accounts", "suit filed accounts"]),
            "recent_inquiries": self._extract_int(text, ["recent enquiries", "total enquiries", "enquiries", "inquiries"]),
            "total_credit_limit": self._extract_amount(text, ["total credit limit", "credit limit", "sanctioned amount"], allow_generic_fallback=False),
            "total_outstanding_balance": self._extract_amount(text, ["total outstanding", "current balance", "outstanding balance"], allow_generic_fallback=False),
            "credit_utilization": self._extract_percentage(text, ["credit utilization", "utilization", "utilisation"]),
            "loan_accounts": loan_accounts,
            "loan_account_overview": self._loan_account_overview(loan_accounts),
        }
        return payload

    def _extract_trade_lines(self, text: str) -> list[dict]:
        accounts: list[dict] = []
        current: dict | None = None
        lines = [" ".join(line.split()) for line in text.splitlines() if line and line.strip()]

        for line in lines:
            lowered = line.lower()
            if any(label in lowered for label in TRADE_LINE_START_LABELS):
                if current and self._trade_line_has_signal(current):
                    accounts.append(self._finalize_trade_line(current))
                current = {}
            if current is None and any(
                token in lowered
                for token in (
                    "account type",
                    "account number",
                    "current balance",
                    "sanctioned amount",
                    "high credit",
                    "emi amount",
                )
            ):
                current = {}
            if current is None:
                continue
            self._apply_trade_line_line(current, line)

        if current and self._trade_line_has_signal(current):
            accounts.append(self._finalize_trade_line(current))

        deduped: list[dict] = []
        seen: set[tuple] = set()
        for account in accounts:
            key = (
                account.get("lender_name", "").upper(),
                account.get("loan_account_number", "")[-8:],
                account.get("account_type", "").upper(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(account)
        return deduped[:16]

    def _apply_trade_line_line(self, current: dict, line: str) -> None:
        current["lender_name"] = current.get("lender_name") or self._extract_label_value_from_line(
            line,
            ["member name", "subscriber name", "lender name", "lender", "institution", "bank name"],
        )
        current["loan_account_number"] = current.get("loan_account_number") or self._extract_label_value_from_line(
            line,
            ["account number", "loan account number", "account no", "loan a/c", "a/c number"],
        )
        current["account_type"] = current.get("account_type") or self._extract_label_value_from_line(
            line,
            ["account type", "loan type", "facility type"],
        )
        current["ownership"] = current.get("ownership") or self._extract_label_value_from_line(
            line,
            ["ownership", "ownership type", "holder type"],
        )
        current["payment_status"] = current.get("payment_status") or self._extract_label_value_from_line(
            line,
            ["payment status", "asset classification", "dpd", "days past due"],
        )
        current["status"] = current.get("status") or self._extract_label_value_from_line(
            line,
            ["account status", "status"],
        )
        current["opened_on"] = current.get("opened_on") or self._extract_date_from_line(
            line,
            ["date opened", "opened on", "opened date", "disbursed on", "disbursement date"],
        )
        current["closed_on"] = current.get("closed_on") or self._extract_date_from_line(
            line,
            ["date closed", "closed on", "closure date", "date reported closed"],
        )
        current["sanctioned_amount"] = current.get("sanctioned_amount") or self._extract_amount_from_line(
            line,
            ["sanctioned amount", "high credit", "credit limit", "loan amount"],
        )
        current["current_balance"] = current.get("current_balance") or self._extract_amount_from_line(
            line,
            ["current balance", "current outstanding", "outstanding balance", "balance outstanding"],
        )
        current["overdue_amount"] = current.get("overdue_amount") or self._extract_amount_from_line(
            line,
            ["amount overdue", "overdue amount", "past due amount"],
        )
        current["emi_amount"] = current.get("emi_amount") or self._extract_amount_from_line(
            line,
            ["emi amount", "installment amount", "emi"],
        )

    def _trade_line_has_signal(self, current: dict) -> bool:
        return bool(
            current.get("lender_name")
            or current.get("loan_account_number")
            or current.get("account_type")
            or current.get("current_balance")
            or current.get("sanctioned_amount")
        )

    def _finalize_trade_line(self, current: dict) -> dict:
        status = str(current.get("status", "") or "").strip()
        payment_status = str(current.get("payment_status", "") or "").strip()
        closed_on = str(current.get("closed_on", "") or "").strip()
        current_balance = float(current.get("current_balance") or 0)
        lowered = f"{status} {payment_status}".lower()
        if not status:
            if closed_on or "closed" in lowered or "settled" in lowered:
                status = "closed"
            elif current_balance > 0:
                status = "active"
            else:
                status = "unknown"
        return {
            "lender_name": str(current.get("lender_name", "") or "").strip()[:180],
            "loan_account_number": str(current.get("loan_account_number", "") or "").strip()[:64],
            "account_type": str(current.get("account_type", "") or "").strip()[:120],
            "ownership": str(current.get("ownership", "") or "").strip()[:80],
            "status": status[:40],
            "opened_on": str(current.get("opened_on", "") or "").strip(),
            "closed_on": closed_on,
            "sanctioned_amount": round(float(current.get("sanctioned_amount") or 0), 2),
            "current_balance": round(current_balance, 2),
            "overdue_amount": round(float(current.get("overdue_amount") or 0), 2),
            "emi_amount": round(float(current.get("emi_amount") or 0), 2),
            "payment_status": payment_status[:120],
        }

    def _extract_label_value_from_line(self, line: str, labels: list[str]) -> str:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*([A-Z0-9/&.,()' -]{{2,180}})", re.IGNORECASE)
            match = pattern.search(line)
            if match:
                return " ".join(match.group(1).strip(" .:-").split())[:180]
        return ""

    def _extract_amount_from_line(self, line: str, labels: list[str]) -> float:
        for label in labels:
            pattern = re.compile(
                rf"{re.escape(label)}\s*[:#-]?\s*(?:INR|RS\.?|â‚¹)?\s*([0-9,]+(?:\.\d{{1,2}})?)",
                re.IGNORECASE,
            )
            match = pattern.search(line)
            if match:
                return float(match.group(1).replace(",", ""))
        return 0.0

    def _extract_date_from_line(self, line: str, labels: list[str]) -> str:
        for label in labels:
            pattern = re.compile(
                rf"{re.escape(label)}\s*[:#-]?\s*([0-9]{{1,2}}[/-][0-9]{{1,2}}[/-][0-9]{{2,4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}|[0-9]{{1,2}}\s+[A-Za-z]{{3,9}}\s+[0-9]{{4}})",
                re.IGNORECASE,
            )
            match = pattern.search(line)
            if match:
                return self._parse_date(match.group(1))
        return ""

    def _loan_account_overview(self, accounts: list[dict]) -> dict:
        return {
            "tracked_accounts": len(accounts),
            "active_accounts": sum(1 for item in accounts if str(item.get("status", "")).lower() == "active"),
            "closed_accounts": sum(1 for item in accounts if str(item.get("status", "")).lower() == "closed"),
            "total_sanctioned_amount": round(sum(float(item.get("sanctioned_amount") or 0) for item in accounts), 2),
            "total_current_balance": round(sum(float(item.get("current_balance") or 0) for item in accounts), 2),
        }

    def _extract_score(self, text: str) -> int:
        for pattern in SCORE_PATTERNS:
            matches = [int(value) for value in pattern.findall(text)]
            matches = [value for value in matches if 300 <= value <= 900]
            prioritized = [value for value in matches if value not in {300, 850, 900}]
            if prioritized:
                return prioritized[0]
            if matches:
                return matches[0]

        for line in text.splitlines():
            lowered = line.lower()
            if "score" not in lowered:
                continue
            numbers = [int(value) for value in re.findall(r"(?<!\d)([3-9]\d{2})(?!\d)", line)]
            if not numbers:
                continue
            prioritized = [value for value in numbers if value not in {300, 850, 900}]
            if prioritized:
                if "your" in lowered:
                    return prioritized[0]
                return prioritized[0]
            return numbers[0]
        return 0

    def _extract_label_value(self, text: str, labels: list[str]) -> str:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*([A-Z0-9/&.,()' -]{{3,120}})", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return " ".join(match.group(1).strip(" .:-").split())[:180]
        return ""

    def _extract_int(self, text: str, labels: list[str]) -> int:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*([0-9]{{1,4}})", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return int(match.group(1))
        return 0

    def _extract_amount(self, text: str, labels: list[str], *, allow_generic_fallback: bool = True) -> float:
        for label in labels:
            pattern = re.compile(
                rf"{re.escape(label)}\s*[:#-]?\s*(?:INR|RS\.?|₹)?\s*([0-9,]+(?:\.\d{{1,2}})?)",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                return float(match.group(1).replace(",", ""))
        if not allow_generic_fallback:
            return 0.0
        generic_match = MONEY_PATTERN.search(text)
        return float(generic_match.group(1).replace(",", "")) if generic_match else 0.0

    def _extract_percentage(self, text: str, labels: list[str]) -> float:
        for label in labels:
            pattern = re.compile(rf"{re.escape(label)}\s*[:#-]?\s*([0-9]{{1,3}}(?:\.\d+)?)\s*%", re.IGNORECASE)
            match = pattern.search(text)
            if match:
                return float(match.group(1))
        return 0.0

    def _extract_date(self, text: str, labels: list[str]) -> str:
        for label in labels:
            pattern = re.compile(
                rf"{re.escape(label)}\s*[:#-]?\s*([0-9]{{1,2}}[/-][0-9]{{1,2}}[/-][0-9]{{2,4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}|[0-9]{{1,2}}\s+[A-Za-z]{{3,9}}\s+[0-9]{{4}})",
                re.IGNORECASE,
            )
            match = pattern.search(text)
            if match:
                return self._parse_date(match.group(1))
        return ""

    def _parse_date(self, value: str) -> str:
        cleaned = " ".join((value or "").strip().split())
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def _preferred_ocr_page_limit(self, filename: str, metadata: dict) -> int:
        normalized = " ".join(
            filter(
                None,
                [
                    filename.upper(),
                    str(metadata.get("title", "")).upper(),
                    str(metadata.get("author", "")).upper(),
                ],
            )
        )
        if any(keyword in normalized for keyword in ("CIBIL", "EXPERIAN", "EQUIFAX", "CRIF", "SCORE REPORT", "CREDIT REPORT")):
            return 2
        return 6

    def _normalize_name(self, value: str) -> str:
        cleaned = re.sub(r"[^A-Z ]+", " ", (value or "").upper()).strip()
        if not cleaned:
            return ""
        compact = cleaned.replace(" ", "")
        if compact and len(compact) % 2 == 0:
            half = len(compact) // 2
            if compact[:half] == compact[half:]:
                return compact[:half]
        return " ".join(cleaned.split())

    def _build_factors(self, payload: dict, bureau: str) -> list[dict]:
        delinquent_accounts = int(payload.get("delinquent_accounts") or 0)
        utilization = float(payload.get("credit_utilization") or 0)
        recent_inquiries = int(payload.get("recent_inquiries") or 0)
        total_accounts = int(payload.get("total_accounts") or 0)
        active_accounts = int(payload.get("active_accounts") or 0)
        closed_accounts = int(payload.get("closed_accounts") or 0)

        payment_score = max(15, 100 - (delinquent_accounts * 28))
        utilization_score = 55 if not utilization else max(10, 100 - min(utilization, 100))
        age_signal = min(active_accounts + closed_accounts, total_accounts) or total_accounts
        age_score = 45 if not age_signal else min(100, 35 + (age_signal * 12))
        mix_score = 40 if not total_accounts else min(100, 40 + (total_accounts * 8))
        inquiry_score = max(20, 100 - (recent_inquiries * 15))

        return [
            self._factor("Payment History", 35, payment_score),
            self._factor("Credit Utilization", 30, utilization_score),
            self._factor("Credit Age", 15, age_score),
            self._factor("Credit Mix", 10, mix_score),
            self._factor("Recent Inquiries", 10, inquiry_score),
        ]

    def _factor(self, name: str, weight: int, score: float) -> dict:
        rounded = round(max(min(score, 100), 0), 1)
        status = "Good" if rounded >= 75 else ("Fair" if rounded >= 55 else "Needs Improvement")
        return {
            "name": name,
            "weight": weight,
            "score": rounded,
            "status": status,
        }

    def _build_summary(self, payload: dict, bureau: str, parser_status: str) -> str:
        score = payload.get("score")
        if score:
            name = payload.get("applicant_name") or "the uploaded applicant"
            bureau_text = bureau or payload.get("bureau") or "bureau"
            report_date = payload.get("report_date") or "unknown report date"
            return (
                f"Uploaded {bureau_text} report for {name} shows score {score} on {report_date}. "
                f"Accounts tracked: {payload.get('total_accounts') or 0}, utilization {payload.get('credit_utilization') or 0}%."
            )[:500]
        if parser_status == "needs_review":
            return "The uploaded credit report looks relevant, but key fields like score or report totals could not be extracted confidently."
        return "The uploaded file could not be parsed into a usable credit-report summary."


credit_report_parser = CreditReportParser()
