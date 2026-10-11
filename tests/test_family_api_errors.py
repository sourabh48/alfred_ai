"""Family Growth exposes safe failures, never internal financial diagnostics."""
import base64
import json
from datetime import timedelta
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialize_payload
from apps.family.models import FamilyAccountLink
from apps.family.views import _family_growth_revision
from tests.test_family_account_links import _fresh_evidence


PRIVATE_MARKERS = ("SyntheticFamilyIdentity", "123456.78", "Bearer synthetic-token", r"F:\synthetic-private\ledger.db", "Traceback (synthetic)")
PRIVATE_TEXT = "; ".join(PRIVATE_MARKERS)
SAFE_MESSAGE = "Family growth is temporarily unavailable. Please try again."


class FamilyApiErrorTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-family-error-limits-"))
        self.enterContext(override_settings(ALFRED_FAMILY_INVITE_THROTTLE_DIR=directory))
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = get_user_model().objects.create_user(username="family_error_user", password="Orbit-X8!Lantern")
        self.client.force_login(self.user)
        self.baseline = dict(total_assets=100000, total_liabilities=10000, net_worth=90000, monthly_income=30000, savings_capacity=5000)
        self.baseline_patch = patch("apps.family.views.resolve_canonical_financial_baseline", return_value=self.baseline)
        self.resolve = self.baseline_patch.start()
        self.addCleanup(self.baseline_patch.stop)
        for name, source in (("ppf_reference", "India Post"), ("nps_tax_reference", "NPS Trust")):
            reference = patch("apps.family.views.verified_intelligence." + name,
                              return_value=SimpleNamespace(evidence=_fresh_evidence(source)))
            reference.start()
            self.addCleanup(reference.stop)

    def assert_private_text_absent(self, response):
        for marker in PRIVATE_MARKERS:
            self.assertNotIn(marker, response.content.decode())
            self.assertNotIn(json.dumps(marker)[1:-1], response.content.decode())

    def assert_safe_failure(self, response):
        self.assertEqual(response.status_code, 500)
        self.assert_private_text_absent(response)
        payload = response.json()
        self.assertEqual(set(payload), {"error", "error_id"})
        self.assertEqual(payload["error"], SAFE_MESSAGE)
        UUID(payload["error_id"])

    def test_service_database_cache_projection_and_reference_failures_are_safe(self):
        for target, exception in (
            ("resolve_canonical_financial_baseline", RuntimeError(PRIVATE_TEXT)),
            ("Dependent.objects.filter", DatabaseError(PRIVATE_TEXT)),
            ("materialize_payload", RuntimeError(PRIVATE_TEXT)),
            ("_family_growth_payload", OverflowError(PRIVATE_TEXT)),
            ("verified_intelligence.ppf_reference", RuntimeError(PRIVATE_TEXT)),
            ("resolve_canonical_financial_baseline", ValidationError(PRIVATE_TEXT)),
        ):
            with self.subTest(target=target, exception=type(exception).__name__):
                cache.clear()
                with patch("apps.family.views." + target, side_effect=exception):
                    self.assert_safe_failure(self.client.get("/api/family/growth/"))

    def test_logs_keep_structured_error_reference_without_exception_body_or_chain(self):
        def fail(*args):
            try:
                raise DatabaseError(PRIVATE_TEXT)
            except DatabaseError as exc:
                raise RuntimeError(PRIVATE_TEXT) from exc
        with patch("apps.family.views.resolve_canonical_financial_baseline", side_effect=fail), self.assertLogs(
            level="ERROR") as captured:
            responses = [self.client.get("/api/family/growth/", {"token": PRIVATE_TEXT}) for _ in range(2)]
        records = [record for record in captured.records if record.name == "apps.family.views"]
        self.assertEqual(len(records), 2)
        for record in captured.records:
            self.assertIsNone(record.exc_info)
            self.assertIsNone(record.stack_info)
            for marker in PRIVATE_MARKERS:
                self.assertNotIn(marker, record.getMessage())
        for response, record in zip(responses, records):
            self.assert_safe_failure(response)
            self.assertEqual(record.error_id, response.json()["error_id"])
            self.assertEqual(record.exception_type, "RuntimeError")
            self.assertEqual(record.args, (record.error_id, "RuntimeError"))
            self.assertIn(record.error_id, record.getMessage())
            self.assertEqual(record.levelname, "ERROR")
            self.assertIsNone(record.exc_info)
            self.assertIsNone(record.stack_info)
            for marker in PRIVATE_MARKERS:
                self.assertNotIn(marker, record.getMessage())
                self.assertNotIn(marker, repr(record.args))
        self.assertNotEqual(responses[0].json()["error_id"], responses[1].json()["error_id"])

    def test_exception_string_is_never_evaluated_for_response_or_logging(self):
        class UnprintableError(Exception):
            def __str__(self):
                raise AssertionError("Exception text must not be read")
        with patch("apps.family.views.resolve_canonical_financial_baseline", side_effect=UnprintableError()):
            self.assert_safe_failure(self.client.get("/api/family/growth/"))

    def test_anonymous_and_basic_auth_requests_never_execute_private_service(self):
        basic = "Basic " + base64.b64encode(b"family_error_user:Orbit-X8!Lantern").decode("ascii")
        for headers in ({}, {"HTTP_AUTHORIZATION": basic}):
            response = Client().get("/api/family/growth/", **headers)
            self.assertEqual(response.status_code, 403)
            self.assert_private_text_absent(response)
        self.resolve.assert_not_called()

    def test_malformed_requests_and_controlled_validation_keep_expected_statuses(self):
        response = self.client.post("/api/family/growth/", '{"private": "synthetic-token"', content_type="application/json")
        self.assertEqual(response.status_code, 405)
        self.resolve.assert_not_called()
        response = self.client.patch("/api/family/account-links/999/financial-sharing/",
            '{"share_financial_summary": synthetic-token', content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assert_private_text_absent(response)
        response = self.client.post("/api/family/", json.dumps({"name": "", "age": -1, "relation": "Child"}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("age", response.json())
        self.assertNotIn("error_id", response.json())
        response = self.client.post("/api/family/account-links/accept/", json.dumps({"invite_code": ""}), content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Enter a complete family link code."})

    def test_query_parameters_cannot_select_another_familys_financial_scope(self):
        other = get_user_model().objects.create_user(username="SyntheticFamilyIdentity", monthly_income=123456.78)
        relative = get_user_model().objects.create_user(username="other_family_relative")
        link = FamilyAccountLink.objects.create(created_by=other, linked_user=relative, status="accepted",
            invite_code_hash="a" * 64, expires_at=timezone.now() + timedelta(days=1),
            share_financial_summary=True, linked_user_share_financial_summary=True)
        response = self.client.get("/api/family/growth/", {"user_id": other.pk, "family_link_id": link.pk})
        self.assertEqual(response.status_code, 200)
        self.assert_private_text_absent(response)
        self.assertEqual({row["user_id"] for row in response.json()["family_financial_members"]}, {self.user.pk})
        self.assertEqual({call.args[0].pk for call in self.resolve.call_args_list}, {self.user.pk})

    def test_normal_success_preserves_financial_summary_and_projection_contract(self):
        response = self.client.get("/api/family/growth/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["own_financial_baseline"], self.baseline)
        self.assertEqual(payload["current_net_worth"], 90000)
        self.assertEqual(len(payload["projections"]), 10)
        self.assertNotIn("error_id", payload)

    def test_reference_diagnostics_are_excluded_from_all_public_evidence(self):
        evidence = dict(_fresh_evidence("India Post"), notes=PRIVATE_TEXT, last_refresh_error=PRIVATE_TEXT)
        with patch("apps.family.views.verified_intelligence.ppf_reference", return_value=SimpleNamespace(evidence=evidence)):
            response = self.client.get("/api/family/growth/")
        self.assertEqual(response.status_code, 200)
        self.assert_private_text_absent(response)
        public = response.json()["grounding"]["evidence"][0]
        self.assertEqual(public["source_name"], "India Post")
        self.assertEqual(public["status"], "fresh")
        self.assertNotIn("notes", public)
        self.assertNotIn("last_refresh_error", public)
        self.assertEqual(evidence["last_refresh_error"], PRIVATE_TEXT)

    def test_legacy_cached_payload_with_internal_diagnostics_is_not_reused(self):
        legacy_revision = _family_growth_revision(self.user, self.baseline).removeprefix("family-growth-safe-errors-v1|")
        materialize_payload(namespace="family-growth", user_id=self.user.pk, revision=legacy_revision,
                            ttl_seconds=60, builder=lambda: {"internal_diagnostics": PRIVATE_TEXT})
        response = self.client.get("/api/family/growth/")
        self.assertEqual(response.status_code, 200)
        self.assert_private_text_absent(response)
        self.assertEqual(response.json()["current_net_worth"], 90000)
