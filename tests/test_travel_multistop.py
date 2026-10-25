"""Owned manual itineraries use one budget; route estimates are never verified evidence."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.mobility.planner_views import session_payload
from apps.mobility.services.travel_conversation import save_plan, send_message
from apps.mobility.services.travel_discovery import fact, value
from apps.mobility.services.travel_itinerary import build_multi_stop_itinerary
from apps.mobility.services.travel.money import rupees
from apps.mobility.services.travel_research import queue_research, run_research
from tests import test_travel_planner as fixtures


class TravelMultiStopTests(TestCase):
    setUp = fixtures.TravelPlannerTests.setUp
    ready = fixtures.TravelPlannerTests.ready

    def researched(self):
        session = self.ready()
        self.assertEqual(run_research(session.research_runs.first().pk)["status"], "ready")
        session.refresh_from_db()
        self.assertGreaterEqual(len(session.candidates), 2)
        return session

    def set_stops(self, session, names, **extra):
        response = self.client.post(f"/api/mobility/planner/sessions/{session.pk}/",
            {"action": "itinerary_stops", "stops": names, "revision": session.revision, **extra}, content_type="application/json")
        session.refresh_from_db()
        return response

    def multi(self):
        session = self.researched()
        names = [s["name"] for s in session.candidates[:2]]
        self.assertEqual(self.set_stops(session, names).status_code, 200)
        return session, names

    def test_chronological_round_trip_one_shared_decimal_budget_and_scoped_evidence(self):
        session = self.researched()
        stops = deepcopy(session.candidates[:2])
        stops[0]["nightly"], stops[1]["nightly"] = "1000.01", "2000.02"
        stops[0]["selected_price_snapshots"] = [{"category": "Stay", "total": "1", "currency": "INR",
            "scope": "whole_trip", "availability": "available", "source_url": "https://example.invalid/quote",
            "expires_at": (timezone.now()+timedelta(days=1)).isoformat()}]
        state = {**session.state, "budget_type": fact("standard"), "budget": fact(100000),
            "vehicle_mileage": fact(30), "fuel_price_per_litre": fact("110.01")}
        result = build_multi_stop_itinerary(state, stops)
        self.assertEqual([s["nights"] for s in result["stops"]], [2, 1])
        self.assertEqual([d["date"] for d in result["days"]],
            [(date.fromisoformat(value(state, "available_start_date"))+timedelta(days=i)).isoformat() for i in range(4)])
        legs = result["route"]["legs"]
        self.assertEqual([(l["from"], l["to"]) for l in legs],
            [("Bengaluru", stops[0]["name"]), (stops[0]["name"], stops[1]["name"]), (stops[1]["name"], "Bengaluru")])
        categories = result["budget"]["categories"]
        self.assertEqual(categories["Stay"], rupees(Decimal("1000.01")*2+Decimal("2000.02")))
        self.assertEqual(categories["Fuel"], rupees(Decimal(sum(l["distance_km"] for l in legs)+100)/30*Decimal("110.01")))
        self.assertEqual(categories["Food"], 650*4)
        self.assertEqual(sum(categories.values()), result["budget"]["expected"])
        self.assertEqual(sum(d["estimated_cost"] for d in result["days"]), result["budget"]["expected"])
        self.assertEqual(result["budget"]["verified_prices"], [])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["map"], {})
        self.assertEqual(result["route_result"], {})
        self.assertEqual(result["weather"]["confidence"], "UNKNOWN")
        self.assertTrue(all(s["sources"] for s in result["stops"]))
        self.assertTrue(all(f"{s['name']}: {issue}" in result["checks"] for s in stops for issue in s["issues"]))
        self.assertIn("not optimized", result["route"]["note"])

    def test_stop_order_edits_saved_plan_and_reopen_preserve_owner_state(self):
        session, names = self.multi()
        self.assertNotIn("_itinerary_stops", session_payload(session)["state"])
        self.assertEqual(self.set_stops(session, names[::-1]).json()["itinerary_stops"], names[::-1])
        self.assertEqual(session.itinerary["route"]["legs"][0]["to"], names[-1])
        before = deepcopy(session.itinerary["days"])
        session = send_message(session.pk, self.user, "Make day 2 relaxed")
        self.assertEqual(session.itinerary["days"][1]["pace"], "relaxed")
        for index in (0, 2, 3):
            self.assertEqual(session.itinerary["days"][index], before[index])
        self.assertEqual(sum(d["estimated_cost"] for d in session.itinerary["days"]), session.itinerary["budget"]["expected"])
        plan = save_plan(session)
        self.assertEqual(plan.itinerary, session.itinerary)
        response = self.client.post("/api/mobility/planner/sessions/", {"plan_id": plan.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], session.pk)
        self.assertEqual(response.json()["itinerary_stops"], names[::-1])
        self.assertEqual(response.json()["itinerary"]["days"], session.itinerary["days"])
        self.assertEqual(self.set_stops(session, names).status_code, 200)

    def test_invalid_or_stale_stop_requests_never_change_the_existing_trip(self):
        session, names = self.multi()
        before = deepcopy(session.itinerary)
        for stops in (None, "not a list", [True], names+names[:1], names+["Other-account stop"], names*3):
            with self.subTest(stops=stops):
                self.assertEqual(self.set_stops(session, stops).status_code, 400)
                self.assertEqual(session.itinerary, before)
        for revision in (True, session.revision-1, str(session.revision)):
            self.assertEqual(self.set_stops(session, names[::-1], revision=revision).status_code, 409)
            self.assertEqual(session.itinerary, before)
        self.assertEqual(self.set_stops(session, []).status_code, 200)
        self.assertEqual(session.itinerary, {})
        self.assertIsNone(value(session.state, "selected_destination"))

    def test_ownership_and_csrf(self):
        session, names = self.multi()
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        self.client.force_login(self.other)
        self.assertEqual(self.set_stops(session, names[::-1]).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post(url, {"action": "itinerary_stops", "stops": names,
            "revision": session.revision}, content_type="application/json").status_code, 403)

    def test_missing_coordinates_unsupported_mode_and_too_short_window_abstain(self):
        session = self.researched()
        stops = deepcopy(session.candidates[:2])
        for key, val in (("origin", "Unresolved synthetic origin"), ("transport_mode", "flight"), ("trip_duration", 2), ("trip_duration", 31)):
            with self.subTest(key=key, val=val), self.assertRaises(ValidationError):
                build_multi_stop_itinerary({**session.state, key: fact(val)}, stops)
        for key, val in (("lat", None), ("lon", float("nan")), ("lat", 91), ("nightly", -1)):
            broken = deepcopy(stops)
            broken[1][key] = val
            with self.subTest(key=key, val=val), self.assertRaises(ValidationError):
                build_multi_stop_itinerary(session.state, broken)

    def test_dates_duration_and_price_changes_rebuild_without_dropping_stops(self):
        session, names = self.multi()
        session = send_message(session.pk, self.user, "Make day 2 relaxed")
        old_budget = deepcopy(session.itinerary["budget"])
        start = self.today+timedelta(days=12)
        session = send_message(session.pk, self.user, f"{start} to {start+timedelta(days=3)}")
        self.assertEqual(session.itinerary["days"][1]["pace"], "relaxed")
        self.assertEqual(session.itinerary["budget"], old_budget)
        self.assertEqual(session.itinerary["days"][0]["date"], start.isoformat())
        session = send_message(session.pk, self.user, "5 days")
        self.assertEqual(len(session.itinerary["days"]), 5)
        self.assertEqual([s["name"] for s in session.itinerary["stops"]], names)
        self.assertEqual(sum(s["nights"] for s in session.itinerary["stops"]), 4)
        session = send_message(session.pk, self.user, "Budget ₹1000 total")
        self.assertEqual(session.itinerary["budget"]["target"], 1000)
        self.assertGreater(session.itinerary["budget"]["over_budget"], 0)

    def test_one_stop_date_change_cannot_restore_old_weather_on_rebuild(self):
        session = self.researched()
        name = session.candidates[0]["name"]
        self.assertEqual(self.set_stops(session, [name]).status_code, 200)
        self.assertTrue(session.itinerary["weather_result"]["success"])
        start = self.today+timedelta(days=15)
        session = send_message(session.pk, self.user, f"{start} to {start+timedelta(days=3)}")
        session = send_message(session.pk, self.user, "Build itinerary")
        self.assertEqual(session.itinerary["weather"]["confidence"], "UNKNOWN")
        self.assertFalse(session.itinerary["weather_result"]["success"])
        self.assertEqual(session.itinerary["weather_result"]["status"], "needs_refresh")

    def test_research_cannot_replace_multi_stop_geometry_days_or_budget(self):
        session, _ = self.multi()
        session = send_message(session.pk, self.user, "Make day 2 relaxed")
        before = deepcopy(session.itinerary)
        run = queue_research(session, recheck=True)
        self.assertEqual(run_research(run.pk)["status"], "ready")
        session.refresh_from_db()
        for key in ("route", "days", "weather", "sources", "edits", "stops"):
            self.assertEqual(session.itinerary[key], before[key])
        self.assertEqual(session.itinerary["budget"]["expected"], before["budget"]["expected"])
        self.assertIn("no complete route", session.itinerary["budget"]["recheck_note"])

    def test_rejecting_active_stop_and_shortening_dates_roll_back(self):
        session, names = self.multi()
        before = deepcopy(session.itinerary)
        response = self.client.post(f"/api/mobility/planner/sessions/{session.pk}/",
            {"action": "reject", "destination": names[0]}, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(f"/api/mobility/planner/sessions/{session.pk}/",
            {"action": "message", "text": "2 days"}, content_type="application/json").status_code, 400)
        session.refresh_from_db()
        self.assertEqual(session.itinerary, before)

    def test_single_destination_choice_explicitly_replaces_multi_stop_plan(self):
        session, _ = self.multi()
        chosen = session.candidates[-1]["name"]
        session = send_message(session.pk, self.user, f"Choose {chosen}")
        self.assertNotIn("_itinerary_stops", session.state)
        self.assertEqual(session.itinerary, {})
        session = send_message(session.pk, self.user, "Build itinerary")
        self.assertEqual(session.itinerary["destination"], chosen)
        self.assertNotIn("stops", session.itinerary)

    def test_saved_details_destination_change_clears_previous_stop_selection(self):
        session, _ = self.multi()
        plan = save_plan(session)
        response = self.client.patch(f"/api/mobility/travel-plans/{plan.pk}/",
            {"destination": "Coorg"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.itinerary, {})
        self.assertNotIn("_itinerary_stops", session.state)

    def test_five_stops_can_span_discovery_batches_without_replacing_the_itinerary(self):
        from tests.test_travel_candidate_pool import synthetic_pool
        session = self.ready()
        session.state["trip_duration"] = fact(6)
        session.state["available_end_date"] = fact(str(date.fromisoformat(value(session.state, "available_start_date"))+timedelta(days=5)))
        session.revision += 1
        session.save()
        with patch('apps.mobility.services.travel.research.research_candidates', side_effect=lambda user,state,preliminary: synthetic_pool(user,state)):
            self.assertEqual(run_research(queue_research(session).pk)["status"], "ready")
        session.refresh_from_db()
        names = [s["name"] for s in session.candidates]
        self.assertEqual(self.set_stops(session, names).status_code, 200)
        previous = deepcopy(session.itinerary)
        session = send_message(session.pk, self.user, "Show more destinations")
        self.assertEqual(run_research(session.research_runs.first().pk)["status"], "ready")
        session.refresh_from_db()
        self.assertEqual(session.itinerary["days"], previous["days"])
        names += [s["name"] for s in session.candidates[:2]]
        self.assertEqual(self.set_stops(session, names).status_code, 200)
        self.assertEqual([s["nights"] for s in session.itinerary["stops"]], [1]*5)
        self.assertEqual(len(session.itinerary["route"]["legs"]), 6)
        self.assertEqual(self.set_stops(session, names+[session.candidates[-1]["name"]]).status_code, 400)
