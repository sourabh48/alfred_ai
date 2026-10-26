"""Synthetic owned desktop edits; no providers, financial writes or production data."""
from copy import deepcopy
from uuid import uuid4

from django.test import Client, TestCase

from apps.mobility.models import TravelPlanningSession
from apps.mobility.services.travel.editor import apply_edit, EditConflict
from apps.mobility.services.travel_discovery import fact
from tests import test_travel_multistop as fixtures


class TravelItineraryEditorTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)
        fixtures.TravelMultiStopTests.setUp(self)
    ready = fixtures.TravelMultiStopTests.ready
    researched = fixtures.TravelMultiStopTests.researched
    set_stops = fixtures.TravelMultiStopTests.set_stops
    multi = fixtures.TravelMultiStopTests.multi

    def payload(self, session):
        return self.client.get(f"/api/mobility/planner/sessions/{session.pk}/").json()

    def edit(self, session, operation, **fields):
        data = {"action": "itinerary_edit", "operation": operation, "revision": session.revision,
                "request_id": str(uuid4()), **fields}
        result = self.client.post(f"/api/mobility/planner/sessions/{session.pk}/", data, content_type="application/json")
        session.refresh_from_db()
        return result

    def test_crud_undo_preserves_unrelated_data_and_invalidates_estimates(self):
        session, _ = self.multi()
        session.itinerary["owner_note"] = {"text": "Synthetic retained note"}; session.save()
        original = self.payload(session)["itinerary"]
        day = original["days"][0]
        response = self.edit(session, "add", day_id=day["id"], fields={"title": "Synthetic accessible museum"})
        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()["itinerary"]["days"][0]["items"][-1]
        identity = item["id"]
        self.assertEqual(session.itinerary["owner_note"], original["owner_note"])
        self.assertEqual(session.itinerary["packing"], original["packing"])
        self.assertEqual(session.itinerary["budget"]["expected"], original["budget"]["expected"])
        self.assertEqual(session.itinerary["budget"]["status"], "needs_recalculation")
        self.assertEqual(session.itinerary["route"]["confidence"], "UNKNOWN")
        self.assertIsNone(session.itinerary["route"]["distance_km_total"])
        self.assertEqual(self.edit(session, "update", day_id=day["id"], item_id=identity,
            fields={"title": "Corrected museum", "duration": "45 minutes"}).status_code, 200)
        self.assertEqual(session.itinerary["days"][0]["items"][-1]["id"], identity)
        self.assertEqual(self.edit(session, "remove", day_id=day["id"], item_id=identity).status_code, 200)
        self.assertNotIn(identity, [i["id"] for i in session.itinerary["days"][0]["items"]])
        self.assertEqual(self.edit(session, "undo").status_code, 200)
        self.assertEqual(session.itinerary["days"][0]["items"][-1]["title"], "Corrected museum")
        self.assertEqual(len(self.payload(session)["itinerary_editor"]["history"]), 4)

    def test_move_across_days_retains_identity_and_metadata(self):
        session, _ = self.multi()
        before = self.payload(session)["itinerary"]
        first, second = before["days"][:2]
        item = next(i for i in first["items"] if i["type"] != "travel")
        result = self.edit(session, "move", day_id=second["id"], item_id=item["id"], before_id=second["items"][0]["id"])
        self.assertEqual(result.status_code, 200, result.content)
        self.assertEqual(session.itinerary["days"][1]["items"][0], item)
        self.assertEqual(session.itinerary["days"][0]["stay"], first["stay"])
        self.assertEqual(session.itinerary["days"][1]["meals"], second["meals"])
        self.assertEqual([d["id"] for d in session.itinerary["days"]], [d["id"] for d in before["days"]])
        self.assertEqual(self.edit(session, "undo").status_code, 200)
        self.assertEqual(self.payload(session)["itinerary"], before)

    def test_stop_order_preserves_edited_activities_allocations_ids_and_dates(self):
        session, _ = self.multi()
        initial = self.payload(session)
        day = initial["itinerary"]["days"][0]
        self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title": "Retained local stop activity"}).status_code, 200)
        before = self.payload(session)
        order = [s["id"] for s in reversed(before["itinerary_editor"]["stops"])]
        result = self.edit(session, "order_stops", stops=order)
        self.assertEqual(result.status_code, 200, result.content)
        after = result.json()
        self.assertEqual([s["id"] for s in after["itinerary_editor"]["stops"]], order)
        self.assertEqual({d["id"] for d in after["itinerary"]["days"]}, {d["id"] for d in before["itinerary"]["days"]})
        self.assertEqual([d["date"] for d in after["itinerary"]["days"]], [d["date"] for d in before["itinerary"]["days"]])
        self.assertTrue(any(i["title"] == "Retained local stop activity" for d in after["itinerary"]["days"] for i in d["items"]))
        self.assertEqual(self.edit(session, "undo").status_code, 200)
        self.assertEqual(self.payload(session)["itinerary"], before["itinerary"])

    def test_replay_is_idempotent_and_reused_identity_or_stale_revision_conflicts(self):
        session, _ = self.multi()
        day = self.payload(session)["itinerary"]["days"][0]
        data = dict(action="itinerary_edit", operation="add", revision=session.revision,
            request_id=str(uuid4()), day_id=day["id"], fields={"title": "Once only"})
        first = self.edit(session, "add", **{k: v for k, v in data.items() if k not in {"action", "operation"}})
        self.assertEqual(first.status_code, 200)
        revision, before = session.revision, deepcopy(session.itinerary)
        self.assertEqual(self.edit(session, "add", **{k: v for k, v in data.items() if k not in {"action", "operation"}}).status_code, 200)
        self.assertEqual(session.revision, revision); self.assertEqual(session.itinerary, before)
        data["fields"] = {"title": "Different use"}
        self.assertEqual(self.edit(session, "add", **{k: v for k, v in data.items() if k not in {"action", "operation"}}).status_code, 409)
        self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title": "Stale"}, revision=revision-1).status_code, 409)
        self.assertEqual(session.itinerary, before)

    def test_compare_and_swap_rejects_a_concurrent_saved_copy(self):
        session, _ = self.multi()
        stale = TravelPlanningSession.objects.get(pk=session.pk)
        day = self.payload(session)["itinerary"]["days"][0]
        self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title": "Winning edit"}).status_code, 200)
        with self.assertRaises(EditConflict):
            apply_edit(stale, dict(operation="add", revision=stale.revision, request_id=str(uuid4()),
                day_id=day["id"], fields={"title": "Losing edit"}))
        self.assertNotIn("Losing edit", str(TravelPlanningSession.objects.get(pk=session.pk).itinerary))

    def test_owner_csrf_invalid_fields_and_travel_leg_are_fail_closed(self):
        session, _ = self.multi()
        day = self.payload(session)["itinerary"]["days"][0]
        before = deepcopy(session.itinerary)
        for fields in ({"title": ""}, {"title": "x"*241}, {"title": "Valid", "cost": 999}, {"priority": "Guaranteed"}):
            self.assertEqual(self.edit(session, "add", day_id=day["id"], fields=fields).status_code, 400)
        self.assertEqual(self.edit(session, "remove", day_id=day["id"], item_id=day["items"][0]["id"]).status_code, 400)
        self.assertEqual(session.itinerary, before)
        self.client.force_login(self.other)
        self.assertEqual(self.edit(session, "undo").status_code, 404)
        client = Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post(f"/api/mobility/planner/sessions/{session.pk}/", {"action":"itinerary_edit"}).status_code, 403)

    def test_save_reopen_private_history_and_context_change(self):
        session, _ = self.multi()
        day = self.payload(session)["itinerary"]["days"][0]
        self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title":"Saved activity"}).status_code, 200)
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        self.assertEqual(self.client.post(url, {"action":"save", "revision":session.revision-1}, content_type="application/json").status_code, 409)
        self.assertEqual(self.client.post(url, {"action":"save", "revision":session.revision}, content_type="application/json").status_code, 200)
        session.refresh_from_db(); session.plan.refresh_from_db()
        self.assertEqual(session.plan.itinerary, session.itinerary)
        payload = self.payload(session)
        self.assertNotIn("_itinerary_editor", payload["state"])
        self.assertNotIn("undo", payload["itinerary_editor"])
        self.assertTrue(payload["itinerary_editor"]["can_undo"])
        self.assertEqual(payload["itinerary"]["days"][0]["items"][-1]["title"], "Saved activity")
        session.state["budget"] = fact(25000); session.revision += 1; session.save()
        before = deepcopy(session.itinerary)
        self.assertFalse(self.payload(session)["itinerary_editor"]["can_undo"])
        self.assertEqual(self.edit(session, "undo").status_code, 409)
        self.assertEqual(session.itinerary, before)

    def test_legacy_chat_mutation_rejects_the_previous_desktop_revision(self):
        session, _ = self.multi()
        day = self.payload(session)["itinerary"]["days"][1]
        revision = session.revision
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        result = self.client.post(url, {"text":"Make day 2 relaxed"}, content_type="application/json")
        self.assertEqual(result.status_code, 200)
        session.refresh_from_db(); self.assertGreater(session.revision, revision)
        before = deepcopy(session.itinerary)
        self.assertEqual(self.edit(session, "add", revision=revision, day_id=day["id"], fields={"title":"Old tab"}).status_code, 409)
        self.assertEqual(session.itinerary, before)

    def test_repeated_legacy_activity_addition_cannot_collide_with_shifted_ids(self):
        session, _ = self.multi()
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        self.assertEqual(self.client.post(url, {"text":"Add one waterfall"}, content_type="application/json").status_code, 200)
        session.refresh_from_db()
        day = self.payload(session)["itinerary"]["days"][1]
        waterfall = day["items"][-1]
        self.assertEqual(self.edit(session, "update", day_id=day["id"], item_id=waterfall["id"], fields={"duration":"Two hours"}).status_code, 200)
        earlier = next(i for i in day["items"][:-1] if i["type"] != "travel")
        self.assertEqual(self.edit(session, "remove", day_id=day["id"], item_id=earlier["id"]).status_code, 200)
        result = self.client.post(url, {"text":"Add one waterfall"}, content_type="application/json")
        self.assertEqual(result.status_code, 200, result.content)
        items = result.json()["itinerary"]["days"][1]["items"]
        self.assertEqual(len({i["id"] for i in items}), len(items))
        self.assertIn(waterfall["id"], [i["id"] for i in items])
        self.assertEqual(sum(i["title"] == waterfall["title"] for i in items), 2)

    def test_history_and_activity_limits_are_bounded_without_changing_the_plan(self):
        session, _ = self.multi()
        day = self.payload(session)["itinerary"]["days"][0]
        for index in range(11):
            self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title":f"Synthetic block {index}"}).status_code, 200)
        history = session.state["_itinerary_editor"]["value"]
        self.assertLessEqual(len(history["undo"]), 10)
        self.assertEqual(len(history["log"]), 11)
        while len(session.itinerary["days"][0]["items"]) < 30:
            self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title":"Another bounded block"}).status_code, 200)
        before = deepcopy(session.itinerary)
        self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title":"Excess block"}).status_code, 400)
        self.assertEqual(session.itinerary, before)

    def test_research_publication_advances_revision_and_preserves_manual_activities(self):
        from apps.mobility.services.travel_research import queue_research, run_research
        session, _ = self.multi()
        day = self.payload(session)["itinerary"]["days"][0]
        self.assertEqual(self.edit(session, "add", day_id=day["id"], fields={"title":"Keep across research"}).status_code, 200)
        revision = session.revision
        run = queue_research(session,recheck=True)
        self.assertEqual(run_research(run.pk)["status"], "ready")
        session.refresh_from_db()
        self.assertGreater(session.revision, revision)
        self.assertTrue(any(i["title"] == "Keep across research" for d in session.itinerary["days"] for i in d["items"]))
        self.assertEqual(self.edit(session, "add", revision=revision, day_id=day["id"], fields={"title":"Stale source view"}).status_code, 409)

    def test_editor_write_rate_limit_remains_enforced(self):
        session, _ = self.multi()
        before = deepcopy(session.itinerary)
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        statuses = [self.client.post(url, {"action":"itinerary_edit"}, content_type="application/json").status_code for _ in range(61)]
        self.assertIn(429, statuses)
        session.refresh_from_db(); self.assertEqual(session.itinerary, before)
