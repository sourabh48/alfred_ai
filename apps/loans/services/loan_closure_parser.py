import re
from datetime import datetime
from typing import BinaryIO

import pdfplumber


class LoanClosureParser:
    CLOSURE_KEYWORDS = (
        "FORECLOSURE",
        "FORECLOSED",
        "NO DUE",
        "NO-DUE",
        "LOAN CLOSURE",
        "LOAN CLOSED",
        "FULL AND FINAL",
    )

    def parse_document(self, file_obj: BinaryIO, file_name: str) -> dict:
        file_name = (file_name or "").lower()
        extracted_text = ""
        if file_name.endswith(".pdf"):
            with pdfplumber.open(file_obj) as pdf:
                extracted_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        else:
            extracted_text = file_obj.read().decode("utf-8", errors="ignore")

        normalized = " ".join(extracted_text.split())
        return {
            "extracted_text": extracted_text,
            "payload": {
                "loan_account_number": self._extract_account_number(normalized),
                "closure_amount": self._extract_amount(normalized),
                "closure_date": self._extract_date(normalized),
                "matched_keyword": self._extract_keyword(normalized),
            },
        }

    def verify_document(self, loan, parsed: dict) -> tuple[bool, str]:
        payload = parsed.get("payload", {})
        text = (parsed.get("extracted_text") or "").upper()
        if not any(keyword in text for keyword in self.CLOSURE_KEYWORDS):
            return False, "Document does not clearly indicate foreclosure, closure, or no-due status."

        account_number = (payload.get("loan_account_number") or "").upper()
        if loan.loan_account_number and account_number:
            if account_number not in loan.loan_account_number.upper() and loan.loan_account_number.upper() not in account_number:
                return False, "Uploaded closure document account number does not match the selected loan."

        lender = (loan.lender or "").upper()
        if lender and lender not in text and not account_number:
            return False, "The lender or loan account reference could not be verified in the closure document."

        return True, "Foreclosure document appears to match the selected loan."

    def _extract_account_number(self, text: str) -> str:
        patterns = [
            r"(?:LOAN|ACCOUNT)\s+(?:NO|NUMBER|ID)\s*[:.]?\s*([A-Z0-9-]{6,24})",
            r"(?:AGREEMENT|CONTRACT)\s+(?:NO|NUMBER)\s*[:.]?\s*([A-Z0-9-]{6,24})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return re.sub(r"[^A-Z0-9]", "", match.group(1).upper())
        return ""

    def _extract_amount(self, text: str) -> float:
        patterns = [
            r"(?:FORECLOSURE|CLOSURE|SETTLEMENT|FINAL)\s+(?:AMOUNT|AMT)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
            r"(?:FULL\s+AND\s+FINAL)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return 0.0

    def _extract_date(self, text: str) -> str:
        patterns = [
            r"(?:CLOSURE|FORECLOSURE|NO\s*DUE)\s+DATE\s*[:.]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
            r"(?:DATE)\s*[:.]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            raw = match.group(1)
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
                try:
                    return datetime.strptime(raw, fmt).date().isoformat()
                except ValueError:
                    continue
        return ""

    def _extract_keyword(self, text: str) -> str:
        for keyword in self.CLOSURE_KEYWORDS:
            if keyword in text.upper():
                return keyword.title()
        return ""


loan_closure_parser = LoanClosureParser()
