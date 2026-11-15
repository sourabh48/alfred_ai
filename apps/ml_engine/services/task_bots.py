"""In-app task bots (owner request 2026-11-14: "i need bots to do tasks"); AI-17 propose-then-confirm, WEALTH2-002 stale check.

Each bot reads the owner's own records, deterministically and without a model, and writes one reviewable proposal.
Nothing changes until the owner confirms in the app. The only actions a confirmation can run are travel reminders,
a travel recheck and filing a spend under a category; every money, booking, trading or sending step stays with the owner.
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


def categorise(user, today):
    """Spends in Other whose merchant the owner has already categorised the same way at least twice (75% of the time)."""
    from apps.expenses.models import Expense
    rows = Expense.objects.filter(user=user, direction="debit")
    history = defaultdict(lambda: defaultdict(int))
    for merchant, category in rows.exclude(category="other").exclude(merchant="").values_list("merchant", "category"):
        history[merchant.strip().lower()][category] += 1
    labels, items = dict(Expense.CATEGORY_CHOICES), []
    for expense in rows.filter(category="other", transaction_date__gte=today - timedelta(days=60)).exclude(merchant="").order_by("-transaction_date", "-id")[:200]:
        counts = history.get(expense.merchant.strip().lower())
        if not counts:
            continue
        category, seen = max(sorted(counts.items()), key=lambda pair: pair[1])
        if seen >= 2 and seen * 4 >= sum(counts.values()) * 3:
            label = labels.get(category, category)
            items.append(_item(f"category:{expense.pk}:{category}", f"{expense.merchant} {_amount(expense.amount, expense.currency)} on {expense.transaction_date:%d %b} to {label}",
                f"You filed {seen} earlier {expense.merchant} spend(s) under {label}.", "/expenses/",
                {"type": "categorise", "expense_id": expense.pk, "category": category, "label": label}))
    return items


def budget_pace(user, today):
    from apps.budgets.services.budget_intelligence import budget_spent, current_budget_plan
    plan = current_budget_plan(user, today=today)
    if plan is None or not plan.inflation_adjusted or plan.inflation_adjusted <= 0:
        return []
    spent = budget_spent(plan, today=today) or Decimal("0")
    days = calendar.monthrange(today.year, today.month)[1]
    used, elapsed = spent / plan.inflation_adjusted, Decimal(today.day) / days
    if used < Decimal("0.9") and used <= elapsed + Decimal("0.1"):
        return []
    left, days_left = plan.inflation_adjusted - spent, days - today.day + 1
    per_day = (max(left, Decimal("0")) / days_left).quantize(Decimal("0.01"))
    currency = plan.currency or "INR"  # a plan without a recorded currency counts as legacy INR (FIN-15)
    return [_item(f"budget:{plan.pk}:{today.isoformat()}", f"Budget: {_amount(spent, currency)} of {_amount(plan.inflation_adjusted, currency)} spent ({used * 100:.0f}%)",
        f"{today.day} of {days} days have gone ({elapsed * 100:.0f}%). "
        + (f"About {_amount(per_day, currency)} a day keeps you inside it." if left > 0 else f"You are {_amount(-left, currency)} over."), "/budgets/")]


def goal_check(user, today):
    from apps.budgets.models import SavingsGoal
    from apps.budgets.money import goal_progress
    items = []
    for goal in SavingsGoal.objects.filter(user=user).order_by("target_date", "id"):
        progress = goal_progress(goal.target_amount, goal.saved_amount, goal.target_date, today)
        if progress["status"] == "overdue":
            items.append(_item(f"goal:{goal.pk}:overdue", f"{goal.name}: target date {goal.target_date:%d %b %Y} has passed",
                f"{_amount(progress['remaining'], goal.currency)} still to save ({progress['percent']}% done). Set a new date or record what you saved.", "/budgets/"))
        elif progress["status"] == "open" and progress["months_left"] and progress["months_left"] <= 3:
            items.append(_item(f"goal:{goal.pk}:{progress['remaining']}", f"{goal.name}: {_amount(progress['monthly_needed'], goal.currency)} a month to finish",
                f"{_amount(progress['remaining'], goal.currency)} left with {progress['months_left']} month(s) to go.", "/budgets/"))
    return items


def subscriptions(user, today):
    """The same merchant charged in three or more different months of the last 120 days, at a steady amount."""
    from apps.expenses.models import Expense
    charges = defaultdict(list)
    for row in (Expense.objects.filter(user=user, direction="debit", transaction_date__gte=today - timedelta(days=120))
                .exclude(merchant="").exclude(classification__in=("transfer", "investment")).order_by("transaction_date", "id")
                .values("merchant", "currency", "amount", "transaction_date")):
        charges[(row["merchant"].strip().lower(), row["currency"])].append(row)
    items = []
    for (name, currency), rows in sorted(charges.items(), key=lambda pair: (pair[0][0], pair[0][1] or "")):
        months = {(row["transaction_date"].year, row["transaction_date"].month) for row in rows}
        amounts = [row["amount"] for row in rows]
        if len(months) >= 3 and max(amounts) <= min(amounts) * Decimal("1.1"):
            last = rows[-1]
            items.append(_item(f"subscription:{name}:{currency or 'none'}", f"{last['merchant']}: about {_amount(last['amount'], currency)} every month",
                f"Charged in {len(months)} different months since {today - timedelta(days=120):%d %b}, last on {last['transaction_date']:%d %b}. "
                "Still using it? Cancel with the provider if not; ALFRED never cancels for you.", "/expenses/"))
    return items


def duplicates(user, today):
    """Two or more entries with the same account, day, amount, direction and merchant in the last 60 days."""
    from django.db.models import Count
    from apps.expenses.models import Expense
    groups = (Expense.objects.filter(user=user, transaction_date__gte=today - timedelta(days=60)).exclude(merchant="")
              .values("bank_account", "transaction_date", "amount", "direction", "merchant", "currency")
              .annotate(rows=Count("id"), references=Count("external_reference", distinct=True)).filter(rows__gt=1)
              .order_by("-transaction_date", "merchant"))
    # As many distinct bank references as entries means separate payments; an empty reference counts as one value.
    return [_item(f"duplicate:{g['bank_account']}:{g['transaction_date'].isoformat()}:{g['amount']}:{g['merchant'].strip().lower()}",
                  f"{g['rows']} x {_amount(g['amount'], g['currency'])} at {g['merchant']} on {g['transaction_date']:%d %b}",
                  "Same account, day, amount and merchant. If it was charged once, delete the extra entry on Expenses.", "/expenses/")
            for g in groups if g["references"] < g["rows"]]


def statements_due(user, today):
    from apps.expenses.models import BankAccount, Expense
    items = []
    for account in BankAccount.objects.filter(user=user, is_active=True).order_by("id"):
        last = (Expense.objects.filter(user=user, bank_account=account, statement_upload__isnull=False)
                .order_by("-transaction_date").values_list("transaction_date", flat=True).first())
        if last and last < today - timedelta(days=35):
            items.append(_item(f"statement:{account.pk}:{last.isoformat()}", f"Upload a new statement for {account.display_name}",
                f"The latest imported entry is from {last:%d %b %Y}; balances and reviews after that are estimates.", "/expenses/"))
    return items


BOTS = {
    "money_review": ("Weekly money review", 7, money_review, "Last 7 days of spending against the week before."),
    "bills_due": ("Bills and EMIs due", 1, bills_due, "Loan instalments due in the next 7 days."),
    "fund_review": ("Fund review", 1, fund_review, "Owned funds that dropped from their recent high (AMFI prices)."),
    "paperwork": ("Documents and service", 1, paperwork, "Vehicle papers expiring and bike service due."),
    "career_follow_ups": ("Career follow-ups", 1, career_follow_ups, "Applications where a follow-up is due."),
    "travel_prep": ("Travel preparation", 1, travel_prep, "Next steps for trips in the coming weeks."),
    "categorise": ("Auto-categorise", 1, categorise, "Files Other spends under the category you always use for that merchant."),
    "budget_pace": ("Budget pace", 1, budget_pace, "Warns when this month's spending runs ahead of your budget."),
    "goal_check": ("Savings goals", 7, goal_check, "Goals past their date or due within three months."),
    "subscriptions": ("Subscriptions", 7, subscriptions, "Steady monthly charges you may have forgotten."),
    "duplicates": ("Possible duplicates", 1, duplicates, "Entries that look recorded twice."),
    "statements_due": ("Statements due", 7, statements_due, "Accounts without a statement for over 35 days."),
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
    if trigger == "schedule" and _records(user).filter(payload__bot=bot, payload__fingerprint=fingerprint).exclude(event_type=PENDING).exists():
        return None  # the owner already confirmed or dismissed this exact list; it returns only when something changes
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


def _categorise(user, action):
    from types import SimpleNamespace
    from apps.expenses.models import Expense
    from apps.expenses.serializers import ExpenseSerializer
    expense = Expense.objects.select_for_update().filter(user=user, pk=action["expense_id"], category="other").first()
    if expense is None:
        raise ActionConflict("That spend was changed or removed. Run the bot again.")
    # The same validated path as editing the spend on Expenses; only the category changes.
    serializer = ExpenseSerializer(expense, data={"category": action["category"]}, partial=True, context={"request": SimpleNamespace(user=user)})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return f"{expense.merchant} filed under {action['label']}."


def _apply(user, action):
    if action["type"] == "categorise":
        return _categorise(user, action)
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


# Daily bots that read only this PC's records refresh every hour, so a new spend or statement shows up the same
# day; an unchanged review keeps its fingerprint and is reused, never duplicated. The fund bot reads AMFI online,
# so it stays once a day, and the weekly bots stay weekly.
NETWORK_BOTS = {"fund_review"}


def run_scheduled(today=None):
    """Hourly Huey job: refresh every bot that is due for each active account; one failure never stops the rest."""
    today = today or timezone.localdate()
    ran = failed = 0
    for user in get_user_model().objects.filter(is_active=True).order_by("id"):
        for bot, (_, every, _, _) in BOTS.items():
            last = _records(user).filter(payload__bot=bot, payload__trigger="schedule").order_by("-created_at").first()
            hourly = every == 1 and bot not in NETWORK_BOTS
            if not hourly and last and last.payload.get("for_date", "") > (today - timedelta(days=every)).isoformat():
                continue
            try:
                run(user, bot, today, trigger="schedule")
                ran += 1
            except Exception as error:
                failed += 1
                logger.warning("Task bot %s failed for one account (%s)", bot, type(error).__name__)
    return {"status": "completed", "processed": ran, "failed": failed}
