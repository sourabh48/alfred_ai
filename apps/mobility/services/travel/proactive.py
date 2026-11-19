"""Proactive next steps for saved trips and trip ideas for free dates (owner request 2026-11-14).

Read-only: every step comes from the owner's saved records, the existing research runs or the static destination
guide, and says so. Nothing is booked, sent or saved here; a step's optional action runs only after the owner
confirms it (planner card or task bot).
"""
from datetime import timedelta

from django.db.models import Q
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
SAFETY_DAYS = 3
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


def flight_steps(plan, today):
    """Live status for each booked flight leaving today or tomorrow (AeroDataBox, with the person's own key)."""
    from . import trip_tools
    from .cache import query
    from .providers.flight_status import AeroDataBoxStatus, describe, flight_number

    steps = []
    for booking in trip_tools._latest(plan.user, f"bookings:{plan.pk}", []):
        number, day = flight_number(booking.get("title")), str(booking.get("start") or "")[:10]
        if booking.get("kind") != "flight" or not number or day not in (today.isoformat(), (today + timedelta(days=1)).isoformat()):
            continue
        try:
            result = query(AeroDataBoxStatus(), {"number": number, "date": day})
        except Exception:
            continue  # a status lookup must never break the trip page
        if result.success:
            status = result.payload
            late = status["delay_minutes"] >= 15 or status["status"].lower() in ("canceled", "cancelled", "diverted")
            steps.append({**_step(plan, "flight", ("Flight change: " if late else "Flight status: ") + number, describe(status),
                                  due_on=today, basis=f"AeroDataBox, checked {timezone.localtime():%d %b %H:%M}"),
                          "id": f"{plan.pk}:flight:{booking.get('id')}"})
    return steps


def safety_steps(plan, today):
    """Strong recent earthquakes near the destination and poor air there, for a trip starting within three days."""
    from .cache import query
    from .providers.safety import POOR_AIR, QUAKE_DAYS, QUAKE_RADIUS_KM, GoogleAirQuality, UsgsEarthquakes, destination_point

    point = destination_point(plan)
    if point is None:
        return []
    where, steps = {"latitude": point[0], "longitude": point[1]}, []
    try:
        quakes = query(UsgsEarthquakes(), {**where, "since": (today - timedelta(days=QUAKE_DAYS)).isoformat()})
        air = query(GoogleAirQuality(), where)
    except Exception:
        return []  # a safety lookup must never break the trip page
    for quake in (quakes.payload.get("quakes") or [])[:2] if quakes.success else []:
        steps.append({**_step(plan, "safety", f"Earthquake near {plan.destination or 'your destination'}",
            f"Magnitude {quake['magnitude']} {quake['place']} on {quake['when']}" + (", with a tsunami flag" if quake["tsunami"] else "")
            + f" (within {QUAKE_RADIUS_KM} km, last {QUAKE_DAYS} days). Check local authorities' advice before you go.",
            due_on=today, links=[{"label": "USGS details", "url": quake["url"]}] if quake["url"] else [],
            basis="US Geological Survey"), "id": f"{plan.pk}:safety:quake:{quake['when']}"})
    if air.success and air.payload["aqi"] < POOR_AIR:
        steps.append(_step(plan, "air", f"Poor air in {plan.destination or 'your destination'}",
            f"{air.payload['category']} right now (Universal AQI {air.payload['aqi']} of 100; main pollutant {air.payload['pollutant'] or 'unknown'}). "
            "Consider a mask and fewer outdoor hours; this is current air, not a forecast.", due_on=today, basis="Google Air Quality"))
    return steps


def next_steps(plan, today=None):
    """What to do next for one saved trip, earliest first. Empty for past, closed or undated trips."""
    today = today or timezone.localdate()
    if plan.status not in ACTIVE or not plan.start_date:
        return []
    live = flight_steps(plan, today)
    if (plan.start_date - today).days <= SAFETY_DAYS and (plan.end_date or plan.start_date) >= today:
        live += safety_steps(plan, today)
    if plan.start_date < today:
        return live  # a trip under way: only live news about its flights
    days = (plan.start_date - today).days
    end = plan.end_date or plan.start_date
    session = getattr(plan, "planning_session", None)
    steps = live

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
    under_way = Q(start_date__lt=today, end_date__gte=today)  # its return flight can still be delayed
    plans = (TravelPlan.objects.filter(Q(start_date__gte=today, start_date__lte=today + timedelta(days=HORIZON_DAYS)) | under_way,
                                       user=user, status__in=ACTIVE)
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


def trip_ideas(user, today=None, limit=3, exclude=()):
    """Destinations from the offline guide that fit saved preferences, for the next free weekend; `exclude` names the
    places the open trip already shows, so no place is suggested twice on the page."""
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
             for d in candidates_for(user, state, limit=limit + len(exclude))
             if d["name"].casefold() not in {str(name).casefold() for name in exclude}][:limit]
    return {"free_dates": {"start": window[0].isoformat(), "end": window[1].isoformat()}, "ideas": ideas,
            "origin": value(state, "origin"),
            "note": "From ALFRED's offline destination guide and your saved preferences. Weather, prices, roads and rooms are not checked yet."}
