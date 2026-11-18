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
from apps.investments.services import research_backtest, research_desk
from apps.investments.services.research_packet import build_packet
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
        self.enterContext(patch.object(research_desk, "macro", return_value=[]))
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

    def test_ideas_are_opt_in_weekly_and_survive_the_daily_cleanup(self):
        self.market["IDEA.NS"] = (_fund(), _prices(RISING))
        self.market["POOR.NS"] = (WEAK, _prices(FALLING))
        companies = [("GOOD.NS", "Good"), ("IDEA.NS", "Idea Co"), ("POOR.NS", "Poor Co"), ("MISSING.NS", "Missing Co")]
        self.enterContext(patch.object(research_desk, "nifty50", return_value=companies))
        self.assertIsNone(research_desk.discover(self.user, TODAY))  # off until the owner switches it on
        self.client.post(URL, {"operation": "discover", "enabled": True}, content_type="application/json")
        run = research_desk.discover(self.user, TODAY)
        self.assertEqual((run["checked"], run["found"]), (2, 1))  # own share skipped, failed fetch not counted, Avoid not kept
        idea = self.suggestions()["IDEA.NS"]
        self.assertTrue(idea["idea"])
        self.assertIn("not on your list", idea["why"])
        self.assertNotIn("POOR.NS", self.suggestions())
        self.assertIsNone(research_desk.discover(self.user, TODAY + timedelta(days=3)))  # weekly
        research_desk.refresh(self.user, TODAY)
        self.assertIn("IDEA.NS", self.suggestions())  # the daily cleanup leaves ideas alone
        self.assertIn("GOOD.NS", self.suggestions())
        self.assertEqual(research_desk.desk(self.user)["last_ideas"]["found"], 1)
        self.market["IDEA.NS"] = (WEAK, _prices(FALLING))
        cache.clear()  # research data is cached per symbol
        research_desk.discover(self.user, TODAY, force=True)
        self.assertNotIn("IDEA.NS", self.suggestions())  # no longer a Buy: the idea is withdrawn
        with patch.object(research_desk, "nifty50", side_effect=PublicHTTPError("upstream_status")):
            response = self.client.post(URL, {"operation": "ideas"}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("NIFTY 50", response.json()["detail"])

    def test_a_resumed_daily_run_skips_shares_already_researched_today(self):
        research_desk.refresh(self.user, TODAY)
        with patch.object(research_desk, "analyse", wraps=research_desk.analyse) as analyse:
            run = research_desk.refresh(self.user, TODAY, resume=True)
            self.assertEqual((run["researched"], analyse.call_count), (2, 0))
            research_desk.refresh(self.user, TODAY)
            self.assertEqual(analyse.call_count, 2)  # Research now reads every share again
        self.assertEqual(len(self.suggestions()), 2)

    def test_nse_list_keeps_equities_and_leaves_out_lenders(self):
        csv = ("Company Name,Industry,Symbol,Series,ISIN Code\r\nSynthetic Motors Ltd.,Automobile,SYNMOT,EQ,X\r\n"
               "Synthetic Bank Ltd.,Financial Services,SYNBANK,EQ,X\r\nOdd Ltd.,Power,ODD,BE,X\r\nBad Ltd.,Power,../x,EQ,X\r\n")
        response = type("Response", (), {"content": ("\ufeff" + csv).encode()})()
        with patch.object(research_desk.public_http, "request", return_value=response) as request:
            self.assertEqual(research_desk.nifty50(), [("SYNMOT.NS", "Synthetic Motors Ltd.")])
            research_desk.nifty50()
        self.assertEqual(request.call_count, 1)  # cached for a week
        self.assertEqual(request.call_args.args[1], research_desk.NIFTY50_URL)

    def test_past_calls_check_is_logged_one_at_a_time_and_shown(self):
        result = {"at": "2025-09-08T10:00:00+00:00", "calls": 3, "shares": 2, "by_rating": [], "skipped": [], "limits": ["x"],
                  "went_its_way_pct": "67", "from": "2023-01-01", "to": "2025-05-01", "recent": []}
        with patch.object(research_backtest, "replay_all", return_value=result) as replay:
            response = self.client.post(URL, {"operation": "backtest"}, content_type="application/json")
            self.assertEqual(response.json()["result"]["calls"], 3)
            self.assertEqual({symbol for symbol, _ in replay.call_args.args[0]}, {"GOOD.NS", "WEAK.NS"})
            cache.add(f"research-desk:backtest:{self.user.pk}", 1, 60)
            self.assertEqual(self.client.post(URL, {"operation": "backtest"}, content_type="application/json").status_code, 400)
        self.assertEqual(research_desk.desk(self.user)["backtest"]["calls"], 3)
        self.assertIsNone(research_desk.desk(self.other)["backtest"])

    def test_printable_report_is_owner_only_and_escaped(self):
        research_desk.save_settings(self.user, watch=[{"symbol": "GOOD.NS", "name": "<i>Good</i>"}])
        research_desk.refresh(self.user, TODAY)
        response = self.client.get("/investments/research-report/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertContains(response, "GOOD.NS")
        self.assertNotContains(response, "<i>Good</i>")
        self.assertContains(response, "Strongest reason against")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get("/investments/research-report/"), "GOOD.NS")
        self.client.logout()
        self.assertEqual(self.client.get("/investments/research-report/").status_code, 302)


def _series(count, start=1672531200, high=True):  # daily from 2023-01-01, rising one unit a day
    closes = [D(100 + i) for i in range(count)]
    prices = {"close": closes, "timestamp": [start + 86400 * i for i in range(count)], "currency": "INR"}
    if high:
        prices.update(high=[c + 2 for c in closes], low=[c - 2 for c in closes])
    return prices


class ResearchExtrasTests(TestCase):
    def test_example_levels_use_the_average_range_and_need_highs_and_lows(self):
        prices = _series(30)
        buy = research_desk.levels(prices, "buy", False, "INR")
        self.assertEqual((buy["atr14"], buy["stop"], buy["support"], buy["resistance"]), ("4.00", "121.00", "108.00", "131.00"))
        self.assertIn("stop-loss", buy["text"])
        self.assertIn("never places orders", buy["text"])
        self.assertIn("sell if it closes below INR 121.00", research_desk.levels(prices, "sell", True, "INR")["text"])
        self.assertIn("traded between", research_desk.levels(prices, "hold", False, "INR")["text"])
        self.assertIsNone(research_desk.levels(_series(30, high=False), "buy", False, "INR"))
        broken = _series(30)
        broken["low"][-3] = None
        self.assertIsNone(research_desk.levels(broken, "buy", False, "INR"))

    def test_macro_lines_come_from_the_world_bank_and_fail_quietly(self):
        from apps.integrations.services.verified_intelligence import verified_intelligence

        result = type("Result", (), {"payload": {"latest_value": 4.953, "latest_year": "2024"}})()
        with patch.object(verified_intelligence, "world_bank_indicator", return_value=result):
            self.assertEqual(research_desk.macro()[0], "India's inflation was 5.0% in 2024 (World Bank, yearly).")
        with patch.object(verified_intelligence, "world_bank_indicator", side_effect=PublicHTTPError("offline")):
            self.assertEqual(research_desk.macro(), [])

    def test_quarterly_revenue_compares_the_same_quarter_a_year_earlier(self):
        quarters = [(date(2024, 6, 30), D(100)), (date(2024, 9, 30), D(110)), (date(2024, 12, 31), D(120)),
                    (date(2025, 3, 31), D(130)), (date(2025, 6, 30), D(90))]
        with patch("apps.investments.services.research_packet.timezone.localdate", return_value=TODAY):
            packet = build_packet("SYNTH.NS", _fund(QuarterlyRevenue=quarters), _prices(RISING))
            self.assertEqual(packet["metrics"]["quarterly_revenue_growth_pct"], {"value": D("-10.0"), "as_of": "2025-06-30"})
            self.assertTrue(any("fell 10.0% on the same quarter" in item["point"] for item in packet["bearish"]))
            gap = build_packet("SYNTH.NS", _fund(QuarterlyRevenue=quarters[:1] + [(date(2025, 9, 30), D(1))] * 4), _prices(RISING))
            self.assertNotIn("quarterly_revenue_growth_pct", gap["metrics"])

    def test_backtest_never_sees_later_prices_or_results_than_its_day(self):
        prices, seen = _series(900), []
        fundamentals = {"TotalRevenue": [(date(2023, 3, 31), D(1), "INR"), (date(2024, 3, 31), D(2), "INR"), (date(2025, 3, 31), D(3), "INR")]}

        def fake_rate(symbol, known, window, today):
            seen.append((today, known, window))
            return None, None, {"rating": "buy"}

        with patch.object(research_backtest, "rate", side_effect=fake_rate):
            cells = research_backtest.replay("SYNTH.NS", fundamentals, prices, prices, until=date(2026, 1, 1))
        self.assertTrue(cells)
        for day, known, window in seen:
            self.assertTrue(all(row[0] + timedelta(days=90) <= day for row in known["TotalRevenue"]))
            self.assertLessEqual(len(window["close"]), research_backtest.WINDOW)
            self.assertLessEqual(research_backtest._days(window)[-1], day)
        first = cells[0]  # day 252 to day 343: 443 / 352
        self.assertEqual((first["return_pct"], first["benchmark_pct"], first["alpha_pct"]), (D("25.9"), D("25.9"), D("0.0")))
        last_exit = date.fromisoformat(cells[-1]["day"]) + timedelta(days=91)
        self.assertLessEqual(last_exit, research_backtest._days(prices)[-1])  # every cell was scored on a real later close

    def test_backtest_summary_counts_by_rating_and_judges_against_nifty(self):
        cell = lambda rating, move, alpha: {"rating": rating, "return_pct": D(move), "alpha_pct": None if alpha is None else D(alpha)}
        rows = research_backtest.summarise([cell("buy", "10", "4"), cell("buy", "-2", "-6"), cell("buy", "5", None),
                                            cell("sell", "-8", "-3"), cell("hold", "1", "0")])
        by = {row["rating"]: row for row in rows}
        self.assertEqual(list(by), ["buy", "hold", "sell"])
        self.assertEqual((by["buy"]["calls"], by["buy"]["average_move_pct"], by["buy"]["average_vs_nifty_pct"], by["buy"]["went_its_way_pct"]),
                         (3, "4.3", "-1.0", "67"))
        self.assertEqual(by["sell"]["went_its_way_pct"], "100")
        self.assertIsNone(by["hold"]["went_its_way_pct"])


def _reply(payload):
    return type("Reply", (), {"json": lambda self: payload})()


class ResearchSourcesTests(TestCase):
    """FRED, Alpha Vantage and SEC EDGAR (owner-approved 2026-11-18) only add context; synthetic replies, no network."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        from apps.investments.services import research_sources
        self.src = research_sources

    def test_fred_needs_a_key_and_drops_stale_series(self):
        with patch.object(self.src.public_http, "request") as request:
            self.assertEqual(self.src.fred_lines("us", TODAY), [])
        request.assert_not_called()

        def reply(method, url, params):
            self.assertEqual(url, self.src.FRED_URL)  # the key goes as a parameter, never into a logged URL
            rows = {"FEDFUNDS": [("2025-08-01", "4.33")], "UNRATE": [("2024-01-01", "3.7")],  # stale: left out
                    "DGS10": [("2025-09-05", "."), ("2025-09-04", "4.17")],
                    "CPIAUCSL": [("2025-08-01", "323.364")] + [("2025-07-01", "322.0")] * 11 + [("2024-08-01", "314.796")]}
            return _reply({"observations": [{"date": d, "value": v} for d, v in rows[params["series_id"]]]})

        with patch.dict("os.environ", {"ALFRED_FRED_API_KEY": "synthetic-fred-key"}), \
                patch.object(self.src.public_http, "request", side_effect=reply):
            lines = self.src.fred_lines("us", TODAY)
        self.assertEqual(lines, ["The US Federal Reserve's policy rate was 4.33% in Aug 2025 (FRED).",
                                 "US consumer prices were 2.7% higher than a year earlier in Aug 2025 (FRED).",
                                 "The US 10-year Treasury yield was 4.17% in 2025-09-04 (FRED)."])
        self.assertFalse(any("synthetic-fred-key" in line for line in lines))

    def test_alpha_vantage_reads_earnings_and_market_price_insider_trades_for_us_shares(self):
        earnings = {"quarterlyEarnings": [{"fiscalDateEnding": "2025-06-30", "reportedDate": "2025-07-23", "reportedEPS": "2.80",
                                           "estimatedEPS": "2.64"}]}
        insiders = {"data": [{"transaction_date": "2025-08-20", "acquisition_or_disposal": "D", "share_price": "250.0"},
                             {"transaction_date": "2025-08-21", "acquisition_or_disposal": "A", "share_price": "0.0"},  # a grant
                             {"transaction_date": "2025-08-22", "acquisition_or_disposal": "A", "share_price": "240.0"},
                             {"transaction_date": "2025-01-02", "acquisition_or_disposal": "D", "share_price": "200.0"}]}  # too old
        replies = lambda method, url, params, max_bytes: _reply(earnings if params["function"] == "EARNINGS" else insiders)
        with patch.dict("os.environ", {"ALFRED_ALPHA_VANTAGE_API_KEY": "SYNTHETICKEY1234"}):
            self.assertEqual(self.src.alpha_vantage_lines("INFY.NS", TODAY), [])  # Indian shares are not covered
            with patch.object(self.src.public_http, "request", side_effect=replies) as request:
                lines = self.src.alpha_vantage_lines("SYNTH", TODAY)
                self.src.alpha_vantage_lines("SYNTH", TODAY)
            self.assertEqual(request.call_count, 2)  # cached: the free key allows 25 requests a day
            self.assertIn("earnings per share 2.80 against an expected 2.64 (6.1% above)", lines[0]["text"])
            self.assertIn("1 purchase(s) and 1 sale(s)", lines[1]["text"])
            cache.clear()
            with patch.object(self.src.public_http, "request", return_value=_reply({"Information": "rate limit"})):
                self.assertEqual(self.src.alpha_vantage_lines("SYNTH", TODAY), [])

    def test_sec_edgar_sends_the_account_email_and_links_recent_reports(self):
        with patch.object(self.src.public_http, "request") as request:
            self.assertEqual(self.src.sec_filings("SYNTH", ""), [])
            self.assertEqual(self.src.sec_filings("SYNTH", "not-an-email"), [])
            self.assertEqual(self.src.sec_filings("INFY.NS", "owner@example.com"), [])
        request.assert_not_called()
        recent = {"form": ["4", "8-K", "10-Q", "SC 13G", "10-K"], "filingDate": ["2025-09-01", "2025-08-15", "2025-08-01", "2025-07-01", "2025-02-01"],
                  "reportDate": ["", "2025-08-14", "2025-06-28", "", "2024-12-31"],
                  "accessionNumber": ["0000000001-25-000005", "0000000001-25-000004", "0000000001-25-000003", "0000000001-25-000002", "0000000001-25-000001"],
                  "primaryDocument": ["x.xml", "a8k.htm", "q2.htm", "g.htm", "<script>.htm"]}

        def reply(method, url, headers, max_bytes):
            self.assertEqual(headers["User-Agent"], "ALFRED research desk owner@example.com")
            if url == self.src.SEC_TICKERS_URL:
                return _reply({"0": {"cik_str": 1234, "ticker": "SYNTH", "title": "Synthetic Inc."}})
            self.assertEqual(url, "https://data.sec.gov/submissions/CIK0000001234.json")
            return _reply({"filings": {"recent": recent}})

        with patch.object(self.src.public_http, "request", side_effect=reply):
            lines = self.src.sec_filings("SYNTH", "owner@example.com")
        self.assertEqual([line["text"] for line in lines], ["8-K filed 2025-08-15 for the period to 2025-08-14 (SEC EDGAR).",
                                                           "10-Q filed 2025-08-01 for the period to 2025-06-28 (SEC EDGAR)."])
        self.assertEqual(lines[1]["url"], "https://www.sec.gov/Archives/edgar/data/1234/000000000125000003/q2.htm")

    def test_the_desk_passes_each_account_email_only_to_sec_edgar(self):
        user = get_user_model().objects.create_user("synthetic-sources", email="owner@example.com", password="Test12345!")
        research_desk.save_settings(user, watch=[{"symbol": "SYNTH", "name": "Synthetic Inc."}])
        with patch("apps.investments.services.research_packet.fetch_fundamentals", return_value=_fund(currency="USD")), \
                patch("apps.investments.services.research_packet.fetch_prices", return_value=_prices(RISING, "USD")), \
                patch("apps.investments.services.research_packet.timezone.localdate", return_value=TODAY), \
                patch.object(research_desk, "headlines", return_value=[]), patch.object(research_desk, "benchmark", return_value=None), \
                patch.object(self.src, "fred_lines", return_value=["US line"]) as fred, \
                patch.object(self.src, "alpha_vantage_lines", return_value=[{"text": "Earnings", "url": None}]) as alpha, \
                patch.object(self.src, "sec_filings", return_value=[{"text": "10-Q", "url": "https://www.sec.gov/x"}]) as sec:
            research_desk.refresh(user, TODAY)
        card = research_desk.desk(user)["suggestions"][0]
        self.assertEqual((card["macro"], [c["text"] for c in card["context"]]), (["US line"], ["Earnings", "10-Q"]))
        fred.assert_called_once_with("us")
        alpha.assert_called_once_with("SYNTH")
        sec.assert_called_once_with("SYNTH", "owner@example.com")
