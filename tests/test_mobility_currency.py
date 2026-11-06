"""FIN-15 mobility: vehicle values, running costs and travel budgets record their currency; rupee totals never use another one."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.mobility.models import BikeProfile, BikeServiceRecord, TravelPlan, TripLog
from apps.mobility.services.bike_service_intelligence import bike_service_intelligence
from scripts.rehearse_money_migrations import copy_database, read_database, table_digest


class MobilityCurrencyTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-mobility-currency-owner")
        self.client.force_login(self.owner)

    def test_service_currency_is_recorded_validated_and_blank_stays_not_recorded(self):
        body = {"bike_name": "Synthetic Bike", "service_date": "2026-10-01", "cost": "50.00"}
        post = lambda **fields: self.client.post("/api/mobility/bike-services/", body | fields, content_type="application/json")
        usd = post(currency="USD")
        self.assertEqual(usd.status_code, 201, usd.content)
        self.assertEqual(usd.json()["currency"], "USD")
        self.assertIsNone(post(currency="").json()["currency"])
        self.assertEqual(post(currency="JPY").status_code, 400)

    def test_vehicle_value_and_running_costs_in_another_currency_stay_out_of_rupee_totals(self):
        rupee = BikeProfile.objects.create(user=self.owner, display_name="Rupee Bike", model_name="Synthetic", estimated_market_value=Decimal("90000.00"))
        dollar = BikeProfile.objects.create(user=self.owner, display_name="Dollar Bike", model_name="Synthetic",
                                            estimated_market_value=Decimal("1200.00"), value_currency="USD")
        for profile, cost, currency in ((rupee, "500.00", None), (rupee, "250.00", "INR"), (rupee, "70.00", "EUR"), (dollar, "30.00", "USD")):
            BikeServiceRecord.objects.create(user=self.owner, bike_profile=profile, bike_name=profile.display_name,
                                             service_date=date(2026, 9, 1), cost=Decimal(cost), currency=currency)
        positions = {row["vehicle"]: row for row in build_financial_intelligence(self.owner)["balance_sheet"]["vehicle_positions"]}
        self.assertEqual((positions["Rupee Bike"]["recognized_value"], positions["Rupee Bike"]["recorded_running_cost_total"]), (90000.0, 750.0))
        self.assertEqual((positions["Dollar Bike"]["recognized_value"], positions["Dollar Bike"]["recorded_running_cost_total"]), (0.0, 0.0))
        self.assertEqual(positions["Dollar Bike"]["other_currency_value"], {"currency": "USD", "estimated_market_value": 1200.0})
        self.assertEqual(positions["Dollar Bike"]["valuation_status"], "other_currency_not_converted")
        rupee.is_primary = True
        rupee.save()
        summary = bike_service_intelligence.build_dashboard(self.owner)["summary"]
        self.assertEqual(Decimal(str(summary["total_service_cost"])), Decimal("750.00"))

    def test_trip_budgets_and_spend_add_up_only_in_rupees(self):
        rupee = TravelPlan.objects.create(user=self.owner, title="Rupee trip", budget=Decimal("5000.00"))
        euro = TravelPlan.objects.create(user=self.owner, title="Euro trip", budget=Decimal("800.00"), budget_currency="EUR")
        TripLog.objects.create(user=self.owner, travel_plan=rupee, log_date=date(2026, 9, 1), title="Day 1", spend_amount=Decimal("1200.00"))
        TripLog.objects.create(user=self.owner, travel_plan=euro, log_date=date(2026, 9, 2), title="Day 1", spend_amount=Decimal("90.00"), currency="EUR")
        summary = self.client.get("/api/mobility/dashboard/").json()["summary"]
        self.assertEqual((Decimal(str(summary["total_trip_budget"])), Decimal(str(summary["total_trip_spend"]))), (Decimal("5000"), Decimal("1200")))
        self.assertEqual(self.client.get(f"/api/mobility/travel-plans/{euro.pk}/").json()["budget_currency"], "EUR")


class MobilityCurrencyMigrationTests(TransactionTestCase):
    def test_forward_keeps_money_and_leaves_currency_unrecorded_and_reverse_refuses_to_erase(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        before_state = [("mobility", "0014_trip_video") if app == "mobility" else (app, name) for app, name in leaves]
        with TemporaryDirectory(prefix="alfred-mobility-currency-synthetic-") as directory:
            source, candidate = Path(directory) / "source.sqlite3", Path(directory) / "candidate.sqlite3"
            alias = "mobility_currency_rehearsal"
            db = connection.copy(alias=alias)
            db.settings_dict["NAME"] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(before_state)
                apps = executor.loader.project_state(before_state).apps
                owner = apps.get_model("users", "User").objects.using(alias).create(username="synthetic-mobility-currency-rehearsal")
                profile = apps.get_model("mobility", "BikeProfile").objects.using(alias).create(
                    user_id=owner.pk, display_name="Synthetic", model_name="Synthetic", estimated_market_value="45000.45")
                apps.get_model("mobility", "BikeServiceRecord").objects.using(alias).create(
                    user_id=owner.pk, bike_profile_id=profile.pk, bike_name="Synthetic", service_date=date(2026, 1, 1), cost="1234.56")
                apps.get_model("mobility", "TravelPlan").objects.using(alias).create(user_id=owner.pk, title="Synthetic", budget="7000.07")
                db.close()
                before = read_database(source)[0]
                copy_database(source, candidate)
                db.settings_dict["NAME"] = str(candidate)
                MigrationExecutor(db).migrate(leaves)
                db.close()
                after = read_database(candidate)[0]
                for table, columns in (("mobility_bikeprofile", ("value_currency", "income_support_currency")),
                                       ("mobility_bikeservicerecord", ("currency",)), ("mobility_travelplan", ("budget_currency",))):
                    for column in columns:
                        self.assertEqual([row.pop(column) for row in after[table]], [None], column)
                for table, rows in before.items():
                    if table != "django_migrations":
                        self.assertEqual(table_digest(rows), table_digest(after[table]), table)
                MigrationExecutor(db).migrate(before_state)  # nothing recorded yet: reverse is allowed
                db.close()
                MigrationExecutor(db).migrate(leaves)
                Current = MigrationExecutor(db).loader.project_state(leaves).apps.get_model("mobility", "TravelPlan")
                Current.objects.using(alias).update(budget_currency="EUR")
                with self.assertRaisesRegex(RuntimeError, "verified pre-migration backup"):
                    MigrationExecutor(db).migrate(before_state)
                db.close()
                row = read_database(candidate)[0]["mobility_travelplan"][0]
                self.assertEqual((row["budget_currency"], Decimal(str(row["budget"]))), ("EUR", Decimal("7000.07")))
            finally:
                db.close()
                del connections[alias]
