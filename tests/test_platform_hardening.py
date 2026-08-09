import json
import socket
from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase

from alfred_ai.services.url_safety import validate_public_http_url
from apps.career.services.job_intelligence import job_intelligence
from apps.expenses.models import BankAccount, Expense
from apps.integrations.models import EmailConnection
from apps.mobility.models import BikeProfile, TravelPlan, TripLog
from apps.reports.models import SystemTicket


class SettingsHardeningTests(SimpleTestCase):
    def test_production_defaults_are_not_permissive(self):
        from alfred_ai.settings import (
            _default_allowed_hosts,
            _default_cors_allow_all,
            _default_hsts_seconds,
            _default_secret_key,
            _default_secure_cookie,
            _default_ssl_redirect,
        )

        self.assertEqual(_default_secret_key(False), "")
        self.assertEqual(_default_allowed_hosts(False), [])
        self.assertFalse(_default_cors_allow_all(False))
        self.assertTrue(_default_ssl_redirect(False))
        self.assertTrue(_default_secure_cookie(False))
        self.assertGreater(_default_hsts_seconds(False), 0)

    def test_local_runtime_defaults_preserve_safe_dev_usability(self):
        from alfred_ai.settings import (
            _default_allowed_hosts,
            _default_cors_allow_all,
            _default_hsts_seconds,
            _default_secret_key,
            _default_secure_cookie,
            _default_ssl_redirect,
        )

        self.assertTrue(_default_secret_key(True))
        self.assertIn("localhost", _default_allowed_hosts(True))
        self.assertIn("testserver", _default_allowed_hosts(True))
        self.assertTrue(_default_cors_allow_all(True))
        self.assertFalse(_default_ssl_redirect(True))
        self.assertFalse(_default_secure_cookie(True))
        self.assertEqual(_default_hsts_seconds(True), 0)


class OutboundUrlSafetyTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="career_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_validate_public_http_url_blocks_unsafe_targets(self):
        blocked = [
            "file:///etc/passwd",
            "http://localhost:8000/admin",
            "http://127.0.0.1:8000/admin",
            "http://169.254.169.254/latest/meta-data/",
        ]

        for url in blocked:
            with self.assertRaises(ValueError):
                validate_public_http_url(url)

    @patch(
        "alfred_ai.services.url_safety.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))],
    )
    @patch("apps.career.services.job_intelligence.requests.get")
    def test_job_page_parser_allows_public_targets(self, requests_get, _getaddrinfo):
        response = Mock()
        response.text = """
            <html>
                <head><title>Backend Engineer</title></head>
                <body>
                    <main>Python Django role in Bengaluru with SQL and Docker.</main>
                </body>
            </html>
        """
        response.raise_for_status = Mock()
        requests_get.return_value = response

        snapshot = job_intelligence.parse_job_page("https://example.com/jobs/backend-engineer")

        self.assertEqual(snapshot.job_url, "https://example.com/jobs/backend-engineer")
        self.assertEqual(snapshot.source_name, "example.com")
        requests_get.assert_called_once()

    @patch(
        "apps.career.views.verified_intelligence.macro_context",
        return_value={
            "payload": {
                "unemployment": {"latest_value": 5.0},
                "inflation": {"latest_value": 5.0},
                "market": {"one_month_return_pct": 0.0},
            },
            "evidence": [],
        },
    )
    def test_job_match_api_rejects_local_targets(self, _macro_context):
        response = self.client.post(
            "/api/career/job-match/",
            data=json.dumps({"job_url": "http://127.0.0.1:8000/private"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("allowed", response.json()["detail"].lower())


class ApiPaginationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="list_user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(
            username="list_admin",
            password="Pass12345!",
            email="admin@example.com",
        )
        self.client = Client()
        self.client.force_login(self.user)

    def test_expense_list_supports_paginated_results(self):
        account = BankAccount.objects.create(
            user=self.user,
            bank_name="HDFC",
            account_number="1234567890",
            account_type="savings",
        )
        for index in range(23):
            Expense.objects.create(
                user=self.user,
                bank_account=account,
                amount=100 + index,
                category="food",
                transaction_date=date(2026, 3, 1) + timedelta(days=index),
                source="manual",
            )

        response = self.client.get("/api/expenses/?page=1&page_size=10")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "23")
        self.assertEqual(response["X-Page-Size"], "10")
        self.assertEqual(response["X-Page"], "1")
        self.assertEqual(response["X-Has-Next"], "true")
        self.assertEqual(len(payload), 10)

    def test_trip_log_list_supports_paginated_results(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Hunter 350",
            model_name="Hunter 350",
            vehicle_type="motorcycle",
        )
        plan = TravelPlan.objects.create(
            user=self.user,
            vehicle_profile=profile,
            title="Weekend Ride",
            destination="Coorg",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 3),
        )
        for index in range(15):
            TripLog.objects.create(
                user=self.user,
                travel_plan=plan,
                log_date=date(2026, 4, 1) + timedelta(days=index),
                title=f"Log {index}",
                distance_km=25 + index,
                spend_amount=150 + index,
            )

        response = self.client.get("/api/mobility/trip-logs/?page=2&page_size=10")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "15")
        self.assertEqual(response["X-Page-Size"], "10")
        self.assertEqual(response["X-Page"], "2")
        self.assertEqual(response["X-Has-Previous"], "true")
        self.assertEqual(len(payload), 5)

    def test_system_ticket_list_supports_paginated_results(self):
        for index in range(12):
            SystemTicket.objects.create(
                user=self.user,
                module="general",
                title=f"Ticket {index}",
                summary="Summary",
                severity="medium",
                handled_by="alfred",
            )

        self.client.force_login(self.superuser)
        response = self.client.get("/api/reports/tickets/?page=1&page_size=10")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "12")
        self.assertEqual(response["X-Has-Next"], "true")
        self.assertEqual(len(payload), 10)

    def test_expense_list_is_paginated_by_default_without_query_params(self):
        account = BankAccount.objects.create(
            user=self.user,
            bank_name="HDFC",
            account_number="222233334444",
            account_type="savings",
        )
        for index in range(31):
            Expense.objects.create(
                user=self.user,
                bank_account=account,
                amount=80 + index,
                category="food",
                transaction_date=date(2026, 2, 1) + timedelta(days=index),
                source="manual",
            )

        response = self.client.get("/api/expenses/")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Total-Count"], "31")
        self.assertEqual(response["X-Page-Size"], "25")
        self.assertEqual(response["X-Page"], "1")
        self.assertEqual(response["X-Has-Next"], "true")
        self.assertEqual(len(payload), 25)


class EmailConnectionTokenSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="email_user", password="Pass12345!")

    def test_email_tokens_are_encrypted_at_rest(self):
        connection = EmailConnection.objects.create(
            user=self.user,
            provider="GMAIL",
            email_address="user@example.com",
            access_token="plain-access-token",
            refresh_token="plain-refresh-token",
        )

        raw = EmailConnection.objects.values("access_token", "refresh_token").get(pk=connection.pk)

        self.assertNotEqual(raw["access_token"], "plain-access-token")
        self.assertNotEqual(raw["refresh_token"], "plain-refresh-token")
        self.assertTrue(raw["access_token"].startswith("enc::"))
        self.assertTrue(raw["refresh_token"].startswith("enc::"))
        self.assertEqual(connection.get_access_token(), "plain-access-token")
        self.assertEqual(connection.get_refresh_token(), "plain-refresh-token")


class HealthEndpointTests(TestCase):
    def test_liveness_endpoint_does_not_probe_dependencies(self):
        response = self.client.get("/health/live/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_readiness_endpoint_checks_database_and_cache(self):
        response = self.client.get("/health/ready/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertEqual(response.json()["checks"]["database"], "ok")
        self.assertEqual(response.json()["checks"]["cache"], "ok")

    def test_health_endpoint_returns_ok_status(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["checks"]["database"], "ok")
        self.assertEqual(response.json()["checks"]["cache"], "ok")
        self.assertIn("ml_runtime", response.json()["checks"])
        self.assertIn("ml_startup_gate", response.json()["checks"])
