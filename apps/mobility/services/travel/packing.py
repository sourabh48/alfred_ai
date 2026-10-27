"""Private packing progress belongs to the saved trip, independently of itinerary edits."""
from copy import deepcopy
from uuid import NAMESPACE_URL, UUID, uuid5

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from ...models import TravelPlan
from ..travel_itinerary import packing_suggestions
from .editor import EditConflict

KEY = "_packing_checklist"
LIMIT = 50


def planning_state_with_checklist(state, plan):
    result = deepcopy(state)
    result.pop(KEY, None)
    if KEY in plan.planning_state:
        result[KEY] = deepcopy(plan.planning_state[KEY])
    return result


def _label(text):
    if not isinstance(text, str) or any(ord(c) < 32 and not c.isspace() for c in text):
        raise ValidationError("Choose a packing item name.")
    text = " ".join(text.split())
    if not 1 <= len(text) <= 160:
        raise ValidationError("Packing item names need 1–160 characters.")
    return text


def _checklist(plan):
    if KEY in plan.planning_state:
        return deepcopy(plan.planning_state[KEY])
    items, names = [], set()
    for label in plan.itinerary.get("packing", []) or packing_suggestions(plan.transport_mode):
        label = _label(label)
        if label.casefold() not in names:
            items.append({"id": str(uuid5(NAMESPACE_URL, f"alfred:packing:{plan.pk}:{label.casefold()}")),
                          "label": label, "packed": False})
            names.add(label.casefold())
        if len(items) == LIMIT:
            break
    return {"revision": 0, "items": items}


def packing_payload(session):
    plan = TravelPlan.objects.filter(pk=session.plan_id, user=session.user).first()
    return {**_checklist(plan), "limit": LIMIT} if plan else None


@transaction.atomic
def update_packing(session, data):
    if not isinstance(data, dict) or set(data) - {"action", "operation", "item_id", "checklist_revision", "label", "packed"}:
        raise ValidationError("Choose a supported packing change without extra fields.")
    session = type(session).objects.select_for_update().get(pk=session.pk, user=session.user)
    plan = TravelPlan.objects.select_for_update().filter(pk=session.plan_id, user=session.user).first()
    if not plan:
        raise ValidationError("Save this trip or a draft before keeping a packing checklist.")
    operation = data.get("operation")
    if not isinstance(operation, str) or operation not in {"add", "update", "remove"} or type(data.get("checklist_revision")) is not int or data["checklist_revision"] < 0:
        raise ValidationError("Choose a packing change and its checklist revision.")
    identity = data.get("item_id")
    try:
        if not isinstance(identity, str) or str(UUID(identity)) != identity:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("A valid packing item identity is required.")
    fields = {k: data[k] for k in ("label", "packed") if k in data}
    if (operation == "remove" and fields) or (operation == "add" and "label" not in fields) or (operation == "update" and not fields):
        raise ValidationError("Choose the fields for this packing change.")
    if "label" in fields:
        fields["label"] = _label(fields["label"])
    if "packed" in fields and type(fields["packed"]) is not bool:
        raise ValidationError("Packed must be true or false.")
    checklist = _checklist(plan)
    items = checklist["items"]
    existing = next((row for row in items if row["id"] == identity), None)
    if operation == "remove" and not existing:
        return
    if operation == "add":
        proposed = {"id": identity, "label": fields["label"], "packed": fields.get("packed", False)}
        if existing == proposed:
            return
        if existing:
            raise EditConflict("That packing identity already exists. Reload the checklist.")
    elif operation == "update":
        if not existing:
            raise EditConflict("That packing item was removed. Reload the checklist.")
        proposed = {**existing, **fields}
        if existing == proposed:
            return
    if data["checklist_revision"] != checklist["revision"]:
        raise EditConflict("This packing checklist changed. Reload the trip; your draft is retained.")
    if operation != "remove":
        if any(row["id"] != identity and row["label"].casefold() == proposed["label"].casefold() for row in items):
            raise ValidationError("That packing item is already listed. Edit the existing item.")
        if operation == "add" and len(items) >= LIMIT:
            raise ValidationError(f"A trip supports at most {LIMIT} packing items.")
    checklist["items"] = [row for row in items if row["id"] != identity]
    if operation == "update":
        checklist["items"] = [proposed if row["id"] == identity else row for row in items]
    elif operation == "add":
        checklist["items"].append(proposed)
    checklist["revision"] += 1
    original = deepcopy(plan.planning_state)
    plan.planning_state[KEY] = checklist
    if not TravelPlan.objects.filter(pk=plan.pk, user=session.user, planning_state=original).update(
            planning_state=plan.planning_state, updated_at=timezone.now()):
        raise EditConflict("The saved trip changed. Reload before changing its checklist.")
    type(session).objects.filter(pk=session.pk, user=session.user).update(revision=F("revision") + 1, updated_at=timezone.now())
    session.refresh_from_db()
