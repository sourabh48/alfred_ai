"""Synthetic-account abuse checks for the two independent invitation quotas."""
import base64
import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.family.models import FamilyAccountLink
from apps.family.services import create_family_link_invite, family_financial_user_ids


CREATE = "/api/family/account-links/"
ACCEPT = CREATE + "accept/"
INVALID_CODE = "ALF-AAAA-AAAA"


class FamilyInvitationThrottleTests(TestCase):
    def setUp(self):
        storage = TemporaryDirectory(prefix="alfred-invite-tests-")
        self.addCleanup(storage.cleanup)
        self.storage = Path(storage.name) / "limits"
        config = override_settings(
            ALFRED_FAMILY_INVITE_THROTTLE_DIR=str(self.storage),
            ALFRED_FAMILY_INVITE_CREATE_LIMIT=2, ALFRED_FAMILY_INVITE_CREATE_WINDOW_SECONDS=60,
            ALFRED_FAMILY_INVITE_ACCEPT_LIMIT=2, ALFRED_FAMILY_INVITE_ACCEPT_WINDOW_SECONDS=60,
        )
        config.enable()
        self.addCleanup(config.disable)
        self.now = timezone.now()
        clock = patch("django.utils.timezone.now", side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.owner = get_user_model().objects.create_user(username="invite_owner", password="Orbit-X8!Lantern")
        self.member = get_user_model().objects.create_user(username="invite_member", password="Orbit-X8!Lantern")
        self.owner_client = Client()
        self.owner_client.force_login(self.owner)
        self.member_client = Client()
        self.member_client.force_login(self.member)

    def post(self, client, path, payload=None, **headers):
        return client.post(path, json.dumps(payload or {}), content_type="application/json", **headers)

    def snapshot(self):
        return list(FamilyAccountLink.objects.order_by("id").values())

    def assert_throttled(self, response):
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)
        self.assertEqual(set(response.json()), {"detail"})

    def test_normal_creation_acceptance_keeps_relationship_and_financial_privacy(self):
        invite = self.post(self.owner_client, CREATE)
        self.assertEqual(invite.status_code, 201)
        response = self.post(self.member_client, ACCEPT, {"code": invite.json()["invite"]["invite_code"]})
        self.assertEqual(response.status_code, 200)
        link = FamilyAccountLink.objects.get()
        self.assertEqual((link.created_by_id, link.linked_user_id, link.status),
                         (self.owner.pk, self.member.pk, "accepted"))
        self.assertFalse(link.share_financial_summary)
        self.assertFalse(link.linked_user_share_financial_summary)
        self.assertEqual(family_financial_user_ids(self.member), [self.member.pk])
        consent = self.member_client.patch(CREATE + f"{link.pk}/financial-sharing/",
            json.dumps({"share_financial_summary": True}), content_type="application/json")
        self.assertEqual(consent.status_code, 200)
        self.assertIn(self.member.pk, family_financial_user_ids(self.owner))

    def test_creation_limit_counts_repeated_or_changed_targets_and_spoofed_headers(self):
        for target in ("synthetic-target", "synthetic-target"):
            self.assertEqual(self.post(self.owner_client, CREATE, {"target": target}).status_code, 201)
        before = self.snapshot()
        for target in ("synthetic-target", "another-target"):
            with patch("apps.family.views.create_family_link_invite") as create:
                response = self.post(self.owner_client, CREATE, {"target": target, "user_id": self.member.pk},
                                     HTTP_X_FORWARDED_FOR="203.0.113.24", HTTP_X_USER_ID=str(self.member.pk))
            self.assert_throttled(response)
            create.assert_not_called()
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(set(FamilyAccountLink.objects.values_list("created_by_id", flat=True)), {self.owner.pk})

    def test_acceptance_limit_counts_invalid_attempts_and_does_not_consume_valid_invite(self):
        link, code = create_family_link_invite(self.owner)
        for _ in range(2):
            self.assertEqual(self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE}).status_code, 400)
        before = self.snapshot()
        with patch("apps.family.views.accept_family_link_code") as accept:
            response = self.post(self.member_client, ACCEPT, {"invite_code": code})
        self.assert_throttled(response)
        accept.assert_not_called()
        self.assertEqual(self.snapshot(), before)
        self.now += timedelta(seconds=60)
        self.assertEqual(self.post(self.member_client, ACCEPT, {"invite_code": code}).status_code, 200)
        link.refresh_from_db()
        self.assertEqual(link.linked_user_id, self.member.pk)

    def test_scopes_are_independent_in_both_directions(self):
        for _ in range(2):
            self.assertEqual(self.post(self.owner_client, CREATE).status_code, 201)
            self.assertEqual(self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE}).status_code, 400)
        _, code = create_family_link_invite(self.member)
        self.assertEqual(self.post(self.owner_client, ACCEPT, {"invite_code": code}).status_code, 200)
        self.assertEqual(self.post(self.member_client, CREATE).status_code, 201)
        self.assert_throttled(self.post(self.owner_client, CREATE))
        self.assert_throttled(self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE}))

    def test_accounts_on_same_ip_have_separate_limits_and_headers_cannot_reset_them(self):
        for _ in range(2):
            self.assertEqual(self.post(self.owner_client, CREATE, REMOTE_ADDR="192.0.2.1").status_code, 201)
        self.assert_throttled(self.post(self.owner_client, CREATE, REMOTE_ADDR="192.0.2.2",
                                       HTTP_X_FORWARDED_FOR="198.51.100.99"))
        self.assertEqual(self.post(self.member_client, CREATE, REMOTE_ADDR="192.0.2.1").status_code, 201)

    def test_rolling_window_retry_and_default_cache_clear_cannot_reset_quota(self):
        from django.core.cache import cache
        self.assertEqual(self.post(self.owner_client, CREATE).status_code, 201)
        self.now += timedelta(seconds=30)
        self.assertEqual(self.post(self.owner_client, CREATE).status_code, 201)
        cache.clear()
        response = self.post(self.owner_client, CREATE)
        self.assert_throttled(response)
        self.assertEqual(int(response["Retry-After"]), 30)
        self.now += timedelta(seconds=30)
        self.assertEqual(self.post(self.owner_client, CREATE).status_code, 201)
        self.assert_throttled(self.post(self.owner_client, CREATE))

    def test_valid_replay_expired_revoked_missing_and_self_codes_cannot_enumerate_state(self):
        with override_settings(ALFRED_FAMILY_INVITE_ACCEPT_LIMIT=20):
            link, code = create_family_link_invite(self.owner)
            self.assertEqual(self.post(self.member_client, ACCEPT, {"invite_code": code}).status_code, 200)
            accepted = self.snapshot()
            replay = self.post(self.member_client, ACCEPT, {"invite_code": code})
            self.assertEqual(self.snapshot(), accepted)
            expired, expired_code = create_family_link_invite(self.owner)
            expired.expires_at = self.now - timedelta(seconds=1)
            expired.save(update_fields=["expires_at"])
            revoked, revoked_code = create_family_link_invite(self.owner)
            revoked.status = "revoked"
            revoked.save(update_fields=["status"])
            _, own_code = create_family_link_invite(self.member)
            responses = [replay] + [self.post(self.member_client, ACCEPT, {"invite_code": value})
                                    for value in (expired_code, revoked_code, INVALID_CODE, own_code)]
            self.assertTrue(all(response.status_code == 400 for response in responses))
            self.assertTrue(all(response.json() == replay.json() for response in responses))
            expired.refresh_from_db()
            revoked.refresh_from_db()
            self.assertEqual(expired.status, "expired")
            self.assertEqual(revoked.status, "revoked")

    def test_authentication_and_csrf_fail_before_consuming_quota(self):
        secure_client = Client(enforce_csrf_checks=True)
        basic = "Basic " + base64.b64encode(b"invite_owner:Orbit-X8!Lantern").decode()
        for path in (CREATE, ACCEPT):
            self.assertEqual(self.post(secure_client, path, HTTP_AUTHORIZATION=basic).status_code, 403)
        secure_client.get("/login/")
        token = secure_client.cookies[settings.CSRF_COOKIE_NAME].value
        secure_client.force_login(self.owner)
        for path in (CREATE, ACCEPT):
            self.assertEqual(self.post(secure_client, path).status_code, 403)
        self.assertFalse(self.storage.exists())
        for _ in range(2):
            self.assertEqual(self.post(secure_client, CREATE, HTTP_X_CSRFTOKEN=token).status_code, 201)
        self.assert_throttled(self.post(secure_client, CREATE, HTTP_X_CSRFTOKEN=token))

    def test_exhausted_limits_do_not_block_reads_consent_revocation_or_other_apis(self):
        link, code = create_family_link_invite(self.owner)
        self.assertEqual(self.post(self.member_client, ACCEPT, {"invite_code": code}).status_code, 200)
        self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE})
        for _ in range(2):
            self.post(self.member_client, CREATE)
        self.assert_throttled(self.post(self.member_client, CREATE))
        self.assert_throttled(self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE}))
        for _ in range(3):
            self.assertEqual(self.member_client.get(CREATE).status_code, 200)
        self.assertEqual(self.member_client.get("/api/users/profile/").status_code, 200)
        consent_path = CREATE + f"{link.pk}/financial-sharing/"
        self.assertEqual(self.member_client.patch(consent_path, json.dumps({"share_financial_summary": True}),
                                                  content_type="application/json").status_code, 200)
        self.assertEqual(self.post(self.member_client, CREATE + f"{link.pk}/revoke/").status_code, 200)
        link.refresh_from_db()
        self.assertEqual(link.status, "revoked")
        self.assertFalse(link.linked_user_share_financial_summary)

    def test_429_responses_and_logs_do_not_echo_tokens_payloads_or_identities(self):
        for _ in range(2):
            self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE})
        marker = "SyntheticFamilyIdentity-Bearer-private-123456.78"
        with self.assertLogs(level="WARNING") as captured:
            response = self.post(self.member_client, ACCEPT, {"invite_code": marker, "finance": marker},
                                 QUERY_STRING="invite_code=" + marker)
        self.assert_throttled(response)
        self.assertNotIn(marker, response.content.decode())
        self.assertNotIn(marker, " ".join(record.getMessage() for record in captured.records))
        self.assertTrue(all(record.exc_info is None for record in captured.records))

    def test_malformed_acceptance_counts_attempts_without_internal_failures(self):
        for payload in ([], {"invite_code": {"private": "synthetic-token"}}):
            response = self.member_client.post(ACCEPT, json.dumps(payload), content_type="application/json")
            self.assertEqual(response.status_code, 400)
            self.assertNotIn("synthetic-token", response.content.decode())
        self.assert_throttled(self.post(self.member_client, ACCEPT, {"invite_code": INVALID_CODE}))

    def test_storage_failures_are_safe_and_fail_closed_without_invitation_writes(self):
        marker = "SyntheticFamilyIdentity-123456.78-Bearer-private-F:\\secret\\cache"
        for path in (CREATE, ACCEPT):
            with patch("apps.family.throttles.Cache", side_effect=OSError(marker)), self.assertLogs(level="ERROR") as logs:
                response = self.post(self.member_client, path, {"invite_code": marker})
            self.assertEqual(response.status_code, 503)
            self.assertIn("error_id", response.json())
            self.assertNotIn(marker, response.content.decode())
            self.assertNotIn(marker, " ".join(record.getMessage() for record in logs.records))
            self.assertTrue(all(record.exc_info is None for record in logs.records))
            self.assertFalse(FamilyAccountLink.objects.exists())

    def test_nonpositive_configuration_cannot_disable_protection(self):
        for config in ({"ALFRED_FAMILY_INVITE_CREATE_LIMIT": 0},
                       {"ALFRED_FAMILY_INVITE_CREATE_WINDOW_SECONDS": -1}):
            with override_settings(**config):
                response = self.post(self.owner_client, CREATE)
            self.assertEqual(response.status_code, 503)
            self.assertFalse(FamilyAccountLink.objects.exists())

    def test_unexpected_invitation_service_failures_use_class_only_logs(self):
        marker = "SyntheticFamilyIdentity-finance-token-123456.78"
        for target, path in (("create_family_link_invite", CREATE), ("accept_family_link_code", ACCEPT)):
            with patch("apps.family.views." + target, side_effect=RuntimeError(marker)), self.assertLogs(level="ERROR") as logs:
                response = self.post(self.owner_client, path, {"invite_code": marker})
            self.assertEqual(response.status_code, 500)
            self.assertNotIn(marker, response.content.decode())
            self.assertNotIn(marker, " ".join(record.getMessage() for record in logs.records))
            self.assertTrue(all(record.exc_info is None for record in logs.records))
            self.assertFalse(FamilyAccountLink.objects.exists())
