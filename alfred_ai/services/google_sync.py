"""Phone sync through Google Calendar and Google Tasks (owner decision 2026-11-18: "Calendar + Tasks").

One way, ALFRED to Google: trips, bookings, career follow-ups and research review dates become events in a separate
"ALFRED" calendar that ALFRED creates (the calendar.app.created permission cannot see any other calendar), and trip
reminders and saved packing lists become tasks in an "ALFRED" task list. Amounts, balances and notes never leave this
PC. The refresh token is kept encrypted under ALFRED's data folder, and Disconnect revokes it at Google.

The same consent also asks to read public calendars (read-only), so a country Nager.Date does not cover, such as
India, gets its public holidays from Google's holiday calendar (owner decision 2026-11-19). Only the country leaves.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from alfred_ai.services import public_http
from alfred_ai.services.public_http import PublicHTTPError

REQUIRED = "https://www.googleapis.com/auth/calendar.app.created https://www.googleapis.com/auth/tasks"
HOLIDAY_SCOPE = "https://www.googleapis.com/auth/calendar.events.public.readonly"
SCOPES = f"{REQUIRED} {HOLIDAY_SCOPE}"
CALENDAR, TASKS = "https://www.googleapis.com/calendar/v3", "https://tasks.googleapis.com/tasks/v1"
TOKEN_URL, REVOKE_URL = "https://oauth2.googleapis.com/token", "https://oauth2.googleapis.com/revoke"
NAME, LIMIT, PAST_DAYS, AHEAD_DAYS = "ALFRED", 400, 30, 400
OK = (200, 201, 204, 404, 410)


class SyncError(Exception):
    """A message safe to show the owner."""


def _folder() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "artifacts" / "google-sync"


def _path(user) -> Path:
    return _folder() / f"user-{user.pk}.json"


def _load(user) -> dict | None:
    try:
        return json.loads(_path(user).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _store(user, data: dict) -> None:
    path = _path(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data), encoding="utf-8")
    os.replace(temporary, path)


def status(user) -> dict:
    from alfred_ai.services import social_login

    data = _load(user) or {}
    return {"available": "google" in {p["id"] for p in social_login.configured()}, "connected": bool(data.get("refresh")),
            "account": data.get("email", ""), "last_sync": data.get("last_sync"), "last_error": data.get("last_error", ""),
            "events": len(data.get("events", {})), "tasks": len(data.get("tasks", {})), "holidays": bool(data.get("holidays"))}


def connect(user, identity: dict, refresh_token: str | None, scope: str) -> None:
    from apps.integrations.models import _encrypt_token

    granted = set((scope or "").split())
    if not refresh_token:
        raise SyncError("Google did not give ALFRED lasting access. Remove ALFRED at myaccount.google.com/permissions and connect again.")
    if not set(REQUIRED.split()) <= granted:
        raise SyncError("Tick both Google Calendar and Google Tasks on Google's screen so ALFRED can sync them.")
    old = _load(user) or {}
    _store(user, {**old, "email": identity["email"], "refresh": _encrypt_token(refresh_token), "last_error": "",
                  "holidays": HOLIDAY_SCOPE in granted})


# shortcut: Google's older holiday calendar names are known here only for India; other countries use the two-letter name.
HOLIDAY_CALENDARS = {"IN": ("in", "indian")}


def public_holidays(user, country: str, year: int) -> dict:
    """Public holidays from Google's holiday calendar for a country, read with the owner's connected Google account."""
    from urllib.parse import quote, urlencode

    data = _load(user) or {}
    if not data.get("refresh") or not data.get("holidays"):
        raise SyncError("Connect Google under Settings > Phone calendar and tasks to read this country's public holidays from Google.")
    token = _access(data)
    window = urlencode({"timeMin": f"{year}-01-01T00:00:00Z", "timeMax": f"{year + 1}-01-01T00:00:00Z",
                        "singleEvents": "true", "orderBy": "startTime", "maxResults": 250})
    for name in HOLIDAY_CALENDARS.get(country, (country.lower(),)):
        calendar = quote(f"en.{name}#holiday@group.v.calendar.google.com", safe="")
        status_code, body = _call(token, "GET", f"{CALENDAR}/calendars/{calendar}/events?{window}")
        if status_code == 200:
            break
    else:
        raise SyncError(f"Google has no public holiday calendar for {country}.")
    holidays = []
    for event in body.get("items") or []:
        day = str((event.get("start") or {}).get("date") or "")
        if len(day) == 10 and day.startswith(str(year)):
            kind = str(event.get("description") or "").strip()[:60]
            holidays.append({"date": day, "name": str(event.get("summary") or "")[:120], "english": "",
                             "national": kind.lower().startswith("public holiday"), "kind": kind, "regions": []})
    if not holidays:
        raise SyncError(f"Google lists no public holidays for {country} in {year}.")
    return {"holidays": holidays, "long_weekends": long_weekends(h["date"] for h in holidays if h["national"])}


def long_weekends(days) -> list:
    """A public holiday next to a weekend: Monday or Friday gives three days off, Tuesday or Thursday four with one leave day."""
    found = []
    for day in sorted({date.fromisoformat(d) for d in days}):
        weekday = day.weekday()
        if weekday in (0, 1):  # Saturday before to the holiday
            start, leave = day - timedelta(days=weekday + 2), [day - timedelta(days=1)] if weekday == 1 else []
            end = day
        elif weekday in (3, 4):  # holiday to the Sunday after
            start, end, leave = day, day + timedelta(days=6 - weekday), [day + timedelta(days=1)] if weekday == 3 else []
        else:
            continue
        found.append({"start": start.isoformat(), "end": end.isoformat(), "days": (end - start).days + 1,
                      "leave_days": [d.isoformat() for d in leave]})
    return found


def _access(data: dict) -> str:
    from alfred_ai.services.social_login import _client
    from apps.integrations.models import _decrypt_token

    client_id, secret = _client("google")
    try:
        token = public_http.request("POST", TOKEN_URL, headers={"Accept": "application/json"}, data={
            "grant_type": "refresh_token", "refresh_token": _decrypt_token(data["refresh"]),
            "client_id": client_id, "client_secret": secret}).json()
    except PublicHTTPError as exc:
        raise SyncError("Google refused ALFRED's access; connect again in Settings." if exc.code in ("authorization_failed", "api_error")
                        else "Could not reach Google. ALFRED will try again later.") from None
    if not token.get("access_token"):
        raise SyncError("Google refused ALFRED's access; connect again in Settings.")
    return token["access_token"]


def _call(token, method, url, body=None):
    response = public_http.request(method, url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                                   json_body=body, accepted_statuses=OK)
    return response.status, (response.json() if response.status not in (204, 404, 410) else {})


# ---- what goes to the phone ----------------------------------------------------------------------------------------

def _digest(item) -> str:
    return hashlib.sha256(json.dumps(item, sort_keys=True).encode()).hexdigest()[:20]


def _all_day(start: date, end: date | None = None) -> dict:
    return {"start": {"date": start.isoformat()}, "end": {"date": ((end or start) + timedelta(days=1)).isoformat()}}


def events(user, today: date) -> dict:
    from apps.career.models import CareerJobAnalysis
    from apps.career.services.application_tracker import follow_up_status
    from apps.investments.models import ResearchDecision
    from apps.mobility.models import TravelPlan
    from apps.mobility.services.travel import trip_tools

    low, high, zone = today - timedelta(days=PAST_DAYS), today + timedelta(days=AHEAD_DAYS), str(settings.TIME_ZONE)
    found = {}
    plans = TravelPlan.objects.filter(user=user, start_date__isnull=False, end_date__gte=low, start_date__lte=high) \
        .exclude(status__in=("draft", "researching", "suggestions_ready", "cancelled"))
    for plan in plans:
        found[f"trip-{plan.pk}"] = {"summary": f"Trip: {plan.title}", "location": plan.destination or "",
                                    **_all_day(plan.start_date, plan.end_date or plan.start_date)}
        for booking in trip_tools.state(user, plan)["bookings"]:
            if not booking.get("start"):
                continue
            details = [f"Confirmation {booking['confirmation']}" if booking.get("confirmation") else "",
                       f"Booked with {booking['provider']}" if booking.get("provider") else "", f"Trip: {plan.title}"]
            event = {"summary": f"{booking['kind'].title()}: {booking['title']}", "location": booking.get("place", ""),
                     "description": "\n".join(d for d in details if d)}
            if "T" in booking["start"]:
                end = booking.get("end") if "T" in (booking.get("end") or "") else \
                    (datetime.fromisoformat(booking["start"]) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
                event.update(start={"dateTime": f"{booking['start']}:00", "timeZone": zone}, end={"dateTime": f"{end}:00", "timeZone": zone})
            else:
                event.update(_all_day(date.fromisoformat(booking["start"]), date.fromisoformat(booking["end"][:10]) if booking.get("end") else None))
            found[f"booking-{plan.pk}-{booking['id']}"] = event
    for analysis in CareerJobAnalysis.objects.filter(user=user).order_by("-updated_at")[:300]:
        payload = analysis.extracted_payload if isinstance(analysis.extracted_payload, dict) else {}
        if not payload.get("application"):
            continue
        due = follow_up_status(payload["application"], today=today)
        if due["status"] in ("due", "upcoming") and due["due_on"]:
            on = max(date.fromisoformat(due["due_on"]), today)  # an overdue follow-up shows today, not in the past
            if on <= high:
                found[f"follow-up-{analysis.pk}"] = {"summary": f"Follow up: {analysis.company or 'application'}"
                                                                f"{f' ({analysis.job_title})' if analysis.job_title else ''}", **_all_day(on)}
    for decision in ResearchDecision.objects.filter(user=user, settled_on__isnull=True, review_on__gte=low, review_on__lte=high):
        found[f"review-{decision.pk}"] = {"summary": f"Research review: {decision.instrument}", **_all_day(decision.review_on)}
    return dict(list(found.items())[:LIMIT])


def tasks(user, today: date) -> dict:
    from apps.mobility.models import TravelPlan
    from apps.mobility.services.travel.packing import KEY as PACKING
    from apps.mobility.services.travel.reminders import KEY as REMINDERS

    found = {}
    for plan in TravelPlan.objects.filter(user=user, end_date__gte=today).exclude(status__in=("cancelled", "completed")):
        state = plan.planning_state if isinstance(plan.planning_state, dict) else {}
        due = f"{(plan.start_date - timedelta(days=1)).isoformat()}T00:00:00.000Z" if plan.start_date else None
        for item in (state.get(PACKING) or {}).get("items") or []:
            found[f"pack-{plan.pk}-{item['id']}"] = {"title": f"Pack: {item['label']}", "notes": f"Trip: {plan.title}",
                                                     "status": "completed" if item.get("packed") else "needsAction",
                                                     **({"due": due} if due else {})}
        for row in ((state.get(REMINDERS) or {}).get("reminders") or []):
            if row.get("status") == "scheduled":
                found[f"reminder-{plan.pk}-{row['id']}"] = {"title": row["label"], "notes": f"Trip: {plan.title}",
                                                            "due": f"{timezone.localtime(datetime.fromisoformat(row['due_at'])).date()}T00:00:00.000Z",
                                                            "status": "needsAction"}
    return dict(list(found.items())[:LIMIT])


# ---- sync ----------------------------------------------------------------------------------------------------------

def _ensure(token, data):
    if data.get("calendar_id"):
        code, _ = _call(token, "GET", f"{CALENDAR}/calendars/{data['calendar_id']}")
        if code in (404, 410):
            data.update(calendar_id=None, events={})
    if not data.get("calendar_id"):
        _, made = _call(token, "POST", f"{CALENDAR}/calendars", {"summary": NAME, "timeZone": str(settings.TIME_ZONE),
                                                                   "description": "Kept in step by ALFRED on your PC."})
        data.update(calendar_id=made["id"], events={})
    if data.get("tasklist_id"):
        code, _ = _call(token, "GET", f"{TASKS}/users/@me/lists/{data['tasklist_id']}")
        if code in (404, 410):
            data.update(tasklist_id=None, tasks={})
    if not data.get("tasklist_id"):
        _, made = _call(token, "POST", f"{TASKS}/users/@me/lists", {"title": NAME})
        data.update(tasklist_id=made["id"], tasks={})


def _apply(token, wanted: dict, known: dict, base: str, *, update_method: str) -> dict:
    """Insert new items, replace changed ones, delete ones ALFRED no longer has. Unchanged items are left alone."""
    kept = {}
    for key, item in wanted.items():
        digest, before = _digest(item), known.get(key)
        if before and before["digest"] == digest:
            kept[key] = before
            continue
        if before:
            code, _ = _call(token, update_method, f"{base}/{before['id']}", {**item, "id": before["id"]})
            if code not in (404, 410):
                kept[key] = {"id": before["id"], "digest": digest}
                continue
        _, made = _call(token, "POST", base, item)
        kept[key] = {"id": made["id"], "digest": digest}
    for key in set(known) - set(wanted):
        _call(token, "DELETE", f"{base}/{known[key]['id']}")
    return kept


def sync(user) -> dict:
    data = _load(user)
    if not data or not data.get("refresh"):
        raise SyncError("Connect Google Calendar and Tasks in Settings first.")
    today = timezone.localdate()
    try:
        token = _access(data)
        _ensure(token, data)
        data["events"] = _apply(token, events(user, today), data.get("events", {}),
                                f"{CALENDAR}/calendars/{data['calendar_id']}/events", update_method="PUT")
        data["tasks"] = _apply(token, tasks(user, today), data.get("tasks", {}),
                               f"{TASKS}/lists/{data['tasklist_id']}/tasks", update_method="PUT")
        data.update(last_sync=timezone.now().isoformat(), last_error="")
    except SyncError as exc:
        data["last_error"] = str(exc)
        raise
    except PublicHTTPError as exc:
        data["last_error"] = ("Google could not be reached or refused a change. Check that the Google Calendar API and Google Tasks "
                              "API are turned on in your Google Cloud project; ALFRED will try again later.")
        raise SyncError(data["last_error"]) from exc
    finally:
        _store(user, data)
    return status(user)


def disconnect(user) -> dict:
    from apps.integrations.models import _decrypt_token

    data = _load(user)
    if data and data.get("refresh"):
        try:
            public_http.request("POST", REVOKE_URL, data={"token": _decrypt_token(data["refresh"])}, accepted_statuses=(200, 400))
        except PublicHTTPError:
            pass  # the local token is removed either way; the owner can also remove ALFRED at myaccount.google.com
    _path(user).unlink(missing_ok=True)
    return status(user)


def sync_everyone() -> int:
    """Background run for every connected owner; one failure never stops the others."""
    from django.contrib.auth import get_user_model

    done = 0
    for path in _folder().glob("user-*.json") if _folder().is_dir() else []:
        number = path.stem.removeprefix("user-")
        user = get_user_model().objects.filter(pk=int(number), is_active=True).first() if number.isdigit() else None
        if user is None:
            continue
        try:
            sync(user)
            done += 1
        except SyncError:
            continue
    return done
