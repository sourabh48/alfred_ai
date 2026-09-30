import json
from copy import deepcopy
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as ModelValidationError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.mobility.models import (BikeProfile, TravelPlan, TravelPlanningSession, TravelPreferenceProfile,
                                  TravelResearchEvidence, TravelResearchSession, TripLog, TripPhoto)
from apps.mobility.services.travel_conversation import extract, new_session, save_plan, send_message
from apps.mobility.services.travel_discovery import budget_for, candidates_for, fact, history_for, learn, value
from apps.mobility.services.travel_itinerary import build_itinerary, edit_itinerary
from apps.mobility.services.travel_research import queue_research, run_research
from apps.mobility.services.travel.providers.base import ProviderResult


def weather_fixture(*args, **kwargs):
    now = timezone.now()
    return ProviderResult("open_meteo","weather",success=True,status="ok",freshness="LIVE",confidence="LIKELY",
        payload={"average_min_temp":20,"average_max_temp":26,"precipitation_total":2,"wind_max":12,"days":[]},
        source_url="https://open-meteo.com/en/docs",retrieved_at=now.isoformat(),verified_at=now.isoformat(),expires_at=(now+timedelta(hours=2)).isoformat())


class TravelPlannerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("travel_test", password="Test12345!", city="Bengaluru")
        self.other = get_user_model().objects.create_user("other_traveller", password="Test12345!")
        self.client.force_login(self.user)
        self.dispatch = patch("apps.mobility.services.travel_research.dispatch").start()
        self.addCleanup(patch.stopall)
        patch("apps.mobility.services.travel.research.weather_result", side_effect=weather_fixture).start()
        patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("Tests must mock travel providers")).start()
        self.today = timezone.localdate()

    def post(self, url, body):
        return self.client.post(url, json.dumps(body), content_type="application/json")

    def ready(self):
        s = new_session(self.user)
        s = send_message(s.id, self.user, f"{self.today+timedelta(days=2)} to {self.today+timedelta(days=5)}. Budget ₹15000. Bike trip, mountains and photography.")
        s = send_message(s.id, self.user, "Yes use that")
        return s

    def chosen(self):
        s = self.ready()
        run_research(s.research_runs.first().id)
        s.refresh_from_db()
        s = send_message(s.id, self.user, "Choose "+s.candidates[0]["name"])
        return send_message(s.id, self.user, "Build itinerary")

    def test_draft_optional_destination_and_dates(self):
        for status in ("draft", "researching", "suggestions_ready"):
            r = self.post("/api/mobility/travel-plans/", {"title":"October weekend", "status":status})
            self.assertEqual(r.status_code, 201, r.content)
            self.assertIsNone(r.json()["destination"])
            TravelPlan.objects.get(pk=r.json()["id"]).full_clean()

    def test_planned_and_confirmed_require_core_details(self):
        for status in ("planned", "confirmed", "booked"):
            r = self.post("/api/mobility/travel-plans/", {"title":"Not ready", "status":status})
            self.assertEqual(r.status_code, 400)
        with self.assertRaises(ModelValidationError):
            TravelPlan(user=self.user, title="Missing", status="planned").full_clean()

    def test_exact_acceptance_extraction(self):
        state, _ = extract({}, "I have holiday from 2 October to 5 October. Budget is ₹15,000. Suggest me somewhere.")
        self.assertEqual(value(state,"trip_duration"), 4)
        self.assertEqual(value(state,"budget"), 15000)
        self.assertNotIn("selected_destination", state)
        self.assertEqual(state["budget"]["source"], "user_message")
        self.assertTrue(state["budget"]["confirmed_by_user"])

    def test_configured_origin_is_reused_without_repeated_question(self):
        s = new_session(self.user)
        self.assertFalse(s.state["origin"]["confirmed_by_user"])
        s = send_message(s.id, self.user, "3 days ₹12000")
        self.assertNotIn("Use that?", s.messages.last().text)
        self.assertTrue(s.research_runs.exists())
        s = send_message(s.id, self.user, "Yes use that")
        self.assertTrue(s.research_runs.exists())

    def test_missing_origin_asked_progressively(self):
        s = new_session(self.other)
        s = send_message(s.id, self.other, "3 days ₹12000")
        self.assertIn("starting from", s.messages.last().text)
        s = send_message(s.id, self.other, "Bengaluru")
        self.assertEqual(value(s.state, "origin"), "Bengaluru")
        self.assertTrue(s.research_runs.exists())

    def test_missing_dates_asks_duration(self):
        s = send_message(new_session(self.user).id, self.user, "Somewhere peaceful")
        self.assertIn("How many days", s.messages.last().text)

    def test_budget_optional_with_tier(self):
        s = send_message(new_session(self.other).id, self.other, "3 days from Bengaluru")
        self.assertIn("premium", s.messages.last().text)
        s = send_message(s.id, self.other, "Budget options")
        self.assertTrue(s.research_runs.exists())

    def test_conversation_persists_and_limits_options(self):
        s = self.ready()
        s = TravelPlanningSession.objects.get(pk=s.id)
        self.assertGreater(s.messages.count(), 3)
        self.assertGreaterEqual(len(s.candidates), 2)
        self.assertLessEqual(len(s.candidates), 3)
        self.assertTrue(all(c["why"] and c["budget"] for c in s.candidates))
        self.assertIsNone(value(s.state, "selected_destination"))

    def test_history_records_repeated_recent_trips(self):
        for _ in range(2):
            TravelPlan.objects.create(user=self.user, title="Coorg", destination="Coorg", start_date=self.today-timedelta(days=5), end_date=self.today-timedelta(days=2), status="completed")
        h = history_for(self.user)
        self.assertEqual(h["visits"]["Coorg"], 2)
        self.assertEqual(h["recent"]["Coorg"], 2)
        state = {"origin":fact("Bengaluru"),"trip_duration":fact(4),"budget":fact(20000),"novelty":fact("mostly_new")}
        new = candidates_for(self.user,state)
        state["novelty"] = fact("mostly_familiar")
        familiar = candidates_for(self.user,state)
        self.assertEqual(familiar[0]["name"],"Coorg")
        self.assertNotEqual(new[0]["name"],"Coorg")

    def test_explicit_preference_influences_ranking(self):
        learn(self.user,"beaches",True,"settings",1,True)
        state={"origin":fact("Bengaluru"),"trip_duration":fact(6),"budget":fact(50000)}
        results=candidates_for(self.user,state)
        self.assertTrue(any("beaches" in c["factors"]["Preferences"] for c in results))

    def test_compare_preserves_selection_and_candidates(self):
        s=self.ready(); before=deepcopy(s.candidates)
        s=send_message(s.id,self.user,"Compare destinations")
        self.assertEqual(s.candidates,before)
        self.assertIn("Compare",s.messages.last().text)

    def test_option_reference_and_destination_selection_do_not_change_origin(self):
        s=self.ready(); name=s.candidates[1]["name"]
        s=send_message(s.id,self.user,"What about option 2?")
        self.assertIsNone(value(s.state,"selected_destination"))
        self.assertEqual(value(s.state,"referenced_destination"),name)
        s=send_message(s.id,self.user,"Choose that")
        self.assertEqual(value(s.state,"selected_destination"),name)
        self.assertEqual(value(s.state,"origin"),"Bengaluru")
        self.assertEqual(s.itinerary,{})

    def test_itinerary_only_after_selection(self):
        s=self.ready()
        s=send_message(s.id,self.user,"Build itinerary")
        self.assertEqual(s.itinerary,{})
        s=self.chosen()
        self.assertEqual(len(s.itinerary["days"]),4)
        for key in ("route","budget","weather","packing","sources"):
            self.assertIn(key,s.itinerary)

    def test_relax_one_day_retains_other_days(self):
        s=self.chosen(); before=deepcopy(s.itinerary)
        s=send_message(s.id,self.user,"Day 2 is too busy. Make it relaxed.")
        self.assertEqual(s.itinerary["days"][1]["pace"],"relaxed")
        for i in (0,2,3): self.assertEqual(s.itinerary["days"][i],before["days"][i])
        self.assertLessEqual(s.itinerary["budget"]["expected"],before["budget"]["expected"])
        self.assertEqual(sum(s.itinerary["budget"]["categories"].values()),s.itinerary["budget"]["expected"])
        self.assertEqual(sum(d["estimated_cost"] for d in s.itinerary["days"]),s.itinerary["budget"]["expected"])

    def test_day_edit_after_hotel_research_survives_recheck(self):
        s = self.chosen()
        s = send_message(s.id, self.user, "Show cheaper hotels")
        self.assertEqual(run_research(s.research_runs.first().id)["status"], "ready")
        s.refresh_from_db()
        before = deepcopy(s.itinerary)
        s = send_message(s.id, self.user, "Day 2 is too busy. Make it relaxed.")
        for index in (0, 2, 3):
            self.assertEqual(s.itinerary["days"][index], before["days"][index])
        edited = deepcopy(s.itinerary)
        s = send_message(s.id, self.user, "Recheck trip")
        self.assertEqual(run_research(s.research_runs.first().id)["status"], "ready")
        s.refresh_from_db()
        self.assertEqual(s.itinerary["days"], edited["days"])
        self.assertEqual(s.itinerary["budget"]["expected"], edited["budget"]["expected"])
        self.assertEqual(sum(d["estimated_cost"] for d in s.itinerary["days"]), s.itinerary["budget"]["expected"])
        self.assertEqual(s.itinerary["external_links"], edited["external_links"])

    def test_budget_sum_range_and_adaptation(self):
        s=self.ready(); b=budget_for({**s.state,"budget":fact(500)},s.candidates[0])
        self.assertEqual(sum(b["categories"].values()),b["expected"])
        self.assertLess(b["minimum"],b["expected"])
        self.assertGreater(b["comfortable"],b["expected"])
        self.assertTrue(b["adaptations"])

    def test_budget_edit_decreases_cost(self):
        s=self.chosen(); before=s.itinerary["budget"]["expected"]
        s=send_message(s.id,self.user,"Reduce the budget")
        self.assertLess(s.itinerary["budget"]["expected"],before)
        self.assertEqual(sum(s.itinerary["budget"]["categories"].values()),s.itinerary["budget"]["expected"])
        self.assertEqual(sum(d["estimated_cost"] for d in s.itinerary["days"]),s.itinerary["budget"]["expected"])

    def test_budget_edit_rounds_half_up_and_preserves_totals(self):
        session = self.chosen()
        state = {**session.state, "trip_duration": fact(2), "number_of_travelers": fact(1),
                 "budget": fact(20000)}
        original = build_itinerary(state, {**session.candidates[0], "nightly": 1006})
        before = deepcopy(original)
        self.assertEqual(original["budget"]["categories"]["Stay"], 1006)

        edited, _ = edit_itinerary(original, "Reduce the budget", state)

        self.assertEqual(edited["budget"]["categories"]["Stay"], 755)  # 754.50 rounds up.
        self.assertEqual(edited["budget"]["expected"], before["budget"]["expected"] - 251)
        self.assertEqual(edited["budget"]["categories"]["Emergency Buffer"],
                         before["budget"]["categories"]["Emergency Buffer"])
        self.assertEqual(edited["days"][-1], before["days"][-1])
        self.assertEqual(sum(day["estimated_cost"] for day in edited["days"]), edited["budget"]["expected"])
        self.assertEqual(sum(edited["budget"]["categories"].values()), edited["budget"]["expected"])
        for total, item_key in (("expected", "expected"), ("minimum", "low"), ("comfortable", "high")):
            self.assertEqual(edited["budget"][total], sum(item[item_key] for item in edited["budget"]["line_items"]))
        stay = next(item for item in edited["budget"]["line_items"] if item["category"] == "Stay")
        self.assertEqual((stay["low"], stay["expected"], stay["high"]), (604, 755, 906))
        self.assertEqual(original, before)
        self.assertEqual(json.loads(json.dumps(edited))["budget"], edited["budget"])
        legacy = deepcopy(original)
        del legacy["budget"]["line_items"]
        edited_legacy, _ = edit_itinerary(legacy, "Reduce the budget", state)
        self.assertEqual(edited_legacy["budget"]["categories"]["Stay"], 755)
        self.assertEqual(edited_legacy["budget"]["low"], edited_legacy["budget"]["minimum"])
        self.assertEqual(edited_legacy["budget"]["high"], edited_legacy["budget"]["comfortable"])

    def test_edit_normalizes_decimal_budget_target_like_initial_budget(self):
        session = self.chosen()
        state = {**session.state, "budget": fact("333.50"), "budget_scope": fact("per_person"),
                 "number_of_travelers": fact(3)}
        edited, _ = edit_itinerary(session.itinerary, "Add one waterfall", state)
        self.assertEqual(edited["budget"]["target"], 1002)
        self.assertIsInstance(edited["budget"]["target"], int)
        self.assertEqual(edited["budget"]["target"], budget_for(state, session.candidates[0])["target"])
        self.assertEqual(edited["budget"]["over_budget"], max(0, edited["budget"]["expected"] - 1002))

    def test_add_day_updates_window(self):
        s=self.chosen(); end=value(s.state,"available_end_date")
        s=send_message(s.id,self.user,"Add one day")
        self.assertEqual(len(s.itinerary["days"]),5)
        self.assertEqual(date.fromisoformat(value(s.state,"available_end_date")),date.fromisoformat(end)+timedelta(days=1))

    def test_vehicle_owner_and_real_specs_only(self):
        s=self.ready()
        bike=BikeProfile.objects.create(user=self.user,display_name="My bike",model_name="Test",expected_mileage_kmpl=35,fuel_tank_capacity_l=12)
        r=self.post(f"/api/mobility/planner/sessions/{s.id}/",{"action":"vehicle","vehicle_id":bike.id})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["state"]["vehicle_mileage"]["value"],35)
        bike.user=self.other;bike.save()
        self.assertEqual(self.post(f"/api/mobility/planner/sessions/{s.id}/",{"action":"vehicle","vehicle_id":bike.id}).status_code,404)

    def test_research_persistence_sources_and_idempotency(self):
        s=self.ready(); run=s.research_runs.first()
        self.assertEqual(run.status,"queued")
        result=run_research(run.id)
        self.assertEqual(result["status"],"ready")
        self.assertTrue(run.evidence.filter(data_type="weather",confidence="LIKELY").exists())
        self.assertTrue(run.evidence.exclude(source_url="").exists())
        count=run.evidence.count(); run_research(run.id)
        self.assertEqual(run.evidence.count(),count)

    def test_expired_lease_recovers_after_restart(self):
        s=self.ready(); run=s.research_runs.first()
        run.status="weather";run.lease_until=timezone.now()-timedelta(minutes=1);run.lease_token="dead-worker";run.save()
        self.assertEqual(run_research(run.id)["status"],"ready")
        run.refresh_from_db();self.assertIsNone(run.lease_until)

    def test_live_lease_prevents_duplicate_worker(self):
        s=self.ready(); run=s.research_runs.first()
        run.lease_until=timezone.now()+timedelta(minutes=1);run.save()
        self.assertEqual(run_research(run.id)["status"],"already_claimed_or_finished")

    def test_failed_source_produces_offline_suggestions(self):
        s=self.ready();run=s.research_runs.first()
        with patch("apps.mobility.services.travel.research.weather_result",side_effect=TimeoutError):
            self.assertEqual(run_research(run.id)["status"],"ready")
        run.refresh_from_db()
        self.assertIn("couldn't verify",run.summary)
        self.assertTrue(run.evidence.filter(data_type="weather",confidence="UNKNOWN").exists())

    def test_old_request_cannot_overwrite_new_preferences(self):
        s=self.ready();run=s.research_runs.first()
        s.revision+=1;s.save()
        self.assertEqual(run_research(run.id)["status"],"superseded")

    def test_stale_evidence_refresh_when_future_plan_reopened(self):
        s=self.chosen();plan=save_plan(s)
        run=s.research_runs.first()
        run.evidence.update(valid_until=timezone.now()-timedelta(hours=1))
        r=self.post("/api/mobility/planner/sessions/",{"plan_id":plan.id})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()["research"]["status"],"queued")

    def test_save_plan_and_reopen_preserves_context(self):
        s=self.chosen();plan=save_plan(s)
        self.assertEqual(plan.destination,value(s.state,"selected_destination"))
        self.assertEqual(plan.itinerary,s.itinerary)
        self.assertEqual(plan.status,"planned")
        r=self.post("/api/mobility/planner/sessions/",{"plan_id":plan.id})
        self.assertEqual(r.json()["id"],s.id)
        self.assertGreater(len(r.json()["messages"]),3)

    def test_save_draft_before_selection(self):
        s=new_session(self.user);plan=save_plan(s,draft=True)
        self.assertIsNone(plan.destination)
        self.assertIsNone(plan.start_date)
        self.assertEqual(plan.status,"draft")

    def test_ownership_isolation_all_session_actions(self):
        s=self.ready();self.client.force_login(self.other)
        url=f"/api/mobility/planner/sessions/{s.id}/"
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertEqual(self.post(url,{"text":"Choose option 1"}).status_code,404)
        self.assertEqual(self.post(url,{"action":"save","draft":True}).status_code,404)
        self.assertEqual(self.client.get("/api/mobility/planner/sessions/").json()["sessions"],[])

    def test_post_trip_feedback_and_preference_reset(self):
        plan=TravelPlan.objects.create(user=self.user,title="Past trip",destination="Coorg",start_date=self.today-timedelta(days=5),end_date=self.today-timedelta(days=2),status="completed")
        r=self.post("/api/mobility/planner/feedback/",{"plan_id":plan.id,"rating":"loved","liked":["photography"]})
        self.assertEqual(r.status_code,200,r.content)
        learn(self.user,"mountains",True,"explicit",1,True)
        p=TravelPreferenceProfile.objects.get(user=self.user)
        self.assertFalse(p.preferences["photography"]["confirmed_by_user"])
        r=self.client.patch("/api/mobility/planner/preferences/",json.dumps({"action":"reset"}),content_type="application/json")
        self.assertNotIn("photography",r.json()["preferences"])
        self.assertIn("mountains",r.json()["preferences"])

    def test_photo_association_requires_owner_confirmation(self):
        past=self.today-timedelta(days=5)
        plan=TravelPlan.objects.create(user=self.user,title="Coorg trip",destination="Coorg",start_date=past,end_date=past+timedelta(days=3),status="completed")
        photo=TripPhoto.objects.create(user=self.user,image="trip_photos/test.jpg",location_name="Coorg",taken_at=timezone.make_aware(datetime.combine(past,datetime.min.time())))
        r=self.client.get("/api/mobility/planner/media-suggestions/")
        self.assertEqual(r.json()["suggestions"][0]["photo_id"],photo.id)
        photo.refresh_from_db();self.assertIsNone(photo.travel_plan_id)
        self.client.force_login(self.other)
        self.assertEqual(self.post("/api/mobility/planner/media-suggestions/",{"photo_id":photo.id,"plan_id":plan.id,"action":"add"}).status_code,404)
        self.client.force_login(self.user)
        self.assertEqual(self.post("/api/mobility/planner/media-suggestions/",{"photo_id":photo.id,"plan_id":plan.id,"action":"add"}).status_code,200)
        photo.refresh_from_db();self.assertEqual(photo.travel_plan_id,plan.id)

    def test_legacy_destination_free_preview_starts_session(self):
        r=self.post("/api/mobility/travel-advisor/preview/",{"start_date":str(self.today),"end_date":str(self.today+timedelta(days=3)),"budget":15000})
        self.assertEqual(r.status_code,201,r.content)
        self.assertIn("messages",r.json())

    def test_invalid_dates_do_not_persist_message_or_state(self):
        s=new_session(self.user);before=s.messages.count()
        r=self.post(f"/api/mobility/planner/sessions/{s.id}/",{"text":"31 February to 4 March"})
        self.assertEqual(r.status_code,400)
        self.assertEqual(s.messages.count(),before)

    def test_dashboard_handles_draft_and_unassigned_photo(self):
        TravelPlan.objects.create(user=self.user,title="Draft",status="draft")
        TripPhoto.objects.create(user=self.user,image="trip_photos/test.jpg",latitude=12,longitude=77)
        r=self.client.get("/api/mobility/dashboard/")
        self.assertEqual(r.status_code,200,r.content)

    def test_research_queries_do_not_include_private_context(self):
        s=self.ready();run=s.research_runs.first();run.deep=True;run.save()
        with patch("apps.mobility.services.travel.research.query_with_fallback",return_value=ProviderResult("fixture","web",error="offline")) as search:
            run_research(run.id)
        self.assertTrue(search.called)
        for call in search.call_args_list:
            query=str(call.args[1])
            for private in (self.user.username,"15000"):
                self.assertNotIn(private,query)
            self.assertLessEqual(set(call.args[1]),{"destination","origin","topic","date","mode"})

    def test_media_preferences_require_opt_in_and_favorite(self):
        photo=TripPhoto.objects.create(user=self.user,image="trip_photos/test.jpg",preference_tags=["photography"])
        from apps.mobility.services.travel_media import learn_from_favorite
        learn_from_favorite(photo)
        p=TravelPreferenceProfile.objects.get(user=self.user)
        self.assertNotIn("photography",p.preferences)
        p.media_learning_enabled=True;p.save()
        learn_from_favorite(photo)
        p.refresh_from_db();self.assertNotIn("photography",p.preferences)
        photo.is_favorite=True;photo.save();learn_from_favorite(photo)
        p.refresh_from_db()
        self.assertFalse(p.preferences["photography"]["confirmed_by_user"])
        self.assertEqual(p.preferences["photography"]["confidence"],.45)

    def test_photo_gps_proposes_but_does_not_auto_associate(self):
        from apps.mobility.planner_views import photo_matches
        past=self.today-timedelta(days=5)
        p=TravelPlan.objects.create(user=self.user,title="Hills",destination="Chikmagalur",start_date=past,end_date=past+timedelta(days=3),status="completed")
        photo=TripPhoto.objects.create(user=self.user,image="trip_photos/gps.jpg",latitude=13.316,longitude=75.773,taken_at=timezone.make_aware(datetime.combine(past,datetime.min.time())))
        self.assertTrue(photo_matches(photo,p))
        self.assertIsNone(photo.travel_plan_id)
        self.post("/api/mobility/planner/media-suggestions/",{"photo_id":photo.id,"plan_id":p.id,"action":"ignore"})
        self.assertEqual(self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"],[])

    def test_pillion_question_is_not_confirmation(self):
        s=self.chosen();s=send_message(s.id,self.user,"Can I do that with pillion?")
        self.assertFalse(s.state["pillion"]["confirmed_by_user"])
        s=send_message(s.id,self.user,"Include pillion")
        self.assertTrue(s.state["pillion"]["confirmed_by_user"])
        self.assertEqual(value(s.state,"number_of_travelers"),2)

    def test_pretrip_recheck_retains_edits_and_only_reports_changes(self):
        s=self.chosen();s=send_message(s.id,self.user,"Make day 2 relaxed")
        before=deepcopy(s.itinerary["days"])
        run=queue_research(s,recheck=True)
        run_research(run.id);s.refresh_from_db();run.refresh_from_db()
        self.assertEqual(s.itinerary["days"],before)
        self.assertEqual(run.changes,[])
        self.assertIn("No meaningful change",run.summary)

    def test_failed_job_and_retry(self):
        s=self.ready();run=s.research_runs.first()
        with patch("apps.mobility.services.travel_research.candidates_for",side_effect=RuntimeError):
            self.assertEqual(run_research(run.id)["status"],"failed")
        s=send_message(s.id,self.user,"Retry research")
        self.assertNotEqual(s.research_runs.first().id,run.id)

    def test_deep_request_upgrades_queued_job(self):
        s=self.ready();run=s.research_runs.first()
        result=queue_research(s,deep=True)
        self.assertEqual(result.id,run.id)
        self.assertTrue(result.deep)

    def test_details_edit_invalidates_itinerary_and_syncs_session(self):
        s=self.chosen();plan=save_plan(s)
        r=self.client.patch(f"/api/mobility/travel-plans/{plan.id}/",json.dumps({"budget":12000}),content_type="application/json")
        self.assertEqual(r.status_code,200,r.content)
        s.refresh_from_db()
        self.assertEqual(value(s.state,"budget"),12000)
        self.assertEqual(s.itinerary,{})

    def test_reset_user_data_removes_private_conversations(self):
        from apps.users.services import clear_user_fed_data
        s=self.ready();other=new_session(self.other)
        clear_user_fed_data(self.user)
        self.assertFalse(TravelPlanningSession.objects.filter(pk=s.id).exists())
        self.assertTrue(TravelPlanningSession.objects.filter(pk=other.id).exists())


class TravelMigrationTests(TransactionTestCase):
    def test_existing_plan_fields_and_related_records_survive(self):
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor
        before=("mobility","0008_bikeservicerecord_source_document")
        after=("mobility","0012_travel_bus_mode")
        executor=MigrationExecutor(connection)
        executor.migrate([before])
        old=executor.loader.project_state([before]).apps
        try:
            # Only mobility is rolled back; the users schema remains current.
            user=get_user_model().objects.create(username="migration_owner")
            plan=old.get_model("mobility","TravelPlan").objects.create(user_id=user.id,title="Existing Coorg trip",destination="Coorg",start_date=date(2026,9,1),end_date=date(2026,9,4),budget=15000,notes="Keep my notes")
            old.get_model("mobility","TripLog").objects.create(user_id=user.id,travel_plan_id=plan.id,log_date=date(2026,9,2),title="Existing log")
            pk=plan.id
        finally:
            MigrationExecutor(connection).migrate([after])
        restored=TravelPlan.objects.get(pk=pk)
        self.assertEqual(restored.destination,"Coorg")
        self.assertEqual(restored.notes,"Keep my notes")
        self.assertEqual(restored.budget,15000)
        self.assertEqual(restored.duration_days,4)
        self.assertEqual(restored.logs.get().title,"Existing log")
        self.assertEqual(restored.status,"planned")
