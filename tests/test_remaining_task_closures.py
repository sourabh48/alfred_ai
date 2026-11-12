from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.investments.models import Investment
from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service
from apps.loans.models import Loan, LoanPaymentHistory
from apps.ml_engine.continual.drift_monitor import drift_monitor
from apps.ml_engine.core.alfred_inference import alfred_engine
from apps.ml_engine.services.tax_optimizer import tax_optimizer


class DriftMonitorTests(SimpleTestCase):
    def test_detect_returns_stable_score_for_similar_numeric_distribution(self):
        score = drift_monitor.detect([100, 105, 110, 115, 120], [101, 106, 111, 116, 121])

        self.assertLess(score, 0.1)
        self.assertEqual(drift_monitor.level(score), "stable")

    def test_detect_flags_material_categorical_distribution_shift(self):
        score = drift_monitor.detect(
            {"food": 80, "shopping": 10, "fuel": 10},
            {"food": 10, "shopping": 80, "fuel": 10},
        )

        self.assertGreaterEqual(score, 0.25)
        self.assertEqual(drift_monitor.level(score), "material")
        self.assertTrue(drift_monitor.explain(["food"] * 10, ["shopping"] * 10)["review_required"])


class EmotionalSpendFallbackTests(SimpleTestCase):
    def test_fallback_emotional_spend_uses_local_impulse_signals(self):
        result = alfred_engine.predict_emotional_spend(
            {
                "amount": 6200,
                "category": "shopping",
                "description": "Flash sale premium sneaker limited offer",
            }
        )

        self.assertTrue(result["is_emotional"])
        self.assertGreaterEqual(result["confidence"], 0.65)
        self.assertIn("description contains impulse-spend language", result["reason"])

    def test_fallback_emotional_spend_keeps_planned_payments_non_emotional(self):
        result = alfred_engine.predict_emotional_spend(
            {
                "amount": 38000,
                "category": "loan",
                "description": "Home loan EMI payment",
            }
        )

        self.assertFalse(result["is_emotional"])
        self.assertIn("planned-payment", result["reason"])


class TaxDeductionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tax-deduction-user",
            password="Pass12345!",
            monthly_income=120000,
        )

    def test_current_deductions_use_recorded_home_loan_payment_components(self):
        Investment.objects.create(
            user=self.user,
            asset_type="mutual_fund",
            asset_name="ELSS Growth Fund",
            institution="Test AMC",
            current_value=30000,
        )
        loan = Loan.objects.create(
            user=self.user,
            loan_type="home",
            lender="SBI",
            principal=4000000,
            interest_rate=8.5,
            emi=36500,
            tenure_months=240,
            remaining_balance=3900000,
            start_date=date(2026, 4, 1),
        )
        LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=date(2026, 9, 10),
            amount=36500,
            principal_component=60000,
            interest_component=90000,
            match_status="matched",
        )
        LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=date(2026, 9, 11),
            amount=36500,
            principal_component=100000,
            interest_component=100000,
            match_status="rejected",
        )

        deductions = tax_optimizer._calculate_current_deductions(self.user)

        self.assertEqual(deductions["80C"], 90000)
        self.assertEqual(deductions["24B"], 90000)


class InvestmentEmailImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="investment-email-user",
            password="Pass12345!",
        )

