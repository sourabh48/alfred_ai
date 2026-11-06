"""AI-17: the assistant proposes a small set of record changes; nothing is saved until the owner confirms.

Parsing is deterministic (no model). Allowed actions never move money, book, trade or send anything.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction

from apps.budgets.models import SavingsGoal
from apps.budgets.money import budget_money
from apps.budgets.serializers import SavingsGoalSerializer

UNITS = {"k": Decimal("1000"), "thousand": Decimal("1000"), "lakh": Decimal("100000"), "lakhs": Decimal("100000"),
         "lac": Decimal("100000"), "lacs": Decimal("100000"), "crore": Decimal("10000000"), "crores": Decimal("10000000"),
         "cr": Decimal("10000000")}
AMOUNT = r"(?:₹|rs\.?|inr)?\s*(?P<{0}>\d[\d,]*(?:\.\d{{1,2}})?)[\s-]*(?P<{0}_unit>k|thousand|lakhs?|lacs?|crores?|cr)?\b(?:\s*rupees)?"
CREATE = re.compile(
    r"^(?:please\s+)?(?:add|create|set\s+up|start|make)\s+(?:a\s+|an\s+|the\s+)?(?:new\s+)?savings\s+goal\s+"
    r"(?:called\s+|named\s+|for\s+)?[\"']?(?P<name>.+?)[\"']?\s+(?:of|for|with\s+a\s+target\s+of|target(?:ing)?)\s+"
    + AMOUNT.format("target") + r"(?:\s+(?:by|before)\s+(?P<date>.+?))?\s*[.!]?$", re.I)
UPDATE = re.compile(
    r"^(?:please\s+)?(?:update|set)\s+(?:my\s+|the\s+)?[\"']?(?P<name>.+?)[\"']?\s+(?:goal\s+)?(?:saved|savings|progress|saved\s+amount)\s+to\s+"
    + AMOUNT.format("saved") + r"\s*[.!]?$", re.I)
ACTIONS = ("create_savings_goal", "update_savings_goal")


class ActionError(ValueError):
    pass


def _amount(match, key):
    try:
        value = Decimal(match.group(key).replace(",", ""))
    except InvalidOperation:
        raise ActionError("I could not read that amount.") from None
    unit = (match.group(key + "_unit") or "").lower()
    return budget_money(value * UNITS.get(unit, Decimal("1")))


def _target_date(text, today):
    text = text.strip().rstrip(".!").replace(",", "")
    for pattern in ("%Y-%m-%d", "%d %B %Y", "%d %b %Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            pass
    for pattern in ("%B %Y", "%b %Y"):
        try:
            month = datetime.strptime(text, pattern).date()
            return month.replace(day=calendar.monthrange(month.year, month.month)[1])
        except ValueError:
            pass
    raise ActionError("Write the date like 31 March 2027, March 2027 or 2027-03-31.")


def _rupees(value):
    return f"₹{value:,.2f}"


def _money(value, currency):
    return _rupees(value) if currency in (None, "", "INR") else f"{currency} {value:,.2f}"


def propose(user, text, today=None):
    """Return a proposal dict, or None when the text is not one of the supported actions."""
    today = today or date.today()
    text = " ".join(str(text or "").split())[:300]
    if match := CREATE.match(text):
        name = match.group("name").strip()
        fields = {"name": name, "target_amount": str(_amount(match, "target")), "saved_amount": "0.00"}
        summary = f"Create savings goal \"{name}\" with a target of {_rupees(Decimal(fields['target_amount']))}"
        if match.group("date"):
            due = _target_date(match.group("date"), today)
            if due < today:
                raise ActionError("That target date has already passed.")
            fields["target_date"] = due.isoformat()
            summary += f" by {due:%d %b %Y}"
        return {"action": "create_savings_goal", "fields": fields, "summary": summary + "."}
    if match := UPDATE.match(text):
        name = match.group("name").strip()
        goals = list(SavingsGoal.objects.filter(user=user, name__iexact=name)[:2])
        if len(goals) != 1:
            raise ActionError(f"I found {'no' if not goals else 'more than one'} savings goal named \"{name}\". Check the name on Budgets.")
        saved = _amount(match, "saved")
        goal = goals[0]
        return {"action": "update_savings_goal", "fields": {"id": goal.pk, "saved_amount": str(saved)},
                "summary": f"Set saved so far for \"{goal.name}\" from {_money(goal.saved_amount, goal.currency)} to {_money(saved, goal.currency)}."}
    return None


def confirm(user, action, fields):
    """Apply an owner-confirmed action through the same validation as the Budgets API."""
    if action not in ACTIONS or not isinstance(fields, dict):
        raise ActionError("This action is not supported.")
    with transaction.atomic():
        if action == "create_savings_goal":
            serializer = SavingsGoalSerializer(data={key: fields.get(key) for key in ("name", "target_amount", "saved_amount", "target_date") if fields.get(key) is not None})
        else:
            goal = SavingsGoal.objects.select_for_update().filter(user=user, pk=fields.get("id")).first()
            if goal is None:
                raise ActionError("That savings goal no longer exists.")
            serializer = SavingsGoalSerializer(goal, data={"saved_amount": fields.get("saved_amount")}, partial=True)
        if not serializer.is_valid():
            raise ActionError("Those values are not valid: " + "; ".join(f"{key}: {' '.join(map(str, value))}" for key, value in serializer.errors.items()))
        goal = serializer.save(user=user) if action == "create_savings_goal" else serializer.save()
    return {"message": f"Saved \"{goal.name}\". Open Budgets to see it.", "url": "/budgets/", "goal": serializer.data}
