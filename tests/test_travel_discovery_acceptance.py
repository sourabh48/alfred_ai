"""Bounded destination discovery with synthetic sources and owner-only history."""
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.mobility.models import TravelPlan, TripLog, TripPhoto
from apps.mobility.services.travel.discovery import rank_places, remember
from apps.mobility.services.travel.providers.base import ProviderResult
from apps.mobility.services.travel.presentation import age_saved_facts
from apps.mobility.services.travel.intent import augment
from apps.mobility.services.travel.research import discover_destinations, enrich_candidate
from apps.mobility.services.travel_catalog import DESTINATIONS
from apps.mobility.services.travel_discovery import candidates_for, fact, history_for
from apps.mobility.services.travel_conversation import new_session
from tests import test_travel_planner as fixtures


def synthetic_discovery_result():
    now = timezone.now()
    return ProviderResult("wikivoyage", "destinations", success=True, status="ok", freshness="LIVE",
        confidence="LIKELY", source_url="https://en.wikivoyage.org/wiki/Special:Search",
        attribution="Synthetic guide fixture; no live access or availability check",
        retrieved_at=(now-timedelta(hours=1)).isoformat(), verified_at=(now-timedelta(hours=1)).isoformat(),
        expires_at=(now+timedelta(hours=1)).isoformat()).as_dict()


class TravelDiscoveryAcceptanceTests(TestCase):
    setUp = fixtures.TravelPlannerTests.setUp

    def options(self, name, **state):
        seed = dict(deepcopy(DESTINATIONS[1]), name=name)
        return candidates_for(self.user, {"origin": fact("Bengaluru"), **state}, destinations=[seed])

    def test_recorded_dynamic_visits_match_case_and_spacing_and_explicit_request_wins(self):
        remember(self.user, {"name": "  Synthetic   Valley "}, "visited")
        self.assertEqual(self.options("synthetic valley")[0]["novelty"], "Previously recorded")
        self.assertEqual(self.options("SYNTHETIC VALLEY", only_new_places=fact(True)), [])
        self.assertEqual(len(self.options("Synthetic Valley", only_new_places=fact(True),
            requested_destination=fact("synthetic valley"))), 1)

    def test_all_rejection_records_apply_across_source_ids_without_affecting_another_owner(self):
        remember(self.user, {"id": "guide:1", "name": "Synthetic Valley"}, "rejected")
        remember(self.user, {"id": "guide:2", "name": "synthetic valley"}, "shown")
        self.assertEqual(self.options("Synthetic Valley"), [])
        remember(self.other, {"name": "Other Valley"}, "visited")
        self.assertEqual(self.options("Other Valley", only_new_places=fact(True))[0]["novelty"], "New in your records")

    def test_dynamic_trip_log_and_photo_locations_are_recorded_without_claiming_unknown_visits(self):
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination="Somewhere else")
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today,
            title="Synthetic log", location_name="Synthetic Log Valley")
        TripPhoto.objects.create(user=self.user, image="synthetic-unwritten.jpg", location_name="Synthetic Photo Valley")
        for name in ("synthetic log valley", "SYNTHETIC PHOTO VALLEY"):
            with self.subTest(name=name):
                self.assertEqual(self.options(name, only_new_places=fact(True)), [])
        option = self.options("Unknown Valley")[0]
        self.assertIn("not proof you have never been", " ".join(option["why"]))

    def test_dynamic_completed_trip_variants_share_visit_and_recent_counts(self):
        for name in ("Synthetic Valley", " synthetic   valley "):
            TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination=name, status="completed",
                start_date=self.today-timedelta(days=3), end_date=self.today-timedelta(days=1))
        option = self.options("SYNTHETIC VALLEY")[0]
        self.assertIn("2 recorded visit(s), 2 dated within the last year", " ".join(option["why"]))

    def test_location_labels_match_a_guide_name_and_dated_logs_and_photos_count_as_recent(self):
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination="Somewhere else")
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today-timedelta(days=30),
            title="Synthetic log", location_name="Log Valley, Synthetic State")
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today-timedelta(days=800),
            title="Old log", location_name="Old Valley")
        TripPhoto.objects.create(user=self.user, image="synthetic-unwritten.jpg", location_name="Photo Valley",
            taken_at=timezone.now()-timedelta(days=30))
        TripPhoto.objects.create(user=self.user, image="synthetic-unwritten.jpg", location_name="Undated Valley")
        for name, recent in (("Log Valley", 1), ("Photo Valley", 1), ("Old Valley", 0), ("Undated Valley", 0)):
            with self.subTest(name=name):
                self.assertIn(f"1 recorded visit(s), {recent} dated within the last year", " ".join(self.options(name)[0]["why"]))
                self.assertEqual(self.options(name, only_new_places=fact(True)), [])
        self.assertEqual(self.options("Log Valley, Synthetic State")[0]["novelty"], "Previously recorded")

    def test_catalog_location_inside_longer_text_keeps_visit_and_gains_recency(self):
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination="Somewhere else")
        name = DESTINATIONS[1]["name"]
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today-timedelta(days=30),
            title="Synthetic log", location_name=f"Camp near {name}")
        history = history_for(self.user)
        self.assertEqual((history["visits"][name], history["recent"][name]), (1, 1))

    def test_visited_place_filter_uses_the_same_place_name_rules(self):
        place = {"id": "osm:node:1", "name": "Synthetic  Valley, Synthetic State", "lat": 12.0, "lon": 77.0, "category": "attraction"}
        self.assertEqual(rank_places(self.user, [place], visited_names={"synthetic valley": 1}, only_new=True), [])
        self.assertEqual(len(rank_places(self.user, [place], visited_names={"other valley": 1}, only_new=True)), 1)

    def test_failed_dynamic_payload_is_not_used_as_successful_destination_evidence(self):
        preliminary = self.options("Offline reference")
        before = deepcopy(preliminary)
        failed = ProviderResult("wikivoyage", "destinations", error="provider_failed",
            payload={"destinations": [dict(deepcopy(DESTINATIONS[1]), name="Unusable source suggestion")]})
        with patch("apps.mobility.services.travel.research.query", return_value=failed):
            options = discover_destinations(self.user, {"origin": fact("Bengaluru")}, preliminary)
        self.assertEqual([d["name"] for d in options], ["Offline reference"])
        self.assertEqual(options[0]["source_freshness"], "STATIC_REFERENCE")
        self.assertFalse(options[0]["discovery_result"]["success"])
        self.assertIn("offline seed catalog", " ".join(options[0]["issues"]))
        self.assertEqual(preliminary, before)

    def test_cached_dynamic_guide_remains_a_source_lead_and_empty_success_uses_reference(self):
        source = ProviderResult("wikivoyage", "destinations", success=True, status="stale",
            freshness="CACHED", stale=True, payload={"destinations": [dict(deepcopy(DESTINATIONS[1]), name="Guide suggestion")]})
        with patch("apps.mobility.services.travel.research.query", return_value=source):
            options = discover_destinations(self.user, {"origin": fact("Bengaluru")}, [])
            self.assertEqual(options[0]["name"], "Guide suggestion")
            self.assertEqual(options[0]["source_freshness"], "CACHED")
            self.assertIn("access remains unverified", " ".join(options[0]["why"]))
            source.payload = {"destinations": []}
            self.assertEqual(discover_destinations(self.user, {"origin": fact("Bengaluru")}, []), [])

    def test_saved_discovery_freshness_tracks_expiry_without_mutating_the_original(self):
        candidate = self.options("Synthetic Valley")[0]
        candidate.update(source_freshness="LIVE", discovery_result=synthetic_discovery_result(),
            quality={"verified": ["destinations"]})
        before = deepcopy(candidate)
        result = age_saved_facts({"candidates": [candidate]})["candidates"][0]
        self.assertEqual(result["source_freshness"], "RECENTLY_VERIFIED")
        self.assertEqual(candidate, before)
        candidate["discovery_result"]["expires_at"] = (timezone.now()-timedelta(seconds=1)).isoformat()
        result = age_saved_facts({"candidates": [candidate]})["candidates"][0]
        self.assertEqual(result["source_freshness"], "CACHED")
        self.assertEqual(result["discovery_result"]["status"], "stale")
        self.assertEqual(result["discovery_result"]["confidence"], "UNKNOWN")
        self.assertNotIn("destinations", result["quality"]["verified"])

    def test_successful_empty_or_filtered_query_does_not_verify_offline_catalog_candidates(self):
        seed = dict(deepcopy(DESTINATIONS[1]), name="Rejected guide suggestion")
        remember(self.user, seed, "rejected")
        for seeds in ([], [seed]):
            with self.subTest(seeds=len(seeds)):
                source = ProviderResult(**synthetic_discovery_result())
                source.payload = {"destinations": seeds}
                with patch("apps.mobility.services.travel.research.query", return_value=source):
                    candidates = discover_destinations(self.user, {"origin": fact("Bengaluru")}, self.options("Offline reference"))
                candidates[0]["quality"] = {"verified": ["destinations"]}
                candidate = age_saved_facts({"candidates": candidates})["candidates"][0]
                self.assertEqual(candidate["name"], "Offline reference")
                self.assertEqual(candidate["source_freshness"], "STATIC_REFERENCE")
                self.assertTrue(candidate["discovery_result"]["success"])
                self.assertNotIn("destinations", candidate["quality"]["verified"])
                self.assertIn("offline seed catalog", " ".join(candidate["issues"]))

    def test_offline_catalog_card_does_not_list_the_guide_query_as_its_source(self):
        source = ProviderResult(**synthetic_discovery_result())
        source.payload = {"destinations": []}
        with patch("apps.mobility.services.travel.research.query", return_value=source):
            candidate = discover_destinations(self.user, {"origin": fact("Bengaluru")}, self.options("Offline reference"))[0]
        offline = ProviderResult("open_meteo", "weather", error="offline")
        with patch("apps.mobility.services.travel.research.query", return_value=offline):
            _, results = enrich_candidate(self.user, {"origin": fact("Bengaluru")}, candidate)
        self.assertNotIn("wikivoyage", [result.provider for result in results])

    def test_every_stop_of_a_completed_trip_counts_as_visited(self):
        TravelPlan.objects.create(user=self.user, title="Two stops", destination="First Stop", status="completed",
            end_date=self.today, planning_state={"_itinerary_stops": fact([{"name": "First Stop"}, {"name": "Second Stop"}])})
        self.assertEqual(self.options("Second Stop", only_new_places=fact(True)), [])

    def test_somewhere_new_wording_excludes_recorded_visits(self):
        for message in ("Suggest somewhere new I haven't been to", "Places I have never been to", "a destination we haven't visited"):
            with self.subTest(message=message):
                self.assertTrue(augment({}, message)["only_new_places"]["value"])
        for message in ("I haven't been on a long ride since March, plan 2 days from Bengaluru",
                        "Find a new place to stay near Coorg", "Take me somewhere familiar, not somewhere new"):
            with self.subTest(message=message):
                self.assertFalse(augment({}, message).get("only_new_places", {}).get("value"))
        self.assertFalse(augment(augment({}, "Somewhere new please"), "Actually revisit a favourite")["only_new_places"]["value"])

    def test_place_name_inside_a_street_or_train_name_is_not_a_visit(self):
        name = DESTINATIONS[0]["name"]
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination="Somewhere else")
        for location in (name + " Road, Mysuru", name + " Express platform"):
            TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today, title="Synthetic log", location_name=location)
        self.assertNotIn(name, history_for(self.user)["visits"])
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today, title="Synthetic log", location_name="Near " + name)
        self.assertIn(name, history_for(self.user)["visits"])

    def test_guide_disambiguation_matches_a_logged_place(self):
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination="Somewhere else")
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today, title="Synthetic log", location_name="Synthetic Town, Maharashtra")
        self.assertEqual(self.options("Synthetic Town (Maharashtra)", only_new_places=fact(True)), [])

    def test_future_preference_timestamp_does_not_raise_its_weight(self):
        from apps.mobility.services.travel_discovery import profile_for
        profile = profile_for(self.user)
        profile.preferences = {style: {"value": True, "confidence": .4, "updated_at": (timezone.now()+timedelta(days=365)).isoformat()}
                               for style in DESTINATIONS[1]["styles"]}
        profile.save()
        baseline = self.options("Synthetic Valley")[0]["score"]
        for pref in profile.preferences.values():
            pref["updated_at"] = timezone.now().isoformat()
        profile.save()
        self.assertEqual(self.options("Synthetic Valley")[0]["score"], baseline)

    def test_incomplete_discovery_source_or_clock_never_claims_freshness(self):
        for field, invalid in (("retrieved_at", None), ("retrieved_at", (timezone.now()+timedelta(days=1)).isoformat()),
                ("expires_at", "2026-99-99T12:00:00Z"), ("expires_at", "2026-10-29T12:00:00"),
                ("source_url", "javascript:alert(1)")):
            with self.subTest(field=field):
                source = synthetic_discovery_result(); source[field] = invalid
                candidate = self.options("Synthetic Valley")[0]
                candidate.update(source_freshness="LIVE", discovery_result=source, quality={"verified": ["destinations"]})
                result = age_saved_facts({"candidates": [candidate]})["candidates"][0]
                self.assertEqual(result["source_freshness"], "UNKNOWN")
                self.assertNotIn("destinations", result["quality"]["verified"])

    def test_discovery_api_preserves_saved_evidence_and_owner_boundary(self):
        session = new_session(self.user)
        candidate = self.options("Synthetic Valley")[0]
        candidate.update(source_freshness="LIVE", discovery_result=synthetic_discovery_result())
        session.candidates = [candidate]; session.save()
        before = deepcopy(session.candidates)
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        payload = self.client.get(url).json()
        self.assertEqual(payload["candidates"][0]["source_freshness"], "RECENTLY_VERIFIED")
        self.assertEqual(payload["candidates"][0]["discovery_result"]["retrieved_at"], candidate["discovery_result"]["retrieved_at"])
        session.refresh_from_db(); self.assertEqual(session.candidates, before)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
