from datetime import date, timedelta
from pathlib import Path
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.budgets.models import Budget
from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume, CareerResumeLearningMemory
from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.family.models import Dependent
from apps.integrations.models import CreditReportUpload, CreditScore, VerifiedExternalInsight
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument
from apps.ml_engine.models.parser_memory import DocumentParserLearningMemory
from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord, TravelPlan, TripPhoto
from apps.relationship.models import RelationshipProfile
from apps.reports.models import ChatGPTImport, GeneratedReport, OperationalLog, SystemTicket
from apps.risk.models import RiskSignal


class UserDataResetApiTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="alfred-test-media-")
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)

        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="reset_user",
            password="Pass12345!",
            monthly_income=95000,
            variable_income=12000,
            rent_or_emi=31000,
            city="Bengaluru",
            country="India",
        )
        self.other_user = user_model.objects.create_user(username="other_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_clear_user_data_resets_only_current_user_records(self):
        self._seed_current_user_data()
        self._seed_other_user_data()

        response = self.client.post("/api/users/profile/clear-data/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["deleted"]["account_preserved"])
        self.assertTrue(payload["deleted"]["profile_fields_reset"])
        self.assertTrue(payload["deleted"]["materialized_caches_cleared"])

        self.user.refresh_from_db()
        self.assertEqual(self.user.monthly_income, 0)
        self.assertEqual(self.user.variable_income, 0)
        self.assertEqual(self.user.rent_or_emi, 0)
        self.assertEqual(self.user.city, "")
        self.assertEqual(self.user.country, "")

        self.assertEqual(CareerProfile.objects.filter(user=self.user).count(), 0)
        self.assertEqual(CareerResume.objects.filter(user=self.user).count(), 0)
        self.assertEqual(CareerJobAnalysis.objects.filter(user=self.user).count(), 0)
        self.assertEqual(CareerResumeLearningMemory.objects.filter(user=self.user).count(), 0)
        self.assertEqual(BankAccount.objects.filter(user=self.user).count(), 0)
        self.assertEqual(StatementUpload.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Loan.objects.filter(user=self.user).count(), 0)
        self.assertEqual(LoanClosureDocument.objects.filter(loan__user=self.user).count(), 0)
        self.assertEqual(LoanForeclosureSnapshot.objects.filter(loan__user=self.user).count(), 0)
        self.assertEqual(LoanImportDocument.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Investment.objects.filter(user=self.user).count(), 0)
        self.assertEqual(InvestmentImportDocument.objects.filter(user=self.user).count(), 0)
        self.assertEqual(BikeProfile.objects.filter(user=self.user).count(), 0)
        self.assertEqual(BikeDocument.objects.filter(user=self.user).count(), 0)
        self.assertEqual(BikeServiceRecord.objects.filter(user=self.user).count(), 0)
        self.assertEqual(TravelPlan.objects.filter(user=self.user).count(), 0)
        self.assertEqual(TripPhoto.objects.filter(user=self.user).count(), 0)
        self.assertEqual(CreditScore.objects.filter(user=self.user).count(), 0)
        self.assertEqual(CreditReportUpload.objects.filter(user=self.user).count(), 0)
        self.assertEqual(BehavioralSignal.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Budget.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Dependent.objects.filter(user=self.user).count(), 0)
        self.assertEqual(RelationshipProfile.objects.filter(user=self.user).count(), 0)
        self.assertEqual(RiskSignal.objects.filter(user=self.user).count(), 0)
        self.assertEqual(SystemTicket.objects.filter(user=self.user).count(), 0)
        self.assertEqual(OperationalLog.objects.filter(user=self.user).count(), 0)
        self.assertEqual(ChatGPTImport.objects.filter(user=self.user).count(), 0)
        self.assertEqual(DocumentParserLearningMemory.objects.filter(user=self.user).count(), 0)
        self.assertEqual(GeneratedReport.objects.filter(user=self.user).count(), 0)
        self.assertEqual(VerifiedExternalInsight.objects.filter(user=self.user).count(), 0)

        self.assertEqual(BankAccount.objects.filter(user=self.other_user).count(), 1)
        self.assertEqual(CareerResume.objects.filter(user=self.other_user).count(), 1)

        for path in self.current_user_file_paths:
            self.assertFalse(path.exists(), msg=f"Expected deleted file at {path}")
        self.assertFalse(self.generated_report_path.exists())

    def test_clear_user_data_invalidates_materialized_financial_cache(self):
        self._seed_current_user_data()
        intelligence = build_financial_intelligence(self.user)
        cache_key = intelligence["_materialized"]["cache_key"]

        self.assertIsNotNone(cache.get(cache_key))

        response = self.client.post("/api/users/profile/clear-data/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(cache.get(cache_key))

    def test_clear_user_data_allows_fresh_new_records_after_reset(self):
        self._seed_current_user_data()

        response = self.client.post("/api/users/profile/clear-data/", data={}, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("start fresh", response.json()["detail"])

        account = BankAccount.objects.create(
            user=self.user,
            bank_name="ICICI",
            account_number="4455667788",
            account_type="savings",
            current_balance=25000,
        )
        expense = Expense.objects.create(
            user=self.user,
            bank_account=account,
            amount=875,
            classification="expense",
            category="food",
            merchant="Fresh Start Cafe",
            transaction_date=date.today(),
        )

        self.assertEqual(BankAccount.objects.filter(user=self.user).count(), 1)
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 1)
        self.assertEqual(expense.merchant, "Fresh Start Cafe")

    def _seed_current_user_data(self):
        CareerProfile.objects.create(user=self.user, role="Backend Engineer", experience_years=5, skills="Python, Django", last_salary=95000)
        resume = CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.pdf", b"resume-data", content_type="application/pdf"),
            file_name="resume.pdf",
            parser_status="parsed",
            parse_confidence=0.95,
            extracted_text="resume text",
            extracted_payload={"role": "Backend Engineer"},
            summary="parsed",
        )
        CareerJobAnalysis.objects.create(user=self.user, job_url="https://example.com/job", fit_score=72, market_risk_score=33)
        CareerResumeLearningMemory.objects.create(user=self.user, file_extension=".pdf", role_hint="backend", skill_signature="python")

        bank_account = BankAccount.objects.create(
            user=self.user,
            bank_name="HDFC",
            account_number="1234567890",
            account_type="savings",
            current_balance=50000,
        )
        statement = StatementUpload.objects.create(
            user=self.user,
            bank_account=bank_account,
            source="bank_statement",
            original_file=SimpleUploadedFile("statement.pdf", b"statement-data", content_type="application/pdf"),
            file_name="statement.pdf",
            parser_status="parsed",
            parse_confidence=0.91,
        )
        Expense.objects.create(
            user=self.user,
            bank_account=bank_account,
            statement_upload=statement,
            amount=1200,
            merchant="Cafe",
            transaction_date=date.today(),
        )

        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            principal=200000,
            interest_rate=12,
            emi=8500,
            tenure_months=36,
            remaining_balance=150000,
            start_date=date(2025, 1, 1),
        )
        closure = LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure.pdf", b"closure-data", content_type="application/pdf"),
            file_name="closure.pdf",
            parser_status="parsed",
            parse_confidence=0.88,
            closure_amount=151000,
        )
        LoanForeclosureSnapshot.objects.create(
            loan=loan,
            closure_document=closure,
            document_type="closure_letter",
            total_amount_payable=151000,
            classification_confidence=0.85,
            linkage_confidence=0.82,
        )
        LoanImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("loan-import.pdf", b"loan-import", content_type="application/pdf"),
            file_name="loan-import.pdf",
            parser_status="parsed",
            parse_confidence=0.77,
        )

        Investment.objects.create(user=self.user, asset_type="equity", asset_name="Index Fund", invested_amount=50000, current_value=52000)
        InvestmentImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("investment.pdf", b"investment-data", content_type="application/pdf"),
            file_name="investment.pdf",
            parser_status="parsed",
            parse_confidence=0.79,
        )

        bike_profile = BikeProfile.objects.create(user=self.user, display_name="Hunter 350", model_name="Hunter 350")
        BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=bike_profile,
            bike_name="Hunter 350",
            service_date=date.today(),
            cost=2300,
        )
        BikeDocument.objects.create(
            user=self.user,
            bike_profile=bike_profile,
            bike_name="Hunter 350",
            document_type="insurance",
            document_file=SimpleUploadedFile("insurance.pdf", b"insurance-data", content_type="application/pdf"),
        )
        travel_plan = TravelPlan.objects.create(
            user=self.user,
            vehicle_profile=bike_profile,
            title="Weekend Ride",
            destination="Mysuru",
            start_date=date.today(),
            end_date=date.today(),
            budget=5000,
        )
        TripPhoto.objects.create(
            user=self.user,
            travel_plan=travel_plan,
            image=SimpleUploadedFile("trip.jpg", b"trip-photo", content_type="image/jpeg"),
        )

        credit_score = CreditScore.objects.create(
            user=self.user,
            bureau="CIBIL",
            score_kind="official",
            score=782,
            rating="Good",
            valid_until=timezone.now() + timedelta(days=30),
        )
        CreditReportUpload.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("cibil.pdf", b"credit-data", content_type="application/pdf"),
            file_name="cibil.pdf",
            bureau="CIBIL",
            parser_status="parsed",
            parse_confidence=0.96,
            parsed_credit_score=credit_score,
        )
        VerifiedExternalInsight.objects.create(
            user=self.user,
            scope="career",
            cache_key="career:role",
            title="Role signal",
            source_name="Source",
            source_url="https://example.com/source",
            stale_after=timezone.now() + timedelta(days=1),
        )

        BehavioralSignal.objects.create(user=self.user, stress_score=42)
        Budget.objects.create(user=self.user, month="2026-04", base_budget=25000, inflation_adjusted=26000)
        Dependent.objects.create(user=self.user, name="Parent", age=58, relation="father")
        RelationshipProfile.objects.create(user=self.user, partner_name="A", partner_financial_score=70)
        RiskSignal.objects.create(user=self.user, layoff_risk=25)
        SystemTicket.objects.create(user=self.user, module="career", title="Sample", summary="sample")
        OperationalLog.objects.create(user=self.user, module="career", event_type="resume_saved", message="saved")
        ChatGPTImport.objects.create(user=self.user, title="Dashboard import", raw_text="Vehicle service chat")
        DocumentParserLearningMemory.objects.create(user=self.user, scope="resume_document", file_extension=".pdf")

        self.generated_report_path = Path(self.media_root) / "generated-report.txt"
        self.generated_report_path.write_text("report")
        GeneratedReport.objects.create(user=self.user, file_path=str(self.generated_report_path))

        self.current_user_file_paths = [
            Path(resume.uploaded_file.path),
            Path(statement.original_file.path),
            Path(closure.uploaded_file.path),
            Path(LoanImportDocument.objects.filter(user=self.user).first().uploaded_file.path),
            Path(InvestmentImportDocument.objects.filter(user=self.user).first().uploaded_file.path),
            Path(BikeDocument.objects.filter(user=self.user).first().document_file.path),
            Path(TripPhoto.objects.filter(user=self.user).first().image.path),
            Path(CreditReportUpload.objects.filter(user=self.user).first().uploaded_file.path),
        ]

    def _seed_other_user_data(self):
        CareerResume.objects.create(
            user=self.other_user,
            uploaded_file=SimpleUploadedFile("other-resume.pdf", b"resume-data", content_type="application/pdf"),
            file_name="other-resume.pdf",
        )
        BankAccount.objects.create(
            user=self.other_user,
            bank_name="ICICI",
            account_number="9988776655",
            account_type="savings",
        )
