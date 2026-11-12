"""One synthetic owner, every kind of account: each amount is counted once and every module reads the same figures.

Expected values are worked out by hand in the comments, not read back from the code under test.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.budgets.models import Budget, SavingsGoal
from apps.budgets.services.budget_intelligence import budget_intelligence_service
from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence, resolve_canonical_financial_baseline
from apps.investments.models import Investment
from apps.loans.models import Loan
from apps.ml_engine.services.recommendation_engine import recommendation_engine


class WholeOwnerFinancialScenarioTests(TestCase):
    def setUp(self):
        cache.clear()
        recommendation_engine.user_profiles.clear()
        today = timezone.localdate()
        self.user = get_user_model().objects.create_user(username="synthetic-whole-owner", password="Pass12345!",
                                                         monthly_income=100000, monthly_income_basis="monthly")
        account = lambda number, kind, balance: BankAccount.objects.create(
            user=self.user, account_number=number, account_type=kind, current_balance=balance, currency="INR")
        self.checking = account("SYNWHOLE01", "savings", "150000.00")
        account("SYNWHOLE02", "current", "-12500.50")      # overdrawn: a liability, not negative cash
        account("SYNWHOLE03", "credit", "-30000.00")       # card balance owed
        account("SYNWHOLE04", "investment", "200000.00")   # the same money as the holding below
        Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Synthetic fund", account_number="SYNWHOLE04",
                                  invested_amount="180000.00", current_value="200000.00", currency="INR")
        loan = lambda kind, principal, balance, emi: Loan.objects.create(
            user=self.user, loan_type=kind, lender="Synthetic Bank", principal=principal, remaining_balance=balance,
            interest_rate=9, emi=emi, tenure_months=120, start_date=today.replace(day=1), currency="INR")
        loan("home", "3000000.00", "2500000.00", "30000.00")
        loan("personal", "200000.00", "150000.00", "5000.00")
        spend = lambda amount, category, **extra: Expense.objects.create(
            user=self.user, bank_account=self.checking, amount=amount, category=category, transaction_date=today,
            direction="debit", currency="INR", **extra)
        spend("8000.00", "Groceries")
        spend("4000.50", "Dining")
        spend("20000.00", "Transfer", classification="transfer")   # to the owner's own account: not spending
        Budget.objects.create(user=self.user, month=today.strftime("%b %Y"), base_budget="40000.00", inflation_adjusted="40000.00",
                              spent="999999.00", currency="INR")  # the stored column is stale on purpose; it must not be used
        SavingsGoal.objects.create(user=self.user, name="Synthetic goal", target_amount="120000.00", saved_amount="20000.00", currency="INR")
        self.client.force_login(self.user)

    def test_every_amount_is_counted_once_and_every_module_agrees(self):
        from apps.ml_engine.services import assistant_tools as tools
        from apps.mobility.services.travel_advisor import travel_advisor
        before = [list(model.objects.values()) for model in (BankAccount, Expense, Investment, Loan, Budget, SavingsGoal)]

        sheet = build_financial_intelligence(self.user)["balance_sheet"]
        assets = {row["label"]: row["amount"] for row in sheet["assets"]}
        liabilities = {row["label"]: row["amount"] for row in sheet["liabilities"]}
        # Cash is the one positive savings account. The overdraft and the card are owed, never negative cash.
        self.assertEqual(assets["Cash and bank balances"], 150000.0)
        # The demat account and the fund are the same 200,000: counted once.
        self.assertEqual(assets["Investments"], 200000.0)
        # No purchase price is recorded, so the home is shown at the labelled loan-principal proxy.
        self.assertEqual(assets["Home property acquisition-cost base (proxy)"], 3000000.0)
        self.assertEqual(liabilities, {"Open loan liabilities": 2650000.0,   # 2,500,000 + 150,000
                                       "Credit card liability": 30000.0, "Overdrawn accounts": 12500.5})
        self.assertEqual(sheet["total_assets"], 3350000.0)        # 150,000 + 200,000 + 3,000,000
        self.assertEqual(sheet["total_liabilities"], 2692500.5)   # 2,650,000 + 30,000 + 12,500.50
        self.assertEqual(sheet["net_worth"], 657499.5)            # 3,350,000 - 2,692,500.50

        base = resolve_canonical_financial_baseline(self.user, fresh=True)
        expected = {
            "monthly_income": 100000.0, "liquid_cash": 150000.0,
            "recurring_emi_burden": 35000.0,                 # 30,000 + 5,000
            "fixed_obligations": 35000.0, "debt_burden_ratio": 35.0,
            "disposable_cash_flow": 65000.0,                 # 100,000 - 35,000
            "current_month_variable_spend": 12000.5,         # 8,000 + 4,000.50; the 20,000 own-account transfer is not spending
            "savings_capacity": 52999.5,                     # 65,000 - 12,000.50
            "essential_monthly_outflow": 47000.5,            # 35,000 + 12,000.50
            "liquid_runway_months": 3.19,                    # 150,000 / 47,000.50
            "total_assets": 3350000.0, "total_liabilities": 2692500.5, "net_worth": 657499.5,
        }
        self.assertEqual({key: base[key] for key in expected}, expected)

        # Budget: spent comes from this month's transactions, not the stale stored column.
        self.assertEqual(self.client.get("/api/budgets/").json()[0]["spent"], 12000.5)
        suggested = budget_intelligence_service.suggest_budget(self.user)
        self.assertEqual((suggested["monthly_income"], suggested["fixed_obligations"], suggested["disposable_income"]), (100000.0, 35000.0, 65000.0))
        # Loans page.
        loans = self.client.get("/api/loans/metrics/").json()
        self.assertEqual({key: loans[key] for key in ("total_remaining", "monthly_emi_burden", "debt_to_income_ratio", "disposable_cash_flow", "savings_capacity")},
                         {"total_remaining": 2650000.0, "monthly_emi_burden": 35000.0, "debt_to_income_ratio": 35.0,
                          "disposable_cash_flow": 65000.0, "savings_capacity": 52999.5})
        # Investments page: cost and value stay separate figures.
        service = "apps.investments.views.portfolio_intelligence_service."  # market lookups are not part of this check
        with patch(service + "get_market_trends_and_suggestions", return_value={}), patch(service + "build_short_horizon_watchlist", return_value={}):
            summary = self.client.get("/api/investments/summary/").json()["summary"]
        self.assertEqual((summary["total_invested"], summary["total_value"], summary["gain_loss"]), (180000.0, 200000.0, 20000.0))
        # Recommendations read the same baseline; their profile names the holding figure for what it is.
        profile = recommendation_engine.build_user_profile(self.user)
        self.assertEqual((profile["income"], profile["monthly_expenses"], profile["monthly_savings"], profile["total_emi"], profile["dti_ratio"]),
                         (100000.0, 12000.5, 52999.5, 35000.0, 35.0))
        self.assertEqual(profile["investments_current_value"], 200000.0)
        self.assertNotIn("total_invested", profile)
        # Travel affordability spends only what is left after obligations and living costs.
        basis = travel_advisor._stay_advice(self.user, per_day_budget=5000, duration_days=4)["affordability_basis"]
        self.assertEqual(basis, {"disposable_cash_flow": 65000.0, "savings_capacity": 52999.5, "debt_burden_ratio": 35.0, "monthly_trip_capacity": 52999.5})
        # The AI finance tool may withhold a figure, but any amount it does give is the canonical one.
        amounts = tools.execute_tool(self.user, "finance.baseline", {}, consent=True)[0]["data"]["amounts"]
        self.assertEqual(amounts["monthly_income"]["amount"], "100000.00")
        for name, item in amounts.items():
            if item["amount"] is not None and name in base:
                self.assertEqual(Decimal(item["amount"]), Decimal(str(base[name])), name)
        # Reading every view wrote nothing.
        self.assertEqual([list(model.objects.values()) for model in (BankAccount, Expense, Investment, Loan, Budget, SavingsGoal)], before)
