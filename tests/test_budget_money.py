"""Synthetic Budget register boundaries, ownership and canonical cents."""
from datetime import date
from decimal import Decimal
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.forms import modelform_factory
from django.db import transaction
from django.test import SimpleTestCase, TestCase

from apps.budgets.models import Budget, BudgetMoneySnapshot
from apps.budgets.money import budget_money, FIELDS
from apps.expenses.models import Expense
from apps.expenses.money import LIMIT
from apps.users.services import clear_user_fed_data


class BudgetMoneyBoundaryTests(SimpleTestCase):
    def test_half_up_zero_and_supported_boundary(self):
        for value, expected in ((0, "0.00"), ("0.005", "0.01"), ("2.675", "2.68"), (LIMIT, str(LIMIT))):
            with self.subTest(value=value):
                self.assertEqual(budget_money(value), Decimal(expected))

    def test_nonfinite_negative_invalid_and_overflow_are_rejected(self):
        for value in (None, True, False, "NaN", "Infinity", "-Infinity", "-0.001", "1e9999",
                      "999999999999.995", "not money", "1" * 129):
            with self.subTest(value=value), self.assertRaises(ValueError):
                budget_money(value)

    def test_model_form_rejects_invalid_precision_and_negative_values(self):
        Form = modelform_factory(Budget, fields=FIELDS)
        for value in ("NaN", "Infinity", "-1", "0.001", "1000000000000"):
            with self.subTest(value=value):
                self.assertFalse(Form(data=dict.fromkeys(FIELDS, value)).is_valid())
        self.assertTrue(Form(data=dict.fromkeys(FIELDS, "0.01")).is_valid())


class BudgetMoneyRuntimeTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="budget-money-owner")
        self.other = get_user_model().objects.create_user(username="budget-money-other")
        self.client.force_login(self.owner)

    def test_model_and_numeric_api_rounding_preserve_partial_updates(self):
        response = self.client.post('/api/budgets/', json.dumps({
            "month": "2026-10", "base_budget": "2.675", "inflation_adjusted": "100000000000.01",
        }), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        row = Budget.objects.get(pk=response.json()['id'])
        self.assertEqual((row.base_budget, row.inflation_adjusted, row.spent),
                         (Decimal('2.68'), Decimal('100000000000.01'), Decimal('0.00')))
        self.assertIsInstance(response.json()['base_budget'], float)
        self.assertEqual(set(response.json()), {'id', 'user', 'month', *FIELDS})
        result = self.client.patch(f'/api/budgets/{row.pk}/', json.dumps({'spent': '0.005'}), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        row.refresh_from_db()
        self.assertEqual((row.base_budget, row.spent), (Decimal('2.68'), Decimal('0.01')))
        self.assertFalse(BudgetMoneySnapshot.objects.exists())

    def test_invalid_api_amounts_reject_the_whole_update(self):
        row = Budget.objects.create(user=self.owner, month='Oct 2026', base_budget=10, inflation_adjusted=10)
        for field in FIELDS:
            for value in ('NaN', 'Infinity', '-Infinity', None, True, '-0.001', '1e9999', 'bad', '999999999999.995'):
                with self.subTest(field=field, value=value):
                    result = self.client.patch(f'/api/budgets/{row.pk}/', json.dumps({
                        field: value, 'month': 'Nov 2026',
                    }), content_type='application/json')
                    self.assertEqual(result.status_code, 400)
                    row.refresh_from_db()
                    self.assertEqual((row.month, row.base_budget, row.inflation_adjusted, row.spent),
                                     ('Oct 2026', 10, 10, 0))

    def test_orm_save_update_and_bulk_reject_invalid_money_without_writes(self):
        row = Budget.objects.create(user=self.owner, month='Oct 2026', base_budget=10, inflation_adjusted=10)
        for value in ('NaN', 'Infinity', '-Infinity', None, True, '-0.001', '1000000000000'):
            with self.subTest(value=value):
                row.spent = value
                with self.assertRaises(ValidationError), transaction.atomic():
                    row.save(update_fields=['spent'])
                with self.assertRaises(ValidationError), transaction.atomic():
                    Budget.objects.filter(pk=row.pk).update(spent=value)
                with self.assertRaises(ValidationError), transaction.atomic():
                    Budget.objects.bulk_update([row], ['spent'])
                with self.assertRaises(ValidationError), transaction.atomic():
                    Budget.objects.bulk_create([Budget(user=self.owner, month='invalid', base_budget=value, inflation_adjusted=10)])
                row.refresh_from_db()
                self.assertEqual(row.spent, Decimal('0.00'))
        self.assertEqual(Budget.objects.count(), 1)

    def test_owner_only_access_and_session_required(self):
        foreign = Budget.objects.create(user=self.other, month='Oct 2026', base_budget=50, inflation_adjusted=50)
        self.assertEqual(self.client.get(f'/api/budgets/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/budgets/{foreign.pk}/', {'spent': 1}, content_type='application/json').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/budgets/{foreign.pk}/').status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get('/api/budgets/').status_code, 403)
        foreign.refresh_from_db()
        self.assertEqual(foreign.spent, 0)

    def test_reset_removes_owned_orphan_snapshots_only(self):
        for owner in (self.owner, self.other):
            row = Budget.objects.create(user=owner, month='Oct 2026', base_budget=1, inflation_adjusted=1)
            BudgetMoneySnapshot.objects.create(user=owner, budget=row, original_budget_id=row.pk,
                source_values={'base_budget': '1.005'}, normalized_values={'base_budget': '1.01'})
            row.delete()
        clear_user_fed_data(self.owner)
        self.assertFalse(BudgetMoneySnapshot.objects.filter(user=self.owner).exists())
        self.assertEqual(BudgetMoneySnapshot.objects.get().user_id, self.other.pk)

    def test_dashboard_uses_exact_owned_spending_and_excludes_transfer_legs(self):
        today = date(2026, 10, 16)
        Budget.objects.create(user=self.owner, month='Oct 2026', base_budget='0.30', inflation_adjusted='0.30')
        for amount in ('0.10', '0.20'):
            Expense.objects.create(user=self.owner, amount=amount, category='food', transaction_date=today)
        Expense.objects.create(user=self.owner, amount=999, category='transfer', transaction_date=today)
        Expense.objects.create(user=self.other, amount=999, category='food', transaction_date=today)
        with patch('apps.budgets.views.timezone.localdate', return_value=today), \
             patch('apps.budgets.services.budget_intelligence.budget_intelligence_service.suggest_budget', return_value={}), \
             patch('apps.budgets.services.budget_intelligence.budget_intelligence_service.calculate_daily_affordability', return_value={}), \
             patch('apps.budgets.services.budget_intelligence.budget_intelligence_service.forecast_finances', return_value={}):
            result = self.client.get('/api/budgets/dashboard/')
        self.assertEqual(result.status_code, 200)
        self.assertEqual({key: result.json()['summary'][key] for key in ('total_budget', 'total_spent', 'total_remaining')},
                         {'total_budget': .30, 'total_spent': .30, 'total_remaining': 0})
        self.assertEqual(result.json()['plan']['inflation_adjusted'], .30)
        self.assertNotIn('currency', result.json()['plan'])
