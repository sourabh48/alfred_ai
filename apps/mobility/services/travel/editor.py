"""Owned manual itinerary edits; history and request receipts stay in session JSON."""
from copy import deepcopy
import hashlib
import json
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from ..travel_discovery import fact, value
from .presentation import invalidate_trip_dates


class EditConflict(APIException):
    status_code = 409
    default_detail = "This trip changed. Reload it before applying this edit; your draft has been retained."


def _json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _prepared(session):
    itinerary = deepcopy(session.itinerary)
    stops = deepcopy(value(session.state, "_itinerary_stops", []))
    def identity(label):
        return str(uuid5(NAMESPACE_URL, f"alfred-trip:{session.pk}:{label}"))
    for stop in stops:
        stop.setdefault("editor_id", identity("stop:" + stop["name"]))
    day_stops = []
    for stop in stops:
        nights = next((r.get("nights", 0) for r in itinerary.get("stops", []) if r["name"] == stop["name"]), 0)
        if type(nights) is not int or not 0 <= nights <= 30:
            raise ValidationError("The saved stop/night allocation needs review before editing.")
        day_stops.extend([stop["editor_id"]]*nights)
    identifiers = []
    for day in itinerary.get("days", []):
        identifiers.extend(row["id"] for row in [day, *day.get("items", [])] if "id" in row)
    if any(not isinstance(key, str) or not 1 <= len(key) <= 80 for key in identifiers) or len(set(identifiers)) != len(identifiers):
        raise ValidationError("The saved itinerary has invalid or duplicate edit identities; the original was retained.")
    identifiers = set(identifiers)
    def assign(row, label):
        if "id" not in row:
            candidate, suffix = identity(label), 0
            while candidate in identifiers:
                suffix += 1
                candidate = identity(f"{label}:{suffix}")
            row["id"] = candidate
            identifiers.add(candidate)
    for index, day in enumerate(itinerary.get("days", [])):
        assign(day, f"day:{index}")
        if index < len(day_stops):
            day.setdefault("stop_id", day_stops[index])
        for position, item in enumerate(day.get("items", [])):
            assign(item, f"item:{day['id']}:{position}:{item.get('title', '')}")
    return itinerary, stops


def _fingerprint(session, itinerary, stops):
    context = {k: v.get("value") if isinstance(v, dict) and "value" in v else v
               for k, v in session.state.items() if k not in {"_itinerary_editor", "_itinerary_documents"}}
    return hashlib.sha256(_json([itinerary, stops, context]).encode()).hexdigest()


def editor_payload(session):
    itinerary, stops = _prepared(session)
    history = value(session.state, "_itinerary_editor", {})
    current = history.get("head") == _fingerprint(session, itinerary, stops)
    return itinerary, {"stops": [{"id": s["editor_id"], "name": s["name"]} for s in stops],
        "can_undo": bool(current and history.get("undo")), "history": history.get("log", []),
        "history_limit": 10, "activity_limit": 30}


def _invalidate(itinerary):
    itinerary["budget"].update(status="needs_recalculation", verified_prices=[],
        recheck_note="Manual itinerary edits changed the plan. Displayed allowances are previous estimates; recalculate costs before relying on them.")
    itinerary["route"].update(status="needs_recalculation", confidence="UNKNOWN", legs=[], options=[],
        distance_km_total=None, distance_km_one_way=None, hours_one_way=None, selected_route_id=None,
        note="The itinerary was manually edited. Route distance, time, access and cost estimates need a new check; no road route is verified by this edit.")
    if itinerary.get("route_result"):
        itinerary["route_result"].update(stale=True, status="needs_refresh", confidence="UNKNOWN", freshness="UNKNOWN")
    for source in itinerary.get("sources", []):
        if source.get("data_type") in {"route", "budget", "cost"}:
            source.update(status="needs_refresh", confidence="UNKNOWN", freshness="UNKNOWN")
    itinerary["map"] = {}
    itinerary["selected_price_snapshots"] = []
    itinerary.setdefault("edits", []).append({"request": "Desktop itinerary edit", "source": "user"})
    itinerary["edits"] = itinerary["edits"][-50:]


def apply_edit(session, data):
    if not isinstance(data, dict) or set(data) - {"action", "revision", "request_id", "operation", "day_id", "item_id", "before_id", "fields", "stops"}:
        raise ValidationError("Choose a supported itinerary edit.")
    try:
        request_id = str(UUID(data.get("request_id", "")))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError("A valid edit request identity is required.")
    signature = hashlib.sha256(_json(data).encode()).hexdigest()
    history = deepcopy(value(session.state, "_itinerary_editor", {}))
    for receipt in history.get("requests", []):
        if receipt["id"] == request_id:
            if receipt["signature"] != signature:
                raise EditConflict("That request identity was already used for a different edit.")
            return
    if type(data.get("revision")) is not int or data["revision"] != session.revision:
        raise EditConflict()
    operation = data.get("operation")
    if operation not in {"add", "update", "remove", "move", "order_stops", "undo"}:
        raise ValidationError("Choose add, update, remove, move, order_stops or undo.")
    itinerary, stops = _prepared(session)
    if not itinerary.get("days"):
        raise ValidationError("Build an itinerary before editing activities.")
    if history.get("head") != _fingerprint(session, itinerary, stops):
        history["undo"] = []
    before = {"itinerary": deepcopy(itinerary), "stops": deepcopy(stops),
              "selected": deepcopy(session.state.get("selected_destination"))}
    if operation == "undo":
        if not history.get("undo"):
            raise EditConflict("No undo is available for the current trip context.")
        snapshot = history["undo"].pop()
        itinerary, stops = snapshot["itinerary"], snapshot["stops"]
        if snapshot["selected"] is None:
            session.state.pop("selected_destination", None)
        else:
            session.state["selected_destination"] = snapshot["selected"]
    elif operation == "order_stops":
        order = data.get("stops")
        by_id = {s["editor_id"]: s for s in stops}
        if not isinstance(order, list) or len(order) < 2 or any(not isinstance(key, str) for key in order) or len(order) != len(by_id) or set(order) != set(by_id):
            raise ValidationError("Reorder the existing stops exactly once; adding/removing stops uses the existing planner.")
        if order == list(by_id):
            raise ValidationError("The stop order has not changed.")
        groups = {key: [d for d in itinerary["days"] if d.get("stop_id") == key] for key in order}
        if any(not days for days in groups.values()):
            raise ValidationError("This itinerary has no stable stop/day allocation. Rebuild its manual stops before reordering.")
        itinerary["days"] = [d for key in order for d in groups[key]] + [d for d in itinerary["days"] if not d.get("stop_id")]
        stops = [by_id[key] for key in order]
        details = {s["name"]: s for s in itinerary["stops"]}
        itinerary["stops"] = [details[s["name"]] for s in stops]
        for stop in itinerary["stops"]:
            stop["date_context_changed"] = True
            for source in stop.get("sources", []):
                source.update(freshness="UNKNOWN", confidence="UNKNOWN", status="needs_refresh")
        itinerary["destination"] = " → ".join(s["name"] for s in stops)
        itinerary["route"]["summary"] = " → ".join([itinerary["origin"], *[s["name"] for s in stops], itinerary["origin"]])
        itinerary["summary"] = "Manually ordered stops; your activities and stay allocations were retained. Recheck the revised journey."
        session.state["selected_destination"] = fact(stops[0]["name"])
        dates = [d.get("date") for d in before["itinerary"]["days"]]
        for index, day in enumerate(itinerary["days"]):
            day.update(day=index+1, date=dates[index])
            for item in day["items"]:
                if item.get("type") == "travel":
                    item.update(title="Travel leg — route needs checking", duration="Recheck the revised stop order and travel time")
        itinerary = invalidate_trip_dates(itinerary)
    else:
        days = {d["id"]: d for d in itinerary["days"]}
        if not isinstance(data.get("day_id"), str) or data["day_id"] not in days:
            raise ValidationError("Choose an existing itinerary day.")
        day = days[data["day_id"]]
        fields = data.get("fields", {})
        if not isinstance(fields, dict) or set(fields) - {"title", "period", "duration", "priority"}:
            raise ValidationError("Only activity title, period, duration and priority can be edited.")
        limits = {"title": 240, "period": 120, "duration": 200, "priority": 20}
        if any(not isinstance(v, str) or not v.strip() or len(v.strip()) > limits[k] for k, v in fields.items()):
            raise ValidationError("Keep activity fields nonempty and within their length limits.")
        fields = {k: v.strip() for k, v in fields.items()}
        if "priority" in fields and fields["priority"] not in {"Must Do", "Recommended", "Optional", "Backup"}:
            raise ValidationError("Choose a supported activity priority.")
        if operation == "add":
            if not fields.get("title") or len(day["items"]) >= 30:
                raise ValidationError("Provide a title; each day supports at most30 activity blocks.")
            day["items"].append({"id": str(uuid4()), "type": "activity", "title": fields["title"],
                "period": "Flexible", "duration": "Confirm timing and access", "priority": "Optional", "cost": 0,
                "cost_note": "User-planned activity; price and access are unverified", **fields})
        else:
            location = next(((d, i) for d in itinerary["days"] for i in d["items"] if i["id"] == data.get("item_id")), None)
            if not location:
                raise ValidationError("Choose an activity belonging to this itinerary.")
            source, item = location
            if item.get("type") == "travel":
                raise ValidationError("Generated travel legs follow stop order. Reorder stops to change the journey.")
            if operation == "move":
                before_id = data.get("before_id")
                if before_id is not None and not any(i["id"] == before_id for i in day["items"]):
                    raise ValidationError("Choose an insertion point in the destination day.")
                if item.get("id") == before_id:
                    raise ValidationError("Choose a different insertion point.")
                if source is not day and len(day["items"]) >= 30:
                    raise ValidationError("That day already has30 activity blocks.")
                source["items"].remove(item)
                position = next((n for n, row in enumerate(day["items"]) if row["id"] == before_id), len(day["items"]))
                day["items"].insert(position, item)
            elif source is not day:
                raise ValidationError("The selected activity belongs to a different day.")
            elif operation == "update":
                if not fields:
                    raise ValidationError("Choose at least one activity field to change.")
                item.update(fields)
            elif operation == "remove":
                day["items"].remove(item)
    if operation != "undo":
        _invalidate(itinerary)
        history.setdefault("undo", []).append(before)
        history["undo"] = history["undo"][-10:]
        while len(_json(history["undo"]).encode()) > 512*1024 and len(history["undo"]) > 1:
            history["undo"].pop(0)
        if len(_json(history["undo"]).encode()) > 512*1024:
            raise ValidationError("This itinerary exceeds the bounded undo storage limit; the original was retained.")
    session.state["_itinerary_stops"] = fact(stops)
    history["head"] = _fingerprint(session, itinerary, stops)
    history["log"] = (history.get("log", []) + [{"revision": session.revision+1, "operation": operation,
        "at": timezone.now().isoformat()}])[-20:]
    history["requests"] = (history.get("requests", []) + [{"id": request_id, "signature": signature}])[-20:]
    session.state["_itinerary_editor"] = fact(history, "desktop_editor")
    updated = type(session).objects.filter(pk=session.pk, user=session.user, revision=session.revision).update(
        state=session.state, itinerary=itinerary, revision=session.revision+1, updated_at=timezone.now())
    if not updated:
        raise EditConflict()
    session.refresh_from_db()
