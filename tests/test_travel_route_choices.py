"""Synthetic route comparison and owner-confirmed draft selection; no provider access."""
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.mobility.models import TravelResearchEvidence
from apps.mobility.services.travel.providers.base import ProviderError, ProviderResult
from apps.mobility.services.travel.providers.routing import GoogleRoutes
from apps.mobility.services.travel.research import enrich_candidate
from apps.mobility.services.travel.mapping import map_features
from apps.mobility.services.travel_conversation import new_session, save_plan
from apps.mobility.services.travel_discovery import budget_for, candidates_for, fact
from apps.mobility.services.travel_itinerary import build_itinerary


def route_fixture(*, distance=80):
    now = timezone.now()
    parameters = {"start": [77.59, 12.97], "end": [77.03, 12.18], "mode": "ride"}
    payload = GoogleRoutes().normalize({"routes": [{"distanceMeters": km*1000, "duration": f"{hours*3600}s", "description": via}
        for km, hours, via in [(distance, 2, "NH275"), (distance+10, 3, "SH17")]]}, parameters)
    return ProviderResult("google_routes", "routing", success=True, status="ok", freshness="LIVE", confidence="LIKELY",
        source_url="https://www.google.com/maps", retrieved_at=now.isoformat(), expires_at=(now+timedelta(days=1)).isoformat(), payload=payload)


def _alternative_requests(query):
    return [c for c in query.call_args_list if c.args[0].category == "routing" and c.args[1].get("alternatives")]


class TravelRouteChoiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("route-owner", password="Test12345!", city="Bengaluru")
        self.other = get_user_model().objects.create_user("route-other", password="Test12345!")
        self.client.force_login(self.user)
        self.session = new_session(self.user)
        self.session.state.update({k: fact(v) for k, v in {"origin": "Bengaluru", "transport_mode": "ride",
            "trip_duration": 3, "budget": 15000, "available_start_date": (timezone.localdate()+timedelta(days=2)).isoformat(),
            "available_end_date": (timezone.localdate()+timedelta(days=4)).isoformat()}.items()})
        self.result = route_fixture()
        self.candidate = candidates_for(self.user, self.session.state)[0]
        self.candidate.update(route_result=self.result.as_dict(), selected_route_id=self.result.payload["routes"][0]["route_id"],
            distance_km=80, travel_hours=2)
        self.candidate["budget"] = budget_for(self.session.state, self.candidate)
        self.candidate["map"] = map_features(self.candidate)
        self.session.candidates = [self.candidate]
        self.session.state["selected_destination"] = fact(self.candidate["name"])
        self.session.state["_destination_pool"] = fact([deepcopy(self.candidate)])
        self.session.itinerary = build_itinerary(self.session.state, self.candidate)
        self.session.status = "ready"
        self.session.save()
        self.url = f"/api/mobility/planner/sessions/{self.session.pk}/"

    def choose(self, **overrides):
        return self.client.post(self.url, {"action": "route_choice", "revision": self.session.revision,
            "candidate_index": 0, "route_id": self.result.payload["routes"][1]["route_id"], **overrides}, content_type="application/json")

    @patch.dict("os.environ", {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-key"})
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_alternative_request_is_bounded_and_identical_routes_are_not_doubled(self, request):
        provider = GoogleRoutes()
        p = {"start": [77, 12], "end": [77.1, 12.1], "mode": "ride"}
        provider.fetch(p)
        self.assertFalse(request.call_args.kwargs["json"]["computeAlternativeRoutes"])
        provider.fetch(p | {"alternatives": True, "avoid_tolls": True})
        self.assertTrue(request.call_args.kwargs["json"]["computeAlternativeRoutes"])
        self.assertEqual(request.call_args.kwargs["json"]["routeModifiers"], {"avoidHighways": False, "avoidTolls": True})
        before = request.call_count
        for bad in (1, "true", None, {}):
            with self.assertRaises(ProviderError): provider.fetch(p | {"alternatives": bad})
        self.assertEqual(request.call_count, before)
        route = {"distanceMeters": 1000, "duration": "60s"}
        normalized = provider.normalize({"routes": [route, route]}, p)
        self.assertEqual(len(normalized["routes"]), 1)
        self.assertEqual(normalized["routes"][0]["motorcycle_legal"], "UNKNOWN")

    def test_short_current_routes_request_alternatives_and_failed_comparison_retains_base(self):
        def run(comparison):
            def fetch(provider, parameters, **kwargs):
                if provider.category == "routing":
                    return comparison if parameters.get("alternatives") else self.result
                return ProviderResult(provider.name, provider.category)
            # One mock for both names: routing's base request goes through the fallback chain in cache.py.
            with patch("apps.mobility.services.travel.research.query", side_effect=fetch) as query,                     patch("apps.mobility.services.travel.cache.query", new=query):
                candidate, _ = enrich_candidate(self.user, self.session.state, self.candidate)
                self.assertEqual(len(_alternative_requests(query)), 1)
            return candidate
        accepted = run(self.result)
        self.assertEqual(len(accepted["route_result"]["payload"]["routes"]), 2)
        failed = run(ProviderResult("google_routes", "routing", error="quota_exhausted"))
        self.assertEqual(failed["route_result"]["payload"], self.result.payload)
        self.assertIn("retaining the single-route", failed["route_alternatives_note"])

    def test_long_or_stale_route_never_requests_alternatives(self):
        for source in (route_fixture(distance=101), ProviderResult(**(self.result.as_dict() | {"stale": True}))):
            with self.subTest(source=source.stale), patch("apps.mobility.services.travel.research.query",
                    side_effect=lambda provider, params, **kw: source if provider.category == "routing" else ProviderResult(provider.name, provider.category)) as query,                     patch("apps.mobility.services.travel.cache.query", new=query):
                enrich_candidate(self.user, self.session.state, self.candidate)
                self.assertEqual(_alternative_requests(query), [])

    def test_explicit_choice_rebuilds_draft_budget_geometry_and_save_reopen(self):
        before_evidence = TravelResearchEvidence.objects.count()
        save_plan(self.session)
        self.session.refresh_from_db()
        saved_before = deepcopy(self.session.plan.itinerary)
        response = self.choose()
        self.assertEqual(response.status_code, 200, response.content)
        self.session.refresh_from_db()
        selected = self.session.candidates[0]
        self.assertEqual(selected["distance_km"], 90)
        self.assertEqual(self.session.itinerary["route"]["selected_route_id"], selected["selected_route_id"])
        self.assertEqual(self.session.itinerary["budget"], budget_for(self.session.state, selected))
        budget = selected["budget"]
        self.assertEqual(sum(budget["categories"].values()), budget["expected"])
        self.assertEqual(sum(day["estimated_cost"] for day in self.session.itinerary["days"]), budget["expected"])
        routes = [f for f in selected["map"]["features"] if f["properties"]["kind"] == "route"]
        self.assertEqual(routes, [])  # Google routes carry distance and time only, so no line is drawn
        self.assertEqual(self.session.state["_destination_pool"]["value"][0]["selected_route_id"], selected["selected_route_id"])
        self.assertEqual(TravelResearchEvidence.objects.count(), before_evidence)
        self.session.plan.refresh_from_db()
        self.assertEqual(self.session.plan.itinerary, saved_before)
        save_plan(self.session)
        reopened = self.client.post("/api/mobility/planner/sessions/", {"plan_id": self.session.plan_id}, content_type="application/json")
        self.assertEqual(reopened.status_code, 200, reopened.content)
        self.assertEqual(reopened.json()["itinerary"]["route"]["selected_route_id"], selected["selected_route_id"])

    def test_confirmed_choice_is_preserved_or_requires_review_when_routes_change(self):
        for changed in (False, True):
            self.candidate.update(selected_route_id=self.result.payload["routes"][1]["route_id"], route_choice_confirmed=True)
            response = route_fixture(distance=81) if changed else self.result
            with self.subTest(changed=changed), patch("apps.mobility.services.travel.research.query",
                    side_effect=lambda provider, params, **kw: response if provider.category == "routing" else ProviderResult(provider.name, provider.category)) as query,                     patch("apps.mobility.services.travel.cache.query", new=query):
                candidate, _ = enrich_candidate(self.user, self.session.state, self.candidate)
                if changed:
                    self.assertTrue(candidate["route_choice_required"])
                    self.assertIsNone(candidate["selected_route_id"])
                    self.assertIsNone(candidate["distance_km"])
                    self.assertIn("choose again", candidate["route_alternatives_note"])
                else:
                    self.assertEqual(candidate["selected_route_id"], self.candidate["selected_route_id"])
                    self.assertEqual(candidate["distance_km"], 90)

    def test_stale_revision_changed_geometry_and_expiry_refuse_without_mutation(self):
        original = deepcopy(self.session.candidates)
        for overrides in ({"revision": -1}, {"route_id": "f"*64}, {"revision": True}):
            self.assertEqual(self.choose(**overrides).status_code, 409)
        for field, val in (("expires_at", (timezone.now()-timedelta(seconds=1)).isoformat()),
                ("retrieved_at", (timezone.now()+timedelta(hours=1)).isoformat()), ("retrieved_at", "invalid"), ("stale", True)):
            self.session.candidates = deepcopy(original)
            self.session.candidates[0]["route_result"][field] = val
            self.session.save()
            before = deepcopy(self.session.itinerary)
            self.assertEqual(self.choose().status_code, 409)
            self.session.refresh_from_db()
            self.assertEqual(self.session.itinerary, before)

    def test_ownership_session_csrf_and_multi_stop_boundaries(self):
        for value in (-1, True, None, "0"):
            self.assertEqual(self.choose(candidate_index=value).status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.choose().status_code, 404)
        self.client.logout()
        self.assertIn(self.choose().status_code, (401, 403))
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.user)
        self.assertEqual(csrf.post(self.url, {"action": "route_choice"}, content_type="application/json").status_code, 403)
        self.client.force_login(self.user)
        self.session.state["_itinerary_stops"] = fact([self.candidate, self.candidate])
        self.session.save()
        self.assertEqual(self.choose().status_code, 400)
