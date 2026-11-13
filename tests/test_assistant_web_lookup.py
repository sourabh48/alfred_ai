"""Ask ALFRED's opt-in online lookup: only a public-looking question leaves the PC, and answers cite what they use."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.ml_engine.services import web_lookup
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from apps.ml_engine.services.memory_reasoning import MockReasoner, OpenAIReasoner
from apps.ml_engine.services.persistent_memory import MemoryStore
from tests.test_persistent_memory import SyntheticEmbeddings

WIKI = PublicResponse(b'{"pages":[{"key":"Repo_rate","title":"Repo rate","excerpt":"The <span class=\\"searchmatch\\">repo</span> rate is 6.5 percent"}]}',
                      "application/json")
RSS = PublicResponse(b"""<?xml version="1.0"?><rss version="2.0"><channel><item><title>Central bank holds repo rate at 6.5%</title>
<link>https://news.example.org/repo</link><description>&lt;b&gt;Synthetic&lt;/b&gt; policy story</description>
<pubDate>Thu, 12 Nov 2026 10:00:00 GMT</pubDate><source url="https://news.example.org">Synthetic News</source></item></channel></rss>""",
                     "application/rss+xml")


def fake_request(method, url, **kwargs):
    return WIKI if "wikipedia.org" in url else RSS


class QuestionFilterTests(SimpleTestCase):
    def test_public_questions_pass_and_private_looking_ones_stay_on_this_pc(self):
        self.assertEqual(web_lookup.check_public("  What is the  current repo rate in India? "), "What is the current repo rate in India?")
        for private in ("my account 123456789012", "salary of ₹12,00,000 is fair?", "rs 5000 loan", "mail a@b.co about it",
                        "is 12 lakh a good income", "reset my password", "key sk-abcdefghijklmnop", "file C:\\Users\\x\\a.pdf", ""):
            with self.subTest(private=private), self.assertRaises(web_lookup.PrivateQuestion):
                web_lookup.check_public(private)

    def test_alfred_decides_memory_for_personal_and_web_for_current_or_unknown_public_questions(self):
        for question in ("latest repo rate in India", "who won the election today", "petrol price in Kolkata",
                         "what is a mutual fund", "explain index funds", "interest rates in the US this year"):
            with self.subTest(question=question):
                self.assertTrue(web_lookup.should_search(question))
        for question in ("what did I save about my trip", "where is my nearest bank", "what can you do", "who is ALFRED",
                         "is 12 lakh a good salary today", "suggest a quiet hobby", ""):
            with self.subTest(question=question):
                self.assertFalse(web_lookup.should_search(question))
        self.assertFalse(web_lookup.should_search("what is a mutual fund", [{"id": "saved"}]))  # memory answers it
        self.assertTrue(web_lookup.should_search("latest mutual fund news", [{"id": "saved"}]))  # memory cannot be current

    def test_search_sends_only_the_question_cleans_results_and_skips_a_failed_source(self):
        with patch("apps.ml_engine.services.web_lookup.public_http.request", side_effect=fake_request) as request:
            results = web_lookup.search("current repo rate in India")
        self.assertEqual([item["ref"] for item in results], ["web-1", "web-2"])
        self.assertEqual(request.call_args_list[0].kwargs["params"], {"q": "current repo rate in India", "limit": 3})
        self.assertIn("current+repo+rate+in+India", request.call_args_list[1].args[1])
        self.assertEqual(results[0]["data"]["snippet"], "The repo rate is 6.5 percent")
        self.assertEqual(results[0]["url"], "https://en.wikipedia.org/wiki/Repo_rate")
        self.assertEqual(results[1]["data"]["source"], "Synthetic News")
        self.assertEqual(results[1]["data"]["snippet"], "Synthetic policy story")

        def wiki_down(method, url, **kwargs):
            if "wikipedia.org" in url: raise PublicHTTPError("timeout")
            return RSS
        with patch("apps.ml_engine.services.web_lookup.public_http.request", side_effect=wiki_down):
            self.assertEqual([item["data"]["source"] for item in web_lookup.search("repo rate")], ["Synthetic News"])
        with patch("apps.ml_engine.services.web_lookup.public_http.request") as request, self.assertRaises(web_lookup.PrivateQuestion):
            web_lookup.search("my account 123456789012")
        request.assert_not_called()

    def test_openai_gets_web_results_but_the_owner_part_is_still_checked(self):
        reasoner = OpenAIReasoner("sk-" + "a" * 30)
        web = [{"ref": "web-1", "title": "Home loan rates", "snippet": "Loan EMI rates 8.5 percent, account offers"}]
        body = reasoner.body({"query": "home rates explained", "memories": [], "web_results": web}, 1024)
        self.assertIn("web-1", body["input"])
        with self.assertRaises(PermissionError):
            reasoner.body({"query": "my account 123456789012", "memories": [], "web_results": web}, 1024)


class HybridWebLookupTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-web-lookup-synthetic-")))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root / "vault"), ALFRED_ABUSE_THROTTLE_DIR=str(root / "limits"),
            ALFRED_MEMORY_MOCK_REASONING=False, ALFRED_MEMORY_OPENAI_AUTHORIZED=False))
        self.enterContext(patch("apps.ml_engine.services.persistent_memory.OllamaEmbeddings", return_value=SyntheticEmbeddings()))
        self.enterContext(patch("apps.ml_engine.services.web_lookup.public_http.request", side_effect=fake_request))
        self.store = MemoryStore(root / "vault")
        self.user = get_user_model().objects.create_user(username="synthetic-web-lookup")
        self.local = Mock()
        self.enterContext(patch("apps.ml_engine.services.hybrid_intelligence.reasoning_provider", return_value=MockReasoner()))

    def ask(self, query="current repo rate in India", **kwargs):
        return hybrid_answer(self.store, self.user, query, local=self.local, **kwargs)

    def test_local_model_gets_web_results_and_a_cited_web_figure_is_shown(self):
        self.local.reason.return_value = "Home loan rates follow the repo rate, now 6.5 percent [web-1]."
        result = self.ask(web_search=True)
        payload = self.local.reason.call_args.args[0]
        self.assertEqual([s["ref"] for s in payload["sources"] if s["classification"] == "public_web_result"], ["web-1", "web-2"])
        self.assertFalse(result["narrative_withheld"]); self.assertTrue(result["cited_web_figures"])
        self.assertIn("https://en.wikipedia.org/wiki/Repo_rate", [s.get("url") for s in result["sources"]])

    def test_a_figure_no_cited_result_shows_is_still_withheld(self):
        self.local.reason.return_value = "Home loan rates will be 7.25 percent next year [web-1]."
        self.assertTrue(self.ask("repo rate interest outlook", web_search=True)["narrative_withheld"])

    def test_no_lookup_unless_asked_and_only_for_general_public_questions(self):
        self.local.reason.return_value = "Synthetic general answer."
        result = self.ask()
        self.assertFalse(any(s.get("classification") == "public_web_result" for s in result["sources"]))
        with self.assertRaises(ValueError): self.ask(scope="finance", web_search=True)
        with self.assertRaises(web_lookup.PrivateQuestion): self.ask("is 12 lakh a good salary", web_search=True)

    def test_without_the_tick_alfred_looks_online_only_when_the_question_needs_it(self):
        self.local.reason.return_value = "Synthetic general answer."
        web = lambda result: [s["ref"] for s in result["sources"] if s.get("classification") == "public_web_result"]
        with override_settings(ALFRED_ASSISTANT_AUTO_WEB=True):
            self.assertEqual(web(self.ask("latest repo rate news")), ["web-1", "web-2"])
            self.assertEqual(web(self.ask("what did I note about my trip")), [])
            self.assertEqual(web(self.ask("is 12 lakh a good salary today")), [])  # private-looking: never searched
            self.assertEqual(web(self.ask("latest repo rate news", scope="finance")), [])
        self.assertEqual(web(self.ask("latest repo rate news")), [])  # switched off

    def test_openai_answers_directly_when_chosen_with_consent(self):
        result = self.ask(web_search=True, provider="openai", cloud_consent=True, query_sensitivity="public")
        self.local.reason.assert_not_called()
        self.assertEqual(result["provider"], "mock")
        self.assertEqual([s["ref"] for s in result["sources"]], ["web-1", "web-2"])
        for refused in ({}, {"cloud_consent": True}, {"cloud_consent": True, "query_sensitivity": "public", "scope": "travel"}):
            with self.subTest(refused=refused), self.assertRaises(ValueError):
                self.ask(provider="openai", **refused)


@override_settings(ALFRED_MEMORY_MOCK_REASONING=False)
class WebLookupAPITests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.client.force_login(get_user_model().objects.create_user(username="synthetic-web-api"))

    def post(self, **body):
        return self.client.post("/api/ai/personal-insights/", {"query": "repo rate", **body}, content_type="application/json")

    def test_api_passes_the_choice_and_explains_a_private_question(self):
        with patch("apps.ml_engine.api.views.hybrid_answer", return_value={"answer": "ok", "provider": "ollama", "sources": []}) as answer:
            self.assertEqual(self.post(web_search=True).status_code, 200)
        self.assertIs(answer.call_args.kwargs["web_search"], True)
        self.assertEqual(answer.call_args.kwargs["provider"], "local")
        with patch("apps.ml_engine.api.views.hybrid_answer", side_effect=web_lookup.PrivateQuestion(web_lookup.PRIVATE_MESSAGE)):
            response = self.post(web_search=True)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "private_question")
        self.assertIn("did not search online", response.json()["detail"])
