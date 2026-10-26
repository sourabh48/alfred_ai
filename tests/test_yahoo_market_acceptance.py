"""Synthetic Yahoo transport contracts, not live/exchange/provider acceptance."""
import copy
from datetime import timedelta
from decimal import Decimal
import json
from urllib.parse import unquote
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.integrations.models import VerifiedExternalInsight
from apps.integrations.services.verified_intelligence import VerifiedIntelligenceService
from apps.investments.models import Investment
from tests.test_investment_market_acceptance import SyntheticAMFI, source_result


def market_payload(**values):
    """Valid provenance for existing refresh-routing fixtures, with explicit values."""
    observed = timezone.now() - timedelta(hours=1)
    return {"nifty_close": 1039.0, "one_month_return_pct": 2.97, "india_vix": 20.39,
        "market_schema_version": 2, "market_observations": {
            "nifty": {"symbol": "^NSEI", "observed_at": observed.isoformat(),
                "baseline_at": (observed - timedelta(days=30)).isoformat(), "observation_count": 40},
            "vix": {"symbol": "^INDIAVIX", "observed_at": observed.isoformat(), "observation_count": 40}}, **values}


class SyntheticYahoo:
    def __init__(self, *, end=None):
        self.end = end or timezone.now().replace(microsecond=0) - timedelta(hours=1)
        self.charts = {}
        for symbol, price in (("^NSEI", 1000), ("^INDIAVIX", 20)):
            stamps = [int((self.end - timedelta(days=39 - i)).timestamp()) for i in range(40)]
            prices = [price + i * (1 if symbol == "^NSEI" else .01) for i in range(40)]
            self.charts[symbol] = {"chart": {"error": None, "result": [{"meta": {"symbol": symbol},
                "timestamp": stamps, "indicators": {"quote": [{"close": prices}]}}]}}
        self.calls = []
        self.fail = False
        self.amfi = SyntheticAMFI()

    def __call__(self, method, url, **kwargs):
        if not url.startswith("https://query1.finance.yahoo.com/v8/finance/chart/"):
            return self.amfi(method, url, **kwargs)
        self.calls.append((method, url, kwargs))
        symbol = unquote(url.rsplit("/", 1)[-1])
        assert method == "GET" and symbol in self.charts, "Unexpected synthetic Yahoo request"
        if self.fail:
            raise PublicHTTPError("synthetic_unavailable")
        return PublicResponse(json.dumps(self.charts[symbol]).encode(), "application/json")


class YahooMarketAcceptanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.service = VerifiedIntelligenceService()
        self.transport = SyntheticYahoo()
        self.enterContext(patch("apps.integrations.services.verified_intelligence.public_http.request", side_effect=self.transport))

    def chart(self, symbol="^NSEI"):
        return self.transport.charts[symbol]["chart"]["result"][0]

    def test_symbol_dates_and_decimal_lookback_are_retained(self):
        result = self.service.market_snapshot()
        self.assertEqual(result.evidence["status"], "fresh")
        self.assertEqual(result.payload["one_month_return_pct"], float(round((Decimal(1039) / Decimal(1009) - 1) * 100, 2)))
        info = result.payload["market_observations"]["nifty"]
        self.assertEqual(info["symbol"], "^NSEI")
        self.assertEqual(info["observation_count"], 40)
        self.assertEqual(info["baseline_at"], (self.transport.end - timedelta(days=30)).isoformat())
        self.assertIn(self.transport.end.isoformat(), result.evidence["summary"])
        self.assertIn("not independently verified exchange closing prices", result.evidence["summary"])

    def test_missing_interior_close_keeps_timestamp_pairing(self):
        self.chart()["indicators"]["quote"][0]["close"][10] = None
        result = self.service._fetch_yahoo_chart("%5ENSEI", "3mo", "1d")
        self.assertEqual(len(result["close"]), 39)
        self.assertEqual(len(result["timestamp"]), 39)
        self.assertEqual(result["close"][10], Decimal(1011))
        self.assertEqual(result["timestamp"][10], self.chart()["timestamp"][11])

    def test_unsorted_identical_duplicates_are_not_extra_observations(self):
        row = self.chart()
        row["timestamp"] = list(reversed(row["timestamp"])) + row["timestamp"][-1:]
        prices = row["indicators"]["quote"][0]["close"]
        row["indicators"]["quote"][0]["close"] = list(reversed(prices)) + prices[-1:]
        result = self.service.market_snapshot()
        self.assertEqual(result.payload["market_observations"]["nifty"]["observation_count"], 40)
        self.assertEqual(result.payload["nifty_close"], 1039)

    def test_wrong_missing_identity_error_and_malformed_shapes_are_rejected(self):
        original = copy.deepcopy(self.transport.charts["^NSEI"])
        mutations = [
            lambda body: body["chart"]["result"][0]["meta"].update(symbol="FOREIGN"),
            lambda body: body["chart"]["result"][0].pop("meta"),
            lambda body: body["chart"].update(error={"code": "Not Found"}),
            lambda body: body.update(chart=[]),
            lambda body: body["chart"]["result"][0]["timestamp"].pop(),
            lambda body: body["chart"]["result"][0].update(timestamp=None),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.transport.charts["^NSEI"] = copy.deepcopy(original)
                mutate(self.transport.charts["^NSEI"])
                with self.assertRaises(ValueError):
                    self.service._fetch_yahoo_chart("%5ENSEI", "3mo", "1d")

    def test_bad_prices_timestamps_latest_missing_and_duplicate_conflicts_are_rejected(self):
        original = copy.deepcopy(self.chart())
        for field, value in [("price", v) for v in (True, 0, -1, float("inf"), float("nan"), None)] + [
                ("time", True), ("time", -1), ("time", 1.5), ("time", int(timezone.now().timestamp()) + 3600), ("duplicate", 1)]:
            with self.subTest(field=field, value=value):
                row = copy.deepcopy(original)
                self.transport.charts["^NSEI"]["chart"]["result"] = [row]
                prices = row["indicators"]["quote"][0]["close"]
                if field == "price": prices[-1] = value
                elif field == "time": row["timestamp"][-1] = value
                else:
                    row["timestamp"].append(row["timestamp"][-1]); prices.append(prices[-1] + 1)
                with self.assertRaises(ValueError):
                    self.service._fetch_yahoo_chart("%5ENSEI", "3mo", "1d")

    def test_stale_either_instrument_and_missing_month_coverage_abstain(self):
        for symbol in ("^NSEI", "^INDIAVIX"):
            with self.subTest(symbol=symbol):
                old = SyntheticYahoo(end=timezone.now() - timedelta(days=8))
                self.transport.charts = copy.deepcopy(SyntheticYahoo().charts)
                self.transport.charts[symbol] = old.charts[symbol]
                self.assertEqual(self.service.market_snapshot(force=True).payload, {})
        cache.clear()
        self.transport.charts = SyntheticYahoo().charts
        self.chart()["timestamp"] = self.chart()["timestamp"][-10:]
        self.chart()["indicators"]["quote"][0]["close"] = self.chart()["indicators"]["quote"][0]["close"][-10:]
        self.assertEqual(self.service.market_snapshot(force=True).payload, {})

    def test_fresh_cache_reuses_valid_provenance_without_http(self):
        first = self.service.market_snapshot()
        self.transport.calls.clear()
        second = self.service.market_snapshot()
        self.assertTrue(second.cached)
        self.assertEqual(second.payload, first.payload)
        self.assertEqual(self.transport.calls, [])

    def test_two_dated_points_support_return_but_not_estimated_volatility(self):
        row = self.chart()
        row["timestamp"] = [row["timestamp"][9], row["timestamp"][-1]]
        prices = row["indicators"]["quote"][0]["close"]
        row["indicators"]["quote"][0]["close"] = [prices[9], prices[-1]]
        result = self.service.market_snapshot()
        self.assertEqual(result.evidence["status"], "fresh")
        self.assertEqual(result.payload["one_month_return_pct"], 2.97)
        self.assertIsNone(result.payload["realized_volatility_pct"])

    def test_legacy_numeric_cache_refreshes_instead_of_claiming_freshness(self):
        self.service._store(scope="market", cache_key="india-equity-volatility", title="Legacy fixture",
            source_name="Yahoo Finance", source_url="https://finance.yahoo.com/quote/%5ENSEI/", query="",
            payload={"nifty_close": 999}, summary="Legacy without observation dates", ttl=timedelta(hours=12), status="fresh", notes="synthetic")
        result = self.service.market_snapshot()
        self.assertEqual(result.payload["market_schema_version"], 2)
        self.assertEqual(len(self.transport.calls), 2)

    def test_observation_expiry_bounds_cache_and_outage_preserves_last_success(self):
        now = timezone.now()
        self.transport.charts = SyntheticYahoo(end=now - timedelta(days=7) + timedelta(seconds=10)).charts
        first = self.service.market_snapshot()
        self.assertEqual(first.evidence["status"], "fresh")
        self.assertLessEqual(first.evidence["stale_after"], (now + timedelta(seconds=11)).isoformat())
        record = VerifiedExternalInsight.objects.get(scope="market", is_active=True)
        self.assertEqual(record.stale_after.isoformat(), first.evidence["stale_after"])
        previous_success = first.evidence["last_refresh_success_at"]
        self.transport.fail = True
        with patch("django.utils.timezone.now", return_value=now + timedelta(seconds=20)):
            self.assertEqual(self.service.refresh_health_snapshot()["fresh_records"], 0)
            refresh = self.service.refresh_due_records(batch_size=1)
            self.assertEqual(refresh["processed"], 1)
            self.assertEqual(refresh["failed"], 1)
            failed = self.service.market_snapshot()
        self.assertEqual(failed.payload, {})
        self.assertNotEqual(failed.evidence["status"], "fresh")
        self.assertEqual(failed.evidence["last_refresh_success_at"], previous_success)

    def test_outages_open_existing_circuit_then_recover_without_partial_prices(self):
        self.service.market_snapshot()
        self.transport.calls.clear(); self.transport.fail = True
        for _ in range(3):
            self.assertEqual(self.service.market_snapshot(force=True).payload, {})
        self.assertEqual(len(self.transport.calls), 3)
        self.assertEqual(self.service.market_snapshot(force=True).payload, {})
        self.assertEqual(len(self.transport.calls), 3)
        cache.clear(); self.transport.fail = False
        self.assertEqual(self.service.market_snapshot(force=True).evidence["status"], "fresh")

    def test_investment_api_owner_totals_survive_provider_identity_outage_and_recovery(self):
        owner = get_user_model().objects.create_user(username="synthetic-yahoo-owner")
        foreign = get_user_model().objects.create_user(username="synthetic-yahoo-other")
        Investment.objects.create(user=owner, asset_name="PRIVATE-YAHOO-HOLDING", current_value="110.20", invested_amount="100.25")
        Investment.objects.create(user=foreign, asset_name="FOREIGN-YAHOO-HOLDING", current_value="999999.99")
        self.client.force_login(owner)
        self.enterContext(patch("apps.investments.services.portfolio_intelligence.verified_intelligence.world_bank_indicator", return_value=source_result({"latest_value": 4.5})))
        self.enterContext(patch("apps.investments.services.portfolio_intelligence.verified_intelligence.google_news_search", return_value=source_result({"items": []})))
        before = list(Investment.objects.values())
        first = self.client.get("/api/investments/summary/").json()
        self.assertTrue(first["watchlist"]["available"])
        self.assertEqual(first["summary"]["gain_loss"], 9.95)
        self.assertNotIn("FOREIGN-YAHOO-HOLDING", str(first))
        self.chart()["meta"]["symbol"] = "FOREIGN"
        self.service.market_snapshot(force=True); cache.clear()
        failed = self.client.get("/api/investments/summary/").json()
        self.assertFalse(failed["watchlist"]["available"])
        self.assertEqual(failed["summary"], first["summary"])
        self.transport.charts = SyntheticYahoo().charts; cache.clear()
        self.assertEqual(self.service.market_snapshot(force=True).evidence["status"], "fresh")
        self.assertEqual(list(Investment.objects.values()), before)
        self.assertNotIn("PRIVATE-YAHOO-HOLDING", str(self.transport.calls))
        now = timezone.now()
        self.transport.charts = SyntheticYahoo(end=now - timedelta(days=7) + timedelta(seconds=10)).charts
        self.service.market_snapshot(force=True); cache.clear()
        before_expiry = self.client.get("/api/investments/summary/").json()
        self.assertTrue(before_expiry["watchlist"]["available"])
        with patch("django.utils.timezone.now", return_value=now + timedelta(seconds=20)):
            after_expiry = self.client.get("/api/investments/summary/").json()
        self.assertTrue(after_expiry["_materialized"]["cached"])
        self.assertFalse(after_expiry["watchlist"]["available"])
        self.assertEqual(after_expiry["summary"], before_expiry["summary"])
        self.assertEqual(list(Investment.objects.values()), before)
