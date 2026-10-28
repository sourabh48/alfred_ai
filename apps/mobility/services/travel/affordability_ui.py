"""Saved-trip evidence binding and presentation for the read-only C1 service."""
import json
import re
from decimal import Decimal, InvalidOperation

from django.utils.crypto import salted_hmac
from apps.expenses.money import expense_money

from .affordability import affordability_source, calculate_affordability


def trip_context(session, plan):
    evidence = dict(session=session.pk, revision=session.revision, owner=plan.user_id,
                    plan=plan.pk, title=plan.title, budget=str(plan.budget),
                    start=str(plan.start_date), end=str(plan.end_date),
                    state=plan.planning_state, itinerary=plan.itinerary)
    snapshot = salted_hmac('travel-affordability-trip-v1', json.dumps(
        evidence, sort_keys=True, default=str, separators=(',', ':')), algorithm='sha256').hexdigest()
    budget = plan.itinerary.get('budget', {}) if isinstance(plan.itinerary, dict) else {}
    estimate = None
    if isinstance(budget, dict) and budget.get('status') != 'needs_recalculation':
        try:
            value = Decimal(str(budget['expected']))
            code = budget.get('currency')
            if value.is_finite() and 0 <= value <= Decimal('999999999999.99') and isinstance(code, str) and re.fullmatch('[A-Z]{3}', code):
                estimate = dict(amount=format(expense_money(value), '.2f'), currency=code, kind='ESTIMATED_NOT_VERIFIED')
        except (KeyError, InvalidOperation, TypeError, ValueError):
            pass
    return dict(snapshot=snapshot, revision=session.revision, title=plan.title,
                estimate=estimate, estimate_status='ESTIMATED_NOT_VERIFIED' if estimate else 'UNAVAILABLE_OR_INVALIDATED',
                scope='Current cash and one month of protected obligations only; future income/spending before departure is not projected.')


def affordability_dashboard(user, session, plan):
    return dict(source=affordability_source(user), trip=trip_context(session, plan))


def affordability_scenario(user, confirmation):
    result = calculate_affordability(user, confirmation)
    if result['status'] == 'INSUFFICIENT_DATA':
        result['label'] = 'Insufficient Data'
    else:
        headroom = Decimal(result['amounts']['headroom'])
        result['label'] = 'Over Budget' if headroom < 0 else 'Tight' if headroom == 0 else 'Affordable'
    result['interpretation'] = 'Scenario only, not certified advice. Tight means exactly zero headroom after the extra contingency.'
    return result
