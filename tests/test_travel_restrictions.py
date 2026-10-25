"""Local synthetic manual references; no road-rule or live-source authenticity claims."""
from copy import deepcopy
from datetime import timedelta, timezone as datetime_timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.mobility.models import TravelResearchEvidence, TravelResearchSession
from apps.mobility.services.travel.restrictions import record_restriction, restriction_context
from apps.mobility.services.travel_conversation import new_session
from apps.mobility.services.travel_discovery import candidates_for, fact
from apps.mobility.services.travel_itinerary import build_itinerary
from tests.test_travel_route_choices import route_fixture


class TravelRestrictionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("restriction-owner", city="Bengaluru")
        self.session = new_session(self.user)
        self.session.state.update({k: fact(v) for k, v in {"origin": "Bengaluru", "transport_mode": "ride", "trip_duration": 3,
            "available_start_date": (timezone.localdate()+timedelta(days=2)).isoformat(),
            "available_end_date": (timezone.localdate()+timedelta(days=4)).isoformat()}.items()})
        self.candidate = candidates_for(self.user, self.session.state)[0]
        self.candidate["route_result"] = route_fixture().as_dict()
        self.route_id = self.candidate["route_result"]["payload"]["routes"][0]["route_id"]
        self.session.candidates = [self.candidate]
        self.session.save()
        self.run = TravelResearchSession.objects.create(session=self.session, status="ready")
        self.now = timezone.now()
        self.data = {"candidate_index": 0, "route_id": self.route_id, "restriction": "PROHIBITED", "road": "Synthetic road",
            "quote": "Synthetic fixture only: motorcycles are prohibited on this road.",
            "source_url": "https://morth.nic.in/synthetic-fixture-not-a-real-notice", "reviewed": True,
            "checked_at": (self.now-timedelta(minutes=5)).isoformat(), "expires_at": (self.now+timedelta(hours=1)).isoformat()}
        self.client.force_login(self.user)
        self.url = f"/api/mobility/planner/sessions/{self.session.pk}/"

    def context(self, session=None):
        session = session or self.session
        payload = restriction_context(session, {"candidates": deepcopy(session.candidates)})
        return payload["candidates"][0]["motorcycle_restrictions"][self.route_id]

    def test_unknown_without_reference_and_verified_review_is_never_legal_clearance(self):
        self.assertEqual(self.context()["status"], "UNKNOWN")
        row = record_restriction(self.session, self.data)
        result = self.context()
        self.assertEqual((result["status"], result["restriction"]), ("VERIFIED", "PROHIBITED"))
        self.assertEqual(result["motorcycle_legal"], "UNKNOWN")
        self.assertFalse(result["independent_authentication"])
        self.assertEqual(result["evidence"][0]["id"], row.pk)
        self.assertEqual(result["evidence"][0]["source_url"], self.data["source_url"])
        self.assertIn("not independent", result["note"])
        self.assertEqual(record_restriction(self.session, self.data).pk, row.pk)
        second = self.candidate["route_result"]["payload"]["routes"][1]["route_id"]
        result = restriction_context(self.session, {"candidates": deepcopy(self.session.candidates)})
        self.assertEqual(result["candidates"][0]["motorcycle_restrictions"][second]["status"], "UNKNOWN")

    def test_expired_reference_becomes_stale_and_cannot_be_created_or_used(self):
        record_restriction(self.session, self.data)
        with patch("apps.mobility.services.travel.restrictions.timezone", SimpleNamespace(now=lambda: self.now+timedelta(hours=2), is_aware=timezone.is_aware)):
            self.assertEqual(self.context()["status"], "STALE")
            self.assertIsNone(self.context()["restriction"])
            with self.assertRaises(ValidationError): record_restriction(self.session, self.data)

    def test_local_timezone_reference_survives_database_utc_roundtrip(self):
        local_zone = datetime_timezone(timedelta(hours=5, minutes=30))
        data = self.data | {"checked_at": (self.now-timedelta(minutes=5)).astimezone(local_zone).isoformat(),
            "expires_at": (self.now+timedelta(hours=1)).astimezone(local_zone).isoformat()}
        record_restriction(self.session, data)
        self.assertEqual(self.context()["status"], "VERIFIED")

    def test_changed_route_inputs_dates_or_vehicle_never_reuses_verified_reference(self):
        record_restriction(self.session, self.data)
        for key, value in (("origin", "Different city"), ("available_start_date", "2027-01-01"), ("avoid_expressways", True), ("transport_mode", "roadtrip")):
            before = deepcopy(self.session.state)
            self.session.state[key] = fact(value)
            self.assertEqual(self.context()["status"], "UNKNOWN", key)
            self.session.state = before
        self.session.candidates[0]["route_result"] = route_fixture(distance=81).as_dict()
        result = restriction_context(self.session, {"candidates": deepcopy(self.session.candidates)})
        self.assertTrue(all(r["status"] == "UNKNOWN" for r in result["candidates"][0]["motorcycle_restrictions"].values()))

    def test_unavailable_or_expired_car_routing_never_proves_motorcycle_legality(self):
        record_restriction(self.session, self.data)
        original = deepcopy(self.candidate["route_result"])
        for field, value in (("success", False), ("stale", True), ("expires_at", (self.now-timedelta(seconds=1)).isoformat()),
                ("retrieved_at", (self.now+timedelta(hours=1)).isoformat()), ("source_url", "")):
            self.candidate["route_result"] = deepcopy(original)
            self.candidate["route_result"][field] = value
            self.assertEqual(self.context()["status"], "UNAVAILABLE")
            with self.assertRaises(ValidationError): record_restriction(self.session, self.data)

    def test_missing_route_identity_is_explicitly_unavailable_and_other_sessions_cannot_reuse_review(self):
        record_restriction(self.session, self.data)
        same_owner = new_session(self.user)
        same_owner.state, same_owner.candidates = deepcopy(self.session.state), deepcopy(self.session.candidates)
        self.assertEqual(self.context(same_owner)["status"], "UNKNOWN")
        for routes in ([], [{"profile": "driving-car", "motorcycle_legal": "UNKNOWN"}]):
            candidate = deepcopy(self.candidate)
            candidate["route_result"]["payload"]["routes"] = routes
            result = restriction_context(self.session, {"candidates": [candidate]})["candidates"][0]
            self.assertEqual(result["motorcycle_restriction_status"], "UNAVAILABLE")
            self.assertEqual(result["motorcycle_restrictions"], {})

    def test_unsupported_sources_fields_claims_times_and_unreviewed_inputs_are_rejected(self):
        for data in (self.data | {"restriction": "ALLOWED"}, self.data | {"reviewed": "true"}, self.data | {"reviewed": False},
                self.data | {"motorcycle_legal": True}, self.data | {"candidate_index": True}, self.data | {"route_id": "f"*64},
                self.data | {"road": ""}, self.data | {"quote": "x"*1201}, self.data | {"expires_at": (self.now+timedelta(days=2)).isoformat()},
                self.data | {"checked_at": (self.now+timedelta(minutes=2)).isoformat()}, self.data | {"checked_at": "2026-10-25T10:00:00"},
                self.data | {"source_url": "https://morth.nic.in.evil.example/notice"}, self.data | {"source_url": "http://morth.nic.in/notice"},
                self.data | {"source_url": "https://secret@morth.nic.in/notice"}, self.data | {"source_url": "https://127.0.0.1/notice"}):
            with self.subTest(data=data), self.assertRaises(ValidationError): record_restriction(self.session, data)

    def test_corrupt_or_foreign_references_are_not_promoted(self):
        row = record_restriction(self.session, self.data)
        row.finding["quote"] = "Changed without a matching receipt"
        row.save()
        self.assertEqual(self.context()["status"], "UNKNOWN")
        row.finding["quote"] = self.data["quote"]
        row.save()
        other = get_user_model().objects.create_user("restriction-other")
        session = new_session(other)
        session.state, session.candidates = deepcopy(self.session.state), deepcopy(self.session.candidates)
        self.assertEqual(self.context(session)["status"], "UNKNOWN")

    def test_conflicting_reviews_abstain_and_withdrawn_reference_does_not_override(self):
        first = record_restriction(self.session, self.data)
        record_restriction(self.session, self.data | {"restriction": "CONDITIONAL", "quote": "Synthetic fixture: motorcycles require a time-limited permit."})
        self.assertEqual(self.context()["status"], "UNKNOWN")
        self.assertTrue(self.context()["conflicting"])
        first.status = "withdrawn"; first.save()
        self.assertEqual(self.context()["restriction"], "CONDITIONAL")

    def test_read_only_projection_ages_independently_of_saved_itinerary(self):
        record_restriction(self.session, self.data)
        original = deepcopy(self.session.candidates)
        itinerary = build_itinerary(self.session.state, self.candidate)
        result = restriction_context(self.session, {"itinerary": itinerary})
        self.assertEqual(result["itinerary"]["motorcycle_restrictions"][self.route_id]["status"], "VERIFIED")
        self.assertEqual(self.session.candidates, original)

    def test_retention_is_bounded_without_deleting_existing_evidence(self):
        row = record_restriction(self.session, self.data)
        for i in range(19):
            record_restriction(self.session, self.data | {"road": f"Synthetic road {i}"})
        with self.assertRaises(Throttled): record_restriction(self.session, self.data | {"road": "Excess reference"})
        self.assertEqual(self.run.evidence.count(), 20)
        self.assertTrue(self.run.evidence.filter(pk=row.pk).exists())

    def review(self, **extra):
        return self.client.post(self.url, {"action": "restriction_review", "revision": self.session.revision, **self.data, **extra}, content_type="application/json")

    def test_api_review_revision_withdrawal_and_read_time_expiry(self):
        before_candidates = deepcopy(self.session.candidates)
        response = self.review()
        self.assertEqual(response.status_code, 200, response.content)
        proof = response.json()["candidates"][0]["motorcycle_restrictions"][self.route_id]
        self.assertEqual(proof["status"], "VERIFIED")
        self.assertEqual(self.review().status_code, 409)
        self.session.refresh_from_db()
        self.assertEqual(self.session.candidates, before_candidates)
        with patch("apps.mobility.services.travel.restrictions.timezone", SimpleNamespace(now=lambda: self.now+timedelta(hours=2), is_aware=timezone.is_aware)):
            expired = self.client.get(self.url).json()["candidates"][0]["motorcycle_restrictions"][self.route_id]
            self.assertEqual(expired["status"], "STALE")
            self.assertIsNone(expired["restriction"])
        response = self.client.post(self.url, {"action": "restriction_withdraw", "revision": self.session.revision,
            "evidence_id": proof["evidence"][0]["id"]}, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["candidates"][0]["motorcycle_restrictions"][self.route_id]["status"], "UNKNOWN")
        self.assertEqual(self.run.evidence.count(), 1)
        self.assertEqual(self.run.evidence.get().finding["quote"], self.data["quote"])

    def test_api_ownership_csrf_and_unsupported_claims(self):
        self.assertEqual(self.review(reviewer_id=self.user.pk).status_code, 400)
        self.assertEqual(self.review(restriction="ALLOWED").status_code, 400)
        self.assertEqual(self.review(expires_at=(self.now-timedelta(seconds=1)).isoformat()).status_code, 400)
        self.assertFalse(self.run.evidence.exists())
        owner_row = record_restriction(self.session, self.data)
        other = get_user_model().objects.create_user("other-api-owner")
        other_session = new_session(other)
        self.client.force_login(other)
        self.assertEqual(self.review().status_code, 404)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        target = f"/api/mobility/planner/sessions/{other_session.pk}/"
        response = self.client.post(target, {"action": "restriction_withdraw", "revision": other_session.revision,
            "evidence_id": owner_row.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 404)
        owner_row.refresh_from_db(); self.assertEqual(owner_row.status, "owner_reviewed")
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url, {"action": "restriction_review"}, content_type="application/json").status_code, 403)
        self.client.logout(); self.assertIn(self.client.get(self.url).status_code, (401, 403))

    def test_source_correction_requires_review_and_foreign_row_binding_is_ignored(self):
        row = record_restriction(self.session, self.data)
        row.source_url = "https://morth.nic.in/changed-reference"; row.save()
        self.assertEqual(self.context()["status"], "UNKNOWN")
        record_restriction(self.session, self.data | {"source_url": row.source_url, "quote": "Corrected synthetic public prohibition reference."})
        self.assertEqual(self.context()["status"], "VERIFIED")
        other = get_user_model().objects.create_user("foreign-row-owner")
        other_run = TravelResearchSession.objects.create(session=new_session(other), status="ready")
        TravelResearchEvidence.objects.filter(research=self.run).update(research=other_run)
        self.assertEqual(self.context()["status"], "UNKNOWN")
