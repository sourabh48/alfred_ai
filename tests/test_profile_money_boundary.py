import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from apps.career.serializers import CareerProjectionScenarioSerializer
from apps.expenses.money import LIMIT
from apps.users.forms import AlfredSignUpForm
from apps.users.money import profile_money
from apps.users.serializers import UserSerializer


class ProfileMoneyBoundaryTests(TestCase):
    invalid = ("NaN", "Infinity", "-Infinity", "1e9999", "-1", "0.001",
               "1000000000000.00", "INR 100", "not-a-number", True, None)

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-money", monthly_income=123.45)
        self.client.force_login(self.user)

    def test_raw_serializer_and_scenario_inputs_are_rejected_before_float_conversion(self):
        for field in ("monthly_income", "variable_income", "rent_or_emi"):
            for value in self.invalid:
                with self.subTest(field=field, kind=type(value).__name__):
                    self.assertFalse(UserSerializer(self.user, data={field: value}, partial=True).is_valid())
                    self.assertFalse(CareerProjectionScenarioSerializer(data={field: value}).is_valid())

    def test_api_rejection_does_not_mutate_other_fields_or_profile(self):
        for method in (self.client.patch, self.client.put):
            for value in self.invalid:
                with self.subTest(method=method.__name__, kind=type(value).__name__):
                    response = method("/api/users/profile/", json.dumps({"monthly_income": value, "city": "changed"}),
                                      content_type="application/json")
                    self.assertEqual(response.status_code, 400)
                    self.user.refresh_from_db()
                    self.assertEqual(self.user.monthly_income, Decimal('123.45'))
                    self.assertEqual(self.user.city, "")

    def test_model_save_queryset_update_and_bulk_insert_reject_invalid_money(self):
        for value in self.invalid:
            with self.subTest(kind=type(value).__name__):
                self.user.monthly_income = value
                with self.assertRaises(ValidationError), transaction.atomic():
                    self.user.save(update_fields=["monthly_income"])
                with self.assertRaises(ValidationError), transaction.atomic():
                    get_user_model().objects.filter(pk=self.user.pk).update(monthly_income=value)
                with self.assertRaises(ValidationError), transaction.atomic():
                    get_user_model().objects.bulk_create([get_user_model()(username="invalid-bulk", monthly_income=value)])
                self.user.refresh_from_db()
                self.assertEqual(self.user.monthly_income, Decimal('123.45'))
        self.assertFalse(get_user_model().objects.filter(username="invalid-bulk").exists())

    def test_signup_forms_reject_invalid_currency_and_keep_empty_optional_inputs(self):
        for value in self.invalid[:-2]:
            with self.subTest(kind=type(value).__name__):
                field = AlfredSignUpForm().fields["monthly_income"]
                with self.assertRaises(ValidationError):
                    field.clean(value)
        self.assertIsNone(AlfredSignUpForm().fields["monthly_income"].clean(""))

    def test_valid_cent_boundaries_remain_numeric_and_round_trip(self):
        for value in (0, "0.01", "123.45", "123.4500", "1e3", LIMIT):
            with self.subTest(value=value):
                result = profile_money(value)
                self.user.monthly_income = result
                self.user.save(update_fields=["monthly_income"])
                self.user.refresh_from_db()
                self.assertEqual(Decimal(str(self.user.monthly_income)), Decimal(str(value)))
                self.assertIsInstance(UserSerializer(self.user).data["monthly_income"], float)

    def test_model_form_and_clean_share_decimal_currency_boundary(self):
        field = get_user_model()._meta.get_field("monthly_income")
        self.assertEqual(field.formfield().clean('0.01'), Decimal('0.01'))
        with self.assertRaises(ValidationError):
            field.formfield().clean("0.001")
        self.user.monthly_income = float("inf")
        with self.assertRaises(ValidationError):
            self.user.full_clean()
