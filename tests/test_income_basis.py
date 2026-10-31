"""FIN-01: the owner states the income period; an amount's size never decides it."""
from decimal import Decimal
from importlib import import_module

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.career.models import CareerProfile
from apps.career.services.income_intelligence import build_employment_income_signals
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.users.forms import AlfredSignUpForm


class IncomeBasisTests(TestCase):
    def user(self, name, amount, basis):
        return get_user_model().objects.create_user(name, password="Synthetic-Pass-1", monthly_income=amount, monthly_income_basis=basis)

    def baseline(self, user):
        return resolve_canonical_financial_baseline(get_user_model().objects.get(pk=user.pk))

    def test_large_monthly_income_is_not_divided(self):
        for amount in (300000, 720000, 1800000):
            with self.subTest(amount=amount):
                baseline = self.baseline(self.user(f"monthly_{amount}", amount, "monthly"))
                self.assertEqual(baseline["monthly_income"], float(amount))
                self.assertEqual(baseline["annual_income"], float(amount * 12))
                self.assertEqual(baseline["income_source"], "reported_monthly_income")

    def test_small_annual_income_is_divided_only_because_it_is_annual(self):
        baseline = self.baseline(self.user("annual_small", 240000, "annual"))
        self.assertEqual(baseline["monthly_income"], 20000.0)
        self.assertEqual(baseline["annual_income"], 240000.0)
        self.assertEqual(baseline["income_source"], "reported_annual_ctc")

    def test_annual_income_keeps_its_exact_entered_annual_amount(self):
        user = self.user("annual_exact", Decimal("1000000.00"), "annual")
        self.assertEqual(user.confirmed_monthly_income, Decimal("83333.33"))
        self.assertEqual(user.confirmed_annual_income, Decimal("1000000.00"))

    def test_unconfirmed_income_is_unverified_and_never_guessed(self):
        for amount in (80000, 300000):
            with self.subTest(amount=amount):
                user = self.user(f"unconfirmed_{amount}", amount, "unconfirmed")
                baseline = self.baseline(user)
                self.assertEqual(baseline["monthly_income"], 0.0)
                self.assertEqual(baseline["income_source"], "reported_income_unconfirmed")
                self.assertEqual(baseline["metric_states"]["monthly_income"]["status"], "unavailable")
                self.assertTrue(baseline["income_basis_needs_confirmation"])
                self.assertIn("confirm", baseline["metric_states"]["monthly_income"]["note"])
                user.refresh_from_db()
                self.assertEqual(user.monthly_income, Decimal(amount))

    def test_unconfirmed_income_cannot_return_through_the_career_profile(self):
        user = self.user("unconfirmed_profile", 300000, "unconfirmed")
        CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=300000)
        signals = build_employment_income_signals(user=user)
        self.assertEqual(signals["monthly_cash_income"], 0.0)
        self.assertEqual(signals["reported_income"]["value"], 300000.0)
        self.assertEqual(signals["reported_income"]["mode"], "unconfirmed")
        self.assertEqual(self.baseline(user)["monthly_income"], 0.0)

    def test_chosen_period_also_covers_a_career_profile_income(self):
        user = self.user("salary_only_annual", 0, "annual")
        CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=1200000)
        baseline = self.baseline(user)
        self.assertEqual(baseline["monthly_income"], 100000.0)
        self.assertEqual(baseline["annual_income"], 1200000.0)
        self.assertEqual(baseline["income_source"], "reported_annual_ctc")

        user.monthly_income_basis = "monthly"
        user.save(update_fields=["monthly_income_basis"])
        self.assertEqual(self.baseline(user)["monthly_income"], 1200000.0)

    def test_career_profile_seeded_from_annual_income_keeps_its_period(self):
        from apps.career.views import _get_profile
        user = self.user("annual_seed", 1200000, "annual")
        self.assertEqual(_get_profile(user).last_salary, Decimal("1200000.00"))
        get_user_model().objects.filter(pk=user.pk).update(monthly_income=0)
        self.assertEqual(self.baseline(user)["monthly_income"], 100000.0)

    def test_family_summary_counts_members_with_unverified_income(self):
        from apps.family.services import accept_family_link_code, create_family_link_invite
        from apps.family.views import _family_financial_summary
        owner = self.user("family_viewer", 90000, "monthly")
        member = self.user("family_unverified", 300000, "unconfirmed")
        link, code = create_family_link_invite(member)
        accept_family_link_code(owner, code)
        link.refresh_from_db()
        type(link).objects.filter(pk=link.pk).update(share_financial_summary=True)
        summary = _family_financial_summary(owner, own_baseline=self.baseline(owner))["family_financial_baseline"]
        self.assertEqual(summary["monthly_income"], 90000.0)
        self.assertEqual(summary["income_unverified_member_count"], 1)

    def test_family_summary_ignores_income_a_member_did_not_agree_to_share(self):
        from apps.family.services import accept_family_link_code, create_family_link_invite
        from apps.family.views import _family_financial_summary
        owner = self.user("family_no_consent_viewer", 90000, "monthly")
        for name, basis in (("family_private_confirmed", "monthly"), ("family_private_unverified", "unconfirmed")):
            link, code = create_family_link_invite(self.user(name, 300000, basis))
            accept_family_link_code(owner, code)
            type(link).objects.filter(pk=link.pk).update(share_financial_summary=False)
        summary = _family_financial_summary(owner, own_baseline=self.baseline(owner))["family_financial_baseline"]
        self.assertEqual(summary["monthly_income"], 90000.0)
        self.assertEqual(summary["income_unverified_member_count"], 0)

    def test_projection_does_not_fall_back_to_unconfirmed_income(self):
        from apps.career.services.projection_engine import build_projection_inputs
        user = self.user("unconfirmed_projection", 300000, "unconfirmed")
        profile = CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=300000)
        self.assertEqual(build_projection_inputs(user=user, profile=profile)["current_income"], 0.0)

    def test_tax_overview_flags_unconfirmed_income_instead_of_a_real_zero(self):
        user = self.user("unconfirmed_tax", 300000, "unconfirmed")
        client = APIClient()
        client.force_login(user)
        payload = client.get("/api/integrations/tax/overview/").json()
        self.assertEqual(float(payload["annual_income"]), 0.0)
        self.assertTrue(payload["financial_baseline"]["income_basis_needs_confirmation"])

    def test_career_salary_alone_on_an_unconfirmed_account_is_flagged(self):
        user = self.user("unconfirmed_salary_only", 0, "unconfirmed")
        self.assertFalse(user.income_basis_needs_confirmation)
        CareerProfile.objects.create(user=user, role="Analyst", experience_years=1, skills="", last_salary=300000)
        self.assertTrue(user.income_basis_needs_confirmation)
        self.assertEqual(self.baseline(user)["monthly_income"], 0.0)

    def test_confirming_changes_the_result_but_not_the_stored_amount(self):
        user = self.user("confirming", 300000, "unconfirmed")
        client = APIClient()
        client.force_login(user)
        self.assertEqual(self.baseline(user)["monthly_income"], 0.0)

        response = client.patch("/api/users/profile/", {"monthly_income_basis": "annual"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.baseline(user)["monthly_income"], 25000.0)

        response = client.patch("/api/users/profile/", {"monthly_income_basis": "monthly"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.baseline(user)["monthly_income"], 300000.0)
        user.refresh_from_db()
        self.assertEqual(user.monthly_income, Decimal("300000.00"))

    def test_profile_api_rejects_returning_to_unconfirmed_and_unknown_values(self):
        user = self.user("api_values", 90000, "monthly")
        client = APIClient()
        client.force_login(user)
        self.assertEqual(client.get("/api/users/profile/").json()["monthly_income_basis"], "monthly")
        for value in ("unconfirmed", "weekly"):
            self.assertEqual(client.patch("/api/users/profile/", {"monthly_income_basis": value}, format="json").status_code, 400)
        user.refresh_from_db()
        self.assertEqual(user.monthly_income_basis, "monthly")

    def test_changing_the_amount_keeps_the_stated_period(self):
        user = self.user("annual_edit", 600000, "annual")
        client = APIClient()
        client.force_login(user)
        self.assertEqual(client.patch("/api/users/profile/", {"monthly_income": 720000}, format="json").status_code, 200)
        self.assertEqual(self.baseline(user)["monthly_income"], 60000.0)

    def test_notice_shows_only_while_confirmation_is_needed(self):
        user = self.user("notice", 300000, "unconfirmed")
        self.client.force_login(user)
        self.assertContains(self.client.get("/settings/"), 'id="incomeBasisNotice"')
        user.monthly_income_basis = "monthly"
        user.save(update_fields=["monthly_income_basis"])
        self.assertNotContains(self.client.get("/settings/"), 'id="incomeBasisNotice"')

    def test_signup_records_the_chosen_period_and_defaults_to_monthly(self):
        base = {"password1": "Synthetic-Pass-1!x", "password2": "Synthetic-Pass-1!x", "monthly_income": "600000"}
        form = AlfredSignUpForm({**base, "username": "signup_annual", "monthly_income_basis": "annual"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().monthly_income_basis, "annual")
        form = AlfredSignUpForm({**base, "username": "signup_default"})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().monthly_income_basis, "monthly")
        self.assertFalse(AlfredSignUpForm({**base, "username": "signup_bad", "monthly_income_basis": "unconfirmed"}).is_valid())

    def test_owner_isolation_and_csrf_still_apply(self):
        owner = self.user("basis_owner", 300000, "unconfirmed")
        other = self.user("basis_other", 90000, "monthly")
        client = APIClient()
        client.force_login(other)
        client.patch("/api/users/profile/", {"monthly_income_basis": "annual"}, format="json")
        owner.refresh_from_db()
        self.assertEqual(owner.monthly_income_basis, "unconfirmed")
        enforcing = APIClient(enforce_csrf_checks=True)
        enforcing.force_login(owner)
        self.assertEqual(enforcing.patch("/api/users/profile/", {"monthly_income_basis": "monthly"}, format="json").status_code, 403)
        owner.refresh_from_db()
        self.assertEqual(owner.monthly_income_basis, "unconfirmed")


class IncomeBasisMigrationTests(TransactionTestCase):
    before = [("users", "0003_user_money_decimal")]
    after = [("users", "0004_user_monthly_income_basis")]

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_rows_become_unconfirmed_with_amounts_unchanged_and_it_reverses(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        User = executor.loader.project_state(self.before).apps.get_model("users", "User")
        for name, amount in (("old_small", "80000.50"), ("old_large", "300000.00"), ("old_zero", "0.00")):
            User.objects.create(username=name, monthly_income=Decimal(amount), variable_income=Decimal("12.34"))
        stored = list(User.objects.order_by("pk").values_list("username", "monthly_income", "variable_income"))

        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        User = executor.loader.project_state(self.after).apps.get_model("users", "User")
        self.assertEqual(list(User.objects.order_by("pk").values_list("username", "monthly_income", "variable_income")), stored)
        self.assertEqual(set(User.objects.values_list("monthly_income_basis", flat=True)), {"unconfirmed"})
        self.assertEqual(User._meta.get_field("monthly_income_basis").default, "monthly")

        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        User = executor.loader.project_state(self.before).apps.get_model("users", "User")
        self.assertEqual(list(User.objects.order_by("pk").values_list("username", "monthly_income", "variable_income")), stored)
        User.objects.all().delete()
