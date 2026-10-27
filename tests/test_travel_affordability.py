"""Synthetic reconciliation and trust-boundary checks for the C1 service only."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.loans.models import Loan
from apps.mobility.services.travel.affordability import affordability_source, calculate_affordability


class TravelAffordabilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='affordability-owner', rent_or_emi=100)
        self.other = get_user_model().objects.create_user(username='affordability-other')
        self.account = BankAccount.objects.create(user=self.user, account_number='synthetic', current_balance='1000.00', last_synced_at=timezone.now())
        self.expense = Expense.objects.create(user=self.user, amount='50.00', category='groceries',
                                              transaction_date=timezone.localdate())
        self.loan = Loan.objects.create(user=self.user, principal='1000.00', emi='25.00', interest_rate=0,
                                        remaining_balance='800.00', start_date=timezone.localdate())

    def confirmation(self):
        source = affordability_source(self.user)
        values = dict(spendable_cash='1000.00', emergency_reserve='200.00',
                      essential_expenses=source['amounts']['essential_expenses'],
                      loan_obligations=source['amounts']['loan_obligations'],
                      committed_savings='100.00', trip_budget='400.00', contingency='25.00')
        return dict(source_revision=source['source_revision'], complete=True, disjoint_allocations=True,
                    **{k: dict(amount=v, currency='USD', verified=True) for k, v in values.items()})

    def test_reconciles_exact_protected_funds_without_debt_principal_or_income(self):
        result = calculate_affordability(self.user, self.confirmation())
        self.assertEqual(result['status'], 'WITHIN_CONFIRMED_FUNDS')
        self.assertFalse(result['certified'])
        self.assertEqual(result['currency'], 'USD')
        self.assertEqual(result['amounts']['essential_expenses'], '150.00')
        self.assertEqual(result['amounts']['loan_obligations'], '25.00')
        self.assertEqual(result['amounts']['protected_funds'], '475.00')
        self.assertEqual(result['amounts']['available_trip_funds'], '525.00')
        self.assertEqual(result['amounts']['headroom'], '100.00')
        self.assertEqual(result['amounts']['shortfall'], '0.00')

    def test_shortfall_includes_existing_protected_funding_deficit(self):
        confirmation = self.confirmation()
        confirmation['spendable_cash']['amount'] = '100.00'
        result = calculate_affordability(self.user, confirmation)
        self.assertEqual(result['status'], 'SHORTFALL')
        self.assertEqual(result['amounts']['available_trip_funds'], '0.00')
        self.assertEqual(result['amounts']['headroom'], '-800.00')
        self.assertEqual(result['amounts']['shortfall'], '800.00')

    def test_decimal_half_up_and_exact_zero_not_missing(self):
        confirmation = self.confirmation()
        confirmation['trip_budget']['amount'] = '525.005'
        confirmation['contingency']['amount'] = Decimal('0')
        result = calculate_affordability(self.user, confirmation)
        self.assertEqual(result['amounts']['total_trip_budget'], '525.01')
        self.assertEqual(result['amounts']['shortfall'], '0.01')
        confirmation['trip_budget']['amount'] = '525.00'
        self.assertEqual(calculate_affordability(self.user, confirmation)['amounts']['headroom'], '0.00')

    def test_currency_must_be_explicit_verified_and_matching(self):
        for currency in (None, '', 'usd', 'USD\r\nX', 'EUR'):
            with self.subTest(currency=currency):
                confirmation = self.confirmation()
                confirmation['trip_budget']['currency'] = currency
                result = calculate_affordability(self.user, confirmation)
                self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
                self.assertIsNone(result['amounts'])
        confirmation = self.confirmation()
        confirmation['spendable_cash']['verified'] = False
        self.assertIn('UNCONFIRMED_SPENDABLE_CASH', calculate_affordability(self.user, confirmation)['issues'])

    def test_missing_malformed_nonfinite_negative_and_float_amounts_rejected(self):
        for value in (None, True, False, 1.01, {}, [], 'NaN', 'Infinity', '-1', '-0.001', '1e9999999', 'x' * 100):
            with self.subTest(value=value):
                confirmation = self.confirmation()
                confirmation['emergency_reserve']['amount'] = value
                result = calculate_affordability(self.user, confirmation)
                self.assertEqual(result['status'], 'INSUFFICIENT_DATA')
                self.assertIsNone(result['amounts'])
        self.assertIn('MALFORMED_CONFIRMATION', calculate_affordability(self.user, None)['issues'])

    def test_allocation_completeness_explicit_and_no_double_count_overrides(self):
        for field in ('complete', 'disjoint_allocations'):
            confirmation = self.confirmation()
            del confirmation[field]
            self.assertIn('OWNER_COMPLETENESS_REQUIRED', calculate_affordability(self.user, confirmation)['issues'])
        for field in ('essential_expenses', 'loan_obligations'):
            confirmation = self.confirmation()
            confirmation[field]['amount'] = '0'
            self.assertIn('CANONICAL_MISMATCH_' + field.upper(), calculate_affordability(self.user, confirmation)['issues'])
        confirmation = self.confirmation()
        confirmation['spendable_cash']['amount'] = '1000.01'
        self.assertIn('CASH_EXCEEDS_CANONICAL_BALANCE', calculate_affordability(self.user, confirmation)['issues'])

    def test_no_writes_or_network_and_identical_repeat_result(self):
        confirmation = self.confirmation()
        def readonly(execute, sql, params, many, context):
            self.assertNotRegex(sql.lstrip().upper(), r'^(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP)\b')
            return execute(sql, params, many, context)
        with connection.execute_wrapper(readonly), patch('requests.sessions.Session.request', side_effect=AssertionError('external request')):
            first = calculate_affordability(self.user, confirmation)
            self.assertEqual(first, calculate_affordability(self.user, confirmation))
        self.assertEqual(first['status'], 'WITHIN_CONFIRMED_FUNDS')

    def test_owner_isolation_authentication_and_opaque_owner_bound_revisions(self):
        with self.assertRaises(PermissionDenied):
            affordability_source(AnonymousUser())
        confirmation = self.confirmation()
        foreign = calculate_affordability(self.other, confirmation)
        self.assertIn('STALE_OR_FOREIGN_SOURCE', foreign['issues'])
        self.assertNotIn('1000.00', str(foreign['source']))
        revision = affordability_source(self.user)['source_revision']
        self.assertEqual(len(revision), 64)
        BankAccount.objects.create(user=self.other, account_number='other', current_balance='900000.00')
        self.assertEqual(affordability_source(self.user)['source_revision'], revision)

    def test_stale_content_in_place_updates_detected_without_timestamp_changes(self):
        confirmation = self.confirmation()
        BankAccount.objects.filter(pk=self.account.pk).update(current_balance='999.00')
        self.assertIn('STALE_OR_FOREIGN_SOURCE', calculate_affordability(self.user, confirmation)['issues'])
        confirmation = self.confirmation()
        Expense.objects.filter(pk=self.expense.pk).update(amount='51.00')
        self.assertIn('STALE_OR_FOREIGN_SOURCE', calculate_affordability(self.user, confirmation)['issues'])
        confirmation = self.confirmation()
        get_user_model().objects.filter(pk=self.user.pk).update(rent_or_emi=101)
        self.assertIn('STALE_OR_FOREIGN_SOURCE', calculate_affordability(self.user, confirmation)['issues'])

    def test_missing_balances_or_history_never_receive_a_funding_outcome(self):
        confirmation = self.confirmation()
        self.account.current_balance = None
        self.account.save(update_fields=['current_balance'])
        source = affordability_source(self.user)
        self.assertIn('UNRESOLVED_ACCOUNT_BALANCE', source['issues'])
        confirmation['source_revision'] = source['source_revision']
        self.assertEqual(calculate_affordability(self.user, confirmation)['status'], 'INSUFFICIENT_DATA')
        self.expense.delete()
        self.assertIn('UNAVAILABLE_OBSERVED_AVERAGE_MONTHLY_VARIABLE_SPEND', affordability_source(self.user)['issues'])

    def test_unreconciled_loans_or_review_debits_block_sufficient_status(self):
        self.loan.verification_status = 'estimated'
        self.loan.save(update_fields=['verification_status'])
        self.assertIn('UNRECONCILED_LOANS', affordability_source(self.user)['issues'])
        self.loan.verification_status = 'confirmed'
        self.loan.remaining_balance = None
        self.loan.save(update_fields=['verification_status', 'remaining_balance'])
        self.assertIn('UNRECONCILED_LOANS', affordability_source(self.user)['issues'])
        Expense.objects.create(user=self.user, amount='60000', category='other')
        self.assertIn('UNRECONCILED_EXPENSES', affordability_source(self.user)['issues'])

    def test_canonical_exact_total_excludes_repeated_rent_loan_transfers_and_investments(self):
        for category, amount in (('rent', '100.00'), ('loan', '25.00'), ('transfer', '500.00'), ('investment', '300.00')):
            Expense.objects.create(user=self.user, amount=amount, category=category)
        baseline = resolve_canonical_financial_baseline(self.user, fresh=True)
        self.assertEqual(baseline['decimal_amounts']['essential_monthly_outflow'], '175.00')
        source = affordability_source(self.user)
        self.assertEqual(source['amounts']['essential_expenses'], '150.00')
        result = calculate_affordability(self.user, self.confirmation())
        self.assertEqual(result['amounts']['available_trip_funds'], '525.00')

    def test_aggregate_totals_not_clipped_to_a_stored_field_limit(self):
        confirmation = self.confirmation()
        confirmation['trip_budget']['amount'] = '999999999999.99'
        confirmation['contingency']['amount'] = '999999999999.99'
        result = calculate_affordability(self.user, confirmation)
        self.assertEqual(result['amounts']['total_trip_budget'], '1999999999999.98')
        self.assertEqual(result['amounts']['shortfall'], '1999999999474.98')

    def test_investment_and_credit_balances_are_not_spendable_cash(self):
        BankAccount.objects.create(user=self.user, account_number='investment', account_type='investment', current_balance='9000')
        self.assertEqual(affordability_source(self.user)['amounts']['cash_limit'], '1000.00')
        credit = BankAccount.objects.create(user=self.user, account_number='card', account_type='credit', current_balance=None)
        self.assertIn('UNRESOLVED_CREDIT_OBLIGATIONS', affordability_source(self.user)['issues'])
        credit.current_balance = 0
        credit.save(update_fields=['current_balance'])
        self.assertTrue(affordability_source(self.user)['complete'])

    def test_current_cash_and_actual_living_spend_evidence_required(self):
        from datetime import timedelta
        self.account.last_synced_at = timezone.now() - timedelta(days=2)
        self.account.save(update_fields=['last_synced_at'])
        self.assertIn('STALE_OR_UNDATED_CASH', affordability_source(self.user)['issues'])
        self.account.last_synced_at = None
        self.account.save(update_fields=['last_synced_at'])
        self.assertIn('STALE_OR_UNDATED_CASH', affordability_source(self.user)['issues'])
        self.expense.category = 'income'
        self.expense.direction = 'credit'
        self.expense.save(update_fields=['category', 'direction'])
        self.assertIn('STALE_OR_MISSING_LIVING_SPEND', affordability_source(self.user)['issues'])
        self.expense.category = 'groceries'
        self.expense.direction = 'debit'
        self.expense.transaction_date = timezone.localdate().replace(day=1) - timedelta(days=1)
        self.expense.save(update_fields=['category', 'direction', 'transaction_date'])
        self.assertIn('STALE_OR_MISSING_LIVING_SPEND', affordability_source(self.user)['issues'])

    def test_future_evidence_cannot_produce_a_funding_outcome(self):
        from datetime import timedelta
        Expense.objects.create(user=self.user, amount='1', category='groceries',
                               transaction_date=timezone.localdate() + timedelta(days=1))
        self.assertIn('FUTURE_DATED_EVIDENCE', affordability_source(self.user)['issues'])

    def test_open_debt_without_a_resolved_payment_schedule_blocks_assessment(self):
        for state in (dict(emi=0), dict(is_active=False), dict(status='defaulted'), dict(status='foreclosure_pending')):
            with self.subTest(state=state):
                Loan.objects.filter(pk=self.loan.pk).update(**{'emi':25, 'is_active':True, 'status':'active', **state})
                self.assertIn('UNRECONCILED_LOANS', affordability_source(self.user)['issues'])
