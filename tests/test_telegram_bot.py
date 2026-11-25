"""ALFRED on Telegram: only a code-linked private chat is answered, never with money, documents or saved history."""
import json
import os
from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services import telegram_bot
from apps.budgets.models import Budget
from apps.expenses.models import BankAccount, Expense
from apps.mobility.models import TravelPlan

TOKEN = {"ALFRED_TELEGRAM_BOT_TOKEN": "123456789:" + "A" * 35}


class TelegramBotTests(TestCase):
    def setUp(self):
        cache.clear()
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": self.enterContext(TemporaryDirectory(prefix="alfred-telegram-synthetic-")),
                                                  **TOKEN}))
        users = get_user_model().objects
        self.owner = users.create_user("synthetic-telegram-owner", password="synthetic-pass-123")
        self.other = users.create_user("synthetic-telegram-other", password="synthetic-pass-123")

    def linked(self, user=None, chat=111):
        self.assertTrue(telegram_bot.reply_to(chat, "/link " + telegram_bot.new_code(user or self.owner)).startswith("Linked."))
        return chat

    def test_only_a_chat_linked_with_a_fresh_code_is_answered(self):
        self.assertIn("not linked", telegram_bot.reply_to(111, "/trip"))
        code = telegram_bot.new_code(self.owner)
        self.assertTrue(telegram_bot.reply_to(111, f"/link {code}").startswith("Linked."))
        self.assertIn("expired", telegram_bot.reply_to(222, f"/link {code}"))  # one use only
        for _ in range(5):
            telegram_bot.reply_to(333, "/link 00000000")
        self.assertIn("Too many", telegram_bot.reply_to(333, "/link " + telegram_bot.new_code(self.other)))
        self.assertEqual(telegram_bot.links_for(self.owner), ["111"])
        self.assertIn("Unlinked", telegram_bot.reply_to(111, "/unlink"))
        self.assertIn("not linked", telegram_bot.reply_to(111, "/trip"))

    def test_each_chat_sees_only_its_own_persons_trip_and_follow_ups(self):
        today = timezone.localdate()
        TravelPlan.objects.create(user=self.other, title="Synthetic Other Trip", start_date=today + timedelta(days=1), status="planned")
        TravelPlan.objects.create(user=self.owner, title="Synthetic Hills", destination="Synthetic Valley",
                                  start_date=today + timedelta(days=5), status="planned")
        chat = self.linked()
        reply = telegram_bot.reply_to(chat, "/trip")
        self.assertIn("Synthetic Hills to Synthetic Valley", reply)
        self.assertNotIn("Other", reply)
        self.assertEqual(telegram_bot.reply_to(chat, "/followups"), "No career follow-ups are due.")

    def test_money_notices_never_reach_telegram(self):
        today = timezone.localdate()
        account = BankAccount.objects.create(user=self.owner, account_number="SYNTG01", account_type="savings", current_balance="50000.00", currency="INR")
        Expense.objects.create(user=self.owner, bank_account=account, amount="12000.50", category="Groceries", transaction_date=today,
                               direction="debit", currency="INR")
        Budget.objects.create(user=self.owner, month=today.strftime("%b %Y"), base_budget="10000.00", inflation_adjusted="10000.00", currency="INR")
        reply = telegram_bot.reply_to(self.linked(), "/notices")
        for private in ("₹", "12,000", "50000", "budget", "SYNTG01"):
            self.assertNotIn(private, reply)
        self.assertIn("Google Maps", reply)  # a non-money notice still comes through

    def test_questions_are_public_only_and_never_use_saved_history(self):
        chat = self.linked()
        with patch("apps.ml_engine.services.web_lookup.search") as search:
            self.assertIn("looks personal", telegram_bot.reply_to(chat, "my account 123456789012 balance"))
        search.assert_not_called()
        web = [{"ref": "web-1", "classification": "public_web_result", "url": "https://en.wikipedia.org/wiki/Lima", "data": {"title": "Lima"}}]
        with patch("apps.ml_engine.services.web_lookup.search", return_value=web), \
                patch("apps.ml_engine.services.hybrid_intelligence.OllamaReasoner.reason", return_value="Lima [web-1].") as reason, \
                patch("apps.ml_engine.services.hybrid_intelligence.OllamaReasoner.use_quick_model"), \
                patch("apps.ml_engine.services.hybrid_intelligence.OllamaReasoner.__init__", return_value=None):
            reply = telegram_bot.reply_to(chat, "What is the capital of Peru?")
        self.assertEqual(reply, "Lima [web-1].\n\nSources:\nhttps://en.wikipedia.org/wiki/Lima")
        self.assertEqual(set(reason.call_args.args[0]), {"query", "sources", "response_style"})  # no memories, history or records

    def test_polling_answers_private_chats_once_and_ignores_groups(self):
        chat = self.linked()
        updates = [{"update_id": 7, "message": {"chat": {"id": chat, "type": "private"}, "text": "/help"}},
                   {"update_id": 8, "message": {"chat": {"id": -5, "type": "group"}, "text": "/trip"}}]
        calls = []

        def call(method, body, **kwargs):
            calls.append((method, body))
            return updates if method == "getUpdates" else {}
        with patch.object(telegram_bot, "_call", side_effect=call):
            self.assertEqual(telegram_bot.poll_once(wait=0), 1)
            updates = []
            telegram_bot.poll_once(wait=0)
        sent = [body for method, body in calls if method == "sendMessage"]
        self.assertEqual([body["chat_id"] for body in sent], [chat])
        self.assertEqual(calls[-1], ("getUpdates", {"offset": 9, "timeout": 0, "allowed_updates": ["message"]}))

    def test_a_failed_send_does_not_log_the_token(self):
        updates = [{"update_id": 1, "message": {"chat": {"id": 5, "type": "private"}, "text": "/help"}}]
        with patch.object(telegram_bot, "_call", side_effect=lambda method, body, **k: updates if method == "getUpdates" else 1 / 0), \
                self.assertLogs("alfred_ai.services.telegram_bot", "WARNING") as logs:
            telegram_bot.poll_once(wait=0)
        self.assertNotIn(TOKEN["ALFRED_TELEGRAM_BOT_TOKEN"], "\n".join(logs.output))

    def test_settings_gives_a_code_only_when_a_bot_is_set_up(self):
        self.client.force_login(self.owner)
        data = self.client.post("/api/settings/telegram/", json.dumps({"action": "code"}), content_type="application/json").json()
        self.assertRegex(data["code"], r"^\d{8}$")
        with patch.dict(os.environ, {"ALFRED_TELEGRAM_BOT_TOKEN": "not-a-token"}):
            data = self.client.post("/api/settings/telegram/", json.dumps({"action": "code"}), content_type="application/json").json()
        self.assertFalse(data["configured"]); self.assertIsNone(data["code"])
        self.linked()
        self.assertEqual(self.client.get("/api/settings/telegram/").json()["linked"], 1)
        self.client.post("/api/settings/telegram/", json.dumps({"action": "unlink"}), content_type="application/json")
        self.assertEqual(telegram_bot.links_for(self.owner), [])
        self.assertEqual(self.client.post("/api/settings/telegram/", "{}", content_type="application/json").status_code, 400)
