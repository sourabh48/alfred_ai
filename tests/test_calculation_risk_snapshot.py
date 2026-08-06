from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from alfred_ai.project_details import project_details_payload
from alfred_ai.services.calculation_risk import calculation_risk_snapshot
from apps.career.models import CareerJobAnalysis, CareerResume
from apps.expenses.models import Expense, StatementUpload
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.integrations.models import CreditReportUpload, VerifiedExternalInsight
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanImportDocument, LoanPaymentHistory
from apps.mobility.models import BikeDocument, BikeIssueReport, BikeProfile
from apps.reports.models import OperationalLog


def _guardrails(**refresh_overrides) -> dict:
    refresh_health = {
        "watchlist_records": 0,
        "fresh_records": 0,
        "active_records": 0,
        "due_records": 0,
        "scheduled_candidate_records": 0,
        "scheduled_refresh_batch_size": 40,
        "capacity_gap_records": 0,
        "scheduled_refresh_healthy": True,
        "healthy": True,
        "summary": "0 active evidence record(s) are fresh; scheduled refresh healthy.",
    }
    refresh_health.update(refresh_overrides)
    return {
        "proof_contract": {
            "surface_count": 1,
            "covered_surface_count": 1,
            "healthy": True,
            "scheduled_refresh": "refresh_due_records",
        },
        "refresh_health": refresh_health,
        "refresh_proof": {"accepted": True, "state": "accepted", "path": "artifacts/evidence_refresh.json"},
        "refresh_batch_size": 40,
    }


def _training_snapshot() -> dict:
    return {
        "overall_progress": 75.9,
        "summary": "6/7 production-ready model states are fresh and ready; one salary-dependent learner is still gated.",
        "total_models": 8,
        "ready_models": 6,
        "fresh_models": 6,
        "skipped_models": 1,
        "failed_models": 0,
        "training_models": 0,
        "trainable_models": 7,
        "supervised_ready_models": 6,
        "supervised_fresh_models": 6,
        "supervised_skipped_models": 1,
        "planned_models": 1,
        "supervised_training_progress": 86.0,
        "average_confidence": 58.5,
        "maturity": {},
        "models": [],
    }


class CalculationRiskSnapshotTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="calc_user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(
            username="calc_admin",
            password="Pass12345!",
            email="calc-admin@example.com",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        cache.clear()

    def _loan(self, **overrides) -> Loan:
        payload = {
            "user": self.user,
            "loan_type": "personal",
            "lender": "Axis Bank",
            "loan_account_number": "AXIS-CALC-1",
            "principal": 150000,
            "interest_rate": 12,
            "emi": 5200,
            "tenure_months": 36,
            "remaining_balance": 120000,
            "start_date": timezone.localdate() - timedelta(days=120),
        }
        payload.update(overrides)
        return Loan.objects.create(**payload)

    def test_loan_repayment_review_gate_and_cash_flow_aggregation_are_reported(self):
        statement = StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="needs-review.pdf",
            parser_status="needs_review",
            parse_confidence=0.52,
        )
        salary = Expense.objects.create(
            user=self.user,
            statement_upload=statement,
            amount=90000,
            classification="other",
            category="income",
            direction="credit",
            transaction_date=timezone.localdate(),
            source="bank_statement",
        )
        emi = Expense.objects.create(
            user=self.user,
            statement_upload=statement,
            amount=5200,
            classification="loan",
            category="loan",
            direction="debit",
            transaction_date=timezone.localdate(),
            source="bank_statement",
        )
        loan = self._loan()
        LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=timezone.localdate(),
            amount=emi.amount,
            principal_component=4200,
            interest_component=1000,
            match_status="review",
            expense_reference=emi,
        )

        snapshot = calculation_risk_snapshot(guardrails=_guardrails())
        queues = {item["key"]: item for item in snapshot["manual_review_queues"]}
        review_gated = {item["key"]: item for item in snapshot["review_gated_calculations"]}
        verified = {item["key"]: item for item in snapshot["verified_calculations"]}

        self.assertEqual(queues["loan_repayment_review"]["count"], 1)
        self.assertEqual(queues["statement_transaction_review"]["count"], 2)
        self.assertEqual(review_gated["loan_repayment_components"]["status"], "review_gated")
        self.assertEqual(verified["cash_flow_aggregation"]["status"], "verified_formula_review_gated_data")
        self.assertLess(snapshot["critical_path_progress"]["cash_flow"], 94)
        self.assertIn("loan repayment import", " ".join(snapshot["blockers"]))
        self.assertIsInstance(snapshot["overall_progress"], int)
        self.assertGreaterEqual(snapshot["overall_progress"], 0)
        self.assertLessEqual(snapshot["overall_progress"], 100)
        self.assertEqual(salary.direction, "credit")

    def test_net_worth_vehicle_treatment_and_actual_cost_gate_are_reported(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Custom Scooter",
            make="Custom",
            model_name="Long Tail 125",
            vehicle_type="scooter",
            usage_pattern="personal",
            estimated_market_value=72000,
            verification_status="custom",
        )
        BikeIssueReport.objects.create(
            user=self.user,
            bike_profile=profile,
            title="Brake noise",
            system="brakes",
            severity="medium",
            status="pending",
            symptom="Brake squeal under load",
            projected_cost=2600,
        )

        snapshot = calculation_risk_snapshot(guardrails=_guardrails())
        heuristic = {item["key"]: item for item in snapshot["heuristic_calculations"]}
        verified = {item["key"]: item for item in snapshot["verified_calculations"]}

        self.assertEqual(heuristic["vehicle_valuation_treatment"]["status"], "heuristic")
        self.assertEqual(snapshot["critical_path_progress"]["vehicle_valuation"], 72)
        self.assertEqual(snapshot["critical_path_progress"]["net_worth"], 76)
        self.assertIn("vehicle market value", " ".join(snapshot["blockers"]))
        self.assertIn("actual-cost outcome", " ".join(snapshot["blockers"]))
        self.assertEqual(verified["net_worth_balance_sheet"]["status"], "verified_formula_with_vehicle_caveat")

    def test_investment_growth_assumptions_and_salary_projection_fallback_are_reported(self):
        Investment.objects.create(
            user=self.user,
            asset_type="mutual_fund",
            asset_name="Index Fund",
            invested_amount=100000,
            current_value=112000,
            monthly_sip=5000,
            annual_return_rate=12,
        )

        snapshot = calculation_risk_snapshot(guardrails=_guardrails())
        heuristic = {item["key"]: item for item in snapshot["heuristic_calculations"]}

        self.assertEqual(heuristic["investment_growth_projection"]["status"], "heuristic_assumption")
        self.assertTrue(any("annual_return_rate" in item for item in heuristic["investment_growth_projection"]["evidence"]))
        self.assertEqual(heuristic["career_salary_projection"]["status"], "heuristic_fallback")
        self.assertIn("salary predictor is not fresh and ready", " ".join(snapshot["blockers"]))
        self.assertEqual(snapshot["salary_outcome_summary"]["maturity_status"], "not_started")

    def test_stale_evidence_marks_external_data_sensitive_calculations(self):
        now = timezone.now()
        VerifiedExternalInsight.objects.create(
            scope="macro",
            cache_key="macro:india",
            title="Macro Snapshot",
            source_name="World Bank",
            source_url="https://example.com/macro",
            query="macro",
            summary="Stale macro data",
            payload={"inflation": 6.1},
            checksum="stale-macro",
            status="fresh",
            fetched_at=now - timedelta(days=3),
            verified_at=now - timedelta(days=3),
            stale_after=now - timedelta(hours=1),
            is_active=True,
        )

        snapshot = calculation_risk_snapshot(
            guardrails=_guardrails(
                watchlist_records=1,
                due_records=1,
                scheduled_refresh_healthy=False,
                healthy=False,
            )
        )
        external = {item["key"]: item for item in snapshot["external_data_sensitive_calculations"]}

        self.assertEqual(snapshot["external_data_health"]["stale_or_due_records"], 1)
        self.assertFalse(snapshot["external_data_health"]["scheduled_refresh_healthy"])
        self.assertEqual(external["risk_outlook_external_context"]["status"], "stale_or_due")
        self.assertLess(snapshot["critical_path_progress"]["risk_outlook"], 82)
        self.assertIn("external-data-sensitive", " ".join(snapshot["blockers"]))

    def test_document_import_review_queues_cover_all_required_families(self):
        statement = StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="statement.pdf",
            parser_status="needs_review",
        )
        loan = self._loan()
        LoanImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("loan.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="loan.pdf",
            parser_status="needs_review",
        )
        LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="closure.pdf",
            parser_status="needs_review",
            verification_status="pending",
        )
        InvestmentImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("investment.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="investment.pdf",
            parser_status="needs_review",
        )
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Vehicle",
            model_name="Vehicle",
            vehicle_type="motorcycle",
        )
        BikeDocument.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name="Vehicle",
            document_type="invoice",
            parser_status="needs_review",
        )
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="resume.pdf",
            parser_status="needs_review",
        )
        CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="Recruiter Mail Intake",
            job_url="https://example.com/job",
            parser_status="needs_review",
        )
        CreditReportUpload.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("credit.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="credit.pdf",
            parser_status="needs_review",
        )

        snapshot = calculation_risk_snapshot(guardrails=_guardrails())
        queues = {item["key"]: item for item in snapshot["manual_review_queues"]}
        review_gated = {item["key"]: item for item in snapshot["review_gated_calculations"]}

        self.assertEqual(statement.parser_status, "needs_review")
        self.assertEqual(queues["statement_import_review"]["count"], 1)
        self.assertEqual(queues["loan_import_review"]["count"], 1)
        self.assertEqual(queues["loan_closure_review"]["count"], 1)
        self.assertEqual(queues["investment_import_review"]["count"], 1)
        self.assertEqual(queues["vehicle_import_review"]["count"], 1)
        self.assertEqual(queues["resume_import_review"]["count"], 1)
        self.assertEqual(queues["recruiter_import_review"]["count"], 1)
        self.assertEqual(queues["credit_report_review"]["count"], 1)
        self.assertEqual(snapshot["document_review_count"], 8)
        self.assertEqual(review_gated["document_derived_imports"]["status"], "review_gated")
        self.assertEqual(snapshot["critical_path_progress"]["document_derived_imports"], 66)

    @patch("alfred_ai.project_details.training_health_snapshot", return_value=_training_snapshot())
    def test_project_details_surfaces_calculation_risk_without_claiming_maturity(self, _training):
        loan = self._loan()
        LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=timezone.localdate(),
            amount=5200,
            principal_component=4200,
            interest_component=1000,
            match_status="review",
        )

        payload = project_details_payload(_guardrails())
        calculation_risk = payload["calculation_risk"]
        summary_card = next(item for item in payload["summary_cards"] if item["label"] == "Calculation Maturity")
        metric = next(item for item in payload["operational_metrics"] if item["label"] == "Calculation Maturity")

        self.assertEqual(summary_card["value"], f"{calculation_risk['overall_progress']}%")
        self.assertEqual(metric["value"], f"{calculation_risk['overall_progress']}%")
        self.assertIn("review-gated", metric["copy"])
        self.assertIn("calculation review queues", " ".join(payload["next_steps"]))
        self.assertTrue(
            any("Calculation-critical paths are audited separately" in item for item in payload["hardening_decisions"])
        )
        self.assertTrue(any("Calculation maturity is" in item for item in payload["risks"]))
        self.assertNotEqual(calculation_risk["maturity_status"], "verified_current_scope")
        for value in calculation_risk["critical_path_progress"].values():
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)

    def test_accepting_review_payment_moves_debt_gate_and_represents_components(self):
        loan = self._loan(remaining_balance=100000, total_paid=0)
        expense = Expense.objects.create(
            user=self.user,
            amount=5200,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank EMI",
            raw_description="AXIS BANK EMI",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="AXIS-EMI-1",
        )
        payment = LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=expense.transaction_date,
            amount=5200,
            principal_component=4200,
            interest_component=1000,
            principal_paid=4200,
            interest_paid=1000,
            remaining_balance=95800,
            detection_confidence=62,
            detection_reason="Low-confidence statement match.",
            matched_reference=expense.external_reference,
            match_status="review",
            loan_effect_applied=False,
            expense_reference=expense,
        )

        before = calculation_risk_snapshot(guardrails=_guardrails())
        self.assertEqual(before["critical_path_progress"]["debt_and_repayment_status"], 68)
        self.assertEqual(
            build_financial_intelligence(self.user)["loan_portfolio"]["payment_component_totals"]["principal_paid"],
            0.0,
        )

        response = self.client.post(
            f"/api/loans/payment-history/{payment.id}/review/",
            data={"decision": "accept", "notes": "Statement amount and lender verified."},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        loan.refresh_from_db()
        cache.clear()
        after = calculation_risk_snapshot(guardrails=_guardrails())
        summary = build_financial_intelligence(self.user)

        self.assertEqual(payment.match_status, "matched")
        self.assertTrue(payment.loan_effect_applied)
        self.assertEqual(round(loan.remaining_balance, 2), 95800.0)
        self.assertEqual(round(loan.total_paid, 2), 5200.0)
        self.assertEqual(after["manual_review_queue_count"], 0)
        self.assertEqual(after["critical_path_progress"]["debt_and_repayment_status"], 90)
        self.assertGreater(after["overall_progress"], before["overall_progress"])
        self.assertEqual(summary["loan_portfolio"]["payment_component_totals"]["principal_paid"], 4200.0)
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="loan_payment_review",
                event_type="loan_payment_review_accepted",
            ).exists()
        )

    def test_rejecting_legacy_applied_payment_reverses_effect_and_unreviewed_rows_remain_gated(self):
        loan = self._loan(remaining_balance=90000, total_paid=6000, last_payment_date=timezone.localdate())
        rejected_expense = Expense.objects.create(
            user=self.user,
            amount=6000,
            classification="loan",
            category="loan",
            merchant="Wrong Merchant",
            description="False loan match",
            raw_description="FALSE LOAN MATCH",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="FALSE-1",
        )
        pending_expense = Expense.objects.create(
            user=self.user,
            amount=5200,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Another low confidence EMI",
            raw_description="AXIS EMI",
            transaction_date=timezone.localdate() + timedelta(days=1),
            direction="debit",
            source="bank_statement",
            external_reference="AXIS-REVIEW-2",
        )
        rejected_payment = LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=rejected_expense.transaction_date,
            amount=6000,
            principal_component=4000,
            interest_component=2000,
            principal_paid=4000,
            interest_paid=2000,
            remaining_balance=90000,
            detection_confidence=55,
            detection_reason="Weak lender-token match.",
            matched_reference=rejected_expense.external_reference,
            match_status="review",
            loan_effect_applied=True,
            expense_reference=rejected_expense,
        )
        pending_payment = LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=pending_expense.transaction_date,
            amount=5200,
            principal_component=4200,
            interest_component=1000,
            principal_paid=4200,
            interest_paid=1000,
            remaining_balance=85800,
            detection_confidence=62,
            detection_reason="Still pending review.",
            matched_reference=pending_expense.external_reference,
            match_status="review",
            loan_effect_applied=False,
            expense_reference=pending_expense,
        )

        response = self.client.post(
            f"/api/loans/payment-history/{rejected_payment.id}/review/",
            data={"decision": "reject", "notes": "Merchant was not lender."},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        rejected_payment.refresh_from_db()
        pending_payment.refresh_from_db()
        loan.refresh_from_db()
        cache.clear()
        snapshot = calculation_risk_snapshot(guardrails=_guardrails())
        summary = build_financial_intelligence(self.user)

        self.assertEqual(rejected_payment.match_status, "rejected")
        self.assertFalse(rejected_payment.loan_effect_applied)
        self.assertEqual(pending_payment.match_status, "review")
        self.assertEqual(round(loan.remaining_balance, 2), 94000.0)
        self.assertEqual(round(loan.total_paid, 2), 0.0)
        self.assertEqual(snapshot["manual_review_queue_count"], 1)
        self.assertEqual(snapshot["critical_path_progress"]["debt_and_repayment_status"], 68)
        self.assertEqual(summary["loan_portfolio"]["payment_component_totals"]["principal_paid"], 0.0)
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="loan_payment_review",
                event_type="loan_payment_review_rejected",
            ).exists()
        )
