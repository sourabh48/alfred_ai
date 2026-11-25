"""PostHog usage counts: ALFRED sends whenever a project key is set, and only allow-listed, non-sensitive values leave the PC."""
import json
import os
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alfred_ai.services import usage_analytics

ON = {"ALFRED_POSTHOG_PROJECT_KEY": "phc_synthetic_project_key"}


@override_settings(ALFRED_MEMORY_MOCK_REASONING=False)
class UsageAnalyticsTests(TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": self.enterContext(TemporaryDirectory(prefix="alfred-analytics-synthetic-"))}))
        self.user = get_user_model().objects.create_user("synthetic-analytics", password="synthetic-pass-123", first_name="Synthia")
        self.client.force_login(self.user)
        self.queued = []
        self.enterContext(patch.object(usage_analytics, "_queue", type("Q", (), {"put_nowait": lambda _, item: self.queued.append(item)})()))
        self.enterContext(patch.object(usage_analytics, "_start"))

    def test_nothing_is_recorded_without_a_project_key_an_approved_host_or_when_stopped(self):
        for env in ({}, {"ALFRED_USAGE_ANALYTICS": "true"}, {**ON, "ALFRED_USAGE_ANALYTICS": "false"},
                    {**ON, "ALFRED_POSTHOG_HOST": "https://posthog.evil.example"}):
            with self.subTest(env=env), patch.dict(os.environ, env):
                usage_analytics.record("page_viewed", {"page": "index"})
                self.client.get("/")
        self.assertEqual(self.queued, [])

    def test_only_allow_listed_events_and_values_are_kept(self):
        self.assertIsNone(usage_analytics.clean("expense_added", {"amount": "12000"}))
        kept = usage_analytics.clean("assistant_answered", {
            "scope": "finance", "model": "fast", "seconds": 3.456, "thinking": False, "web_results": True,
            "question": "What is my EMI?", "answer": "₹12,000", "email": "synthia@example.org"})
        self.assertEqual(kept, {"scope": "finance", "model": "fast", "seconds": 3.5, "thinking": False, "web_results": True})
        self.assertEqual(usage_analytics.clean("assistant_answered", {"scope": "my salary", "model": "qwen3.5:9b", "seconds": "3"}), {})
        self.assertEqual(usage_analytics.clean("page_viewed", {"page": "/loans/42/?q=Bajaj"}), {})
        with override_settings(ALFRED_QUICK_OLLAMA_MODEL="qwen3.5:9b"):
            self.assertEqual((usage_analytics.model_tier("qwen3.5:9b"), usage_analytics.model_tier("my-own-model:1b")), ("fast", "main"))

    def test_pages_are_counted_by_route_name_and_the_batch_carries_no_person(self):
        with patch.dict(os.environ, ON):
            self.client.get("/")
            self.client.get("/api/ai/speech/status/")  # API calls are not page views
            self.assertEqual([(item["event"], item["properties"]) for item in self.queued], [("page_viewed", {"page": "index"})])
            with patch("alfred_ai.services.public_http.request") as request:
                self.assertTrue(usage_analytics.send(self.queued + self.queued))
        method, url = request.call_args.args
        self.assertEqual((method, url), ("POST", "https://eu.i.posthog.com/batch/"))
        body = request.call_args.kwargs["json_body"]
        events = body["batch"]
        self.assertEqual(len({event["distinct_id"] for event in events}), 1)  # one random ID for the whole PC
        self.assertTrue(all(event["properties"]["$process_person_profile"] is False and event["properties"]["$geoip_disable"] for event in events))
        sent = json.dumps(events)
        for private in ("synthetic-analytics", "Synthia", "@"):
            self.assertNotIn(private, sent)
        # The account ID as a value, not as text: a random ID or timestamp can end in the same digit (failed CI 2026-11-25/26).
        values, pending = [], list(events)
        while pending:
            item = pending.pop()
            if isinstance(item, dict): pending.extend(item.values())
            elif isinstance(item, list): pending.extend(item)
            else: values.append(item)
        self.assertFalse({self.user.pk, str(self.user.pk)} & {value for value in values if isinstance(value, (int, str)) and not isinstance(value, bool)})

    def test_a_local_answer_reports_topic_model_tier_and_seconds_only(self):
        result = {"answer": "Synthetic EMI is ₹12,000.", "provider": "ollama", "local_model": "qwen3.5:9b", "answer_seconds": 2.04,
                  "local_thinking": False, "sources": [{"classification": "public_web_result", "url": "https://example.org"}]}
        with patch.dict(os.environ, ON), override_settings(ALFRED_QUICK_OLLAMA_MODEL="qwen3.5:9b"), \
                patch("apps.ml_engine.api.views.hybrid_answer", return_value=result):
            self.assertEqual(self.client.post("/api/ai/personal-insights/", {"query": "What is my EMI?", "scope": "finance"}, content_type="application/json").status_code, 200)
        answered = [item["properties"] for item in self.queued if item["event"] == "assistant_answered"]
        self.assertEqual(answered, [{"scope": "finance", "model": "fast", "seconds": 2.0, "thinking": False, "web_results": True}])
        self.assertNotIn("EMI", json.dumps(self.queued))

    def test_a_failed_send_never_breaks_alfred(self):
        with patch.dict(os.environ, ON), patch("alfred_ai.services.public_http.request", side_effect=OSError("offline")):
            self.assertFalse(usage_analytics.send([{"event": "page_viewed", "properties": {"page": "index"}, "timestamp": "t"}]))
