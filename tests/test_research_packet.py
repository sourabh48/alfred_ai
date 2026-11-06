"""INVEST2-001 evidence packet: dated, sourced case for and against one stock; no rating, no writes."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from alfred_ai.services.public_http import PublicHTTPError
from apps.investments.models import Investment, ResearchDecision
from apps.investments.services.research_packet import build_packet, fetch_fundamentals, price_metrics

Y1, Y2 = date(2024, 3, 31), date(2025, 3, 31)
D = Decimal


def _fund(currency="INR", **override):
    rows = {"TotalRevenue": [(Y1, D(1000)), (Y2, D(1200))], "NetIncome": [(Y1, D(150)), (Y2, D(180))],
            "FreeCashFlow": [(Y2, D(160))], "TotalDebt": [(Y2, D(200))], "StockholdersEquity": [(Y2, D(1000))],
            "CurrentAssets": [(Y2, D(600))], "CurrentLiabilities": [(Y2, D(300))], "DilutedAverageShares": [(Y2, D(10))]}
    rows.update(override)
    return {name: [(d, v, currency) for d, v in values] for name, values in rows.items()}


def _prices(closes, currency="INR"):
    return {"close": closes, "timestamp": [1735689600 + 86400 * i for i in range(len(closes))], "currency": currency}


RISING = [100 + i * 0.5 for i in range(250)]  # last close 224.5, above its 200-day average


class PacketRuleTests(SimpleTestCase):
    def test_known_metrics_and_both_sides(self):
        p = build_packet("SYNTH.NS", _fund(), _prices(RISING))
        m = p["metrics"]
        self.assertEqual((m["revenue_growth_pct"]["value"], m["net_margin_pct"]["value"], m["free_cash_flow_to_profit"]["value"],
                          m["debt_to_equity"]["value"], m["current_ratio"]["value"]), (D("20.0"), D("15.0"), D("0.89"), D("0.20"), D("2.00")))
        self.assertEqual(m["revenue_growth_pct"]["as_of"], "2025-03-31")
        self.assertTrue(all(point["as_of"] for point in p["bullish"] + p["bearish"]))
        self.assertEqual(len(p["bullish"]), 6)  # growth, margin, cash, debt, liquidity, trend
        self.assertEqual(p["bearish"], [])
        # 224.5 x 10 shares / 180 profit
        self.assertEqual((p["valuation"]["status"], p["valuation"]["price_to_earnings"]), ("estimated", D("12.5")))
        self.assertNotIn("rating", p)
        self.assertIn("Nothing is bought, sold or changed.", p["limits"])

    def test_ratios_never_mix_years(self):
        # Profit only for the older year: margin uses 2024 revenue, not the newer 2025 figure
        p = build_packet("SYNTH.NS", _fund(NetIncome=[(Y1, D(150))]), {})
        self.assertEqual((p["metrics"]["net_margin_pct"]["value"], p["metrics"]["net_margin_pct"]["as_of"]), (D("15.0"), "2024-03-31"))
        self.assertNotIn("free_cash_flow_to_profit", p["metrics"])  # no shared year for cash flow and profit
        self.assertIn("A year of daily prices", p["missing_evidence"])

    def test_valuation_abstains_on_currency_mismatch_and_losses(self):
        mismatch = build_packet("SYNTH", _fund(currency="USD"), _prices(RISING, "INR"))["valuation"]
        self.assertEqual(mismatch["status"], "unavailable")
        self.assertIn("does not convert", mismatch["reason"])
        loss = build_packet("SYNTH", _fund(NetIncome=[(Y1, D(-50)), (Y2, D(-60))]), _prices(RISING))
        self.assertEqual(loss["valuation"]["status"], "unavailable")
        self.assertTrue(any("lost money" in point["point"] for point in loss["bearish"]))

    def test_price_risk_screens(self):
        crash = [200.0] * 20 + [200 - i * 3 for i in range(40)]  # falls 58.5% from the peak
        metrics = price_metrics(crash, list(range(len(crash))))
        self.assertLess(metrics["max_drawdown_pct"], -30)
        self.assertIsNone(metrics["above_200_day_average"])  # fewer than 200 closes
        self.assertEqual(price_metrics([1.0] * 29, list(range(29))), {})
        bear = build_packet("SYNTH", {}, _prices(crash))["bearish"]
        self.assertTrue(any(point["metric"] == "max_drawdown_pct" for point in bear))

    def test_fundamentals_parser_keeps_dated_numbers_only(self):
        payload = {"timeseries": {"result": [
            {"meta": {"type": ["annualTotalRevenue"]}, "annualTotalRevenue": [
                {"asOfDate": "2025-03-31", "currencyCode": "inr", "reportedValue": {"raw": 1200}},
                {"asOfDate": None, "reportedValue": {"raw": 5}}, {"asOfDate": "2024-03-31", "reportedValue": {}}]},
            {"meta": {"type": ["trailingPeRatio"]}, "trailingPeRatio": [{"asOfDate": "2025-03-31", "reportedValue": {"raw": 9}}]}]}}
        response = MagicMock()
        response.json.return_value = payload
        with patch("alfred_ai.services.public_http.request", return_value=response) as request:
            self.assertEqual(fetch_fundamentals("SYNTH.NS"), {"TotalRevenue": [(Y2, D(1200), "INR")]})
        self.assertTrue(request.call_args.args[1].startswith("https://query1.finance.yahoo.com/"))


class PacketApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="packet", password="pw-synthetic-1")
        self.other = get_user_model().objects.create_user(username="packet-other", password="pw-synthetic-2")
        self.client.force_login(self.user)
        self.holding = Investment.objects.create(user=self.user, asset_name="Synth Ltd", asset_type="equity",
                                                 invested_amount=D(1000), current_value=D(3000), currency="INR")
        Investment.objects.create(user=self.user, asset_name="Fund", asset_type="mutual_fund",
                                  invested_amount=D(1000), current_value=D(7000), currency="INR")
        self.stranger = Investment.objects.create(user=self.other, asset_name="Theirs", asset_type="equity",
                                                  invested_amount=D(1), current_value=D(1), currency="INR")

    def _get(self, **params):
        with patch("apps.investments.services.research_packet.fetch_fundamentals", return_value=_fund()), \
                patch("apps.investments.services.research_packet.fetch_prices", return_value=_prices(RISING)):
            return self.client.get("/api/investments/research/packet/", params)

    def test_packet_with_holding_weight_and_no_writes(self):
        before = (Investment.objects.count(), ResearchDecision.objects.count(), self.holding.current_value)
        response = self._get(symbol="synth.ns", holding=self.holding.pk)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual((body["symbol"], body["portfolio"]["weight_pct"]), ("SYNTH.NS", 30.0))
        self.holding.refresh_from_db()
        self.assertEqual((Investment.objects.count(), ResearchDecision.objects.count(), self.holding.current_value), before)

    def test_bad_input_other_owner_and_upstream_failure(self):
        self.assertEqual(self._get(symbol="../etc").status_code, 400)
        self.assertEqual(self._get(symbol="SYNTH", holding="1; drop").status_code, 400)
        self.assertEqual(self._get(symbol="SYNTH", holding=self.stranger.pk).status_code, 404)
        with patch("apps.investments.services.research_packet.fetch_fundamentals", side_effect=PublicHTTPError("upstream_status")):
            failed = self.client.get("/api/investments/research/packet/", {"symbol": "OTHER"})
        self.assertEqual(failed.status_code, 502)
        self.client.logout()
        self.assertIn(self._get(symbol="SYNTH").status_code, (401, 403))
