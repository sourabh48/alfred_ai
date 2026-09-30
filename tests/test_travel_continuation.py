from unittest.mock import patch
from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.mobility.services.travel.intent import augment
from apps.mobility.services.travel.research import enrich_candidate, research_candidates
from apps.mobility.services.travel.providers.base import ProviderResult
from apps.mobility.services.travel_discovery import candidates_for, fact, value
from apps.mobility.services.travel_conversation import new_session, send_message
from apps.mobility.services.travel_research import run_research
from apps.mobility.services.travel.presentation import age_saved_facts
from apps.mobility.models import TravelPreferenceProfile, UserDestinationHistory


class TravelContinuationTests(TestCase):
    def setUp(self):
        network = patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("Mock network only"))
        network.start()
        self.addCleanup(network.stop)
        self.user = get_user_model().objects.create_user("travel-continuation")
        self.state = {k:fact(v) for k,v in {"origin":"Bengaluru","trip_duration":3,"budget_type":"budget","transport_mode":"ride"}.items()}

    def test_intent_retains_context_and_finds_named_destination(self):
        state = augment(self.state,"Plan a 3-day bike trip from Bengaluru to Coorg.")
        self.assertEqual(value(state,"requested_destination"),"Coorg")
        state = augment(state,"Avoid expressways. Find unexplored places around Wayanad.")
        self.assertTrue(value(state,"avoid_expressways"))
        self.assertTrue(value(state,"discover_places"))
        self.assertEqual(value(state,"requested_destination"),"Wayanad")
        self.assertEqual(value(state,"origin"),"Bengaluru")

    def test_comparison_and_permit_followup(self):
        state = augment(self.state,"Compare bike vs train vs flight")
        self.assertEqual(value(state,"transport_mode"),"ride")
        self.assertEqual(value(state,"compare_modes"),["ride","train","flight"])
        state = augment(state,"Is Chembra Peak open and is permission required?")
        self.assertEqual(value(state,"permit_place"),"Chembra Peak")
        self.assertIn("permits",value(state,"research_categories"))

    @patch("apps.mobility.services.travel.research.query")
    def test_arbitrary_destination_is_retained_when_geocoding_unavailable(self, query):
        query.return_value = ProviderResult("open_meteo","geocoding",error="missing_configuration")
        options = research_candidates(self.user,{**self.state,"requested_destination":fact("Ziro")},[])
        self.assertEqual(options[0]["name"],"Ziro")
        self.assertIsNone(options[0]["lat"])
        self.assertEqual(options[0]["geocoding_result"]["freshness"],"UNKNOWN")

    @patch("apps.mobility.services.travel.research.query")
    def test_unavailable_providers_preserve_candidate_and_quality_contract(self, query):
        query.side_effect = lambda provider,params,**kw: ProviderResult(provider.name,provider.category,error="fixture_unavailable")
        original = candidates_for(self.user,self.state)[0]
        enriched, results = enrich_candidate(self.user,self.state,original)
        self.assertEqual(enriched["name"],original["name"])
        self.assertEqual(enriched["quality"]["verified"],[])
        self.assertTrue(enriched["quality"]["unavailable"])
        self.assertEqual(enriched["budget"]["freshness"],"ESTIMATED")
        self.assertEqual(enriched["map"]["type"],"FeatureCollection")
        self.assertNotIn("quality",original)

    @patch("apps.mobility.services.travel_research.dispatch")
    @patch("apps.mobility.services.travel.research.query")
    def test_named_trip_followups_worker_and_reopen(self, query, dispatch):
        query.side_effect = lambda provider,params,**kw: ProviderResult(provider.name,provider.category,error="fixture_unavailable")
        self.user.city = "Bengaluru"
        self.user.save()
        session = send_message(new_session(self.user).id,self.user,"Plan a 3-day bike trip from Bengaluru to Coorg. Budget 15000.")
        self.assertEqual(run_research(session.research_runs.first().id)["status"],"ready")
        session.refresh_from_db()
        self.assertEqual(session.itinerary["destination"],"Coorg")
        self.assertEqual(len(session.itinerary["days"]),3)
        session = send_message(session.id,self.user,"Avoid expressways")
        self.assertTrue(value(session.state,"avoid_expressways"))
        self.assertEqual(value(session.state,"origin"),"Bengaluru")
        session = send_message(session.id,self.user,"Compare bike vs train vs flight")
        self.assertEqual(value(session.state,"transport_mode"),"ride")
        self.assertEqual(value(session.state,"compare_modes"),["ride","train","flight"])
        self.client.force_login(self.user)
        response = self.client.get(f"/api/mobility/planner/sessions/{session.id}/")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["state"]["trip_duration"]["value"],3)

    def test_saved_preferences_reused(self):
        TravelPreferenceProfile.objects.create(user=self.user,preferences={"origin":fact("Pune"),"avoid_expressways":fact(True),"preferred_transport":fact("ride")})
        session = new_session(self.user)
        self.assertEqual(value(session.state,"origin"),"Pune")
        self.assertTrue(value(session.state,"avoid_expressways"))
        self.assertEqual(value(session.state,"transport_mode"),"ride")

    def test_expired_nested_offers_and_forecast_age_on_read(self):
        old = (timezone.now()-timedelta(minutes=1)).isoformat()
        candidate = {"weather_result":{"expires_at":old,"freshness":"LIVE","payload":{}},"weather":{},"weather_proposals":[{}],
                     "hotels_result":{"expires_at":old,"freshness":"LIVE","payload":{"options":[{"availability":"available"}]}}}
        result = age_saved_facts({"candidates":[candidate]})["candidates"][0]
        self.assertEqual(result["weather_proposals"],[])
        self.assertEqual(result["weather"]["freshness"],"CACHED")
        self.assertIn("expired",result["hotels_result"]["payload"]["options"][0]["availability"])

    def test_place_actions_and_quota_dashboard_are_owner_and_staff_scoped(self):
        session = new_session(self.user)
        session.candidates = [{"name":"Ziro"}]
        session.save()
        other = get_user_model().objects.create_user("unrelated")
        self.client.force_login(other)
        url = f"/api/mobility/planner/sessions/{session.id}/"
        self.assertEqual(self.client.post(url,json.dumps({"action":"place","place_key":"name:ziro","event":"visited"}),content_type="application/json").status_code,404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/mobility/planner/providers/").status_code,403)
        self.assertEqual(self.client.post(url,json.dumps({"action":"place","place_key":"name:ziro","event":"visited"}),content_type="application/json").status_code,200)
        self.assertTrue(UserDestinationHistory.objects.get(user=self.user).events.get("visited"))
        self.user.is_staff = True
        self.user.save()
        response = self.client.get("/api/mobility/planner/providers/")
        self.assertEqual(response.status_code,200)
        self.assertIn("configuration",response.json())
        configured = {(p["provider"], p["category"]) for p in response.json()["configuration"]}
        self.assertTrue({("open_meteo", "weather"), ("duffel", "flights"), ("brave", "web"),
                         ("searxng", "web"), ("wikivoyage", "web"), ("wikivoyage", "destinations")} <= configured)
        with patch.dict("os.environ", {"TRAVEL_BRAVE_API_KEY": "secret-test-sentinel"}):
            self.assertNotIn("secret-test-sentinel", self.client.get("/api/mobility/planner/providers/").content.decode())
