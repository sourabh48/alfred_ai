from copy import deepcopy
from math import asin, cos, radians, sin, sqrt
import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.mobility.models import UserDestinationHistory


def place_key(place):
    return str(place.get("id") or "name:"+re.sub(r"\s+", " ", place["name"].strip().casefold()))[:200]


def remember(user, place, action):
    if action not in {"shown", "accepted", "rejected", "visited", "saved", "skipped"}:
        raise ValidationError("Unsupported place action.")
    with transaction.atomic():
        record, _ = UserDestinationHistory.objects.select_for_update().get_or_create(
            user=user, place_key=place_key(place), defaults={"name": place["name"][:200]})
        record.events[action] = timezone.now().isoformat()
        if action == "shown":
            record.shown_count += 1
        record.save(update_fields=["events", "shown_count", "updated_at"])
    return record


def km_between(a, b):
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    return 6371*2*asin(min(1, sqrt(sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2)))


def rank_places(user, places, *, interests=(), route=None, visited_names=(), weather_risks=(), only_new=False, limit=12):
    records = list(UserDestinationHistory.objects.filter(user=user))
    memory = {row.place_key: row for row in records}
    by_name = {row.name.casefold(): row for row in records}
    visited = {str(name).casefold() for name in visited_names}
    seen_ids, seen_places, ranked = set(), [], []
    for original in places:
        place = deepcopy(original)
        key = place_key(place)
        if key in seen_ids or any(p["name"].casefold() == place["name"].casefold() and km_between((p["lat"],p["lon"]),(place["lat"],place["lon"])) < .15 for p in seen_places):
            continue
        seen_ids.add(key)
        seen_places.append(place)
        record = memory.get(key) or by_name.get(place["name"].casefold())
        events = record.events if record else {}
        if "rejected" in events or (only_new and ("visited" in events or place["name"].casefold() in visited)):
            continue
        if place.get("access") in {"no", "private"}:
            continue
        score, reasons = 40, []
        category = place.get("category", "")
        if category in interests or (category == "viewpoint" and "photography" in interests) or (category == "camping" and "camping" in interests):
            score += 20
            reasons.append("Matches your interests")
        if record:
            score -= min(25, record.shown_count*5)
            if "skipped" in events:
                score -= 15
        else:
            score += 10
            reasons.append("Newly discovered by ALFRED in your records")
        if route:
            samples = route[::max(1, len(route)//200)] + [route[-1]]
            distance = min(km_between((place["lat"],place["lon"]),(c[1],c[0])) for c in samples)
            place["route_distance_km"] = round(distance, 1)
            place["route_distance_basis"] = "Straight-line distance to sampled route points; not road detour distance"
            score -= min(20, distance)
            if distance > 2:
                reasons.append("Off the main route; verify access and detour time")
        if weather_risks and category in {"viewpoint", "camping", "attraction"}:
            score -= 15
            reasons.append("Outdoor suitability needs a weather check")
        # No review counts or popularity are invented from missing metadata.
        place.update(discovery_score=round(score, 1), reasons=reasons,
                     description="Locally interesting; popularity is not verified.",
                     opening_status="UNKNOWN", popularity="UNKNOWN",
                     checks=["Confirm opening hours, permission, seasonal access and current conditions."])
        ranked.append(place)
    return sorted(ranked, key=lambda p: -p["discovery_score"])[:limit]
