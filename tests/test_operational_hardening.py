from datetime import date, timedelta
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import (
    EVIDENCE_REFRESH_PROOF_SOURCE,
    advisory_proof_contract_snapshot,
    freshness_snapshot,
    InsightResult,
    load_evidence_refresh_proof,
    proof_contract_payload,
)
from apps.reports.models import SystemTicket


class VerifiedIntelligenceCircuitBreakerTests(TestCase):
    def setUp(self):
        cache.clear()

    def _create_evidence(
        self,
        *,
        scope: str,
        cache_key: str,
        title: str | None = None,
        source_name: str = "Example Source",
        source_url: str | None = None,
        query: str = "",
        status: str = "stale",
        stale_after=None,
        payload: dict | None = None,
    ) -> VerifiedExternalInsight:
        now = timezone.now()
        return VerifiedExternalInsight.objects.create(
            scope=scope,
            cache_key=cache_key,
            title=title or f"{scope} evidence",
            source_name=source_name,
            source_url=source_url or f"https://example.com/{scope}/{cache_key.replace(':', '-')}",
            query=query,
            summary="Stored evidence",
            payload=payload or {"stored": True},
            checksum=cache_key,
            status=status,
            fetched_at=now - timedelta(hours=4),
            verified_at=now - timedelta(hours=4),
            stale_after=stale_after or now - timedelta(hours=1),
            notes="",
            is_active=True,
        )

    def test_freshness_snapshot_treats_due_records_as_not_fresh(self):
        now = timezone.now()
        snapshot = freshness_snapshot(
            [
                {
                    "source_name": "Fresh source",
                    "source_url": "https://example.com/fresh",
                    "status": "fresh",
                    "stale_after": (now + timedelta(hours=2)).isoformat(),
                },
                {
                    "source_name": "Due source",
                    "source_url": "https://example.com/due",
                    "status": "fresh",
                    "stale_after": (now - timedelta(minutes=5)).isoformat(),
                },
                {
                    "source_name": "Missing freshness",
                    "source_url": "https://example.com/missing",
                    "status": "fresh",
                },
            ]
        )

        self.assertEqual(snapshot["tracked_records"], 3)
        self.assertEqual(snapshot["fresh_records"], 1)
        self.assertEqual(snapshot["stale_or_due_records"], 2)
        self.assertEqual(snapshot["missing_freshness_records"], 1)
        self.assertFalse(snapshot["proof_complete"])

    def test_advisory_proof_contract_requires_fresh_source_backed_records(self):
        now = timezone.now()
        evidence = [
            {
                "source_name": "World Bank",
                "source_url": "https://example.com/world-bank",
                "status": "fresh",
                "stale_after": (now + timedelta(hours=2)).isoformat(),
            }
        ]
        contract = proof_contract_payload(
            evidence_items=evidence,
            required_sources=["World Bank", "Yahoo Finance"],
            advisory_surface="recommendation_overview",
        )

        self.assertFalse(contract["complete"])
        self.assertEqual(contract["missing_required_sources"], ["Yahoo Finance"])
        self.assertEqual(contract["refresh_contract"]["scheduled_refresh"], "refresh_due_records")
        self.assertTrue(contract["refresh_contract"]["stale_after_required"])
        self.assertTrue(contract["refresh_contract"]["source_url_required"])
        self.assertTrue(contract["refresh_contract"]["stale_fallback"])
        self.assertTrue(contract["refresh_contract"]["circuit_breaker"])

    def test_advisory_proof_contract_snapshot_covers_current_signal_surfaces(self):
        snapshot = advisory_proof_contract_snapshot()

        self.assertTrue(snapshot["healthy"])
        self.assertEqual(snapshot["covered_surface_count"], snapshot["surface_count"])
        self.assertEqual(snapshot["scheduled_refresh"], "refresh_due_records")
        self.assertIn("relationship-adjacent", snapshot["new_signal_rule"])
        self.assertTrue(any(surface["key"] == "relationship_alignment" for surface in snapshot["surfaces"]))
        self.assertTrue(any(surface["key"] == "recommendation_overview" for surface in snapshot["surfaces"]))
        for feature in ("source_url", "stale_after", "scheduled_refresh", "circuit_breaker", "stale_fallback"):
            self.assertIn(feature, snapshot["required_features"])

    def test_circuit_breaker_falls_back_to_stale_payload_after_repeated_failures(self):
        now = timezone.now()
        VerifiedExternalInsight.objects.create(
            scope="news",
            cache_key="google-news:test-role",
            title="Test feed",
            source_name="Google News RSS",
            source_url="https://news.google.com/rss/search?q=test-role",
            query="test role",
            summary="Existing cached payload",
            payload={"items": [{"title": "cached"}]},
            checksum="abc",
            status="stale",
            fetched_at=now - timedelta(hours=3),
            verified_at=now - timedelta(hours=3),
            stale_after=now - timedelta(hours=1),
            notes="older cached record",
            is_active=True,
        )

        failing_fetcher = Mock(side_effect=RuntimeError("upstream unavailable"))
        for _ in range(3):
            result = verified_intelligence._use_or_refresh(
                scope="news",
                cache_key="google-news:test-role",
                title="Test feed",
                source_name="Google News RSS",
                source_url="https://news.google.com/rss/search?q=test-role",
                ttl=timedelta(hours=8),
                fetcher=failing_fetcher,
                query="test role",
            )
            self.assertEqual(result.payload["items"][0]["title"], "cached")
            self.assertTrue(result.cached)

        blocked_fetcher = Mock(side_effect=AssertionError("breaker should stop this fetch"))
        result = verified_intelligence._use_or_refresh(
            scope="news",
            cache_key="google-news:test-role",
            title="Test feed",
            source_name="Google News RSS",
            source_url="https://news.google.com/rss/search?q=test-role",
            ttl=timedelta(hours=8),
            fetcher=blocked_fetcher,
            query="test role",
        )

        self.assertEqual(blocked_fetcher.call_count, 0)
        self.assertEqual(result.payload["items"][0]["title"], "cached")
        self.assertIn("Circuit breaker", result.evidence.get("notes", ""))
        record = VerifiedExternalInsight.objects.get(scope="news", cache_key="google-news:test-role", is_active=True)
        self.assertEqual(record.last_refresh_status, "skipped")
        self.assertTrue(record.last_refresh_attempt_at)
        self.assertIn("Circuit breaker", record.last_refresh_error)

    def test_refresh_due_records_respects_batch_size(self):
        now = timezone.now()
        VerifiedExternalInsight.objects.create(
            scope="news",
            cache_key="google-news:first",
            title="First feed",
            source_name="Google News RSS",
            source_url="https://news.google.com/rss/search?q=first",
            query="first",
            summary="First stale record",
            payload={"items": []},
            checksum="first",
            status="stale",
            fetched_at=now - timedelta(hours=4),
            verified_at=now - timedelta(hours=4),
            stale_after=now - timedelta(hours=1),
            notes="",
            is_active=True,
        )
        VerifiedExternalInsight.objects.create(
            scope="jobs",
            cache_key="remotive:second",
            title="Second feed",
            source_name="Remotive Jobs API",
            source_url="https://remotive.com/api/remote-jobs",
            query="second",
            summary="Second stale record",
            payload={"jobs": []},
            checksum="second",
            status="stale",
            fetched_at=now - timedelta(hours=4),
            verified_at=now - timedelta(hours=4),
            stale_after=now - timedelta(hours=1),
            notes="",
            is_active=True,
        )

        with patch.object(verified_intelligence, "google_news_search", return_value={"items": []}) as news_mock, patch.object(
            verified_intelligence,
            "remotive_jobs",
            return_value={"jobs": []},
        ) as jobs_mock:
            result = verified_intelligence.refresh_due_records(batch_size=1)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["refreshed"], 1)
        self.assertEqual(result["batch_size"], 1)
        self.assertEqual(news_mock.call_count + jobs_mock.call_count, 1)
        self.assertEqual(result["candidate_records"], 2)
        self.assertEqual(result["capacity_gap_records"], 1)
        self.assertTrue(result["batch_limited"])

    def test_refresh_health_snapshot_reports_capacity_gap_and_per_scope_state(self):
        now = timezone.now()
        with patch.object(verified_intelligence, "REFRESH_BATCH_SIZE", 2):
            self._create_evidence(
                scope="jobs",
                cache_key="remotive:python",
                source_name="Remotive Jobs API",
                source_url="https://remotive.com/api/remote-jobs",
                query="python",
                status="fresh",
                stale_after=now - timedelta(minutes=10),
            )
            self._create_evidence(
                scope="news",
                cache_key="google-news:market",
                source_name="Google News RSS",
                source_url="https://news.google.com/rss/search?q=market",
                query="market",
                status="stale",
                stale_after=now - timedelta(hours=1),
            )
            self._create_evidence(
                scope="market",
                cache_key="india-equity-volatility",
                source_name="Yahoo Finance",
                source_url="https://finance.yahoo.com/quote/%5ENSEI/",
                status="fresh",
                stale_after=now + timedelta(hours=12),
            )
            self._create_evidence(
                scope="macro",
                cache_key="world-bank:FP.CPI.TOTL.ZG",
                source_name="World Bank",
                source_url="https://api.worldbank.org/v2/country/IND/indicator/FP.CPI.TOTL.ZG?format=json&per_page=8",
                status="fresh",
                stale_after=now + timedelta(days=30),
            )
            self._create_evidence(
                scope="tax",
                cache_key="india-income-tax-regimes",
                source_name="Income Tax Department",
                source_url="https://www.incometax.gov.in/iec/foportal/",
                status="failed",
                stale_after=now + timedelta(days=30),
            )

            health = verified_intelligence.refresh_health_snapshot(now=now)

        self.assertEqual(health["active_records"], 5)
        self.assertEqual(health["fresh_records"], 2)
        self.assertEqual(health["watchlist_records"], 3)
        self.assertEqual(health["due_records"], 1)
        self.assertEqual(health["scheduled_candidate_records"], 3)
        self.assertEqual(health["scheduled_refresh_batch_size"], 2)
        self.assertEqual(health["capacity_gap_records"], 1)
        self.assertTrue(health["batch_limited"])
        self.assertFalse(health["freshness_healthy"])
        self.assertFalse(health["scheduled_refresh_healthy"])
        self.assertFalse(health["healthy"])
        self.assertIn("candidate gap", health["summary"])

        scopes = {item["scope"]: item for item in health["per_scope"]}
        self.assertEqual(set(scopes), {"jobs", "macro", "market", "news", "tax"})
        self.assertEqual(scopes["jobs"]["due_records"], 1)
        self.assertEqual(scopes["news"]["stale_records"], 1)
        self.assertEqual(scopes["tax"]["failed_records"], 1)
        self.assertEqual(scopes["market"]["fresh_records"], 1)
        self.assertEqual(scopes["macro"]["fresh_records"], 1)
        self.assertEqual(scopes["jobs"]["scheduled_candidate_records"], 1)
        self.assertEqual(scopes["news"]["scheduled_candidate_records"], 1)
        self.assertEqual(scopes["tax"]["scheduled_candidate_records"], 1)

    def test_refresh_due_records_reduces_watchlist_and_includes_failed_records(self):
        now = timezone.now()
        self._create_evidence(
            scope="news",
            cache_key="google-news:market",
            source_name="Google News RSS",
            source_url="https://news.google.com/rss/search?q=market&hl=en-IN&gl=IN&ceid=IN:en",
            query="market",
            status="stale",
            stale_after=now - timedelta(hours=1),
        )
        self._create_evidence(
            scope="jobs",
            cache_key="remotive:python",
            source_name="Remotive Jobs API",
            source_url="https://remotive.com/api/remote-jobs",
            query="python",
            status="failed",
            stale_after=now + timedelta(days=1),
        )

        with patch.object(
            verified_intelligence,
            "_fetch_google_news",
            return_value=({"items": []}, "News refreshed.", "notes"),
        ) as news_mock, patch.object(
            verified_intelligence,
            "_fetch_remotive_jobs",
            return_value=({"jobs": []}, "Jobs refreshed.", "notes"),
        ) as jobs_mock:
            result = verified_intelligence.refresh_due_records(batch_size=2)

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["refreshed"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["watchlist_before"], 2)
        self.assertEqual(result["watchlist_after"], 0)
        self.assertTrue(result["watchlist_reduced"])
        self.assertEqual(result["candidate_records"], 2)
        self.assertEqual(result["capacity_gap_records"], 0)
        self.assertFalse(result["batch_limited"])
        self.assertEqual(news_mock.call_count, 1)
        self.assertEqual(jobs_mock.call_count, 1)
        self.assertTrue(all(scope["watchlist_records"] == 0 for scope in result["per_scope_health"]))

    def test_refresh_due_records_routes_job_records_to_source_adapter(self):
        now = timezone.now()
        for cache_key, source_name, source_url in [
            ("arbeitnow:data-analyst", "Arbeitnow Job Board API", "https://www.arbeitnow.com/api/job-board-api"),
            ("remoteok:data-analyst", "Remote OK API", "https://remoteok.com/api"),
        ]:
            VerifiedExternalInsight.objects.create(
                scope="jobs",
                cache_key=cache_key,
                title=f"{source_name} stale feed",
                source_name=source_name,
                source_url=source_url,
                query="data analyst",
                summary="Stale job feed",
                payload={"jobs": []},
                checksum=cache_key,
                status="stale",
                fetched_at=now - timedelta(hours=4),
                verified_at=now - timedelta(hours=4),
                stale_after=now - timedelta(hours=1),
                notes="",
                is_active=True,
            )

        with patch.object(verified_intelligence, "arbeitnow_jobs") as arbeitnow_mock, patch.object(
            verified_intelligence,
            "remoteok_jobs",
        ) as remoteok_mock, patch.object(verified_intelligence, "remotive_jobs") as remotive_mock:
            result = verified_intelligence.refresh_due_records(batch_size=2)

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["refreshed"], 2)
        self.assertEqual(arbeitnow_mock.call_count, 1)
        self.assertEqual(remoteok_mock.call_count, 1)
        self.assertEqual(remotive_mock.call_count, 0)

    def test_refresh_due_records_forces_due_soon_records_and_reports_health(self):
        now = timezone.now()
        original = self._create_evidence(
            scope="market",
            cache_key="india-equity-volatility",
            title="India Market Snapshot",
            source_name="Yahoo Finance",
            source_url="https://finance.yahoo.com/quote/%5ENSEI/",
            status="fresh",
            stale_after=now + timedelta(hours=1),
            payload={"nifty_close": 100},
        )

        with patch.object(
            verified_intelligence,
            "_fetch_market_snapshot",
            return_value=(
                {"nifty_close": 123.45, "one_month_return_pct": 1.1, "india_vix": 12.3},
                "Market refreshed.",
                "Fresh market data.",
            ),
        ) as fetch_mock:
            result = verified_intelligence.refresh_due_records(batch_size=1)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["refreshed"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["watchlist_before"], 0)
        self.assertEqual(result["watchlist_after"], 0)
        self.assertTrue(result["last_refresh_attempt_at"])
        self.assertTrue(result["last_refresh_success_at"])
        self.assertEqual(result["per_scope"], [{"scope": "market", "processed": 1, "refreshed": 1, "skipped": 0, "failed": 0}])
        self.assertEqual(fetch_mock.call_count, 1)

        original.refresh_from_db()
        self.assertFalse(original.is_active)
        latest = VerifiedExternalInsight.objects.get(scope="market", cache_key="india-equity-volatility", is_active=True)
        self.assertEqual(latest.payload["nifty_close"], 123.45)
        self.assertEqual(latest.last_refresh_status, "refreshed")
        self.assertTrue(latest.last_refresh_attempt_at)
        self.assertTrue(latest.last_refresh_success_at)

    def test_refresh_due_records_reports_per_scope_and_unsupported_skips(self):
        unsupported = self._create_evidence(
            scope="unknown",
            cache_key="unsupported",
            title="Unsupported Evidence",
            source_name="Unsupported",
            source_url="https://example.com/unsupported",
        )

        result = verified_intelligence.refresh_due_records(batch_size=1)

        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["refreshed"], 0)
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["watchlist_before"], 1)
        self.assertEqual(result["watchlist_after"], 1)
        self.assertEqual(result["per_scope"], [{"scope": "unknown", "processed": 1, "refreshed": 0, "skipped": 1, "failed": 0}])
        self.assertEqual(result["records"][0]["status"], "skipped")
        self.assertIn("No refresh adapter", result["records"][0]["reason"])

        unsupported.refresh_from_db()
        self.assertEqual(unsupported.status, "stale")
        self.assertEqual(unsupported.last_refresh_status, "skipped")
        self.assertTrue(unsupported.last_refresh_attempt_at)
        self.assertIn("No refresh adapter", unsupported.last_refresh_error)

    def test_refresh_due_records_routes_all_supported_cache_key_patterns(self):
        supported_records = [
            {
                "scope": "macro",
                "cache_key": "world-bank:FP.CPI.TOTL.ZG",
                "title": "India inflation rate",
                "source_name": "World Bank",
                "source_url": "https://api.worldbank.org/v2/country/IND/indicator/FP.CPI.TOTL.ZG?format=json&per_page=8",
            },
            {
                "scope": "market",
                "cache_key": "india-equity-volatility",
                "title": "India Market Snapshot",
                "source_name": "Yahoo Finance",
                "source_url": "https://finance.yahoo.com/quote/%5ENSEI/",
            },
            {
                "scope": "travel",
                "cache_key": "geocode:darjeeling",
                "title": "Destination match for Darjeeling",
                "source_name": "OpenStreetMap Nominatim",
                "source_url": "https://nominatim.openstreetmap.org/search",
                "query": "Darjeeling",
            },
            {
                "scope": "travel",
                "cache_key": "offbeat:darjeeling",
                "title": "Offbeat suggestions near Darjeeling",
                "source_name": "OpenStreetMap Nominatim",
                "source_url": "https://nominatim.openstreetmap.org/search",
                "query": "Darjeeling",
            },
            {
                "scope": "travel",
                "cache_key": "weather:27.030:88.260:2026-08-05:2026-08-06",
                "title": "Weather forecast 2026-08-05 to 2026-08-06",
                "source_name": "Open-Meteo",
                "source_url": "https://api.open-meteo.com/v1/forecast",
            },
            {
                "scope": "news",
                "cache_key": "google-news:test-role",
                "title": "Google News search for test role",
                "source_name": "Google News RSS",
                "source_url": "https://news.google.com/rss/search?q=test+role&hl=en-IN&gl=IN&ceid=IN:en",
                "query": "test role",
            },
            {
                "scope": "jobs",
                "cache_key": "remotive:data-analyst",
                "title": "Remotive job search for data analyst",
                "source_name": "Remotive Jobs API",
                "source_url": "https://remotive.com/api/remote-jobs",
                "query": "data analyst",
            },
            {
                "scope": "jobs",
                "cache_key": "arbeitnow:data-analyst",
                "title": "Arbeitnow job search for data analyst",
                "source_name": "Arbeitnow Job Board API",
                "source_url": "https://www.arbeitnow.com/api/job-board-api",
                "query": "data analyst",
            },
            {
                "scope": "jobs",
                "cache_key": "remoteok:data-analyst",
                "title": "Remote OK job search for data analyst",
                "source_name": "Remote OK API",
                "source_url": "https://remoteok.com/api",
                "query": "data analyst",
            },
            {
                "scope": "tax",
                "cache_key": "india-income-tax-regimes",
                "title": "India income tax regime reference",
                "source_name": "Income Tax Department",
                "source_url": "https://www.incometax.gov.in/iec/foportal/",
            },
            {
                "scope": "tax",
                "cache_key": "india-nps-tax-benefit",
                "title": "NPS tax benefit reference",
                "source_name": "NPS Trust",
                "source_url": "https://npstrust.org.in/",
            },
            {
                "scope": "tax",
                "cache_key": "india-ppf-reference",
                "title": "PPF contribution reference",
                "source_name": "India Post",
                "source_url": "https://www.indiapost.gov.in/Financial/pages/content/post-office-saving-schemes.aspx",
            },
        ]
        for item in supported_records:
            self._create_evidence(**item, payload={"previous": item["cache_key"]})

        with patch.object(
            verified_intelligence,
            "_fetch_world_bank",
            return_value=({"latest_year": "2026", "latest_value": 4.2, "series": []}, "World Bank refreshed.", "notes"),
        ) as world_bank_mock, patch.object(
            verified_intelligence,
            "_fetch_market_snapshot",
            return_value=({"nifty_close": 25000.0, "one_month_return_pct": 1.0, "india_vix": 12.0}, "Market refreshed.", "notes"),
        ) as market_mock, patch.object(
            verified_intelligence,
            "_fetch_geocode",
            return_value=({"display_name": "Darjeeling", "latitude": 27.03, "longitude": 88.26}, "Geocode refreshed.", "notes"),
        ) as geocode_mock, patch.object(
            verified_intelligence,
            "_fetch_offbeat",
            return_value=({"results": []}, "Offbeat refreshed.", "notes"),
        ) as offbeat_mock, patch.object(
            verified_intelligence,
            "_fetch_weather",
            return_value=({"average_max_temp": 23.0}, "Weather refreshed.", "notes"),
        ) as weather_mock, patch.object(
            verified_intelligence,
            "_fetch_google_news",
            return_value=({"items": []}, "News refreshed.", "notes"),
        ) as news_mock, patch.object(
            verified_intelligence,
            "_fetch_remotive_jobs",
            return_value=({"jobs": []}, "Remotive refreshed.", "notes"),
        ) as remotive_mock, patch.object(
            verified_intelligence,
            "_fetch_arbeitnow_jobs",
            return_value=({"jobs": []}, "Arbeitnow refreshed.", "notes"),
        ) as arbeitnow_mock, patch.object(
            verified_intelligence,
            "_fetch_remoteok_jobs",
            return_value=({"jobs": []}, "Remote OK refreshed.", "notes"),
        ) as remoteok_mock:
            result = verified_intelligence.refresh_due_records(batch_size=20)

        self.assertEqual(result["processed"], len(supported_records))
        self.assertEqual(result["refreshed"], len(supported_records))
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["watchlist_before"], len(supported_records))
        self.assertEqual(result["watchlist_after"], 0)
        self.assertTrue(result["last_refresh_attempt_at"])
        self.assertTrue(result["last_refresh_success_at"])
        self.assertEqual(world_bank_mock.call_count, 1)
        self.assertEqual(market_mock.call_count, 1)
        self.assertEqual(geocode_mock.call_count, 1)
        self.assertEqual(offbeat_mock.call_count, 1)
        self.assertEqual(weather_mock.call_count, 1)
        self.assertEqual(news_mock.call_count, 1)
        self.assertEqual(remotive_mock.call_count, 1)
        self.assertEqual(arbeitnow_mock.call_count, 1)
        self.assertEqual(remoteok_mock.call_count, 1)

        per_scope = {item["scope"]: item for item in result["per_scope"]}
        self.assertEqual(per_scope["macro"]["refreshed"], 1)
        self.assertEqual(per_scope["market"]["refreshed"], 1)
        self.assertEqual(per_scope["travel"]["refreshed"], 3)
        self.assertEqual(per_scope["news"]["refreshed"], 1)
        self.assertEqual(per_scope["jobs"]["refreshed"], 3)
        self.assertEqual(per_scope["tax"]["refreshed"], 3)

        health = verified_intelligence.refresh_health_snapshot()
        health_scopes = [scope["scope"] for scope in health["per_scope"]]
        self.assertTrue(health["healthy"])
        self.assertEqual(health["active_records"], len(supported_records))
        self.assertEqual(health["fresh_records"], len(supported_records))
        self.assertEqual(health["watchlist_records"], 0)
        self.assertEqual(len(health_scopes), len(set(health_scopes)))
        self.assertTrue(all(scope["last_refresh_success_at"] for scope in health["per_scope"]))

    def test_refresh_due_records_can_write_accepted_refresh_proof(self):
        now = timezone.now()
        self._create_evidence(
            scope="news",
            cache_key="google-news:market",
            source_name="Google News RSS",
            source_url="https://news.google.com/rss/search?q=market&hl=en-IN&gl=IN&ceid=IN:en",
            query="market",
            status="stale",
            stale_after=now - timedelta(hours=1),
        )

        with tempfile.TemporaryDirectory() as tempdir, patch.object(
            verified_intelligence,
            "_fetch_google_news",
            return_value=({"items": []}, "News refreshed.", "notes"),
        ):
            proof_path = Path(tempdir) / "evidence-refresh-proof.json"
            result = verified_intelligence.refresh_due_records(
                batch_size=1,
                write_proof=True,
                proof_path=proof_path,
            )
            loaded = load_evidence_refresh_proof(proof_path)

        proof = result["refresh_proof"]
        self.assertEqual(proof["source"], EVIDENCE_REFRESH_PROOF_SOURCE)
        self.assertEqual(proof["validation"]["state"], "accepted")
        self.assertEqual(proof["validation"]["fresh_records"], 1)
        self.assertEqual(proof["validation"]["watchlist_records"], 0)
        self.assertTrue(loaded["accepted"])
        self.assertEqual(loaded["path"], str(proof_path))
        self.assertIn("Accepted evidence refresh proof", loaded["summary"])


class ProjectDetailsDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="project_user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(username="project_admin", password="Pass12345!", email="admin@example.com")

    def test_project_details_dashboard_is_superuser_only(self):
        self.client.force_login(self.user)
        response = self.client.get("/project-details/")
        self.assertEqual(response.status_code, 403)

    def test_project_details_dashboard_renders_for_superuser(self):
        SystemTicket.objects.create(
            user=self.user,
            module="reports",
            title="Escalated issue",
            summary="High severity example",
            severity="high",
            handled_by="developer",
            status="open",
        )
        self.client.force_login(self.superuser)
        response = self.client.get("/project-details/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operational Guardrails")
        self.assertContains(response, "Adaptive Learning Progress")
        self.assertContains(response, "In Progress Tracks")
        self.assertContains(response, "Operational Snapshot")
        self.assertContains(response, "Internal Clock")
        self.assertContains(response, "Developer Escalations")

    def test_reports_dashboard_is_superuser_only(self):
        self.client.force_login(self.user)
        response = self.client.get("/reports/")
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.superuser)
        response = self.client.get("/reports/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Superuser report library")

    def test_main_dashboard_no_longer_shows_platform_status_block(self):
        self.client.force_login(self.user)
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Platform Roadmap")
        self.assertNotContains(response, "Completion Snapshot")
