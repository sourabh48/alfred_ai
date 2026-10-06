import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.utils import timezone

from apps.family.models import Dependent, FamilyAccountLink
from apps.family.services import create_family_link_invite, family_financial_user_ids, hash_family_link_code


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
        self.assertNotContains(response, 'id="settingsDependentForm"')
        self.assertContains(response, 'id="settingsAcceptInviteForm"')
        self.assertNotContains(response, "Manual Dependents")
        self.assertContains(response, "Connected Members")
        self.assertContains(response, 'id="settingsLinkedAccountsList"')
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
        self.assertEqual(payload["family_financial_user_count"], 1)
        self.assertEqual(payload["shared_dependent_count"], 1)
        self.assertFalse(payload["links"][0]["share_financial_summary"])
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
        link = FamilyAccountLink.objects.get()
        self.assertEqual(self._consent(self.member_client, link, True).status_code, 200)

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

    def _connect(self, creator=None, member_client=None):
        link, code = create_family_link_invite(creator or self.owner)
        response = (member_client or self.member_client).post(
            "/api/family/account-links/accept/", json.dumps({"invite_code": code}),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        link.refresh_from_db()
        return link

    def _consent(self, client, link, enabled):
        return client.patch(f"/api/family/account-links/{link.pk}/financial-sharing/",
                            json.dumps({"share_financial_summary": enabled}), content_type="application/json")

    def _growth(self, client):
        def baseline_for(user):
            return {"total_assets": user.id * 1000, "total_liabilities": 100,
                    "net_worth": user.id * 1000 - 100, "monthly_income": user.monthly_income,
                    "savings_capacity": user.id * 100}
        with patch("apps.family.views.resolve_canonical_financial_baseline", side_effect=baseline_for) as baseline, patch(
            "apps.family.views.verified_intelligence.ppf_reference",
            return_value=SimpleNamespace(evidence=_fresh_evidence("India Post"))), patch(
            "apps.family.views.verified_intelligence.nps_tax_reference",
            return_value=SimpleNamespace(evidence=_fresh_evidence("NPS Trust"))):
            response = client.get("/api/family/growth/")
        self.assertEqual(response.status_code, 200)
        return response.json(), {call.args[0].pk for call in baseline.call_args_list}

    def test_new_model_and_invite_defaults_do_not_grant_financial_access(self):
        self.assertIs(FamilyAccountLink._meta.get_field("share_financial_summary").default, False)
        response = self.owner_client.post("/api/family/account-links/",
            json.dumps({"share_financial_summary": True, "linked_user_share_financial_summary": True}),
            content_type="application/json")
        self.assertEqual(response.status_code, 201)
        link = FamilyAccountLink.objects.get()
        self.assertFalse(link.share_financial_summary)
        self.assertFalse(link.linked_user_share_financial_summary)
        response = self.member_client.post("/api/family/account-links/accept/",
            json.dumps({"invite_code": response.json()["invite"]["invite_code"], "share_financial_summary": True}),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(family_financial_user_ids(self.member), [self.member.pk])

    def test_absent_consent_filters_aggregate_members_and_nested_profiles(self):
        self._connect()
        for client, user in ((self.owner_client, self.owner), (self.member_client, self.member)):
            payload, resolved = self._growth(client)
            self.assertEqual(resolved, {user.pk})
            self.assertEqual({row["user_id"] for row in payload["family_financial_members"]}, {user.pk})
            self.assertEqual(payload["financial_baseline"]["monthly_income"], user.monthly_income)
            self.assertEqual(payload["grounding"]["history"]["total_assets"], user.pk * 1000)
            snapshot = client.get("/api/family/account-links/").json()
            self.assertNotIn("monthly_income", json.dumps(snapshot))
            self.assertNotIn("total_assets", json.dumps(snapshot))

    def test_each_owner_can_authorize_only_their_own_summary(self):
        link = self._connect()
        response = self._consent(self.owner_client, link, True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["links"][0]["share_financial_summary"])
        self.assertFalse(response.json()["links"][0]["receives_financial_summary"])
        member_snapshot = self.member_client.get("/api/family/account-links/").json()["links"][0]
        self.assertFalse(member_snapshot["share_financial_summary"])
        self.assertTrue(member_snapshot["receives_financial_summary"])
        self.assertEqual(family_financial_user_ids(self.owner), [self.owner.pk])
        payload, _ = self._growth(self.member_client)
        self.assertEqual({row["user_id"] for row in payload["family_financial_members"]}, {self.owner.pk, self.member.pk})
        self.assertEqual(payload["financial_baseline"]["monthly_income"], 205000)
        self.assertEqual(self._consent(self.member_client, link, True).status_code, 200)
        self.assertEqual(set(family_financial_user_ids(self.owner)), {self.owner.pk, self.member.pk})
        link.refresh_from_db()
        self.assertTrue(link.share_financial_summary)
        self.assertTrue(link.linked_user_share_financial_summary)

    def test_consent_revocation_removes_warm_cached_summary_without_disconnect(self):
        link = self._connect()
        self.assertEqual(self._consent(self.owner_client, link, True).status_code, 200)
        before, _ = self._growth(self.member_client)
        cached, _ = self._growth(self.member_client)
        self.assertEqual(before["financial_baseline"]["member_count"], 2)
        self.assertTrue(cached["_materialized"]["cached"])
        self.assertEqual(self._consent(self.owner_client, link, False).status_code, 200)
        after, resolved = self._growth(self.member_client)
        self.assertEqual(resolved, {self.member.pk})
        self.assertEqual(after["financial_baseline"]["member_count"], 1)
        self.assertEqual(after["linked_family_account_count"], 1)
        self.assertFalse(after["_materialized"]["cached"])
        self.assertEqual(self.member_client.get("/api/family/account-links/").json()["family_context_user_count"], 2)

    def test_financial_updates_refresh_recipient_cache_with_dependent_sharing_off(self):
        link = self._connect()
        link.share_dependents = False
        link.save(update_fields=["share_dependents"])
        self.assertEqual(self._consent(self.owner_client, link, True).status_code, 200)
        self._growth(self.member_client)
        cached, _ = self._growth(self.member_client)
        self.assertTrue(cached["_materialized"]["cached"])
        response = self.owner_client.patch("/api/users/profile/", json.dumps({"monthly_income": 135000}),
                                           content_type="application/json")
        self.assertEqual(response.status_code, 200)
        updated, _ = self._growth(self.member_client)
        self.assertEqual(updated["financial_baseline"]["monthly_income"], 220000)
        self.assertFalse(updated["_materialized"]["cached"])

    def test_profile_permission_is_respected_inside_opted_in_financial_summary(self):
        link = self._connect()
        link.share_profile_summary = False
        link.save(update_fields=["share_profile_summary"])
        self.assertEqual(self._consent(self.owner_client, link, True).status_code, 200)
        self.assertIsNone(self.member_client.get("/api/family/account-links/").json()["links"][0]["linked_profile"])
        payload, _ = self._growth(self.member_client)
        summary = next(row for row in payload["family_financial_members"] if row["user_id"] == self.owner.pk)
        self.assertEqual(summary["monthly_income"], 120000)
        for field in ("username", "city", "country"):
            self.assertIsNone(summary[field])
        self.assertEqual(summary["display_name"], "Linked member")

    def test_unrelated_account_cannot_authorize_revoke_or_view_family_finances(self):
        link = self._connect()
        outsider = get_user_model().objects.create_user(username="family_outsider")
        client = Client()
        client.force_login(outsider)
        self.assertEqual(self._consent(client, link, True).status_code, 404)
        self.assertEqual(client.post(f"/api/family/account-links/{link.pk}/revoke/", {}, content_type="application/json").status_code, 404)
        self.assertEqual(client.get("/api/family/account-links/").json()["links"], [])
        payload, resolved = self._growth(client)
        self.assertEqual(resolved, {outsider.pk})
        self.assertEqual({row["user_id"] for row in payload["family_financial_members"]}, {outsider.pk})

    def test_family_consent_is_not_transitive(self):
        first = self._connect()
        self.assertEqual(self._consent(self.owner_client, first, True).status_code, 200)
        third = get_user_model().objects.create_user(username="third_family")
        client = Client()
        client.force_login(third)
        second = self._connect(self.member, client)
        self.assertEqual(self._consent(self.member_client, second, True).status_code, 200)
        self.assertEqual(set(family_financial_user_ids(third)), {third.pk, self.member.pk})
        self.assertNotIn(self.owner.pk, family_financial_user_ids(third))
        self.assertEqual(self._consent(client, first, True).status_code, 404)

    def test_pending_revoked_expired_and_missing_links_cannot_enable_sharing(self):
        link, _ = create_family_link_invite(self.owner)
        for state in ("pending", "revoked", "expired"):
            with self.subTest(state=state):
                link.status = state
                link.save(update_fields=["status"])
                self.assertEqual(self._consent(self.owner_client, link, True).status_code, 404)
        self.assertEqual(self._consent(self.owner_client, SimpleNamespace(pk=999999), True).status_code, 404)

    def test_consent_rejects_missing_ambiguous_or_foreign_permission_fields(self):
        link = self._connect()
        for data in ({}, {"share_financial_summary": "true"}, {"share_financial_summary": 1},
                     {"share_financial_summary": None}, {"share_financial_summary": True, "linked_user_share_financial_summary": True},
                     {"share_financial_summary": True, "created_by": self.member.pk}):
            with self.subTest(data=data):
                response = self.owner_client.patch(f"/api/family/account-links/{link.pk}/financial-sharing/",
                    json.dumps(data), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                link.refresh_from_db()
                self.assertFalse(link.share_financial_summary)
                self.assertFalse(link.linked_user_share_financial_summary)

    def test_consent_requires_session_and_csrf(self):
        import base64
        from django.conf import settings
        link = self._connect()
        client = Client(enforce_csrf_checks=True)
        basic = "Basic " + base64.b64encode(b"family_owner:Pass12345!").decode("ascii")
        self.assertEqual(client.patch(f"/api/family/account-links/{link.pk}/financial-sharing/",
            json.dumps({"share_financial_summary": True}), content_type="application/json", HTTP_AUTHORIZATION=basic).status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(self._consent(client, link, True).status_code, 403)
        client.get("/settings/")
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        response = client.patch(f"/api/family/account-links/{link.pk}/financial-sharing/",
            json.dumps({"share_financial_summary": True}), content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)

    def test_relationship_revocation_clears_both_financial_grants(self):
        link = self._connect()
        self.assertEqual(self._consent(self.owner_client, link, True).status_code, 200)
        self.assertEqual(self._consent(self.member_client, link, True).status_code, 200)
        response = self.member_client.post(f"/api/family/account-links/{link.pk}/revoke/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        link.refresh_from_db()
        self.assertFalse(link.share_financial_summary)
        self.assertFalse(link.linked_user_share_financial_summary)
        self.assertEqual(family_financial_user_ids(self.member), [self.member.pk])

    def test_admin_cannot_edit_owners_or_grant_financial_consent(self):
        from django.contrib import admin
        from django.test import RequestFactory
        link = self._connect()
        request = RequestFactory().get("/admin/family/familyaccountlink/")
        request.user = self.owner
        request.user.is_superuser = True
        model_admin = admin.site._registry[FamilyAccountLink]
        fields = model_admin.get_form(request, link).base_fields
        for field in ("created_by", "linked_user", "status", "share_financial_summary", "linked_user_share_financial_summary"):
            self.assertNotIn(field, fields)
        self.assertFalse(model_admin.has_add_permission(request))
