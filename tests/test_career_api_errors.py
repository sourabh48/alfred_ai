import json
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.test import Client, TestCase


PRIVATE_MARKER = "synthetic-secret-token-in-private-parser-path"


class CareerApiErrorTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="career_error_user", password="Orbit-X8!Lantern")
        self.client.force_login(self.user)

    def assert_safe_response(self, response, field, status):
        self.assertEqual(response.status_code, status)
        self.assertNotIn(PRIVATE_MARKER, response.content.decode())
        payload = response.json()
        self.assertEqual(set(payload), {field, "error_id"})
        self.assertTrue(payload[field])
        UUID(payload["error_id"])

    def test_projection_failure_does_not_return_exception_text(self):
        with patch("apps.career.views._get_profile", side_effect=RuntimeError(PRIVATE_MARKER)):
            response = self.client.get("/api/career/projection/")
        self.assert_safe_response(response, "error", 500)

    def test_recruiter_parser_failure_does_not_return_exception_text(self):
        with patch("apps.career.views.verified_intelligence.macro_context", return_value={}), patch(
            "apps.career.views.build_employment_income_signals", return_value={}
        ), patch("apps.career.views.job_intelligence.parse_recruiter_message", side_effect=ValueError(PRIVATE_MARKER)):
            response = self.client.post("/api/career/recruiter-match/",
                                        json.dumps({"message_text": "Synthetic recruiter text"}),
                                        content_type="application/json")
        self.assert_safe_response(response, "detail", 400)

    def test_job_parser_failure_does_not_return_exception_text(self):
        with patch("apps.career.views.verified_intelligence.macro_context", return_value={}), patch(
            "apps.career.views.build_employment_income_signals", return_value={}
        ), patch("apps.career.views.job_intelligence.parse_job_page", side_effect=RuntimeError(PRIVATE_MARKER)):
            response = self.client.post("/api/career/job-match/",
                                        json.dumps({"job_url": "https://jobs.example.com/role"}),
                                        content_type="application/json")
        self.assert_safe_response(response, "detail", 400)

    def test_failure_log_contains_reference_and_class_without_private_details(self):
        with patch("apps.career.views._get_profile", side_effect=RuntimeError(PRIVATE_MARKER)), self.assertLogs(
            "apps.career.views", level="ERROR"
        ) as captured:
            first = self.client.get("/api/career/projection/")
            second = self.client.get("/api/career/projection/")
        log_text = " ".join(captured.output)
        self.assertNotIn(PRIVATE_MARKER, log_text)
        self.assertIn("RuntimeError", log_text)
        self.assertIn(first.json()["error_id"], log_text)
        self.assertIn(second.json()["error_id"], log_text)
        self.assertNotEqual(first.json()["error_id"], second.json()["error_id"])
        self.assertTrue(all(record.exc_info is None for record in captured.records))

    def test_anonymous_projection_does_not_execute_private_handler(self):
        with patch("apps.career.views._get_profile") as get_profile:
            response = Client().get("/api/career/projection/")
        self.assertEqual(response.status_code, 403)
        get_profile.assert_not_called()
