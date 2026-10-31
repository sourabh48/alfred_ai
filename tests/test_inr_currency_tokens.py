"""The system reads a rupee amount however it is written: symbol, code or name."""
from django.test import SimpleTestCase

from alfred_ai.services.document_extraction import MONEY_RE, _build_field_candidates
from apps.career.services.job_intelligence import JobIntelligenceService
from apps.expenses.services.statement_import import _extract_loan_hints
from apps.integrations.services.credit_report_parser import CreditReportParser, MONEY_PATTERN
from apps.investments.services.portfolio_intelligence import PortfolioIntelligenceService
from apps.loans.services.loan_closure_parser import LoanClosureParser
from apps.loans.services.loan_pdf_parser import LoanPDFParser
from apps.ml_engine.services.memory_reasoning import public_payload
from apps.mobility.services.bike_document_ai import MONEY_RE as BIKE_MONEY_RE, NUMERIC_TOKEN_RE
from apps.mobility.services.travel_conversation import extract
from apps.mobility.services.travel_discovery import value

PREFIXED = ("₹12,500.00", "₹ 12,500.00", "₨ 12,500.00", "Rs 12,500.00", "Rs. 12,500.00", "RS.12,500.00", "Rs/- 12,500.00", "INR 12,500.00", "Rupees 12,500.00", "rupee 12,500.00", "â‚¹12,500.00")
SUFFIXED = ("12,500.00 rupees", "12,500.00 INR", "12,500.00 Rs", "Rs. 12,500.00/-")
GENERIC_FORMS = PREFIXED + SUFFIXED
# A bare "/-" says rupees only beside a label; anywhere else it also ends other currencies and references.
ALL_FORMS = GENERIC_FORMS + ("12,500.00/-",)
NOT_RUPEES = ("USD 500/-", "$12,500/-", "EUR 500", "RS-232", "Ref 45/-", "INV12500/-", "12.345 rs", "Rs.-5,000", "$12,500 rupees", "Mirrors 500")


class InrAmountTests(SimpleTestCase):
    def test_statement_loan_hint(self):
        for form in ALL_FORMS:
            with self.subTest(form=form):
                self.assertEqual(_extract_loan_hints(f"EMI Amount: {form}")["emi_amount"], 12500.0)

    def test_loan_pdf_amounts(self):
        parser = LoanPDFParser()
        for form in ALL_FORMS:
            with self.subTest(form=form):
                self.assertEqual(parser._extract_principal(f"Loan Amount: {form}"), 12500.0)
                self.assertEqual(parser._extract_emi(f"EMI Amount: {form}"), 12500.0)
                self.assertEqual(parser._extract_outstanding(f"Outstanding Amount: {form}"), 12500.0)

    def test_loan_closure_amounts(self):
        parser = LoanClosureParser()
        for form in ALL_FORMS:
            with self.subTest(form=form):
                self.assertEqual(parser._extract_total_amount(f"Foreclosure Amount: {form}"), 12500.0)
                self.assertEqual(parser._extract_amount_for_labels(f"Penalty: {form}", ["Penalty"]), 12500.0)

    def test_credit_report_amounts_including_tradeline_rows(self):
        parser = CreditReportParser()
        for form in ALL_FORMS:
            with self.subTest(form=form):
                self.assertEqual(parser._extract_amount(f"Current Balance: {form}", ["Current Balance"]), 12500.0)
                self.assertEqual(parser._extract_optional_amount_from_line(f"Current Balance: {form}", ["Current Balance"]), 12500.0)
        for form in GENERIC_FORMS:
            with self.subTest(form=form):
                self.assertEqual(float(MONEY_PATTERN.search(f"Owed {form} today").group(1).replace(",", "")), 12500.0)

    def test_a_currency_name_touching_its_label_still_counts(self):
        self.assertEqual(LoanPDFParser()._extract_principal("Loan AmountRs.5,00,000"), 500000.0)
        self.assertEqual(_extract_loan_hints("EMI AmountINR 12,500.00")["emi_amount"], 12500.0)

    def test_bike_document_amounts(self):
        for form in GENERIC_FORMS:
            with self.subTest(form=form):
                self.assertEqual(float(BIKE_MONEY_RE.search(f"Total {form}").group(1).replace(",", "")), 12500.0)
        self.assertEqual(BIKE_MONEY_RE.search("Amount in Rupees, Total Rs 500").group(1), "500")
        self.assertEqual(NUMERIC_TOKEN_RE.match("12,500.00/-").group(1), "12,500.00")

    def test_document_review_offers_the_amount(self):
        for form in GENERIC_FORMS:
            with self.subTest(form=form):
                values = [item["value"] for item in _build_field_candidates(f"Paid {form} today") if item["field_type"] == "amount"]
                self.assertTrue(values)
                self.assertIn("12,500.00", values[0])

    def test_a_bare_number_or_a_word_ending_in_rs_is_not_money(self):
        for text in ("Invoice 12500", "Worked 40 hours 12500", "Page 3 of 12", "Mirrors 500"):
            with self.subTest(text=text):
                self.assertIsNone(MONEY_RE.search(text))
                self.assertIsNone(MONEY_PATTERN.search(text))

    def test_other_currencies_and_references_are_not_read_as_rupees(self):
        for text in NOT_RUPEES:
            with self.subTest(text=text):
                self.assertIsNone(MONEY_RE.search(text))
                self.assertIsNone(MONEY_PATTERN.search(text))
                self.assertIsNone(BIKE_MONEY_RE.search(text))

    def test_a_long_digit_run_is_not_money(self):
        self.assertIsNone(MONEY_RE.search("1" * 200000))
        self.assertIsNone(MONEY_RE.search("1," * 100000))

    def test_travel_budget(self):
        for text in ("₹12000", "rs 12000", "Rs. 12,000", "INR 12000", "rupees 12000", "12000 rupees", "12,000/-", "12000 INR"):
            with self.subTest(text=text):
                self.assertEqual(value(extract({}, text)[0], "budget"), 12000.0)
        self.assertEqual(value(extract({}, "5 thousand rupees")[0], "budget"), 5000.0)
        self.assertEqual(value(extract({}, "budget in rupees, around 5000")[0], "budget"), 5000.0)
        self.assertIsNone(value(extract({}, "stay 3 hours 20 minutes")[0], "budget"))

    def test_job_salary_text(self):
        parse = JobIntelligenceService()._parse_salary_text
        for text in ("₹50,000 per month", "Rs. 50,000 per month", "INR 50,000 per month", "Rupees 50,000 per month", "50,000 rupees per month", "50,000 Rs per month", "50,000/- per month"):
            with self.subTest(text=text):
                parsed = parse(f"Salary {text}")
                self.assertEqual(parsed["salary_min"], 50000.0)
                self.assertEqual(parsed["currency"], "INR")
        self.assertEqual(parse("Salary $50,000 per year")["currency"], "USD")

    def test_holding_names_drop_the_currency(self):
        name = PortfolioIntelligenceService()._extract_asset_name
        for form in ("₹ 5000", "Rupees 5000", "INR 5000", "Rs. 5000"):
            with self.subTest(form=form):
                self.assertEqual(name(f"Axis Bluechip Fund {form}"), "Axis Bluechip Fund")
        self.assertIn("Rupee Bond", name("HSBC Rupee Bond Fund 5000"))


class CloudBoundaryTests(SimpleTestCase):
    def test_rupee_amounts_never_leave_in_any_form(self):
        for text in ("paid ₹500", "paid ₨500", "paid € 500", "paid £500", "paid Rs. 500", "paid INR 500", "paid rupees 500", "paid 500 rupees", "paid 500 INR",
                     "paid 500 Rs", "paid 500/-", "paid Rs/- 500", "paid ₹\n500", "500\trupees"):
            with self.subTest(text=text), self.assertRaises(PermissionError):
                public_payload({"context": text})

    def test_private_words_beside_non_latin_letters_never_leave(self):
        for text in ("salaryका विवरण", "loanの情報"):
            with self.subTest(text=text), self.assertRaises(PermissionError):
                public_payload({"context": text})

    def test_a_payload_that_cannot_be_encoded_is_refused(self):
        with self.assertRaises(ValueError):
            public_payload({"context": float("nan")})

    def test_plain_public_text_still_passes(self):
        public_payload({"context": "monsoon routes near Munnar"})
