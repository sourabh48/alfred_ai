"""FIN-15 loans: each loan records its contract currency; rupee totals and bank matching never use another currency."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence, resolve_canonical_financial_baseline
from apps.loans.models import Loan, LoanPaymentHistory
from apps.loans.services import loan_intelligence_service
from apps.ml_engine.services.canonical_evidence import record_source
from scripts.rehearse_money_migrations import copy_database, read_database, table_digest


class LoanCurrencyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-loan-currency-owner")
        self.client.force_login(self.owner)

    def add(self, **fields):
        body = {"loan_type": "personal", "lender": "Synthetic Lender", "principal": "10000.00", "interest_rate": 10, "emi": "500.00",
                "tenure_months": 24, "remaining_balance": "8000.00", "start_date": "2026-01-01", **fields}
        return self.client.post("/api/loans/", body, content_type="application/json")

    def test_currency_is_recorded_only_when_given_and_checked_against_the_registry(self):
        usd = self.add(currency="USD").json()
        self.assertEqual((usd["currency"], usd["currency_status"]), ("USD", "recorded"))
        for body in ({}, {"currency": ""}, {"currency": None}):
            with self.subTest(body=body):
                row = self.add(**body).json()
                self.assertEqual((row["currency"], row["currency_status"]), (None, "not_recorded"))
        for code in ("JPY", "usd", "XXX"):
            with self.subTest(code=code):
                self.assertEqual(self.add(currency=code).status_code, 400)

    def test_rupee_totals_exclude_other_currencies_which_are_listed_and_grouped_not_converted(self):
        self.add(currency="INR", remaining_balance="8000.00", emi="500.00")
        self.add(remaining_balance="2000.00", emi="100.00")  # not recorded keeps the legacy INR convention
        self.add(currency="USD", remaining_balance="300.25", emi="20.10")
        self.add(currency="USD", remaining_balance="0.75", emi="0.40")
        portfolio = build_financial_intelligence(self.owner)["loan_portfolio"]
        self.assertEqual((portfolio["manual_total_outstanding"], portfolio["manual_total_emi"]), (10000.0, 600.0))
        self.assertEqual(portfolio["other_currencies"], [dict(currency="USD", loans=2, outstanding=301.0, monthly_emi=20.5)])
        self.assertEqual({row["currency"] for row in portfolio["other_currency_loans"]}, {"USD"})
        self.assertEqual(len(portfolio["manual_loans"]), 2)
        sheet = build_financial_intelligence(self.owner)["balance_sheet"]
        self.assertEqual(sheet["total_liabilities"], 10000.0)
        self.assertEqual(sheet["excluded_other_currency_loans"], 2)
        self.assertIn("loan(s) recorded in another currency", sheet["summary"])
        baseline = resolve_canonical_financial_baseline(self.owner, fresh=True)
        self.assertEqual(Decimal(str(baseline["recurring_emi_burden"])), Decimal("600.00"))
        summary = self.client.get("/api/loans/summary/").json()["summary"]
        self.assertEqual(summary["other_currencies"][0]["currency"], "USD")

    def test_bank_debits_never_match_a_loan_in_another_currency(self):
        usd = Loan.objects.get(pk=self.add(currency="USD", loan_account_number="SYNLN123456").json()["id"])
        debit = Expense.objects.create(user=self.owner, amount=Decimal("500.00"), direction="debit", transaction_date=date(2026, 3, 5),
                                       description="EMI SYNLN123456 Synthetic Lender")
        self.assertIsNone(loan_intelligence_service.match_expense_to_loan(self.owner, debit)["loan"])
        rupee = Loan.objects.get(pk=self.add(currency="INR", loan_account_number="SYNLN123456").json()["id"])
        self.assertEqual(loan_intelligence_service.match_expense_to_loan(self.owner, debit)["loan"], rupee)
        self.assertNotEqual(rupee, usd)

    def test_a_recorded_currency_is_locked_once_payments_exist_and_consolidation_never_mixes(self):
        usd = self.add(currency="USD").json()
        legacy = self.add().json()
        for loan in (usd, legacy):
            LoanPaymentHistory.objects.create(loan_id=loan["id"], payment_date=date(2026, 2, 1), amount=Decimal("500.00"))
        self.assertEqual(self.client.patch(f"/api/loans/{usd['id']}/", {"currency": "EUR"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.patch(f"/api/loans/{usd['id']}/", {"currency": "USD"}, content_type="application/json").status_code, 200)
        recorded = self.client.patch(f"/api/loans/{legacy['id']}/", {"currency": "INR"}, content_type="application/json")
        self.assertEqual((recorded.status_code, recorded.json()["currency"]), (200, "INR"))
        body = {"loan_ids": [usd["id"], legacy["id"]], "lender": "Synthetic New Lender", "principal": "16000.00", "emi": "800.00",
                "interest_rate": 9, "tenure_months": 24}
        response = self.client.post("/api/loans/consolidate/", body, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("same currency", response.json()["detail"])
        other = self.add(currency="USD").json()
        merged = self.client.post("/api/loans/consolidate/", body | {"loan_ids": [usd["id"], other["id"]]}, content_type="application/json")
        self.assertEqual((merged.status_code, merged.json()["loan"]["currency"]), (201, "USD"))

    def test_ai_evidence_carries_the_recorded_currency(self):
        usd = self.add(currency="USD").json()["id"]
        legacy = self.add().json()["id"]
        amounts = record_source(self.owner, "loan", usd)["data"]["amounts"]
        self.assertEqual({(v["currency"], v["currency_status"]) for v in amounts.values()}, {("USD", "recorded")})
        legacy_amounts = record_source(self.owner, "loan", legacy)["data"]["amounts"]
        self.assertEqual({(v["currency"], v["currency_status"]) for v in legacy_amounts.values()}, {(None, "not_recorded")})


class LoanCurrencyMigrationTests(TransactionTestCase):
    def test_forward_keeps_money_and_leaves_currency_unrecorded_and_reverse_refuses_to_erase(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before_state = [("loans", "0016_loan_document_evidence") if app == "loans" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-loan-currency-synthetic-") as directory:
            source, candidate = Path(directory) / "source.sqlite3", Path(directory) / "candidate.sqlite3"
            alias = "loan_currency_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(before_state)
                apps = executor.loader.project_state(before_state).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-loan-currency-rehearsal")
                apps.get_model("loans", "Loan").objects.using(alias).create(
                    user_id=owner.pk, principal="10000.01", interest_rate=9.5, emi="500.25", remaining_balance="8000.10", start_date=date(2026, 1, 1))
                db.close()
                before = read_database(source)[0]
                copy_database(source, candidate)
                db.settings_dict["NAME"] = str(candidate)
                MigrationExecutor(db).migrate(leaves)
                db.close()
                after = read_database(candidate)[0]
                self.assertEqual([row.pop("currency") for row in after["loans_loan"]], [None])
                for table, rows in before.items():
                    if table != "django_migrations":
                        self.assertEqual(table_digest(rows), table_digest(after[table]), table)
                MigrationExecutor(db).migrate(before_state)  # nothing recorded yet: reverse is allowed
                db.close()
                MigrationExecutor(db).migrate(leaves)
                Current = MigrationExecutor(db).loader.project_state(leaves).apps.get_model("loans", "Loan")
                Current.objects.using(alias).update(currency="USD")
                with self.assertRaisesRegex(RuntimeError, "verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before_state)
                db.close()
                row = read_database(candidate)[0]["loans_loan"][0]
                self.assertEqual((row["currency"], Decimal(str(row["remaining_balance"]))), ("USD", Decimal("8000.10")))
            finally:
                db.close()
                del connections[alias]
