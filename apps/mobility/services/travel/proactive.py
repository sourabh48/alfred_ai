"""Proactive next steps for saved trips and trip ideas for free dates (owner request 2026-11-14).

Read-only: every step comes from the owner's saved records, the existing research runs or the static destination
guide, and says so. Nothing is booked, sent or saved here; a step's optional action runs only after the owner
confirms it (planner card or task bot).
"""
from datetime import timedelta

from django.utils import timezone

from ...models import TravelPlan
from ..travel_discovery import candidates_for, fact, value
from .bike import bike_context
from .links import booking_sites
from .packing import _checklist
from .providers.weather import FORECAST_DAYS
from .reminders import RemindersUnavailable, _load as reminder_policy

ACTIVE = ("draft", "researching", "suggestions_ready", "planned", "confirmed", "booked")
HORIZON_DAYS = 60
IDEA_WEEKS = 8


def _step(plan, kind, title, detail, *, due_on=None, links=(), action=None, basis="Your saved trip"):
    return {"id": f"{plan.pk}:{kind}", "plan_id": plan.pk, "session_id": getattr(getattr(plan, "planning_session", None), "pk", None),
            "trip": plan.title, "kind": kind, "title": title, "detail": detail,
            "due_on": due_on.isoformat() if due_on else None, "links": list(links), "action": action, "basis": basis}


def _latest_recheck(plan):
    session = getattr(plan, "planning_session", None)
    if session is None:
        return None
    return session.research_runs.filter(recheck=True, status="ready", completed_at__gte=plan.created_at).order_by("-completed_at").first()


def next_steps(plan, today=None):
    """What to do next for one saved trip, earliest first. Empty for past, closed or undated trips."""
    today = today or timezone.localdate()
    if plan.status not in ACTIVE or not plan.start_date or plan.start_date < today:
        return []
    days = (plan.start_date - today).days
    end = plan.end_date or plan.start_date
    session = getattr(plan, "planning_session", None)
    steps = []

    forecast_from = plan.start_date - timedelta(days=FORECAST_DAYS - 1)
    run = session.research_runs.filter(status="ready").order_by("-completed_at").first() if session else None
    checked = timezone.localdate(run.completed_at) if run and run.completed_at else None
    if days >= FORECAST_DAYS:
        steps.append(_step(plan, "weather", "Weather check opens later",
            f"Google's forecast covers 10 days, so your dates can be checked from {forecast_from:%d %b %Y}.", due_on=forecast_from))
    elif checked is None or checked < forecast_from or (days <= 3 and checked < today - timedelta(days=1)):
        steps.append(_step(plan, "weather", "Recheck the weather now",
            "Your dates are inside the forecast window" + (f"; the last check was {checked:%d %b %Y}." if checked else " and no check is saved yet."),
            due_on=today, action={"type": "recheck"} if session else None))

    recheck = _latest_recheck(plan)
    for index, change in enumerate((recheck.changes or [])[:5] if recheck else []):
        steps.append({**_step(plan, "changed", "Changed since you saved the trip", str(change), due_on=today,
                              basis=f"Recheck on {timezone.localdate(recheck.completed_at):%d %b %Y}"),
                      "id": f"{plan.pk}:changed:{index}"})

    if plan.status != "booked" and days <= 30:
        sites = [site for site in booking_sites() if site["category"] == "hotels"]
        steps.append(_step(plan, "stay", "Confirm where you stay",
            "The trip is not marked booked. ALFRED never books; compare and book on the verified sites, then mark the trip booked."
            + (f" Saved stay note: {plan.stay_details}." if plan.stay_details else ""),
            due_on=max(today, plan.start_date - timedelta(days=14)),
            links=[{"label": site["label"], "url": site["url"]} for site in sites]))

    if days <= 7:
        left = [item["label"] for item in _checklist(plan)["items"] if not item["packed"]]
        if left:
            steps.append(_step(plan, "packing", f"{len(left)} packing item(s) not ticked",
                ", ".join(left[:5]) + (" and more." if len(left) > 5 else "."), due_on=max(today, plan.start_date - timedelta(days=2))))

    if plan.transport_mode in ("ride", "roadtrip") and plan.vehicle_profile_id:
        route = plan.itinerary.get("route") or {}
        distance = route.get("distance_km_total") or ((route.get("distance_km_one_way") or 0) * 2) or None
        for index, warning in enumerate(bike_context(plan.vehicle_profile, end_date=end.isoformat(), distance_km=distance)["warnings"][:6]):
            steps.append({**_step(plan, "vehicle", "Check the bike before the ride", warning, due_on=max(today, plan.start_date - timedelta(days=3)),
                                  basis="Your saved bike records, not an inspection"), "id": f"{plan.pk}:vehicle:{index}"})

    if session and days >= 2:
        try:
            policy = reminder_policy(plan)
        except RemindersUnavailable:
            policy = None
        if policy is not None and not any(row["status"] == "scheduled" for row in policy["reminders"]):
            eve = plan.start_date - timedelta(days=1)
            steps.append(_step(plan, "reminder", "Add a reminder for the evening before",
                f"A reminder at 18:00 on {eve:%d %b %Y} to check weather, documents and packing. It turns on reminders for this trip.",
                due_on=today, action={"type": "reminder", "label": f"Tomorrow: {plan.title[:120]}. Check weather, documents and packing.",
                                      "zone": timezone.get_current_timezone_name(), "local_time": f"{eve.isoformat()}T18:00",
                                      "enable": not policy["enabled"]}))
    return sorted(steps, key=lambda step: (step["due_on"] or "9999", step["id"]))


def upcoming_steps(user, today=None):
    today = today or timezone.localdate()
    plans = (TravelPlan.objects.filter(user=user, status__in=ACTIVE, start_date__gte=today,
                                       start_date__lte=today + timedelta(days=HORIZON_DAYS))
             .select_related("vehicle_profile", "planning_session").order_by("start_date", "id")[:10])
    return [step for plan in plans for step in next_steps(plan, today)]


def free_weekend(user, today=None):
    """The next Saturday-Sunday with no active saved trip on either day."""
    today = today or timezone.localdate()
    busy = [(p.start_date, p.end_date or p.start_date) for p in TravelPlan.objects.filter(
        user=user, status__in=ACTIVE, start_date__isnull=False, start_date__lte=today + timedelta(weeks=IDEA_WEEKS + 1))]
    saturday = today + timedelta(days=(5 - today.weekday()) % 7 or 7)
    for week in range(IDEA_WEEKS):
        start = saturday + timedelta(weeks=week)
        if not any(first <= start + timedelta(days=1) and start <= last for first, last in busy):
            return start, start + timedelta(days=1)
    return None


def trip_ideas(user, today=None, limit=3):
    """Destinations from the offline guide that fit saved preferences, for the next free weekend."""
    window = free_weekend(user, today)
    if window is None:
        return {"free_dates": None, "ideas": [], "note": "No free weekend in the next eight weeks."}
    latest = user.travel_sessions.order_by("-updated_at", "-id").first()
    state = {key: item for key, item in (latest.state if latest else {}).items()
             if key in ("origin", "budget", "transport_mode", "maximum_daily_driving", "must_avoid", "preferred_trip_style",
                        "preferred_activities", "number_of_travelers")}
    if not value(state, "origin") and getattr(user, "city", ""):
        state["origin"] = fact(user.city, "profile_city")
    if not value(state, "origin"):
        return {"free_dates": None, "ideas": [], "note": "Add your home city in your profile or a trip, and ALFRED will suggest weekend trips."}
    state.update(trip_duration=fact(2, "free_weekend"), available_start_date=fact(window[0].isoformat(), "free_weekend"),
                 available_end_date=fact(window[1].isoformat(), "free_weekend"))
    ideas = [{"name": d["name"], "fit": d["fit"], "why": d["why"], "distance_km": d.get("distance_km"),
              "distance_basis": d.get("distance_basis"), "source_freshness": d.get("source_freshness", "STATIC_REFERENCE")}
             for d in candidates_for(user, state, limit=limit)]
    return {"free_dates": {"start": window[0].isoformat(), "end": window[1].isoformat()}, "ideas": ideas,
            "origin": value(state, "origin"),
            "note": "From ALFRED's offline destination guide and your saved preferences. Weather, prices, roads and rooms are not checked yet."}
