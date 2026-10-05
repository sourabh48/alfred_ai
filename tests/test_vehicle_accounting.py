"""Vehicle ownership, borrowing, and running expenses have separate accounting."""

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import (
    _build_vehicle_positions,
    build_financial_intelligence,
    resolve_canonical_financial_baseline,
)
from apps.loans.models import Loan
from apps.mobility.models import BikeProfile, BikeServiceRecord, TravelPlan, TripLog


class VehicleAccountingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="vehicle-accounting")
        self.client.force_login(self.user)

    def profile(self, **changes):
        values = {
            "user": self.user,
            "display_name": "Recorded Vehicle",
            "model_name": "Custom Model",
            "usage_pattern": "personal",
            "estimated_market_value": 100000,
        }
        values.update(changes)
        return BikeProfile.objects.create(**values)

    def loan(self, **changes):
        values = {
            "user": self.user,
            "loan_type": "car",
            "lender": "Vehicle Finance",
            "loan_account_number": "VEHICLE-001",
            "principal": 60000,
            "remaining_balance": 40000,
            "interest_rate": 10,
            "emi": 2500,
            "tenure_months": 24,
            "start_date": timezone.localdate(),
            "verification_status": "confirmed",
            "status": "active",
        }
        values.update(changes)
        return Loan.objects.create(**values)

    def running_cost_records(self, profile, *, service_cost=12000, trip_spend=24000):
        BikeServiceRecord.objects.create(
            user=profile.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date=timezone.localdate(),
            cost=service_cost,
        )
        plan = TravelPlan.objects.create(
            user=profile.user,
            vehicle_profile=profile,
            title="Recorded Drive",
            destination="Nearby Town",
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
        )
        TripLog.objects.create(
            user=profile.user,
            travel_plan=plan,
            log_date=timezone.localdate(),
            title="Recorded Trip Expense",
            spend_amount=trip_spend,
        )

    def assert_accounting(self, *, assets, debt, pending=0, emi=0):
        expected = {
            "total_assets": assets,
            "total_liabilities": debt,
            "net_worth": assets - debt,
        }
        intelligence = build_financial_intelligence(self.user)
        baseline = resolve_canonical_financial_baseline(self.user)
        dashboard_response = self.client.get("/api/expenses/dashboard/")
        networth_response = self.client.get("/api/loans/networth/")
        self.assertEqual(dashboard_response.status_code, 200, dashboard_response.content)
        self.assertEqual(networth_response.status_code, 200, networth_response.content)
        dashboard = dashboard_response.json()
        networth = networth_response.json()
        for values in (
            intelligence["balance_sheet"], intelligence["baseline"], baseline,
            dashboard["balance_sheet"], dashboard["baseline"],
        ):
            for key, amount in expected.items():
                self.assertEqual(values[key], amount, key)
        self.assertEqual(baseline["recurring_emi_burden"], emi)
        self.assertEqual(networth["net_worth"], assets - debt)
        self.assertEqual(networth["assets"]["total"], assets)
        self.assertEqual(networth["assets"]["vehicles"], assets)
        self.assertEqual(networth["assets"]["utility_and_income_supporting_vehicles"], assets)
        self.assertEqual(networth["liabilities"]["total"], debt)
        self.assertEqual(networth["liabilities"]["loans"], debt - pending)
        self.assertEqual(networth["liabilities"]["pending_foreclosure_balance"], pending)
        self.assertEqual(networth["liabilities"]["lifestyle_vehicle_burden"], 0)
        self.assertEqual(
            networth["metrics"]["asset_allocation"]["vehicle_asset_percentage"],
            100 if assets else 0,
        )
        self.assertEqual(sum(row["amount"] for row in intelligence["balance_sheet"]["assets"]), assets)
        self.assertEqual(sum(row["amount"] for row in intelligence["balance_sheet"]["liabilities"]), debt)
        self.assertNotIn(
            "Lifestyle vehicle burden",
            {row["label"] for row in intelligence["balance_sheet"]["liabilities"]},
        )
        return intelligence, networth

    def test_personal_essential_mixed_and_commercial_vehicles_use_full_market_value(self):
        for usage in ("personal", "essential", "mixed", "commercial"):
            profile = self.profile(display_name=usage, usage_pattern=usage, monthly_income_support=20000)
            self.running_cost_records(profile)

        intelligence, _ = self.assert_accounting(assets=400000, debt=0)

        self.assertEqual(len(intelligence["balance_sheet"]["vehicle_positions"]), 4)
        for position in intelligence["balance_sheet"]["vehicle_positions"]:
            with self.subTest(vehicle=position["vehicle"]):
                self.assertEqual(position["bucket"], "asset")
                self.assertEqual(position["recognized_value"], 100000)
                self.assertEqual(position["estimated_market_value"], 100000)

    def test_zero_values_do_not_create_assets_or_liabilities_from_income_or_running_cost(self):
        for usage in ("personal", "essential", "mixed", "commercial"):
            profile = self.profile(
                display_name=usage, usage_pattern=usage,
                estimated_market_value=0, monthly_income_support=20000,
            )
            self.running_cost_records(profile)

        intelligence, _ = self.assert_accounting(assets=0, debt=0)

        for position in intelligence["balance_sheet"]["vehicle_positions"]:
            with self.subTest(vehicle=position["vehicle"]):
                self.assertEqual(position["bucket"], "asset")
                self.assertEqual(position["recognized_value"], 0)

    def test_unknown_market_value_does_not_use_an_income_or_cost_proxy(self):
        profile = BikeProfile(
            id=123, user=self.user, display_name="Value Unknown", model_name="Custom Model",
            usage_pattern="commercial", estimated_market_value=None, monthly_income_support=20000,
        )
        service = BikeServiceRecord(bike_profile_id=123, cost=12000)
        trip = TripLog(travel_plan=TravelPlan(vehicle_profile_id=123), spend_amount=24000)

        position = _build_vehicle_positions([profile], [service], [trip])[0]

        self.assertEqual(position["bucket"], "asset")
        self.assertEqual(position["recognized_value"], 0)
        self.assertEqual(position["estimated_market_value"], 0)

    def test_legacy_negative_market_value_is_not_a_negative_asset_or_a_debt(self):
        profile = self.profile(estimated_market_value=-25000, monthly_income_support=10000)
        self.running_cost_records(profile)

        intelligence, _ = self.assert_accounting(assets=0, debt=0)

        self.assertEqual(intelligence["balance_sheet"]["vehicle_positions"][0]["recognized_value"], 0)
        self.assertEqual(intelligence["balance_sheet"]["vehicle_positions"][0]["estimated_market_value"], 0)

    def test_confirmed_vehicle_loan_is_counted_once_alongside_the_full_vehicle_asset(self):
        profile = self.profile()
        self.running_cost_records(profile)
        self.loan()

        intelligence, networth = self.assert_accounting(assets=100000, debt=40000, emi=2500)

        self.assertEqual(networth["loan_breakdown"], {"Car Loan": 40000})
        self.assertEqual(intelligence["balance_sheet"]["liabilities"], [{"label": "Open loan liabilities", "amount": 40000}])
        self.assertEqual(intelligence["balance_sheet"]["vehicle_positions"][0]["recognized_value"], 100000)

    def test_unconfirmed_vehicle_loans_are_excluded_from_debt_and_recurring_emi(self):
        self.profile()
        for verification in ("estimated", "needs_review"):
            self.loan(verification_status=verification, auto_detected=True, verification_source="emi_pattern")

        _, networth = self.assert_accounting(assets=100000, debt=0)

        self.assertEqual(networth["loan_breakdown"], {})

    def test_foreclosure_pending_retains_debt_and_closure_preserves_vehicle_ownership(self):
        self.profile()
        loan = self.loan()
        self.assert_accounting(assets=100000, debt=40000, emi=2500)
        loan.status = "foreclosure_pending"
        loan.save(update_fields=["status", "updated_at"])
        self.assert_accounting(assets=100000, debt=40000, pending=40000)
        for closed_status in ("foreclosed", "closed", "prepaid"):
            with self.subTest(status=closed_status):
                loan.status = closed_status
                loan.is_active = False
                loan.save(update_fields=["status", "is_active", "updated_at"])
                self.assert_accounting(assets=100000, debt=0)

    def test_zero_value_vehicle_with_confirmed_loan_still_reports_actual_debt(self):
        self.profile(estimated_market_value=0)
        self.loan()

        self.assert_accounting(assets=0, debt=40000, emi=2500)

    def test_explicit_zero_loan_balance_does_not_create_debt_or_emi(self):
        self.profile()
        self.loan(remaining_balance=0)

        self.assert_accounting(assets=100000, debt=0)

    def test_operating_expenses_change_cashflow_without_creating_vehicle_liabilities(self):
        profile = self.profile(monthly_income_support=20000)
        self.running_cost_records(profile, service_cost=6000, trip_spend=6000)
        Expense.objects.create(
            user=self.user, amount=30000, direction="credit", category="income",
            classification="other", transaction_date=timezone.localdate(), description="Monthly Salary",
        )
        for category, amount in (("fuel", 3000), ("bills", 6000), ("travel", 6000)):
            Expense.objects.create(
                user=self.user, amount=amount, direction="debit", category=category,
                classification="expense", transaction_date=timezone.localdate(),
                description=f"Vehicle operating cost: {category}",
            )

        intelligence, _ = self.assert_accounting(assets=100000, debt=0)

        self.assertEqual(intelligence["summary"]["current_month_income"], 30000)
        self.assertEqual(intelligence["summary"]["current_month_expense"], 15000)
        self.assertEqual(intelligence["summary"]["current_month_outflow"], 15000)
        self.assertEqual(intelligence["summary"]["current_month_loans"], 0)
        self.assertEqual(intelligence["summary"]["current_month_net"], 15000)
        self.assertEqual(intelligence["baseline"]["observed_average_monthly_variable_spend"], 15000)

    def test_vehicle_edit_and_delete_refresh_warmed_financial_and_networth_caches(self):
        profile = self.profile()
        self.loan()
        self.assert_accounting(assets=100000, debt=40000, emi=2500)

        response = self.client.patch(
            f"/api/mobility/bikes/{profile.pk}/",
            {"estimated_market_value": 125000, "usage_pattern": "commercial", "monthly_income_support": 20000},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assert_accounting(assets=125000, debt=40000, emi=2500)
        response = self.client.patch(
            f"/api/mobility/bikes/{profile.pk}/",
            {"usage_pattern": "essential", "monthly_income_support": 99999},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertEqual(profile.estimated_market_value, 125000)
        self.assertEqual(response.json()["estimated_market_value"], 125000)
        self.assert_accounting(assets=125000, debt=40000, emi=2500)
        response = self.client.delete(f"/api/mobility/bikes/{profile.pk}/")
        self.assertEqual(response.status_code, 204, response.content)
        self.assert_accounting(assets=0, debt=40000, emi=2500)

    def test_catalog_refresh_on_partial_edit_preserves_recorded_financial_fields(self):
        profile = self.profile(
            usage_pattern="commercial", estimated_market_value=125000, monthly_income_support=7000,
        )
        url = f"/api/mobility/bikes/{profile.pk}/"
        response = self.client.patch(
            url, {"display_name": "Hunter 350", "make": "Royal Enfield"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertEqual(profile.catalog_key, "royal-enfield-hunter-350")
        self.assertEqual(profile.usage_pattern, "commercial")
        self.assertEqual(profile.estimated_market_value, 125000)
        self.assertEqual(profile.monthly_income_support, 7000)
        self.assertEqual(response.json()["estimated_market_value"], 125000)
        self.assert_accounting(assets=125000, debt=0)

        response = self.client.patch(
            url, {"estimated_market_value": 0, "monthly_income_support": 0, "usage_pattern": "essential"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response = self.client.patch(url, {"vehicle_number": "TEST123"}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        profile.refresh_from_db()
        self.assertEqual(profile.usage_pattern, "essential")
        self.assertEqual(profile.estimated_market_value, 0)
        self.assertEqual(profile.monthly_income_support, 0)
        self.assert_accounting(assets=0, debt=0)

    def test_other_users_vehicle_assets_loans_and_costs_do_not_change_own_accounting(self):
        self.profile()
        other = get_user_model().objects.create_user(username="other-vehicle-accounting")
        profile = self.profile(user=other, display_name="Other Owner", estimated_market_value=500000)
        self.running_cost_records(profile)
        self.loan(user=other, remaining_balance=25000)

        intelligence, _ = self.assert_accounting(assets=100000, debt=0)

        self.assertEqual([item["vehicle"] for item in intelligence["balance_sheet"]["vehicle_positions"]], ["Recorded Vehicle"])
