from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.investments.models import ResearchSearch
from apps.investments.services.research_packet import build_packet, research_packet
from apps.investments.services.research_searches import remember, review_recent
from apps.ml_engine.services import task_bots
from tests.test_research_packet import _fund, _prices, RISING


class ResearchSearchTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("search-owner")
        self.other = get_user_model().objects.create_user("search-other")
        self.client.force_login(self.user)
        self.packet = build_packet("SYNTH.NS", _fund(), _prices(RISING))

    def test_history_is_owner_scoped_bounded_and_clearable(self):
        for i in range(23):
            remember(self.user, {**self.packet, "symbol": f"S{i}.NS"})
        remember(self.other, self.packet)
        self.assertEqual(ResearchSearch.objects.filter(user=self.user).count(), 20)
        response = self.client.get("/api/investments/research/searches/")
        self.assertEqual(len(response.json()["searches"]), 20)
        self.assertNotIn("SYNTH.NS", [row["symbol"] for row in response.json()["searches"]])
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(self.client.delete("/api/investments/research/searches/").status_code, 204)
        self.assertEqual(ResearchSearch.objects.count(), 1)

    def test_successful_lookup_saves_search_but_failure_does_not(self):
        with patch("apps.investments.research_views._packet", return_value=(self.packet, None)):
            self.assertEqual(self.client.get("/api/investments/research/packet/?symbol=SYNTH.NS").status_code, 200)
        self.assertEqual(ResearchSearch.objects.get(user=self.user).symbol, "SYNTH.NS")
        self.assertEqual(self.client.get("/api/investments/research/packet/?symbol=../bad").status_code, 400)
        self.assertEqual(ResearchSearch.objects.filter(user=self.user).count(), 1)

    def test_account_reset_removes_only_owners_search_history(self):
        from apps.users.services import clear_user_fed_data
        remember(self.user, self.packet)
        remember(self.other, self.packet)
        clear_user_fed_data(self.user)
        self.assertFalse(ResearchSearch.objects.filter(user=self.user).exists())
        self.assertTrue(ResearchSearch.objects.filter(user=self.other).exists())

    def test_market_index_does_not_request_company_fundamentals(self):
        with patch("apps.investments.services.research_packet.fetch_fundamentals") as fundamentals, patch("apps.investments.services.research_packet.fetch_prices", return_value=_prices(RISING)):
            packet = research_packet("^NSEI", refresh=True)
        fundamentals.assert_not_called()
        self.assertEqual(packet["symbol"], "^NSEI")
        self.assertIn("price", packet["metrics"])

    def test_background_review_bounded_and_does_not_resurrect_deleted_searches(self):
        for i in range(4):
            remember(self.user, {**self.packet, "symbol": f"S{i}.NS"})
        ResearchSearch.objects.update(checked_at=timezone.now()-timedelta(days=2))
        with patch("apps.investments.services.research_searches.research_packet", return_value=self.packet) as fetch:
            self.assertEqual(len(review_recent(self.user, timezone.localdate())), 3)
            self.assertEqual(fetch.call_count, 3)
        ResearchSearch.objects.update(last_attempt_at=timezone.now()-timedelta(days=1))

        def deleted(symbol):
            ResearchSearch.objects.filter(user=self.user).delete()
            return self.packet
        with patch("apps.investments.services.research_searches.research_packet", side_effect=deleted):
            self.assertEqual(review_recent(self.user, timezone.localdate()), [])
        self.assertFalse(ResearchSearch.objects.filter(user=self.user).exists())

    def test_cached_research_keeps_original_fetch_time_and_refresh_fetches_again(self):
        with patch("apps.investments.services.research_packet.fetch_fundamentals", return_value=_fund()) as fetch, patch("apps.investments.services.research_packet.fetch_prices", return_value=_prices(RISING)):
            first = research_packet("SYNTH.NS")
            second = research_packet("SYNTH.NS")
            self.assertEqual(first["retrieved_at"], second["retrieved_at"])
            self.assertEqual(fetch.call_count, 1)
            research_packet("SYNTH.NS", refresh=True)
            self.assertEqual(fetch.call_count, 2)

    def test_stale_or_future_evidence_does_not_produce_positive_guidance(self):
        with patch("apps.investments.services.research_packet.timezone.localdate", return_value=date(2027, 1, 1)):
            packet = build_packet("SYNTH.NS", _fund(), _prices(RISING))
        self.assertEqual(packet["beginner"]["lean"], "not_enough")
        self.assertEqual(packet["valuation"]["status"], "unavailable")
        with patch("apps.investments.services.research_packet.timezone.localdate", return_value=date(2023, 1, 1)):
            packet = build_packet("SYNTH.NS", _fund(), {})
        self.assertIsNone(packet["latest_period_end"])

    def test_one_new_statement_does_not_refresh_older_research_signs(self):
        today = date(2027, 1, 1)
        fundamentals = _fund()
        fundamentals["DilutedAverageShares"] = [(today, fundamentals["DilutedAverageShares"][0][1], "INR")]
        prices = _prices(RISING)
        end = int(timezone.now().replace(year=2027, month=1, day=1).timestamp())
        prices["timestamp"] = [end - (len(RISING)-1-i)*86400 for i in range(len(RISING))]
        with patch("apps.investments.services.research_packet.timezone.localdate", return_value=today):
            packet = build_packet("SYNTH.NS", fundamentals, prices)
        self.assertEqual(packet["beginner"]["lean"], "not_enough")
        self.assertEqual(packet["freshness"]["statement_status"], "stale")

    def test_mixed_currency_ratio_abstains_and_leap_day_is_supported(self):
        fundamentals = _fund()
        fundamentals["CurrentAssets"] = [(date(2025, 3, 31), row[1], "USD") for row in fundamentals["CurrentAssets"]]
        packet = build_packet("SYNTH.NS", fundamentals, {})
        self.assertNotIn("current_ratio", packet["metrics"])
        leap = {name: [(date(2024, 2, 29), row[1], row[2]) for row in rows[-1:]] for name, rows in _fund().items()}
        self.assertEqual(build_packet("SYNTH.NS", leap, {})["latest_period_end"], "2024-02-29")

    def test_failed_background_review_keeps_timestamp_and_does_not_overwrite_new_search(self):
        row = remember(self.user, self.packet)
        old_check = timezone.now()-timedelta(days=2)
        ResearchSearch.objects.filter(pk=row.pk).update(checked_at=old_check)
        with patch("apps.investments.services.research_searches.research_packet", side_effect=RuntimeError("synthetic outage")):
            self.assertEqual(review_recent(self.user, timezone.localdate()), [])
        row.refresh_from_db()
        self.assertEqual(row.checked_at, old_check)
        self.assertIn("could not refresh", row.error)
        def newer_search(symbol):
            remember(self.user, self.packet)
            raise RuntimeError("old request failed after the new search succeeded")
        ResearchSearch.objects.filter(pk=row.pk).update(last_attempt_at=old_check-timedelta(days=2))  # past the failure back-off
        with patch("apps.investments.services.research_searches.research_packet", side_effect=newer_search) as fetch:
            self.assertEqual(review_recent(self.user, timezone.localdate()), [])
            fetch.assert_called_once()
        row.refresh_from_db()
        self.assertEqual(row.error, "")

    def test_old_failures_rotate_and_do_not_retry_in_the_same_window(self):
        now = timezone.now()
        with patch("apps.investments.services.research_searches.timezone.now", return_value=now-timedelta(days=4)):
            for i in range(4):
                remember(self.user, {**self.packet, "symbol": f"S{i}.NS"})
        ResearchSearch.objects.filter(user=self.user).update(checked_at=now-timedelta(days=4))
        untouched = remember(self.other, self.packet)

        def fetch(symbol):
            if symbol != "S3.NS":
                raise RuntimeError("synthetic outage")
            return self.packet

        with patch("apps.investments.services.research_searches.research_packet", side_effect=fetch) as provider:
            self.assertEqual(review_recent(self.user, timezone.localdate()), [])
            self.assertEqual(review_recent(self.user, timezone.localdate()), [])
            self.assertEqual([call.args[0] for call in provider.call_args_list], ["S0.NS", "S1.NS", "S2.NS"])
            with patch("apps.investments.services.research_searches.timezone.now", return_value=now+timedelta(days=1)):
                self.assertEqual(len(review_recent(self.user, timezone.localdate())), 1)
            self.assertEqual(provider.call_args_list[3].args[0], "S3.NS")
        untouched.refresh_from_db()
        self.assertIsNone(untouched.last_attempt_at)

    def test_failing_symbols_back_off_so_healthy_ones_keep_their_daily_slot(self):
        now = timezone.now()
        with patch("apps.investments.services.research_searches.timezone.now", return_value=now-timedelta(days=5)):
            for i in range(4):
                remember(self.user, {**self.packet, "symbol": f"S{i}.NS"})
        ResearchSearch.objects.filter(user=self.user).update(checked_at=now-timedelta(days=5))
        good = {"S3.NS"}

        def fetch(symbol):
            if symbol not in good:
                raise RuntimeError("synthetic outage")
            return self.packet

        calls = []
        with patch("apps.investments.services.research_searches.research_packet", side_effect=lambda s: calls.append(s) or fetch(s)):
            for day in range(5):
                with patch("apps.investments.services.research_searches.timezone.now", return_value=now+timedelta(days=day)):
                    review_recent(self.user, timezone.localdate())
        failing = [s for s in calls if s != "S3.NS"]
        self.assertEqual(calls.count("S3.NS"), 3)  # days 1, 2 and 4: oldest attempt first, so day 3 retries the failing ones
        self.assertEqual(sorted(failing), ["S0.NS", "S0.NS", "S1.NS", "S1.NS", "S2.NS", "S2.NS"])  # day 0, then day 3 only
        row = ResearchSearch.objects.get(user=self.user, symbol="S0.NS")
        self.assertEqual(row.checked_at, now-timedelta(days=5))  # the last good evidence keeps its own time
        self.assertTrue(row.error)

    def test_stock_review_acknowledgment_never_repeats_the_provider_call(self):
        row = remember(self.user, self.packet)
        ResearchSearch.objects.filter(pk=row.pk).update(checked_at=timezone.now()-timedelta(days=2))
        with patch("apps.investments.services.research_searches.research_packet", return_value=self.packet) as fetch:
            review = task_bots.run(self.user, "research_watch")
            self.assertIsNone(task_bots.run(self.user, "research_watch"))
            self.assertIn(review["proposal_id"], [proposal["proposal_id"] for proposal in task_bots.pending(self.user)])
            result = task_bots.confirm(self.user, review["proposal_id"], [review["items"][0]["id"]], review["fingerprint"])
            self.assertEqual(result["applied"], [])
            fetch.assert_called_once()
        self.assertEqual(task_bots.pending(self.user), [])

    def test_scheduled_empty_or_failed_online_run_keeps_daily_cadence(self):
        today = timezone.localdate()
        row = remember(self.user, self.packet)
        ResearchSearch.objects.filter(pk=row.pk).update(checked_at=timezone.now()-timedelta(days=2))
        with patch.object(task_bots, "BOTS", {"research_watch": task_bots.BOTS["research_watch"]}), patch(
            "apps.investments.services.research_searches.research_packet", side_effect=RuntimeError("synthetic outage")
        ) as provider:
            self.assertEqual(task_bots.run_scheduled(today)["processed"], 2)
            self.assertEqual(task_bots.run_scheduled(today)["processed"], 0)
            provider.assert_called_once()
        row.refresh_from_db()
        self.assertIsNotNone(row.last_attempt_at)
        self.assertIn("could not refresh", row.error)
        self.assertContains(self.client.get("/settings/diagnostics/"), "1 stock research refresh has failed")
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get("/settings/diagnostics/"), "stock research refresh")
