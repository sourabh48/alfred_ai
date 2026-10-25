from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.serializers import CareerJobAnalysisSerializer
from apps.career.services import job_intelligence, resume_intelligence


JD = "Backend Engineer at Synthetic Example. Python, SQL and React. 3 years experience required."
RESUME = {"role": "Backend Engineer", "experience_years": 4, "skills": ["Python", "SQL"]}


def offline_career(test):
    for target, value in (
        ("verified_intelligence.macro_context", {"payload": {"unemployment": {}, "inflation": {}, "market": {}}, "evidence": []}),
        ("job_intelligence.market_outlook", {"risk_score": 50, "evidence": [], "insights": [], "layoff_news": [], "job_market_news": []}),
        ("job_intelligence.suggest_openings", {"openings": [], "evidence": {}}),
    ):
        test.enterContext(patch("apps.career.views." + target, return_value=value))


class CareerMatchingRulesTests(SimpleTestCase):
    def test_skill_terms_do_not_infer_substrings_in_either_parser(self):
        for service in (job_intelligence, resume_intelligence):
            with self.subTest(service=type(service).__name__):
                skills = service._extract_skills("JavaScript PostgreSQL proactive excellent Django Python")
                self.assertIn("Javascript", skills)
                self.assertIn("Postgresql", skills)
                self.assertIn("Python", skills)
                self.assertTrue({"Java", "Sql", "React", "Excel"}.isdisjoint(skills))

    def test_reviewed_overlap_keeps_existing_weights_and_source_fields(self):
        snapshot = job_intelligence.parse_recruiter_message(JD)
        fit = job_intelligence.compare_resume_to_job({**RESUME, "skills": [" python ", "SQL", "sql"]}, snapshot)
        self.assertEqual(fit["matched_skills"], ["Python", "Sql"])
        self.assertEqual(fit["missing_skills"], ["React"])
        self.assertEqual(fit["fit_score"], 80)
        self.assertEqual(fit["score_status"], "RULE_BASED")
        self.assertEqual(fit["sources"][0]["skills"], ["Python", "Sql"])
        self.assertIn("Python", fit["sources"][1]["excerpt"])
        self.assertIn("not a hiring probability", " ".join(fit["uncertainty"]))

    def test_missing_requirements_abstain_instead_of_claiming_experience_match(self):
        fit = job_intelligence.compare_resume_to_job(RESUME, job_intelligence.parse_recruiter_message("Contact our team about opportunities."))
        self.assertIsNone(fit["fit_score"])
        self.assertEqual(fit["score_status"], "UNAVAILABLE")
        self.assertNotIn("meet or exceed", " ".join(fit["strengths"]))
        self.assertIn("Insufficient evidence", " ".join(fit["gaps"]))

    def test_optional_negated_or_conflicting_evidence_withholds_overall_score(self):
        for text in (JD + " React is optional.", JD + " Java is not required.", JD + " 8 years experience required."):
            with self.subTest(text=text):
                fit = job_intelligence.compare_resume_to_job(RESUME, job_intelligence.parse_recruiter_message(text))
                self.assertIsNone(fit["fit_score"])
                self.assertIn("review", " ".join(fit["uncertainty"]).lower())

    def test_empty_or_nonfinite_resume_evidence_is_not_a_zero_percent_prediction(self):
        snapshot = job_intelligence.parse_recruiter_message(JD)
        for resume in ({}, {**RESUME, "experience_years": float("nan")}, {**RESUME, "experience_years": -1}):
            with self.subTest(resume=resume):
                fit = job_intelligence.compare_resume_to_job(resume, snapshot)
                self.assertIsNone(fit["fit_score"])

    def test_serialized_unavailable_score_and_legacy_score_are_distinct(self):
        row = CareerJobAnalysis(fit_score=0, extracted_payload={"fit": {"score_status": "UNAVAILABLE"}})
        self.assertIsNone(CareerJobAnalysisSerializer(row).data["fit_score"])
        row.extracted_payload = {}
        self.assertEqual(CareerJobAnalysisSerializer(row).data["fit_score"], 0)

    def test_unknown_fit_produces_review_action_instead_of_invented_low_match(self):
        from apps.risk.services import risk_intelligence
        row = CareerJobAnalysis(fit_score=0, extracted_payload={"fit": {"score_status": "UNAVAILABLE"}})
        actions = risk_intelligence._build_actions([], {}, {}, row)
        self.assertEqual(actions[0]["title"], "Review job-fit evidence")
        self.assertNotIn("70/100", actions[0]["note"])

    def test_unbounded_experience_text_cannot_create_infinite_years(self):
        self.assertEqual(job_intelligence._extract_experience("9" * 1000 + " years"), 0)

    def test_equivalent_experience_mentions_do_not_create_a_false_conflict(self):
        fit = job_intelligence.compare_resume_to_job(RESUME, job_intelligence.parse_recruiter_message(JD + " Minimum 3.0 years experience."))
        self.assertEqual(fit["fit_score"], 80)

    def test_salary_requires_pay_evidence_and_skips_unrelated_numbers(self):
        for text in (JD, "3 months experience; 12 users, Python 3.12", "Role 1234; application deadline 2026"):
            with self.subTest(text=text):
                self.assertEqual(job_intelligence._extract_salary({}, text), (0, 0, "", ""))
        salary = job_intelligence._parse_salary_text(JD + " Pay: ₹18–22 LPA")
        self.assertEqual((salary["salary_min"], salary["salary_max"]), (1800000, 2200000))


class CareerMatchingOwnerAcceptanceTests(TestCase):
    def setUp(self):
        limits = self.enterContext(TemporaryDirectory(prefix="alfred-career-match-limits-"))
        self.enterContext(override_settings(ALFRED_ABUSE_THROTTLE_DIR=limits))
        offline_career(self)
        self.owner = get_user_model().objects.create_user("synthetic_match_owner")
        self.foreign = get_user_model().objects.create_user("synthetic_match_foreign")
        self.resume = CareerResume.objects.create(user=self.owner, file_name="synthetic-owned-resume.txt",
            parser_status="parsed", extracted_payload=RESUME)
        CareerResume.objects.create(user=self.foreign, file_name="SYNTHETIC-FOREIGN-PRIVATE.txt",
            parser_status="parsed", extracted_payload={**RESUME, "skills": ["SECRET-FOREIGN", "React"]})
        self.client.force_login(self.owner)

    def test_match_cites_owned_captured_resume_and_jd_after_resume_changes(self):
        response = self.client.post("/api/career/recruiter-match/", {"message_text": JD}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        fit = response.json()["fit"]
        self.assertEqual(fit["sources"][0]["record_id"], self.resume.pk)
        self.assertEqual(fit["sources"][0]["label"], self.resume.file_name)
        self.assertNotIn("SECRET-FOREIGN", str(response.json()))
        self.resume.extracted_payload = {"skills": ["React"]}
        self.resume.save()
        stored = CareerJobAnalysis.objects.get(user=self.owner)
        self.assertEqual(stored.extracted_payload["fit"], fit)
        self.client.force_login(self.foreign)
        self.assertNotIn(str(stored.pk), [str(item["id"]) for item in self.client.get("/api/career/job-analyses/").json()["results"]])

    def test_explicit_older_resume_is_used_by_text_and_url_intake(self):
        CareerResume.objects.create(user=self.owner, file_name="newer-unrelated.txt",
            parser_status="parsed", extracted_payload={"skills": ["Excel"]})
        for path, data in (
            ("recruiter-match", {"message_text": JD}),
            ("job-match", {"job_url": "https://example.org/synthetic-job"}),
        ):
            with self.subTest(path=path), patch("apps.career.views.job_intelligence.parse_job_page",
                    return_value=job_intelligence.parse_recruiter_message(JD)):
                response = self.client.post(f"/api/career/{path}/",
                    {**data, "resume_id": self.resume.pk}, content_type="application/json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["fit"]["sources"][0]["record_id"], self.resume.pk)
                self.assertEqual(response.json()["fit"]["fit_score"], 80)

    def test_recruiter_attachment_evidence_survives_retry_and_correction(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        response = self.client.post("/api/career/recruiter-match/", {
            "message_text": "Please review the attached opportunity.",
            "resume_id": self.resume.pk,
            "attachment": SimpleUploadedFile("synthetic-jd.txt", JD.encode(), content_type="text/plain"),
        })
        self.assertEqual(response.status_code, 200)
        row = CareerJobAnalysis.objects.get(pk=response.json()["analysis"]["id"])
        original_source = row.extracted_payload["fit"]["sources"][0]
        self.assertEqual(row.available_fit_score, 80)
        self.resume.extracted_payload = {"skills": ["NEW-UNRELATED"]}
        self.resume.save()
        correction = self.client.post("/api/documents/review-queue/resolve/", {
            "scope": "recruiter_document", "id": row.pk,
            "corrections": {"company": "Corrected Synthetic Employer"},
        }, content_type="application/json")
        self.assertEqual(correction.status_code, 200)
        response = self.client.post("/api/documents/review-queue/retry/",
            {"scope": "recruiter_document", "id": row.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.company, "Corrected Synthetic Employer")
        self.assertEqual(row.available_fit_score, 80)
        self.assertEqual(row.extracted_payload["fit"]["sources"][0], original_source)
        self.assertIn("React", row.extracted_payload["job_snapshot"]["required_skills"])
        self.assertIn("React", row.extracted_payload["intake_combined_text"])

    def test_url_and_text_match_share_grounding_and_abstention(self):
        snapshot = job_intelligence.parse_recruiter_message("Synthetic role without skill or experience requirements")
        with patch("apps.career.views.job_intelligence.parse_job_page", return_value=snapshot):
            response = self.client.post("/api/career/job-match/", {"job_url": "https://example.org/synthetic-job"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["analysis"]["fit_score"])
        self.assertIn("unavailable", response.json()["analysis"]["summary"].lower())
        self.assertTrue(any("unavailable" in item.lower() for item in response.json()["career_timing"]["signals"]))

    def test_document_review_preserves_captured_resume_and_nullable_fit(self):
        from alfred_ai.services.document_review import _apply_recruiter_analysis_update
        response = self.client.post("/api/career/recruiter-match/", {"message_text": JD}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        row = CareerJobAnalysis.objects.get(user=self.owner)
        original = row.extracted_payload["fit"]["sources"][0]
        _apply_recruiter_analysis_update(row, job_intelligence.parse_recruiter_message("No structured requirements supplied."),
            resume_payload={"skills": ["SYNTHETIC-NEW-RESUME"]})
        row.save(); row.refresh_from_db()
        self.assertIsNone(row.available_fit_score)
        self.assertEqual(row.extracted_payload["fit"]["sources"][0], original)
        self.assertIn("unavailable", row.summary.lower())

    def test_session_csrf_and_failed_resume_cannot_be_bypassed_by_request_ids(self):
        self.assertEqual(Client().post("/api/career/recruiter-match/", {"message_text": JD}).status_code, 403)
        protected = Client(enforce_csrf_checks=True); protected.force_login(self.owner)
        self.assertEqual(protected.post("/api/career/recruiter-match/", {"message_text": JD}).status_code, 403)
        self.resume.parser_status = "needs_review"; self.resume.save()
        response = self.client.post("/api/career/recruiter-match/", {"message_text": JD, "resume_id": self.resume.pk, "user": self.foreign.pk}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["analysis"]["fit_score"])
        self.assertTrue(CareerJobAnalysis.objects.filter(user=self.owner).exists())
        self.assertFalse(CareerJobAnalysis.objects.filter(user=self.foreign).exists())

    def test_resume_selection_rejects_foreign_missing_and_malformed_before_parsing(self):
        foreign = CareerResume.objects.get(user=self.foreign)
        before = CareerJobAnalysis.objects.count()
        with patch("apps.career.views.job_intelligence.parse_recruiter_message") as recruiter, \
                patch("apps.career.views.job_intelligence.parse_job_page") as job:
            for path, data in (("recruiter-match", {"message_text": JD}),
                    ("job-match", {"job_url": "https://example.org/synthetic-job"})):
                for value, expected in ((foreign.pk, 404), (999999, 404), (-1, 400),
                        (True, 400), ([], 400), ({"id": self.resume.pk}, 400), (2**64, 400)):
                    with self.subTest(path=path, value=value):
                        response = self.client.post(f"/api/career/{path}/",
                            {**data, "resume_id": value}, content_type="application/json")
                        self.assertEqual(response.status_code, expected)
                        self.assertNotIn("SYNTHETIC-FOREIGN", str(response.content))
            recruiter.assert_not_called()
            job.assert_not_called()
        self.assertEqual(CareerJobAnalysis.objects.count(), before)
        resumes = self.client.get("/api/career/resumes/").json()
        self.assertEqual([item["id"] for item in resumes], [self.resume.pk])

    def test_recruiter_quota_remains_active_before_parsing_or_saving(self):
        with override_settings(ALFRED_EXPENSIVE_ACCOUNT_LIMIT=1), patch(
                "apps.career.views.job_intelligence.parse_recruiter_message",
                wraps=job_intelligence.parse_recruiter_message) as parse:
            first = self.client.post("/api/career/recruiter-match/", {"message_text": JD})
            self.assertEqual(first.status_code, 200)
            before = list(CareerJobAnalysis.objects.values())
            rejected = self.client.post("/api/career/recruiter-match/", {"message_text": JD})
            self.assertEqual(rejected.status_code, 429)
            self.assertGreater(int(rejected["Retry-After"]), 0)
            parse.assert_called_once()
            self.assertEqual(list(CareerJobAnalysis.objects.values()), before)

    def test_recruiter_correction_and_retry_cannot_access_another_owners_analysis(self):
        response = self.client.post("/api/career/recruiter-match/", {"message_text": JD})
        row = CareerJobAnalysis.objects.get(pk=response.json()["analysis"]["id"])
        before = row.extracted_payload
        self.client.force_login(self.foreign)
        for action in ("resolve", "retry"):
            response = self.client.post(f"/api/documents/review-queue/{action}/", {
                "scope": "recruiter_document", "id": row.pk,
                "corrections": {"company": "FOREIGN-WRITE"},
            }, content_type="application/json")
            self.assertEqual(response.status_code, 404)
            self.assertNotIn(self.resume.file_name, str(response.content))
        row.refresh_from_db()
        self.assertEqual(row.extracted_payload, before)
