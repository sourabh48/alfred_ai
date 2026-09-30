from collections import Counter

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.mobility.models import BikeProfile, TravelPlan, TravelPreferenceProfile, TripLog, TripPhoto, UserDestinationHistory
from .travel_catalog import DESTINATIONS, approximate_road_km, lookup


def value(state, key, default=None):
    return state.get(key, {}).get("value", default)


def fact(value, source="user_message", confirmed=True, confidence=1.0):
    freshness = "ESTIMATED" if source in {"planning_assumption","assistant_proposal","approximate_user_duration"} else "USER_PROVIDED"
    return {"value": value, "source": source, "confidence": confidence, "confirmed_by_user": confirmed, "freshness":freshness}


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
    for row in UserDestinationHistory.objects.filter(user=user):
        if "visited" in row.events:
            visits[row.name] = max(visits[row.name],1)
    return {"visits": dict(visits), "recent": dict(recent), "ratings": ratings}


def budget_for(state, destination, *, relaxed_days=0):
    from .travel.costs import calculate_budget
    return calculate_budget(state, destination, relaxed_days=relaxed_days)


def candidates_for(user, state, limit=3, *, destinations=None, origin_coordinates=None):
    profile = profile_for(user)
    history = history_for(user)
    memory = {row.name.casefold():row for row in UserDestinationHistory.objects.filter(user=user)}
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
    for seed in (DESTINATIONS if destinations is None else destinations):
        d = dict(seed)
        d.setdefault("source_freshness", "STATIC_REFERENCE")
        record = memory.get(d["name"].casefold())
        explicitly_requested = str(value(state,"requested_destination","")).casefold() == d["name"].casefold()
        if not explicitly_requested and ((record and "rejected" in record.events) or (value(state,"only_new_places") and history["visits"].get(d["name"]))):
            continue
        if any(a in d["name"].lower() for a in avoid):
            continue
        # An optional activity can be omitted; avoiding trekking doesn't exclude
        # every mountain destination that also happens to offer trekking.
        if any(a in {"beaches","mountains","forests"} and a in d["styles"] for a in avoid):
            continue
        d["styles"] = [s for s in d["styles"] if s not in avoided_styles]
        km = approximate_road_km(value(state, "origin", ""), d, origin_coordinates)
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
        if record and not explicitly_requested:
            score -= min(15,record.shown_count*3)
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
