from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.investments.models import ResearchSearch
from apps.investments.services.research_packet import build_packet, research_packet
from apps.investments.services.research_searches import remember, review_recent
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
        with patch("apps.investments.services.research_searches.research_packet", side_effect=newer_search):
            self.assertEqual(review_recent(self.user, timezone.localdate()), [])
        row.refresh_from_db()
        self.assertEqual(row.error, "")
