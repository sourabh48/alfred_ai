from copy import deepcopy
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.mobility.models import TravelProviderRequest, TravelProviderState
from apps.mobility.services.travel.cache import query, query_with_fallback
from apps.mobility.services.travel.providers.base import Provider
from apps.mobility.services.travel.research import enrich_candidate
from apps.mobility.services.travel_conversation import new_session, save_plan, send_message
from apps.mobility.services.travel_discovery import candidates_for, fact, value
from apps.mobility.services.travel_research import queue_research, run_research


class FixtureProvider(Provider):
    min_interval = 0
    allowed_parameters = {"name", "latitude", "longitude", "start", "end", "mode",
                          "avoid_expressways", "avoid_tolls", "preference", "start_date", "end_date",
                          "categories", "check_in", "check_out", "adults", "rooms", "origin",
                          "destination", "departure_date", "return_date", "date", "topic"}

    def __init__(self, category, payload):
        self.name = "fixture_" + category
        self.category = category
        self.source_url = "https://example.org/" + category
        self.payload = payload
        self.fetch = Mock(return_value=(payload, "a" * 64))

    def unavailable_reason(self):
        return ""

    def normalize(self, raw, parameters):
        return deepcopy(raw)


class TravelSelectiveRefreshTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("selective-travel", city="Bengaluru")
        start = timezone.localdate() + timedelta(days=2)
        self.state = {k: fact(v) for k, v in {
            "origin": "Bengaluru", "trip_duration": 3, "budget_type": "budget", "transport_mode": "ride",
            "available_start_date": str(start), "available_end_date": str(start + timedelta(days=2)),
            "origin_airport": "BLR", "destination_airport": "CCJ", "research_categories": ["hotels"],
        }.items()}
        self.destination = candidates_for(self.user, self.state)[0]
        self.providers = {category: FixtureProvider(category, payload) for category, payload in {
            "routing": {"routes": [{"distance_km": 200, "duration_hours": 4,
                                     "geometry": {"type": "LineString", "coordinates": [[77, 12], [76, 11]]}}]},
            "weather": {"summary": "Synthetic forecast", "precipitation_total": 0, "days": []},
            "places": {"places": []}, "hotels": {"options": []}, "flights": {"options": []},
            "trains": {"options": []}, "web": {"findings": []},
        }.items()}
        factories = {"OpenRouteService": "routing", "OpenMeteoWeather": "weather", "OverpassPlaces": "places",
                     "DuffelAccommodation": "hotels", "DuffelFlights": "flights", "IndianRailProvider": "trains",
                     "BraveSearch": "web", "SearXNGSearch": "web", "WikivoyageSearch": "web"}
        for factory, category in factories.items():
            p = patch("apps.mobility.services.travel.research." + factory, return_value=self.providers[category])
            p.start()
            self.addCleanup(p.stop)
        for target in ("apps.mobility.services.travel_research.dispatch",):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        p = patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("Mock network only"))
        p.start()
        self.addCleanup(p.stop)

    def seeded(self):
        destination, _ = enrich_candidate(self.user, self.state, self.destination)
        for provider in self.providers.values():
            provider.fetch.reset_mock()
        return destination

    def session(self):
        session = new_session(self.user)
        session.state = deepcopy(self.state)
        session.candidates = [self.seeded()]
        session.save()
        return session

    def itinerary(self):
        session = self.session()
        run_research(queue_research(session, recheck=True).id)
        session.refresh_from_db()
        session = send_message(session.id, self.user, "Choose " + session.candidates[0]["name"])
        return send_message(session.id, self.user, "Build itinerary")

    def test_weather_refresh_does_not_fetch_unrelated_expired_categories(self):
        destination = self.seeded()
        VerifiedExternalInsight.objects.filter(scope="travel_provider").update(stale_after=timezone.now() - timedelta(seconds=1))
        state = {**self.state, "force_refresh": fact(True), "refresh_categories": fact(["weather"])}
        refreshed, _ = enrich_candidate(self.user, state, destination)
        self.providers["weather"].fetch.assert_called_once()
        for category in set(self.providers) - {"weather"}:
            self.providers[category].fetch.assert_not_called()
            if category != "web":
                self.assertEqual(refreshed[{"routing": "route"}.get(category, category) + "_result"]["freshness"], "CACHED")
        self.assertNotIn("routing", refreshed["quality"]["verified"])
        self.assertEqual(refreshed["weather_result"]["freshness"], "LIVE")

    def test_stay_refresh_reuses_fresh_route_and_preserves_provenance(self):
        destination = self.seeded()
        refreshed, _ = enrich_candidate(self.user, {**self.state, "force_refresh": fact(True),
            "refresh_categories": fact(["hotels"])}, destination)
        self.providers["hotels"].fetch.assert_called_once()
        self.providers["routing"].fetch.assert_not_called()
        self.assertEqual(refreshed["route_result"]["retrieved_at"], destination["route_result"]["retrieved_at"])
        self.assertEqual(refreshed["route_result"]["response_hash"], destination["route_result"]["response_hash"])
        self.assertEqual(refreshed["route_result"]["freshness"], "RECENTLY_VERIFIED")

    def test_latest_requested_web_topic_is_not_crowded_out_by_old_interests(self):
        state = {**self.state, "research_categories": fact(["permits", "hotels", "trains", "flights"]),
                 "refresh_categories": fact(["flights"]), "force_refresh": fact(True)}
        refreshed, _ = enrich_candidate(self.user, state, self.seeded())
        self.assertTrue(any(r["request_parameters"]["topic"] == "flights" and r["freshness"] == "LIVE"
                            for r in refreshed["web_research"]))
        self.providers["web"].fetch.assert_called_once()

    def test_changed_route_parameters_do_not_reuse_the_old_route(self):
        destination = self.seeded()
        state = {**self.state, "avoid_expressways": fact(True), "refresh_categories": fact(["routing"])}
        refreshed, _ = enrich_candidate(self.user, state, destination)
        self.providers["routing"].fetch.assert_called_once()
        self.providers["hotels"].fetch.assert_not_called()
        self.assertTrue(refreshed["route_result"]["request_parameters"]["avoid_expressways"])

    def test_date_change_fetches_new_weather_without_reusing_old_dates(self):
        destination = self.seeded()
        new_start = timezone.localdate() + timedelta(days=5)
        state = {**self.state, "available_start_date": fact(str(new_start)),
            "available_end_date": fact(str(new_start + timedelta(days=2))), "refresh_categories": fact(["weather"])}
        refreshed, _ = enrich_candidate(self.user, state, destination)
        self.providers["weather"].fetch.assert_called_once()
        self.providers["routing"].fetch.assert_not_called()
        self.providers["hotels"].fetch.assert_not_called()
        self.assertEqual(refreshed["hotels_result"]["error"], "refresh_not_requested")
        self.assertFalse(refreshed["hotels_result"]["success"])
        self.assertEqual(refreshed["weather_result"]["request_parameters"]["start_date"], str(new_start))

    def test_whole_trip_force_refresh_still_rechecks_all_categories(self):
        destination = self.seeded()
        enrich_candidate(self.user, {**self.state, "force_refresh": fact(True)}, destination)
        for category, provider in self.providers.items():
            self.assertGreater(provider.fetch.call_count, 0, category)

    def test_scoped_refresh_does_not_bypass_existing_quota_or_lease(self):
        destination = self.seeded()
        state = {**self.state, "force_refresh": fact(True), "refresh_categories": fact(["weather"])}
        self.providers["weather"].limits = {"day": 1}
        refreshed, _ = enrich_candidate(self.user, state, destination)
        self.assertEqual(refreshed["weather_result"]["error"], "local_quota_exhausted")
        self.providers["weather"].fetch.assert_not_called()
        self.providers["weather"].limits = {"day": 100}
        TravelProviderState.objects.filter(provider="fixture_weather").update(lease_until=timezone.now() + timedelta(minutes=1))
        refreshed, _ = enrich_candidate(self.user, state, destination)
        self.assertEqual(refreshed["weather_result"]["error"], "provider_busy_or_backoff")
        self.providers["weather"].fetch.assert_not_called()

    def test_cache_only_miss_and_fallback_cannot_fetch(self):
        provider = self.providers["weather"]
        missing = query(provider, {"latitude": 12}, cache_only=True, force=True)
        self.assertFalse(missing.success)
        self.assertEqual(missing.error, "refresh_not_requested")
        first = query(provider, {"latitude": 12})
        VerifiedExternalInsight.objects.update(stale_after=timezone.now() - timedelta(seconds=1))
        provider.fetch.reset_mock()
        result = query_with_fallback([provider], {"latitude": 12}, cache_only=True)
        self.assertEqual(result.retrieved_at, first.retrieved_at)
        self.assertTrue(result.stale)
        self.assertEqual(result.confidence, "UNKNOWN")
        provider.fetch.assert_not_called()
        self.assertEqual(TravelProviderRequest.objects.filter(network_call=True).count(), 1)

    def test_followup_uses_current_message_instead_of_accumulated_interests(self):
        session = self.session()
        session = send_message(session.id, self.user, "Refresh weather")
        run = session.research_runs.first()
        self.assertEqual(value(run.request, "refresh_categories"), ["weather"])
        self.assertTrue(value(run.request, "force_refresh"))
        self.assertNotIn("force_refresh", session.state)
        self.assertNotIn("refresh_categories", session.state)

    def test_different_pending_scope_gets_a_new_revision_and_old_result_cannot_apply(self):
        session = self.session()
        session = send_message(session.id, self.user, "Refresh hotels")
        old_run = session.research_runs.first()
        session = send_message(session.id, self.user, "Refresh weather")
        new_run = session.research_runs.first()
        self.assertNotEqual(new_run.id, old_run.id)
        self.assertEqual(run_research(old_run.id)["status"], "superseded")
        self.assertEqual(run_research(new_run.id)["status"], "ready")
        session.refresh_from_db()
        self.assertEqual(value(session.state, "origin"), "Bengaluru")

    def test_recheck_saved_destination_skips_discovery_and_retains_user_edits(self):
        session = self.session()
        session = send_message(session.id, self.user, "Choose " + session.candidates[0]["name"])
        session = send_message(session.id, self.user, "Build itinerary")
        session = send_message(session.id, self.user, "Make day 2 relaxed")
        before = deepcopy(session.itinerary)
        run = queue_research(session, recheck=True, categories=["hotels"])
        with patch("apps.mobility.services.travel.research.research_candidates", side_effect=AssertionError("No rediscovery")):
            self.assertEqual(run_research(run.id)["status"], "ready")
        session.refresh_from_db()
        self.assertEqual(session.itinerary["days"], before["days"])
        self.assertEqual(session.itinerary["budget"]["categories"], before["budget"]["categories"])
        self.assertEqual(value(session.state, "selected_destination"), before["destination"])

    def test_train_followup_does_not_accidentally_request_rain(self):
        session = send_message(self.session().id, self.user, "Refresh trains")
        self.assertEqual(value(session.research_runs.first().request, "refresh_categories"), ["trains"])

    def test_inventory_followups_do_not_force_unrelated_hotels(self):
        for text, category in (("Refresh flight availability", "flights"), ("Refresh buses", "buses"),
                               ("Refresh bus availability", "buses")):
            with self.subTest(category=category):
                session = send_message(self.session().id, self.user, text)
                self.assertEqual(value(session.research_runs.first().request, "refresh_categories"), [category])

    def test_recheck_preserves_the_selected_location_for_ambiguous_names(self):
        session = self.session()
        chosen = session.candidates[0]
        session.state["selected_destination"] = fact(chosen["name"])
        session.state["selected_location"] = fact({"name": chosen["name"], "lat": chosen["lat"], "lon": chosen["lon"]})
        session.candidates.append({**deepcopy(chosen), "lat": chosen["lat"] + 1})
        session.save()
        self.assertEqual(run_research(queue_research(session, recheck=True, categories=["weather"]).id)["candidate_count"], 1)
        session.refresh_from_db()
        self.assertEqual(session.candidates[0]["lat"], chosen["lat"])

    def test_explicit_scope_change_supersedes_an_active_job_without_state_change(self):
        session = self.session()
        old = queue_research(session, recheck=True, force=True, categories=["hotels"])
        new = queue_research(session, recheck=True, force=True, categories=["weather"])
        self.assertNotEqual(old.id, new.id)
        self.assertGreater(new.revision, old.revision)

    def test_repeated_weather_refresh_does_not_accumulate_risk_penalties(self):
        self.providers["weather"].payload["days"] = [{"date": value(self.state, "available_start_date"),
            "risks": ["rain"], "rain_mm": 30, "max_temp_c": 25, "wind_kmh": 10}]
        first = self.seeded()
        for _ in range(3):
            second, _ = enrich_candidate(self.user, {**self.state, "force_refresh": fact(True),
                "refresh_categories": fact(["weather"])}, first)
            self.assertEqual(second["score"], first["score"])

    def test_unknown_changed_route_cannot_retain_the_old_verified_distance(self):
        destination = self.seeded()
        refreshed, _ = enrich_candidate(self.user, {**self.state, "origin": fact("Pune"),
            "refresh_categories": fact(["weather"])}, destination)
        self.providers["routing"].fetch.assert_not_called()
        self.assertFalse(refreshed["route_result"]["success"])
        self.assertNotEqual(refreshed["distance_km"], destination["distance_km"])
        self.assertIn("Estimated", refreshed["distance_basis"])

    def test_date_change_preserves_independent_evidence_and_edited_days(self):
        session = send_message(self.itinerary().id, self.user, "Make day 2 relaxed")
        before = deepcopy(session.itinerary)
        for provider in self.providers.values():
            provider.fetch.reset_mock()
        start = timezone.localdate() + timedelta(days=6)
        session = send_message(session.id, self.user, f"{start} to {start + timedelta(days=2)}")
        self.assertEqual(session.itinerary["route_result"], before["route_result"])
        self.assertIn("route", {s["data_type"] for s in session.itinerary["sources"]})
        self.assertIn("routing", session.itinerary["quality"]["verified"])
        self.assertNotIn("weather", session.itinerary["quality"]["verified"])
        self.assertEqual(session.itinerary["budget"]["categories"], before["budget"]["categories"])
        self.assertEqual(session.itinerary["days"][1]["items"], before["days"][1]["items"])
        self.assertEqual(session.itinerary["days"][0]["date"], str(start))
        for destination in [*session.candidates, session.itinerary]:
            for category in ("weather", "hotels", "flights", "trains"):
                self.assertEqual(destination[category + "_result"]["status"], "needs_refresh")
                self.assertEqual(destination[category + "_result"]["payload"], {})
            self.assertEqual(destination["web_research"], [])
        session = send_message(session.id, self.user, "Build itinerary")
        self.assertEqual(session.itinerary["weather_result"]["status"], "needs_refresh")
        for provider in self.providers.values():
            provider.fetch.assert_not_called()

    def test_date_change_with_weather_followup_invalidates_before_queuing(self):
        session = self.itinerary()
        start = timezone.localdate() + timedelta(days=6)
        session = send_message(session.id, self.user, f"{start} to {start + timedelta(days=2)}. Check weather")
        self.assertEqual(session.itinerary["weather_result"]["status"], "needs_refresh")
        self.assertEqual(session.itinerary["days"][0]["date"], str(start))
        self.assertEqual(value(session.research_runs.first().request, "refresh_categories"), ["weather"])

    def test_earlier_window_research_cannot_claim_a_current_forecast_in_the_api(self):
        session = self.itinerary()
        old = session.research_runs.first()
        old_summary = old.summary
        old_count = old.evidence.count()
        start = timezone.localdate() + timedelta(days=6)
        session = send_message(session.id, self.user, f"{start} to {start + timedelta(days=2)}")
        self.client.force_login(self.user)
        payload = self.client.get(f"/api/mobility/planner/sessions/{session.id}/").json()
        self.assertTrue(payload["research"]["outdated"])
        self.assertEqual(payload["research"]["stage"], "Recheck needed")
        self.assertNotIn(old_summary, payload["research"]["summary"])
        self.assertEqual(payload["research"]["sources_checked"], 0)
        self.assertEqual(payload["research"]["evidence"], [])
        old.refresh_from_db()
        self.assertEqual(old.summary, old_summary)
        self.assertEqual(old.evidence.count(), old_count)

    def test_plan_and_session_stay_unchanged_when_invalidation_fails(self):
        session = self.itinerary()
        plan = save_plan(session)
        session.refresh_from_db()
        previous_state = deepcopy(session.state)
        self.client.force_login(self.user)
        start = timezone.localdate() + timedelta(days=6)
        with patch("apps.mobility.services.travel.presentation.invalidate_trip_dates", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.client.patch(f"/api/mobility/travel-plans/{plan.id}/",
                    {"start_date": str(start), "end_date": str(start + timedelta(days=2))}, content_type="application/json")
        session.refresh_from_db()
        plan.refresh_from_db()
        self.assertEqual(session.state, previous_state)
        self.assertEqual(str(plan.start_date), value(previous_state, "available_start_date"))

    def test_plan_date_edit_cannot_resurrect_candidate_offers_or_accepted_prices(self):
        session = self.itinerary()
        quote = {"category": "Stay", "total": "100.00", "currency": "INR", "scope": "whole_trip",
                 "availability": "available", "source_url": "https://example.org/quote",
                 "expires_at": (timezone.now() + timedelta(hours=1)).isoformat()}
        session.candidates[0]["selected_price_snapshots"] = [quote]
        session.save()
        plan = save_plan(session)
        self.client.force_login(self.user)
        start = timezone.localdate() + timedelta(days=7)
        response = self.client.patch(f"/api/mobility/travel-plans/{plan.id}/",
            {"start_date": str(start), "end_date": str(start + timedelta(days=2))}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.candidates[0]["selected_price_snapshots"], [])
        self.assertEqual(session.candidates[0]["budget"]["verified_prices"], [])
        self.assertEqual(session.candidates[0]["hotels_result"]["status"], "needs_refresh")

    def test_date_edit_of_a_reopened_plan_preserves_draft_edits_without_old_offers(self):
        original = send_message(self.itinerary().id, self.user, "Make day 2 relaxed")
        plan = save_plan(original)
        original.plan = None
        original.save(update_fields=["plan"])
        reopened = new_session(self.user, plan)
        self.assertFalse(reopened.candidates)
        start = timezone.localdate() + timedelta(days=5)
        reopened = send_message(reopened.id, self.user, f"{start} to {start + timedelta(days=2)}")
        self.assertEqual(reopened.itinerary["days"][0]["date"], str(start))
        self.assertEqual(reopened.itinerary["days"][1]["items"], original.itinerary["days"][1]["items"])
        self.assertEqual(reopened.itinerary["hotels_result"]["status"], "needs_refresh")
        self.assertEqual(reopened.itinerary["route_result"], original.itinerary["route_result"])
