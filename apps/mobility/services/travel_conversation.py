"""Local, deterministic travel intent extraction with explicit provenance.

No private conversation, history, vehicle record or media is sent to a model
provider. Unrecognised edits ask for clarification instead of inventing changes.
"""
import calendar
from copy import deepcopy
from datetime import date, timedelta
import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.mobility.models import BikeProfile, TravelMessage, TravelPlan, TravelPlanningSession
from .travel_catalog import ALIASES, CITIES, DESTINATIONS, lookup
from .travel_discovery import candidates_for, fact, learn, profile_for, value
from .travel_itinerary import build_itinerary, edit_itinerary
from .travel_research import queue_research

STYLE_WORDS = {
    "mountains": ["mountain", "hills"], "beaches": ["beach"], "forests": ["forest", "nature"],
    "waterfalls": ["waterfall"], "wildlife": ["wildlife"], "historical places": ["history", "historical"],
    "architecture": ["architecture"], "trekking": ["trek", "hiking"], "camping": ["camping", "camp"],
    "photography": ["photography", "photos"], "food": ["food"], "culture": ["culture"], "nightlife": ["nightlife"],
    "quiet locations": ["peaceful", "quiet", "relaxing", "romantic"], "offbeat places": ["offbeat"],
    "adventure": ["adventure"], "slow travel": ["slow travel", "relaxed"], "cool weather": ["cool", "cooler"],
    "scenic roads": ["scenic", "bike trip", "road trip"], "budget travel": ["budget travel"],
}
MONTHS = {name.lower(): n for n in range(1, 13) for name in (calendar.month_name[n], calendar.month_abbr[n])}
MONTH_PATTERN = "|".join(sorted(MONTHS, key=len, reverse=True))


def say(session, text, chips=()):
    return TravelMessage.objects.create(session=session, role="assistant", text=text, chips=list(chips))


def new_session(user, plan=None):
    session = TravelPlanningSession.objects.create(user=user, plan=plan, title=plan.title if plan else "Your next escape")
    if plan:
        session.state = deepcopy(plan.planning_state)
        for key, val in {"selected_destination": plan.destination, "available_start_date": plan.start_date.isoformat() if plan.start_date else None,
                         "available_end_date": plan.end_date.isoformat() if plan.end_date else None,
                         "budget": plan.budget, "transport_mode": plan.transport_mode, "trip_duration": plan.duration_days or None}.items():
            if val is not None:
                session.state[key] = fact(val, "saved_plan", True)
        session.itinerary = plan.itinerary
        session.status = "itinerary_ready" if plan.itinerary else "discovery"
    if not value(session.state, "origin") and user.city:
        session.state["origin"] = fact(user.city, "configured_home_city", False, .85)
    session.save()
    say(session, "Where are you thinking of going? Or just tell me your dates, budget, or the kind of escape you want. A destination is optional.",
        ["3-day bike trip", "Under ₹10,000", "Somewhere cool", "Weekend escape", "Photography trip", "Surprise me"])
    return session


def extract(state, text):
    state = deepcopy(state)
    lower = text.lower().strip().replace("’", "'")
    notes = []
    def put(k, v, source="user_message", confirmed=True, confidence=1):
        state[k] = fact(v, source, confirmed, confidence)
    money = re.search(r"(?:₹|inr\s*|rs\.?\s*|budget(?:\s+is|\s+of)?\s*|under\s+|around\s+)([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh)?", lower)
    if not money:
        money = re.search(r"\b(\d+(?:\.\d+)?)\s*(k|thousand|lakh)\b", lower)
    if money:
        amount = float(money[1].replace(",", "")) * ({"k": 1000, "thousand": 1000, "lakh": 100000}.get(money[2], 1))
        if not 0 < amount <= 100000000:
            raise ValidationError("Choose a positive budget up to ₹10 crore.")
        put("budget", amount)
        explicit_scope = "per person" in lower or "each" in lower or "total" in lower
        put("budget_scope", "per_person" if "per person" in lower or "each" in lower else "whole_trip",
            "user_message" if explicit_scope else "planning_assumption", explicit_scope, 1 if explicit_scope else .7)
    for tier in ("budget", "moderate", "premium"):
        if lower in {tier, f"{tier} options"}:
            put("budget_type", tier)
    duration = re.search(r"\b(\d+)\s*[- ]?\s*days?\b", lower)
    if duration and not re.search(r"\bday\s*\d+", lower):
        if not 1 <= int(duration[1]) <= 30:
            raise ValidationError("Plan between 1 and 30 days per session.")
        put("trip_duration", int(duration[1]))
    elif "weekend" in lower and not value(state, "trip_duration"):
        put("trip_duration", 3 if "long" in lower else 2, "approximate_user_duration", False, .8)
    iso = re.findall(r"\b20\d{2}-\d{2}-\d{2}\b", lower)
    dates = None
    inferred_year = False
    try:
        if len(iso) >= 2:
            dates = (date.fromisoformat(iso[0]), date.fromisoformat(iso[1]))
        else:
            pattern = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*({MONTH_PATTERN})?\s*(?:to|until|through|[-–—])\s*(\d{{1,2}})(?:st|nd|rd|th)?\s*({MONTH_PATTERN})(?:\s+(20\d{{2}}))?"
            m = re.search(pattern, lower)
            if m:
                year = int(m[5] or timezone.localdate().year)
                start = date(year, MONTHS[m[2] or m[4]], int(m[1]))
                end = date(year + (MONTHS[m[4]] < start.month), MONTHS[m[4]], int(m[3]))
                if not m[5] and end < timezone.localdate():
                    start, end = start.replace(year=start.year+1), end.replace(year=end.year+1)
                dates = start, end
                if not m[5]:
                    inferred_year = True
                    notes.append(f"I used {start.year} for these dates; tell me if you meant another year.")
        if dates:
            days = (dates[1]-dates[0]).days+1
            if not 1 <= days <= 30:
                raise ValueError()
            put("available_start_date", dates[0].isoformat(), "user_dates_inferred_year" if inferred_year else "user_message", not inferred_year, .85 if inferred_year else 1)
            put("available_end_date", dates[1].isoformat(), "user_dates_inferred_year" if inferred_year else "user_message", not inferred_year, .85 if inferred_year else 1)
            put("trip_duration", days)
    except ValueError:
        raise ValidationError("Use a valid date window of 1–30 days, for example ‘2 October to 5 October 2026’.")
    if "add one day" in lower or "add a day" in lower:
        duration = min(30, int(value(state, "trip_duration", 2))+1)
        put("trip_duration", duration)
        if value(state, "available_start_date"):
            put("available_end_date", (date.fromisoformat(value(state, "available_start_date"))+timedelta(days=duration-1)).isoformat())
    origin_match = re.search(r"(?:starting (?:from|in)|start (?:from|in)|origin(?: is)?|from)\s+([a-z][a-z .'-]{1,70}?)(?=[,.;!?]|\s+(?:for|on|with|under|and|to|home)\b|$)", lower)
    if origin_match and not re.match(MONTH_PATTERN, origin_match[1]):
        put("origin", origin_match[1].strip().title())
    elif (lower in CITIES and (not value(state, "origin") or value(state, "pending_question") == "origin")) or (value(state, "pending_question") == "origin" and re.fullmatch(r"[a-z][a-z .'-]{1,70}", lower)
                              and lower not in {"surprise me", "change starting city"}):
        put("origin", lower.title())
    if lower in {"yes", "yes use that", "confirm starting city"} or lower.startswith("confirm "):
        if value(state, "origin"):
            state["origin"] = fact(value(state, "origin"), "user_confirmation", True)
    if "change starting city" in lower:
        state.pop("origin", None)
    styles = set(value(state, "preferred_trip_style", []))
    avoided = set(value(state, "must_avoid", []))
    for style, words in STYLE_WORDS.items():
        for word in words:
            if re.search(r"\b"+re.escape(word), lower):
                if re.search(r"(?:no|not|avoid|without|remove|don't want)\s+(?:\w+\s+)?"+re.escape(word), lower):
                    avoided.add(style)
                    styles.discard(style)
                else:
                    styles.add(style)
                break
    for place in [d["name"] for d in DESTINATIONS] + ["Goa"]:
        if re.search(r"(?:not|avoid|except|no)\s+"+place.lower(), lower):
            avoided.add(place)
    if styles:
        put("preferred_trip_style", sorted(styles))
    if avoided:
        put("must_avoid", sorted(avoided))
    if any(w in lower for w in ("haven't visited", "not visited", "somewhere new", "mostly new")):
        put("novelty", "mostly_new")
    elif "familiar" in lower or "revisit" in lower:
        put("novelty", "mostly_familiar")
    for pattern, mode in [(r"\b(?:bike|motorcycle|riding)\b", "ride"), (r"\b(?:car|road trip)\b", "roadtrip"), (r"\btrain\b", "train"), (r"\bflight|fly\b", "flight")]:
        if re.search(pattern, lower):
            put("transport_mode", mode)
    if "pillion" in lower:
        asking = "?" in lower or lower.startswith("can i")
        put("pillion", not bool(re.search(r"(?:no|without)\s+pillion", lower)), confirmed=not asking, confidence=.7 if asking else 1)
        if not asking and value(state, "pillion"):
            put("number_of_travelers", max(2, value(state, "number_of_travelers", 1)))
    for kind in ("solo", "couple", "family", "group"):
        if kind in lower or kind == "couple" and "romantic" in lower:
            put(kind+"_trip", True)
            if kind in {"solo", "couple"}:
                put("number_of_travelers", 1 if kind == "solo" else 2)
    travellers = re.search(r"\b(\d+)\s*(?:people|persons|travellers|travelers|adults)\b", lower)
    if travellers:
        if not 1 <= int(travellers[1]) <= 50:
            raise ValidationError("Use between 1 and 50 travellers.")
        put("number_of_travelers", int(travellers[1]))
    if "not too much riding" in lower or "short rides" in lower:
        put("maximum_daily_driving", 200)
    daily = re.search(r"(\d+)\s*km\s*(?:a|per|each)?\s*day", lower)
    if daily:
        put("maximum_daily_driving", max(20, min(1000, int(daily[1]))))
    if "wake" in lower and "8" in lower:
        put("earliest_departure_hour", 8)
    for food in ("vegetarian", "vegan", "halal", "gluten-free"):
        if food in lower:
            put("food_preferences", food)
    for stay in ("homestay", "resort", "hostel", "hotel", "camping"):
        if stay in lower:
            put("preferred_accommodation", stay)
    for interest in ("camping", "trekking", "photography", "nightlife"):
        if interest in styles or interest in avoided:
            put(interest+"_interest", interest in styles)
    return state, notes


def vehicle_state(session):
    ident = value(session.state, "vehicle_profile")
    bike = BikeProfile.objects.filter(user=session.user, pk=ident).first() if ident else None
    if not bike and not ident and value(session.state,"transport_mode") in {"ride","roadtrip"}:
        types = ["motorcycle","scooter"] if value(session.state,"transport_mode") == "ride" else ["car"]
        bike = BikeProfile.objects.filter(user=session.user,is_primary=True,vehicle_type__in=types).first()
        if bike:
            session.state["vehicle_profile"] = fact(bike.id,"configured_primary_vehicle",False,.85)
    if bike:
        for field, val in {"vehicle_name": bike.display_name, "vehicle_mileage": bike.expected_mileage_kmpl,
                           "vehicle_tank_litres": bike.fuel_tank_capacity_l}.items():
            if val:
                session.state[field] = fact(val, "vehicle_profile", session.state["vehicle_profile"].get("confirmed_by_user",False), .95)


def ready_prompt(session, prefix=""):
    state = session.state
    if not value(state, "trip_duration"):
        state["pending_question"] = fact("duration", "assistant", False)
        say(session, prefix+"How many days do you have? Approximate duration is fine.", ["2 days", "3 days", "4 days", "A long weekend"])
    elif not value(state, "origin"):
        state["pending_question"] = fact("origin", "assistant", False)
        say(session, prefix+"Where will you be starting from? A city is enough.")
    elif not state["origin"].get("confirmed_by_user"):
        state["pending_question"] = fact("origin_confirmation", "assistant", False)
        say(session, prefix+f"I'll assume you're starting from {value(state, 'origin')}, from your configured city. Use that?",
            ["Yes use that", "Change starting city"])
    elif not value(state, "budget") and not value(state, "budget_type"):
        state["pending_question"] = fact("budget", "assistant", False)
        say(session, prefix+"I can suggest places without an exact budget. Do you want budget, moderate or premium options?",
            ["Budget options", "Moderate options", "Premium options"])
    else:
        state.pop("pending_question", None)
        session.save()
        session.candidates = candidates_for(session.user, state)
        session.save(update_fields=["candidates"])
        queue_research(session)
        say(session, prefix+f"I'll compare places for {value(state, 'trip_duration')} days from {value(state, 'origin')}. Preliminary estimates are below; current research continues in the background.",
            ["Mountains", "Beach", "Nature", "Research thoroughly"])
    session.save()


@transaction.atomic
def send_message(session_id, user, text):
    session = TravelPlanningSession.objects.select_for_update().get(pk=session_id, user=user)
    text = str(text).strip()
    if not text or len(text) > 2000:
        raise ValidationError("Send a message of 1–2,000 characters.")
    old_state = deepcopy(session.state)
    session.state, notes = extract(session.state, text)
    TravelMessage.objects.create(session=session, role="user", text=text)
    lower = text.lower()
    if session.state != old_state:
        session.revision += 1
    for key in ([] if session.itinerary else value(session.state, "preferred_trip_style", [])):
        if key not in value(old_state, "preferred_trip_style", []):
            learn(user, key, True, "Explicit statement: "+text[:160], 1, True)
    for key in value(session.state, "must_avoid", []):
        if key not in value(old_state, "must_avoid", []):
            learn(user, key, False, "Explicit avoidance: "+text[:160], 1, True)
    vehicle_state(session)
    if session.title == "Your next escape" and value(session.state,"available_start_date"):
        session.title = date.fromisoformat(value(session.state,"available_start_date")).strftime("%B escape")
    session.save()
    prefix = " ".join(notes) + (" " if notes else "")
    if lower in {"compare", "compare destinations", "compare again"}:
        say(session, "Compare the options below. Estimates share the same budget assumptions; unknown facts are labelled.")
        return session
    if lower in {"research thoroughly", "deep research", "research more", "retry research", "recheck trip"}:
        if not session.candidates:
            ready_prompt(session, prefix)
        else:
            queue_research(session, deep=True, recheck=lower == "recheck trip")
            say(session, "Research is saved and queued. You can close this page; the results and sources will be here when you return.")
        return session
    choice = None
    option = re.search(r"(?:option|choose)\s*(\d)\b", lower)
    if option and 1 <= int(option[1]) <= len(session.candidates):
        choice = session.candidates[int(option[1])-1]
    for candidate in session.candidates:
        if (lower.rstrip(".! ") == candidate["name"].lower() or re.search(r"(?:choose|let's do|lets do|go with|select)\s+"+re.escape(candidate["name"].lower()), lower)):
            choice = candidate
    if lower in {"let's do that", "choose that", "choose it"}:
        choice = next((c for c in session.candidates if c["name"] == value(session.state, "referenced_destination")), None)
    if choice and ("what about" in lower or lower.endswith("?")):
        session.state["referenced_destination"] = fact(choice["name"], "conversation_reference", False)
        say(session, f"Option {session.candidates.index(choice)+1} is {choice['name']}. " + " ".join(choice["why"]) + " I haven't selected it yet.",
            ["Choose "+choice["name"], "Compare destinations"])
        session.save()
        return session
    if choice:
        session.state["selected_destination"] = fact(choice["name"])
        session.status = "destination_selected"
        session.itinerary = {}
        session.title = f"{choice['name']} escape"
        for style in choice["styles"]:
            learn(user, style, True, f"Accepted recommendation: {choice['name']}", .55)
        say(session, f"Great. {choice['name']} for {value(session.state, 'trip_duration')} days from {value(session.state, 'origin')}, "
            + (f"target ₹{value(session.state, 'budget'):,.0f}. " if value(session.state, "budget") else "with your chosen budget style. ")
            + "Shall I build the full itinerary?", ["Build itinerary", "Compare again", "Adjust budget", "Change dates"])
    elif lower in {"build itinerary", "build the itinerary"}:
        selected = next((c for c in session.candidates if c["name"] == value(session.state, "selected_destination")), None)
        if not selected:
            say(session, "Choose a destination first, then I'll build one detailed itinerary.")
        else:
            session.itinerary = build_itinerary(session.state, selected)
            session.status = "itinerary_ready"
            say(session, "Your flexible itinerary is ready. Review the day-by-day plan, budget and verification notes. Tell me what to change.",
                ["Make day 2 relaxed", "Reduce the budget", "Add one waterfall"])
    elif lower == "adjust budget":
        say(session, "What budget should I use? For example: ‘Budget ₹12,000 total’.")
    elif lower == "change dates":
        say(session, "Tell me the new dates, for example ‘2 October to 5 October 2026’, or a duration such as ‘4 days’.")
    elif "pillion" in lower:
        if session.state.get("pillion", {}).get("confirmed_by_user"):
            if session.itinerary and session.itinerary.get("bike"):
                session.itinerary["bike"]["pillion"] = value(session.state,"pillion")
                session.itinerary["checks"].append("Pillion changed: review luggage, rest breaks and a two-person budget before saving.")
            say(session, "I've updated the pillion preference. Use your vehicle's documented capacity, allow regular breaks, and verify road/weather suitability. Rebuild the itinerary to recalculate for the traveller count.", ["Build itinerary"])
        else:
            say(session, "I can adapt this trip for a pillion. Vehicle load limits and current road suitability need checking; I won't invent them. Shall I include a second traveller and recalculate?", ["Include pillion"])
    elif session.itinerary:
        timing_changed = any(value(session.state,k) != value(old_state,k) for k in ("available_start_date", "available_end_date", "trip_duration"))
        if timing_changed:
            selected = next((c for c in session.candidates if c["name"] == value(session.state, "selected_destination")), None)
            if selected:
                old_itinerary = deepcopy(session.itinerary)
                session.itinerary = build_itinerary(session.state, selected)
                if len(old_itinerary["days"]) == len(session.itinerary["days"]):
                    for old_day, day in zip(old_itinerary["days"], session.itinerary["days"]):
                        old_day["date"] = day["date"]
                    session.itinerary["days"] = old_itinerary["days"]
                    session.itinerary["budget"] = old_itinerary["budget"]
                    session.itinerary["edits"] = old_itinerary["edits"]
                session.itinerary["weather"] = {"summary":"Dates changed. Recheck weather for the revised window.","confidence":"UNKNOWN"}
                session.itinerary["sources"] = []
                say(session, "Updated the dates and duration. Review the revised plan and recheck weather before saving.", ["Recheck trip"])
        else:
            edited, reply = edit_itinerary(session.itinerary, text, session.state)
            if edited:
                session.itinerary = edited
            say(session, reply)
    else:
        if "cheaper" in lower:
            session.state["budget_type"] = fact("budget")
            if value(session.state, "budget"):
                session.state["budget"] = fact(round(value(session.state, "budget")*.8), "assistant_proposal", False, .6)
                prefix += "I'll compare options about 20% cheaper; this is a proposed target you can change. "
            session.revision += 1
        ready_prompt(session, prefix)
    session.save()
    return session


@transaction.atomic
def save_plan(session, draft=False):
    session = TravelPlanningSession.objects.select_for_update().get(pk=session.id)
    selected = value(session.state, "selected_destination")
    start, end = value(session.state, "available_start_date"), value(session.state, "available_end_date")
    if not draft and (not selected or not session.itinerary or not start or not end):
        raise ValidationError("Choose a destination, build the itinerary and confirm dates before saving a planned trip. You can save a draft now.")
    plan = session.plan or TravelPlan(user=session.user)
    if not draft:
        # Save is explicit acceptance of the displayed core plan, including the
        # clearly labelled inferred year. Destination still requires selection.
        for key in ("available_start_date","available_end_date","budget_scope","budget"):
            if key in session.state:
                session.state[key] = fact(value(session.state,key),"saved_plan_confirmation",True)
    plan.title = session.title
    plan.destination = selected or None
    plan.start_date = date.fromisoformat(start) if start else None
    plan.end_date = date.fromisoformat(end) if end else None
    plan.budget = value(session.state, "budget", 0) or session.itinerary.get("budget", {}).get("expected", 0)
    plan.transport_mode = value(session.state, "transport_mode", "mixed")
    plan.status = (session.status if session.status in {"researching","suggestions_ready"} else "draft") if draft else "planned"
    plan.planning_state = deepcopy(session.state)
    plan.itinerary = deepcopy(session.itinerary)
    plan.vehicle_profile = BikeProfile.objects.filter(user=session.user, pk=value(session.state, "vehicle_profile")).first()
    if session.itinerary:
        plan.stay_details = session.itinerary["days"][0].get("stay", "")[:200]
    plan.full_clean()
    plan.save()
    session.plan = plan
    session.save()
    if not draft:
        for key, val in {"typical_duration":plan.duration_days, "typical_spend":plan.budget, "preferred_transport":plan.transport_mode}.items():
            learn(session.user,key,val,f"Saved trip: {plan.title}",.5)
    say(session, "Draft saved. You can return to this conversation later." if draft else "Travel Plan saved with your itinerary, research and conversation. No retyping needed.")
    return plan
