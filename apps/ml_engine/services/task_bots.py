"""In-app task bots (owner request 2026-11-14: "i need bots to do tasks"); AI-17 propose-then-confirm, WEALTH2-002 stale check.

Each bot reads the owner's own records, deterministically and without a model, and writes one reviewable proposal.
Nothing changes until the owner confirms in the app. The only actions a confirmation can run are travel reminders
and a travel recheck; every money, booking, trading or sending step stays with the owner on its own page.
"""
from __future__ import annotations

import calendar
import json
import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.reports.models import OperationalLog
from apps.reports.services import operational_logging_service
from .assistant_actions import ActionConflict, ActionError

SCOPE = "assistant_bot"
PENDING, CONFIRMED, DISMISSED, SUPERSEDED = "bot_proposal_pending", "bot_proposal_confirmed", "bot_proposal_dismissed", "bot_proposal_superseded"
ITEM_LIMIT = 20
logger = logging.getLogger(__name__)


class BotUnavailable(ActionError):
    pass


def _amount(value, currency):
    return f"₹{value:,.2f}" if currency == "INR" else f"{currency} {value:,.2f}" if currency else f"{value:,.2f} (currency not recorded)"


def _item(key, title, detail, url, action=None):
    return {"id": key, "title": title, "detail": detail, "url": url, "action": action}


def money_review(user, today):
    from apps.expenses.models import Expense
    spend = Expense.objects.filter(user=user, classification="expense", direction="debit")
    week, previous = (today - timedelta(days=6), today), (today - timedelta(days=13), today - timedelta(days=7))
    totals = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    for index, window in enumerate((week, previous)):
        for row in spend.filter(transaction_date__range=window).values("currency").annotate(total=Sum("amount")):
            totals[row["currency"]][index] = row["total"] or Decimal("0")
    items = []
    for currency, (now, before) in sorted(totals.items(), key=lambda pair: pair[0] or ""):
        if not now:
            continue
        top = (spend.filter(transaction_date__range=week, currency=currency).values("category")
               .annotate(total=Sum("amount")).order_by("-total", "category")[:3])
        items.append(_item(f"spend:{currency or 'none'}", f"Spent {_amount(now, currency)} in the last 7 days",
            f"The 7 days before: {_amount(before, currency)}. Largest: "
            + ", ".join(f"{row['category']} {_amount(row['total'], currency)}" for row in top) + ".", "/expenses/"))
    uncategorised = spend.filter(category="other", transaction_date__gte=today - timedelta(days=30)).count()
    if uncategorised:
        items.append(_item("uncategorised", f"{uncategorised} spend(s) in the last 30 days are in Other",
            "Give them a category so budgets and reviews are right.", "/expenses/"))
    return items


def _next_due(day, after):
    """The next date on or after `after` that falls on this day of the month (the last day in a shorter month)."""
    year, month = after.year, after.month
    for _ in range(2):
        due = after.replace(year=year, month=month, day=min(day, calendar.monthrange(year, month)[1]))
        if due >= after:
            return due
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return due


def bills_due(user, today):
    from apps.loans.models import Loan
    items = []
    for loan in Loan.objects.filter(user=user, is_active=True, status="active", emi__gt=0).order_by("id"):
        anchor = loan.last_payment_date or loan.start_date
        # A payment recorded in the last 20 days covers this month's instalment.
        start = max(today, loan.last_payment_date + timedelta(days=20)) if loan.last_payment_date else today
        due = _next_due(anchor.day, start)
        if due <= today + timedelta(days=7):
            name = loan.lender or loan.get_loan_type_display()
            items.append(_item(f"loan:{loan.pk}:{due.isoformat()}", f"EMI {_amount(loan.emi, loan.currency)} to {name} around {due:%d %b}",
                f"Estimated from the day of your {'last recorded payment' if loan.last_payment_date else 'loan start date'}; "
                "check your lender's schedule. ALFRED never pays for you.", "/loans/"))
    return items


def fund_review(user, today):
    from apps.investments.services.beginner_guide import beginner_guide
    try:
        holdings = beginner_guide(user, {"available": False})["holdings"]
    except Exception as error:  # AMFI prices may be unreachable offline; the bot reports that rather than guessing.
        raise BotUnavailable("Fund prices from AMFI are not available right now. Try again later.") from error
    return [_item(f"fund:{row['id']}:{row['action']}", f"{row['name']}: {row['action'].title()}", row["text"]
                  + " A guide from AMFI prices, not financial advice; ALFRED never buys or sells.", "/investments/")
            for row in holdings if row["action"] in ("review", "sell")]


def paperwork(user, today):
    from apps.mobility.models import BikeDocument, BikeServiceRecord
    items, seen = [], set()
    for doc in BikeDocument.objects.filter(user=user, expiry_date__isnull=False, document_type__in=("insurance", "puc", "rc")).order_by("-expiry_date", "-id"):
        key = (doc.bike_profile_id or doc.bike_name, doc.document_type)
        if key in seen:
            continue
        seen.add(key)
        if doc.expiry_date <= today + timedelta(days=30):
            word = "expired" if doc.expiry_date < today else "expires"
            items.append(_item(f"doc:{doc.pk}:{doc.expiry_date.isoformat()}", f"{doc.bike_name} {doc.document_type.upper()} {word} {doc.expiry_date:%d %b %Y}",
                "From your saved vehicle document. Renew it with the issuer and upload the new copy.", "/bike-service/"))
    seen = set()
    for service in BikeServiceRecord.objects.filter(user=user).order_by("-service_date", "-id"):
        key = service.bike_profile_id or service.bike_name
        if key in seen:
            continue
        seen.add(key)
        if service.next_service_date and service.next_service_date <= today + timedelta(days=14):
            items.append(_item(f"service:{service.pk}:{service.next_service_date.isoformat()}", f"{service.bike_name} service due {service.next_service_date:%d %b %Y}",
                "The next-service date on your last service record.", "/bike-service/"))
    return items


def career_follow_ups(user, today):
    from apps.career.models import CareerJobAnalysis
    from apps.career.services import application_tracker
    items = []
    for analysis in CareerJobAnalysis.objects.filter(user=user).order_by("-updated_at", "-id")[:300]:
        payload = analysis.extracted_payload if isinstance(analysis.extracted_payload, dict) else {}
        status = application_tracker.follow_up_status(payload.get("application"), today=today)
        if status["status"] == "due":
            items.append(_item(f"career:{analysis.pk}:{status['due_on']}", f"Follow up: {analysis.job_title} at {analysis.company}",
                status["detail"] + " Draft it on Career; nothing is sent without your approval.", "/career/"))
    return items


def travel_prep(user, today):
    from apps.mobility.services.travel.proactive import upcoming_steps
    soon = (today + timedelta(days=7)).isoformat()
    return [_item(f"travel:{step['id']}", f"{step['trip']}: {step['title']}", step["detail"], "/mobility/"
                  + (f"?session={step['session_id']}" if step["session_id"] else ""),
                  {**step["action"], "plan_id": step["plan_id"]} if step["action"] else None)
            for step in upcoming_steps(user, today) if step["action"] or (step["due_on"] or "9999") <= soon]


BOTS = {
    "money_review": ("Weekly money review", 7, money_review, "Last 7 days of spending against the week before."),
    "bills_due": ("Bills and EMIs due", 1, bills_due, "Loan instalments due in the next 7 days."),
    "fund_review": ("Fund review", 1, fund_review, "Owned funds that dropped from their recent high (AMFI prices)."),
    "paperwork": ("Documents and service", 1, paperwork, "Vehicle papers expiring and bike service due."),
    "career_follow_ups": ("Career follow-ups", 1, career_follow_ups, "Applications where a follow-up is due."),
    "travel_prep": ("Travel preparation", 1, travel_prep, "Next steps for trips in the coming weeks."),
}


def catalog():
    return [{"name": name, "label": label, "every_days": days, "description": text} for name, (label, days, _, text) in BOTS.items()]


def _fingerprint(user, bot, items):
    encoded = json.dumps([user.pk, bot, items], cls=DjangoJSONEncoder, sort_keys=True, separators=(",", ":"))
    return salted_hmac("alfred.task-bot.v1", encoded, algorithm="sha256").hexdigest()


def _records(user):
    return OperationalLog.objects.filter(user=user, module="assistant", scope=SCOPE)


def _items(user, bot, today):
    if bot not in BOTS:
        raise ActionError("Choose one of ALFRED's bots.")
    return BOTS[bot][2](user, today)[:ITEM_LIMIT]


def _public(record):
    payload = record.payload
    return {"proposal_id": payload["proposal_id"], "bot": payload["bot"], "label": BOTS[payload["bot"]][0],
            "state": payload["state"], "created_at": record.created_at.isoformat(), "for_date": payload["for_date"],
            "fingerprint": payload["fingerprint"], "items": payload["items"]}


@transaction.atomic
def run(user, bot, today=None, *, trigger="request"):
    """Prepare or refresh the bot's proposal. Returns it, or None when nothing is due."""
    today = today or timezone.localdate()
    items = _items(user, bot, today)
    fingerprint = _fingerprint(user, bot, items)
    pending = _records(user).select_for_update().filter(event_type=PENDING, payload__bot=bot)
    same = next((record for record in pending if record.payload["fingerprint"] == fingerprint), None)
    for record in pending:
        if record is not same:
            record.event_type, record.payload = SUPERSEDED, {**record.payload, "state": "superseded"}
            record.save(update_fields=["event_type", "payload"])
    if same:
        return _public(same)
    if not items:
        return None
    record = operational_logging_service.log(user=user, module="assistant", category="background" if trigger == "schedule" else "api",
        scope=SCOPE, event_type=PENDING, message=f"{BOTS[bot][0]} prepared a review; nothing changes until the owner confirms.",
        payload=dict(proposal_id=uuid4().hex, bot=bot, state="pending", for_date=today.isoformat(), trigger=trigger,
                     fingerprint=fingerprint, items=items))
    return _public(record)


def pending(user):
    return [_public(record) for record in _records(user).filter(event_type=PENDING).order_by("-created_at", "-id")[:50]
            if record.payload.get("bot") in BOTS]


def _pending_record(user, identity):
    if not isinstance(identity, str) or len(identity) != 32:
        raise ActionError("Choose a proposal from the list.")
    record = _records(user).select_for_update().filter(payload__proposal_id=identity).first()
    if record is None:
        raise ActionError("This proposal is unavailable. Run the bot again.")
    if record.event_type != PENDING:
        raise ActionConflict(f"This proposal was already {record.payload['state']}. Run the bot again.")
    return record


def _apply(user, action):
    from apps.mobility.models import TravelPlanningSession
    from apps.mobility.services.travel import reminders
    from apps.mobility.services.travel_research import queue_research
    session = TravelPlanningSession.objects.filter(user=user, plan_id=action["plan_id"]).first()
    if session is None:
        raise ActionConflict("That trip is no longer saved. Run the bot again.")
    if action["type"] == "recheck":
        queue_research(session, recheck=True)
        return "Weather and route recheck started."
    revision = reminders.reminder_payload(session)["revision"]
    if action["enable"]:
        reminders.update_reminders(session, dict(action="reminders", operation="consent", request_id=str(uuid4()),
                                                 reminder_revision=revision, enabled=True))
        revision += 1
    reminders.update_reminders(session, dict(action="reminders", operation="create", request_id=str(uuid4()), reminder_revision=revision,
                                             reminder_id=str(uuid4()), label=action["label"], zone=action["zone"], local_time=action["local_time"]))
    return "Reminder added."


@transaction.atomic
def confirm(user, identity, item_ids, fingerprint, today=None):
    """Apply the chosen items of a reviewed proposal once, if nothing it depends on changed since."""
    record = _pending_record(user, identity)
    payload = record.payload
    if not isinstance(item_ids, list) or not all(isinstance(key, str) for key in item_ids) or len(item_ids) > ITEM_LIMIT:
        raise ActionError("Choose items from this proposal.")
    if not isinstance(fingerprint, str) or not constant_time_compare(fingerprint, payload["fingerprint"]):
        raise ActionError("The reviewed proposal was changed. Run the bot again.")
    items = {item["id"]: item for item in payload["items"]}
    if set(item_ids) - set(items):
        raise ActionError("Choose items from this proposal.")
    if _fingerprint(user, payload["bot"], _items(user, payload["bot"], today or timezone.localdate())) != payload["fingerprint"]:
        raise ActionConflict("Your records changed after this review. Run the bot again for a fresh one.")
    results = []
    for key in item_ids:
        if items[key]["action"]:
            results.append({"id": key, "result": _apply(user, items[key]["action"])})
    payload.update(state="confirmed", confirmed_at=timezone.now().isoformat(), applied=results, reviewed=item_ids)
    record.event_type, record.payload = CONFIRMED, payload
    record.message = f"Owner confirmed {BOTS[payload['bot']][0]}; {len(results)} action(s) applied once."
    record.save(update_fields=["event_type", "payload", "message"])
    return {"message": (" ".join(r["result"] for r in results) or "Marked as reviewed. Nothing else changed."), "applied": results}


@transaction.atomic
def dismiss(user, identity):
    record = _pending_record(user, identity)
    record.event_type, record.payload = DISMISSED, {**record.payload, "state": "dismissed"}
    record.save(update_fields=["event_type", "payload"])
    return {"message": "Dismissed. Nothing was changed."}


def run_scheduled(today=None):
    """Daily Huey job: refresh every bot that is due for each active account; one failure never stops the rest."""
    today = today or timezone.localdate()
    ran = failed = 0
    for user in get_user_model().objects.filter(is_active=True).order_by("id"):
        for bot, (_, every, _, _) in BOTS.items():
            last = _records(user).filter(payload__bot=bot, payload__trigger="schedule").order_by("-created_at").first()
            if last and last.payload.get("for_date", "") > (today - timedelta(days=every)).isoformat():
                continue
            try:
                run(user, bot, today, trigger="schedule")
                ran += 1
            except Exception as error:
                failed += 1
                logger.warning("Task bot %s failed for one account (%s)", bot, type(error).__name__)
    return {"status": "completed", "processed": ran, "failed": failed}
