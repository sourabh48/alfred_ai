"""
Loan Book PDF Parser
Parses loan statements and loan books from banks and NBFCs.
"""
import re
from datetime import datetime
from typing import List, Dict, BinaryIO

from alfred_ai.services import apply_parser_learning, extract_document_text


class LoanPDFParser:
    """Parse loan details from PDF statements."""

    # Known lenders and their patterns
    LENDER_PATTERNS = [
        (r"BAJAJ\s+(?:HOUSING|FINANCE)", "Bajaj Finance"),
        (r"POONAWALLA\s+FINCORP", "Poonawalla Fincorp"),
        (r"HDFC\s+(?:HOME|PERSONAL)", "HDFC Bank"),
        (r"ICICI\s+(?:HOME|PERSONAL)", "ICICI Bank"),
        (r"SBI\s+(?:HOME|PERSONAL)", "State Bank of India"),
        (r"AXIS\s+(?:HOME|PERSONAL)", "Axis Bank"),
        (r"TATA\s+CAPITAL", "Tata Capital"),
        (r"FULLERTON", "Fullerton India"),
        (r"MUTHOOT", "Muthoot Finance"),
        (r"MANAPPURAM", "Manappuram Finance"),
    ]

    LOAN_TYPE_PATTERNS = [
        (r"HOME\s+LOAN|HOUSING\s+LOAN", "home"),
        (r"PERSONAL\s+LOAN|PL\b", "personal"),
        (r"CAR\s+LOAN|AUTO\s+LOAN|VEHICLE\s+LOAN", "car"),
        (r"EDUCATION\s+LOAN|STUDENT\s+LOAN", "education"),
        (r"BUSINESS\s+LOAN", "business"),
        (r"CREDIT\s+CARD", "credit_card"),
    ]

    def parse_loan_pdf(self, pdf_file: BinaryIO, user=None, filename: str = "") -> List[Dict]:
        """
        Parse loan details from PDF.
        Returns list of loan dictionaries.
        """
        return self.parse_document(pdf_file, user=user, filename=filename)["loans"]

    def parse_document(self, pdf_file: BinaryIO, user=None, filename: str = "") -> Dict:
        """Parse a loan document and return metadata plus extracted loan rows."""
        loans = []
        full_text = ""
        document_type = "other"
        confidence = 0.0

        try:
            raw_bytes = self._read_bytes(pdf_file)
            extraction = extract_document_text(raw_bytes, filename or getattr(pdf_file, "name", "loan.pdf"))
            full_text = extraction.text
            document_type = self._detect_document_type(full_text)
            if document_type == "loan_book":
                loans = self._parse_loan_book(full_text)
            else:
                loan = self._parse_single_loan_statement(full_text)
                if loan and any(loan.values()):
                    loans = [loan]
            confidence = max(self._document_confidence(full_text, loans, document_type), extraction.confidence * 0.75 if full_text.strip() else 0.0)
            confidence, _ = apply_parser_learning(
                user=user,
                scope="loan_document",
                filename=filename or getattr(pdf_file, "name", "loan.pdf"),
                detected_type=document_type,
                text=full_text,
                field_names=sorted({key for loan in loans for key, value in loan.items() if value not in ("", None, 0)}),
                confidence=confidence,
            )

        except Exception as e:
            print(f"Error parsing loan PDF: {e}")

        return {
            "document_type": document_type,
            "confidence": confidence,
            "extracted_text": full_text[:20000],
            "loans": loans,
            "parser_notes": " ".join(extraction.notes[:6]).strip() if 'extraction' in locals() else "",
            "payload": {
                "extraction_method": extraction.method if 'extraction' in locals() else "",
                "extraction_notes": extraction.notes[:6] if 'extraction' in locals() else [],
                "raw_text_excerpt": " ".join((full_text or "").split())[:600],
                "extraction_review": extraction.review_payload if 'extraction' in locals() else {},
            },
        }

    def _read_bytes(self, upload: BinaryIO) -> bytes:
        current = upload.tell() if hasattr(upload, "tell") else None
        if hasattr(upload, "seek"):
            upload.seek(0)
        content = upload.read()
        if current is not None and hasattr(upload, "seek"):
            upload.seek(current)
        return content

    def _is_loan_book(self, text: str) -> bool:
        """Detect if PDF is a loan book (multiple loans) or single statement."""
        # Look for indicators of multiple loans
        loan_count_patterns = [
            r"LOAN\s+(?:NO|NUMBER|ID)\s*[:.]?\s*\d+",
            r"ACCOUNT\s+(?:NO|NUMBER)\s*[:.]?\s*\d+",
        ]

        matches = 0
        for pattern in loan_count_patterns:
            matches += len(re.findall(pattern, text, re.IGNORECASE))

        return matches > 1

    def _detect_document_type(self, text: str) -> str:
        upper = text.upper()
        if self._is_loan_book(text):
            return "loan_book"
        if any(token in upper for token in ("SANCTION LETTER", "SANCTIONED AMOUNT", "DATE OF SANCTION")):
            return "sanction_letter"
        if any(token in upper for token in ("REPAYMENT SCHEDULE", "AMORTIZATION", "INSTALLMENT SCHEDULE")):
            return "repayment_schedule"
        if any(token in upper for token in ("LOAN STATEMENT", "OUTSTANDING", "EMI AMOUNT")):
            return "loan_statement"
        return "other"

    def _parse_loan_book(self, text: str) -> List[Dict]:
        """Parse multiple loans from loan book."""
        loans = []

        # Split by loan sections (common patterns)
        loan_sections = re.split(
            r"(?:LOAN\s+(?:NO|NUMBER|DETAILS)|ACCOUNT\s+(?:NO|NUMBER))\s*[:.]?\s*\d+",
            text,
            flags=re.IGNORECASE
        )

        for section in loan_sections[1:]:  # Skip first split (header)
            loan = self._extract_loan_details(section)
            if loan and loan.get('principal', 0) > 0:
                loans.append(loan)

        return loans

    def _parse_single_loan_statement(self, text: str) -> Dict:
        """Parse single loan from statement."""
        return self._extract_loan_details(text)

    def _document_confidence(self, text: str, loans: List[Dict], document_type: str) -> float:
        confidence = 0.4 if text.strip() else 0.0
        if document_type != "other":
            confidence += 0.15
        if loans:
            confidence += 0.25
        if any(loan.get("loan_account_number") for loan in loans):
            confidence += 0.1
        if any(loan.get("loan_type") and loan.get("loan_type") != "other" for loan in loans):
            confidence += 0.05
        if any(loan.get("lender") and loan.get("lender") != "Unknown Lender" for loan in loans):
            confidence += 0.05
        return round(min(confidence, 0.97), 2)

    def _extract_loan_details(self, text: str) -> Dict:
        """Extract loan details from text section."""
        loan = {
            "lender": self._extract_lender(text),
            "loan_type": self._extract_loan_type(text),
            "loan_account_number": self._extract_account_number(text),
            "principal": self._extract_principal(text),
            "interest_rate": self._extract_interest_rate(text),
            "emi": self._extract_emi(text),
            "tenure_months": self._extract_tenure(text),
            "remaining_balance": self._extract_outstanding(text),
            "start_date": self._extract_start_date(text),
        }

        # Auto-calculate missing values
        if loan['remaining_balance'] is None and loan['principal']:
            loan['remaining_balance'] = loan['principal']

        if loan['tenure_months'] is None and loan['principal'] and loan['emi']:
            # Rough estimate
            loan['tenure_months'] = int(loan['principal'] / loan['emi'])

        return loan

    def _extract_lender(self, text: str) -> str:
        """Extract lender name."""
        for pattern, lender in self.LENDER_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return lender

        # Fallback: Look for bank name
        bank_match = re.search(r"([A-Z\s]+(?:BANK|FINANCE|FINCORP))", text)
        if bank_match:
            return bank_match.group(1).strip().title()

        return "Unknown Lender"

    def _extract_loan_type(self, text: str) -> str:
        """Extract loan type."""
        for pattern, loan_type in self.LOAN_TYPE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return loan_type

        return "other"

    def _extract_account_number(self, text: str) -> str:
        """Extract loan account number."""
        patterns = [
            r"(?:LOAN|ACCOUNT)\s+(?:NO|NUMBER|ID)\s*[:.]?\s*([A-Z0-9]{6,20})",
            r"(?:AGREEMENT|CONTRACT)\s+(?:NO|NUMBER)\s*[:.]?\s*([A-Z0-9]{6,20})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_principal(self, text: str) -> float:
        """Extract principal/loan amount."""
        patterns = [
            r"(?:PRINCIPAL|LOAN)\s+(?:AMOUNT|AMT)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
            r"SANCTIONED\s+(?:AMOUNT|AMT)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
            r"DISBURSED\s+(?:AMOUNT|AMT)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))

        return 0.0

    def _extract_interest_rate(self, text: str) -> float:
        """Extract interest rate."""
        patterns = [
            r"(?:INTEREST|RATE)\s+(?:RATE|%)\s*[:.]?\s*([0-9.]+)\s*%",
            r"ROI\s*[:.]?\s*([0-9.]+)\s*%",
            r"([0-9.]+)\s*%\s+(?:P\.A|PER\s+ANNUM)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return 0.0

    def _extract_emi(self, text: str) -> float:
        """Extract EMI amount."""
        patterns = [
            r"EMI\s+(?:AMOUNT|AMT)?\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
            r"(?:MONTHLY|INSTALLMENT)\s+(?:AMOUNT|AMT)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))

        return 0.0

    def _extract_tenure(self, text: str) -> int:
        """Extract loan tenure in months."""
        patterns = [
            r"(?:TENURE|PERIOD)\s*[:.]?\s*([0-9]+)\s+(?:MONTHS|MOS)",
            r"(?:TENURE|PERIOD)\s*[:.]?\s*([0-9]+)\s+(?:YEARS|YRS)",  # Convert to months
        ]

        # Months pattern
        match = re.search(patterns[0], text, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Years pattern
        match = re.search(patterns[1], text, re.IGNORECASE)
        if match:
            return int(match.group(1)) * 12

        return 0

    def _extract_outstanding(self, text: str) -> float:
        """Extract outstanding/remaining balance."""
        patterns = [
            r"(?:OUTSTANDING|BALANCE)\s+(?:AMOUNT|AMT|PRINCIPAL)?\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
            r"(?:REMAINING|CURRENT)\s+(?:BALANCE|PRINCIPAL)\s*[:.]?\s*(?:INR|RS\.?)?\s*([0-9,]+(?:\.\d{2})?)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))

        return None

    def _extract_start_date(self, text: str) -> str:
        """Extract loan start date."""
        patterns = [
            r"(?:START|DISBURSEMENT|SANCTION)\s+DATE\s*[:.]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
            r"(?:DATE\s+OF\s+)?(?:DISBURSEMENT|SANCTION)\s*[:.]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"]:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            return parsed_date.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                except Exception:
                    pass

        # Default to current date if not found
        return datetime.now().strftime("%Y-%m-%d")


# Singleton instance
loan_pdf_parser = LoanPDFParser()
