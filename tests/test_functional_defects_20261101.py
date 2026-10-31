"""Defects found by post-master functional testing of 96d4637."""
from datetime import date

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.transaction_intelligence import resolve_bank_account
from apps.mobility.services.travel.intent import augment
from apps.mobility.services.travel_discovery import fact, value

QUOTAS = dict(ALFRED_API_ACCOUNT_LIMIT=10 ** 6, ALFRED_API_GLOBAL_LIMIT=10 ** 6,
              ALFRED_EXPENSIVE_ACCOUNT_LIMIT=10 ** 6, ALFRED_EXPENSIVE_GLOBAL_LIMIT=10 ** 6)


class TripWordingTests(SimpleTestCase):
    def destination(self, text):
        return value(augment({"origin": fact("Bengaluru", "configured_home_city", False, .85)}, text), "requested_destination")

    def test_ordinary_ways_of_naming_a_place(self):
        for text in ("Bengaluru to Coorg", "Bengaluru to Coorg from 2026-11-21 to 2026-11-24. Budget 25000.", "I want to go to Coorg",
                     "go to coorg for 3 days", "Coorg trip for 4 days", "Plan a trip from Bengaluru to Coorg", "Coorg",
                     "from Bengaluru to Coorg next month", "trip to Coorg in December", "trip to Coorg this weekend", "Trip to Coorg, Karnataka"):
            with self.subTest(text=text):
                self.assertEqual(self.destination(text), "Coorg")

    def test_a_named_start_replaces_the_profile_city(self):
        state = augment({"origin": fact("Mysuru", "configured_home_city", False, .85)}, "Bengaluru to Coorg")
        self.assertEqual(value(state, "origin"), "Bengaluru")

    def test_a_place_outside_the_catalogue_still_counts_when_clearly_named(self):
        self.assertEqual(self.destination("I want to go to Ziro"), "Ziro")

    def test_ordinary_sentences_name_no_place(self):
        for text in ("Bike trip for 4 days", "Weekend trip please", "2 October to 5 October", "Yes use that", "Mountains and photography", "go to next step",
                     "Budget 25000", "surprise me"):
            with self.subTest(text=text):
                self.assertIsNone(self.destination(text))

    def test_a_city_answering_the_start_question_is_not_a_destination(self):
        state = augment({"pending_question": fact("origin")}, "Coorg")
        self.assertIsNone(value(state, "requested_destination"))


@override_settings(**QUOTAS)
class RepeatedReferenceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("repeat_owner", password="Synthetic-Pass-1")
        self.account = BankAccount.objects.create(user=self.user, bank_name="Bank", account_number="R1001", current_balance="100")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def row(self, **changes):
        values = dict(amount="20000.25", category="rent", classification="expense", direction="debit", transaction_date="2026-11-01",
                      description="Rent", merchant="Rent", bank_account=self.account.pk, external_reference="REF-1")
        values.update(changes)
        return self.client.post("/api/expenses/", values, format="json")

    def test_the_same_reference_cannot_be_saved_twice(self):
        self.assertEqual(self.row().status_code, 201)
        repeated = self.row()
        self.assertEqual(repeated.status_code, 400)
        self.assertIn("external_reference", repeated.json())
        self.assertEqual(Expense.objects.filter(user=self.user).count(), 1)

    def test_different_payments_can_still_be_saved(self):
        self.assertEqual(self.row().status_code, 201)
        for changes in (dict(external_reference="REF-2"), dict(amount="100.00"), dict(transaction_date="2026-11-02"), dict(external_reference="")):
            with self.subTest(changes=changes):
                self.assertEqual(self.row(**changes).status_code, 201)
        self.assertEqual(self.row(external_reference="").status_code, 201)

    def test_another_owner_and_another_account_are_separate(self):
        self.assertEqual(self.row().status_code, 201)
        second = BankAccount.objects.create(user=self.user, bank_name="Other", account_number="R2002", current_balance="1")
        self.assertEqual(self.row(bank_account=second.pk).status_code, 201)
        other = get_user_model().objects.create_user("repeat_other", password="Synthetic-Pass-1")
        account = BankAccount.objects.create(user=other, bank_name="Bank", account_number="R1001", current_balance="1")
        client = APIClient()
        client.force_authenticate(other)
        values = dict(amount="20000.25", category="rent", classification="expense", direction="debit", transaction_date="2026-11-01",
                      description="Rent", merchant="Rent", bank_account=account.pk, external_reference="REF-1")
        self.assertEqual(client.post("/api/expenses/", values, format="json").status_code, 201)

    def test_editing_a_row_keeps_its_own_reference(self):
        created = self.row().json()
        edited = self.client.patch(f"/api/expenses/{created['id']}/", dict(description="Rent November"), format="json")
        self.assertEqual(edited.status_code, 200)


class RefusedPageTests(TestCase):
    def test_a_refused_page_explains_itself_and_keeps_the_exception_private(self):
        self.client.force_login(get_user_model().objects.create_user("refused_owner", password="Synthetic-Pass-1"))
        response = self.client.get("/reports/")
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "not available to your account", status_code=403)
        self.assertNotContains(response, "superusers", status_code=403)


class StatementAccountDetailsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("account_owner", password="Synthetic-Pass-1")
        self.account = BankAccount.objects.create(user=self.user, bank_name="My Salary Bank", account_holder="Owner", account_number="A1001",
                                                  account_type="savings", current_balance="500.00")

    def resolve(self, **changes):
        values = dict(user=self.user, bank_name="HDFC Bank", account_holder="MR SOMEONE", account_number="A1001", account_type="other", current_balance=None)
        values.update(changes)
        return resolve_bank_account(**values)

    def test_a_statement_keeps_what_the_owner_entered(self):
        self.resolve()
        self.account.refresh_from_db()
        self.assertEqual((self.account.bank_name, self.account.account_holder, self.account.account_type), ("My Salary Bank", "Owner", "savings"))

    def test_a_statement_fills_blank_details(self):
        blank = BankAccount.objects.create(user=self.user, account_number="A2002", current_balance="0")
        self.resolve(account_number="A2002")
        blank.refresh_from_db()
        self.assertEqual((blank.bank_name, blank.account_holder), ("HDFC Bank", "MR SOMEONE"))

    def test_a_new_account_takes_the_statement_details(self):
        made = self.resolve(account_number="A3003", account_type="credit")
        self.assertEqual((made.bank_name, made.account_type), ("HDFC Bank", "credit"))

    def test_the_closing_balance_still_updates(self):
        self.resolve(current_balance="750.50")
        self.account.refresh_from_db()
        self.assertEqual(str(self.account.current_balance), "750.50")
