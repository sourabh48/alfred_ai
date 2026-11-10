"""AI-17: the assistant proposes a small set of record changes; nothing is saved until the owner confirms.

Parsing is deterministic (no model). Allowed actions never move money, book, trade or send anything.
"""
from __future__ import annotations

import calendar
import json
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.budgets.models import SavingsGoal
from apps.budgets.money import budget_money
from apps.budgets.serializers import SavingsGoalSerializer
from apps.reports.models import OperationalLog
from apps.reports.services import operational_logging_service

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
PROPOSAL_TTL = timedelta(minutes=10)
SCOPE = "assistant_action"


class ActionError(ValueError):
    pass


class ActionConflict(ActionError):
    pass


def _digest(value):
    try:
        encoded = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError):
        raise ActionError("Use valid action fields.") from None
    if len(encoded.encode()) > 4096:
        raise ActionError("The action is too large. Make a new request.")
    # Keyed fingerprints keep low-entropy personal values out of audit records.
    return salted_hmac("alfred.assistant-action.v1", encoded, algorithm="sha256").hexdigest()


def _revision(goal):
    values = {key: getattr(goal, key) for key in (
        "id", "user_id", "name", "target_amount", "saved_amount", "target_date", "currency")}
    values["updated_at"] = goal.updated_at.isoformat()
    return _digest(values)


def _amount(match, key):
    try:
        value = Decimal(match.group(key).replace(",", ""))
    except InvalidOperation:
        raise ActionError("I could not read that amount.") from None
    unit = (match.group(key + "_unit") or "").lower()
    try:
        return budget_money(value * UNITS.get(unit, Decimal("1")))
    except ValueError:
        raise ActionError("Enter an amount within the supported range.") from None


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
    if text is not None and (not isinstance(text, str) or len(text.encode()) > 1200):
        raise ActionError("Use a short text request for the savings goal.")
    text = " ".join((text or "").split())
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
                "revision": _revision(goal),
                "summary": f"Set saved so far for \"{goal.name}\" from {_money(goal.saved_amount, goal.currency)} to {_money(saved, goal.currency)}."}
    return None


def _serializer(user, action, fields):
    if action not in ACTIONS or not isinstance(fields, dict):
        raise ActionError("This action is not supported.")
    if action == "create_savings_goal":
        serializer = SavingsGoalSerializer(data=fields)
    else:
        if type(fields.get("id")) is not int:
            raise ActionError("Choose a valid savings goal.")
        goal = SavingsGoal.objects.select_for_update().filter(user=user, pk=fields["id"]).first()
        if goal is None:
            raise ActionConflict("That savings goal no longer exists. Make a new request.")
        serializer = SavingsGoalSerializer(goal, data={"saved_amount": fields.get("saved_amount")}, partial=True)
    if not serializer.is_valid():
        raise ActionError("Those values are not valid: " + "; ".join(f"{key}: {' '.join(map(str, value))}" for key, value in serializer.errors.items()))
    return serializer


@transaction.atomic
def prepare(user, text, today=None):
    proposal = propose(user, text, today)
    if proposal is None:
        return None
    serializer = _serializer(user, proposal["action"], proposal["fields"])
    if serializer.instance and _revision(serializer.instance) != proposal["revision"]:
        raise ActionConflict("The goal changed while preparing this review. Make a new request.")
    now = timezone.now()
    if _records(user).filter(created_at__gt=now-PROPOSAL_TTL, event_type="assistant_action_pending").count() >= 20:
        raise ActionError("Too many pending actions. Cancel a review or wait ten minutes.")
    identity = uuid4().hex
    expires = now + PROPOSAL_TTL
    operational_logging_service.log(user=user, module="assistant", category="api", scope=SCOPE,
        event_type="assistant_action_pending", message="Savings-goal action awaiting owner confirmation.",
        payload=dict(proposal_id=identity, action=proposal["action"], state="pending", expires_at=expires.isoformat(),
                     revision=proposal.get("revision"), binding=_digest([user.pk, identity, proposal["action"], proposal["fields"]])))
    return {**proposal, "proposal_id": identity, "expires_at": expires.isoformat()}


def _records(user):
    return OperationalLog.objects.filter(user=user, module="assistant", scope=SCOPE)


def _identity(identity):
    if not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{32}", identity):
        raise ActionError("Review a new server proposal before confirming.")


def _receipt(payload, replay=False):
    return dict(message="Savings goal saved. Open Budgets to see it.", url="/budgets/",
                goal_id=payload["goal_id"], already_applied=replay)


@transaction.atomic
def confirm(user, identity, action, fields):
    """The redacted audit claim and canonical write commit together, including on SQLite."""
    _identity(identity)
    if action not in ACTIONS or not isinstance(fields, dict):
        raise ActionError("This action is not supported.")
    binding = _digest([user.pk, identity, action, fields])
    records = _records(user).filter(payload__proposal_id=identity)
    # Write before reading: SQLite must serialize concurrent claims, not upgrade a stale read transaction.
    claimed = records.filter(event_type="assistant_action_pending").update(event_type="assistant_action_claimed")
    record = records.select_for_update().first()
    if record is None:
        raise ActionError("This proposal is unavailable. Make a new request.")
    payload = record.payload
    if not constant_time_compare(payload["binding"], binding):
        raise ActionError("The reviewed action was changed. Make a new request.")
    if not claimed:
        if payload["state"] == "confirmed":
            return _receipt(payload, replay=True)
        raise ActionConflict("This proposal was cancelled. Make a new request.")
    if timezone.now() >= datetime.fromisoformat(payload["expires_at"]):
        raise ActionConflict("This proposal expired. Make a new request.")
    serializer = _serializer(user, action, fields)
    if serializer.instance and _revision(serializer.instance) != payload["revision"]:
        raise ActionConflict("The goal changed after this review. Make a new request.")
    goal = serializer.save(user=user) if action == "create_savings_goal" else serializer.save()
    payload.update(state="confirmed", goal_id=goal.pk, confirmed_at=timezone.now().isoformat())
    record.payload = payload
    record.event_type = "assistant_action_confirmed"
    record.message = "Owner-confirmed savings-goal action applied once."
    record.save(update_fields=["payload", "event_type", "message"])
    return _receipt(payload)


@transaction.atomic
def cancel(user, identity):
    _identity(identity)
    records = _records(user).filter(payload__proposal_id=identity)
    records.filter(event_type="assistant_action_pending").update(event_type="assistant_action_cancelled")
    record = records.select_for_update().first()
    if record is None:
        raise ActionError("This proposal is unavailable. Make a new request.")
    if record.payload["state"] == "confirmed":
        raise ActionConflict("This action was already saved. Check Budgets.")
    record.payload = {**record.payload, "state": "cancelled"}
    record.message = "Savings-goal proposal cancelled; no financial posting."
    record.save(update_fields=["payload", "message"])
    return {"message": "Cancelled. Nothing was saved."}
