"""Career Ops ports at 775861b (MIT): calibrate, story bank, debrief, deep research, red flags, sessions, practice,
upskill and titles."""
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
        patterns = self.client.get("/api/career/patterns/")
        self.assertEqual(patterns["Cache-Control"], "no-store, private")
        self.assertEqual(set(patterns.json()) >= {"calibration", "skill_gaps", "titles", "red_flags"}, True)
        self.assertEqual(self.client.get(f"{url}?round=screen").status_code, 404)
        self.client.force_login(owner)
        guide = self.client.get(f"{url}?round=screen")
        self.assertEqual(guide["Cache-Control"], "no-store, private")
        self.assertIn("Deep research: Synthetic Corp - Backend Engineer", guide.json()["research_prompt"])
        self.assertEqual(guide.json()["practice"]["questions"][1]["question"], "Why Synthetic Corp and why this role?")
        self.assertEqual(self.client.get(f"{url}?round=nope").status_code, 400)
        practice = {"action": "add", "kind": "practice", "item": {"round_type": "behavioral", "turns": [
            {"question": "Tell me about a failure.", "answer": "We lost 25 customers.", "rating": "gap"}]}}
        session = self.client.post(url, practice, content_type="application/json").json()["opportunity"]["interview_notes"]["sessions"][0]
        self.assertEqual(session["turns"][0]["checks"], ["No reflection: add what you learned or would do differently.",
                                                         "Not in your CV: 25. Say these only if you can stand behind them."])


TRANSCRIPT = """---
company: Synthetic Corp
role: Backend Engineer
round: HM
date: 2026-11-05
interviewer_role: Engineering manager
source: debrief
stated_priorities:
  - speaker: Hiring manager
    quote: "The biggest project this year is the billing rewrite."
---

## Q1
**Interviewer:** Tell me about a migration you led.
It can be any size.
<!-- competency: delivery, ownership -->
**Candidate:** I moved billing to queues.
Then I learned to stage it.

## Q2
**Interviewer:** Anything else?
"""


def job_row(company, title, *, notes=None, score=None, missing=(), matched=(), stage=None):
    payload = {"interview_notes": notes or {}, "fit": {"missing_skills": list(missing), "matched_skills": list(matched)}}
    if score is not None:
        payload["triage"] = {"score": score}
    if stage:
        payload["application"] = {"stage": stage, "history": []}
    return SimpleNamespace(pk=1, company=company, job_title=title, extracted_payload=payload)


class SessionsResearchAndRedFlagTests(SimpleTestCase):
    def test_transcript_import_reads_front_matter_turns_and_tags(self):
        notes = interview_notes.apply_change({}, {"action": "add", "kind": "transcript", "item": {"text": TRANSCRIPT, "signals": ["process"]}}, today=TODAY)
        session = notes["sessions"][0]
        self.assertEqual((session["source"], session["round_type"], session["on"], session["interviewer_role"]),
                         ("debrief", "hiring-manager", "2026-11-05", "Engineering manager"))
        self.assertEqual(session["turns"][0], {"question": "Tell me about a migration you led.\nIt can be any size.",
                                               "answer": "I moved billing to queues.\nThen I learned to stage it.",
                                               "competency": "delivery, ownership", "rating": ""})
        self.assertEqual(session["turns"][1]["answer"], "")
        self.assertEqual(session["stated_priorities"], [{"speaker": "Hiring manager", "quote": "The biggest project this year is the billing rewrite."}])
        self.assertEqual(session["signals"], ["process"])
        practice = interview_notes.apply_change({}, {"action": "add", "kind": "transcript", "item": {
            "text": TRANSCRIPT.replace("source: debrief", "source: mock"), "signals": ["process"]}}, today=TODAY)["sessions"][0]
        self.assertEqual((practice["signals"], practice["stated_priorities"]), ([], []))  # mock rounds are not the company's
        for text, message in (("", "Paste"), ("no turns here", "No **Interviewer:**"), ("x" * 60001, "longer than"),
                              (TRANSCRIPT.replace("2026-11-05", "2026-12-01"), "future"),
                              (TRANSCRIPT.replace("source: debrief", "source: chat"), "listed round type and source")):
            with self.assertRaisesMessage(ValueError, message):
                interview_notes.apply_change({}, {"action": "add", "kind": "transcript", "item": {"text": text}}, today=TODAY)
        with self.assertRaisesMessage(ValueError, "interviewer signals"):
            interview_notes.apply_change({}, {"action": "add", "kind": "transcript", "item": {"text": TRANSCRIPT, "signals": ["rude"]}}, today=TODAY)
        with self.assertRaisesMessage(ValueError, "add or remove"):
            interview_notes.apply_change({}, {"action": "add", "kind": "session", "item": {}}, today=TODAY)

    def test_research_needs_a_web_source_except_your_angle(self):
        add = lambda item: interview_notes.apply_change({}, {"action": "add", "kind": "research", "item": item}, today=TODAY)
        saved = add({"axis": "recent-moves", "note": "Raised a round", "source_url": "https://news.example.test/a", "checked_on": "2026-11-11"})
        self.assertEqual(saved["research"][0]["source_url"], "https://news.example.test/a")
        self.assertEqual(add({"axis": "your-angle", "note": "My billing work fits"})["research"][0]["checked_on"], "2026-11-12")
        for item, message in (({"axis": "culture", "note": "Remote"}, "Add the link"), ({"axis": "x", "note": "n"}, "listed research topic"),
                              ({"axis": "culture", "note": "n", "source_url": "javascript:alert(1)"}, "web link"),
                              ({"axis": "culture", "note": "n", "source_url": "https://user:pw@example.test/"}, "web link"),
                              ({"axis": "culture", "note": ""}, "Write what you found")):
            with self.assertRaisesMessage(ValueError, message):
                add(item)
        prompt = interview_notes.research_prompt(SimpleNamespace(company="Synthetic Corp", job_title="Backend Engineer"))
        self.assertIn("Synthetic Corp - Backend Engineer", prompt)
        self.assertNotIn("CV", prompt)

    def test_red_flag_score_levels_and_practice_exclusion(self):
        notes = {"debriefs": [{"on": "2026-11-01", "questions": "Q", "signals": ["scope_ambiguity", "defensive_closure"]},
                              {"on": "2026-11-03", "questions": "Q", "signals": ["scope_ambiguity"]}],
                 "sessions": [{"source": "practice", "on": "2026-11-04", "turns": [{"question": "Q"}], "signals": ["process"]}]}
        report = interview_notes.red_flags([job_row("Synthetic Corp", "Backend Engineer", notes=notes),
                                            job_row("Calm Corp", "Engineer", notes={"debriefs": [{"on": "2026-11-02", "gaps": "g"}]}),
                                            job_row("", "No company", notes=notes), job_row("Empty Corp", "x")])
        first, second = report["companies"]
        self.assertEqual((first["company"], first["rounds"], first["score"], first["level"]), ("Synthetic Corp", 2, 3, "Enter with eyes open"))
        self.assertEqual([(row["key"], row["rounds"], row["pattern"]) for row in first["signals"]],
                         [("scope_ambiguity", 2, True), ("defensive_closure", 1, False)])
        self.assertEqual((second["company"], second["score"]), ("Calm Corp", 0))
        notes["debriefs"][1]["signals"] = ["scope_ambiguity", "defensive_closure"]
        self.assertEqual(interview_notes.red_flags([job_row("Synthetic Corp", "B", notes=notes)])["companies"][0]["level"], "Reconsider")

    def test_practice_questions_prefer_real_ones_and_answers_get_checks(self):
        notes = interview_notes.apply_change({}, {"action": "add", "kind": "transcript", "item": {"text": TRANSCRIPT}}, today=TODAY)
        notes = interview_notes.apply_change(notes, {"action": "add", "kind": "debrief", "item": {"on": "2026-11-06", "round_type": "technical",
                                                                                                 "questions": "- How does Kafka order messages?"}}, today=TODAY)
        job = job_row("Synthetic Corp", "Backend Engineer", notes=notes, matched=["Python"], missing=["Kafka"])
        result = interview_notes.practice_questions(job, "technical")
        self.assertEqual(result["questions"][0], {"question": "How does Kafka order messages?", "origin": "asked before"})
        self.assertEqual(len(result["questions"]), interview_notes.PRACTICE_LENGTH)
        self.assertIn({"question": "Walk me through how you have used Python in real work, including a trade-off you made.",
                       "origin": "common question"}, result["questions"])
        self.assertEqual(result["stated_priorities"][0]["speaker"], "Hiring manager")
        with self.assertRaisesMessage(ValueError, "Choose screen"):
            interview_notes.practice_questions(job, "onsite")
        checks = interview_notes.answer_checks({"answer": "We cut cost by 40% in 3 weeks. " * 50}, "behavioral", "Cut cost by 40%.")
        self.assertEqual(len(checks), 3)
        self.assertIn("Not in your CV: 3.", checks[2])
        self.assertEqual(interview_notes.answer_checks({"answer": "I learned to stage it."}, "behavioral", ""), [])
        self.assertEqual(interview_notes.answer_checks({"answer": ""}, "screen", ""), ["Not answered."])
        saved = interview_notes.apply_change(notes, {"action": "add", "kind": "practice", "item": {
            "round_type": "technical", "on": "2026-11-12", "signals": ["process"],
            "turns": [{"question": "Q", "answer": "A", "rating": "gap"}]}}, today=TODAY)["sessions"][-1]
        self.assertEqual((saved["source"], saved["signals"], saved["turns"][0]["rating"]), ("practice", [], "gap"))
        with self.assertRaisesMessage(ValueError, "strong, solid or gap"):
            interview_notes.apply_change(notes, {"action": "add", "kind": "practice", "item": {"turns": [{"question": "Q", "rating": "great"}]}}, today=TODAY)


class UpskillAndTitlesTests(SimpleTestCase):
    def test_gap_tiers_weights_and_known_skills(self):
        rows = [job_row("A", "t", score=2.0, missing=["Kafka", "Go"]), job_row("B", "t", score=3.0, missing=["Kafka"]),
                job_row("C", "t", score=3.5, missing=["kafka", "Rust"]), job_row("D", "t", score=4.5, missing=["Go"]),
                job_row("E", "t", score=3.0, missing=["Python"]), job_row("F", "t", missing=["Rust"])]
        result = application_kit.skill_gaps(rows, "Python and SQL")
        self.assertTrue(result["available"])
        gaps = {gap["skill"].casefold(): gap for gap in result["gaps"]}
        self.assertEqual((gaps["kafka"]["tier"], gaps["kafka"]["jobs"], gaps["kafka"]["low_fit_jobs"], gaps["kafka"]["weight"]), ("Critical", 3, 3, 6.5))
        self.assertEqual((gaps["go"]["tier"], gaps["go"]["weight"]), ("Low", 3.5))
        self.assertEqual((gaps["rust"]["tier"], gaps["rust"]["weight"]), ("Low", 2.5))  # unscored job weighs 1
        self.assertNotIn("python", gaps)
        self.assertEqual(result["already_on_cv"], ["Python"])
        self.assertEqual(result["gaps"][0]["skill"], "Kafka")
        thin = application_kit.skill_gaps(rows[:3], "")
        self.assertEqual((thin["available"], thin["scored"]), (False, 3))

    def test_titles_need_quoted_cv_evidence_and_skip_covered(self):
        cv = "Built Python services for billing\nLed SQL reporting\nHobbies: chess"
        rows = [job_row("A", "Backend Engineer", matched=["Python"]), job_row("B", "Data Engineer", matched=["SQL", "Python"], score=4.2),
                job_row("C", "Platform Engineer", matched=["Go"]), job_row("D", "Solutions Architect", matched=["SQL"], stage="interview"),
                job_row("E", "data engineer", matched=["SQL"])]
        result = application_kit.title_suggestions(rows, ["Backend"], cv)
        self.assertEqual([row["title"] for row in result["suggestions"]], ["Solutions Architect", "Data Engineer"])
        self.assertEqual(result["suggestions"][1]["evidence"], ["Built Python services for billing", "Led SQL reporting"])
        self.assertTrue(result["suggestions"][0]["reached_interview"])
