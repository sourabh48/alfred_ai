"""A2A agent links: a Settings token is always required, only nearby addresses are served, answers stay read-only."""
import json
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from alfred_ai.services import agent_link
from apps.mobility.models import TravelPlan


class AgentLinkTests(TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": self.enterContext(TemporaryDirectory(prefix="alfred-a2a-synthetic-"))}))
        self.owner = get_user_model().objects.create_user("synthetic-a2a-owner", password="synthetic-pass-123")
        TravelPlan.objects.create(user=self.owner, title="Synthetic Coast", start_date=timezone.localdate() + timedelta(days=4), status="planned")
        self.agent = Client(REMOTE_ADDR="192.168.1.20")

    def ask(self, text, token, client=None, method="tasks/send"):
        body = {"jsonrpc": "2.0", "id": "r1", "method": method, "params": {"id": "t1", "message": {"role": "user", "parts": [{"type": "text", "text": text}]}}}
        return (client or self.agent).post("/a2a/tasks", json.dumps(body), content_type="application/json",
                                           **({"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}))

    def test_a_token_from_settings_is_required_and_shown_once(self):
        self.client.force_login(self.owner)
        made = self.client.post("/api/settings/agent-links/", json.dumps({"action": "create"}), content_type="application/json").json()
        token = made["token"]
        self.assertTrue(token.startswith("alfred_a2a_"))
        self.assertIsNone(self.client.get("/api/settings/agent-links/").json()["token"])
        self.assertNotIn(token, agent_link._path().read_text(encoding="utf-8"))  # only its hash is kept
        self.assertEqual(self.ask("/trip", None).status_code, 401)
        self.assertEqual(self.ask("/trip", "alfred_a2a_wrong").status_code, 401)
        reply = self.ask("/trip", token).json()
        self.assertEqual(reply["result"]["status"]["state"], "completed")
        self.assertIn("Synthetic Coast", reply["result"]["artifacts"][0]["parts"][0]["text"])
        self.assertIn("Synthetic Coast", self.ask("/trip", token, method="message/send").json()["result"]["artifacts"][0]["parts"][0]["text"])
        self.client.post("/api/settings/agent-links/", json.dumps({"action": "revoke"}), content_type="application/json")
        self.assertEqual(self.ask("/trip", token).status_code, 401)

    def test_only_this_pc_and_the_home_network_are_served(self):
        token = agent_link.new_token(self.owner)
        self.assertEqual(self.ask("/trip", token, client=Client(REMOTE_ADDR="203.0.113.9")).status_code, 403)
        self.assertEqual(Client(REMOTE_ADDR="203.0.113.9").get("/.well-known/agent.json").status_code, 403)
        for outside in ("8.8.8.8", "169.254.1.1", "100.64.0.1", "2001:db8::1"):
            self.assertFalse(agent_link.nearby(outside), outside)
        for inside in ("127.0.0.1", "::1", "192.168.1.9", "172.20.0.2", "::ffff:192.168.1.9", "fd00::5"):
            self.assertTrue(agent_link.nearby(inside), inside)
        card = Client(REMOTE_ADDR="10.0.0.5").get("/.well-known/agent.json").json()
        self.assertEqual(card["authentication"], {"schemes": ["bearer"]})
        self.assertNotIn("synthetic-a2a-owner", json.dumps(card))

    def test_answers_are_the_read_only_set_and_other_methods_are_refused(self):
        token = agent_link.new_token(self.owner)
        with patch("alfred_ai.services.telegram_bot.public_answer", return_value="Public answer.") as public:
            self.assertEqual(self.ask("What is the capital of Peru?", token).json()["result"]["artifacts"][0]["parts"][0]["text"], "Public answer.")
        public.assert_called_once()
        refused = self.agent.post("/a2a/tasks", json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tasks/cancel", "params": {}}),
                                  content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}").json()
        self.assertEqual(refused["error"]["code"], -32601)
        self.assertEqual(self.ask("", token).json()["error"]["code"], -32602)
