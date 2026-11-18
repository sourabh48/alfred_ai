"""The 16 Nov 2026 investment audit's reproduced defects, asserted as corrected behaviour (the probes recorded the bugs)."""
from datetime import date, timedelta
from decimal import Decimal as D
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.investments.models import Investment
from apps.investments.serializers import InvestmentSerializer
from apps.investments.services import fund_prices
from apps.investments.services.beginner_guide import beginner_guide
from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service as service
from apps.investments.services.research_challenge import parse_challenge
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from apps.investments.services.research_packet import build_packet, fetch_fundamentals
from tests.test_research_packet import RISING, _fund, _prices


class ResearchEvidenceRegressions(SimpleTestCase):
    def test_old_prices_and_statements_are_not_rated_or_valued(self):
        packet = build_packet("SYNTH.NS", _fund(), _prices(RISING))  # prices end 2025-09-07
        self.assertEqual(packet["beginner"]["lean"], "not_enough")
        self.assertNotEqual(packet["valuation"]["status"], "estimated")

    def test_future_statements_are_dropped_by_the_provider_parser(self):
        response = MagicMock()
        response.json.return_value = {"timeseries": {"result": [{"meta": {"type": ["annualTotalRevenue"]},
            "annualTotalRevenue": [{"asOfDate": "2099-03-31", "currencyCode": "INR", "reportedValue": {"raw": 1200}}]}]}}
        with patch("alfred_ai.services.public_http.request", return_value=response):
            rows = fetch_fundamentals("SYNTH.NS")
        self.assertEqual(rows.get("TotalRevenue", []), [])

    def test_mixed_statement_currencies_give_no_ratio_or_valuation(self):
        funds = _fund()
        funds["NetIncome"] = [(day, amount, "USD") for day, amount, currency in funds["NetIncome"]]
        today = date(2025, 9, 8)
        with patch("apps.investments.services.research_packet.timezone.localdate", return_value=today):
            packet = build_packet("SYNTH.NS", funds, _prices(RISING))
        self.assertIsNone(packet["metrics"].get("net_margin_pct"))
        self.assertNotEqual(packet["valuation"]["status"], "estimated")

    def test_leap_day_period_builds_a_packet(self):
        packet = build_packet("SYNTH.NS", {"TotalRevenue": [(date(2024, 2, 29), D(100), "INR")]}, {})
        self.assertEqual(packet["latest_period_end"], "2024-02-29")

    def test_model_point_with_wrong_json_type_is_dropped_not_crashed(self):
        points = {"F1": {"point": "Revenue grew", "as_of": "2025-03-31"}}
        with self.assertRaises(EmbeddingUnavailable):  # the controlled "model unavailable" path, not a TypeError
            parse_challenge('{"objections":[{"point":["F1"],"why":"Cyclical earnings"}]}', points)
        result = parse_challenge('{"objections":[{"point":["F1"],"why":"Cyclical earnings"},{"point":"F1","why":"Cyclical earnings"}]}', points)
        self.assertEqual((len(result["objections"]), result["dropped"]), (1, 1))

    def test_model_advice_and_spelled_out_promises_are_dropped(self):
        with self.assertRaises(EmbeddingUnavailable):
            parse_challenge('{"overlooked":["Buy now with all your savings; returns will double."]}', {})
        for promise in ("Returns will double soon.", "Guaranteed gains ahead.", "A risk-free compounder."):
            result = parse_challenge('{"overlooked":["%s","Debt could weigh on margins."]}' % promise, {})
            self.assertEqual((result["overlooked"], result["dropped"]), (["Debt could weigh on margins."], 1), promise)


class FundAndPortfolioRegressions(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("investment-audit-synthetic")
        self.fund = Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Synthetic debt fund",
                                              currency="INR", invested_amount=100, current_value=100, units=10, amfi_scheme_code="123456")

    def refresh(self, day):
        with patch.object(service, "_get_amfi_latest_nav_report", return_value={"items": [{
                "scheme_code": "123456", "scheme_name": "Synthetic debt fund", "fund_house": "Synthetic AMC", "nav_date": day, "nav": D(8)}]}):
            fund_prices.refresh_fund_values()
        self.fund.refresh_from_db()

    def test_stale_nav_keeps_the_recorded_value(self):
        self.refresh(timezone.localdate() - timedelta(days=30))
        self.assertEqual(self.fund.current_value, D(100))

    def test_unit_edit_revalues_at_the_known_nav(self):
        self.refresh(timezone.localdate())
        serializer = InvestmentSerializer(self.fund, data={"units": "20", "current_value": "80"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.refresh(timezone.localdate())
        self.assertEqual(self.fund.current_value, D(160))

    def test_sparse_old_history_gives_no_guidance(self):
        rows = [{"scheme_code": "123456", "nav_date": timezone.localdate() - timedelta(days=n),
                 "scheme_name": "Synthetic debt fund", "nav": D(10)} for n in (45, 44)]
        with patch.object(service, "_get_amfi_history_report", return_value={"series": rows}):
            result = beginner_guide(self.user, {"available": False})["holdings"][0]
        self.assertEqual(result["action"], "unknown")

    def test_unclassified_fund_is_unknown_exposure_not_equity_and_hybrid(self):
        mix = service._portfolio_mix(self.user)
        self.assertEqual((mix["equity_pct"], mix["debt_pct"]), (0.0, 0.0))
        self.assertEqual(mix.get("unknown_pct"), 100.0)
        # Unknown exposure neither penalises nor rewards a candidate category.
        self.assertEqual(service._diversification_fit_score("debt", mix), service._diversification_fit_score("equity_core", mix))
