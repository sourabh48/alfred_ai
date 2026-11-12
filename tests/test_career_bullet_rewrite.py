"""Local-model CV bullet rewriting: suggestions that add facts are rejected by code, not trusted."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.services import bullet_rewrite
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from tests.test_career_application_kit import CV, JD, analysis

BULLET = "Reduced SQL query time by 40% with indexing"


class InventionCheckTests(SimpleTestCase):
    def check(self, rewritten):
        return bullet_rewrite.invention_issues(BULLET, rewritten, ["Kafka", "SQL", "Python"])

    def test_plain_rewording_passes(self):
        self.assertEqual(self.check("Cut SQL query time by 40% through indexing"), [])

    def test_new_numbers_names_keywords_and_scope_are_rejected(self):
        self.assertIn("Adds numbers", self.check("Reduced SQL query time by 60% with indexing")[0])
        self.assertTrue(any("names or tools" in issue for issue in self.check("Reduced SQL query time by 40% with Redis indexing")))
        self.assertTrue(any("job keywords" in issue for issue in self.check("Reduced SQL and Kafka query time by 40% with indexing")))
        self.assertTrue(any("bigger scope" in issue for issue in self.check("Led indexing work that reduced SQL query time by 40%")))
        self.assertEqual(bullet_rewrite.invention_issues("Mentored three engineers", "Mentored 3 engineers", []), [])
        self.assertIn("Adds numbers", bullet_rewrite.invention_issues("Mentored three engineers", "Mentored 4 engineers", [])[0])
        self.assertIn("Drops numbers", bullet_rewrite.invention_issues("Mentored three engineers", "Mentored engineers", [])[0])


class FakeRewriter:
    def __init__(self, answers):
        self.answers = list(answers)

    def rewrite(self, bullet, terms, *, deadline):
        return self.answers.pop(0)


class RewriteTests(SimpleTestCase):
    def test_each_suggestion_is_checked_and_unchanged_is_not_accepted(self):
        results = bullet_rewrite.rewrite_bullets(
            [BULLET, "Built Django APIs", "Mentored engineers"], ["Kafka"],
            rewriter=FakeRewriter(["Cut SQL query time 40% via indexing", "Built Kafka and Django APIs", "Mentored engineers"]))
        self.assertEqual([item["accepted"] for item in results], [True, False, False])
        self.assertIn("unchanged", results[2]["issues"][0])

    def test_model_must_answer_with_the_schema(self):
        rewriter = bullet_rewrite.BulletRewriter.__new__(bullet_rewrite.BulletRewriter)
        rewriter.model, rewriter.cancellation = "llama3.2:3b", None
        rewriter._digest = lambda **kwargs: "same"
        rewriter._request = lambda *args, **kwargs: {"model": "llama3.2:3b", "done": True,
                                                     "message": {"role": "assistant", "content": "not json"}}
        with self.assertRaises(EmbeddingUnavailable):
            rewriter.rewrite(BULLET, [], deadline=10**12)
        seen = []
        rewriter._request = lambda method, path, body, **kwargs: seen.append(body) or {
            "model": "llama3.2:3b", "done": True, "message": {"role": "assistant", "content": '{"rewritten": " Cut  time "}'}}
        self.assertEqual(rewriter.rewrite(BULLET, ["Kafka"], deadline=10**12), "Cut time")
        self.assertEqual(seen[0]["options"]["temperature"], 0)
        self.assertIn("untrusted data", seen[0]["messages"][0]["content"])


class RewriteApiTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner, self.other = users.objects.create_user("rw-owner"), users.objects.create_user("rw-other")
        self.item = CareerJobAnalysis.objects.create(user=self.owner, job_url="https://jobs.example.test/1", job_title="Senior Backend Engineer",
                                                     extracted_text=JD, extracted_payload=analysis().extracted_payload)
        self.url = f"/api/career/job-analyses/{self.item.pk}/rewrite-bullets/"

    def test_needs_a_cv_and_stays_owner_scoped(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.url).status_code, 400)

    def test_rewrites_cv_bullets_and_reports_local_ai_down(self):
        CareerResume.objects.create(user=self.owner, uploaded_file=SimpleUploadedFile("cv.txt", b"cv"), file_name="cv.txt", parser_status="parsed",
                                    extracted_text=CV, extracted_payload={"skills": ["Python", "Django", "SQL"]})
        self.client.force_login(self.owner)
        with mock.patch.object(bullet_rewrite.BulletRewriter, "__init__", return_value=None), \
                mock.patch.object(bullet_rewrite.BulletRewriter, "rewrite", side_effect=lambda bullet, terms, deadline: bullet.upper()):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(any("REDUCED SQL QUERY TIME" in item["suggestion"] for item in response.json()["results"]))
        with mock.patch.object(bullet_rewrite.BulletRewriter, "__init__", side_effect=EmbeddingUnavailable("no model")):
            self.assertEqual(self.client.post(self.url).status_code, 503)
