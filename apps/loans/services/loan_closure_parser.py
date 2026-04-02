import re
from datetime import datetime
from typing import BinaryIO

from alfred_ai.services import apply_parser_learning, extract_document_text


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

    def parse_document(self, file_obj: BinaryIO, file_name: str, *, user=None) -> dict:
        raw_bytes = file_obj.read()
        extracted = extract_document_text(raw_bytes, file_name, ocr_page_limit=8)
        extracted_text = extracted.text or ""
        normalized = " ".join(extracted_text.split())
        document_type = self._classify_document_type(normalized)
        payload = {
            "document_type": document_type,
            "lender_name": self._extract_lender_name(normalized),
            "borrower_name": self._extract_borrower_name(normalized),
            "loan_account_number": self._extract_account_number(normalized),
            "statement_date": self._extract_date_for_labels(normalized, ["STATEMENT DATE", "LETTER DATE", "DATE"]),
            "effective_closure_date": self._extract_date_for_labels(normalized, ["CLOSURE DATE", "FORECLOSURE DATE", "LOAN CLOSED ON", "NO DUE DATE"]),
            "due_by_date": self._extract_date_for_labels(normalized, ["DUE BY", "PAY BY", "PAYMENT DUE DATE", "VALID TILL"]),
            "outstanding_principal": self._extract_amount_for_labels(normalized, ["OUTSTANDING PRINCIPAL", "PRINCIPAL OUTSTANDING", "PRINCIPAL AMOUNT"]),
            "accrued_interest": self._extract_amount_for_labels(normalized, ["ACCRUED INTEREST", "INTEREST AMOUNT", "INTEREST"]),
            "foreclosure_charges": self._extract_amount_for_labels(normalized, ["FORECLOSURE CHARGES", "PRE CLOSURE CHARGES", "PRE-CLOSURE CHARGES", "CLOSURE CHARGES"]),
            "taxes_gst": self._extract_amount_for_labels(normalized, ["GST", "TAX", "SERVICE TAX"]),
            "overdue_charges": self._extract_amount_for_labels(normalized, ["OVERDUE CHARGES", "PENALTY", "PENAL CHARGES", "LATE PAYMENT CHARGES"]),
            "total_amount_payable": self._extract_total_amount(normalized),
            "matched_keyword": self._extract_keyword(normalized),
        }
        payload["closure_amount"] = payload["total_amount_payable"]
        payload["closure_date"] = payload["effective_closure_date"] or payload["statement_date"]
        field_names = [key for key, value in payload.items() if value not in ("", None, 0)]
        base_confidence = extracted.confidence
        if payload["matched_keyword"]:
            base_confidence += 0.08
        if payload["loan_account_number"]:
            base_confidence += 0.08
        if payload["total_amount_payable"]:
            base_confidence += 0.08
        if document_type != "other":
            base_confidence += 0.08
        base_confidence = min(0.97, max(0.08, base_confidence))
        confidence, learning_notes = apply_parser_learning(
            user=user,
            scope="loan_closure_document",
            filename=file_name,
            detected_type="loan_closure_document",
            text=extracted_text,
            field_names=field_names,
            confidence=base_confidence,
        )
        parser_status = (
            "parsed"
            if payload["matched_keyword"] and (payload["loan_account_number"] or payload["total_amount_payable"])
            else ("needs_review" if extracted_text.strip() or confidence >= 0.2 else "failed")
        )
        return {
            "extracted_text": extracted_text,
            "payload": payload,
            "confidence": confidence,
            "parser_status": parser_status,
            "parser_notes": " ".join([*extracted.notes, *learning_notes]).strip(),
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
        payload_lender = (payload.get("lender_name") or "").upper()
        if lender and lender not in text and lender not in payload_lender and not account_number:
            return False, "The lender or loan account reference could not be verified in the closure document."

        return True, "Foreclosure document appears to match the selected loan."

    def _classify_document_type(self, text: str) -> str:
        upper = text.upper()
        if any(keyword in upper for keyword in ["FORECLOSURE STATEMENT", "PRE-CLOSURE STATEMENT", "PRE CLOSURE STATEMENT"]):
            return "foreclosure_statement"
        if any(keyword in upper for keyword in ["NO DUE", "NO-DUE", "NO OBJECTION", "NOC"]):
            return "noc"
        if any(keyword in upper for keyword in ["CLOSURE LETTER", "LOAN CLOSURE", "LOAN CLOSED", "FULL AND FINAL"]):
            return "closure_letter"
        if "LOAN STATEMENT" in upper:
            return "loan_statement"
        return "other"

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

    def _extract_lender_name(self, text: str) -> str:
        match = re.search(r"([A-Z][A-Z& ]{3,40}(?:BANK|FINANCE|FINANCIAL SERVICES|NBFC|CAPITAL|HOUSING|LOANS))", text, re.IGNORECASE)
        return " ".join(match.group(1).split()).title() if match else ""

    def _extract_borrower_name(self, text: str) -> str:
        patterns = [
            r"(?:BORROWER\s+NAME|CUSTOMER\s+NAME|BORROWER|CUSTOMER)\s*[:.]?\s*([A-Z][A-Z ]{2,80}?)(?=\s+(?:LOAN\s+ACCOUNT|ACCOUNT\s+NUMBER|STATEMENT\s+DATE|CLOSURE\s+DATE|DUE\s+BY|OUTSTANDING|ACCRUED|FORECLOSURE|GST|OVERDUE|TOTAL)\b|$)",
            r"\b(?:MR|MRS|MS)\s+([A-Z][A-Z ]{2,80}?)(?=\s+(?:LOAN\s+ACCOUNT|ACCOUNT\s+NUMBER|STATEMENT\s+DATE|CLOSURE\s+DATE|DUE\s+BY|OUTSTANDING|ACCRUED|FORECLOSURE|GST|OVERDUE|TOTAL)\b|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split()).title()
        return ""

    def _extract_amount_for_labels(self, text: str, labels: list[str]) -> float:
        amount_pattern = r"(?:INR|RS\.?|₹)?\s*([0-9,]+(?:\.\d{1,2})?)"
        for label in labels:
            pattern = rf"{re.escape(label)}\s*[:.]?\s*{amount_pattern}"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        return 0.0

    def _extract_total_amount(self, text: str) -> float:
        patterns = [
            r"(?:TOTAL|FINAL|FULL\s+AND\s+FINAL|TOTAL\s+AMOUNT\s+PAYABLE|AMOUNT\s+PAYABLE)\s*(?:AMOUNT|AMT)?\s*[:.]?\s*(?:INR|RS\.?|₹)?\s*([0-9,]+(?:\.\d{1,2})?)",
            r"(?:FORECLOSURE|CLOSURE|SETTLEMENT)\s+(?:AMOUNT|AMT)\s*[:.]?\s*(?:INR|RS\.?|₹)?\s*([0-9,]+(?:\.\d{1,2})?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(",", ""))
        total_from_components = sum(
            value or 0
            for value in [
                self._extract_amount_for_labels(text, ["OUTSTANDING PRINCIPAL", "PRINCIPAL OUTSTANDING"]),
                self._extract_amount_for_labels(text, ["ACCRUED INTEREST", "INTEREST AMOUNT"]),
                self._extract_amount_for_labels(text, ["FORECLOSURE CHARGES", "PRE CLOSURE CHARGES", "PRE-CLOSURE CHARGES"]),
                self._extract_amount_for_labels(text, ["GST", "TAX", "SERVICE TAX"]),
                self._extract_amount_for_labels(text, ["OVERDUE CHARGES", "PENALTY", "PENAL CHARGES"]),
            ]
        )
        return round(total_from_components, 2) if total_from_components else 0.0

    def _extract_date_for_labels(self, text: str, labels: list[str]) -> str:
        patterns = [rf"{re.escape(label)}\s*[:.]?\s*([0-9]{{1,2}}[/-][0-9]{{1,2}}[/-][0-9]{{2,4}})" for label in labels]
        patterns.append(r"(?:DATE)\s*[:.]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})")
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
