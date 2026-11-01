"""Synthetic normalized-feed acceptance; no live provider or application submission."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError
from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume
from apps.career.services.job_intelligence import JOB_FEED_ADAPTERS, job_intelligence, verified_intelligence


def lead(**changes):
    return {"title": "Data Analyst", "company": "Synthetic Company", "location": "Bengaluru, Karnataka, India",
        "url": "https://jobs.example.org/roles/123", "tags": ["Python", "SQL"], **changes}


def feed(index=0, *, jobs=None, status="fresh", expires=None):
    now = timezone.now()
    adapter = JOB_FEED_ADAPTERS[index]
    return SimpleNamespace(payload={"jobs": [lead()] if jobs is None else jobs}, evidence={
        "source_name": adapter["name"], "source_url": adapter["source_url"], "status": status,
        "verified_at": (now - timedelta(hours=1)).isoformat(), "fetched_at": (now - timedelta(hours=1)).isoformat(),
        "stale_after": (expires or now + timedelta(hours=2)).isoformat()})


def feeds(test, results):
    mocks = []
    for adapter, result in zip(JOB_FEED_ADAPTERS, results):
        kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
        mocks.append(test.enterContext(patch.object(verified_intelligence, adapter["method"], **kwargs)))
    return mocks


class CareerDiscoveryRulesTests(SimpleTestCase):
    def test_missing_metadata_retains_unverified_leads_without_fabricated_dates(self):
        feeds(self, [{"jobs": [lead()]}, feed(1, jobs=[]), feed(2, jobs=[])])
        result = job_intelligence.suggest_openings("Data Analyst", ["Python"])
        item = result["openings"][0]
        self.assertFalse(item["verified_source"])
        self.assertEqual(item["source_status"], "unknown")
        self.assertEqual(item["verified_at"], "")
        self.assertNotEqual(result["evidence"]["status"], "fresh")

    def test_source_freshness_is_fail_closed_for_invalid_dates_identity_and_expiry(self):
        base = feed().evidence
        now = timezone.now()
        cases = [({}, "fresh"), ({"status": "stale"}, "stale"),
            ({"stale_after": (now - timedelta(seconds=1)).isoformat()}, "stale"),
            ({"stale_after": now.isoformat()}, "stale"), ({"stale_after": ""}, "unknown"),
            ({"verified_at": "invalid"}, "unknown"), ({"verified_at": now.replace(tzinfo=None).isoformat()}, "unknown"),
            ({"verified_at": (now + timedelta(days=1)).isoformat()}, "unknown"),
            ({"source_url": "https://unrelated.example.org/feed"}, "unknown"),
            ({"source_url": "javascript:alert(1)"}, "unknown"), ({"status": "failed"}, "unavailable")]
        for changes, expected in cases:
            with self.subTest(changes=changes):
                self.assertEqual(job_intelligence.opening_evidence_status({**base, **changes}), expected)

    def test_unsafe_links_and_malformed_rows_never_become_opening_actions(self):
        bad_urls = ["javascript:alert(1)", "http://jobs.example.org/x", "https://127.0.0.1/x",
            "https://user:secret@jobs.example.org/x", "https://jobs.example.org/\nattack"]
        rows = [None, [], "bad", lead(company=[]), lead(salary={}), lead(title=[])]
        rows += [lead(url=url) for url in bad_urls]
        feeds(self, [feed(jobs=rows), feed(1, jobs=[lead(title="<img src=x onerror=alert(1)>", tags=[None, {}, "SQL"])]), feed(2, jobs=[])])
        result = job_intelligence.suggest_openings("Data Analyst", ["Python"])
        self.assertEqual(result["total_candidates"], 1)
        self.assertEqual(result["openings"][0]["tags"], ["SQL"])
        self.assertEqual(result["openings"][0]["url"], lead()["url"])

    def test_duplicate_url_prefers_fresh_evidence_and_preserves_distinct_job_ids(self):
        feeds(self, [feed(status="stale", jobs=[lead(url="https://JOBS.example.org/roles/123#old")]),
            feed(1, jobs=[lead(url="https://jobs.example.org/roles/123#new")]),
            feed(2, jobs=[lead(url="https://jobs.example.org/roles/456")])])
        result = job_intelligence.suggest_openings("Data Analyst", ["Python"])
        self.assertEqual(result["total_candidates"], 2)
        item = next(i for i in result["openings"] if i["url"].endswith("123"))
        self.assertEqual(item["portal_name"], JOB_FEED_ADAPTERS[1]["name"])
        self.assertTrue(item["verified_source"])
        self.assertNotIn("#", item["url"])

    def test_provider_outage_does_not_hide_another_feed_or_invent_success(self):
        feeds(self, [PublicHTTPError("timeout"), feed(1), SimpleNamespace(payload=[], evidence=["bad"])])
        result = job_intelligence.suggest_openings("Data Analyst", ["Python"])
        self.assertEqual(result["total_candidates"], 1)
        self.assertEqual(result["openings"][0]["portal_name"], JOB_FEED_ADAPTERS[1]["name"])
        self.assertTrue(result["openings"][0]["verified_source"])
        self.assertNotEqual(result["evidence"]["status"], "fresh")
        self.assertEqual(result["source_evidence"][0]["status"], "unavailable")

    def test_each_normalized_feed_is_bounded_before_deduplication(self):
        rows = [lead(url=f"https://jobs.example.org/{i}") for i in range(100)]
        feeds(self, [feed(jobs=rows), feed(1, jobs=[]), feed(2, jobs=[])])
        result = job_intelligence.suggest_openings("Data Analyst", ["Python"])
        self.assertEqual(result["total_candidates"], 10)
        self.assertEqual(len(result["openings"]), 8)

    def test_another_known_feed_cannot_supply_the_current_adapters_identity(self):
        wrong = feed()
        wrong.evidence["source_url"] = JOB_FEED_ADAPTERS[1]["source_url"]
        feeds(self, [wrong, feed(1, jobs=[]), feed(2, jobs=[])])
        item = job_intelligence.suggest_openings("Data Analyst", ["Python"])["openings"][0]
        self.assertFalse(item["verified_source"])
        self.assertEqual(item["source_status"], "unknown")
        self.assertEqual(item["source_evidence"]["source_url"], "")

    def test_missing_publication_dates_remain_unknown_and_sort_without_error(self):
        feeds(self, [feed(jobs=[lead(publication_date=None),
            lead(url="https://jobs.example.org/roles/456", publication_date="")]), feed(1, jobs=[]), feed(2, jobs=[])])
        result = job_intelligence.suggest_openings("Data Analyst", ["Python"])
        self.assertEqual(result["total_candidates"], 2)
        self.assertTrue(all(item["publication_date"] == "" for item in result["openings"]))

    def test_search_terms_come_only_from_the_configured_role_and_skills(self):
        mocks = feeds(self, [feed(jobs=[]), feed(1, jobs=[]), feed(2, jobs=[])])
        job_intelligence.suggest_openings("Java Developer", ["Java", "Spring Boot", "AWS"])
        self.assertEqual({call.args[0] for call in mocks[0].call_args_list},
            {"Java Developer Java Spring Boot", "Java Developer", "Java"})

    def test_non_text_saved_skills_do_not_break_discovery(self):
        feeds(self, [feed(), feed(1, jobs=[]), feed(2, jobs=[])])
        result = job_intelligence.suggest_openings("Data Analyst", [None, 5, "", "SQL"])
        self.assertEqual(result["total_candidates"], 1)

    def test_role_and_skills_match_whole_words_only(self):
        feeds(self, [feed(jobs=[lead(title="JavaScript Engineer", tags=[], url="https://jobs.example.org/js"),
            lead(title="Senior Java Engineer", tags=[], url="https://jobs.example.org/java")]), feed(1, jobs=[]), feed(2, jobs=[])])
        rows = {i["title"]: i for i in job_intelligence.suggest_openings("Java Developer", ["Java"])["openings"]}
        self.assertEqual(rows["JavaScript Engineer"]["match_reasons"], [])
        self.assertFalse(rows["JavaScript Engineer"]["role_matched"])
        self.assertTrue(rows["Senior Java Engineer"]["role_matched"])
        self.assertGreater(rows["Senior Java Engineer"]["relevance_score"], rows["JavaScript Engineer"]["relevance_score"])

    def test_tracking_parameters_and_trailing_slash_do_not_split_one_posting(self):
        urls = ["https://jobs.example.org/roles/123?utm_source=feed", "https://jobs.example.org/roles/123/?ref=board",
            "https://jobs.example.org/roles/123?gh_jid=9", "https://jobs.example.org/roles/123?gh_jid=10&utm_medium=x"]
        feeds(self, [feed(jobs=[lead(url=url) for url in urls]), feed(1, jobs=[]), feed(2, jobs=[])])
        self.assertEqual(job_intelligence.suggest_openings("Data Analyst", ["Python"])["total_candidates"], 3)


class CareerDiscoveryAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="discovery-owner", password="SyntheticPassword!123")
        self.other = get_user_model().objects.create_user(username="PRIVATE-OTHER", password="SyntheticPassword!123")
        CareerProfile.objects.create(user=self.user, role="Data Analyst", skills="Python, SQL", experience_years=3, last_salary=50000)
        CareerProfile.objects.create(user=self.other, role="PRIVATE-FOREIGN-ROLE", skills="PRIVATE-FOREIGN-SKILL", experience_years=2, last_salary=40000)
        self.client.force_login(self.user)
        self.enterContext(patch("apps.career.views.verified_intelligence.macro_context",
            return_value={"payload": {"unemployment": {}, "inflation": {}, "market": {}}, "evidence": []}))
        self.enterContext(patch.object(job_intelligence, "market_outlook",
            return_value={"risk_score": 50, "evidence": [], "insights": [], "layoff_news": [], "job_market_news": []}))

    def test_owner_cache_cannot_extend_feed_expiry_or_modify_owned_profiles(self):
        now = timezone.now()
        mocks = feeds(self, [feed(expires=now + timedelta(seconds=10)), feed(1, jobs=[]), feed(2, jobs=[])])
        before = list(CareerProfile.objects.order_by("pk").values())
        first = self.client.get("/api/career/dashboard/")
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["openings"][0]["verified_source"])
        count = mocks[0].call_count
        with patch("django.utils.timezone.now", return_value=now + timedelta(seconds=11)):
            second = self.client.get("/api/career/dashboard/")
        self.assertEqual(mocks[0].call_count, count, "Owner cache must actually be exercised")
        item = second.json()["openings"][0]
        self.assertFalse(item["verified_source"])
        self.assertEqual(item["source_status"], "stale")
        self.assertEqual(first.json()["openings_evidence"]["status"], "fresh")
        self.assertEqual(second.json()["openings_evidence"]["status"], "stale")
        self.assertEqual(list(CareerProfile.objects.order_by("pk").values()), before)
        self.assertNotIn("PRIVATE-FOREIGN", str(first.json()))
        self.assertNotIn("PRIVATE-FOREIGN", str(mocks[0].call_args_list))

    def test_location_filter_and_session_isolation_use_existing_owner_preferences(self):
        feeds(self, [feed(jobs=[lead(), lead(url="https://jobs.example.org/us", location="Austin, Texas, United States")]), feed(1, jobs=[]), feed(2, jobs=[])])
        response = self.client.get("/api/career/dashboard/?country=India&state=Karnataka")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["location"] for item in response.json()["openings"]], [lead()["location"]])
        self.assertNotIn("PRIVATE-FOREIGN", str(response.json()))
        self.client.logout()
        self.assertIn(self.client.get("/api/career/dashboard/").status_code, (401, 403))

    def test_configured_profile_skills_drive_discovery_after_a_resume_upload(self):
        CareerResume.objects.create(user=self.user, file_name="synthetic.txt", uploaded_file="synthetic.txt", parser_status="parsed",
            extracted_payload={"role": "Resume Role", "skills": ["Cobol"]})
        mocks = feeds(self, [feed(jobs=[]), feed(1, jobs=[]), feed(2, jobs=[])])
        self.assertEqual(self.client.get("/api/career/dashboard/").status_code, 200)
        terms = {call.args[0] for call in mocks[0].call_args_list}
        self.assertIn("Data Analyst Python SQL", terms)
        self.assertNotIn("Cobol", " ".join(terms))

    def test_saved_analysis_salary_keeps_its_read_date_instead_of_looking_newly_verified(self):
        read_at = timezone.now() - timedelta(days=30)
        analysis = CareerJobAnalysis.objects.create(user=self.user, job_url="https://jobs.example.org/roles/saved", location="Bengaluru",
            extracted_payload={"job_snapshot": {"title": "Data Analyst", "location": "Bengaluru", "salary_min": 1800000,
                "salary_max": 2200000, "salary_currency": "INR", "salary_period": "year", "source_kind": "job_page"}})
        CareerJobAnalysis.objects.filter(pk=analysis.pk).update(created_at=read_at)
        feeds(self, [feed(jobs=[]), feed(1, jobs=[]), feed(2, jobs=[])])
        benchmark = self.client.get("/api/career/dashboard/").json()["compensation_benchmark"]
        self.assertTrue(benchmark["available"])
        self.assertEqual(benchmark["salary_observations"][0]["observed_at"], read_at.isoformat())
        self.assertEqual(benchmark["evidence"][-1]["status"], "stale")
        self.assertEqual(benchmark["evidence"][-1]["verified_at"], read_at.isoformat())
        self.assertFalse(benchmark["evidence_contract"]["proof_complete"])
