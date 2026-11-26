"""NEW-2: a beginner gets three plain fund picks and Hold / Review / Sell for owned funds. Synthetic AMFI data only."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.investments.models import Investment
from apps.investments.services import beginner_guide as guide, fund_prices


def watch_item(code, name):
    return {"scheme_code": code, "scheme_name": name, "fund_house": "Synthetic AMC", "family_label": "Large cap", "nav_source_value": "45.1235",
            "nav_date": "2026-11-13", "realized_volatility_pct": 4.2, "return_30d_pct": 2.345, "history_days": 58, "max_drawdown_pct": -6.71}


def series(code, navs, newest_days_ago=1, pad=True):
    """Daily NAV rows ending `newest_days_ago` days back; padded at the start so the history has enough observations."""
    navs = [navs[0]] * (max(0, guide.WATCHLIST_MIN_OBSERVATIONS - len(navs)) if pad else 0) + list(navs)
    today = timezone.localdate()
    return [{"scheme_code": code, "scheme_name": f"Synthetic {code} - Direct Plan - Growth", "nav": Decimal(nav),
             "nav_date": today - timedelta(days=newest_days_ago + len(navs) - 1 - i)} for i, nav in enumerate(navs)]


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


class HoldingEvidenceTests(TestCase):
    """No hold, review or sell without dated, fresh, agreed and complete AMFI evidence; the page and the bot share the rule."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("synthetic-fund-signal")
        Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Synthetic", currency="INR",
                                  invested_amount=100, current_value=100, units=10, amfi_scheme_code="123456")

    def holding(self, rows):
        with patch.object(guide.portfolio_intelligence_service, "_get_amfi_history_report", return_value={"series": rows}):
            return guide.beginner_guide(self.user, {"available": False})["holdings"][0]

    def test_a_fresh_complete_history_gives_a_dated_signal_in_any_row_order(self):
        rows = series("123456", ["10", "9", "8"])
        newest = rows[-1]["nav_date"]
        for ordered in (rows, rows[::-1], rows[5:] + rows[:5]):
            result = self.holding(ordered)
            self.assertEqual((result["action"], result["as_of"]), ("sell", newest.isoformat()))
            self.assertIn(f"Based on AMFI prices up to {newest:%d %b %Y}", result["text"])
        old = rows + [dict(rows[0], nav=Decimal("500"), nav_date=timezone.localdate() - timedelta(days=guide.WATCHLIST_HISTORY_DAYS + 5))]
        self.assertEqual(self.holding(old)["action"], "sell")  # a price outside the window is not the "recent high"

    def test_stale_sparse_conflicting_future_and_mixed_histories_give_no_signal(self):
        today = timezone.localdate()
        fresh = series("123456", ["10", "9", "8"])
        cases = {
            "audit case: two prices 50 and 40 days old": ([dict(fresh[0], nav=Decimal(n), nav_date=today - timedelta(days=d)) for d, n in ((50, "10"), (40, "8"))], "too old"),
            "stale": (series("123456", ["10", "9", "8"], newest_days_ago=fund_prices.WATCHLIST_NAV_MAX_AGE_DAYS + 1), "too old"),
            "sparse": (series("123456", ["10", "9", "8"], pad=False), "only 3 recent prices"),
            "conflicting": (fresh + [dict(fresh[-1], nav=Decimal("9.5"))], "two different prices"),
            "future": (fresh + [dict(fresh[-1], nav_date=today + timedelta(days=1))], "dated in the future"),
            "another fund's rows": (fresh[:-1] + [dict(fresh[-1], scheme_name="Synthetic Other - Direct Plan - Growth")], "do not agree on which fund"),
            "none": ([], "no recent prices"),
        }
        for name, (rows, reason) in cases.items():
            with self.subTest(name):
                result = self.holding(rows)
                self.assertEqual(result["action"], "unknown")
                self.assertIn(reason, result["text"]); self.assertIn("No signal is given", result["text"])
                self.assertNotIn("sell", result["text"].lower())

    def test_no_history_at_all_says_why_and_the_empty_picks_say_why_too(self):
        waiting = {"series": [], "evidence": {"summary": "AMFI's price history (about 50 MB) is downloading in the background. Check again in a few minutes."}}
        with patch.object(guide.portfolio_intelligence_service, "_get_amfi_history_report", return_value=waiting):
            result = guide.beginner_guide(self.user, {"available": False, "summary": "Synthetic watchlist reason."})
        self.assertEqual(result["holdings"][0]["text"], "ALFRED cannot judge this fund now: AMFI's price history (about 50 MB) is "
                         "downloading in the background. Check again in a few minutes. No signal is given.")
        self.assertEqual(result["picks_reason"], "Synthetic watchlist reason.")

    def test_the_scheduled_fund_bot_stays_quiet_on_stale_history_and_speaks_on_fresh(self):
        from apps.ml_engine.services import task_bots
        target = "apps.investments.services.portfolio_intelligence.portfolio_intelligence_service._get_amfi_history_report"
        today = timezone.localdate()
        stale = [dict(series("123456", ["10"])[0], nav=Decimal(n), nav_date=today - timedelta(days=d)) for d, n in ((50, "10"), (40, "8"))]
        with patch(target, return_value={"series": stale}):
            self.assertEqual(task_bots.fund_review(self.user, today), [])
        with patch(target, return_value={"series": series("123456", ["10", "9", "8"])}):
            titles = [item["title"] for item in task_bots.fund_review(self.user, today)]
        self.assertEqual(titles, ["Synthetic: Sell"])
