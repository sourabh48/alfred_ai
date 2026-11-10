"""AI-17: proposals change nothing; only an owner-confirmed, allow-listed action is saved."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
import json
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import OperationalError, connections
from django.test import Client, TestCase, TransactionTestCase
from django.utils import timezone

from apps.budgets.models import SavingsGoal
from apps.ml_engine.services.assistant_actions import ActionConflict, ActionError, cancel, confirm, prepare, propose
from apps.reports.models import OperationalLog
from apps.reports.services import operational_logging_service

TODAY = date(2026, 11, 6)


class AssistantActionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-action-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-action-other")
        self.client.force_login(self.owner)

    def proposal(self, text="add a savings goal Synthetic bike of 1000.25"):
        response = self.client.post("/api/ai/actions/propose/", {"text": text}, content_type="application/json")
        self.assertIn("no-store", response["Cache-Control"])
        return response.json()["proposal"]

    def confirm(self, proposal):
        return self.client.post("/api/ai/actions/confirm/", {**proposal, "confirmed": True}, content_type="application/json")

    def test_confirmation_cannot_replace_the_reviewed_amount(self):
        proposal = self.proposal()
        proposal["fields"]["target_amount"] = "9999.99"
        self.assertEqual(self.confirm(proposal).status_code, 400)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_replayed_confirmation_creates_only_one_goal(self):
        proposal = self.proposal()
        self.assertEqual(self.confirm(proposal).status_code, 201)
        self.assertIn(self.confirm(proposal).status_code, (200, 409))
        self.assertEqual(SavingsGoal.objects.count(), 1)

    def test_changed_goal_requires_a_new_review(self):
        goal = SavingsGoal.objects.create(user=self.owner, name="Bike", target_amount="1000.00")
        proposal = self.proposal("update Bike saved to 250.10")
        goal.saved_amount = Decimal("600.25")
        goal.save()
        self.assertEqual(self.confirm(proposal).status_code, 409)
        goal.refresh_from_db()
        self.assertEqual(goal.saved_amount, Decimal("600.25"))

    def test_expiry_uses_server_time_even_if_client_extends_it(self):
        proposal = self.proposal()
        proposal["expires_at"] = "2099-01-01T00:00:00+00:00"
        with patch("apps.ml_engine.services.assistant_actions.timezone.now", return_value=timezone.now()+timedelta(minutes=11)):
            self.assertEqual(self.confirm(proposal).status_code, 409)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_revision_preserves_submillisecond_updates(self):
        goal = SavingsGoal.objects.create(user=self.owner, name="Bike", target_amount="1000.00")
        proposal = self.proposal("update Bike saved to 250.10")
        SavingsGoal.objects.filter(pk=goal.pk).update(updated_at=goal.updated_at+timedelta(microseconds=1))
        self.assertEqual(self.confirm(proposal).status_code, 409)

    def test_cross_owner_and_unknown_ids_cannot_confirm_or_cancel(self):
        proposal = self.proposal()
        self.client.force_login(self.other)
        self.assertEqual(self.confirm(proposal).status_code, 400)
        self.assertEqual(self.client.post("/api/ai/actions/cancel/", {"proposal_id": proposal["proposal_id"]}, content_type="application/json").status_code, 400)
        self.client.force_login(self.owner)
        for identity in (None, "", "0"*32, True, [], "../outside"):
            with self.subTest(identity=identity):
                self.assertEqual(self.confirm({**proposal, "proposal_id": identity}).status_code, 400)
        self.assertEqual(self.confirm(proposal).status_code, 201)

    def test_cancellation_is_server_side_and_does_not_claim_a_saved_action(self):
        proposal = self.proposal()
        for _ in range(2):
            response = self.client.post("/api/ai/actions/cancel/", {"proposal_id": proposal["proposal_id"]}, content_type="application/json")
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.confirm(proposal).status_code, 409)
        self.assertFalse(SavingsGoal.objects.exists())
        saved = self.proposal()
        self.assertEqual(self.confirm(saved).status_code, 201)
        self.assertEqual(self.client.post("/api/ai/actions/cancel/", {"proposal_id": saved["proposal_id"]}, content_type="application/json").status_code, 409)
        self.assertEqual(SavingsGoal.objects.count(), 1)

    def test_revision_covers_all_reviewed_terms_even_without_updated_timestamp(self):
        goal = SavingsGoal.objects.create(user=self.owner, name="Bike", target_amount="1000.00")
        for field, value in (("name", "Changed"), ("target_amount", "2000.00"), ("saved_amount", "40.01"),
                             ("currency", "USD"), ("target_date", date(2028, 1, 1))):
            with self.subTest(field=field):
                goal.refresh_from_db()
                proposal = self.proposal(f"update {goal.name} saved to 250.10")
                SavingsGoal.objects.filter(pk=goal.pk).update(**{field: value})
                self.assertEqual(self.confirm(proposal).status_code, 409)

    def test_deleted_goal_is_not_recreated_and_applied_replay_does_not_overwrite_new_progress(self):
        goal = SavingsGoal.objects.create(user=self.owner, name="Bike", target_amount="1000.00")
        proposal = self.proposal("update Bike saved to 250.10")
        self.assertEqual(self.confirm(proposal).status_code, 201)
        SavingsGoal.objects.filter(pk=goal.pk).update(saved_amount="600.00")
        replay = self.confirm(proposal)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["already_applied"])
        goal.refresh_from_db()
        self.assertEqual(goal.saved_amount, Decimal("600.00"))
        pending = self.proposal("update Bike saved to 20")
        goal.delete()
        self.assertEqual(self.confirm(pending).status_code, 409)
        self.assertEqual(self.confirm(proposal).status_code, 200)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_receipt_failure_rolls_back_claim_and_goal_then_retry_succeeds(self):
        proposal = self.proposal()
        with patch.object(OperationalLog, "save", side_effect=OperationalError("SYNTHETIC-PRIVATE-FAILURE")):
            response = self.confirm(proposal)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("SYNTHETIC-PRIVATE", response.content.decode())
        self.assertFalse(SavingsGoal.objects.exists())
        record = OperationalLog.objects.get(scope="assistant_action")
        self.assertEqual((record.event_type, record.payload["state"]), ("assistant_action_pending", "pending"))
        self.assertEqual(self.confirm(proposal).status_code, 201)

    def test_audit_retains_only_keyed_bindings_and_redacted_receipts(self):
        proposal = self.proposal("add a savings goal Synthetic-private-marker of 2345.67")
        self.assertEqual(self.confirm(proposal).status_code, 201)
        record = OperationalLog.objects.get(scope="assistant_action")
        raw = json.dumps(record.payload)
        self.assertNotIn("Synthetic-private-marker", raw)
        self.assertNotIn("2345.67", raw)
        self.assertNotIn("fields", record.payload)
        public = operational_logging_service.serialize(record)["payload"]
        self.assertEqual(public["state"], "confirmed")
        self.assertFalse({"binding", "revision", "proposal_id"} & set(public))
        OperationalLog.objects.filter(pk=record.pk).delete()
        self.assertEqual(self.confirm(proposal).status_code, 400)
        self.assertEqual(SavingsGoal.objects.count(), 1)

    def test_lost_response_retries_across_sessions_with_one_receipt(self):
        proposal = self.proposal()
        original = self.confirm(proposal)
        self.client = Client()
        self.client.force_login(self.owner)
        replay = self.confirm(proposal)
        self.assertEqual((original.status_code, replay.status_code), (201, 200))
        self.assertEqual(original.json()["goal_id"], replay.json()["goal_id"])
        self.assertEqual(SavingsGoal.objects.count(), 1)
        self.assertEqual(OperationalLog.objects.filter(event_type="assistant_action_confirmed").count(), 1)

    def test_confirmation_and_cancel_require_session_and_csrf(self):
        proposal = self.proposal()
        client = Client(enforce_csrf_checks=True)
        for authenticated in (False, True):
            if authenticated:
                client.force_login(self.owner)
            for endpoint, payload in (("confirm", {**proposal, "confirmed": True}), ("cancel", {"proposal_id": proposal["proposal_id"]})):
                self.assertEqual(client.post(f"/api/ai/actions/{endpoint}/", payload, content_type="application/json").status_code, 403)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_malformed_fields_and_invalid_proposals_do_not_post_or_allocate_receipts(self):
        for text in ("add a savings goal X of 0", "add a savings goal X of 99999999999999999999999999", ["not text"], "a"*1201):
            response = self.client.post("/api/ai/actions/propose/", {"text": text}, content_type="application/json")
            self.assertIsNone(response.json()["proposal"])
        self.assertFalse(OperationalLog.objects.exists())
        proposal = self.proposal()
        for fields in ([], None, {**proposal["fields"], "currency": "USD"}, {**proposal["fields"], "target_amount": True}):
            self.assertEqual(self.confirm({**proposal, "fields": fields}).status_code, 400)
        for payload in ([], {**proposal, "confirmed": 1}, {**proposal, "confirmed": True, "unexpected": "x"}):
            self.assertEqual(self.client.post("/api/ai/actions/confirm/", payload, content_type="application/json").status_code, 400)
        self.assertFalse(SavingsGoal.objects.exists())

    def test_pending_reviews_are_bounded_and_old_history_does_not_block_new_reviews(self):
        for _ in range(20):
            self.assertIsNotNone(self.proposal())
        response = self.client.post("/api/ai/actions/propose/", {"text": "add a savings goal Bike of 100"}, content_type="application/json")
        self.assertIsNone(response.json()["proposal"])
        OperationalLog.objects.all().update(created_at=timezone.now()-timedelta(minutes=11))
        self.assertIsNotNone(self.proposal())

    def test_create_requests_parse_indian_units_and_dates(self):
        cases = {
            "Add a savings goal Emergency fund of 1.5 lakh by March 2027": ("Emergency fund", "150000.00", "2027-03-31"),
            "create savings goal called 'Goa trip' for ₹50,000.50": ("Goa trip", "50000.50", None),
            "please set up a new savings goal named Bike for 75k before 2027-01-15.": ("Bike", "75000.00", "2027-01-15"),
            "add a savings goal House for 1 crore by 31 December 2030": ("House", "10000000.00", "2030-12-31"),
            # Exactly what Whisper wrote for a spoken request (AI-18).
            "Add the Savings Goal Emergency Fund of 1-Lac by March 2027.": ("Emergency Fund", "100000.00", "2027-03-31"),
            "add a savings goal Car of 2 lakh rupees": ("Car", "200000.00", None),
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


class ConcurrentAssistantActionTests(TransactionTestCase):
    def test_simultaneous_confirmation_and_retry_never_apply_twice(self):
        owner = get_user_model().objects.create_user(username="synthetic-action-race-owner")
        proposal = prepare(owner, "add a savings goal Bike of 100.25")
        barrier = Barrier(2, timeout=10)

        def execute():
            try:
                barrier.wait()
                return confirm(owner, proposal["proposal_id"], proposal["action"], proposal["fields"])
            except OperationalError:
                return "retry"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: execute(), range(2)))
        self.assertTrue(any(isinstance(result, dict) for result in results), results)
        self.assertTrue(all(isinstance(result, dict) or result == "retry" for result in results))
        self.assertTrue(confirm(owner, proposal["proposal_id"], proposal["action"], proposal["fields"])["already_applied"])
        self.assertEqual(SavingsGoal.objects.count(), 1)
        self.assertEqual(OperationalLog.objects.get().payload["state"], "confirmed")

    def test_confirm_racing_cancel_has_one_consistent_outcome(self):
        owner = get_user_model().objects.create_user(username="synthetic-action-cancel-race")
        proposal = prepare(owner, "add a savings goal Bike of 100.25")
        barrier = Barrier(2, timeout=10)

        def execute(is_cancel):
            try:
                barrier.wait()
                return cancel(owner, proposal["proposal_id"]) if is_cancel else confirm(owner, proposal["proposal_id"], proposal["action"], proposal["fields"])
            except (OperationalError, ActionConflict):
                return "retry"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, (False, True)))
        self.assertTrue(any(isinstance(result, dict) for result in results), results)
        state = OperationalLog.objects.get().payload["state"]
        self.assertIn(state, ("confirmed", "cancelled"))
        self.assertEqual(SavingsGoal.objects.count(), int(state == "confirmed"))
        if state == "confirmed":
            self.assertTrue(confirm(owner, proposal["proposal_id"], proposal["action"], proposal["fields"])["already_applied"])
        else:
            with self.assertRaises(ActionConflict):
                confirm(owner, proposal["proposal_id"], proposal["action"], proposal["fields"])
