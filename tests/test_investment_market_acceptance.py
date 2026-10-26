"""Synthetic market observations; no live provider or real-account acceptance."""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.investments.models import Investment
from apps.investments.services.portfolio_intelligence import (
    AMFI_HISTORY_URL, AMFI_OPEN_NAV_URL, portfolio_intelligence_service as service,
)


SCHEME = "Synthetic Flexi Cap Fund - Direct Plan - Growth"


def source_result(payload, name="Yahoo Finance"):
    now = timezone.now()
    return SimpleNamespace(payload=payload, evidence={
        "source_name": name, "source_url": "https://finance.yahoo.com/quote/%5ENSEI/",
        "status": "fresh", "summary": "Synthetic provider fixture, not live data.",
        "fetched_at": now.isoformat(), "verified_at": now.isoformat(),
        "stale_after": (now + timedelta(hours=12)).isoformat(),
    })


class SyntheticAMFI:
    def __init__(self, *, days=60, end=None):
        end = end or timezone.localdate()
        self.rows = []
        for index in range(days + 1):
            day = end - timedelta(days=days - index)
            nav = Decimal("100.0001") + Decimal(index) / 10
            self.rows.append(f"990001;{SCHEME};SYNTH-ISIN-A;SYNTH-ISIN-B;{nav};;;{day:%d-%b-%Y}")
        self.latest = ("Open Ended Schemes(Equity Scheme - Flexi Cap Fund)\nSynthetic Fund House\n"
            f"990001;SYNTH-ISIN-A;SYNTH-ISIN-B;{SCHEME};{nav};{end:%d-%b-%Y}")
        self.fail = False
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        assert method == "GET" and url in {AMFI_OPEN_NAV_URL, AMFI_HISTORY_URL}, "Unexpected provider request"
        if self.fail:
            raise PublicHTTPError("synthetic_unavailable")
        text = self.latest if url == AMFI_OPEN_NAV_URL else "\n".join(self.rows)
        return PublicResponse(text.encode(), "text/plain")


class InvestmentMarketAcceptanceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.owner = get_user_model().objects.create_user(username="synthetic-market-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-market-other")
        self.client.force_login(self.owner)
        self.holding = Investment.objects.create(user=self.owner, asset_type="mutual_fund",
            asset_name="SYNTHETIC-PRIVATE-HOLDING", current_value="110.20", invested_amount="100.25", monthly_sip="1.01")
        Investment.objects.create(user=self.other, asset_type="equity", asset_name="FOREIGN-PRIVATE-HOLDING", current_value="999999.99")
        self.transport = SyntheticAMFI()
        self.market = source_result({"one_month_return_pct": 0, "india_vix": 14})
        self.enterContext(patch("apps.investments.services.portfolio_intelligence.public_http.request", side_effect=self.transport))
        self.enterContext(patch("apps.investments.services.portfolio_intelligence.verified_intelligence.market_snapshot", side_effect=lambda: self.market))
        self.enterContext(patch("apps.investments.services.portfolio_intelligence.verified_intelligence.world_bank_indicator",
            return_value=source_result({"latest_value": 4.5}, "World Bank")))
        self.enterContext(patch("apps.investments.services.portfolio_intelligence.verified_intelligence.google_news_search",
            return_value=source_result({"items": []}, "Synthetic news")))

    def test_fresh_numeric_quotes_keep_precision_identity_dates_and_holdings(self):
        before = list(Investment.objects.values())
        response = self.client.get("/api/investments/summary/")
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertTrue(payload["watchlist"]["available"])
        item = payload["watchlist"]["items"][0]
        self.assertEqual(item["scheme_code"], "990001")
        self.assertEqual(item["nav_source_value"], "106.0001")
        self.assertEqual(item["observation_count"], 61)
        self.assertEqual(item["history_days"], 60)
        self.assertEqual(item["nav_date"], timezone.localdate().isoformat())
        self.assertEqual(item["return_60d_pct"], float(round(Decimal(6) / Decimal("100.0001") * 100, 2)))
        self.assertEqual(payload["summary"]["total_value"], 110.20)
        self.assertEqual(payload["summary"]["gain_loss"], 9.95)
        self.assertNotIn("FOREIGN-PRIVATE-HOLDING", str(payload))
        self.assertEqual(list(Investment.objects.values()), before)
        self.assertNotIn("SYNTHETIC-PRIVATE-HOLDING", str(self.transport.calls))
        self.assertTrue(all(p["source_url"].startswith("https://") for p in item["proof"]))

    def test_stale_future_and_conflicting_identity_quotes_abstain(self):
        for kind in ("stale", "future", "identity", "latest_conflict", "history_conflict", "end_mismatch"):
            with self.subTest(kind=kind):
                cache.clear()
                self.transport = SyntheticAMFI(end=timezone.localdate() + timedelta(days=1 if kind == "future" else -8 if kind == "stale" else 0))
                if kind == "identity":
                    self.transport.rows[0] = self.transport.rows[0].replace("SYNTH-ISIN-A", "SYNTH-ISIN-X")
                elif kind == "latest_conflict":
                    self.transport.latest += "\n" + self.transport.latest.splitlines()[-1].replace("106.0001", "107.0001")
                elif kind == "history_conflict":
                    self.transport.rows.append(self.transport.rows[-1].replace("106.0001", "107.0001"))
                elif kind == "end_mismatch":
                    self.transport.latest = self.transport.latest.replace("106.0001", "107.0001")
                with patch("apps.investments.services.portfolio_intelligence.public_http.request", side_effect=self.transport):
                    result = service.build_short_horizon_watchlist(self.owner)
                self.assertFalse(result["available"])
                self.assertEqual(result["items"], [])

    def test_duplicate_dates_do_not_inflate_history_or_invent_sixty_day_returns(self):
        self.transport = SyntheticAMFI(days=35)
        self.transport.rows *= 2
        with patch("apps.investments.services.portfolio_intelligence.public_http.request", side_effect=self.transport):
            item = service.build_short_horizon_watchlist(self.owner)["items"][0]
        self.assertEqual(item["observation_count"], 36)
        self.assertEqual(item["history_days"], 35)
        self.assertIsNone(item["return_60d_pct"])
        self.assertNotIn("60-day drawdown", str(item["proof"]))

    def test_peak_to_trough_drawdown_includes_recovered_losses(self):
        today = timezone.localdate()
        metrics = service._series_metrics([
            {"nav": Decimal("100"), "nav_date": today - timedelta(days=60)},
            {"nav": Decimal("50"), "nav_date": today - timedelta(days=30)},
            {"nav": Decimal("110"), "nav_date": today},
        ])
        self.assertEqual(metrics["max_drawdown_pct"], -50)

    def test_repeated_sparse_points_do_not_satisfy_the_observation_minimum(self):
        self.transport.rows = self.transport.rows[::4] * 3
        self.assertFalse(service.build_short_horizon_watchlist(self.owner)["available"])

    def test_empty_response_is_failed_evidence_not_a_fresh_quote(self):
        self.transport.latest = "No observations in this synthetic response"
        result = service.build_short_horizon_watchlist(self.owner)
        self.assertFalse(result["available"])
        self.assertEqual(result["evidence"][1]["status"], "failed")

    def test_long_history_gaps_do_not_masquerade_as_recent_lookback_returns(self):
        self.transport.rows = self.transport.rows[:17] + self.transport.rows[-1:]
        self.assertFalse(service.build_short_horizon_watchlist(self.owner)["available"])

    def test_invalid_prices_never_become_observed_navs(self):
        for value in ("NaN", "Infinity", "-1", "0", "", "USD 12", "1,2", "1e9999"):
            with self.subTest(value=value):
                body = f"990001;A;B;{SCHEME};{value};{timezone.localdate():%d-%b-%Y}"
                self.assertEqual(service._parse_amfi_nav_report(body, history_mode=False), [])

    def test_missing_invalid_or_expired_yahoo_context_does_not_mean_zero_market(self):
        for value in (None, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                self.market.payload["india_vix"] = value
                self.assertFalse(service.build_short_horizon_watchlist(self.owner)["available"])
        self.market.payload["india_vix"] = 14
        self.market.evidence["stale_after"] = (timezone.now() - timedelta(seconds=1)).isoformat()
        self.assertFalse(service.build_short_horizon_watchlist(self.owner)["available"])
        context = service.get_market_trends_and_suggestions(self.owner)
        self.assertNotIn("Verified market context is", str(context["suggestions"]))

    def test_expired_source_is_not_reused_from_owner_summary_cache(self):
        now = timezone.now()
        self.market.evidence["stale_after"] = (now + timedelta(seconds=5)).isoformat()
        first = self.client.get("/api/investments/summary/").json()
        self.assertTrue(first["watchlist"]["available"])
        with patch("django.utils.timezone.now", return_value=now + timedelta(seconds=10)), patch("django.utils.timezone.localdate", return_value=timezone.localdate()):
            second = self.client.get("/api/investments/summary/").json()
        self.assertTrue(second["_materialized"]["cached"])
        self.assertFalse(second["watchlist"]["available"])
        self.assertNotIn("Verified market context is", str(second["market_context"]["suggestions"]))
        self.assertEqual(second["summary"], first["summary"])

    def test_outage_is_bounded_cached_and_recovers_without_portfolio_writes(self):
        before = list(Investment.objects.values())
        self.transport.fail = True
        for _ in range(2):
            self.assertFalse(service.build_short_horizon_watchlist(self.owner)["available"])
        self.assertEqual(len(self.transport.calls), 1)
        cache.clear()
        self.transport.fail = False
        self.assertTrue(service.build_short_horizon_watchlist(self.owner)["available"])
        self.assertEqual(list(Investment.objects.values()), before)
