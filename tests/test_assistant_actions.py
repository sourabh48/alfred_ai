"""AI-17: proposals change nothing; only an owner-confirmed, allow-listed action is saved."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.budgets.models import SavingsGoal
from apps.ml_engine.services.assistant_actions import ActionError, propose

TODAY = date(2026, 11, 6)


class AssistantActionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-action-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-action-other")
        self.client.force_login(self.owner)

    def test_create_requests_parse_indian_units_and_dates(self):
        cases = {
            "Add a savings goal Emergency fund of 1.5 lakh by March 2027": ("Emergency fund", "150000.00", "2027-03-31"),
            "create savings goal called 'Goa trip' for ₹50,000.50": ("Goa trip", "50000.50", None),
            "please set up a new savings goal named Bike for 75k before 2027-01-15.": ("Bike", "75000.00", "2027-01-15"),
            "add a savings goal House for 1 crore by 31 December 2030": ("House", "10000000.00", "2030-12-31"),
        }
        for text, (name, target, due) in cases.items():
            with self.subTest(text=text):
                proposal = propose(self.owner, text, TODAY)
                self.assertEqual(proposal["action"], "create_savings_goal")
                self.assertEqual((proposal["fields"]["name"], proposal["fields"]["target_amount"], proposal["fields"].get("target_date")), (name, target, due))
        self.assertFalse(SavingsGoal.objects.exists())

    def test_ordinary_questions_and_bad_values_make_no_proposal(self):
        for text in ("How much did I spend on food?", "transfer 5000 to my savings account", "", None, "buy 10 shares"):
            with self.subTest(text=text):
                self.assertIsNone(propose(self.owner, text, TODAY))
        for text in ("add a savings goal X of 100 by 2026-11-01", "add a savings goal X of 100 by someday"):
            with self.subTest(text=text), self.assertRaises(ActionError):
                propose(self.owner, text, TODAY)

    def test_propose_then_confirm_saves_exact_cents_and_cancel_saves_nothing(self):
        with patch("django.utils.timezone.localdate", return_value=TODAY):
            response = self.client.post("/api/ai/actions/propose/", {"text": "add a savings goal Car of 2,00,000.25 by June 2027"}, content_type="application/json")
        proposal = response.json()["proposal"]
        self.assertIn("₹200,000.25", proposal["summary"])
        self.assertFalse(SavingsGoal.objects.exists())
        unconfirmed = self.client.post("/api/ai/actions/confirm/", {"action": proposal["action"], "fields": proposal["fields"]}, content_type="application/json")
        self.assertEqual(unconfirmed.status_code, 400)
        self.assertFalse(SavingsGoal.objects.exists())
        saved = self.client.post("/api/ai/actions/confirm/", {**proposal, "confirmed": True}, content_type="application/json")
        self.assertEqual(saved.status_code, 201, saved.content)
        goal = SavingsGoal.objects.get()
        self.assertEqual((goal.user, goal.target_amount, goal.target_date), (self.owner, Decimal("200000.25"), date(2027, 6, 30)))

    def test_update_only_touches_the_owners_named_goal(self):
        mine = SavingsGoal.objects.create(user=self.owner, name="Emergency fund", target_amount="1000.00")
        theirs = SavingsGoal.objects.create(user=self.other, name="Travel", target_amount="1000.00")
        proposal = self.client.post("/api/ai/actions/propose/", {"text": "update emergency fund saved to 250.10"}, content_type="application/json").json()["proposal"]
        self.assertEqual(proposal["fields"], {"id": mine.pk, "saved_amount": "250.10"})
        self.assertIsNone(self.client.post("/api/ai/actions/propose/", {"text": "update Travel saved to 5"}, content_type="application/json").json()["proposal"])
        forged = self.client.post("/api/ai/actions/confirm/", {"action": "update_savings_goal", "fields": {"id": theirs.pk, "saved_amount": "5"}, "confirmed": True}, content_type="application/json")
        self.assertEqual(forged.status_code, 400)
        self.assertEqual(self.client.post("/api/ai/actions/confirm/", {**proposal, "confirmed": True}, content_type="application/json").status_code, 201)
        mine.refresh_from_db(); theirs.refresh_from_db()
        self.assertEqual((mine.saved_amount, theirs.saved_amount), (Decimal("250.10"), Decimal("0")))

    def test_unknown_actions_and_invalid_values_are_refused(self):
        for payload in ({"action": "transfer_money", "fields": {"amount": "5"}, "confirmed": True},
                        {"action": "create_savings_goal", "fields": {"name": "X", "target_amount": "-1"}, "confirmed": True},
                        {"action": "create_savings_goal", "fields": "not-a-dict", "confirmed": True}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/api/ai/actions/confirm/", payload, content_type="application/json").status_code, 400)
        self.assertFalse(SavingsGoal.objects.exists())
        self.client.logout()
        self.assertIn(self.client.post("/api/ai/actions/propose/", {"text": "x"}, content_type="application/json").status_code, {401, 403})
