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

    def test_chart_uses_cashflow_treatment_not_raw_bank_movement(self):
        Expense.objects.create(
            user=self.user,
            amount=1000,
            classification="other",
            category="transfer",
            payment_mode="BANK",
            merchant="Family transfer",
            description="Transfer credit",
            raw_description="TRANSFER CREDIT",
            transaction_date=date(2026, 1, 25),
            direction="credit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=2000,
            classification="other",
            category="transfer",
            payment_mode="BANK",
            merchant="Self transfer",
            description="Transfer debit",
            raw_description="TRANSFER DEBIT",
            transaction_date=date(2026, 3, 12),
            direction="debit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=300,
            classification="other",
            category="credit_card",
            payment_mode="BANK",
            merchant="Card payment",
            description="Card payment",
            raw_description="CARD PAYMENT",
            transaction_date=date(2026, 3, 13),
            direction="debit",
            source="manual",
        )
        Expense.objects.create(
            user=self.user,
            amount=60000,
            classification="expense",
            category="other",
            payment_mode="BANK",
            merchant="Self cheque",
            description="Self Chq Paid",
            raw_description="SELF CHQ PAID",
            transaction_date=date(2026, 3, 14),
            direction="debit",
            source="manual",
        )

        response = self.client.get("/api/expenses/chart/?granularity=yearly")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["income_values"], [0.0, 500.0])
        self.assertEqual(payload["bank_credit_values"], [0.0, 1500.0])
        self.assertEqual(payload["bank_debit_values"], [225.0, 62330.0])
        self.assertEqual(payload["outflow_values"], [225.0, 330.0])
        self.assertEqual(payload["transfer_in_values"], [0.0, 1000.0])
        self.assertEqual(payload["transfer_out_values"], [0.0, 2000.0])
        self.assertEqual(payload["credit_card_payment_values"], [0.0, 300.0])
        self.assertEqual(payload["review_required_values"], [0.0, 60000.0])
