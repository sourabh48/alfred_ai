"""Automatic research desk: ALFRED researches and suggests; the owner only accepts or rejects; nothing is ever traded."""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

from alfred_ai import native_tasks
from alfred_ai.services.public_http import PublicHTTPError
from apps.investments.models import Investment, ResearchDecision
from apps.investments.services import research_desk
from tests.test_research_packet import RISING, Y1, Y2, D, _fund, _prices

TODAY = date(2025, 9, 8)  # the fixture prices end on 2025-09-07
FALLING = [300 - i * 0.6 for i in range(250)]
WEAK = _fund(TotalRevenue=[(Y1, D(1200)), (Y2, D(1000))], NetIncome=[(Y1, D(50)), (Y2, D(-40))], TotalDebt=[(Y2, D(1500))],
             CurrentAssets=[(Y2, D(200))], CurrentLiabilities=[(Y2, D(300))], FreeCashFlow=[(Y2, D(-10))])
URL = "/api/investments/research/desk/"


class ResearchDeskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.enterContext(patch("apps.investments.services.research_packet.timezone.localdate", return_value=TODAY))
        self.enterContext(patch.object(research_desk, "headlines", return_value=[]))
        self.enterContext(patch.object(research_desk, "benchmark", return_value={"level": "25000.0000", "as_of": "2025-09-05"}))
        self.market = {"GOOD.NS": (_fund(), _prices(RISING)), "WEAK.NS": (WEAK, _prices(FALLING))}
        self.enterContext(patch("apps.investments.services.research_packet.fetch_fundamentals", side_effect=lambda s: self.data(s)[0]))
        self.enterContext(patch("apps.investments.services.research_packet.fetch_prices", side_effect=lambda s: self.data(s)[1]))
        self.user = get_user_model().objects.create_user("synthetic-desk-owner", password="Test12345!")
        self.other = get_user_model().objects.create_user("synthetic-desk-other", password="Test12345!")
        research_desk.save_settings(self.user, watch=[{"symbol": "GOOD.NS", "name": "GOOD.NS"}, {"symbol": "WEAK.NS", "name": "WEAK.NS"}])
        self.client.force_login(self.user)

    def data(self, symbol):
        if symbol not in self.market:
            raise PublicHTTPError("upstream_status")
        return self.market[symbol]

    def suggestions(self, user=None):
        return {s["symbol"]: s for s in research_desk.desk(user or self.user)["suggestions"]}

    def test_rules_give_a_cautious_buy_an_avoid_and_no_rating_on_stale_data(self):
        good = research_desk.analyse("GOOD.NS", "GOOD.NS")
        self.assertEqual((good["rating"], good["label"]), ("overweight", "Buy a little"))  # fast rise held a Buy back
        self.assertIn("RSI", good["risks"][0])
        self.assertEqual([step["role"] for step in good["steps"]], ["Analysts", "Bull and bear researchers", "Research manager", "Trader",
                                                                   "Risk team", "Portfolio manager"])
        self.assertEqual(len(good["charts"]["price"]["close"]), len(good["charts"]["price"]["sma200"]))
        self.assertEqual(good["charts"]["results"]["labels"], ["2024-03", "2025-03"])
        weak = research_desk.analyse("WEAK.NS", "WEAK.NS")
        self.assertEqual((weak["rating"], weak["label"]), ("sell", "Avoid"))
        holding = Investment(user=self.user, asset_type="equity", asset_name="WEAK.NS", current_value=Decimal("10"))
        self.assertEqual(research_desk.analyse("WEAK.NS", "WEAK.NS", holding=holding, portfolio_total=Decimal("100"))["label"], "Sell")
        with patch("apps.investments.services.research_packet.timezone.localdate", return_value=TODAY + timedelta(days=30)):
            self.assertIsNone(research_desk.analyse("GOOD.NS", "GOOD.NS"))  # a month-old close is not rated

    def test_refresh_suggests_once_skips_failures_and_never_touches_holdings(self):
        Investment.objects.create(user=self.user, asset_type="equity", asset_name="Synthetic Co", invested_amount=1, current_value=1)
        holdings = list(Investment.objects.values())
        research_desk.save_settings(self.user, watch=research_desk.desk_settings(self.user)["watch"] + [{"symbol": "GONE.NS", "name": "GONE.NS"}],
                                    include_holdings=True)
        run = research_desk.refresh(self.user, TODAY)
        self.assertEqual(run["researched"], 2)
        self.assertEqual({item["name"] for item in run["skipped"]}, {"Synthetic Co", "GONE.NS"})
        first = self.suggestions()
        research_desk.refresh(self.user, TODAY)
        self.assertEqual({s: v["id"] for s, v in self.suggestions().items()}, {s: v["id"] for s, v in first.items()})
        self.assertEqual(list(Investment.objects.values()), holdings)
        self.assertEqual(ResearchDecision.objects.count(), 0)
        self.assertEqual(self.suggestions(self.other), {})

    def test_an_owned_share_recorded_by_symbol_is_researched_only_when_allowed(self):
        Investment.objects.create(user=self.user, asset_type="equity", asset_name="WEAK.NS", invested_amount=50, current_value=50)
        Investment.objects.create(user=self.user, asset_type="mutual_fund", asset_name="Index fund", invested_amount=50, current_value=50)
        research_desk.refresh(self.user, TODAY)
        self.assertEqual(self.suggestions()["WEAK.NS"]["label"], "Avoid")
        research_desk.save_settings(self.user, include_holdings=True)
        research_desk.refresh(self.user, TODAY)
        self.assertEqual(self.suggestions()["WEAK.NS"]["label"], "Sell")  # as a holding, the older Avoid is superseded
        self.assertIn("It is already more than a fifth of your holdings.", self.suggestions()["WEAK.NS"]["risks"])

    def test_accept_writes_a_journal_entry_and_reject_keeps_a_call_away_until_it_changes(self):
        research_desk.refresh(self.user, TODAY)
        good, weak = self.suggestions()["GOOD.NS"], self.suggestions()["WEAK.NS"]
        with self.assertRaises(ValueError):
            research_desk.accept(self.other, good["id"], TODAY)
        result = research_desk.accept(self.user, good["id"], TODAY)
        decision = ResearchDecision.objects.get(pk=result["decision_id"], user=self.user)
        self.assertEqual((decision.instrument, decision.rating, decision.entry_price, decision.benchmark, decision.benchmark_entry, decision.currency),
                         ("GOOD.NS", "overweight", Decimal("224.5000"), "NIFTY 50", Decimal("25000.0000"), "INR"))
        self.assertEqual(decision.review_on, TODAY + timedelta(days=91))
        self.assertIn("Nothing was bought or sold", result["message"])
        with self.assertRaises(ValueError):
            research_desk.accept(self.user, good["id"], TODAY)
        research_desk.reject(self.user, weak["id"])
        research_desk.refresh(self.user, TODAY)
        self.assertEqual(self.suggestions(), {})
        self.market["WEAK.NS"] = (_fund(), _prices(RISING))  # the company recovers: a new call comes back
        cache.clear()
        research_desk.refresh(self.user, TODAY)
        self.assertEqual(self.suggestions()["WEAK.NS"]["rating"], "overweight")
        self.assertEqual(Investment.objects.count(), 0)

    def test_a_week_old_suggestion_cannot_be_accepted(self):
        research_desk.refresh(self.user, TODAY)
        with self.assertRaises(ValueError):
            research_desk.accept(self.user, self.suggestions()["GOOD.NS"]["id"], TODAY + timedelta(days=9))

    def test_due_calls_are_checked_against_the_latest_close_and_get_a_lesson(self):
        research_desk.refresh(self.user, TODAY)
        decision = ResearchDecision.objects.get(pk=research_desk.accept(self.user, self.suggestions()["GOOD.NS"]["id"], TODAY)["decision_id"])
        ResearchDecision.objects.create(user=self.user, instrument="GOOD.NS", rating="buy", thesis="My own call", decided_on=TODAY,
                                        review_on=TODAY, entry_price=Decimal("1"))  # the owner's own entries are left alone
        later = TODAY + timedelta(days=95)
        self.assertEqual(research_desk.settle_due(TODAY), 0)  # not due yet
        prices = _prices(RISING + [250.0] * 100)  # closes run to 2025-12-16, after the check date
        with patch.object(research_desk, "research_data", return_value={"fundamentals": {}, "prices": prices}), \
                patch.object(research_desk, "benchmark", return_value={"level": "26000.0000", "as_of": "2025-12-16"}):
            self.assertEqual(research_desk.settle_due(later), 1)
        decision.refresh_from_db()
        self.assertEqual((decision.settled_on, decision.exit_price, decision.benchmark_exit), (date(2025, 12, 16), Decimal("250.0000"), Decimal("26000.0000")))
        self.assertIn("The call held up.", decision.lesson)  # +11.36% against the index's +4%
        self.assertEqual(ResearchDecision.objects.filter(settled_on__isnull=True).count(), 1)

    def test_api_is_owner_only_and_accepts_only_known_actions(self):
        self.assertEqual(self.client.post(URL, {"operation": "run"}, content_type="application/json").status_code, 200)
        data = self.client.get(URL).json()
        self.assertEqual(len(data["suggestions"]), 2)
        self.assertEqual(self.client.post(URL, {"operation": "buy", "id": data["suggestions"][0]["id"]}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(URL, {"operation": "watch_add", "symbol": "Infosys"}, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.post(URL, {"operation": "holdings", "include": "yes"}, content_type="application/json").status_code, 400)
        response = self.client.post(URL, {"operation": "reject", "id": data["suggestions"][0]["id"]}, content_type="application/json")
        self.assertEqual(response.json()["desk"]["answered"][0]["state"], "rejected")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(URL).json()["suggestions"], [])
        self.assertEqual(self.client.post(URL, {"operation": "accept", "id": data["suggestions"][1]["id"]}, content_type="application/json").status_code, 400)
        self.client.logout()
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_the_daily_job_researches_every_account_and_settles(self):
        self.assertIn("research-desk", native_tasks.DAILY_JOBS)
        with patch.object(research_desk, "settle_due", return_value=0):
            result = native_tasks.DAILY_JOBS["research-desk"]()
        self.assertEqual((result["processed"], result["failed"]), (2, 0))
        self.assertEqual(len(self.suggestions()), 2)

    def test_personal_fit_is_unknown_without_answers_and_blocks_on_a_thin_reserve_or_near_goal(self):
        from apps.budgets.models import SavingsGoal
        from apps.expenses.models import BankAccount

        research_desk.refresh(self.user, TODAY)
        good = self.suggestions_on(TODAY)["GOOD.NS"]
        self.assertEqual((good["status"], good["fit"]["state"]), ("Investment candidate", "unknown"))
        self.assertIn("how big a fall", " ".join(good["fit"]["missing"]))
        self.assertNotIn("amount", good)  # ALFRED never proposes a sum
        self.assertEqual(self.suggestions_on(TODAY)["WEAK.NS"]["fit"]["state"], "not_needed")
        research_desk.save_settings(self.user, profile={"loss": "high", "horizon": "over_5"})
        baseline = {"metric_states": {"liquid_runway_months": {"status": "derived"}},
                    "decimal_amounts": {"liquid_cash": "30000.00", "essential_monthly_outflow": "10000.00"}}
        with patch("apps.expenses.services.financial_intelligence.resolve_canonical_financial_baseline", return_value=baseline):
            good = self.suggestions_on(TODAY)["GOOD.NS"]
            fit = good["fit"]
            self.assertEqual((fit["state"], good["status"]), ("does_not_fit", "Not for you yet"))
            self.assertIn("GOOD.NS: Buy a little (new), but not for you yet", [item["title"] for item in research_desk.notices(self.user, TODAY)])
            self.assertIn("about 3.0 months", fit["reasons"][0])
            baseline["decimal_amounts"]["liquid_cash"] = "90000.00"
            self.assertEqual(self.suggestions_on(TODAY)["GOOD.NS"]["fit"]["state"], "fits")
            SavingsGoal.objects.create(user=self.user, name="Synthetic deposit", target_amount=Decimal("500000"),
                                       saved_amount=Decimal("1000"), target_date=TODAY + timedelta(days=400))
            self.assertIn("Synthetic deposit", self.suggestions_on(TODAY)["GOOD.NS"]["fit"]["reasons"][0])
        with self.assertRaises(ValueError):
            research_desk.save_settings(self.user, profile={"loss": "reckless", "horizon": None})
        self.assertFalse(BankAccount.objects.filter(user=self.user).exists())  # nothing was written to the owner's money

    def suggestions_on(self, day):
        return {s["symbol"]: s for s in research_desk.desk(self.user, day)["suggestions"]}

    def test_card_explains_why_now_against_and_change_and_tracks_a_changed_call(self):
        research_desk.refresh(self.user, TODAY)
        weak = self.suggestions_on(TODAY)["WEAK.NS"]
        self.assertEqual((weak["status"], weak["why"]), ("Avoid", "It is on your watch list."))
        self.assertTrue(weak["against"]); self.assertIn("200-day average", weak["change_if"])
        self.assertNotIn("changed_from", weak)
        self.market["WEAK.NS"] = (_fund(), _prices(RISING))  # the company's numbers and price turn around
        cache.clear()  # past the 15-minute data cache
        research_desk.refresh(self.user, TODAY)
        changed = self.suggestions_on(TODAY)["WEAK.NS"]
        self.assertEqual(changed["changed_from"], "Avoid")
        self.assertIn("Changed from Avoid", changed["change"])
        self.assertEqual(len(research_desk.desk(self.user, TODAY)["suggestions"]), 2)  # one open call per share
        research_desk.refresh(self.user, TODAY + timedelta(days=1))
        again = self.suggestions_on(TODAY + timedelta(days=1))["WEAK.NS"]
        self.assertEqual((again["first_seen"], again["for_date"], again["changed_from"]), (TODAY.isoformat(), (TODAY + timedelta(days=1)).isoformat(), "Avoid"))

    def test_later_hides_a_call_for_a_week_and_home_notices_skip_routine_and_repeat(self):
        from apps.ml_engine.services import task_bots

        research_desk.refresh(self.user, TODAY)
        with patch("apps.ml_engine.services.task_bots.timezone.localdate", return_value=TODAY), \
                patch("apps.investments.services.research_desk.timezone.localdate", return_value=TODAY):
            first = task_bots.run(self.user, "research_desk", TODAY)
            self.assertEqual(sorted(item["title"] for item in first["items"]), ["GOOD.NS: Buy a little (new)", "WEAK.NS: Avoid (new)"])
            self.assertEqual(task_bots.run(self.user, "research_desk", TODAY)["proposal_id"], first["proposal_id"])  # no duplicate
            research_desk.refresh(self.user, TODAY)  # unchanged evidence
            self.assertEqual(task_bots.run(self.user, "research_desk", TODAY)["proposal_id"], first["proposal_id"])
        weak = self.suggestions_on(TODAY)["WEAK.NS"]
        research_desk.later(self.user, weak["id"], TODAY)
        self.assertNotIn("WEAK.NS", self.suggestions_on(TODAY))
        self.assertEqual(research_desk.desk(self.user, TODAY)["snoozed"], 1)
        research_desk.refresh(self.user, TODAY)  # unchanged evidence keeps the snooze
        self.assertNotIn("WEAK.NS", self.suggestions_on(TODAY + timedelta(days=6)))
        self.assertIn("WEAK.NS", self.suggestions_on(TODAY + timedelta(days=7)))

    def test_pause_stops_the_daily_job_and_a_second_run_waits_for_the_first(self):
        get_user_model().objects.filter(pk=self.other.pk).update(is_active=False)
        research_desk.save_settings(self.user, enabled=False)
        self.assertIsNone(research_desk.desk(self.user, TODAY)["next_run"])
        self.assertEqual(research_desk.run_scheduled(TODAY)["processed"], 0)
        self.assertFalse(research_desk.desk(self.user, TODAY)["suggestions"])
        research_desk.save_settings(self.user, enabled=True)
        cache.add(f"research-desk:running:{self.user.pk}", 1, 60)
        result = research_desk.run_scheduled(TODAY)
        self.assertEqual((result["processed"], result["failed"]), (0, 1))  # the running one is not doubled
        cache.clear()
        self.assertEqual(research_desk.run_scheduled(TODAY)["processed"], 1)
        self.assertTrue(research_desk.desk(self.user, TODAY)["next_run"])
        response = self.client.post(URL, {"operation": "monitor", "enabled": "no"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        response = self.client.post(URL, {"operation": "monitor", "enabled": False}, content_type="application/json")
        self.assertFalse(response.json()["desk"]["settings"]["enabled"])
