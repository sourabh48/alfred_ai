from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.integrations.services import verified_intelligence
from apps.integrations.services.verified_intelligence import freshness_snapshot
from apps.reports.models import SystemTicket


class VerifiedIntelligenceCircuitBreakerTests(TestCase):
    def setUp(self):
        cache.clear()

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
