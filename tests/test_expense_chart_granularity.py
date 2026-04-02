from datetime import date

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from apps.expenses.models import Expense


class ExpenseChartGranularityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="expense_chart_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

        Expense.objects.create(
            user=self.user,
            amount=100,
            classification="expense",
            category="food",
            payment_mode="UPI",
            merchant="Cafe One",
            description="Lunch",
            raw_description="Lunch",
            transaction_date=date(2025, 1, 10),
            direction="debit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=50,
            classification="loan",
            category="loan",
            payment_mode="BANK",
            merchant="Loan EMI",
            description="EMI",
            raw_description="EMI",
            transaction_date=date(2025, 2, 5),
            direction="debit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=75,
            classification="expense",
            category="shopping",
            payment_mode="CARD",
            merchant="Shop Two",
            description="Shopping",
            raw_description="Shopping",
            transaction_date=date(2025, 4, 15),
            direction="debit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=500,
            classification="other",
            category="income",
            payment_mode="BANK",
            merchant="Employer",
            description="Salary",
            raw_description="Salary",
            transaction_date=date(2026, 1, 20),
            direction="credit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=30,
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

    def test_quarterly_financial_flow_groups_expenses_by_quarter(self):
        response = self.client.get("/api/expenses/chart/?granularity=quarterly")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["granularity"], "quarterly")
        self.assertEqual(payload["labels"], ["Q1 2025", "Q2 2025", "Q1 2026"])
        self.assertEqual(payload["expense_values"], [100.0, 75.0, 0.0])
        self.assertEqual(payload["loan_values"], [50.0, 0.0, 0.0])
        self.assertEqual(payload["other_values"], [0.0, 0.0, 30.0])
        self.assertEqual(payload["income_values"], [0.0, 0.0, 500.0])

    def test_yearly_financial_flow_groups_expenses_by_year(self):
        response = self.client.get("/api/expenses/chart/?granularity=yearly")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["granularity"], "yearly")
        self.assertEqual(payload["labels"], ["2025", "2026"])
        self.assertEqual(payload["expense_values"], [175.0, 0.0])
        self.assertEqual(payload["loan_values"], [50.0, 0.0])
        self.assertEqual(payload["other_values"], [0.0, 30.0])
        self.assertEqual(payload["income_values"], [0.0, 500.0])

    def test_invalid_granularity_falls_back_to_monthly(self):
        response = self.client.get("/api/expenses/chart/?granularity=weekly")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["granularity"], "monthly")
        self.assertEqual(payload["labels"], ["Jan 2025", "Feb 2025", "Apr 2025", "Jan 2026", "Mar 2026"])
