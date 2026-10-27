"""Opted-in local reminders; schedule and visible delivery share the trip transaction."""
from copy import deepcopy
from datetime import datetime, timezone as utc_timezone
import hashlib
import json
import re
import sqlite3
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from diskcache import Timeout as CacheTimeout

from django.db import transaction
from django.core.cache import cache
from django.db.models import F, Q
from django.utils import timezone
from django.utils.timezone import now as current_time
from rest_framework.exceptions import APIException, ValidationError

from ...models import TravelPlan, TravelPlanningSession
from .editor import EditConflict

KEY = "_travel_reminders"
LIMIT = 20
DELIVERY_LIMIT = 100
CLOSED = {"completed", "cancelled"}
CURSOR = "alfred:travel:reminder-sweep-cursor"


class RemindersUnavailable(APIException):
    status_code = 503
    default_detail = "Local reminder data needs repair. No delivery was made; existing trip data is retained."


def _stamp(value):
    if timezone.is_naive(value):
        raise ValueError("An aware timestamp is required.")
    return value.astimezone(utc_timezone.utc).replace(microsecond=0).isoformat()


def _identity(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except (ValueError, TypeError, AttributeError):
        return False


def _title(value):
    if not isinstance(value, str) or any(ord(c) < 32 and not c.isspace() for c in value):
        raise ValidationError("Choose a reminder name.")
    value = " ".join(value.split())
    if not 1 <= len(value) <= 160:
        raise ValidationError("Reminder names need 1–160 characters.")
    return value


def schedule(zone, local_time, fold=None):
    if not isinstance(zone, str) or len(zone) > 64 or not isinstance(local_time, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", local_time):
        raise ValidationError("Choose an IANA timezone and a local date/time to the minute.")
    if fold is not None and (type(fold) is not int or fold not in (0, 1)):
        raise ValidationError("Choose the first or second occurrence of an ambiguous local time.")
    try:
        tz = ZoneInfo(zone)
        naive = datetime.strptime(local_time, "%Y-%m-%dT%H:%M")
        choices = {}
        for candidate in (0, 1):
            aware = naive.replace(tzinfo=tz, fold=candidate)
            instant = aware.astimezone(utc_timezone.utc)
            if instant.astimezone(tz).replace(tzinfo=None) == naive:
                choices.setdefault(_stamp(instant), candidate)
    except (ZoneInfoNotFoundError, ValueError, OverflowError):
        raise ValidationError("Choose a valid IANA timezone and local date/time.") from None
    if not choices:
        raise ValidationError("That local time does not exist because the clock changes. Choose another time.")
    if len(choices) > 1 and fold is None:
        raise ValidationError("That local time occurs twice. Choose its first or second occurrence.")
    selected = next((instant for instant, occurrence in choices.items() if occurrence == fold), next(iter(choices)))
    return selected, choices[selected]


def _next(policy):
    return min((row["due_at"] for row in policy["reminders"] if row["status"] == "scheduled"), default=None) if policy["enabled"] else None


def _load(plan):
    if KEY not in plan.planning_state:
        return dict(revision=0, enabled=False, consent_at=None, reminders=[], deliveries=[], requests=[], next_due_at=None)
    policy = deepcopy(plan.planning_state[KEY])
    try:
        if set(policy) != {"revision", "enabled", "consent_at", "reminders", "deliveries", "requests", "next_due_at"} or type(policy["revision"]) is not int or policy["revision"] < 0 or type(policy["enabled"]) is not bool:
            raise ValueError()
        for key, cap in (("reminders", LIMIT), ("deliveries", DELIVERY_LIMIT), ("requests", 20)):
            if not isinstance(policy[key], list) or len(policy[key]) > cap:
                raise ValueError()
        if policy["enabled"] and not policy["consent_at"]:
            raise ValueError()
        if policy["consent_at"] is not None and _stamp(datetime.fromisoformat(policy["consent_at"])) != policy["consent_at"]:
            raise ValueError()
        identities, occurrences = set(), set()
        by_occurrence = {}
        for row in policy["reminders"]:
            if set(row) != {"id", "occurrence_id", "label", "zone", "local_time", "fold", "due_at", "status"} or not _identity(row["id"]) or not _identity(row["occurrence_id"]) or row["id"] in identities or row["occurrence_id"] in occurrences:
                raise ValueError()
            if row["status"] not in ("scheduled", "cancelled", "delivered") or _title(row["label"]) != row["label"] or schedule(row["zone"], row["local_time"], row["fold"])[0] != row["due_at"]:
                raise ValueError()
            identities.add(row["id"]); occurrences.add(row["occurrence_id"])
            by_occurrence[row["occurrence_id"]] = row
        delivered = set()
        for row in policy["deliveries"]:
            if set(row) != {"occurrence_id", "reminder_id", "label", "due_at", "delivered_at", "late"} or not _identity(row["occurrence_id"]) or row["occurrence_id"] in delivered or row["reminder_id"] not in identities or _title(row["label"]) != row["label"] or type(row["late"]) is not bool:
                raise ValueError()
            due, at = datetime.fromisoformat(row["due_at"]), datetime.fromisoformat(row["delivered_at"])
            if due.tzinfo is None or at.tzinfo is None or at < due or _stamp(due) != row["due_at"] or _stamp(at) != row["delivered_at"] or row["late"] != (at > due):
                raise ValueError()
            delivered.add(row["occurrence_id"])
            current = by_occurrence.get(row["occurrence_id"])
            if current and (row["reminder_id"] != current["id"] or row["label"] != current["label"] or row["due_at"] != current["due_at"]):
                raise ValueError()
        for row in policy["reminders"]:
            if (row["occurrence_id"] in delivered) != (row["status"] == "delivered"):
                raise ValueError()
        requests = set()
        for receipt in policy["requests"]:
            if set(receipt) != {"id", "signature"} or not _identity(receipt["id"]) or receipt["id"] in requests or not re.fullmatch("[a-f0-9]{64}", receipt["signature"]):
                raise ValueError()
            requests.add(receipt["id"])
        if not policy["enabled"] and any(row["status"] == "scheduled" for row in policy["reminders"]):
            raise ValueError()
        if policy["next_due_at"] != _next(policy) or len(policy["deliveries"]) + sum(r["status"] == "scheduled" for r in policy["reminders"]) > DELIVERY_LIMIT:
            raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError, ValidationError):
        raise RemindersUnavailable() from None
    return policy


def reminder_payload(session):
    plan = TravelPlan.objects.filter(pk=session.plan_id, user=session.user).first()
    if not plan:
        return None
    policy = _load(plan)
    return {k: policy[k] for k in ("revision", "enabled", "reminders", "deliveries")} | {"limit": LIMIT, "delivery_limit": DELIVERY_LIMIT, "closed": plan.status in CLOSED}


def _locked_plan(identity, owner=None):
    if identity is None:
        return None
    TravelPlanningSession.objects.select_for_update().filter(plan_id=identity).first()
    plans = TravelPlan.objects.select_for_update()
    return plans.filter(pk=identity, **({"user": owner} if owner is not None else {})).first()


def _save(plan, policy):
    original = deepcopy(plan.planning_state)
    policy["revision"] += 1
    policy["next_due_at"] = _next(policy)
    plan.planning_state[KEY] = policy
    if not TravelPlan.objects.filter(pk=plan.pk, user_id=plan.user_id, planning_state=original).update(planning_state=plan.planning_state, updated_at=current_time()):
        raise EditConflict("The saved trip changed. Reload before changing reminders.")
    TravelPlanningSession.objects.filter(plan=plan, user_id=plan.user_id).update(revision=F("revision") + 1, updated_at=current_time())


def cancel_closed_trip(plan):
    if plan.status not in CLOSED or KEY not in plan.planning_state:
        return
    try:
        policy = _load(plan)
    except RemindersUnavailable:
        return  # Corrupt schedules remain retained and fail closed during delivery.
    if policy["enabled"] or any(row["status"] == "scheduled" for row in policy["reminders"]):
        policy["enabled"] = False
        for row in policy["reminders"]:
            if row["status"] == "scheduled":
                row["status"] = "cancelled"
        _save(plan, policy)


@transaction.atomic
def update_reminders(session, data):
    allowed = {"action", "operation", "request_id", "reminder_revision", "reminder_id", "enabled", "label", "zone", "local_time", "fold"}
    if not isinstance(data, dict) or set(data) - allowed or not _identity(data.get("request_id")):
        raise ValidationError("Choose a supported reminder change with a request identity.")
    plan = _locked_plan(session.plan_id, session.user)
    if not plan:
        raise ValidationError("Save this trip or a draft before scheduling reminders.")
    policy = _load(plan)
    signature = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    for receipt in policy["requests"]:
        if receipt["id"] == data["request_id"]:
            if receipt["signature"] != signature:
                raise EditConflict("That request identity was used for another reminder change.")
            return
    if type(data.get("reminder_revision")) is not int or data["reminder_revision"] != policy["revision"]:
        raise EditConflict("Reminders changed. Reload the trip; your draft is retained.")
    operation = data.get("operation")
    fields = set(data) - {"action", "operation", "request_id", "reminder_revision"}
    if operation == "consent" and fields == {"enabled"} and type(data["enabled"]) is bool:
        if data["enabled"] and plan.status in CLOSED:
            raise ValidationError("Completed or cancelled trips cannot enable reminders.")
        policy["enabled"] = data["enabled"]
        if policy["enabled"]:
            policy["consent_at"] = _stamp(current_time())
        else:
            for row in policy["reminders"]:
                if row["status"] == "scheduled":
                    row["status"] = "cancelled"
    elif isinstance(operation, str) and operation in ("create", "edit", "reschedule", "cancel"):
        if not _identity(data.get("reminder_id")):
            raise ValidationError("Choose a valid reminder identity.")
        existing = next((r for r in policy["reminders"] if r["id"] == data["reminder_id"]), None)
        if operation == "cancel":
            if fields != {"reminder_id"} or not existing:
                raise ValidationError("Choose an existing reminder to cancel.")
            if existing["status"] == "scheduled":
                existing["status"] = "cancelled"
        else:
            if fields - {"reminder_id", "label", "zone", "local_time", "fold"} or not policy["enabled"] or plan.status in CLOSED:
                raise ValidationError("Explicitly enable local reminders on an active trip first.")
            if operation == "create" and (existing or len(policy["reminders"]) >= LIMIT):
                raise ValidationError("Choose a new reminder identity; a trip supports at most20 reminders.")
            if operation != "create" and (not existing or operation == "edit" and existing["status"] != "scheduled"):
                raise EditConflict("Choose reschedule for a delivered or cancelled reminder.")
            label = _title(data.get("label"))
            due, fold = schedule(data.get("zone"), data.get("local_time"), data.get("fold"))
            if due <= _stamp(current_time()):
                raise ValidationError("Choose a future reminder time. Offline overdue reminders will still be delivered late.")
            scheduled = sum(r["status"] == "scheduled" and r is not existing for r in policy["reminders"])
            if len(policy["deliveries"]) + scheduled >= DELIVERY_LIMIT:
                raise ValidationError("This trip has reached its100-occurrence reminder history limit; existing records are retained.")
            row = dict(id=data["reminder_id"], occurrence_id=str(uuid4()), label=label, zone=data["zone"], local_time=data["local_time"], fold=fold, due_at=due, status="scheduled")
            if existing:
                existing.update(row)
            else:
                policy["reminders"].append(row)
    else:
        raise ValidationError("Choose consent, create, edit, cancel or reschedule.")
    policy["requests"] = [*policy["requests"][-19:], {"id": data["request_id"], "signature": signature}]
    _save(plan, policy)


@transaction.atomic
def deliver_due(identity, now=None):
    plan = _locked_plan(identity)
    if not plan:
        return 0
    policy = _load(plan)
    if plan.status in CLOSED:
        cancel_closed_trip(plan)
        return 0
    if not policy["enabled"]:
        return 0
    at = _stamp(now or current_time())
    delivered = 0
    for row in policy["reminders"]:
        if row["status"] == "scheduled" and row["due_at"] <= at:
            policy["deliveries"].append(dict(occurrence_id=row["occurrence_id"], reminder_id=row["id"], label=row["label"], due_at=row["due_at"], delivered_at=at, late=at > row["due_at"]))
            row["status"] = "delivered"
            delivered += 1
    if delivered:
        _save(plan, policy)
    return delivered


def sweep_due():
    now = current_time()
    candidates = TravelPlan.objects.filter(**{f"planning_state__{KEY}__enabled": True}).filter(
        Q(**{f"planning_state__{KEY}__next_due_at__lte": _stamp(now)}) | Q(status__in=CLOSED))
    counts = dict(processed=0, refreshed=0, failed=0)
    try:
        cursor = cache.get(CURSOR, 0)
    except (OSError, sqlite3.Error, CacheTimeout):
        cursor = 0
    if type(cursor) is not int or cursor < 0:
        cursor = 0
    identities = list(candidates.filter(pk__gt=cursor).order_by("pk").values_list("pk", flat=True)[:100])
    if not identities and cursor:
        identities = list(candidates.order_by("pk").values_list("pk", flat=True)[:100])
    for identity in identities:
        try:
            counts["refreshed"] += deliver_due(identity)
        except (RemindersUnavailable, EditConflict):
            counts["failed"] += 1
        counts["processed"] += 1
    # Only pagination uses cache; a reset safely replays durable, idempotent trip state.
    try:
        cache.set(CURSOR, identities[-1] if identities else 0, timeout=None)
    except (OSError, sqlite3.Error, CacheTimeout):
        pass
    return counts
