"""FIN-15 banking: accounts and transactions record their currency; rupee totals never include another currency."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.ml_engine.services.canonical_evidence import record_source
from scripts.rehearse_money_migrations import copy_database, read_database, table_digest


class BankingCurrencyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-banking-currency-owner")
        self.client.force_login(self.owner)

    def add(self, **fields):
        body = {"transaction_date": "2026-10-05", "amount": "100.00", "direction": "debit", "classification": "expense",
                "category": "groceries", "merchant": "Synthetic Shop", **fields}
        return self.client.post("/api/expenses/", body, content_type="application/json")

    def test_transaction_currency_is_recorded_validated_and_never_relabelled(self):
        usd = self.add(currency="USD")
        self.assertEqual(usd.status_code, 201, usd.content)
        self.assertEqual((usd.json()["currency"], usd.json()["currency_status"]), ("USD", "recorded"))
        legacy = self.add().json()
        self.assertEqual((legacy["currency"], legacy["currency_status"]), (None, "not_recorded"))
        for code in ("JPY", "usd"):
            with self.subTest(code=code):
                self.assertEqual(self.add(currency=code).status_code, 400)
        self.assertEqual(self.client.patch(f"/api/expenses/{usd.json()['id']}/", {"currency": "EUR"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/expenses/{legacy['id']}/", {"currency": "INR"}, content_type="application/json").json()["currency"], "INR")

    def test_a_confirmed_account_currency_prefills_new_postings_and_locks_once_used(self):
        account = BankAccount.objects.create(user=self.owner, bank_name="Synthetic Bank", account_number="SYN0001")
        old = Expense.objects.create(user=self.owner, bank_account=account, amount=Decimal("5.00"), transaction_date=date(2026, 9, 1))
        url = f"/api/expenses/accounts/{account.pk}/"
        self.assertEqual(self.client.patch(url, {"currency": "USD"}, content_type="application/json").json()["currency"], "USD")
        old.refresh_from_db()
        self.assertIsNone(old.currency)  # confirming the account never relabels history
        account.refresh_from_db()
        new = Expense.objects.create(user=self.owner, bank_account=account, amount=Decimal("6.00"), transaction_date=date(2026, 9, 2))
        self.assertEqual(new.currency, "USD")
        self.assertEqual(self.client.patch(url, {"currency": "EUR"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"currency": "USD"}, content_type="application/json").status_code, 200)

    def test_rupee_totals_and_the_balance_sheet_leave_other_currencies_out(self):
        BankAccount.objects.create(user=self.owner, bank_name="Rupee Bank", account_number="SYN0002", current_balance=Decimal("1000.00"))
        BankAccount.objects.create(user=self.owner, bank_name="Dollar Bank", account_number="SYN0003", current_balance=Decimal("5.00"), currency="USD")
        self.add(amount="100.00")
        self.add(amount="40.00", currency="INR")
        self.add(amount="999.00", currency="USD")
        timeline = self.client.get("/api/expenses/timeline/").json()
        self.assertEqual(timeline["summary"]["other_currency_transaction_count"], 1)
        self.assertEqual(sum(Decimal(str(group["day_total"])) for group in timeline["timeline"]), Decimal("140.00"))
        sheet = build_financial_intelligence(self.owner)["balance_sheet"]
        self.assertEqual(sheet["excluded_other_currency_accounts"], 1)
        self.assertIn("another currency", sheet["summary"])
        self.assertNotIn(5.0, [item["amount"] for item in sheet.get("assets", []) if "Dollar" in str(item.get("label", ""))])

    def test_ai_evidence_and_export_carry_the_recorded_currency(self):
        usd = self.add(currency="USD").json()["id"]
        amounts = record_source(self.owner, "expense", usd)["data"]["amounts"]
        self.assertEqual({(v["currency"], v["currency_status"]) for v in amounts.values() if v.get("amount") is not None}, {("USD", "recorded")})
        rows = b"".join(self.client.get("/api/expenses/export/").streaming_content).decode()
        self.assertIn(",USD,", rows)


class BankingCurrencyMigrationTests(TransactionTestCase):
    def test_forward_keeps_money_and_leaves_currency_unrecorded_and_reverse_refuses_to_erase(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before_state = [("expenses", "0006_statement_transaction_evidence") if app == "expenses" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-banking-currency-synthetic-") as directory:
            source, candidate = Path(directory) / "source.sqlite3", Path(directory) / "candidate.sqlite3"
            alias = "banking_currency_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(before_state)
                apps = executor.loader.project_state(before_state).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-banking-currency-rehearsal")
                account = apps.get_model("expenses", "BankAccount").objects.using(alias).create(
                    user_id=owner.pk, bank_name="Synthetic", account_number="SYN0004", current_balance="10.01")
                apps.get_model("expenses", "Expense").objects.using(alias).create(
                    user_id=owner.pk, bank_account_id=account.pk, amount="12.34", transaction_date=date(2026, 1, 1))
                db.close()
                before = read_database(source)[0]
                copy_database(source, candidate)
                db.settings_dict["NAME"] = str(candidate)
                MigrationExecutor(db).migrate(leaves)
                db.close()
                after = read_database(candidate)[0]
                for table in ("expenses_bankaccount", "expenses_expense"):
                    self.assertEqual([row.pop("currency") for row in after[table]], [None])
                for table, rows in before.items():
                    if table != "django_migrations":
                        self.assertEqual(table_digest(rows), table_digest(after[table]), table)
                MigrationExecutor(db).migrate(before_state)  # nothing recorded yet: reverse is allowed
                db.close()
                MigrationExecutor(db).migrate(leaves)
                Current = MigrationExecutor(db).loader.project_state(leaves).apps.get_model("expenses", "Expense")
                Current.objects.using(alias).update(currency="USD")
                with self.assertRaisesRegex(RuntimeError, "verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before_state)
                db.close()
                row = read_database(candidate)[0]["expenses_expense"][0]
                self.assertEqual((row["currency"], Decimal(str(row["amount"]))), ("USD", Decimal("12.34")))
            finally:
                db.close()
                del connections[alias]
