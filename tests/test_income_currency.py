"""FIN-15 income: entered income, housing cost and career salary record their currency; rupee income never uses another one."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.career.models import CareerProfile
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from scripts.rehearse_money_migrations import copy_database, read_database, table_digest


class IncomeCurrencyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-income-currency-owner")
        self.client.force_login(self.owner)

    def patch(self, **fields):
        return self.client.patch("/api/users/profile/", fields, content_type="application/json")

    def baseline(self):
        self.owner.refresh_from_db()
        return resolve_canonical_financial_baseline(self.owner, fresh=True)

    def test_profile_currencies_are_recorded_validated_and_blank_stays_not_recorded(self):
        saved = self.patch(monthly_income="5000.00", income_currency="USD", rent_currency="", variable_income_currency="GBP").json()
        self.assertEqual((saved["income_currency"], saved["rent_currency"], saved["variable_income_currency"]), ("USD", None, "GBP"))
        for code in ("JPY", "usd"):
            with self.subTest(code=code):
                self.assertEqual(self.patch(income_currency=code).status_code, 400)

    def test_income_and_housing_in_another_currency_stay_out_of_rupee_income(self):
        self.patch(monthly_income="5000.00", monthly_income_basis="monthly", income_currency="USD", rent_or_emi="1500.00", rent_currency="USD")
        self.owner.refresh_from_db()
        self.assertEqual((self.owner.confirmed_monthly_income, self.owner.confirmed_annual_income), (Decimal("0.00"), Decimal("0.00")))
        baseline = self.baseline()
        self.assertEqual((Decimal(str(baseline["monthly_income"])), Decimal(str(baseline["rent_burden"]))), (Decimal("0"), Decimal("0")))
        self.patch(income_currency="INR", rent_currency=None)
        baseline = self.baseline()
        self.assertEqual((Decimal(str(baseline["monthly_income"])), Decimal(str(baseline["rent_burden"]))), (Decimal("5000"), Decimal("1500")))
        self.assertEqual(baseline["income_source"], "reported_monthly_income")

    def test_a_career_salary_in_another_currency_is_not_a_rupee_income_fallback(self):
        profile = CareerProfile.objects.create(user=self.owner, role="Synthetic Engineer", experience_years=3, skills="python",
                                               last_salary=Decimal("7000.00"), salary_currency="EUR")
        self.assertEqual(Decimal(str(self.baseline()["monthly_income"])), Decimal("0"))
        response = self.client.put("/api/career/", {"role": "Synthetic Engineer", "experience_years": 3, "skills": "python",
                                                    "last_salary": "7000.00", "salary_currency": ""}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertIsNone(profile.salary_currency)  # blank means not recorded, never a guessed INR
        self.assertEqual(Decimal(str(self.baseline()["monthly_income"])), Decimal("7000"))


class IncomeCurrencyMigrationTests(TransactionTestCase):
    def test_forward_keeps_money_and_leaves_currency_unrecorded_and_reverse_refuses_to_erase(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        earlier = {"users": "0004_user_monthly_income_basis", "career": "0005_career_salary_decimal"}
        before_state = [(app, earlier.get(app, name)) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-income-currency-synthetic-") as directory:
            source, candidate = Path(directory) / "source.sqlite3", Path(directory) / "candidate.sqlite3"
            alias = "income_currency_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(before_state)
                apps = executor.loader.project_state(before_state).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(
                    username="synthetic-income-currency-rehearsal", monthly_income="12345.67", rent_or_emi="890.12")
                apps.get_model("career", "CareerProfile").objects.using(alias).create(
                    user_id=owner.pk, role="Synthetic", experience_years=1, skills="", last_salary="4321.09")
                db.close()
                before = read_database(source)[0]
                copy_database(source, candidate)
                db.settings_dict["NAME"] = str(candidate)
                MigrationExecutor(db).migrate(leaves)
                db.close()
                after = read_database(candidate)[0]
                for table, columns in (("users_user", ("income_currency", "variable_income_currency", "rent_currency", "display_currency")),
                                       ("career_careerprofile", ("salary_currency",))):
                    for column in columns:
                        self.assertEqual([row.pop(column) for row in after[table]], [None], column)
                for table, rows in before.items():
                    if table != "django_migrations":
                        self.assertEqual(table_digest(rows), table_digest(after[table]), table)
                MigrationExecutor(db).migrate(before_state)  # nothing recorded yet: reverse is allowed
                db.close()
                MigrationExecutor(db).migrate(leaves)
                Current = MigrationExecutor(db).loader.project_state(leaves).apps.get_model("users", "User")
                Current.objects.using(alias).update(rent_currency="USD")
                with self.assertRaisesRegex(RuntimeError, "verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before_state)
                db.close()
                row = read_database(candidate)[0]["users_user"][0]
                self.assertEqual((row["rent_currency"], Decimal(str(row["rent_or_emi"]))), ("USD", Decimal("890.12")))
            finally:
                db.close()
                del connections[alias]
