"""FIN-15: positions record their currency; rupee totals never add another currency, and nothing is converted."""
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.expenses.services.financial_intelligence import _build_balance_sheet
from apps.investments.models import Investment
from apps.investments.views import _investment_allocation_payload, _investment_summary_payload
from apps.ml_engine.services.canonical_evidence import record_source
from scripts.rehearse_money_migrations import copy_database, read_database, table_digest


class InvestmentCurrencyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-currency-owner")
        self.client.force_login(self.owner)

    def add(self, **fields):
        body = {"asset_type": "equity", "asset_name": "Synthetic fund", "invested_amount": "1000.00", "current_value": "1200.50", "monthly_sip": "100.00", **fields}
        return self.client.post("/api/investments/", body, content_type="application/json")

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

    def test_rupee_totals_exclude_other_currencies_which_are_grouped_not_converted(self):
        self.add(currency="INR", asset_name="Rupee fund")
        self.add(asset_name="Legacy fund")  # not recorded keeps the legacy INR convention
        self.add(currency="USD", asset_name="Dollar fund", current_value="300.25", invested_amount="250.00")
        self.add(currency="USD", asset_name="Dollar ETF", current_value="0.75", invested_amount="1.00", monthly_sip="0")
        summary = _investment_summary_payload(self.owner)["summary"]
        self.assertEqual((summary["total_value"], summary["total_invested"], summary["monthly_sip"]), (2401.0, 2000.0, 200.0))
        self.assertEqual((summary["positions"], summary["positions_in_rupee_totals"]), (4, 2))
        self.assertEqual(summary["other_currencies"], [dict(currency="USD", positions=2, total_value="301.00", total_invested="251.00", monthly_sip="100.00")])
        self.assertEqual(sum(_investment_allocation_payload(self.owner)["values"]), 2401.0)
        sheet = _build_balance_sheet(user=self.owner, loans=[])
        self.assertEqual(next(a["amount"] for a in sheet["assets"] if a["label"] == "Investments"), 2401.0)
        self.assertEqual(sheet["excluded_other_currency_investments"], 2)
        self.assertIn("no currency conversion", sheet["summary"])

    def test_ai_evidence_carries_the_recorded_currency(self):
        usd = Investment.objects.get(pk=self.add(currency="USD").json()["id"])
        legacy = Investment.objects.get(pk=self.add().json()["id"])
        amounts = record_source(self.owner, "investment", usd.pk)["data"]["amounts"]
        self.assertEqual({(v["currency"], v["currency_status"]) for v in amounts.values()}, {("USD", "recorded")})
        self.assertEqual(amounts["current_value"]["amount"], "1200.50")
        legacy_amounts = record_source(self.owner, "investment", legacy.pk)["data"]["amounts"]
        self.assertEqual({(v["currency"], v["currency_status"]) for v in legacy_amounts.values()}, {(None, "not_recorded")})


class InvestmentCurrencyMigrationTests(TransactionTestCase):
    def test_forward_keeps_money_and_leaves_currency_unrecorded_and_reverse_refuses_to_erase(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before_state = [("investments", "0005_investment_document_evidence") if app == "investments" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-investment-currency-synthetic-") as directory:
            source, candidate = Path(directory) / "source.sqlite3", Path(directory) / "candidate.sqlite3"
            alias = "investment_currency_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(before_state)
                apps = executor.loader.project_state(before_state).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-currency-rehearsal")
                apps.get_model("investments", "Investment").objects.using(alias).create(
                    user_id=owner.pk, asset_name="SYNTHETIC", asset_type="equity", invested_amount="100.01", current_value="123.45", monthly_sip="1.01")
                db.close()
                before = read_database(source)[0]
                copy_database(source, candidate)
                db.settings_dict["NAME"] = str(candidate)
                MigrationExecutor(db).migrate(leaves)
                db.close()
                after = read_database(candidate)[0]
                self.assertEqual([row.pop("currency") for row in after["investments_investment"]], [None])
                # 0009 adds fund-price columns; they start empty and leave the recorded money unchanged.
                self.assertEqual([[row.pop(c) for c in ("amfi_scheme_code", "units", "nav", "nav_date", "value_before_nav")]
                                  for row in after["investments_investment"]], [["", None, None, None, None]])
                for table, rows in before.items():
                    if table != "django_migrations":
                        self.assertEqual(table_digest(rows), table_digest(after[table]), table)
                MigrationExecutor(db).migrate(before_state)  # nothing recorded yet: reverse is allowed
                db.close()
                MigrationExecutor(db).migrate(leaves)
                Current = MigrationExecutor(db).loader.project_state(leaves).apps.get_model("investments", "Investment")
                Current.objects.using(alias).update(currency="USD")
                with self.assertRaisesRegex(RuntimeError, "verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before_state)
                db.close()
                self.assertEqual([row["currency"] for row in read_database(candidate)[0]["investments_investment"]], ["USD"])
                self.assertEqual(Decimal(str(read_database(candidate)[0]["investments_investment"][0]["current_value"])), Decimal("123.45"))
            finally:
                db.close()
                del connections[alias]
