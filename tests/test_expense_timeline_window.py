from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.expenses.models import Expense


class ExpenseTimelineWindowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="expense_window_user",
            password="Pass12345!",
        )
        self.client = Client()
        self.client.force_login(self.user)

        Expense.objects.create(
            user=self.user,
            amount=1000,
            classification="expense",
            category="food",
            payment_mode="UPI",
            merchant="Swiggy",
            description="Comfort dinner",
            raw_description="Comfort dinner",
            transaction_date=date(2026, 2, 5),
            direction="debit",
            source="manual",
            is_emotional=True,
            model_confidence=0.86,
        )
        Expense.objects.create(
            user=self.user,
            amount=4000,
            classification="expense",
            category="shopping",
            payment_mode="CARD",
            merchant="Myntra",
            description="Sale purchase",
            raw_description="Sale purchase",
            transaction_date=date(2026, 3, 10),
            direction="debit",
            source="manual",
            is_emotional=True,
            model_confidence=0.88,
        )
        Expense.objects.create(
            user=self.user,
            amount=1500,
            classification="other",
            category="other",
            payment_mode="BANK",
            merchant="Transfer",
            description="Other outflow",
            raw_description="Other outflow",
            transaction_date=date(2026, 3, 11),
            direction="debit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=25000,
            classification="other",
            category="income",
            payment_mode="BANK",
            merchant="Employer",
            description="Salary",
            raw_description="Salary",
            transaction_date=date(2026, 3, 2),
            direction="credit",
            source="manual",
        )

    def test_timeline_returns_monthly_window_and_unwanted_spend_lane(self):
        response = self.client.get("/api/expenses/timeline/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertEqual(payload["monthly_window"]["reference_month"], "Mar 2026")
        self.assertEqual(payload["monthly_window"]["previous_month"], "Feb 2026")
        self.assertEqual(payload["monthly_window"]["current"]["outflow_total"], 5500.0)
        self.assertEqual(payload["monthly_window"]["current"]["income_total"], 25000.0)
        self.assertEqual(payload["monthly_window"]["current"]["unwanted_total"], 4000.0)
        self.assertEqual(payload["monthly_window"]["previous"]["outflow_total"], 1000.0)
        self.assertEqual(payload["monthly_window"]["window"][-1]["label"], "Mar 2026")

        self.assertEqual(payload["summary"]["unwanted_total"], 5000.0)
        self.assertEqual(payload["summary"]["unwanted_count"], 2)
        self.assertEqual(payload["unwanted_expenses"]["current_month_total"], 4000.0)
        self.assertAlmostEqual(payload["unwanted_expenses"]["current_month_ratio"], 72.7, places=1)
        self.assertEqual(payload["unwanted_expenses"]["overall_total"], 5000.0)
        self.assertEqual(payload["unwanted_expenses"]["emotional_total"], 5000.0)
        self.assertEqual(payload["unwanted_expenses"]["discretionary_total"], 5000.0)
        self.assertEqual(payload["unwanted_expenses"]["top_categories"][0]["label"], "Shopping")
        self.assertEqual(payload["unwanted_expenses"]["items"][0]["merchant"], "Myntra")
        self.assertEqual(payload["unwanted_expenses"]["items"][0]["signal"], "Emotional + discretionary")
        self.assertEqual(payload["timeline_meta"]["total_matching_count"], 4)
        self.assertEqual(payload["timeline_meta"]["visible_count"], 4)

    def test_timeline_filters_by_query_and_transaction_id(self):
        target = Expense.objects.get(merchant="Myntra")

        response = self.client.get("/api/expenses/timeline/?q=myntra")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["timeline_meta"]["total_matching_count"], 1)
        self.assertEqual(payload["timeline_meta"]["filtered_expense_total"], 4000.0)
        self.assertEqual(payload["timeline"][0]["items"][0]["merchant"], "Myntra")

        response = self.client.get(f"/api/expenses/timeline/?transaction_id={target.id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["timeline_meta"]["transaction_id"], str(target.id))
        self.assertEqual(payload["timeline_meta"]["total_matching_count"], 1)
        self.assertEqual(payload["timeline"][0]["items"][0]["id"], target.id)
