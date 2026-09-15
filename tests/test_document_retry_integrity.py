from contextlib import ExitStack
from datetime import date
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume
from apps.career.services.resume_intelligence import ParsedResume
from apps.expenses.models import StatementUpload
from apps.integrations.models import CreditReportUpload
from apps.integrations.services.credit_report_parser import ParsedCreditReport
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanImportDocument
from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord
from apps.mobility.services.bike_document_ai import ParsedDocument


class DocumentRetryIntegrityTests(TestCase):
    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = get_user_model().objects.create_user(username="retry-integrity")
        self.client.force_login(self.user)

    def _file(self):
        return SimpleUploadedFile("source.pdf", b"source for mocked parser", content_type="application/pdf")

    def _loan(self, account="LOAN-1", **fields):
        return Loan.objects.create(
            user=self.user, lender="Example Bank", loan_account_number=account,
            principal=100000, interest_rate=10, emi=5000, start_date="2026-01-01", **fields,
        )

    def _post(self, action, scope, document, **extra):
        response = self.client.post(
            f"/api/documents/review-queue/{action}/",
            {"scope": scope, "id": document.pk, **extra}, content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        document.refresh_from_db()
        return response.json()

    def test_missing_and_purged_sources_preserve_saved_evidence_in_all_file_scopes(self):
        loan = self._loan()
        models = [
            ("statement_document", StatementUpload, "original_file", {"user": self.user}),
            ("loan_document", LoanImportDocument, "uploaded_file", {"user": self.user}),
            ("loan_closure_document", LoanClosureDocument, "uploaded_file", {"loan": loan}),
            ("investment_document", InvestmentImportDocument, "uploaded_file", {"user": self.user}),
            ("vehicle_document", BikeDocument, "document_file", {"user": self.user}),
            ("resume_document", CareerResume, "uploaded_file", {"user": self.user}),
            ("credit_report", CreditReportUpload, "uploaded_file", {"user": self.user}),
        ]
        parser_paths = [
            "queue_statement_retry", "retry_statement_upload", "loan_pdf_parser.parse_document",
            "loan_closure_parser.parse_document", "portfolio_intelligence_service.parse_portfolio_document",
            "bike_document_ai.parse", "resume_intelligence.parse", "credit_report_parser.parse",
        ]
        with ExitStack() as stack:
            parsers = [stack.enter_context(patch(f"alfred_ai.services.document_review.{path}")) for path in parser_paths]
            for purged in (False, True):
                for scope, model, field, owner in models:
                    with self.subTest(scope=scope, purged=purged):
                        evidence = {
                            "accepted_corrections": {"review_note": "Checked by user"},
                            "extraction_review": {"raw_text_excerpt": "Saved OCR evidence"},
                            "raw_file_retention": {"deleted": purged},
                            "background_retry": {"retry_count": 2, "state": "needs_review"},
                        }
                        document = model.objects.create(
                            **owner, **{field: "" if purged else "missing/source.pdf"},
                            parser_status="parsed", parse_confidence=0.9, extracted_payload=evidence,
                        )
                        self._post("retry", scope, document)
                        self.assertEqual(document.parser_status, "parsed")
                        self.assertEqual(document.parse_confidence, 0.9)
                        retry = document.extracted_payload["background_retry"]
                        self.assertEqual(retry["state"], "unavailable")
                        self.assertEqual(retry["retry_count"], 2)
                        self.assertEqual(retry["resolution"], "raw_file_deleted" if purged else "source_file_missing")
                        for key in ("accepted_corrections", "extraction_review", "raw_file_retention"):
                            self.assertEqual(document.extracted_payload[key], evidence[key])
            for parser in parsers:
                parser.assert_not_called()

    def test_statement_correction_without_source_saves_fields_without_retrying(self):
        document = StatementUpload.objects.create(user=self.user, original_file="missing/source.pdf")
        with patch("alfred_ai.services.document_review.queue_statement_retry") as queue, patch(
            "alfred_ai.services.document_review.retry_statement_upload"
        ) as retry:
            self._post("resolve", "statement_document", document, corrections={"account_holder": "Verified Holder"})
        self.assertEqual(document.account_holder, "Verified Holder")
        self.assertEqual(document.extracted_payload["accepted_corrections"]["account_holder"], "Verified Holder")
        self.assertEqual(document.extracted_payload["background_retry"]["state"], "unavailable")
        queue.assert_not_called()
        retry.assert_not_called()

    def test_resume_list_corrections_survive_retry_and_reach_profile(self):
        document = CareerResume.objects.create(user=self.user, uploaded_file=self._file(), file_name="resume.pdf")
        accepted = {"role": "Backend Developer", "experience_years": 0, "skills": ["Java", "Spring Boot"]}
        self._post("resolve", "resume_document", document, corrections=accepted)
        self.assertEqual(document.extracted_payload["skills"], accepted["skills"])
        parsed = ParsedResume(
            parser_status="parsed", confidence=0.9, extracted_text="Noisy OCR",
            payload={"role": "Analyst", "experience_years": 7, "skills": ["Excel"]},
            summary="Parsed", strengths=[], weaknesses=[],
        )
        with patch("alfred_ai.services.document_review.resume_intelligence.parse", return_value=parsed):
            self._post("retry", "resume_document", document)
        for key, value in accepted.items():
            self.assertEqual(document.extracted_payload[key], value)
        profile = CareerProfile.objects.get(user=self.user)
        self.assertEqual(profile.role, accepted["role"])
        self.assertEqual(profile.skills, "Java, Spring Boot")

    def test_partial_loan_retry_keeps_other_links_and_accepted_identity(self):
        primary = self._loan()
        secondary = self._loan("LOAN-2")
        document = LoanImportDocument.objects.create(
            user=self.user, uploaded_file=self._file(), file_name="loans.pdf",
            extracted_payload={"loans": [{"lender": primary.lender, "loan_account_number": "LOAN-1"}]},
        )
        document.linked_loans.add(primary)
        self._post("resolve", "loan_document", document, corrections={"lender": "Verified Bank", "loan_account_number": "VERIFIED-1"})
        document.linked_loans.add(secondary)
        with patch("alfred_ai.services.document_review.loan_pdf_parser.parse_document", return_value={
            "document_type": "loan_statement", "confidence": 0.8, "extracted_text": "Retry evidence",
            "loans": [{"lender": "Wrong Bank", "loan_account_number": "OCR-ERROR", "principal": 100000}],
        }):
            self._post("retry", "loan_document", document)
        primary.refresh_from_db()
        self.assertEqual(primary.lender, "Verified Bank")
        self.assertEqual(primary.loan_account_number, "VERIFIED-1")
        self.assertEqual(set(document.linked_loans.values_list("pk", flat=True)), {primary.pk, secondary.pk})
        self.assertEqual(Loan.objects.filter(user=self.user).count(), 2)
        self.assertTrue(document.summary.startswith("2 loan record"))

    def test_partial_investment_retry_preserves_unextracted_fields_and_accounts(self):
        primary = Investment.objects.create(
            user=self.user, asset_name="Index Fund", asset_type="mutual_fund", institution="Broker",
            account_number="ACCOUNT-1", invested_amount=10000, current_value=12000,
            monthly_sip=500, annual_return_rate=8, risk_level="medium", notes="Keep this note",
        )
        secondary = Investment.objects.create(
            user=self.user, asset_name="Index Fund", asset_type="mutual_fund", institution="Broker",
            account_number="ACCOUNT-2", current_value=9000,
        )
        document = InvestmentImportDocument.objects.create(user=self.user, uploaded_file=self._file(), file_name="holdings.pdf")
        document.linked_investments.add(primary, secondary)
        with patch("alfred_ai.services.document_review.portfolio_intelligence_service.parse_portfolio_document", return_value={
            "broker": "Broker", "parser_status": "parsed", "confidence": 0.9,
            "investments": [{"asset_name": "Index Fund", "institution": "Broker", "account_number": "ACCOUNT-1", "current_value": 12500, "invested_amount": 0}],
            "payload": {},
        }):
            self._post("retry", "investment_document", document)
        primary.refresh_from_db()
        secondary.refresh_from_db()
        self.assertEqual(primary.current_value, 12500)
        self.assertEqual(primary.invested_amount, 10000)
        self.assertEqual(primary.monthly_sip, 500)
        self.assertEqual(primary.annual_return_rate, 8)
        self.assertEqual(primary.risk_level, "medium")
        self.assertEqual(primary.asset_type, "mutual_fund")
        self.assertEqual(primary.notes, "Keep this note")
        self.assertEqual(secondary.current_value, 9000)
        self.assertEqual(set(document.linked_investments.values_list("pk", flat=True)), {primary.pk, secondary.pk})
        self.assertTrue(document.summary.startswith("2 investment record"))

    def test_investment_correction_keeps_other_holdings_and_survives_retry(self):
        primary_data = {"asset_name": "OCR Fund", "institution": "Broker", "account_number": "ACCOUNT-1"}
        primary = Investment.objects.create(user=self.user, asset_type="mutual_fund", monthly_sip=500, **primary_data)
        secondary = Investment.objects.create(user=self.user, asset_name="Other Fund", asset_type="debt", current_value=8000)
        document = InvestmentImportDocument.objects.create(
            user=self.user, uploaded_file=self._file(), file_name="holdings.pdf", broker_name="Broker",
            extracted_payload={"investments": [primary_data]},
        )
        document.linked_investments.add(primary, secondary)
        corrections = {"asset_name": "Verified Fund", "broker_name": "Verified Broker", "current_value": 0}
        self._post("resolve", "investment_document", document, corrections=corrections)
        corrected = document.linked_investments.get(asset_name="Verified Fund")
        self.assertEqual(corrected.monthly_sip, 500)
        self.assertTrue(document.linked_investments.filter(pk=secondary.pk).exists())
        with patch("alfred_ai.services.document_review.portfolio_intelligence_service.parse_portfolio_document", return_value={
            "broker": "Wrong Broker", "parser_status": "parsed", "confidence": 0.9,
            "investments": [{**primary_data, "current_value": 99999}], "payload": {},
        }):
            self._post("retry", "investment_document", document)
        corrected.refresh_from_db()
        self.assertEqual(document.broker_name, "Verified Broker")
        self.assertEqual(corrected.current_value, 0)
        self.assertEqual(corrected.monthly_sip, 500)
        self.assertEqual(set(document.linked_investments.values_list("pk", flat=True)), {corrected.pk, secondary.pk})

    def test_vehicle_retry_keeps_reviewed_type_zero_cost_and_service_date(self):
        profile = BikeProfile.objects.create(user=self.user, display_name="Test Bike", vehicle_number="KA01AA1234")
        document = BikeDocument.objects.create(
            user=self.user, bike_profile=profile, document_file=self._file(), document_type="other", premium_amount=1800,
            extracted_payload={"accepted_corrections": {"document_type": "invoice", "cost": 0, "service_center": "Verified Workshop"}},
        )
        record = BikeServiceRecord.objects.create(
            user=self.user, bike_profile=profile, source_document=document, service_date="2026-03-20",
            cost=1800, service_center="Old Workshop",
        )
        parsed = ParsedDocument(
            document_type="insurance", title="Noisy invoice", confidence=0.8, fields={"amount": 99999},
            parser_status="parsed", parser_notes="Retry", source_text="Invoice",
            service_payload={"cost": 99999, "service_center": "Wrong Workshop"},
        )
        with patch("alfred_ai.services.document_review.bike_document_ai.parse", return_value=parsed), patch(
            "alfred_ai.services.document_review.bike_document_ai.verify_relevance",
            return_value={"accepted": True, "score": 1, "reasons": []},
        ):
            self._post("retry", "vehicle_document", document)
        record.refresh_from_db()
        self.assertEqual(document.document_type, "invoice")
        self.assertEqual(document.extracted_payload["accepted_corrections"]["document_type"], "invoice")
        self.assertEqual(document.premium_amount, 0)
        self.assertEqual(record.cost, 0)
        self.assertEqual(record.service_center, "Verified Workshop")
        self.assertEqual(record.service_date, date(2026, 3, 20))

    def test_loan_retry_targets_reviewed_row_when_extraction_reorders_or_omits_it(self):
        for omit_primary in (False, True):
            with self.subTest(omit_primary=omit_primary):
                primary = self._loan(f"PRIMARY-{omit_primary}")
                secondary = self._loan(f"SECONDARY-{omit_primary}")
                primary_data = {"lender": primary.lender, "loan_account_number": primary.loan_account_number, "principal": 100000}
                secondary_data = {"lender": secondary.lender, "loan_account_number": secondary.loan_account_number, "principal": 250000}
                document = LoanImportDocument.objects.create(
                    user=self.user, uploaded_file=self._file(), file_name="loans.pdf",
                    extracted_payload={"loans": [primary_data, secondary_data]},
                )
                document.linked_loans.add(primary, secondary)
                self._post("resolve", "loan_document", document, corrections={
                    "lender": "Verified Bank", "loan_account_number": f"VERIFIED-{omit_primary}",
                })
                primary.refresh_from_db()
                self.assertEqual(primary.loan_account_number, f"VERIFIED-{omit_primary}")
                rows = [secondary_data] if omit_primary else [secondary_data, primary_data]
                with patch("alfred_ai.services.document_review.loan_pdf_parser.parse_document", return_value={
                    "document_type": "loan_statement", "confidence": 0.8, "loans": rows,
                }):
                    self._post("retry", "loan_document", document)
                primary.refresh_from_db()
                secondary.refresh_from_db()
                self.assertEqual(primary.principal, 100000)
                self.assertEqual(primary.lender, "Verified Bank")
                self.assertEqual(secondary.principal, 250000)
                self.assertEqual(secondary.loan_account_number, secondary_data["loan_account_number"])
                self.assertEqual(secondary.lender, "Example Bank")
                self.assertEqual(document.extracted_payload["loans"][0]["loan_account_number"], primary.loan_account_number)
                self.assertEqual(set(document.linked_loans.values_list("pk", flat=True)), {primary.pk, secondary.pk})

    def test_investment_retry_targets_reviewed_row_when_extraction_reorders_or_omits_it(self):
        for omit_primary in (False, True):
            with self.subTest(omit_primary=omit_primary):
                primary_data = {"asset_name": "Primary Fund", "institution": "Broker", "account_number": f"PRIMARY-{omit_primary}"}
                secondary_data = {"asset_name": "Other Fund", "institution": "Broker", "account_number": f"SECONDARY-{omit_primary}"}
                primary = Investment.objects.create(user=self.user, asset_type="mutual_fund", current_value=10000, **primary_data)
                secondary = Investment.objects.create(user=self.user, asset_type="debt", current_value=20000, **secondary_data)
                document = InvestmentImportDocument.objects.create(
                    user=self.user, uploaded_file=self._file(), file_name="holdings.pdf", broker_name="Broker",
                    extracted_payload={"investments": [primary_data, secondary_data]},
                )
                document.linked_investments.add(primary, secondary)
                self._post("resolve", "investment_document", document, corrections={"asset_name": "Verified Fund", "current_value": 15000})
                corrected = document.linked_investments.get(asset_name="Verified Fund")
                rows = [{**secondary_data, "current_value": 25000}]
                if not omit_primary:
                    rows.append({**primary_data, "current_value": 99999})
                with patch("alfred_ai.services.document_review.portfolio_intelligence_service.parse_portfolio_document", return_value={
                    "broker": "Broker", "parser_status": "parsed", "confidence": 0.9, "investments": rows, "payload": {},
                }):
                    self._post("retry", "investment_document", document)
                corrected.refresh_from_db()
                secondary.refresh_from_db()
                self.assertEqual(corrected.current_value, 15000)
                self.assertEqual(secondary.current_value, 25000)
                self.assertEqual(secondary.asset_name, "Other Fund")
                self.assertEqual(document.extracted_payload["investments"][0]["asset_name"], "Verified Fund")
                self.assertEqual(set(document.linked_investments.values_list("pk", flat=True)), {corrected.pk, secondary.pk})

    def test_loan_closure_retry_verifies_accepted_fields(self):
        accepted = {"loan_account_number": "LOAN-1", "closure_amount": 12345, "closure_date": "2026-03-20", "matched_keyword": "no dues"}
        document = LoanClosureDocument.objects.create(
            loan=self._loan(), uploaded_file=self._file(), file_name="closure.pdf",
            extracted_payload={"accepted_corrections": accepted},
        )
        with patch("alfred_ai.services.document_review.loan_closure_parser.parse_document", return_value={
            "payload": {"loan_account_number": "WRONG", "closure_amount": 99999, "closure_date": "2026-01-01", "matched_keyword": "wrong"},
            "extracted_text": "Noisy OCR", "confidence": 0.9, "parser_status": "parsed",
        }), patch("alfred_ai.services.document_review.loan_closure_parser.verify_document", return_value=(False, "Review needed")) as verify:
            self._post("retry", "loan_closure_document", document)
        for key, value in accepted.items():
            self.assertEqual(verify.call_args.args[1]["payload"][key], value)
            self.assertEqual(document.extracted_payload[key], value)
        self.assertEqual(document.closure_amount, 12345)
        self.assertEqual(document.closure_date, date(2026, 3, 20))

    def test_credit_retry_keeps_accepted_metadata(self):
        document = CreditReportUpload.objects.create(user=self.user, uploaded_file=self._file(), file_name="credit.pdf")
        accepted = {"bureau": "CIBIL", "applicant_name": "Verified Applicant", "report_number": "VERIFIED-1", "report_date": "2026-03-20"}
        self._post("resolve", "credit_report", document, corrections=accepted)
        parsed = ParsedCreditReport(
            parser_status="parsed", confidence=0.9, bureau="EXPERIAN", extracted_text="Noisy OCR",
            payload={"applicant_name": "Wrong Applicant", "report_number": "WRONG", "report_date": "2026-01-01"},
            factors=[], summary="Parsed", parser_notes="Retry",
        )
        with patch("alfred_ai.services.document_review.credit_report_parser.parse", return_value=parsed):
            self._post("retry", "credit_report", document)
        for key, value in accepted.items():
            self.assertEqual(document.extracted_payload[key], value)
        self.assertEqual(document.bureau, "CIBIL")
        self.assertEqual(document.applicant_name, "Verified Applicant")
        self.assertEqual(document.report_number, "VERIFIED-1")
        self.assertEqual(document.report_date, date(2026, 3, 20))

    def test_recruiter_retry_keeps_accepted_fields_and_zero_experience(self):
        document = CareerJobAnalysis.objects.create(
            user=self.user, source_name="Recruiter Mail Intake",
            job_url="https://example.test/job", apply_url="https://example.test/job",
            extracted_payload={"source_kind": "recruiter_message", "intake_message_text": "Role: Analyst\nCompany: Wrong Company\nNeed 7 years experience in SQL"},
        )
        accepted = {"job_title": "Backend Developer", "company": "Verified Company", "location": "Bengaluru", "experience_years": 0, "salary_min": 1200000, "salary_max": 1800000}
        self._post("resolve", "recruiter_document", document, corrections=accepted)
        self._post("retry", "recruiter_document", document)
        self.assertEqual(document.job_title, accepted["job_title"])
        self.assertEqual(document.company, accepted["company"])
        for key in ("location", "experience_years", "salary_min", "salary_max"):
            self.assertEqual(document.extracted_payload["job_snapshot"][key], accepted[key])
