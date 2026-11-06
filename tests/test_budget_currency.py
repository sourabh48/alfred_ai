"""FIN-15 budgets: a plan and a savings goal record one currency; a plan is compared only with spend in that currency."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.budgets.services.budget_intelligence import budget_intelligence_service
from apps.expenses.models import Expense
from scripts.rehearse_money_migrations import copy_database, read_database, table_digest


class BudgetCurrencyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-budget-currency-owner")
        self.client.force_login(self.owner)
        self.today = timezone.localdate()

    def plan(self, **fields):
        body = {"month": self.today.strftime("%b %Y"), "base_budget": "1000.00", "inflation_adjusted": "1000.00", **fields}
        return self.client.post("/api/budgets/", body, content_type="application/json")

    def spend(self, amount, currency=None):
        Expense.objects.create(user=self.owner, amount=Decimal(amount), direction="debit", category="groceries",
                               transaction_date=self.today, currency=currency)

    def test_currency_is_recorded_validated_and_blank_stays_not_recorded(self):
        self.assertEqual(self.plan(currency="USD").json()["currency"], "USD")
        self.assertIsNone(self.plan(currency="").json()["currency"])
        self.assertEqual(self.plan(currency="JPY").status_code, 400)
        goal = self.client.post("/api/budgets/goals/", {"name": "Synthetic trip", "target_amount": "500.00", "currency": "EUR"},
                                content_type="application/json").json()
        self.assertEqual(goal["currency"], "EUR")

    def test_a_rupee_plan_counts_only_rupee_spend(self):
        self.plan(currency="INR")
        self.spend("100.00")
        self.spend("40.00", "INR")
        self.spend("999.00", "USD")
        summary = self.client.get("/api/budgets/dashboard/").json()["summary"]
        self.assertEqual((summary["currency"], Decimal(str(summary["total_spent"]))), ("INR", Decimal("140.00")))

    def test_a_plan_in_another_currency_counts_only_that_currency_and_never_feeds_the_rupee_guide(self):
        self.plan(currency="USD", inflation_adjusted="300.00")
        self.spend("100.00")
        self.spend("25.50", "USD")
        self.spend("10.00", "EUR")
        data = self.client.get("/api/budgets/dashboard/").json()
        self.assertEqual((data["summary"]["currency"], Decimal(str(data["summary"]["total_spent"]))), ("USD", Decimal("25.50")))
        self.assertEqual(Decimal(str(data["summary"]["total_remaining"])), Decimal("274.50"))
        self.assertEqual(data["plan"]["currency"], "USD")
        self.assertNotEqual(budget_intelligence_service.calculate_daily_affordability(self.owner)["basis"], "saved_plan")


class BudgetCurrencyMigrationTests(TransactionTestCase):
    def test_forward_keeps_money_and_leaves_currency_unrecorded_and_reverse_refuses_to_erase(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before_state = [("budgets", "0003_savings_goal") if app == "budgets" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-budget-currency-synthetic-") as directory:
            source, candidate = Path(directory) / "source.sqlite3", Path(directory) / "candidate.sqlite3"
            alias = "budget_currency_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(before_state)
                apps = executor.loader.project_state(before_state).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-budget-currency-rehearsal")
                apps.get_model("budgets", "Budget").objects.using(alias).create(
                    user_id=owner.pk, month="Jan 2026", base_budget="1000.01", inflation_adjusted="1050.02", spent="12.34")
                apps.get_model("budgets", "SavingsGoal").objects.using(alias).create(
                    user_id=owner.pk, name="Synthetic", target_amount="500.05", saved_amount="10.10", target_date=date(2027, 1, 1))
                db.close()
                before = read_database(source)[0]
                copy_database(source, candidate)
                db.settings_dict["NAME"] = str(candidate)
                MigrationExecutor(db).migrate(leaves)
                db.close()
                after = read_database(candidate)[0]
                for table in ("budgets_budget", "budgets_savingsgoal"):
                    self.assertEqual([row.pop("currency") for row in after[table]], [None])
                for table, rows in before.items():
                    if table != "django_migrations":
                        self.assertEqual(table_digest(rows), table_digest(after[table]), table)
                MigrationExecutor(db).migrate(before_state)  # nothing recorded yet: reverse is allowed
                db.close()
                MigrationExecutor(db).migrate(leaves)
                Current = MigrationExecutor(db).loader.project_state(leaves).apps.get_model("budgets", "SavingsGoal")
                Current.objects.using(alias).update(currency="GBP")
                with self.assertRaisesRegex(RuntimeError, "verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before_state)
                db.close()
                row = read_database(candidate)[0]["budgets_savingsgoal"][0]
                self.assertEqual((row["currency"], Decimal(str(row["target_amount"]))), ("GBP", Decimal("500.05")))
            finally:
                db.close()
                del connections[alias]
