"""NEW-2: a beginner gets three plain fund picks and Hold / Review / Sell for owned funds. Synthetic AMFI data only."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.investments.models import Investment
from apps.investments.services import beginner_guide as guide


def watch_item(code, name):
    return {"scheme_code": code, "scheme_name": name, "fund_house": "Synthetic AMC", "family_label": "Large cap", "nav_source_value": "45.1235",
            "nav_date": "2026-11-13", "realized_volatility_pct": 4.2, "return_30d_pct": 2.345, "history_days": 58, "max_drawdown_pct": -6.71}


def series(code, navs):
    today = timezone.localdate()
    return [{"scheme_code": code, "nav": Decimal(nav), "nav_date": today - timedelta(days=len(navs) - i)} for i, nav in enumerate(navs)]


class BeginnerGuideTests(TestCase):
    def test_signal_thresholds_measure_the_drop_from_the_recent_high(self):
        self.assertEqual(guide.holding_signal([Decimal("100"), Decimal("95")])[0], "hold")
        self.assertEqual(guide.holding_signal([Decimal("100"), Decimal("92")])[0], "review")   # exactly 8% below
        self.assertEqual(guide.holding_signal([Decimal("100"), Decimal("85")])[0], "sell")     # exactly 15% below
        self.assertIn("15.0% below", guide.holding_signal([Decimal("80"), Decimal("100"), Decimal("85")])[1])
        self.assertIsNone(guide.holding_signal([Decimal("100")]))

    def test_picks_and_owned_funds_are_plain_and_only_the_owners(self):
        owner, other = (get_user_model().objects.create_user(name) for name in ("synthetic-new-investor", "synthetic-other"))
        for user, name, code in ((owner, "Falling fund", "111"), (owner, "Steady fund", "222"), (owner, "Unpriced fund", "333"), (other, "Other's fund", "222")):
            Investment.objects.create(user=user, asset_type="mutual_fund", asset_name=name, currency="INR", amfi_scheme_code=code, units="10")
        Investment.objects.create(user=owner, asset_type="equity", asset_name="No code", currency="INR")
        history = {"series": series("111", ["100", "90", "84"]) + series("222", ["50", "51", "50.5"]), "evidence": {}}
        watchlist = {"available": True, "items": [watch_item(str(n), f"Synthetic Fund {n} - Direct Plan - Growth") for n in range(5)]}
        with patch.object(guide.portfolio_intelligence_service, "_get_amfi_history_report", return_value=history):
            result = guide.beginner_guide(owner, watchlist)
        self.assertEqual([pick["scheme_code"] for pick in result["picks"]], ["0", "1", "2"])
        self.assertEqual((result["picks"][0]["risk"], result["picks"][0]["why"]),
                         ("Medium", "Up 2.3% in the last month. Its worst fall in the last 58 days was 6.7%."))
        self.assertEqual({item["name"]: item["action"] for item in result["holdings"]},
                         {"Falling fund": "sell", "Steady fund": "hold", "Unpriced fund": "unknown"})
        self.assertIn("never buys or sells", result["note"])
        self.assertEqual(guide.beginner_guide(owner, {"available": False, "items": watchlist["items"]})["picks"], [])  # stale proof: no picks
