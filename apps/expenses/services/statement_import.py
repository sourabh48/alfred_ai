from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from importlib import import_module
from io import BytesIO
from io import StringIO
from pathlib import Path
import json
import logging
import os
import re
import subprocess
import sys
import textwrap
import zipfile
from typing import BinaryIO

from pypdf import PdfReader

from alfred_ai.services import apply_parser_learning
from alfred_ai.services.currency import INR_LABEL_TOKEN
from alfred_ai.services.pdf_recovery import rebuild_orphaned_pdf
from alfred_ai.services.ocr_process import ocr_command, hidden_process_options, private_ocr_input
from alfred_ai.services.api_errors import safe_error_details
from alfred_ai.services.upload_limits import (
    check_document_resources, check_text_budget, document_source, read_upload_bytes, upload_deadline,
)


# dd/mm/yy, dd/mm/yyyy, dd-mm-yy and dd-mm-yyyy
DATE_TOKEN = r"\d{2}[/-]\d{2}[/-](?:\d{4}|\d{2})"
# 1,234.56 | -1,234.56 | (1,234.56), optionally followed by a Dr/Cr marker
MONEY_TOKEN = r"(?:-?[0-9][0-9,]*\.\d{2}|\([0-9][0-9,]*\.\d{2}\))(?:\s?(?:Dr|Cr)\.?(?![A-Za-z]))?"
CELL_TOKEN = rf"(?:{MONEY_TOKEN}|-)"
TXN_START_RE = re.compile(rf"^{DATE_TOKEN}\s+")
# One amount column, or separate withdrawal and deposit columns, then the closing balance.
TXN_RE = re.compile(
    rf"^(?P<txn_date>{DATE_TOKEN})\s+"
    r"(?P<body>.+?)\s+"
    rf"(?:(?P<value_date>{DATE_TOKEN})\s+)?"
    rf"(?P<first>{CELL_TOKEN})\s+"
    rf"(?:(?P<second>{CELL_TOKEN})\s+)?"
    rf"(?P<closing>{MONEY_TOKEN})"
    r"(?:\s+(?P<tail>.*))?$",
    re.IGNORECASE,
)
MONEY_MARKER_RE = re.compile(r"\s?(Dr|Cr)\.?$", re.IGNORECASE)
MAX_UNPARSED_ROWS = 200
TABLE_EXTENSIONS = {".csv", ".xlsx"}
TABLE_HEADERS = {
    "date": ("txn date", "transaction date", "tran date", "trans date", "date", "posting date", "value date"),
    "description": ("narration", "description", "particulars", "transaction details", "details", "remarks"),
    "debit": ("withdrawal amt", "withdrawal amount", "withdrawal", "withdrawals", "debit amount", "debit", "dr amount"),
    "credit": ("deposit amt", "deposit amount", "deposit", "deposits", "credit amount", "credit", "cr amount"),
    "amount": ("amount", "transaction amount", "txn amount"),
    "marker": ("dr/cr", "cr/dr", "dr / cr", "debit/credit", "type"),
    "balance": ("closing balance", "balance", "running balance", "available balance"),
    "reference": ("chq./ref.no", "chq/ref no", "ref no./cheque no", "reference no", "reference", "ref no", "cheque no"),
}
NO_TABLE_DETAIL = "No transaction table with date, description and amount columns was found in this file."
TABLE_SUMMARY_WORDS = ("opening balance", "closing balance", "total", "statement summary", "generated on")
CARD_TXN_RE = re.compile(
    r"(?P<txn_date>\d{2}/\d{2}/\d{4})\|\s*\d{2}:\d{2}\s+"
    r"(?P<body>.+?)\s+"
    r"(?P<sign>\+)?(?P<amount>[0-9,]+\.\d{2})(?=\s|$)",
    re.IGNORECASE,
)
PERIOD_RE = re.compile(
    r"(?:Statement(?:\s+of\s+account)?|Stat(?:ement| ent))?\s*From\s*[:\-]?\s*"
    r"(\d{2}[/:\-]\d{2}[/:\-]\d{4})\s*To\s*[:\-]?\s*(\d{2}[/:\-]\d{2}[/:\-]\d{4})",
    re.IGNORECASE,
)
ACCOUNT_NO_RE = re.compile(
    r"(?:Account|Accoust|Accont|Accoent)\s*(?:No|No\.|Number)\s*[:\-]?\s*([0-9A-Z ]{8,})",
    re.IGNORECASE,
)
ACCOUNT_HOLDER_RE = re.compile(r"\b(?:MR|MRS|MS)\s+([A-Z ]{3,80})")
REFERENCE_RE = re.compile(r"\b[A-Z0-9]{10,}\b")
# Document text is untrusted. These never occur in a real name, and ' & / . - all do.
STATEMENT_MARKUP_RE = re.compile(r"[<>\"`\x00-\x1f\x7f]")


def clean_statement_text(value) -> str:
    """Treat metadata carrying markup as unknown; a blank beats a mangled name."""
    text = str(value or "")
    return "" if STATEMENT_MARKUP_RE.search(text) else text


def clean_statement_file_name(value) -> str:
    """Keep an uploaded name recognizable while removing its markup characters."""
    cleaned = STATEMENT_MARKUP_RE.sub("", str(value or "")).strip()
    return cleaned or "statement.pdf"

HEADER_PREFIXES = (
    "Page No",
    "MR ",
    "JOINT HOLDERS",
    "Nomination",
    "Statement of accountFrom",
    "Account Branch",
    "Address",
    "City",
    "State",
    "Phone no.",
    "OD Limit",
    "Currency",
    "Email",
    "Cust ID",
    "Account No",
    "A/C Open Date",
    "Account Status",
    "RTGS/NEFT IFSC",
    "Branch Code",
    "Account Type",
    "HDFC BANK LIMITED",
    "*Closing balance",
    "Contents of this statement",
    "State account branch GSTN",
    "HDFC Bank GSTIN",
    "Registered Office Address",
    "Date Narration",
)

ACCOUNT_HOLDER_STOP_WORDS = {
    "BENGALURU",
    "BANGALORE",
    "KARNATAKA",
    "CITY",
    "STATE",
    "EMAIL",
    "PHONE",
    "ACCOUNT",
    "ADDRESS",
    "BRANCH",
}

PAYMENT_MODE_RULES = [
    ("UPI", "UPI"),
    ("ACH D", "ACH"),
    ("NEFT CR", "NEFT"),
    ("RTGS CR", "RTGS"),
    ("IMPS CR", "IMPS"),
    ("ATM", "ATM"),
    ("POS", "CARD"),
    ("CARD", "CARD"),
]

NOISE_MARKERS = (
    "STATEMENT SUMMARY",
    "Generated On:",
    "Generated By:",
    "This is a computer generated statement",
    "Opening Balance",
)

KNOWN_MERCHANT_RULES = [
    (("SWIGGY",), "Swiggy"),
    (("ZOMATO", "ETERNAL"), "Zomato"),
    (("GOOGLE PLAY", "PLAYSTORE"), "Google Play"),
    (("GOOGLE PAY", "GOOGLEPAY", "GPAY", "G PAY"), "Google Pay"),
    (("NETFLIX",), "Netflix"),
    (("SPOTIFY",), "Spotify"),
    (("YOUTUBE",), "YouTube"),
    (("JIO PREPAID RECHARGE",), "Jio Prepaid Recharge"),
    (("CRED CLUB", "PAYMENT ON CRED", "RAZPCREDCLUB"), "CRED Club"),
    (("ONECARD",), "OneCard"),
    (("AMAZON",), "Amazon"),
    (("FLIPKART",), "Flipkart"),
    (("MYNTRA",), "Myntra"),
    (("SMART BAZAAR",), "Smart Bazaar"),
    (("NOBROKER",), "NoBroker"),
]

MERCHANT_NOISE_PATTERNS = (
    r"\bPAID\s+V\s*IA\s+CRED\b",
    r"\bPAYMENT\s+ON\s+CRED\b",
    r"\bPAY\s+FOR\s+INTENT\b",
    r"\bIN\s+APP\b",
    r"\bREMARKS\b.*$",
    r"\bSTATEMENT\s+SUMMARY\b.*$",
)

CLASSIFICATION_RULES = [
    ("other", "investment", ("GROWW", "ZERODHA", "MUTUAL FUND", "STOCK", "MF ")),
    ("expense", "groceries", ("GROCERY", "SUPERMARKET", "SMART BAZAAR")),
    ("expense", "food", ("CAFE", "BAKERY", "HOTEL", "RESTAURANT", "SWIGGY", "ZOMATO", "FOOD")),
    ("expense", "health", ("DENTAL", "PHARMA", "HOSPITAL", "CLINIC", "MEDICAL")),
    ("expense", "fuel", ("FILLING STATIO", "PETROL", "FUEL", "HPCL", "IOCL", "BPCL", "INDIAN OIL")),
    ("expense", "bills", ("FINANCE CHARGES", "IGST-", "CGST-", "SGST-", "GST-")),
    ("expense", "utilities", ("ELECTRICIT", "RECHARGE", "PAYMENTFORBILLS", "BILL", "WATER", "GAS")),
    ("expense", "subscription", ("GOOGLE PLAY", "PLAYSTORE", "NETFLIX", "SPOTIFY", "PRIME", "YOUTUBE")),
    ("expense", "shopping", ("AMAZON", "MYNTRA", "FLIPKART", "SHOP", "NOBROKER")),
    ("expense", "travel", ("UBER", "OLA", "METRO", "IRCTC", "AUTOMOB")),
    ("other", "credit_card", ("ONECARD", "CRED CLUB", "PAYMENT ON CRED", "RAZPCREDCLUB", "CREDIT CARD")),
    ("other", "transfer", ("GOOGLE PAY", "GOOGLEPAY", "GPAY", "G PAY", "PHONEPE", "PAYTM", "AMAZON PAY")),
]
SUBSCRIPTION_KEYWORDS = ("GOOGLE PLAY", "PLAYSTORE", "NETFLIX", "SPOTIFY", "PRIME", "YOUTUBE", "SUBSCRIPTION", "MEMBERSHIP")
INVESTMENT_KEYWORDS = ("GROWW", "ZERODHA", "MUTUAL FUND", "STOCK", "MF ")
CREDIT_CARD_KEYWORDS = ("ONECARD", "CRED CLUB", "PAYMENT ON CRED", "RAZPCREDCLUB", "CREDIT CARD")
MANDATE_KEYWORDS = ("MANDATEEXECUTE", "AUTOPAY", "AUTO PAY", "EMANDATE", "E-MANDATE", "ENACH")
DIGITAL_WALLET_KEYWORDS = ("GOOGLE PAY", "GOOGLEPAY", "GPAY", "G PAY", "PHONEPE", "PAYTM", "AMAZON PAY")
LOAN_EXCLUSION_KEYWORDS = (
    "GOOGLE PLAY",
    "PLAYSTORE",
    "GOOGLE PAY",
    "GOOGLEPAY",
    "GPAY",
    "G PAY",
    "NETFLIX",
    "SPOTIFY",
    "YOUTUBE",
    "SUBSCRIPTION",
    "MEMBERSHIP",
    "FINANCE CHARGES",
    "IGST-",
    "CGST-",
    "SGST-",
    "GST-",
)
LOAN_KEYWORD_PATTERNS = (
    re.compile(r"\bBAJAJ(?:\s+HOUSING)?\b"),
    re.compile(r"\bPOONAWALLA\b"),
    re.compile(r"\bEMI\b"),
    re.compile(r"\bLOAN(?:\s+PAYMENT|\s+ACCOUNT|\s+A/C|\s+INSTAL(?:L)?MENT)?\b"),
    re.compile(r"\bH404HHL[0-9A-Z]*\b"),
    re.compile(r"\bHOUSING\s+FINANC(?:E|)\b"),
    re.compile(r"\bFINCORP\b"),
    re.compile(r"\bFINANCE\b"),
    re.compile(r"\bHOME\s+LOAN\b"),
    re.compile(r"\bHOUSING\s+LOAN\b"),
    re.compile(r"\bPERSONAL\s+LOAN\b"),
    re.compile(r"\bCAR\s+LOAN\b"),
    re.compile(r"\bAUTO\s+LOAN\b"),
    re.compile(r"\bVEHICLE\s+LOAN\b"),
    re.compile(r"\bEDUCATION\s+LOAN\b"),
    re.compile(r"\bSTUDENT\s+LOAN\b"),
    re.compile(r"\bPLA\d+\b"),
)
BANK_NAME_RULES = [
    ("HDFC BANK", "HDFC Bank"),
    ("ICICI BANK", "ICICI Bank"),
    ("STATE BANK OF INDIA", "State Bank of India"),
    ("AXIS BANK", "Axis Bank"),
    ("KOTAK", "Kotak Mahindra Bank"),
]
STATEMENT_KIND_RULES = [
    ("credit_card_statement", ("CREDIT CARD", "CARD STATEMENT", "TOTAL AMOUNT DUE", "MINIMUM AMOUNT DUE", "PAYMENT DUE DATE")),
    ("loan_statement", ("LOAN STATEMENT", "REPAYMENT SCHEDULE", "SANCTION LETTER", "DISBURSEMENT", "EMI AMOUNT", "AMORTIZATION")),
    ("investment_statement", ("PORTFOLIO", "HOLDINGS STATEMENT", "MUTUAL FUND", "DEMAT", "BROKERAGE", "CONTRACT NOTE")),
]
LOAN_TYPE_HINT_RULES = [
    ("home", ("HOME LOAN", "HOUSING LOAN", "HHL")),
    ("personal", ("PERSONAL LOAN", "PL ")),
    ("car", ("CAR LOAN", "AUTO LOAN", "VEHICLE LOAN")),
    ("education", ("EDUCATION LOAN", "STUDENT LOAN")),
    ("business", ("BUSINESS LOAN",)),
    ("credit_card", ("CREDIT CARD",)),
]

STATEMENT_OCR_PAGE_LIMIT = max(1, int(os.getenv("STATEMENT_OCR_PAGE_LIMIT", "6")))
STATEMENT_OCR_PREVIEW_PAGES = max(2, int(os.getenv("STATEMENT_OCR_PREVIEW_PAGES", "2")))
ISOLATED_OCR_TIMEOUT_SECONDS = max(45, int(os.getenv("STATEMENT_ISOLATED_OCR_TIMEOUT_SECONDS", "90")))

ISOLATED_OCR_WORKER = textwrap.dedent(
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
        for _, cells in grouped:
            ordered = [text for _, text in sorted(cells, key=lambda entry: entry[0])]
            line = normalize(" ".join(ordered))
            if line:
                lines.append(line)
        return lines

    pdf_path = sys.argv[1]
    page_limit = max(int(sys.argv[2]), 1)
    ocr = RapidOCR(no_cls=True, det_limit_side_len=768, max_side_len=1920)
    document = fitz.open(pdf_path)
    pages = []
    try:
        for index in range(min(document.page_count, page_limit)):
            page = document.load_page(index)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            image = Image.open(BytesIO(pix.tobytes("png")))
            if index > 0:
                crop_top = int(image.height * 0.14)
                image = image.crop((0, crop_top, image.width, image.height))
            result, _ = ocr(image)
            lines = group_rows(result)
            if lines:
                pages.append("\\n".join(lines))
    finally:
        document.close()
    print(json.dumps({"text": "\\n".join(part for part in pages if part).strip()}, ensure_ascii=False))
    """
)

logger = logging.getLogger(__name__)


@dataclass
class ParsedTransaction:
    transaction_date: date
    amount: Decimal
    closing_balance: Decimal | None
    direction: str
    classification: str
    category: str
    payment_mode: str
    merchant: str
    description: str
    raw_description: str
    external_reference: str
    counterparty: str
    company_name: str


@dataclass
class StatementParseResult:
    bank_name: str
    account_holder: str
    account_number: str
    statement_start: date | None
    statement_end: date | None
    transactions: list[ParsedTransaction]
    statement_kind: str
    parser_status: str
    confidence: float
    source_text: str
    loan_hints: dict
    parser_notes: str = ""
    preview_only: bool = False
    processed_page_count: int = 0
    total_page_count: int = 0
    preview_transaction_count: int = 0
    # Rows that look like transactions but could not be read; never silently dropped.
    unparsed_rows: list = field(default_factory=list)


@dataclass
class StatementTextExtraction:
    text: str
    notes: list[str]
    preview_only: bool
    processed_page_count: int = 0
    total_page_count: int = 0


def parse_bank_statement(file_obj: BinaryIO, user=None, *, ocr_page_limit: int | None = None, preview_page_limit: int | None = None, enable_isolated_ocr: bool = True) -> StatementParseResult:
    table_rows = _read_statement_table(file_obj)
    if table_rows is not None:
        extraction = StatementTextExtraction(
            text="\n".join(" ".join(str(cell or "").strip() for cell in row) for row in table_rows).strip(),
            notes=["Read the uploaded spreadsheet statement."], preview_only=False)
    else:
        raw_bytes = _read_file_bytes(file_obj)
        extraction = _extract_statement_text(
            raw_bytes,
            ocr_page_limit=ocr_page_limit or STATEMENT_OCR_PAGE_LIMIT,
            preview_page_limit=preview_page_limit or STATEMENT_OCR_PREVIEW_PAGES,
            enable_isolated_ocr=enable_isolated_ocr,
        )
    full_text = extraction.text
    check_text_budget(full_text)
    extraction_notes = list(extraction.notes)
    preview_only = extraction.preview_only

    bank_name = _extract_bank_name(full_text)
    account_holder = _extract_account_holder(full_text)
    account_number = _extract_account_number(full_text)
    statement_start, statement_end = _extract_statement_period(full_text)
    statement_kind = _detect_statement_kind(full_text)
    loan_hints = _extract_loan_hints(full_text)

    transactions: list[ParsedTransaction] = []
    unparsed_rows: list[dict] = []
    if table_rows is not None:
        transactions, unparsed_rows = _parse_table_rows(table_rows)
    else:
        column_directions = _statement_column_directions(full_text)
        previous_closing: Decimal | None = None
        for group in _collect_transaction_groups(full_text.splitlines()):
            transaction, reason = _parse_transaction_group(group, previous_closing, column_directions)
            if transaction is None:
                _note_unparsed(unparsed_rows, group, reason)
                continue
            transactions.append(transaction)
            previous_closing = transaction.closing_balance
    if unparsed_rows:
        extraction_notes.append(f"{len(unparsed_rows)} row(s) could not be read and were not imported; they are listed for review.")
    if statement_kind == "credit_card_statement":
        seen = {(item.transaction_date, item.raw_description, item.amount, item.direction) for item in transactions}
        for transaction in _parse_credit_card_transactions(full_text.splitlines()):
            key = (transaction.transaction_date, transaction.raw_description, transaction.amount, transaction.direction)
            if key in seen:
                continue
            transactions.append(transaction)
            seen.add(key)

    preview_transaction_count = len(transactions) if preview_only else 0
    if preview_only:
        if preview_transaction_count:
            extraction_notes.append(
                f"OCR preview recovered {preview_transaction_count} transaction row(s) from the first "
                f"{max(extraction.processed_page_count, 1)} repaired page(s); Alfred imported this partial slice "
                f"while deeper parsing remains queued for the remaining "
                f"{max(extraction.total_page_count - extraction.processed_page_count, 0)} page(s)."
            )
        elif extraction.total_page_count > extraction.processed_page_count:
            extraction_notes.append(
                f"OCR preview recovered header data from the first {max(extraction.processed_page_count, 1)} repaired page(s); "
                "full transaction extraction still needs a deeper retry or a cleaner bank-export PDF."
            )

    confidence = 0.08 if not full_text.strip() else 0.45
    if full_text.strip():
        confidence += 0.15
    if bank_name:
        confidence += 0.1
    if account_number:
        confidence += 0.1
    if transactions:
        confidence += 0.25
    elif statement_kind != "other_statement":
        confidence += 0.05
    if preview_only and preview_transaction_count:
        confidence = min(max(confidence, 0.56), 0.68)
    elif preview_only or any("OCR preview" in note or "first page" in note for note in extraction_notes):
        confidence = min(confidence, 0.62)
    confidence, _ = apply_parser_learning(
        user=user,
        scope="statement_document",
        filename=getattr(file_obj, "name", "statement.pdf"),
        detected_type=statement_kind,
        text=full_text,
        field_names=["bank_name", "account_holder", "account_number", "statement_start", "statement_end"] + ([item.category for item in transactions[:6]] if transactions else []),
        confidence=confidence,
    )
    confidence = round(max(0.0, min(float(confidence or 0), 0.99)), 2)
    parser_status = "parsed" if transactions and not preview_only else ("needs_review" if full_text.strip() else "failed")

    return StatementParseResult(
        bank_name=bank_name,
        account_holder=account_holder,
        account_number=account_number,
        statement_start=statement_start,
        statement_end=statement_end,
        transactions=transactions,
        statement_kind=statement_kind,
        parser_status=parser_status,
        confidence=confidence,
        source_text=full_text[:20000],
        loan_hints=loan_hints,
        parser_notes=" ".join(extraction_notes[:5]).strip(),
        preview_only=preview_only,
        processed_page_count=extraction.processed_page_count,
        total_page_count=extraction.total_page_count,
        preview_transaction_count=preview_transaction_count,
        unparsed_rows=unparsed_rows,
    )


def _note_unparsed(unparsed_rows: list[dict], text: str, reason: str) -> None:
    if len(unparsed_rows) < MAX_UNPARSED_ROWS:
        unparsed_rows.append({"text": _normalize_space(str(text))[:300], "reason": reason})


def _parse_statement_date(token: str) -> date:
    separator = "/" if "/" in token else "-"
    year = "%Y" if len(token.rsplit(separator, 1)[-1]) == 4 else "%y"
    try:
        return datetime.strptime(token, f"%d{separator}%m{separator}{year}").date()
    except ValueError:
        raise ValueError(f"'{token}' is not a valid date")


def _money_cell(token) -> tuple[Decimal | None, str | None]:
    """Signed amount and its Dr/Cr marker; a blank or '-' cell is empty, not zero."""
    text = str(token or "").strip()
    for symbol in ("\u20b9", "INR", "Rs.", "Rs"):
        text = text.replace(symbol, "")
    text = text.strip()
    if text in {"", "-"}:
        return None, None
    marker = None
    found = MONEY_MARKER_RE.search(text)
    if found:
        marker = found.group(1).lower()
        text = text[:found.start()].strip()
    negative = text.startswith("-") or (text.startswith("(") and text.endswith(")"))
    try:
        value = Decimal(text.strip("-()").replace(",", "").strip())
    except InvalidOperation:
        raise ValueError(f"'{token}' is not an amount")
    if not value.is_finite():
        raise ValueError(f"'{token}' is not an amount")
    return (-value if negative else value), marker


def _signed_balance(token) -> Decimal | None:
    value, marker = _money_cell(token)
    if value is None:
        return None
    # A balance marked Dr is overdrawn.
    return -abs(value) if marker == "dr" else (abs(value) if marker == "cr" else value)


def _amount_and_direction(first, second, closing, previous_closing, explicit_direction=None):
    """Read one amount column, or separate withdrawal/deposit columns, into (amount, direction or None)."""
    first_value, first_marker = _money_cell(first)
    if second is not None:
        second_value, _ = _money_cell(second)
        debit, credit = abs(first_value or 0), abs(second_value or 0)
        if debit and credit:
            raise ValueError("Both withdrawal and deposit columns have amounts")
        if not debit and not credit:
            raise ValueError("No amount in the withdrawal or deposit column")
        amount, direction = (debit, "debit") if debit else (credit, "credit")
        # The printed balance outranks a guess about which column a '-' filled.
        if previous_closing is not None and closing is not None and abs(closing - previous_closing) == amount:
            direction = "credit" if closing > previous_closing else "debit"
        return amount, direction
    if first_value is None or first_value == 0:
        raise ValueError("No amount")
    direction = explicit_direction
    if direction is None and first_marker:
        direction = "debit" if first_marker == "dr" else "credit"
    if direction is None and first_value < 0:
        direction = "debit"
    return abs(first_value), direction


def _read_statement_table(file_obj) -> list[list] | None:
    """Rows of a CSV or XLSX statement, or None for a PDF."""
    extension = os.path.splitext(str(getattr(file_obj, "name", "") or "").lower())[1]
    if extension not in TABLE_EXTENSIONS:
        return None
    # shortcut: the stdlib spreadsheet readers live in the fund look-through service; move them to a shared module if a third caller appears.
    from apps.investments.services.fund_look_through import LookThroughError, _csv_rows, _xlsx_sheets
    from alfred_ai.services.upload_limits import UploadFormatError, UploadLimitExceeded

    raw = read_upload_bytes(file_obj)
    try:
        if extension == ".csv":
            rows = _csv_rows(raw)
            if _table_columns(rows) is None:
                raise UploadFormatError(NO_TABLE_DETAIL)
            return rows
        check_document_resources(raw, file_obj.name)
        sheets = _xlsx_sheets(raw)
    except LookThroughError:  # only raised for too many rows
        raise UploadLimitExceeded()
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise UploadFormatError()
    for _, rows in sheets:
        if _table_columns(rows) is not None:
            return rows
    raise UploadFormatError(NO_TABLE_DETAIL)


def _header_label(value) -> str:
    text = _normalize_space(str(value or "")).lower().rstrip(".:").strip()
    return re.sub(r"\s*\((?:inr|rs\.?|\u20b9)\)$", "", text)


def _table_columns(rows) -> tuple[int, dict[str, int]] | None:
    for index, row in enumerate(rows[:50]):
        labels = [_header_label(cell) for cell in row]
        columns: dict[str, int] = {}
        for name, synonyms in TABLE_HEADERS.items():
            for synonym in synonyms:
                position = next((i for i, label in enumerate(labels) if label == synonym and i not in columns.values()), None)
                if position is not None:
                    columns[name] = position
                    break
        if "date" in columns and "description" in columns and ("amount" in columns or {"debit", "credit"} <= columns.keys()):
            return index, columns
    return None


def _table_date(value) -> date | None:
    text = _normalize_space(str(value or ""))
    if not text:
        return None
    if re.fullmatch(DATE_TOKEN, text):
        return _parse_statement_date(text)
    if re.fullmatch(r"\d{4,5}(?:\.0+)?", text):
        # Spreadsheet date serial (1900 date system).
        return date(1899, 12, 30) + timedelta(days=int(float(text)))
    from apps.investments.services.fund_look_through import _date
    found = _date(text)
    if found is None:
        raise ValueError(f"'{text}' is not a date")
    return found


def _parse_table_rows(rows) -> tuple[list[ParsedTransaction], list[dict]]:
    located = _table_columns(rows)
    if located is None:
        return [], []
    header_index, columns = located
    cell = lambda row, name: row[columns[name]] if name in columns and columns[name] < len(row) else None
    transactions: list[ParsedTransaction] = []
    unparsed: list[dict] = []
    previous_closing: Decimal | None = None
    for row in rows[header_index + 1:]:
        if not any(str(value or "").strip() for value in row):
            continue
        text = " | ".join(str(value or "").strip() for value in row)
        try:
            transaction_date = _table_date(cell(row, "date"))
            if transaction_date is None:
                if any(word in text.lower() for word in TABLE_SUMMARY_WORDS):
                    continue
                raise ValueError("No transaction date")
            description = _normalize_space(str(cell(row, "description") or ""))
            reference = _normalize_space(str(cell(row, "reference") or ""))
            closing = _signed_balance(cell(row, "balance"))
            marker = str(cell(row, "marker") or "").strip().lower().rstrip(".")
            explicit = {"dr": "debit", "d": "debit", "debit": "debit", "cr": "credit", "c": "credit", "credit": "credit"}.get(marker)
            if "debit" in columns and "credit" in columns:
                amount, direction = _amount_and_direction(cell(row, "debit") or "-", cell(row, "credit") or "-", closing, previous_closing)
            else:
                amount, direction = _amount_and_direction(cell(row, "amount"), None, closing, previous_closing, explicit)
        except ValueError as error:
            _note_unparsed(unparsed, text, str(error))
            continue
        raw = f"{description} {reference}".strip()
        if direction is None:
            direction = _infer_direction(raw, closing, previous_closing) if closing is not None else _infer_direction(raw, Decimal("0"), None)
        details = classify_transaction_text(raw, direction)
        transactions.append(ParsedTransaction(
            transaction_date=transaction_date, amount=amount, closing_balance=closing,
            direction=details["direction"], classification=details["classification"], category=details["category"],
            payment_mode=details["payment_mode"], merchant=details["merchant"], description=details["description"],
            raw_description=details["raw_description"], external_reference=details["external_reference"],
            counterparty=details["counterparty"], company_name=details["company_name"],
        ))
        if closing is not None:
            previous_closing = closing
    return transactions, unparsed


def summarize_transactions(transactions: list[ParsedTransaction]) -> dict[str, float | int]:
    from apps.expenses.money import expense_money, money_float

    summary = {
        "expense_total": expense_money(0),
        "loan_total": expense_money(0),
        "other_total": expense_money(0),
        "income_total": expense_money(0),
        "transaction_count": len(transactions),
    }

    for item in transactions:
        amount = expense_money(item.amount)
        if item.direction == "credit":
            summary["income_total"] += amount
            continue

        if item.classification == "expense":
            summary["expense_total"] += amount
        elif item.classification == "loan":
            summary["loan_total"] += amount
        else:
            summary["other_total"] += amount

    return {key: value if key == "transaction_count" else money_float(value) for key, value in summary.items()}


def _read_file_bytes(file_obj: BinaryIO) -> bytes:
    raw_bytes = document_source(file_obj)
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    return raw_bytes


def _extract_statement_text(raw_bytes: bytes, *, ocr_page_limit: int, preview_page_limit: int, enable_isolated_ocr: bool) -> StatementTextExtraction:
    if upload_deadline.get() is not None:
        from alfred_ai.services.bounded_parser import run_bounded_parser
        return StatementTextExtraction(**run_bounded_parser("statement", raw_bytes, "statement.pdf",
            ocr_page_limit=ocr_page_limit, preview_page_limit=preview_page_limit))
    if not raw_bytes:
        return StatementTextExtraction(text="", notes=["Uploaded statement file was empty."], preview_only=False)

    extraction_notes: list[str] = []

    try:
        text = _extract_with_pypdf(raw_bytes)
        if text:
            return StatementTextExtraction(text=text, notes=extraction_notes, preview_only=False)
        extraction_notes.append("Primary PDF reader did not extract readable text.")
    except Exception as exc:
        extraction_notes.append(f"Primary PDF reader failed: {exc}")

    try:
        text = _extract_with_fitz(raw_bytes)
        if text:
            extraction_notes.append("Fallback PDF reader recovered readable text.")
            return StatementTextExtraction(text=text, notes=extraction_notes, preview_only=False)
        extraction_notes.append("Fallback PDF reader did not extract readable text.")
    except Exception as exc:
        extraction_notes.append(f"Fallback PDF reader failed: {exc}")

    if enable_isolated_ocr and len(raw_bytes) >= 4096:
        isolated_text = _extract_with_isolated_ocr(raw_bytes, page_limit=preview_page_limit)
        if isolated_text:
            extraction_notes.append("Isolated OCR worker recovered readable text from the original PDF.")
            return StatementTextExtraction(
                text=isolated_text,
                notes=extraction_notes,
                preview_only=True,
                processed_page_count=preview_page_limit,
            )

    repaired = rebuild_orphaned_pdf(raw_bytes)
    if repaired:
        extraction_notes.append(
            f"Recovered a structurally broken PDF by rebuilding its page tree and xref table ({repaired.page_count} page(s))."
        )
        repaired_machine_page_limit = repaired.page_count if repaired.page_count <= ocr_page_limit else min(max(preview_page_limit, 2), repaired.page_count)
        repaired_text = _extract_with_pypdf(repaired.repaired_bytes, page_limit=repaired_machine_page_limit) or _extract_with_fitz(
            repaired.repaired_bytes,
            page_limit=repaired_machine_page_limit,
        )
        if repaired_text:
            extraction_notes.append(
                "Repaired PDF yielded machine-readable text."
                if repaired.page_count <= repaired_machine_page_limit
                else f"Repaired PDF yielded machine-readable preview text from the first {repaired_machine_page_limit} page(s)."
            )
            return StatementTextExtraction(
                text=repaired_text,
                notes=extraction_notes,
                preview_only=repaired.page_count > repaired_machine_page_limit,
                processed_page_count=repaired_machine_page_limit,
                total_page_count=repaired.page_count,
            )

        ocr_page_count = repaired.page_count if repaired.page_count <= ocr_page_limit else min(max(preview_page_limit, 2), repaired.page_count)
        ocr_text = _extract_with_ocr(repaired.repaired_bytes, page_limit=ocr_page_count)
        if not ocr_text and enable_isolated_ocr:
            ocr_text = _extract_with_isolated_ocr(repaired.repaired_bytes, page_limit=ocr_page_count)
            if ocr_text:
                extraction_notes.append("Isolated OCR worker recovered readable text from the repaired PDF.")
        if ocr_text:
            if repaired.page_count <= ocr_page_limit:
                extraction_notes.append(
                    f"OCR recovered statement text from {ocr_page_count} repaired page(s)."
                )
            return StatementTextExtraction(
                text=ocr_text,
                notes=extraction_notes,
                preview_only=repaired.page_count > ocr_page_limit,
                processed_page_count=ocr_page_count,
                total_page_count=repaired.page_count,
            )

    return StatementTextExtraction(text="", notes=extraction_notes, preview_only=False)


def _extract_with_pypdf(raw_bytes: bytes, page_limit: int | None = None) -> str:
    with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
        reader = PdfReader(BytesIO(raw_bytes))
    pages = []
    for page in reader.pages[:page_limit]:
        text = page.extract_text() or ""
        if re.search(r"Withdrawal\s+Amt", text, re.IGNORECASE) and re.search(r"Deposit\s+Amt", text, re.IGNORECASE):
            # Flattening blank cells loses whether the first amount is a deposit.
            # Keep the printed columns when the PDF exposes usable positions.
            try:
                layout = page.extract_text(extraction_mode="layout") or ""
                if _statement_column_directions(layout):
                    text = layout
            except Exception:
                logger.debug("Statement layout extraction unavailable; retaining plain text.", exc_info=True)
        pages.append(text)
    return "\n".join(pages).strip()


def _statement_column_directions(text: str) -> dict[tuple[str, float, float], str | None]:
    """Read explicit withdrawal/deposit cells; ambiguous collisions stay untrusted."""
    directions = {}
    columns = None
    transaction_date = None
    money = re.compile(r"[0-9,]+\.\d{2}")
    for line in text.splitlines():
        headers = [re.search(pattern, line, re.IGNORECASE) for pattern in (
            r"Withdrawal\s+Amt\.?", r"Deposit\s+Amt\.?", r"Closing\s+Balance")]
        if all(headers) and headers[0].start() < headers[1].start() < headers[2].start():
            columns = tuple(header.start() for header in headers)
            transaction_date = None
            continue
        date_match = TXN_START_RE.match(line.strip())
        if date_match:
            transaction_date = date_match.group().strip()
        if not columns or not transaction_date:
            continue
        withdrawal, deposit, closing = columns
        cells = [line[withdrawal:deposit].strip(), line[deposit:closing].strip(), line[closing:].strip()]
        if not money.fullmatch(cells[2]) or any(cell and not money.fullmatch(cell) for cell in cells[:2]):
            continue
        values = [_to_decimal(cell) if cell else Decimal("0") for cell in cells]
        if bool(values[0]) == bool(values[1]):
            continue
        key = (transaction_date, values[0] or values[1], values[2])
        direction = "debit" if values[0] else "credit"
        directions[key] = direction if key not in directions or directions[key] == direction else None
    return directions


def _extract_with_fitz(raw_bytes: bytes, page_limit: int | None = None) -> str:
    fitz = _load_fitz()
    if not fitz:
        return ""
    document = fitz.open(stream=raw_bytes, filetype="pdf")
    try:
        pages = [document.load_page(index).get_text("text") or "" for index in range(min(document.page_count, page_limit or document.page_count))]
    finally:
        document.close()
    text = "\n".join(pages).strip()
    return text


def _extract_with_ocr(raw_bytes: bytes, page_limit: int) -> str:
    fitz, rapid_ocr, image_module = _load_ocr_dependencies()
    if not fitz or not rapid_ocr or not image_module:
        return ""

    try:
        document = fitz.open(stream=raw_bytes, filetype="pdf")
    except Exception:
        logger.warning("Statement OCR could not open the PDF stream.", exc_info=True)
        return ""

    text_parts: list[str] = []
    try:
        pages_to_process = min(document.page_count, page_limit)
        matrix_scale = 1.6 if pages_to_process <= 4 else 1.3
        for index in range(pages_to_process):
            try:
                page = document.load_page(index)
                pix = page.get_pixmap(matrix=fitz.Matrix(matrix_scale, matrix_scale), alpha=False)
                image = image_module.open(BytesIO(pix.tobytes("png")))
                if index > 0:
                    top = int(image.height * 0.14)
                    image = image.crop((0, top, image.width, max(image.height - 40, top + 1)))
                result, _ = rapid_ocr(image)
            except Exception:
                logger.warning("Statement OCR failed on one PDF page; continuing with remaining pages.", exc_info=True)
                continue

            lines = _group_ocr_rows(result or [])
            if lines:
                text_parts.append("\n".join(lines))
    finally:
        document.close()

    return "\n".join(part for part in text_parts if part).strip()


def _group_ocr_rows(results: list) -> list[str]:
    grouped_rows: list[tuple[float, list[tuple[float, str]]]] = []

    for item in results:
        if len(item) < 2:
            continue
        box = item[0]
        text = _normalize_space(str(item[1]).replace("：", ":").replace("₹", "Rs "))
        if not text:
            continue
        top = min(float(point[1]) for point in box)
        left = min(float(point[0]) for point in box)
        if grouped_rows and abs(grouped_rows[-1][0] - top) <= 8:
            grouped_rows[-1][1].append((left, text))
        else:
            grouped_rows.append((top, [(left, text)]))

    lines: list[str] = []
    for _, cells in grouped_rows:
        ordered = [text for _, text in sorted(cells, key=lambda entry: entry[0])]
        line = _normalize_space(" ".join(ordered))
        if line:
            lines.append(line)
    return lines


@lru_cache(maxsize=1)
def _load_fitz():
    try:
        return import_module("fitz")
    except Exception:
        return None


@lru_cache(maxsize=1)
def _load_ocr_dependencies():
    try:
        fitz = import_module("fitz")
        rapid_ocr = import_module("rapidocr_onnxruntime").RapidOCR(
            no_cls=True,
            det_limit_side_len=768,
            max_side_len=1920,
        )
        image_module = import_module("PIL.Image")
    except Exception:
        return None, None, None
    return fitz, rapid_ocr, image_module


def _extract_with_isolated_ocr(raw_bytes: bytes, page_limit: int) -> str:
    if len(raw_bytes) < 4096:
        return ""
    try:
        with private_ocr_input(raw_bytes) as temp_path:
            completed = subprocess.run(
                ocr_command("statement", ISOLATED_OCR_WORKER, temp_path, page_limit),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=ISOLATED_OCR_TIMEOUT_SECONDS,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                **hidden_process_options(),
            )
        if completed.returncode != 0:
            return ""
        lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not lines:
            return ""
        payload = json.loads(lines[-1])
        return str(payload.get("text") or "").strip()
    except Exception as exc:
        safe_error_details(exc, "Isolated statement OCR is unavailable.", logger_name=__name__)
        return ""


def _collect_transaction_groups(lines: list[str]) -> list[str]:
    groups: list[str] = []
    current: list[str] = []

    for raw_line in lines:
        line = _normalize_space(raw_line)
        if not line or _is_statement_header(line):
            continue

        if TXN_START_RE.match(line):
            if current:
                groups.append(" ".join(current))
            current = [line]
            continue

        if current:
            current.append(line)

    if current:
        groups.append(" ".join(current))

    return groups


def _parse_transaction_group(group: str, previous_closing: Decimal | None, column_directions=None) -> tuple[ParsedTransaction | None, str]:
    match = TXN_RE.search(_normalize_space(group))
    if match is None:
        return None, "No amount and closing balance could be found"
    try:
        transaction_date = _parse_statement_date(match.group("txn_date"))
        closing_balance = _signed_balance(match.group("closing"))
        amount, direction = _amount_and_direction(match.group("first"), match.group("second"), closing_balance, previous_closing)
    except ValueError as error:
        return None, str(error)

    description = match.group("body")
    if match.group("tail"):
        description = f"{description} {match.group('tail')}"
    direction = direction or (column_directions or {}).get((match.group("txn_date"), amount, closing_balance))
    details = classify_transaction_text(description, direction or _infer_direction(description, closing_balance, previous_closing))

    return ParsedTransaction(
        transaction_date=transaction_date,
        amount=amount,
        closing_balance=closing_balance,
        direction=details["direction"],
        classification=details["classification"],
        category=details["category"],
        payment_mode=details["payment_mode"],
        merchant=details["merchant"],
        description=details["description"],
        raw_description=details["raw_description"],
        external_reference=details["external_reference"],
        counterparty=details["counterparty"],
        company_name=details["company_name"],
    ), ""


def _parse_credit_card_transactions(lines: list[str]) -> list[ParsedTransaction]:
    transactions: list[ParsedTransaction] = []
    for raw_line in lines:
        line = _normalize_space(raw_line)
        if not line:
            continue
        for match in CARD_TXN_RE.finditer(line):
            amount = _to_decimal(match.group("amount"))
            if amount <= 0:
                continue
            description = _normalize_space(match.group("body"))
            direction = "credit" if match.group("sign") == "+" else "debit"
            details = classify_transaction_text(description, direction)
            transactions.append(
                ParsedTransaction(
                    transaction_date=datetime.strptime(match.group("txn_date"), "%d/%m/%Y").date(),
                    amount=amount,
                    closing_balance=Decimal("0"),
                    direction=details["direction"],
                    classification=details["classification"],
                    category=details["category"],
                    payment_mode=details["payment_mode"],
                    merchant=details["merchant"],
                    description=details["description"],
                    raw_description=details["raw_description"],
                    external_reference=details["external_reference"],
                    counterparty=details["counterparty"],
                    company_name=details["company_name"],
                )
            )
    return transactions


def classify_transaction_text(description: str, direction: str) -> dict[str, str]:
    cleaned = _sanitize_description(description)
    normalized_direction = _infer_direction(cleaned, 0, None) if direction not in {"credit", "debit"} else direction
    classification, category = _classify_transaction(cleaned, normalized_direction)

    return {
        "direction": normalized_direction,
        "classification": classification,
        "category": category,
        "payment_mode": _infer_payment_mode(cleaned),
        "merchant": _extract_merchant(cleaned),
        "description": _build_description(cleaned, classification, category),
        "raw_description": cleaned,
        "external_reference": _extract_reference(cleaned),
        "counterparty": _extract_merchant(cleaned),
        "company_name": _extract_company_name(cleaned),
    }


def _classify_transaction(description: str, direction: str) -> tuple[str, str]:
    text = description.upper()

    if direction == "credit":
        if any(keyword in text for keyword in ("REFUND", "REVERSAL", "REVERSED")):
            return "other", "income"
        if any(keyword in text for keyword in ("NEFT CR", "RTGS CR", "IMPS CR", "SALARY", "BONUS")):
            return "other", "income"
        return "other", "transfer"

    if any(keyword in text for keyword in SUBSCRIPTION_KEYWORDS):
        return "expense", "subscription"

    if _looks_like_wallet_mandate(text):
        if any(keyword in text for keyword in ("NETFLIX", "SPOTIFY", "PRIME", "YOUTUBE", "GOOGLE PLAY", "PLAYSTORE", "SUBSCRIPTION", "MEMBERSHIP")):
            return "expense", "subscription"
        return "other", "transfer"

    if any(keyword in text for keyword in INVESTMENT_KEYWORDS):
        return "other", "investment"

    if any(keyword in text for keyword in CREDIT_CARD_KEYWORDS):
        return "other", "credit_card"

    if _looks_like_loan_payment(text):
        return "loan", "loan"

    for classification, category, keywords in CLASSIFICATION_RULES:
        if any(keyword in text for keyword in keywords):
            return classification, category

    if any(token in text for token in ("@YBL", "@OKAXIS", "@AXIS", "@PTY", "@YESPAY")):
        return "other", "transfer"

    return "expense", "other"


def _looks_like_loan_payment(text: str) -> bool:
    if any(keyword in text for keyword in LOAN_EXCLUSION_KEYWORDS):
        return False
    if _looks_like_wallet_mandate(text):
        return False
    return any(pattern.search(text) for pattern in LOAN_KEYWORD_PATTERNS)


def _looks_like_wallet_mandate(text: str) -> bool:
    return any(keyword in text for keyword in DIGITAL_WALLET_KEYWORDS) and any(keyword in text for keyword in MANDATE_KEYWORDS)


def _infer_direction(description: str, closing_balance: Decimal, previous_closing: Decimal | None) -> str:
    text = description.upper()

    if previous_closing is not None:
        if closing_balance > previous_closing:
            return "credit"
        if closing_balance < previous_closing:
            return "debit"

    if any(keyword in text for keyword in (" CR", " REFUND", "REVERSAL", "SALARY", "NEFT CR", "RTGS CR", "IMPS CR")):
        return "credit"

    return "debit"


def _infer_payment_mode(description: str) -> str:
    text = description.upper()
    for prefix, payment_mode in PAYMENT_MODE_RULES:
        if text.startswith(prefix):
            return payment_mode
    return "BANK"


def _extract_merchant(description: str) -> str:
    text = description.upper()
    known_merchant = _match_known_merchant(text)
    if known_merchant:
        return known_merchant

    pieces = re.split(r"[-/]", text)
    merchant_parts: list[str] = []

    for piece in pieces:
        value = _clean_merchant_piece(piece)
        if not value:
            continue
        if any(char.isdigit() for char in value) and len(value.replace(" ", "")) > 8:
            continue
        if value in {"UPI", "ACH D", "NEFT CR", "RTGS CR", "IMPS CR", "PAY", "UPI PAY"}:
            continue
        if value.startswith(("YESB", "UTIB", "HDFC", "ICIC", "KKBK", "FDRL", "AIRP", "RZP")):
            continue
        merchant_parts.append(value.title())
        if len(" ".join(merchant_parts)) >= 40:
            break

    if merchant_parts:
        return " ".join(merchant_parts[:3])

    return description[:60].title()


def _build_description(raw_description: str, classification: str, category: str) -> str:
    cleaned = raw_description.strip()
    if classification == "loan":
        return f"Auto-classified as loan payment: {cleaned[:140]}"
    if category == "credit_card":
        return f"Auto-classified as credit card payment: {cleaned[:140]}"
    if category == "investment":
        return f"Auto-classified as investment transfer: {cleaned[:140]}"
    return cleaned[:140]


def _extract_reference(description: str) -> str:
    matches = REFERENCE_RE.findall(description.upper())
    if not matches:
        return ""
    return matches[-1]


def _extract_statement_period(full_text: str) -> tuple[date | None, date | None]:
    match = PERIOD_RE.search(full_text)
    if match is None:
        return None, None
    return (
        datetime.strptime(match.group(1).replace(":", "/").replace("-", "/"), "%d/%m/%Y").date(),
        datetime.strptime(match.group(2).replace(":", "/").replace("-", "/"), "%d/%m/%Y").date(),
    )


def _extract_account_number(full_text: str) -> str:
    match = ACCOUNT_NO_RE.search(full_text)
    if match is None:
        return ""
    return _normalize_space(match.group(1))


def _extract_account_holder(full_text: str) -> str:
    for raw_line in full_text.splitlines():
        line = _normalize_space(raw_line).upper()
        if not line.startswith(("MR ", "MRS ", "MS ")):
            continue
        candidate = line.split(" ", 1)[1]
        cleaned_tokens: list[str] = []
        for token in candidate.split():
            if token in ACCOUNT_HOLDER_STOP_WORDS:
                break
            cleaned_tokens.append(token)
            if len(cleaned_tokens) >= 4:
                break
        if cleaned_tokens:
            return clean_statement_text(_normalize_space(" ".join(cleaned_tokens).title()))

    match = ACCOUNT_HOLDER_RE.search(full_text.upper())
    if match is None:
        return ""
    tokens: list[str] = []
    for token in match.group(1).split():
        if token in ACCOUNT_HOLDER_STOP_WORDS:
            break
        tokens.append(token)
        if len(tokens) >= 4:
            break
    return _normalize_space(" ".join(tokens).title())


def _extract_bank_name(full_text: str) -> str:
    text = full_text.upper()
    for keyword, label in BANK_NAME_RULES:
        if keyword in text:
            return label
    match = re.search(r"([A-Z ]+BANK(?: LIMITED)?)", text)
    if match is None:
        return ""
    return _normalize_space(match.group(1).title())


def _detect_statement_kind(full_text: str) -> str:
    text = full_text.upper()
    for statement_kind, keywords in STATEMENT_KIND_RULES:
        if any(keyword in text for keyword in keywords):
            return statement_kind
    if any(keyword in text for keyword in ("STATEMENT OF ACCOUNT", "ACCOUNT NO", "CLOSING BALANCE")):
        return "bank_statement"
    return "other_statement"


def _extract_loan_hints(full_text: str) -> dict:
    text = full_text.upper()
    inferred_type = ""
    for loan_type, keywords in LOAN_TYPE_HINT_RULES:
        if any(keyword in text for keyword in keywords):
            inferred_type = loan_type
            break

    lender = _extract_bank_name(full_text)
    match = re.search(rf"(?:EMI|INSTALLMENT)\s+(?:AMOUNT|AMT)?\s*[:.]?\s*{INR_LABEL_TOKEN}?\s*([0-9,]+(?:\.\d{{2}})?)", text, re.IGNORECASE)
    emi_amount = float(match.group(1).replace(",", "")) if match else 0.0

    return {
        "loan_type": inferred_type,
        "lender": lender,
        "emi_amount": emi_amount,
    }


def _is_statement_header(line: str) -> bool:
    if line == ".":
        return True
    return line.startswith(HEADER_PREFIXES)


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _sanitize_description(value: str) -> str:
    cleaned = _normalize_space(value)
    for marker in NOISE_MARKERS:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[0].strip()
    return _normalize_space(cleaned)


def _to_decimal(value: str) -> Decimal:
    return Decimal(str(value).replace(",", ""))


def _match_known_merchant(text: str) -> str:
    if "INDIAN OIL" in text:
        return "Indian Oil Petrol Pump"

    filling_station = re.search(r"(?:UPI-)?([A-Z0-9 ]+FILLING STATIO)", text)
    if filling_station:
        return filling_station.group(1).replace("STATIO", "Station").title()

    for keywords, merchant in KNOWN_MERCHANT_RULES:
        if any(keyword in text for keyword in keywords):
            return merchant

    return ""


def _extract_company_name(text: str) -> str:
    merchant = _match_known_merchant(text)
    if merchant:
        return merchant

    upper = text.upper()
    for keyword, label in BANK_NAME_RULES:
        if keyword in upper:
            return label
    for keyword in ("AMAZON", "FLIPKART", "MYNTRA", "SWIGGY", "ZOMATO", "GROWW", "ZERODHA", "CRED", "JIO", "NETFLIX", "SPOTIFY", "GOOGLE PLAY", "PLAYSTORE", "YOUTUBE"):
        if keyword in upper:
            return "Google Play" if keyword in {"GOOGLE PLAY", "PLAYSTORE"} else keyword.title()
    if any(keyword in upper for keyword in ("GOOGLE PAY", "GOOGLEPAY", "GPAY", "G PAY")):
        return "Google Pay"

    merchant_guess = _extract_merchant(text)
    return merchant_guess[:255]


def _clean_merchant_piece(piece: str) -> str:
    value = _normalize_space(re.sub(r"[^A-Z0-9& ]", " ", piece.upper()))
    for pattern in MERCHANT_NOISE_PATTERNS:
        value = _normalize_space(re.sub(pattern, "", value))
    value = value.replace("PETROL PU", "PETROL PUMP")
    value = value.replace("FILLING STATIO", "FILLING STATION")
    return _normalize_space(value)
