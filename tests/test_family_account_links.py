import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.family.models import Dependent, FamilyAccountLink
from apps.family.services import create_family_link_invite, hash_family_link_code


def _fresh_evidence(source_name: str) -> dict:
    return {
        "source_name": source_name,
        "source_url": f"https://example.com/{source_name.lower().replace(' ', '-')}",
        "status": "fresh",
        "stale_after": (timezone.now() + timedelta(days=7)).isoformat(),
        "scheduled_refresh": "refresh_due_records",
        "circuit_breaker": {"state": "closed"},
        "stale_fallback": {"available": True},
    }


class FamilyAccountLinkTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="family_owner",
            password="Pass12345!",
            first_name="Family",
            last_name="Owner",
            city="Bengaluru",
            country="India",
            monthly_income=120000,
        )
        self.member = user_model.objects.create_user(
            username="family_member",
            password="Pass12345!",
            first_name="Family",
            last_name="Member",
            city="Pune",
            country="India",
            monthly_income=85000,
        )
        self.owner_client = Client()
        self.owner_client.force_login(self.owner)
        self.member_client = Client()
        self.member_client.force_login(self.member)

    def tearDown(self):
        cache.clear()

    def test_settings_page_renders_profile_family_and_link_contract(self):
        response = self.owner_client.get("/settings/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="accountSettingsRoot"')
        self.assertContains(response, 'id="accountProfileForm"')
        self.assertContains(response, 'id="settingsDependentForm"')
        self.assertContains(response, 'id="settingsAcceptInviteForm"')
        self.assertContains(response, "Manual Dependents")
        self.assertContains(response, "Linked spouse/family data is populated from linked accounts above.")
        self.assertContains(response, "/static/js/settings.js")

    def test_family_link_code_is_one_time_output_and_hash_stored(self):
        response = self.owner_client.post(
            "/api/family/account-links/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        code = payload["invite"]["invite_code"]
        link = FamilyAccountLink.objects.get()

        self.assertEqual(payload["invite"]["stored_as"], "sha256_hmac")
        self.assertEqual(link.status, FamilyAccountLink.STATUS_PENDING)
        self.assertEqual(link.invite_code_hash, hash_family_link_code(code))
        self.assertNotEqual(link.invite_code_hash, code)
        self.assertNotIn(code, json.dumps(payload["links"]))

    def test_second_user_accepts_link_and_gets_safe_profile_summary(self):
        invite_response = self.owner_client.post(
            "/api/family/account-links/",
            data=json.dumps({}),
            content_type="application/json",
        )
        code = invite_response.json()["invite"]["invite_code"]
        Dependent.objects.create(user=self.owner, name="Owner Child", age=7, relation="Child")

        response = self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": code}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        link = FamilyAccountLink.objects.get()
        self.assertEqual(link.status, FamilyAccountLink.STATUS_ACCEPTED)
        self.assertEqual(link.linked_user, self.member)
        payload = response.json()
        self.assertEqual(payload["accepted_link_count"], 1)
        self.assertEqual(payload["linked_user_count"], 1)
        self.assertEqual(payload["family_financial_user_count"], 2)
        self.assertEqual(payload["shared_dependent_count"], 1)
        self.assertTrue(payload["links"][0]["share_financial_summary"])
        self.assertEqual(payload["links"][0]["linked_profile"]["username"], "family_owner")
        self.assertNotIn("monthly_income", payload["links"][0]["linked_profile"])

    def test_family_link_blocks_self_accept_expired_code_and_duplicates(self):
        link, code = create_family_link_invite(self.owner)

        self_response = self.owner_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": code}),
            content_type="application/json",
        )
        self.assertEqual(self_response.status_code, 400)
        self.assertIn("different signed-in user", self_response.json()["detail"])

        link.expires_at = timezone.now() - timedelta(minutes=1)
        link.save(update_fields=["expires_at", "updated_at"])
        expired_response = self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": code}),
            content_type="application/json",
        )
        self.assertEqual(expired_response.status_code, 400)
        link.refresh_from_db()
        self.assertEqual(link.status, FamilyAccountLink.STATUS_EXPIRED)

        second_link, second_code = create_family_link_invite(self.owner)
        accept_response = self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": second_code}),
            content_type="application/json",
        )
        self.assertEqual(accept_response.status_code, 200)
        third_link, third_code = create_family_link_invite(self.owner)
        duplicate_response = self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": third_code}),
            content_type="application/json",
        )
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertIn("already linked", duplicate_response.json()["detail"])
        second_link.refresh_from_db()
        third_link.refresh_from_db()
        self.assertEqual(second_link.status, FamilyAccountLink.STATUS_ACCEPTED)
        self.assertEqual(third_link.status, FamilyAccountLink.STATUS_PENDING)

    def test_family_link_revoke_removes_shared_context(self):
        invite_response = self.owner_client.post(
            "/api/family/account-links/",
            data=json.dumps({}),
            content_type="application/json",
        )
        code = invite_response.json()["invite"]["invite_code"]
        accept_response = self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": code}),
            content_type="application/json",
        )
        link_id = accept_response.json()["links"][0]["id"]

        response = self.member_client.post(
            f"/api/family/account-links/{link_id}/revoke/",
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["accepted_link_count"], 0)
        self.assertEqual(response.json()["family_context_user_count"], 1)
        link = FamilyAccountLink.objects.get(id=link_id)
        self.assertEqual(link.status, FamilyAccountLink.STATUS_REVOKED)

    def test_family_growth_uses_linked_dependents_and_accepted_financial_summary(self):
        Dependent.objects.create(user=self.owner, name="Owner Child", age=7, relation="Child")
        Dependent.objects.create(user=self.member, name="Member Parent", age=67, relation="Parent")
        invite_response = self.owner_client.post(
            "/api/family/account-links/",
            data=json.dumps({}),
            content_type="application/json",
        )
        code = invite_response.json()["invite"]["invite_code"]
        self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": code}),
            content_type="application/json",
        )

        owner_baseline = {
            "total_assets": 500000,
            "total_liabilities": 100000,
            "net_worth": 400000,
            "savings_capacity": 25000,
            "monthly_income": 120000,
        }
        member_baseline = {
            "total_assets": 250000,
            "total_liabilities": 100000,
            "net_worth": 150000,
            "savings_capacity": 15000,
            "monthly_income": 85000,
        }
        def baseline_for(user):
            return owner_baseline if user.id == self.owner.id else member_baseline

        with patch("apps.family.views.resolve_canonical_financial_baseline", side_effect=baseline_for), patch(
            "apps.family.views.verified_intelligence.ppf_reference",
            return_value=SimpleNamespace(evidence=_fresh_evidence("India Post")),
        ), patch(
            "apps.family.views.verified_intelligence.nps_tax_reference",
            return_value=SimpleNamespace(evidence=_fresh_evidence("NPS Trust")),
        ):
            response = self.owner_client.get("/api/family/growth/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["dependents_count"], 2)
        self.assertEqual(payload["own_dependents_count"], 1)
        self.assertEqual(payload["linked_family_account_count"], 1)
        self.assertEqual(payload["linked_family_dependent_count"], 1)
        self.assertEqual(payload["linked_family_financial_account_count"], 1)
        self.assertEqual(payload["financial_baseline"]["scope"], "accepted_family_financial_summary")
        self.assertEqual(payload["financial_baseline"]["member_count"], 2)
        self.assertEqual(payload["financial_baseline"]["total_assets"], 750000.0)
        self.assertEqual(payload["financial_baseline"]["total_liabilities"], 200000.0)
        self.assertEqual(payload["financial_baseline"]["net_worth"], 550000.0)
        self.assertEqual(payload["financial_baseline"]["savings_capacity"], 40000.0)
        self.assertEqual(payload["financial_baseline"]["monthly_income"], 205000.0)
        self.assertEqual(payload["own_financial_baseline"], owner_baseline)
        self.assertEqual(payload["shared_family_context"]["financial_baseline_scope"], "accepted_family_financial_summary")
        self.assertEqual(payload["shared_family_context"]["financial_member_count"], 2)
        self.assertEqual(len(payload["family_financial_members"]), 2)
        self.assertEqual({item["role"] for item in payload["family_financial_members"]}, {"self", "linked"})

    def test_family_growth_respects_financial_summary_sharing_flag(self):
        invite_response = self.owner_client.post(
            "/api/family/account-links/",
            data=json.dumps({}),
            content_type="application/json",
        )
        code = invite_response.json()["invite"]["invite_code"]
        self.member_client.post(
            "/api/family/account-links/accept/",
            data=json.dumps({"invite_code": code}),
            content_type="application/json",
        )
        link = FamilyAccountLink.objects.get()
        link.share_financial_summary = False
        link.save(update_fields=["share_financial_summary", "updated_at"])

        owner_baseline = {
            "total_assets": 500000,
            "total_liabilities": 100000,
            "net_worth": 400000,
            "savings_capacity": 25000,
            "monthly_income": 120000,
        }
        member_baseline = {
            "total_assets": 250000,
            "total_liabilities": 100000,
            "net_worth": 150000,
            "savings_capacity": 15000,
            "monthly_income": 85000,
        }

        def baseline_for(user):
            return owner_baseline if user.id == self.owner.id else member_baseline

        with patch("apps.family.views.resolve_canonical_financial_baseline", side_effect=baseline_for), patch(
            "apps.family.views.verified_intelligence.ppf_reference",
            return_value=SimpleNamespace(evidence=_fresh_evidence("India Post")),
        ), patch(
            "apps.family.views.verified_intelligence.nps_tax_reference",
            return_value=SimpleNamespace(evidence=_fresh_evidence("NPS Trust")),
        ):
            response = self.owner_client.get("/api/family/growth/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["financial_baseline"]["member_count"], 1)
        self.assertEqual(payload["financial_baseline"]["net_worth"], 400000.0)
        self.assertEqual(payload["linked_family_financial_account_count"], 0)
