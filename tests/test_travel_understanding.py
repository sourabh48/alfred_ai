"""The Travel planner reads each message with the local model (owner request 2026-11-20); rules stay the backup."""
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.mobility.models import TravelPlanningSession
from apps.mobility.services.travel import understanding
from apps.mobility.services.travel.understanding import clean
from apps.mobility.services.travel_conversation import extract, new_session
from apps.mobility.services.travel_discovery import value


def soon(days):
    return (timezone.localdate() + timedelta(days=days)).isoformat()


class CleanTests(TestCase):
    def test_a_casual_message_becomes_alfreds_own_fields(self):
        message = "me and 2 buddies wanna chill somewhere cool this weekend, maybe 5k each, going on bikes from blr"
        answer = {"origin": "blr", "start_date": soon(1), "end_date": soon(2), "days": 2, "budget_rupees": 5000,
                  "budget_scope": "per_person", "travellers": 3, "transport": "ride", "trip_styles": ["chill", "cool"], "avoid": []}
        self.assertEqual(clean(answer, message), {
            "origin": "Bengaluru", "available_start_date": soon(1), "available_end_date": soon(2), "trip_duration": 2,
            "budget": 5000.0, "budget_scope": "per_person", "number_of_travelers": 3, "transport_mode": "ride",
            "preferred_trip_style": ["cool weather"]})

    def test_anything_the_message_does_not_support_is_dropped(self):
        message = "plan something relaxing with my wife, she hates long drives, beach would be nice"
        answer = {"destination": "Goa", "origin": "Mumbai", "budget_rupees": 20000, "transport": "flight", "travellers": 2,
                  "start_date": soon(-3), "end_date": soon(-1), "trip_styles": ["beach", "nightlife"], "avoid": ["long drives"]}
        self.assertEqual(clean(answer, message), {"number_of_travelers": 2, "preferred_trip_style": ["beaches"]})
        self.assertEqual(clean({"destination": "beach"}, "a beach trip please"), {})  # a kind of trip, not a place
        self.assertEqual(clean({"days": 2}, "make day 2 relaxed"), {})  # an itinerary edit, not the trip length
        self.assertEqual(clean({"transport": "bus"}, "somewhere for business"), {})
        self.assertEqual(clean("not a dict", "anything"), {})
        self.assertEqual(clean({"food": "veg"}, "veg food only"), {"food_preferences": "vegetarian"})
        far = {"start_date": soon(1), "end_date": soon(40)}
        self.assertEqual(clean(far, "from tomorrow for 40 days"), {})

    def test_per_person_needs_the_message_to_say_so(self):
        message = "a 4 day car trip from Pune for 2 people, budget 30000 rupees"
        self.assertNotIn("budget_scope", clean({"budget_rupees": 30000, "budget_scope": "per_person"}, message))
        self.assertEqual(clean({"budget_rupees": 3000, "budget_scope": "per_person"}, "3000 per head")["budget_scope"], "per_person")

    def test_a_lone_place_after_the_starting_city_question_is_the_origin(self):
        self.assertEqual(clean({"destination": "Mysuru"}, "mysuru", pending="origin"), {"origin": "Mysuru"})
        self.assertEqual(clean({"destination": "Coorg"}, "can we do coorg instead?"), {"requested_destination": "Coorg"})

    def test_a_place_alfred_just_offered_counts_only_when_the_message_points_back(self):
        offered = "Three ideas: Coorg, Chikmagalur or Wayanad."
        self.assertEqual(clean({"destination": "Chikmagalur"}, "lets do the second one", alfred_said=offered),
                         {"requested_destination": "Chikmagalur"})
        self.assertEqual(clean({"destination": "Chikmagalur"}, "3 days please", alfred_said=offered), {})
        self.assertEqual(clean({"destination": "Ooty"}, "go there", alfred_said=offered), {})  # never offered


class MergeTests(TestCase):
    def test_rules_win_where_they_matched_and_the_model_fills_the_rest(self):
        state, notes = extract({}, "4 days, budget 12000, me and 2 buddies",
                               {"trip_duration": 2, "budget": 9000.0, "number_of_travelers": 3, "transport_mode": "ride"})
        self.assertEqual((value(state, "trip_duration"), value(state, "budget")), (4, 12000.0))  # the rules read these
        self.assertEqual(state["number_of_travelers"]["source"], "local_ai_reading")
        self.assertEqual(value(state, "transport_mode"), "ride")
        self.assertIn("I understood: 3 travellers; travelling by motorbike.", " ".join(notes))
        same, notes = extract({}, "4 days", None)
        self.assertEqual(value(same, "trip_duration"), 4)
        self.assertFalse(any("I understood" in n for n in notes))

    def test_styles_are_added_to_what_was_already_wanted(self):
        state, _ = extract({}, "mountains please", {"preferred_trip_style": ["cool weather"]})
        self.assertEqual(value(state, "preferred_trip_style"), ["cool weather", "mountains"])


class ReadTests(TestCase):
    def test_reading_off_or_a_failing_model_leaves_the_rules_alone(self):
        self.assertEqual(understanding.read("3 days in goa"), {})  # off while testing
        with override_settings(ALFRED_TRAVEL_LOCAL_READING=True), \
                patch("apps.career.services.bullet_rewrite.LocalChat.ask", side_effect=OSError("Ollama is not running")):
            self.assertEqual(understanding.read("3 days in goa"), {})
        with override_settings(ALFRED_TRAVEL_LOCAL_READING=True, ALFRED_TRAVEL_READING_MODEL="gemini-cloud"), \
                patch("apps.career.services.bullet_rewrite.LocalChat.ask") as ask:
            self.assertEqual(understanding.read("3 days in goa"), {})
        ask.assert_not_called()  # never a cloud model

    def test_the_model_gets_only_the_message_today_and_the_last_question(self):
        with override_settings(ALFRED_TRAVEL_LOCAL_READING=True), \
                patch("apps.career.services.bullet_rewrite.LocalChat.ask", return_value={"destination": "Goa"}) as ask:
            self.assertEqual(understanding.read("a goa trip", pending="duration"), {"requested_destination": "Goa"})
        system, payload = ask.call_args.args[:2]
        self.assertEqual(payload, {"message": "a goa trip", "alfred_last_asked": "duration"})
        with override_settings(ALFRED_TRAVEL_LOCAL_READING=True), \
                patch("apps.career.services.bullet_rewrite.LocalChat.ask", return_value={"destination": "Wayanad"}) as ask:
            self.assertEqual(understanding.read("that one", recent=[("user", "somewhere green"), ("assistant", "Coorg or Wayanad?")]),
                             {"requested_destination": "Wayanad"})
        self.assertEqual(ask.call_args.args[1]["earlier_chat"], [{"from": "traveller", "text": "somewhere green"},
                                                                 {"from": "ALFRED", "text": "Coorg or Wayanad?"}])
        self.assertIn(timezone.localdate().isoformat(), system)
        today = timezone.localdate()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        self.assertIn(f"'this weekend' means Saturday {saturday.isoformat()}", system)  # the model miscounted weekdays itself

    def test_a_festival_message_gets_holiday_dates_and_the_lookup_is_used_when_it_answers(self):
        user = get_user_model().objects.create_user("synthetic-travel-festival")
        diwali = (timezone.localdate() + timedelta(days=30)).isoformat()
        with override_settings(ALFRED_TRAVEL_LOCAL_READING=True), \
                patch("apps.mobility.services.travel.trip_tools.holidays", return_value={"holidays": [{"date": diwali, "english": "Diwali"}]}) as lookup, \
                patch("apps.career.services.bullet_rewrite.LocalChat.ask", return_value={}) as ask:
            understanding.read("a trip for the diwali weekend", user=user)
            holidays = ask.call_args.args[1]["upcoming_holidays"]
            self.assertIn({"name": "Diwali", "date": diwali, "weekday": date.fromisoformat(diwali).strftime("%A")}, holidays)
            self.assertEqual(lookup.call_args.kwargs["user"], user)
            christmas = next(h["date"] for h in holidays if h["name"] == "Christmas")
            self.assertTrue(christmas.endswith("-12-25") and christmas >= timezone.localdate().isoformat())
            lookup.side_effect = OSError("offline")
            understanding.read("around christmas", user=user)
            self.assertIn("Christmas", [h["name"] for h in ask.call_args.args[1]["upcoming_holidays"]])  # fixed dates still given
            lookup.reset_mock()
            understanding.read("3 days in goa", user=user)
            self.assertNotIn("upcoming_holidays", ask.call_args.args[1])
            lookup.assert_not_called()  # no lookup unless a holiday is named


class ChatTests(TestCase):
    def test_a_chat_message_uses_the_reading_and_says_what_it_understood(self):
        user = get_user_model().objects.create_user("synthetic-travel-reading")
        session = new_session(user)
        self.client.force_login(user)
        reading = {"number_of_travelers": 3, "transport_mode": "ride"}
        with patch("apps.mobility.services.travel.understanding.read", return_value=reading) as read:
            response = self.client.post(f"/api/mobility/planner/sessions/{session.pk}/", {"action": "message", "text": "me and 2 buddies on a bike"},
                                        content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(read.call_args.args[0], "me and 2 buddies on a bike")
        self.assertEqual([role for role, _ in read.call_args.kwargs["recent"]], ["assistant"])  # ALFRED's greeting
        session.refresh_from_db()
        self.assertEqual(session.state["transport_mode"]["source"], "user_message")  # the rules read "bike" themselves
        self.assertEqual(session.state["number_of_travelers"]["source"], "local_ai_reading")
        self.assertIn("I understood: 3 travellers.", session.messages.filter(role="assistant").last().text)
        stranger = get_user_model().objects.create_user("synthetic-travel-reading-other")
        self.client.force_login(stranger)
        with patch("apps.mobility.services.travel.understanding.read") as read:
            self.assertEqual(self.client.post(f"/api/mobility/planner/sessions/{session.pk}/", {"action": "message", "text": "hi"},
                                              content_type="application/json").status_code, 404)
        read.assert_not_called()  # someone else's trip is never read
