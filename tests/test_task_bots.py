"""Proactive travel steps and in-app task bots on synthetic records only; nothing changes before Confirm."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.career.models import CareerJobAnalysis
from apps.expenses.models import Expense
from apps.investments.models import Investment
from apps.loans.models import Loan
from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord, TravelPlan, TravelPlanningSession, TravelResearchSession
from apps.mobility.services.travel import proactive, reminders
from apps.ml_engine.services import task_bots
from apps.reports.models import OperationalLog
from apps.reports.services import operational_logging_service
from alfred_ai import native_tasks
from tests import test_travel_planner as planner_fixtures

URL = "/api/ai/bots/"


def financial_rows():
    return [list(model.objects.order_by("pk").values()) for model in (Expense, Loan, Investment)]


class Fixtures(TestCase):
    def setUp(self):
        self.enterContext(patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("No network in bot tests")))
        self.dispatch = self.enterContext(patch("apps.mobility.services.travel_research.dispatch"))
        self.today = timezone.localdate()
        self.user = get_user_model().objects.create_user("synthetic-bot-owner", password="Test12345!", city="Bengaluru")
        self.other = get_user_model().objects.create_user("synthetic-bot-other", password="Test12345!")
        self.client.force_login(self.user)

    def trip(self, days=5, user=None, **fields):
        user = user or self.user
        plan = TravelPlan.objects.create(user=user, title="Synthetic Coorg ride", destination="Coorg", status="planned",
            start_date=self.today + timedelta(days=days), end_date=self.today + timedelta(days=days + 2), transport_mode="ride", **fields)
        TravelPlanningSession.objects.create(user=user, plan=plan, title=plan.title, state={})
        return TravelPlan.objects.select_related("planning_session").get(pk=plan.pk)

    def post(self, **data):
        return self.client.post(URL, data, content_type="application/json")


class ProactiveTravelTests(Fixtures):
    def test_saved_trip_gets_next_steps_from_its_own_records(self):
        plan = self.trip(days=5)
        kinds = {step["kind"]: step for step in proactive.next_steps(plan, self.today)}
        self.assertEqual(set(kinds), {"weather", "stay", "packing", "reminder"})
        self.assertEqual(kinds["weather"]["action"], {"type": "recheck"})
        self.assertIn("never books", kinds["stay"]["detail"])
        self.assertTrue(all(link["url"].startswith("https://") for link in kinds["stay"]["links"]))
        self.assertEqual(kinds["reminder"]["action"]["local_time"], f"{plan.start_date - timedelta(days=1)}T18:00")
        self.assertTrue(kinds["reminder"]["action"]["enable"])
        self.assertNotIn(reminders.KEY, TravelPlan.objects.get(pk=plan.pk).planning_state)  # read-only

    def test_far_trip_waits_for_forecast_window_and_closed_trips_get_nothing(self):
        plan = self.trip(days=25)
        weather = next(step for step in proactive.next_steps(plan, self.today) if step["kind"] == "weather")
        self.assertEqual(weather["title"], "Weather check opens later")
        self.assertIsNone(weather["action"])
        self.assertEqual(weather["due_on"], str(plan.start_date - timedelta(days=9)))
        plan.status = "cancelled"
        self.assertEqual(proactive.next_steps(plan, self.today), [])

    def test_changes_from_a_recheck_and_bike_records_are_flagged(self):
        bike = BikeProfile.objects.create(user=self.user, display_name="Synthetic bike", model_name="Synthetic 350")
        BikeServiceRecord.objects.create(user=self.user, bike_profile=bike, bike_name="Synthetic bike", service_date=self.today - timedelta(days=200),
                                         next_service_date=self.today + timedelta(days=3))
        plan = self.trip(days=5, vehicle_profile=bike)
        TravelResearchSession.objects.create(session=plan.planning_session, recheck=True, status="ready", completed_at=timezone.now(),
                                             changes=["Coorg: forecast rain changed from 2 to 40 mm across the trip."])
        steps = proactive.next_steps(plan, self.today)
        self.assertIn("forecast rain changed from 2 to 40 mm", next(s for s in steps if s["kind"] == "changed")["detail"])
        self.assertTrue(any("service due" in s["detail"].lower() for s in steps if s["kind"] == "vehicle"))
        self.assertNotIn("weather", {s["kind"] for s in steps})  # a check from today is current

    def test_trip_ideas_use_the_next_free_weekend_and_say_what_is_unchecked(self):
        saturday = self.today + timedelta(days=(5 - self.today.weekday()) % 7 or 7)
        TravelPlan.objects.create(user=self.user, title="Busy", status="planned", start_date=saturday, end_date=saturday + timedelta(days=1))
        result = proactive.trip_ideas(self.user, self.today)
        self.assertEqual(result["free_dates"]["start"], str(saturday + timedelta(days=7)))
        self.assertTrue(result["ideas"])
        self.assertTrue(all(idea["source_freshness"] == "STATIC_REFERENCE" for idea in result["ideas"]))
        self.assertIn("not checked", result["note"])
        self.assertEqual(proactive.trip_ideas(self.other, self.today)["ideas"], [])  # no home city, no guess

    def test_suggestions_endpoint_is_owner_only_and_not_cached(self):
        plan = self.trip(days=5)
        response = self.client.get(f"/api/mobility/planner/suggestions/?session={plan.planning_session.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertTrue(response.json()["next_steps"])
        self.assertEqual(self.client.get("/api/mobility/planner/suggestions/").json()["next_steps"], response.json()["next_steps"])
        other = self.trip(days=5, user=self.other)
        self.assertEqual(self.client.get(f"/api/mobility/planner/suggestions/?session={other.planning_session.pk}").status_code, 404)
        self.assertEqual(self.client.get("/api/mobility/planner/suggestions/?session=x").status_code, 400)


class TaskBotTests(Fixtures):
    def spend(self, amount, days_ago=1, category="food"):
        return Expense.objects.create(user=self.user, amount=Decimal(amount), category=category, currency="INR",
                                      transaction_date=self.today - timedelta(days=days_ago), description="Synthetic spend")

    def test_weekly_money_review_is_decimal_exact_deduplicated_and_superseded(self):
        self.spend("1200.50"); self.spend("99.50", category="travel"); self.spend("10.00", days_ago=9); self.spend("5.25", category="other")
        first = self.post(operation="run", bot="money_review").json()["proposal"]
        self.assertEqual(first["items"][0]["title"], "Spent ₹1,305.25 in the last 7 days")
        self.assertIn("The 7 days before: ₹10.00", first["items"][0]["detail"])
        self.assertEqual(first["items"][1]["id"], "uncategorised")
        self.assertEqual(self.post(operation="run", bot="money_review").json()["proposal"]["proposal_id"], first["proposal_id"])
        self.spend("1.00")
        second = self.post(operation="run", bot="money_review").json()["proposal"]
        self.assertNotEqual(second["proposal_id"], first["proposal_id"])
        self.assertEqual([p["proposal_id"] for p in self.client.get(URL).json()["proposals"]], [second["proposal_id"]])

    def test_confirm_marks_reviewed_and_rejects_stale_tampered_or_repeated_reviews(self):
        self.spend("50.00")
        before = financial_rows()
        proposal = task_bots.run(self.user, "money_review", self.today)
        confirm = dict(operation="confirm", proposal_id=proposal["proposal_id"], item_ids=[proposal["items"][0]["id"]],
                       fingerprint=proposal["fingerprint"], confirmed=True)
        self.assertEqual(self.post(**{**confirm, "confirmed": False}).status_code, 400)
        self.assertEqual(self.post(**{**confirm, "fingerprint": "0" * 64}).status_code, 400)
        self.assertEqual(self.post(**{**confirm, "item_ids": ["invented"]}).status_code, 400)
        self.assertEqual(self.post(**{**confirm, "extra": 1}).status_code, 400)
        self.spend("7.00")  # the records the review depends on changed
        self.assertEqual(self.post(**confirm).status_code, 409)
        stale = OperationalLog.objects.get(payload__proposal_id=proposal["proposal_id"])
        self.assertEqual(stale.event_type, task_bots.PENDING)
        fresh = task_bots.run(self.user, "money_review", self.today)
        confirm.update(proposal_id=fresh["proposal_id"], item_ids=[fresh["items"][0]["id"]], fingerprint=fresh["fingerprint"])
        response = self.post(**confirm)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("Nothing else changed", response.json()["message"])
        self.assertEqual(self.post(**confirm).status_code, 409)
        self.assertEqual(financial_rows()[1:], before[1:])
        self.assertEqual(len(financial_rows()[0]), len(before[0]) + 1)  # only the test's own new spend

    def test_travel_prep_reminder_applies_once_only_after_confirm(self):
        plan = self.trip(days=5)
        proposal = self.post(operation="run", bot="travel_prep").json()["proposal"]
        item = next(item for item in proposal["items"] if item["action"] and item["action"]["type"] == "reminder")
        self.assertNotIn(reminders.KEY, TravelPlan.objects.get(pk=plan.pk).planning_state)
        self.assertEqual(self.client.get(f"/mobility/?session={plan.planning_session.pk}").status_code, 200)
        response = self.post(operation="confirm", proposal_id=proposal["proposal_id"], item_ids=[item["id"]],
                             fingerprint=proposal["fingerprint"], confirmed=True)
        self.assertEqual(response.status_code, 200, response.content)
        policy = reminders.reminder_payload(plan.planning_session)
        self.assertTrue(policy["enabled"])
        self.assertEqual([(r["local_time"], r["status"]) for r in policy["reminders"]], [(f"{plan.start_date - timedelta(days=1)}T18:00", "scheduled")])
        self.dispatch.assert_not_called()  # the recheck item was not chosen

    def test_travel_prep_recheck_queues_research_when_chosen(self):
        plan = self.trip(days=5)
        proposal = task_bots.run(self.user, "travel_prep", self.today)
        item = next(item for item in proposal["items"] if item["action"] and item["action"]["type"] == "recheck")
        task_bots.confirm(self.user, proposal["proposal_id"], [item["id"]], proposal["fingerprint"], self.today)
        self.assertTrue(TravelResearchSession.objects.filter(session=plan.planning_session, recheck=True).exists())

    def test_bills_paperwork_and_career_bots_read_only_their_owner_records(self):
        Loan.objects.create(user=self.user, lender="Synthetic Bank", principal=Decimal("100000"), interest_rate=9.5, emi=Decimal("4321.00"),
                            currency="INR", start_date=(self.today + timedelta(days=3)).replace(year=self.today.year - 1))
        Loan.objects.create(user=self.other, lender="Other Bank", principal=Decimal("1"), interest_rate=1, emi=Decimal("1"),
                            start_date=self.today.replace(year=self.today.year - 1))
        bills = task_bots.run(self.user, "bills_due", self.today)
        self.assertEqual(len(bills["items"]), 1)
        self.assertIn("EMI ₹4,321.00 to Synthetic Bank", bills["items"][0]["title"])
        self.assertIn("never pays", bills["items"][0]["detail"])
        BikeDocument.objects.create(user=self.user, bike_name="Synthetic bike", document_type="insurance", expiry_date=self.today + timedelta(days=10))
        BikeDocument.objects.create(user=self.user, bike_name="Synthetic bike", document_type="puc", expiry_date=self.today + timedelta(days=200))
        papers = task_bots.run(self.user, "paperwork", self.today)
        self.assertEqual([item["title"] for item in papers["items"]], [f"Synthetic bike INSURANCE expires {self.today + timedelta(days=10):%d %b %Y}"])
        applied = (self.today - timedelta(days=30)).isoformat()
        CareerJobAnalysis.objects.create(user=self.user, job_title="Synthetic Analyst", company="Example Co",
            extracted_payload={"application": {"stage": "applied", "history": [{"stage": "applied", "on": applied}], "follow_ups": []}})
        career = task_bots.run(self.user, "career_follow_ups", self.today)
        self.assertEqual(career["items"][0]["title"], "Follow up: Synthetic Analyst at Example Co")
        self.assertIn("nothing is sent", career["items"][0]["detail"])
        self.assertIsNone(task_bots.run(self.other, "career_follow_ups", self.today))

    def test_fund_review_reports_drops_and_abstains_when_prices_are_missing(self):
        Investment.objects.create(user=self.user, asset_name="Synthetic Flexi Cap", amfi_scheme_code="100001", currency="INR",
                                  invested_amount=Decimal("1000"), current_value=Decimal("1000"))
        navs = ["100"] * 18 + ["90", "80"]  # enough fresh daily prices for a signal; the parser gives real dates
        history = {"series": [{"scheme_code": "100001", "nav_date": self.today - timedelta(days=len(navs) - index), "nav": Decimal(nav)}
                              for index, nav in enumerate(navs)]}
        target = "apps.investments.services.portfolio_intelligence.portfolio_intelligence_service._get_amfi_history_report"
        with patch(target, return_value=history):
            proposal = task_bots.run(self.user, "fund_review", self.today)
        self.assertEqual(proposal["items"][0]["title"], "Synthetic Flexi Cap: Sell")
        self.assertIn("never buys or sells", proposal["items"][0]["detail"])
        with patch(target, side_effect=OSError("offline")):
            response = self.post(operation="run", bot="fund_review")
        self.assertEqual(response.status_code, 400)
        self.assertIn("not available", response.json()["detail"])

    def test_owner_isolation_and_audit_redaction(self):
        self.spend("10.00")
        proposal = task_bots.run(self.user, "money_review", self.today)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(URL).json()["proposals"], [])
        self.assertEqual(self.post(operation="dismiss", proposal_id=proposal["proposal_id"]).status_code, 400)
        self.assertEqual(self.post(operation="run", bot="shell").status_code, 400)
        record = OperationalLog.objects.get(payload__proposal_id=proposal["proposal_id"])
        self.assertEqual(set(operational_logging_service.serialize(record)["payload"]), {"bot", "state", "for_date"})
        self.client.force_login(self.user)
        self.assertEqual(self.post(operation="dismiss", proposal_id=proposal["proposal_id"]).status_code, 200)
        self.assertEqual(self.client.get(URL).json()["proposals"], [])
        self.client.logout()
        self.assertIn(self.client.get(URL).status_code, (401, 403))

    def test_daily_schedule_runs_each_bot_once_per_cadence_and_survives_one_failure(self):
        self.spend("10.00")
        self.trip(days=5)
        with patch.dict(task_bots.BOTS, fund_review=("Fund review", 1, lambda user, today: 1 / 0, "")):
            first = native_tasks.DAILY_JOBS["task-bots"]()
        self.assertGreaterEqual(first["failed"], 1)
        self.assertTrue(task_bots.pending(self.user))
        self.assertTrue(all(p["proposal_id"] for p in task_bots.pending(self.user)))
        with patch.object(task_bots, "run", wraps=task_bots.run) as again:
            task_bots.run_scheduled(self.today)
        self.assertNotIn("money_review", {call.args[1] for call in again.call_args_list if call.args[0] == self.user})
        self.assertEqual(task_bots.run_scheduled(self.today + timedelta(days=7))["status"], "completed")


class RecheckRouteChangeTests(TestCase):
    setUp, ready, chosen = (getattr(planner_fixtures.TravelPlannerTests, name) for name in ("setUp", "ready", "chosen"))

    def test_recheck_reports_a_changed_route_distance(self):
        from apps.mobility.services.travel_research import queue_research, run_research
        session = self.chosen()
        name = session.candidates[0]["name"]
        session.candidates[0]["distance_km"] = (session.candidates[0].get("distance_km") or 100) + 150
        session.save(update_fields=["candidates"])
        run = queue_research(session, recheck=True)
        run_research(run.id)
        run.refresh_from_db()
        self.assertTrue(any(change.startswith(f"{name}: route distance changed") for change in run.changes), run.changes)


class MoreBotsTests(Fixtures):
    """Auto-categorise acts only on Confirm; the other five bots only read the owner's records."""

    def row(self, merchant, amount, days_ago=1, category="other", user=None, **fields):
        return Expense.objects.create(user=user or self.user, merchant=merchant, amount=Decimal(amount), category=category,
                                      currency="INR", transaction_date=self.today - timedelta(days=days_ago), **fields)

    def test_categorise_files_a_spend_only_after_confirm_and_skips_unclear_merchants(self):
        for days in (40, 50):
            self.row("Synthetic Cafe", "120.00", days, category="food")
        self.row("Synthetic Mixed", "10.00", 40, category="food"); self.row("Synthetic Mixed", "10.00", 41, category="shopping")
        self.row("Synthetic Cafe", "99.00", 40, category="other", user=self.other)  # another owner's history never counts
        target = self.row("synthetic cafe ", "130.00")
        self.row("Synthetic Mixed", "12.00")
        proposal = task_bots.run(self.user, "categorise", self.today)
        self.assertEqual([item["action"]["expense_id"] for item in proposal["items"]], [target.pk])
        self.assertEqual(Expense.objects.get(pk=target.pk).category, "other")  # nothing changes before Confirm
        item = proposal["items"][0]
        response = self.post(operation="confirm", proposal_id=proposal["proposal_id"], item_ids=[item["id"]],
                             fingerprint=proposal["fingerprint"], confirmed=True)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("filed under Food", response.json()["message"])
        target.refresh_from_db()
        self.assertEqual((target.category, target.amount), ("food", Decimal("130.00")))
        self.assertIsNone(task_bots.run(self.user, "categorise", self.today))

    def test_categorise_confirm_refuses_a_spend_changed_after_the_review(self):
        for days in (40, 50):
            self.row("Synthetic Cafe", "120.00", days, category="food")
        target = self.row("Synthetic Cafe", "130.00")
        proposal = task_bots.run(self.user, "categorise", self.today)
        Expense.objects.filter(pk=target.pk).update(category="travel")
        response = self.post(operation="confirm", proposal_id=proposal["proposal_id"], item_ids=[proposal["items"][0]["id"]],
                             fingerprint=proposal["fingerprint"], confirmed=True)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Expense.objects.get(pk=target.pk).category, "travel")

    def test_budget_pace_warns_only_when_spending_runs_ahead(self):
        from datetime import date
        from apps.budgets.models import Budget
        day = date(2026, 11, 10)  # a third of the month has gone
        Budget.objects.create(user=self.user, month="Nov 2026", base_budget=Decimal("3000"), inflation_adjusted=Decimal("3000"), currency="INR")
        Expense.objects.create(user=self.user, amount=Decimal("900.00"), category="food", currency="INR", transaction_date=date(2026, 11, 5))
        self.assertIsNone(task_bots.run(self.user, "budget_pace", day))  # 30% used, on pace
        Expense.objects.create(user=self.user, amount=Decimal("600.00"), category="food", currency="INR", transaction_date=date(2026, 11, 6))
        item = task_bots.run(self.user, "budget_pace", day)["items"][0]
        self.assertEqual(item["title"], "Budget: ₹1,500.00 of ₹3,000.00 spent (50%)")
        self.assertIn("About ₹71.43 a day keeps you inside it.", item["detail"])  # 1,500 over the 21 days left

    def test_goals_subscriptions_duplicates_and_statements_are_read_only(self):
        from apps.budgets.models import SavingsGoal
        from apps.expenses.models import BankAccount, StatementUpload
        SavingsGoal.objects.create(user=self.user, name="Synthetic bike fund", target_amount=Decimal("1000"), saved_amount=Decimal("400"),
                                   target_date=self.today + timedelta(days=45), currency="INR")
        SavingsGoal.objects.create(user=self.user, name="Synthetic old goal", target_amount=Decimal("500"), saved_amount=Decimal("100"),
                                   target_date=self.today - timedelta(days=3), currency="INR")
        SavingsGoal.objects.create(user=self.user, name="Synthetic far goal", target_amount=Decimal("500"), target_date=self.today + timedelta(days=400))
        for days in (5, 35, 65):
            self.row("Synthetic Stream", "199.00", days, category="subscription")
        for days in (5, 35, 65):
            self.row("Synthetic Varying", "100.00" if days != 35 else "300.00", days)
        self.row("Synthetic Twice", "45.00", 2); self.row("Synthetic Twice", "45.00", 2)
        self.row("Synthetic Two refs", "45.00", 3, external_reference="A1"); self.row("Synthetic Two refs", "45.00", 3, external_reference="B2")
        account = BankAccount.objects.create(user=self.user, nickname="Synthetic Savings", account_number="TEST-BOT-1")
        upload = StatementUpload.objects.create(user=self.user, bank_account=account, file_name="synthetic.pdf")
        self.row("Synthetic Statement Row", "1.00", 50, bank_account=account, statement_upload=upload)
        before = financial_rows()
        titles = {bot: [item["title"] for item in (task_bots.run(self.user, bot, self.today) or {"items": []})["items"]]
                  for bot in ("goal_check", "subscriptions", "duplicates", "statements_due")}
        self.assertEqual(len(titles["goal_check"]), 2)
        self.assertIn("Synthetic old goal: target date", titles["goal_check"][0])
        self.assertTrue(titles["goal_check"][1].startswith("Synthetic bike fund: ₹"))
        self.assertEqual(titles["subscriptions"], ["Synthetic Stream: about ₹199.00 every month"])
        self.assertEqual(titles["duplicates"], [f"2 x ₹45.00 at Synthetic Twice on {self.today - timedelta(days=2):%d %b}"])
        self.assertEqual(titles["statements_due"], ["Upload a new statement for Synthetic Savings " + account.masked_account_number])
        self.assertEqual(financial_rows(), before)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(URL).json()["proposals"], [])


class HourlyBotScheduleTests(Fixtures):
    def spend(self, amount):
        return Expense.objects.create(user=self.user, amount=Decimal(amount), category="food", currency="INR",
                                      transaction_date=self.today - timedelta(days=1), merchant="Synthetic Shop")

    def test_local_daily_bots_refresh_each_run_and_a_dismissed_list_stays_dismissed(self):
        from apps.budgets.models import Budget
        Budget.objects.create(user=self.user, month=self.today.strftime("%b %Y"), base_budget=Decimal("100"),
                              inflation_adjusted=Decimal("100"), currency="INR")
        self.spend("95.00")
        first = task_bots.run_scheduled(self.today)
        pace = [p for p in task_bots.pending(self.user) if p["bot"] == "budget_pace"]
        self.assertEqual(len(pace), 1)
        task_bots.dismiss(self.user, pace[0]["proposal_id"])
        task_bots.run_scheduled(self.today)  # an hour later, nothing changed
        self.assertEqual([p for p in task_bots.pending(self.user) if p["bot"] == "budget_pace"], [])
        self.spend("10.00")  # a new spend the same day
        task_bots.run_scheduled(self.today)
        refreshed = [p for p in task_bots.pending(self.user) if p["bot"] == "budget_pace"]
        self.assertEqual(len(refreshed), 1)
        self.assertIn("₹105.00 of ₹100.00", refreshed[0]["items"][0]["title"])
        self.assertEqual(first["failed"], 0)

    def test_online_fund_bot_and_weekly_bots_keep_their_cadence(self):
        from apps.expenses.models import BankAccount
        account = BankAccount.objects.create(user=self.user, nickname="Synthetic Savings", account_number="TEST-HOURLY-1")
        from apps.expenses.models import StatementUpload
        upload = StatementUpload.objects.create(user=self.user, bank_account=account, file_name="synthetic.pdf")
        Expense.objects.create(user=self.user, bank_account=account, statement_upload=upload, amount=Decimal("1.00"), currency="INR",
                               transaction_date=self.today - timedelta(days=50))  # gives the weekly statements bot a review
        with patch.object(task_bots, "run", wraps=task_bots.run) as first:
            task_bots.run_scheduled(self.today)
        self.assertIn("fund_review", {call.args[1] for call in first.call_args_list if call.args[0] == self.user})
        with patch.object(task_bots, "run", wraps=task_bots.run) as again:
            task_bots.run_scheduled(self.today)
        bots = {call.args[1] for call in again.call_args_list if call.args[0] == self.user}
        self.assertIn("categorise", bots)
        reviewed_weekly = {p["bot"] for p in task_bots.pending(self.user) if task_bots.BOTS[p["bot"]][1] == 7}
        self.assertTrue(reviewed_weekly)
        self.assertFalse(reviewed_weekly & bots)  # a weekly bot that already produced this week's review waits a week
