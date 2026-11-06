"""FIN-06: owner savings goals in INR with Decimal progress."""
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.budgets.models import SavingsGoal
from apps.budgets.money import goal_progress
from apps.users.services import clear_user_fed_data

TODAY = date(2026, 11, 6)


class GoalProgressTests(TestCase):
    def test_monthly_amount_rounds_up_to_the_cent_and_handles_edges(self):
        result = goal_progress(Decimal("100000.00"), Decimal("10000.01"), date(2027, 2, 1), TODAY)
        self.assertEqual(result["remaining"], Decimal("89999.99"))
        self.assertEqual(result["months_left"], 3)
        self.assertEqual(result["monthly_needed"], Decimal("30000.00"))
        self.assertEqual(result["percent"], Decimal("10.0"))
        self.assertEqual(goal_progress(Decimal("10"), Decimal("0"), date(2026, 11, 30), TODAY)["months_left"], 1)
        self.assertEqual(goal_progress(Decimal("10"), Decimal("0"), date(2027, 11, 6), TODAY)["monthly_needed"], Decimal("0.84"))
        reached = goal_progress(Decimal("10"), Decimal("12"), None, TODAY)
        self.assertEqual((reached["status"], reached["remaining"], reached["percent"]), ("reached", Decimal("0"), Decimal("100.0")))
        overdue = goal_progress(Decimal("10"), Decimal("4"), date(2026, 11, 5), TODAY)
        self.assertEqual((overdue["status"], overdue["monthly_needed"]), ("overdue", None))
        self.assertIsNone(goal_progress(Decimal("10"), Decimal("4"), None, TODAY)["monthly_needed"])


class SavingsGoalApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-goal-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-goal-other")
        self.client.force_login(self.owner)

    def test_create_update_list_and_delete_keep_exact_cents(self):
        with patch("django.utils.timezone.localdate", return_value=TODAY):
            response = self.client.post("/api/budgets/goals/", {"name": "  Synthetic   fund ", "target_amount": "100000.00",
                "saved_amount": "10000.01", "target_date": "2027-02-01"}, content_type="application/json")
        self.assertEqual(response.status_code, 201, response.content)
        goal = SavingsGoal.objects.get()
        self.assertEqual((goal.user, goal.name, goal.saved_amount), (self.owner, "Synthetic fund", Decimal("10000.01")))
        self.assertEqual(response.json()["progress"]["monthly_needed"], 30000.0)
        response = self.client.patch(f"/api/budgets/goals/{goal.pk}/", {"saved_amount": "20000.10"}, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        goal.refresh_from_db()
        self.assertEqual((goal.saved_amount, goal.target_amount), (Decimal("20000.10"), Decimal("100000.00")))
        self.assertEqual([item["id"] for item in self.client.get("/api/budgets/goals/").json()], [goal.pk])
        self.assertEqual(self.client.delete(f"/api/budgets/goals/{goal.pk}/").status_code, 204)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_invalid_amounts_and_names_are_rejected_without_writes(self):
        for payload in ({"name": "x", "target_amount": "0"}, {"name": "x", "target_amount": "-5"},
                        {"name": "x", "target_amount": "NaN"}, {"name": "   ", "target_amount": "10"},
                        {"name": "x", "target_amount": "10", "saved_amount": "-1"}, {"name": "x", "target_amount": "1e20"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/api/budgets/goals/", payload, content_type="application/json").status_code, 400)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_other_owners_goals_are_invisible_and_untouchable(self):
        foreign = SavingsGoal.objects.create(user=self.other, name="FOREIGN-GOAL", target_amount="10.00")
        self.assertNotIn("FOREIGN-GOAL", self.client.get("/api/budgets/goals/").content.decode())
        for method in ("get", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(f"/api/budgets/goals/{foreign.pk}/", {"saved_amount": "5"}, content_type="application/json")
                self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.saved_amount, Decimal("0"))
        self.client.logout()
        self.assertIn(self.client.get("/api/budgets/goals/").status_code, {401, 403})

    def test_user_data_reset_removes_only_that_owners_goals(self):
        SavingsGoal.objects.create(user=self.owner, name="Mine", target_amount="10.00")
        SavingsGoal.objects.create(user=self.other, name="Theirs", target_amount="10.00")
        clear_user_fed_data(self.owner)
        self.assertEqual(list(SavingsGoal.objects.values_list("name", flat=True)), ["Theirs"])
