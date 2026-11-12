"""Calibration (career-ops calibrate.mjs), interview stories and debriefs (story-bank, interview/debrief), 775861b MIT."""
from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.services import application_kit, interview_notes

TODAY = date(2026, 11, 12)


def row(score, stage, history=()):
    application = {"stage": stage, "history": [{"stage": item, "on": "2026-10-01"} for item in history]}
    return SimpleNamespace(extracted_payload={"triage": {"score": score} if score is not None else None, "application": application})


class CalibrationTests(SimpleTestCase):
    def test_separating_inverted_and_floor(self):
        high = [row(4.6, "hired", ["applied", "interview", "offer", "hired"]), row(4.7, "rejected", ["applied", "interview", "rejected"])] * 3
        low = [row(3.0, "rejected", ["applied", "rejected"])] * 5
        result = application_kit.calibration(high + low, min_band=5)
        self.assertEqual(result["verdict"], "separating")
        bands = {band["band"]: band for band in result["bands"]}
        self.assertEqual((bands["4.5 and up"]["interview_rate"], bands["4.5 and up"]["offer_rate"]), (100, 50))
        self.assertEqual(bands["Below 3.5"]["interview_rate"], 0)
        self.assertEqual(application_kit.calibration(low + [row(4.8, "rejected", ["applied", "rejected"])] * 5)["verdict"], "flat")
        inverted = [row(3.0, "interview", ["applied", "interview"])] * 5 + [row(4.5, "rejected", ["rejected"])] * 5
        self.assertEqual(application_kit.calibration(inverted)["verdict"], "inverted")
        thin = application_kit.calibration(high[:2])
        self.assertEqual(thin["verdict"], "insufficient")
        self.assertTrue(all(band["interview_rate"] is None for band in thin["bands"]))

    def test_waiting_unscored_and_unsent_are_left_out(self):
        result = application_kit.calibration([row(4.0, "applied", ["applied"]), row(4.0, "assessment", ["applied", "assessment"]),
                                              row(None, "rejected", ["rejected"]), row(4.0, "discarded"), row(4.0, "evaluated"),
                                              SimpleNamespace(extracted_payload=None)])
        self.assertEqual((result["resolved"], result["in_flight"], result["unscored"]), (0, 2, 1))


class NotesTests(SimpleTestCase):
    def test_story_and_debrief_validation(self):
        story = {"title": "Cut deploy time", "action": "Moved builds to cached runners", "result": "Deploys took 12 minutes instead of 40"}
        notes = interview_notes.apply_change({}, {"action": "add", "kind": "story", "item": story}, today=TODAY)
        self.assertEqual(notes["stories"][0]["title"], "Cut deploy time")
        with self.assertRaisesMessage(ValueError, "title and what you did"):
            interview_notes.apply_change(notes, {"action": "add", "kind": "story", "item": {"title": "No action"}}, today=TODAY)
        with self.assertRaisesMessage(ValueError, "longer than"):
            interview_notes.apply_change(notes, {"action": "add", "kind": "story", "item": {**story, "action": "x" * 1501}}, today=TODAY)
        with self.assertRaisesMessage(ValueError, "future"):
            interview_notes.apply_change(notes, {"action": "add", "kind": "debrief", "item": {"on": "2026-11-13", "questions": "Q"}}, today=TODAY)
        with self.assertRaisesMessage(ValueError, "listed round"):
            interview_notes.apply_change(notes, {"action": "add", "kind": "debrief", "item": {"round_type": "x", "questions": "Q"}}, today=TODAY)
        with self.assertRaisesMessage(ValueError, "at least"):
            interview_notes.apply_change(notes, {"action": "add", "kind": "debrief", "item": {"interviewer": "Asha"}}, today=TODAY)
        notes = interview_notes.apply_change(notes, {"action": "add", "kind": "debrief", "item": {"on": "2026-11-10", "questions": "Kafka?"}}, today=TODAY)
        notes = interview_notes.apply_change(notes, {"action": "add", "kind": "debrief", "item": {"on": "2026-11-01", "gaps": "Kafka"}}, today=TODAY)
        self.assertEqual([item["on"] for item in notes["debriefs"]], ["2026-11-01", "2026-11-10"])
        with self.assertRaisesMessage(ValueError, "no longer there"):
            interview_notes.apply_change(notes, {"action": "remove", "kind": "story", "index": 3}, today=TODAY)
        notes = interview_notes.apply_change(notes, {"action": "remove", "kind": "story", "index": 0}, today=TODAY)
        self.assertEqual(notes["stories"], [])

    def test_figures_not_in_the_cv_are_listed(self):
        story = {"title": "t", "action": "Led three engineers", "result": "Cut cost by 40% to 1,200 a month"}
        self.assertEqual(interview_notes.unverified_figures(story, "Cut cost by 40% at Synthetic Corp."), ["1200", "3"])
        self.assertEqual(interview_notes.clean({"stories": [{"title": "bad"}, story, "x"]})["stories"][0]["title"], "t")


class NotesApiTests(TestCase):
    def test_owner_only_revision_guard_and_story_bank(self):
        users = get_user_model()
        owner, other = users.objects.create_user("notes-owner"), users.objects.create_user("notes-other")
        job = CareerJobAnalysis.objects.create(user=owner, job_url="https://jobs.example.test/1", company="Synthetic Corp",
                                               job_title="Backend Engineer", extracted_payload={"application": {"stage": "interview"}})
        CareerResume.objects.create(user=owner, file_name="cv.txt", uploaded_file="career_resumes/cv.txt", extracted_text="Cut cost by 40%.")
        url = f"/api/career/job-analyses/{job.pk}/interview-notes/"
        story = {"action": "add", "kind": "story", "item": {"title": "Cost", "action": "Cut cost by 40% and 25%"}}
        self.client.force_login(other)
        self.assertEqual(self.client.post(url, story, content_type="application/json").status_code, 404)
        self.client.force_login(owner)
        self.assertEqual(self.client.post(url, {**story, "revision": "stale"}, content_type="application/json").status_code, 409)
        self.assertEqual(self.client.post(url, {"action": "add", "kind": "story", "item": {}}, content_type="application/json").status_code, 400)
        response = self.client.post(url, story, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["opportunity"]["interview_notes"]["stories"][0]["title"], "Cost")
        job.refresh_from_db()
        self.assertEqual(job.extracted_payload["application"], {"stage": "interview"})  # other saved data kept
        bank = self.client.get("/api/career/stories/")
        self.assertEqual(bank["Cache-Control"], "no-store, private")
        self.assertEqual(bank.json()["stories"][0]["source"], "Synthetic Corp - Backend Engineer")
        self.assertEqual(bank.json()["stories"][0]["unverified_figures"], ["25"])
        self.client.force_login(other)
        self.assertEqual(self.client.get("/api/career/stories/").json()["stories"], [])
        self.assertIn("calibration", self.client.get("/api/career/patterns/").json())
