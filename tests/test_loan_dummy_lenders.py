"""LOAN-08 with dummy documents: invented statements in six common Indian lender layouts are read field by field.

Every name, number and amount is made up; the layouts follow the label wording lenders commonly use (lakh grouping,
"Rate of Interest", "Instalment", "A/c No."). Synthetic text PDFs only; no real lender document is used.
"""
from decimal import Decimal
from io import BytesIO

import fitz
from django.test import SimpleTestCase

from apps.loans.services.loan_pdf_parser import LoanPDFParser

LENDERS = {
    "hdfc-home": ("HDFC HOME LOANS\nLoan Statement\nLoan Account No: 612345678\nLoan Amount : Rs. 35,00,000.00\n"
                  "Rate of Interest : 8.75% p.a.\nEMI Amount : Rs. 30,925.00\nTenure : 240 Months\n"
                  "Principal Outstanding : Rs. 31,24,567.89\nDisbursement Date : 15/04/2021",
                  dict(lender="HDFC Bank", loan_type="home", loan_account_number="612345678", principal="3500000.00", interest_rate=8.75,
                       emi="30925.00", tenure_months=240, remaining_balance="3124567.89")),
    "sbi-home": ("STATE BANK OF INDIA\nSBI Home Loan - Account Statement\nLoan A/c No. 38012345678\nSanctioned Amount ₹ 40,00,000\n"
                 "ROI : 8.50 %\nEMI : ₹ 34,713\nTenure : 20 Years\nOutstanding Balance : ₹ 36,12,340.00\nDate of Disbursement : 01-06-2020",
                 dict(lender="State Bank of India", loan_type="home", loan_account_number="38012345678", principal="4000000", interest_rate=8.5,
                      emi="34713", tenure_months=240, remaining_balance="3612340.00")),
    "icici-personal": ("ICICI Bank\nPersonal Loan Statement\nLoan Account Number LBPUN00001234567\nLoan Amount INR 5,00,000\n"
                       "Interest Rate 11.25% per annum\nInstalment Amount INR 10,934\nTenure 60 months\nPrincipal Outstanding INR 3,21,456.12",
                       dict(lender="ICICI Bank", loan_type="personal", loan_account_number="LBPUN00001234567", principal="500000", interest_rate=11.25,
                            emi="10934", tenure_months=60, remaining_balance="321456.12")),
    "bajaj-personal": ("Bajaj Finance Limited\nPersonal Loan - Statement of Account\nLoan Account No.: 4XXPL12345678\nLoan Amount: Rs.3,00,000\n"
                       "Rate of Interest (p.a.): 14%\nEMI Amount: Rs.7,000\nTenure (months): 60\nTotal Outstanding: Rs. 2,10,500",
                       dict(lender="Bajaj Finance", loan_type="personal", loan_account_number="4XXPL12345678", principal="300000", interest_rate=14.0,
                            emi="7000", tenure_months=60, remaining_balance="210500")),
    "axis-car": ("AXIS BANK\nCar Loan Repayment Schedule\nAgreement No: AXCAR1234567\nLoan Amount: 8,00,000\nInterest Rate: 9.15%\n"
                 "EMI: 16,650\nTenure: 60 Months\nBalance Principal: 5,40,210",
                 dict(lender="Axis Bank", loan_type="car", loan_account_number="AXCAR1234567", principal="800000", interest_rate=9.15,
                      emi="16650", tenure_months=60, remaining_balance="540210")),
    "kotak-education": ("Kotak Mahindra Bank\nEducation Loan Statement\nLoan Account Number: 0123EDU456\nDisbursed Amount: Rs 12,00,000\n"
                        "Rate of Interest: 10.40% p.a.\nMonthly Instalment: Rs 15,800\nRepayment Tenure: 120 months\nPrincipal Outstanding: Rs 9,85,000",
                        dict(lender="Kotak Mahindra Bank", loan_type="education", loan_account_number="0123EDU456", principal="1200000",
                             interest_rate=10.4, emi="15800", tenure_months=120, remaining_balance="985000")),
}


def pdf(text):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 60), text, fontname="helv", fontsize=10)  # helv lacks ₹; the extracted text keeps the label
    data = document.tobytes()
    document.close()
    return BytesIO(data)


class DummyLenderTests(SimpleTestCase):
    def test_every_field_is_read_from_six_lender_layouts(self):
        parser = LoanPDFParser()
        for name, (text, expected) in LENDERS.items():
            with self.subTest(lender=name):
                text = text.replace("₹", "INR")  # the built-in PDF font has no rupee sign
                loans = parser.parse_document(pdf(text), filename=f"{name}.pdf")["loans"]
                self.assertEqual(len(loans), 1)
                got = {key: loans[0][key] for key in expected}
                want = {key: Decimal(value) if key in ("principal", "emi", "remaining_balance") else value for key, value in expected.items()}
                self.assertEqual(got, want)

    def test_the_rupee_sign_is_read_like_rs(self):
        details = LoanPDFParser()._extract_loan_details("SBI Home Loan\nSanctioned Amount ₹ 40,00,000\nEMI : ₹ 34,713\nOutstanding Balance : ₹ 36,12,340.00")
        self.assertEqual((details["principal"], details["emi"], details["remaining_balance"]), (Decimal("4000000"), Decimal("34713"), Decimal("3612340.00")))
