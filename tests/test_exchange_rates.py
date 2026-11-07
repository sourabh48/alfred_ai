"""Display-only conversion: stored ECB rates, the viewer's currency, approximate figures, records untouched."""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services import exchange_rates
from apps.integrations.models import VerifiedExternalInsight
from apps.integrations.services import verified_intelligence
from apps.investments.models import Investment
from apps.mobility.models import TravelPlan

RATES = {"INR": "104.8645", "USD": "1.1165", "GBP": "0.83415"}


def store_table(days_old=0, rates=RATES):
    return VerifiedExternalInsight.objects.create(
        scope="fx", cache_key="ecb-daily", title="ECB reference exchange rates", source_name="European Central Bank via Frankfurter",
        source_url=verified_intelligence.FX_SOURCE_URL, stale_after=timezone.now() + timedelta(hours=12),
        payload={"base": "EUR", "date": (timezone.localdate() - timedelta(days=days_old)).isoformat(), "rates": {"EUR": "1", **rates}})


def no_network(*args, **kwargs):
    raise AssertionError("a page read must never fetch rates")


class ConversionTests(TestCase):
    def test_cross_rate_maths_is_decimal_and_rounded_to_cents(self):
        store_table()
        table = exchange_rates.rate_table()
        self.assertEqual(exchange_rates.convert("100", "USD", "INR", table), Decimal("9392.25"))  # 100 * 104.8645 / 1.1165
        self.assertEqual(exchange_rates.convert("10.005", "INR", "INR", table), Decimal("10.01"))
        self.assertEqual(exchange_rates.convert("1000", None, "USD", table), Decimal("10.65"))  # not recorded counts as INR
        self.assertIsNone(exchange_rates.convert("5", "USD", "JPY", table))  # no rate, no guess
        self.assertIsNone(exchange_rates.convert("5", "USD", "INR", None))
        self.assertFalse(table["stale"])
        store_table(days_old=10)
        self.assertTrue(exchange_rates.rate_table()["stale"])

    def test_viewer_currency_prefers_choice_then_country_then_browser_language(self):
        user = SimpleNamespace(display_currency=None, country="")
        self.assertEqual(exchange_rates.display_currency(user, ""), ("INR", "default"))
        self.assertEqual(exchange_rates.display_currency(user, "en-GB,en;q=0.8"), ("GBP", "language"))
        self.assertEqual(exchange_rates.display_currency(user, "zz;;,--,de"), ("INR", "default"))
        user.country = "Germany"
        self.assertEqual(exchange_rates.display_currency(user, "en-GB"), ("EUR", "country"))
        user.display_currency = "JPY"
        self.assertEqual(exchange_rates.display_currency(user, "en-GB"), ("JPY", "chosen"))
        user.display_currency = "XXX"
        self.assertEqual(exchange_rates.display_currency(user, ""), ("EUR", "country"))

    def test_fetch_keeps_valid_tables_and_rejects_bad_ones_without_losing_the_old_one(self):
        good = {"amount": 1.0, "base": "EUR", "date": timezone.localdate().isoformat(), "rates": {"INR": 104.8645, "USD": 1.1165}}
        bad = {**good, "rates": {"INR": 104.8, "USD": -1}}
        with patch("alfred_ai.services.public_http.request", return_value=SimpleNamespace(json=lambda: good)) as fetch:
            verified_intelligence.exchange_rates(force=True)
        self.assertNotIn("params", fetch.call_args.kwargs)  # nothing about the owner is sent
        self.assertEqual(exchange_rates.rate_table()["rates"]["USD"], Decimal("1.1165"))
        with patch("alfred_ai.services.public_http.request", return_value=SimpleNamespace(json=lambda: bad)):
            verified_intelligence.exchange_rates(force=True)
        self.assertEqual(exchange_rates.rate_table()["rates"]["USD"], Decimal("1.1165"))


@patch("alfred_ai.services.public_http.request", no_network)
class ApproximateApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-fx-owner")
        self.client.force_login(self.owner)

    def add_investment(self, **fields):
        body = {"asset_type": "equity", "asset_name": "Synthetic fund", "invested_amount": "100.00", "current_value": "100.00", "monthly_sip": "0", **fields}
        self.assertEqual(self.client.post("/api/investments/", body, content_type="application/json").status_code, 201)

    def test_investments_show_approximate_figures_and_records_keep_their_currency(self):
        self.add_investment(currency="INR", current_value="1000.00")
        self.add_investment(currency="USD")
        before = list(Investment.objects.values_list("currency", "current_value"))
        summary = self.client.get("/api/investments/summary/").json()["summary"]
        self.assertIsNone(summary["other_currencies"][0]["approximate"])  # no table stored yet
        self.assertEqual((summary["display_currency"]["rate_date"], summary["display_currency"]["totals"]["total_value"]), (None, None))
        store_table()
        summary = self.client.get("/api/investments/summary/").json()["summary"]
        self.assertEqual(summary["total_value"], 1000.0)  # rupee totals unchanged
        self.assertEqual(summary["other_currencies"][0]["approximate"]["total_value"], "9392.25")
        self.assertEqual(summary["display_currency"]["totals"]["total_value"], "10392.25")
        self.assertEqual(summary["display_currency"]["currency"], "INR")
        self.assertEqual(list(Investment.objects.values_list("currency", "current_value")), before)

    def test_profile_choice_drives_loans_and_travel(self):
        store_table()
        self.assertEqual(self.client.patch("/api/users/profile/", {"display_currency": "XXX"}, content_type="application/json").status_code, 400)
        profile = self.client.patch("/api/users/profile/", {"display_currency": "USD"}, content_type="application/json").json()
        self.assertEqual(profile["display_currency_in_use"], {"currency": "USD", "basis": "chosen"})
        loan = {"loan_type": "personal", "lender": "Synthetic Lender", "principal": "10000.00", "interest_rate": 10, "emi": "500.00",
                "tenure_months": 24, "remaining_balance": "8000.00", "start_date": "2026-01-01", "currency": "GBP"}
        self.assertEqual(self.client.post("/api/loans/", loan, content_type="application/json").status_code, 201)
        summary = self.client.get("/api/loans/summary/").json()["summary"]
        group = summary["other_currencies"][0]
        self.assertEqual(group["approximate"]["currency"], "USD")
        self.assertEqual(Decimal(group["approximate"]["monthly_emi"]), (Decimal("500") * Decimal("1.1165") / Decimal("0.83415")).quantize(Decimal("0.01")))
        TravelPlan.objects.create(user=self.owner, title="Synthetic trip", budget=Decimal("20000.00"), budget_currency="INR")
        plan = self.client.get("/api/mobility/dashboard/").json()["travel_plans"][0]
        self.assertEqual(plan["approximate"], {"currency": "USD", "budget": "212.94"})
        self.assertEqual(self.client.patch("/api/users/profile/", {"display_currency": ""}, content_type="application/json").json()["display_currency"], None)
