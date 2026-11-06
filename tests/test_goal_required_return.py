"""Wealth 2.0: the yearly return a savings goal needs for a monthly amount the owner types; read-only."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.budgets.models import SavingsGoal
from apps.budgets.money import required_annual_return


class RequiredReturnTests(SimpleTestCase):
    def test_known_answers_and_bands(self):
        self.assertEqual(required_annual_return("100000", "0", "110000", 12), (Decimal("10.0"), "aggressive"))
        self.assertEqual(required_annual_return("0", "1000", "12000", 12), (Decimal("0"), "no_growth"))
        percent, band = required_annual_return("0", "1000", "12330", 12)  # about 6% a year: 330 earned on an average balance near 5,500
        self.assertEqual(band, "moderate")
        self.assertTrue(Decimal("5.8") < percent < Decimal("6.4"), percent)
        self.assertEqual(required_annual_return("1", "0", "1000000000", 12), (None, "unrealistic"))
        self.assertEqual(required_annual_return("100000", "0", "103000", 12)[1], "conservative")
        self.assertEqual(required_annual_return("100000", "0", "120000", 12)[1], "unrealistic")


class GoalPlanApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-goal-plan")
        self.client.force_login(self.owner)
        self.goal = SavingsGoal.objects.create(user=self.owner, name="Synthetic", target_amount=Decimal("120000.00"),
                                               saved_amount=Decimal("10000.00"), target_date=timezone.localdate() + timedelta(days=730))

    def plan(self, goal, amount):
        return self.client.get(f"/api/budgets/goals/{goal.pk}/plan/", {"monthly_contribution": amount})

    def test_plan_reports_return_band_and_assumptions_without_writing(self):
        before = SavingsGoal.objects.values().get(pk=self.goal.pk)
        data = self.plan(self.goal, "4000").json()
        self.assertEqual((data["currency"], data["months_left"]), ("INR", 24))
        self.assertGreater(data["required_annual_return_percent"], 0)
        self.assertIn(data["band"], {"conservative", "moderate", "aggressive", "unrealistic"})
        self.assertEqual(len(data["assumptions"]), 3)
        self.assertEqual(self.plan(self.goal, "5000").json()["band"], "no_growth")
        self.assertEqual(SavingsGoal.objects.values().get(pk=self.goal.pk), before)

    def test_bad_amounts_dates_and_other_owners_are_refused(self):
        for amount in ("-1", "abc", "", "NaN"):
            with self.subTest(amount=amount):
                self.assertEqual(self.plan(self.goal, amount).status_code, 400)
        undated = SavingsGoal.objects.create(user=self.owner, name="No date", target_amount=Decimal("100.00"))
        self.assertEqual(self.plan(undated, "1").status_code, 400)
        reached = SavingsGoal.objects.create(user=self.owner, name="Done", target_amount=Decimal("100.00"), saved_amount=Decimal("100.00"),
                                             target_date=timezone.localdate() + timedelta(days=60))
        self.assertEqual(self.plan(reached, "1").status_code, 400)
        other = get_user_model().objects.create_user(username="synthetic-goal-other")
        foreign = SavingsGoal.objects.create(user=other, name="Theirs", target_amount=Decimal("100.00"),
                                             target_date=timezone.localdate() + timedelta(days=60))
        self.assertEqual(self.plan(foreign, "1").status_code, 404)
