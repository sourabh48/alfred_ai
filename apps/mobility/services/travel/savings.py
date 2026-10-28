"""Private, read-only future cash scenarios; projected salary is never current cash."""
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from django.utils.crypto import constant_time_compare, salted_hmac

from apps.expenses.models import Expense
from apps.expenses.money import expense_money
from apps.expenses.services.cashflow_treatment import classify_cashflow
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.loans.models import Loan
from .affordability import calculate_affordability

CENT = Decimal('.01')
SCENARIOS = ('conservative', 'baseline', 'optimistic')


def savings_source(user):
    baseline = resolve_canonical_financial_baseline(user, fresh=True)
    loans = [dict(id=l.pk, emi=str(l.emi), start=l.start_date.isoformat())
             for l in Loan.objects.filter(user=user, is_active=True, status='active', remaining_balance__gt=0).order_by('pk')]
    income_dates = [e.transaction_date.isoformat() for e in Expense.objects.filter(user=user)
                    if classify_cashflow(e).counts_income]
    source = dict(monthly_income=baseline.get('decimal_amounts', {}).get('monthly_income'),
                  income_state=baseline.get('metric_states', {}).get('monthly_income', {}),
                  income_observed_through=max(income_dates, default=None), loans=loans)
    source['revision'] = salted_hmac('travel-savings-v1', json.dumps(
        dict(owner=user.pk, baseline=baseline, source=source), sort_keys=True, default=str), algorithm='sha256').hexdigest()
    return source


def _date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError
    return date.fromisoformat(value)


def _money(item, currency):
    if (not isinstance(item, dict) or set(item) != {'amount', 'currency', 'verified'} or
            item['currency'] != currency or item['verified'] is not True or
            not isinstance(item['amount'], str) or len(item['amount']) > 40 or Decimal(item['amount']) < 0):
        raise ValueError
    return expense_money(item['amount'])


def calculate_savings(user, confirmation, assumptions):
    current = calculate_affordability(user, confirmation)
    source = savings_source(user)
    result = dict(status='INSUFFICIENT_DATA', certified=False, current=current, source=source,
                  scenarios=None, issues=list(current['issues']))
    if not isinstance(assumptions, dict):
        result['issues'].append('MALFORMED_SAVINGS_ASSUMPTIONS')
        return result
    if not isinstance(assumptions.get('source_revision'), str) or not constant_time_compare(assumptions['source_revision'], source['revision']):
        result['issues'].append('STALE_OR_FOREIGN_SOURCE')
    if result['issues']:
        return result
    try:
        if set(assumptions) != {'source_revision', 'departure', 'income_from', 'income_until', 'verified_on',
                                'monthly_income', 'monthly_goals', 'monthly_contribution', 'schedules', 'scenarios', 'confirmed'}:
            raise ValueError
        today = _date(current['source']['as_of_date'])
        departure = _date(assumptions['departure'])
        start = today + timedelta(days=1)
        # Bounded monthly output; departure day income is unavailable for the trip.
        if not today < departure <= today + timedelta(days=366 * 5):
            raise ValueError
        if (assumptions['confirmed'] is not True or _date(assumptions['verified_on']) != today or
                not _date(assumptions['income_from']) <= today or _date(assumptions['income_until']) < departure - timedelta(days=1)):
            raise ValueError
        currency = current['currency']
        income = _money(assumptions['monthly_income'], currency)
        goals = _money(assumptions['monthly_goals'], currency)
        contribution = _money(assumptions['monthly_contribution'], currency)
        if (income <= 0 or source['income_state'].get('status') == 'unavailable' or
                income != Decimal(source['monthly_income'])):
            raise ValueError
        schedules = assumptions['schedules']
        if not isinstance(schedules, list) or len(schedules) != len(source['loans']) or len(schedules) > 100:
            raise ValueError
        dues = []
        seen = set()
        for schedule in schedules:
            if (not isinstance(schedule, dict) or set(schedule) != {'id', 'next_due', 'final_due', 'verified'} or
                    type(schedule['id']) is not int or schedule['id'] in seen or schedule['verified'] is not True):
                raise ValueError
            loan = next(l for l in source['loans'] if l['id'] == schedule['id'])
            seen.add(loan['id'])
            due = _date(schedule['next_due'])
            final = _date(schedule['final_due']) if schedule['final_due'] else None
            if due <= today or due < _date(loan['start']) or (final and final < due):
                raise ValueError
            anchor = due.day
            # Irregular final payments need their own verified amounts; never silently omit one.
            if final and final.day != min(anchor, calendar.monthrange(final.year, final.month)[1]):
                raise ValueError
            while due < departure and (final is None or due <= final):
                dues.append((due, Decimal(loan['emi'])))
                year, month = due.year + (due.month == 12), due.month % 12 + 1
                due = date(year, month, min(anchor, calendar.monthrange(year, month)[1]))
        if sum((Decimal(l['emi']) for l in source['loans']), Decimal(0)) != Decimal(current['amounts']['loan_obligations']):
            raise ValueError
        specs = assumptions['scenarios']
        if not isinstance(specs, dict) or set(specs) != set(SCENARIOS):
            raise ValueError
        factors = {}
        for name in SCENARIOS:
            spec = specs[name]
            if not isinstance(spec, dict) or set(spec) != {'income_percent', 'expense_percent'}:
                raise ValueError
            if any(not isinstance(v, str) or len(v) > 8 for v in spec.values()):
                raise ValueError
            inc, out = (Decimal(spec[k]) for k in ('income_percent', 'expense_percent'))
            if not inc.is_finite() or not out.is_finite() or not 0 <= inc <= 100 or not 100 <= out <= 200:
                raise ValueError
            factors[name] = inc / 100, out / 100
        if not (factors['conservative'][0] <= factors['baseline'][0] <= factors['optimistic'][0] and
                factors['conservative'][1] >= factors['baseline'][1] >= factors['optimistic'][1]):
            raise ValueError
    except (ValueError, ArithmeticError, TypeError, KeyError, StopIteration):
        result['issues'].append('INVALID_OR_INCOMPLETE_SAVINGS_ASSUMPTIONS')
        return result
    amounts = {key: Decimal(value) for key, value in current['amounts'].items()}
    opening = amounts['spendable_cash'] - amounts['emergency_reserve'] - amounts['committed_savings']
    target = amounts['total_trip_budget']
    periods = []
    cursor = start
    while cursor < departure:
        next_month = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
        end = min(next_month, departure)
        fraction = Decimal((end - cursor).days) / Decimal(calendar.monthrange(cursor.year, cursor.month)[1])
        periods.append((cursor, end, fraction))
        cursor = end
    weight = sum((p[2] for p in periods), Decimal(0))
    scenarios = {}
    for name, (income_factor, expense_factor) in factors.items():
        funds, rows, losses = opening, [], Decimal(0)
        for begin, end, fraction in periods:
            earned = (income * income_factor * fraction).quantize(CENT, rounding=ROUND_FLOOR)
            essential = (amounts['essential_expenses'] * expense_factor * fraction).quantize(CENT, rounding=ROUND_CEILING)
            committed = (goals * fraction).quantize(CENT, rounding=ROUND_CEILING)
            emi = sum((value for due, value in dues if begin <= due < end), Decimal(0))
            net = earned - essential - committed - emi
            planned = (contribution * fraction).quantize(CENT, rounding=ROUND_FLOOR)
            allocated = min(net, planned)  # Negative cash flow consumes unallocated cash; never hide a deficit.
            funds += allocated
            losses += min(net, Decimal(0))
            rows.append(dict(start=begin.isoformat(), end_exclusive=end.isoformat(), days=(end-begin).days,
                             **{k: format(v, '.2f') for k, v in dict(income=earned, essentials=essential,
                                goals=committed, emi=emi, net_cashflow=net, trip_allocation=allocated, projected_funds=funds).items()}))
        needed = max(Decimal(0), target - opening - losses)
        required = (needed / weight).quantize(CENT, rounding=ROUND_CEILING) if weight else None
        scenarios[name] = dict(months=rows, projected_trip_funds=format(max(Decimal(0), funds), '.2f'),
            protected_funding_deficit=format(max(Decimal(0), -funds), '.2f'),
            headroom=format(funds-target, '.2f'), shortfall=format(max(Decimal(0), target-funds), '.2f'),
            required_monthly_saving=format(required, '.2f') if required is not None else None,
            status='PROJECTED_WITHIN_BUDGET' if funds >= target else 'PROJECTED_SHORTFALL', assumptions=specs[name])
    result.update(status='PROJECTED_ESTIMATE', currency=current['currency'], departure=departure.isoformat(),
                  projected_from=start.isoformat(), starting_unallocated_cash=format(opening, '.2f'), scenarios=scenarios,
                  limitations=['Future income is uncertain, not guaranteed or spendable today.',
                    'Daily accrual model, not a payday or bank-balance forecast. Departure day is excluded.',
                    'Reserve and existing goals are protected once. Future goals and scheduled EMIs are deducted separately.',
                    'Only planned contributions are allocated; excess cash flow is excluded. Deficits reduce trip funds.',
                    'Required monthly saving is an estimated lower bound before cent rounding; cash-flow capacity may prevent it.'])
    return result
