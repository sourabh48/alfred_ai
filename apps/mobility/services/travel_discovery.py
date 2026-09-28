from collections import Counter
from math import ceil

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.mobility.models import BikeProfile, TravelPlan, TravelPreferenceProfile, TripLog, TripPhoto
from .travel_catalog import DESTINATIONS, approximate_road_km, lookup


def value(state, key, default=None):
    return state.get(key, {}).get("value", default)


def fact(value, source="user_message", confirmed=True, confidence=1.0):
    return {"value": value, "source": source, "confidence": confidence, "confirmed_by_user": confirmed}


def profile_for(user):
    return TravelPreferenceProfile.objects.get_or_create(user=user)[0]


def learn(user, key, val, source, confidence=0.6, confirmed=False):
    profile = profile_for(user)
    if not profile.learning_enabled and not confirmed:
        return
    old = profile.preferences.get(key, {})
    if old.get("confirmed_by_user") and not confirmed:
        return
    reasons = old.get("reasons", [])
    if source not in reasons:
        reasons = (reasons + [source])[-15:]
    profile.preferences[key] = {**fact(val, source, confirmed, confidence), "reasons": reasons,
                                "updated_at": timezone.now().isoformat()}
    profile.save(update_fields=["preferences", "updated_at"])


def history_for(user):
    visits = Counter()
    recent = Counter()
    ratings = {}
    now = timezone.localdate()
    for p in TravelPlan.objects.filter(user=user).prefetch_related("logs").select_related("feedback"):
        if p.destination and (p.status == "completed" or p.logs.exists()):
            name = (lookup(p.destination) or {}).get("name", p.destination)
            visits[name] += 1
            if p.end_date and 0 <= (now - p.end_date).days <= 365:
                recent[name] += 1
        try:
            ratings[p.destination] = p.feedback.rating
        except TravelPlan.feedback.RelatedObjectDoesNotExist:
            pass
    locations = list(TripLog.objects.filter(user=user).exclude(location_name="").values_list("location_name", flat=True))
    locations += list(TripPhoto.objects.filter(user=user).exclude(location_name="").values_list("location_name", flat=True))
    for d in DESTINATIONS:
        if not visits[d["name"]] and any(d["name"].lower() in loc.lower() for loc in locations):
            visits[d["name"]] = 1
    return {"visits": dict(visits), "recent": dict(recent), "ratings": ratings}


def budget_for(state, destination, *, relaxed_days=0):
    days = max(1, min(int(value(state, "trip_duration", 3)), 30))
    people = max(1, int(value(state, "number_of_travelers", 1)))
    mode = value(state, "transport_mode", "mixed")
    km = destination.get("distance_km")
    nightly = destination.get("nightly", 1500)
    tier = value(state, "budget_type", "moderate")
    target = value(state, "budget", 0) or 0
    if value(state, "budget_scope") == "per_person":
        target *= people
    if tier == "budget" or (target and target / days / people < 3000):
        nightly *= .7
    elif tier == "premium":
        nightly *= 2
    # Vehicle is resolved and supplied locally by the owner-scoped service.
    mileage = value(state, "vehicle_mileage")
    if mileage is not None and mileage <= 0:
        mileage = None
    assumptions = [f"{people} traveller(s), {days} days, {max(days-1, 0)} nights; shared rooms for pairs.",
                   "INR estimates, not quotes or confirmed availability. Meals estimated at ₹650 per person/day."]
    fuel = 0
    transport = 0
    if mode in {"ride", "roadtrip"}:
        planning_mileage = mileage or (30 if mode == "ride" else 14)
        fuel = round(((km or 250) * 2 + days * 25) / planning_mileage * 110)
        assumptions.append(f"Fuel allowance ₹110/litre; {planning_mileage} km/l " +
                           ("from your vehicle profile." if mileage else "as a costing assumption, not a vehicle specification."))
    else:
        transport = round(max(1000, (km or 250) * (6 if mode != "flight" else 14)) * people)
        assumptions.append("Transport allowance only; no train/flight fare or seat availability verified.")
    categories = {"Transport": transport, "Fuel": fuel, "Tolls": 400 if mode == "roadtrip" else 0,
                  "Stay": round(nightly * max(0, days-1) * ceil(people/2)), "Food": 650*days*people,
                  "Activities": max(0, days-2-relaxed_days)*350*people, "Permits": 300*people,
                  "Parking": 100*days if mode in {"ride", "roadtrip"} else 0,
                  "Local Transport": 0 if mode in {"ride", "roadtrip"} else 350*days*people}
    categories["Emergency Buffer"] = round(sum(categories.values()) * .15)
    expected = sum(categories.values())
    return {"categories": categories, "minimum": round(expected*.8), "expected": expected,
            "comfortable": round(expected*1.2), "target": target, "currency": "INR", "scope": "whole_trip",
            "over_budget": max(0, expected-target) if target else 0, "assumptions": assumptions,
            "adaptations": (["Choose a budget homestay", "Remove paid activities", "Try a nearer destination or shorten the trip"] if target and expected > target else [])}


def candidates_for(user, state, limit=3):
    profile = profile_for(user)
    history = history_for(user)
    styles = set(value(state, "preferred_trip_style", []) + value(state, "preferred_activities", []))
    weights = {s:1 for s in styles}
    for k, pref in profile.preferences.items():
        if pref.get("value") is not True:
            continue
        confidence = pref.get("confidence",0)
        updated = parse_datetime(pref.get("updated_at") or "")
        if updated and not pref.get("confirmed_by_user"):
            confidence *= max(.2, 1-(timezone.now()-updated).days/730)
        if confidence >= .3:
            styles.add(k)
            weights.setdefault(k,confidence)
    avoid = [str(a).lower() for a in value(state, "must_avoid", [])]
    avoided_styles = set(avoid)
    styles -= avoided_styles
    days = value(state, "trip_duration", 3)
    novelty = value(state, "novelty", profile.novelty)
    results = []
    for seed in DESTINATIONS:
        d = dict(seed)
        if any(a in d["name"].lower() for a in avoid):
            continue
        # An optional activity can be omitted; avoiding trekking doesn't exclude
        # every mountain destination that also happens to offer trekking.
        if any(a in {"beaches","mountains","forests"} and a in d["styles"] for a in avoid):
            continue
        d["styles"] = [s for s in d["styles"] if s not in avoided_styles]
        km = approximate_road_km(value(state, "origin", ""), d)
        if km and km < 40:
            continue
        d["distance_km"] = km
        d["travel_hours"] = round(km/45+km/180*.3, 1) if km else None
        d["distance_basis"] = "Estimated one-way road distance from town centres; not a verified route."
        budget = budget_for(state, d)
        d["budget"] = budget
        match = sorted(styles.intersection(d["styles"]))
        visits = history["visits"].get(d["name"], 0)
        recent = history["recent"].get(d["name"], 0)
        budget_fit = not budget["over_budget"]
        day_limit = value(state, "maximum_daily_driving", 300)
        driving = value(state,"transport_mode","mixed") in {"ride","roadtrip"}
        distance_limit = day_limit if driving else max(200,days*200)
        time_fit = km is not None and km * (2 if days == 1 else 1) <= distance_limit and days <= d.get("maximum_days",30)
        score = 30 + 20*budget_fit + 15*time_fit + min(20, 5*sum(weights.get(s,1) for s in match))
        score += (12 if not visits else -min(12, recent*6)) if novelty == "mostly_new" else (12 if visits else 0) if novelty == "mostly_familiar" else (4 if not recent else 0)
        if km:
            score -= min(35, max(0, km-300)/40)
        if days > d.get("maximum_days",30):
            score -= 8*(days-d["maximum_days"])
        rating = history["ratings"].get(d["name"])
        score += 5 if rating == "loved" else -10 if rating == "disliked" else 0
        destination_preference = profile.preferences.get("destination:"+d["name"], {})
        if destination_preference.get("value") is False:
            score -= 8 * destination_preference.get("confidence", .5)
        disliked_styles = [s for s in d["styles"] if profile.preferences.get(s, {}).get("value") is False]
        score -= min(20, len(disliked_styles)*5)
        reasons = ["Expected estimate fits your budget." if budget_fit else "A lower-cost stay or shorter trip may be needed.",
                   "Fits your available duration under these travel assumptions." if time_fit else "Travel distance/time needs closer review."]
        if match:
            reasons.append("Matches: " + ", ".join(match) + ".")
        if visits:
            reasons.append(f"You have {visits} recorded visit(s), {recent} within the last year; novelty setting: {novelty.replace('_', ' ')}.")
        else:
            reasons.append("No visit found in your saved trips, logs or photo locations; this is not proof you have never been.")
        d.update(score=round(score), fit="Strong fit" if score >= 75 else "Worth considering" if score >= 55 else "Needs adjustments",
                 why=reasons, novelty="Previously recorded" if visits else "New in your records",
                 factors={"Budget": "Within estimate" if budget_fit else "Over target", "Time": "Good" if time_fit else "Review travel time",
                          "Preferences": ", ".join(match) or "Open to discovery", "Novelty": novelty.replace("_", " "),
                          "Weather": "Unknown", "Roads / restrictions": "Unverified", "Stay availability": "Unverified",
                          "Photography": "Suggested" if "photography" in d["styles"] else "Not assessed"},
                 weather={"summary": "Live forecast not checked yet.", "confidence": "UNKNOWN"},
                 issues=[d["caution"], "Stay prices, permits, road access and opening hours are not yet verified."], sources=[])
        results.append(d)
    return sorted(results, key=lambda d: -d["score"])[:limit]
