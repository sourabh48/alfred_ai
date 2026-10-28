"""Read-only, one-month liquidity assessment; no booking or financial advice.

Cash is owner-confirmed gross spendable cash before protected allocations.
Essentials exclude the separately counted loan obligation. Reserve, savings,
trip budget and EXTRA contingency must be disjoint, explicitly confirmed pots.
No future income, investments, debt principal or inferred currency is spendable.
"""
import json
import re
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.expenses.models import BankAccount, Expense
from apps.expenses.money import expense_money
from apps.expenses.services.cashflow_treatment import classify_cashflow
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.expenses.services.statement_evidence import evidence_for_rows
from apps.loans.models import Loan


FIELDS = ('spendable_cash', 'emergency_reserve', 'essential_expenses',
          'loan_obligations', 'committed_savings', 'trip_budget', 'contingency')


@transaction.atomic
def affordability_source(user):
    """Return owner-only exact canonical amounts and an opaque content revision.

    Currency is intentionally absent: legacy financial records do not establish
    it. The owner must explicitly verify matching currency before calculation.
    """
    if not getattr(user, 'is_authenticated', False) or not user.pk:
        raise PermissionDenied('Owner authentication required.')
    user = get_user_model().objects.get(pk=user.pk)
    expenses = list(Expense.objects.select_related('bank_account', 'statement_upload__bank_account').filter(user=user).order_by('transaction_date', 'id'))
    accounts = list(BankAccount.objects.filter(user=user, is_active=True))
    cash_accounts = [a for a in accounts if a.account_type not in ('credit', 'investment')]
    loans = list(Loan.objects.filter(user=user))
    baseline = resolve_canonical_financial_baseline(user, fresh=True, expenses=expenses)
    exact = baseline.get('decimal_amounts', {})
    issues = []
    statement_sources = evidence_for_rows(user, expenses)
    if any(status != 'owner_confirmed' for _, _, status in statement_sources):
        issues.append('UNVERIFIED_STATEMENT_SOURCE')
    for metric in ('liquid_cash', 'observed_average_monthly_variable_spend'):
        if baseline.get('metric_states', {}).get(metric, {}).get('status') != 'observed':
            issues.append('UNAVAILABLE_' + metric.upper())
    if not cash_accounts or any(a.current_balance is None or a.current_balance < 0 for a in cash_accounts):
        issues.append('UNRESOLVED_ACCOUNT_BALANCE')
    today = timezone.localdate()
    # C1 requires current-day cash evidence and current-month living-spend evidence.
    if any(not a.last_synced_at or a.last_synced_at > timezone.now() or
           timezone.localtime(a.last_synced_at).date() != today for a in cash_accounts):
        issues.append('STALE_OR_UNDATED_CASH')
    direct = [e for e in expenses if classify_cashflow(e).counts_direct_expense]
    if not direct or max(e.transaction_date for e in direct).replace(day=1) != today.replace(day=1):
        issues.append('STALE_OR_MISSING_LIVING_SPEND')
    if any(a.account_type == 'credit' and a.current_balance != 0 for a in accounts):
        issues.append('UNRESOLVED_CREDIT_OBLIGATIONS')
    if any(classify_cashflow(e).requires_review for e in expenses):
        issues.append('UNRECONCILED_EXPENSES')
    if any(e.transaction_date > today for e in expenses):
        issues.append('FUTURE_DATED_EVIDENCE')
    if any(l.verification_status != 'confirmed' or
           (l.status not in ('closed', 'foreclosed', 'prepaid') and
            (l.remaining_balance is None or l.remaining_balance < 0 or
             (l.remaining_balance > 0 and (l.status != 'active' or not l.is_active or l.emi <= 0)))) for l in loans):
        issues.append('UNRECONCILED_LOANS')
    try:
        # Canonical aggregate strings are exact; never route them through floats.
        cash = Decimal(exact['liquid_cash']) - sum((max(a.current_balance or Decimal('0'), Decimal('0'))
                    for a in accounts if a.account_type == 'investment'), Decimal('0'))
        loan = Decimal(exact['recurring_emi_burden'])
        essentials = Decimal(exact['essential_monthly_outflow']) - loan
        if any(not v.is_finite() or v < 0 for v in (cash, loan, essentials)):
            raise ValueError
        amounts = dict(cash_limit=format(cash, '.2f'),
                       essential_expenses=format(essentials, '.2f'),
                       loan_obligations=format(loan, '.2f'))
    except (KeyError, ArithmeticError, ValueError):
        amounts = {}
        issues.append('UNAVAILABLE_EXACT_AMOUNTS')
    today = today.isoformat()
    evidence = dict(version=2, owner=user.pk, date=today, baseline=baseline, statement_sources=statement_sources,
                    accounts=[(a.pk, a.current_balance, a.account_type, a.last_synced_at) for a in accounts],
                    expenses=[(e.pk, e.amount, e.category, e.classification, e.direction,
                               e.transaction_date, e.bank_account_id) for e in expenses],
                    loans=[(l.pk, l.verification_status, l.remaining_balance, l.status, l.updated_at) for l in loans])
    revision = salted_hmac('travel-affordability-v1', json.dumps(
        evidence, sort_keys=True, default=str, separators=(',', ':')), algorithm='sha256').hexdigest()
    return dict(source_revision=revision, as_of_date=today, period='one_month',
                reference_month=baseline['reference_month'], amounts=amounts,
                cash_observed_at=min((a.last_synced_at.isoformat() for a in cash_accounts
                                      if a.last_synced_at), default=None),
                spend_observed_through=max((e.transaction_date.isoformat() for e in direct), default=None),
                metric_states=baseline['metric_states'], complete=not issues, issues=issues)


def calculate_affordability(user, confirmation):
    """Assess only current, owner-confirmed, same-currency evidence.

    Service boundary only in C1; C2 will provide the authenticated UI/API.
    Confirmation requires all seven amounts, each with currency and verified=True,
    complete=True and disjoint_allocations=True. These are explicit attestations,
    never defaults. Zero must be explicitly confirmed; missing is not zero.
    """
    source = affordability_source(user)
    result = dict(status='INSUFFICIENT_DATA', certified=False, source=source,
                  currency=None, amounts=None, issues=list(source['issues']))
    if not isinstance(confirmation, dict):
        result['issues'].append('MALFORMED_CONFIRMATION')
        return result
    revision = confirmation.get('source_revision')
    if not isinstance(revision, str) or not constant_time_compare(revision, source['source_revision']):
        result['issues'].append('STALE_OR_FOREIGN_SOURCE')
    if confirmation.get('complete') is not True or confirmation.get('disjoint_allocations') is not True:
        result['issues'].append('OWNER_COMPLETENESS_REQUIRED')
    values = {}
    currency = None
    for field in FIELDS:
        item = confirmation.get(field)
        if not isinstance(item, dict) or item.get('verified') is not True:
            result['issues'].append('UNCONFIRMED_' + field.upper())
            continue
        code = item.get('currency')
        if not isinstance(code, str) or not re.fullmatch('[A-Z]{3}', code):
            result['issues'].append('INVALID_CURRENCY_' + field.upper())
            continue
        if currency is None:
            currency = code
        elif currency != code:
            result['issues'].append('CURRENCY_MISMATCH')
        value = item.get('amount')
        try:
            # Decimal text only: no float ingress, implicit null/boolean or exponent expansion.
            if not isinstance(value, (str, Decimal)) or len(str(value)) > 40:
                raise ValueError
            if Decimal(value) < 0:
                raise ValueError
            amount = expense_money(value)
            values[field] = amount
        except (ValueError, ArithmeticError):
            result['issues'].append('INVALID_AMOUNT_' + field.upper())
    if not result['issues']:
        canonical = source['amounts']
        if values['spendable_cash'] > Decimal(canonical['cash_limit']):
            result['issues'].append('CASH_EXCEEDS_CANONICAL_BALANCE')
        for field in ('essential_expenses', 'loan_obligations'):
            if values[field] != Decimal(canonical[field]):
                result['issues'].append('CANONICAL_MISMATCH_' + field.upper())
    if result['issues']:
        return result
    protected = sum((values[k] for k in ('emergency_reserve', 'essential_expenses',
                                       'loan_obligations', 'committed_savings')), Decimal('0.00'))
    remaining = values['spendable_cash'] - protected
    available = max(Decimal('0.00'), remaining)
    total = values['trip_budget'] + values['contingency']
    headroom = remaining - total
    result.update(status='WITHIN_CONFIRMED_FUNDS' if headroom >= 0 else 'SHORTFALL', currency=currency,
                  amounts={k: format(v, '.2f') for k, v in dict(
                      **values, protected_funds=protected, available_trip_funds=available,
                      total_trip_budget=total, headroom=headroom,
                      shortfall=max(Decimal('0.00'), -headroom)).items()})
    return result
