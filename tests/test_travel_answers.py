"""Questions about a planned trip are answered by the local model from that trip's saved research only (owner request 2026-11-20)."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.mobility.services.travel import answers
from apps.mobility.services.travel_conversation import new_session
from apps.mobility.services.travel_discovery import fact

ITINERARY = {"destination": "Coorg", "route": {"distance_km_one_way": 265, "hours_one_way": 6.5}, "budget": {"total": 9000},
             "days": [{"date": "2026-11-21", "title": "Ride to Coorg", "items": []}],
             "weather_result": {"success": True, "retrieved_at": "2026-11-20T08:00:00+05:30",
                                "payload": {"days": [{"date": "2026-11-21", "precipitation_total": 12.0}]}},
             "climate_result": {"success": False, "payload": {"note": "never shown"}}}
STATE = {"origin": fact("Bengaluru"), "transport_mode": fact("ride")}
ASK = "apps.career.services.bullet_rewrite.LocalChat.ask"


@override_settings(ALFRED_TRAVEL_LOCAL_READING=True)
class AnswerTests(TestCase):
    def test_only_saved_successful_research_goes_to_the_model(self):
        facts = answers.trip_facts(ITINERARY, STATE)
        self.assertEqual(facts["weather"]["days"], [{"date": "2026-11-21", "precipitation_total": 12.0, "weekday": "Saturday"}])
        self.assertEqual(facts["weather"]["retrieved_at"], "2026-11-20T08:00:00+05:30")
        self.assertNotIn("climate", facts)  # a failed lookup is not a fact
        self.assertEqual((facts["origin"], facts["route"]["hours_one_way"]), ("Bengaluru", 6.5))
        huge = {**ITINERARY, "days": [{"date": "2026-11-21", "title": "x" * 200}] * 60}
        self.assertNotIn("days", answers.trip_facts(huge, STATE))  # trimmed to fit the small model's window

    def test_an_answer_found_in_the_facts_is_labelled_and_anything_else_says_so(self):
        with patch(ASK, return_value={"answer": "About 12 mm of rain is forecast for 2026-11-21.", "found_in_trip_facts": "yes"}) as ask:
            reply = answers.answer("will it rain on the way?", ITINERARY, STATE)
        self.assertEqual(reply, "About 12 mm of rain is forecast for 2026-11-21. (From this trip's saved research; check the linked sources before you go.)")
        self.assertEqual(set(ask.call_args.args[1]), {"question", "trip_facts"})
        with patch(ASK, return_value={"answer": "Probably open.", "found_in_trip_facts": "no"}):
            self.assertEqual(answers.answer("is the homestay open?", ITINERARY, STATE), answers.NOT_FOUND)
        with patch(ASK, side_effect=OSError("Ollama is not running")):
            self.assertEqual(answers.answer("will it rain?", ITINERARY, STATE), "")
        with patch(ASK) as ask:
            self.assertEqual(answers.answer("make it relaxed", ITINERARY, STATE), "")  # not a question
            self.assertEqual(answers.answer("will it rain?", {}, STATE), "")  # no trip planned yet
            with override_settings(ALFRED_TRAVEL_LOCAL_READING=False):
                self.assertEqual(answers.answer("will it rain?", ITINERARY, STATE), "")
        ask.assert_not_called()

    def test_the_chat_replies_with_the_answer_when_nothing_else_acted_on_the_question(self):
        user = get_user_model().objects.create_user("synthetic-travel-answers")
        session = new_session(user)
        session.itinerary, session.state = ITINERARY, {**session.state, **STATE}
        session.save()
        self.client.force_login(user)
        with patch("apps.mobility.services.travel.understanding.read", return_value={}), \
                patch("apps.mobility.services.travel.answers.answer", return_value="About 12 mm of rain.") as answer:
            response = self.client.post(f"/api/mobility/planner/sessions/{session.pk}/", {"action": "message", "text": "will it rain there?"},
                                        content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(answer.call_args.args[0], "will it rain there?")
        self.assertEqual(session.messages.filter(role="assistant").last().text, "About 12 mm of rain.")
        session.candidates = [{"name": "Coorg"}]
        session.save()
        with patch("apps.mobility.services.travel.understanding.read", return_value={}),                 patch("apps.mobility.services.travel_conversation.queue_research") as research,                 patch("apps.mobility.services.travel.answers.answer", return_value="About 12 mm of rain."):
            self.client.post(f"/api/mobility/planner/sessions/{session.pk}/", {"action": "message", "text": "is rain expected?"},
                             content_type="application/json")
        research.assert_called_once()  # the question still refreshes the research
        self.assertTrue(session.messages.filter(role="assistant").last().text.startswith("About 12 mm of rain. I'm also refreshing"))
