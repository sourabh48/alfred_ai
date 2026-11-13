"""INV-05: fund holdings follow AMFI's daily NAV automatically, and Home says what changed. Synthetic data only."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.investments.models import Investment
from apps.investments.services import fund_prices


def report(nav="45.1235", days_ago=1, code="120503"):
    return {"items": [{"scheme_code": code, "scheme_name": "Synthetic Bluechip Fund - Direct Plan - Growth", "fund_house": "Synthetic AMC",
                       "category": "Open Ended Schemes(Equity Scheme - Large Cap Fund)", "nav": Decimal(nav),
                       "nav_date": timezone.localdate() - timedelta(days=days_ago)}], "evidence": {}}


class FundPriceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("synthetic-fund-owner", password="pw-synthetic-1")
        self.fund = Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Synthetic Bluechip", currency="INR",
                                              invested_amount="10000.00", current_value="10000.00", amfi_scheme_code="120503", units="250.5000")
        self.latest = patch.object(fund_prices.portfolio_intelligence_service, "_get_amfi_latest_nav_report", return_value=report())
        self.latest.start(); self.addCleanup(self.latest.stop)

    def test_value_follows_the_nav_once_per_new_price_and_keeps_the_value_before(self):
        untouched = [Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="No units", currency="INR",
                                               current_value="500.00", amfi_scheme_code="120503"),
                     Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Dollar", currency="USD",
                                               current_value="500.00", amfi_scheme_code="120503", units="1")]
        self.assertEqual(fund_prices.refresh_fund_values(), {"checked": 1, "updated": 1})
        self.fund.refresh_from_db()
        self.assertEqual(self.fund.current_value, Decimal("11303.44"))  # 250.5 x 45.1235 = 11303.43675, rounded HALF_UP
        self.assertEqual((self.fund.value_before_nav, self.fund.nav), (Decimal("10000.00"), Decimal("45.1235")))
        self.assertEqual(fund_prices.refresh_fund_values()["updated"], 0)  # same price date: nothing changes
        for item in untouched:
            item.refresh_from_db(); self.assertEqual(item.current_value, Decimal("500.00"))
        self.latest.stop()
        with patch.object(fund_prices.portfolio_intelligence_service, "_get_amfi_latest_nav_report", return_value=report("44", days_ago=0)):
            fund_prices.refresh_fund_values()
        self.latest.start()
        self.fund.refresh_from_db()
        self.assertEqual((self.fund.value_before_nav, self.fund.current_value), (Decimal("11303.44"), Decimal("11022.00")))

    def test_home_tells_the_owner_and_search_finds_funds_by_name(self):
        fund_prices.refresh_fund_values()
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/"), "1 fund revalued from AMFI prices")
        found = self.client.get("/api/investments/funds/", {"q": "synthetic bluechip direct"}).json()["funds"]
        self.assertEqual([fund["scheme_code"] for fund in found], ["120503"])
        self.assertEqual(self.client.get("/api/investments/funds/", {"q": "zz"}).json()["funds"], [])
        self.client.logout()
        self.assertIn(self.client.get("/api/investments/funds/", {"q": "bluechip"}).status_code, (401, 403))

    def test_the_fund_code_and_units_are_checked_when_saved(self):
        self.client.force_login(self.user)
        base = {"asset_type": "mutual_fund", "asset_name": "Synthetic", "invested_amount": 100, "current_value": 100, "currency": "INR"}
        self.assertEqual(self.client.post("/api/investments/", base | {"amfi_scheme_code": "abc"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post("/api/investments/", base | {"units": "-1"}, content_type="application/json").status_code, 400)
        saved = self.client.post("/api/investments/", base | {"amfi_scheme_code": "120503", "units": "1.5", "nav": "999"}, content_type="application/json")
        self.assertEqual(saved.status_code, 201, saved.content)
        self.assertIsNone(saved.json()["nav"])  # set only by AMFI, never by the form
