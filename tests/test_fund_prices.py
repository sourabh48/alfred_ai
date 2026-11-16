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
        self.assertEqual(fund_prices.refresh_fund_values(), {"checked": 1, "updated": 1, "without_fresh_price": 0})
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


def price(nav="8", days_ago=0, **extra):
    return {"scheme_code": "123456", "scheme_name": "Synthetic Fund - Direct Plan - Growth", "fund_house": "Synthetic AMC",
            "nav": nav if not isinstance(nav, str) else Decimal(nav), "nav_date": timezone.localdate() - timedelta(days=days_ago)} | extra


class FundEvidenceTests(TestCase):
    """A holding changes only on fresh, agreed, valid evidence, and stays consistent with its units and fund."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("synthetic-fund-evidence", password="pw-synthetic-2")
        self.fund = Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Synthetic", currency="INR",
                                              invested_amount=100, current_value=100, units=10, amfi_scheme_code="123456")

    def refresh(self, *items):
        report = {"items": list(items), "evidence": {}}
        with patch.object(fund_prices.portfolio_intelligence_service, "_get_amfi_latest_nav_report", return_value=report):
            result = fund_prices.refresh_fund_values()
        self.fund.refresh_from_db()
        return result

    def test_stale_future_invalid_missing_and_conflicting_prices_change_nothing(self):
        limit = fund_prices.WATCHLIST_NAV_MAX_AGE_DAYS
        cases = {"stale": [price(days_ago=100)], "just too old": [price(days_ago=limit + 1)], "future": [price(days_ago=-1)],
                 "zero": [price("0")], "negative": [price("-8")], "not a number": [price(Decimal("NaN"))], "float": [price(8.0)],
                 "text date": [price() | {"nav_date": "2026-11-15"}], "missing": [],
                 "conflicting": [price("8"), price("9")]}
        for name, items in cases.items():
            with self.subTest(name):
                self.assertEqual(self.refresh(*items), {"checked": 1, "updated": 0, "without_fresh_price": 1})
                self.assertEqual((self.fund.current_value, self.fund.nav, self.fund.nav_date, self.fund.value_before_nav),
                                 (Decimal("100.00"), None, None, None))
                self.assertEqual(fund_prices.nav_state(self.fund), "waiting")
        self.assertEqual(self.refresh(price(days_ago=limit))["updated"], 1)  # the oldest accepted age
        self.assertEqual((self.fund.current_value, fund_prices.nav_state(self.fund)), (Decimal("80.00"), "current"))
        self.assertEqual(self.refresh(price(days_ago=limit), price(days_ago=limit))["updated"], 0)  # the same row twice is not a conflict

    def test_a_holding_whose_price_has_gone_old_says_so(self):
        old = timezone.localdate() - timedelta(days=30)
        Investment.objects.filter(pk=self.fund.pk).update(nav=Decimal("8"), nav_date=old, current_value=Decimal("80"))
        self.client.force_login(self.user)
        row = self.client.get(f"/api/investments/{self.fund.pk}/").json()
        self.assertEqual((row["nav_state"], row["nav_date"], row["current_value"]), ("stale", old.isoformat(), 80.0))
        plain = Investment.objects.create(user=self.user, asset_type="equity", asset_name="No fund code", currency="INR", current_value=5)
        self.assertEqual(self.client.get(f"/api/investments/{plain.pk}/").json()["nav_state"], "")

    def test_editing_units_through_the_api_keeps_value_and_totals_consistent(self):
        self.refresh(price("8"))
        self.assertEqual((self.fund.current_value, self.fund.value_before_nav), (Decimal("80.00"), Decimal("100.00")))
        self.client.force_login(self.user)
        total = lambda: Decimal(str(self.client.get("/api/investments/summary/").json()["summary"]["total_value"]))
        self.assertEqual(total(), Decimal("80"))
        edited = self.client.patch(f"/api/investments/{self.fund.pk}/", {"units": "20", "current_value": 80}, content_type="application/json")
        self.assertEqual(edited.status_code, 200, edited.content)
        self.assertEqual((edited.json()["current_value"], edited.json()["value_before_nav"]), (160.0, None))  # 20 x 8, at once
        self.assertEqual(total(), Decimal("160"))
        for _ in range(2):  # repeated refreshes with the same price: nothing left to correct
            self.assertEqual(self.refresh(price("8"))["updated"], 0)
        self.assertEqual((self.fund.units, self.fund.current_value), (Decimal("20"), Decimal("160.00")))
        self.assertNotContains(self.client.get("/"), "revalued from AMFI prices")  # a units edit is not a price move
        # A value typed over the priced one is put right by the next refresh, on the same price date.
        Investment.objects.filter(pk=self.fund.pk).update(current_value=Decimal("1"), value_before_nav=Decimal("150"))
        self.assertEqual(self.refresh(price("8"))["updated"], 1)
        self.assertEqual((self.fund.current_value, self.fund.value_before_nav), (Decimal("160.00"), Decimal("150.00")))
        too_big = self.client.patch(f"/api/investments/{self.fund.pk}/", {"units": "99999999999999"}, content_type="application/json")
        self.assertEqual(too_big.status_code, 400)
        self.fund.refresh_from_db()
        self.assertEqual((self.fund.units, self.fund.current_value), (Decimal("20"), Decimal("160.00")))  # rolled back whole

    def test_changing_the_fund_or_currency_drops_the_old_price_evidence(self):
        self.refresh(price("8"))
        self.client.force_login(self.user)
        for change in ({"amfi_scheme_code": "654321"}, {"currency": "USD"}, {"amfi_scheme_code": ""}):
            with self.subTest(change=change):
                Investment.objects.filter(pk=self.fund.pk).update(amfi_scheme_code="123456", currency="INR", nav=Decimal("8"),
                    nav_date=timezone.localdate(), current_value=Decimal("80"), value_before_nav=Decimal("100"))
                saved = self.client.patch(f"/api/investments/{self.fund.pk}/", change, content_type="application/json").json()
                self.assertEqual((saved["nav"], saved["nav_date"], saved["value_before_nav"], saved["current_value"]), (None, None, None, 80.0))
        Investment.objects.filter(pk=self.fund.pk).update(amfi_scheme_code="654321")
        self.assertEqual(self.refresh(price("8"))["without_fresh_price"], 1)  # the old fund's price does not value the new one
        self.assertEqual(self.refresh(price("3") | {"scheme_code": "654321"})["updated"], 1)
        self.assertEqual((self.fund.current_value, self.fund.nav), (Decimal("30.00"), Decimal("3")))

    def interleave(self, during, *items):
        """Run a refresh whose download finishes only after `during` has changed the database."""
        def download():
            during()
            return {item["scheme_code"]: item for item in items}
        with patch.object(fund_prices, "_latest", side_effect=download):
            result = fund_prices.refresh_fund_values()
        return result

    def test_a_newer_price_recorded_during_the_download_is_not_replaced_by_an_older_one(self):
        today = timezone.localdate()
        newer = lambda: Investment.objects.filter(pk=self.fund.pk).update(nav=Decimal("12"), nav_date=today, current_value=Decimal("120"))
        self.assertEqual(self.interleave(newer, price("8", days_ago=1))["updated"], 0)
        self.fund.refresh_from_db()
        self.assertEqual((self.fund.nav, self.fund.nav_date, self.fund.current_value), (Decimal("12"), today, Decimal("120.00")))

    def test_an_edit_or_deletion_during_the_download_never_stops_the_other_holdings(self):
        other = Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Other", currency="INR",
                                          current_value=50, units=5, amfi_scheme_code="123456")
        gone = Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Gone", currency="INR",
                                         current_value=50, units=5, amfi_scheme_code="123456")
        def during():
            Investment.objects.filter(pk=self.fund.pk).update(units=Decimal("30"))  # edited: priced from the row as it is now
            gone.delete()
        self.assertEqual(self.interleave(during, price("8")), {"checked": 3, "updated": 2, "without_fresh_price": 0})
        self.fund.refresh_from_db(); other.refresh_from_db()
        self.assertEqual((self.fund.current_value, other.current_value), (Decimal("240.00"), Decimal("40.00")))
        untracked = lambda: Investment.objects.filter(pk=other.pk).update(amfi_scheme_code="")
        self.assertEqual(self.interleave(untracked, price("9"))["updated"], 1)
        other.refresh_from_db()
        self.assertEqual(other.current_value, Decimal("40.00"))  # no longer a priced fund: left alone
