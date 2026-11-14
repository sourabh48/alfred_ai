"""Offline country and state matching from the bundled dr5hn world dataset (ODbL-1.0).

No network calls: names and coordinates are matched against static/vendor/world/world.json.
"""
import json
import re
import unicodedata
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt

from django.conf import settings

WORLD_FILE = settings.BASE_DIR / "static" / "vendor" / "world" / "world.json"
MAX_CENTROID_KM = 1000  # beyond this the point is open sea, not a state


def _key(text):
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.casefold()).split())


@lru_cache(maxsize=1)
def _world():
    data = json.loads(WORLD_FILE.read_text(encoding="utf-8"))
    countries = {row[0]: {"code": row[0], "name": row[2], "flag": row[3]} for row in data["countries"]}
    by_name = {_key(row[2]): row[0] for row in data["countries"]}
    by_iso3 = {row[1]: row[0] for row in data["countries"]}
    states, state_names = [], {}
    for country, code, name, lat, lng in data["states"]:
        state = {"country": country, "code": code, "name": name, "lat": lat, "lng": lng}
        states.append(state)
        state_names.setdefault(_key(name), []).append(state)
    return countries, by_name, by_iso3, states, state_names


def _result(country_code, state=None):
    countries = _world()[0]
    country = countries.get(country_code)
    if not country:
        return None
    return {
        "country_code": country["code"], "country": country["name"], "flag": country["flag"],
        "state_code": state["code"] if state else "", "state": state["name"] if state else "",
    }


def match_text(text):
    """Match a free-text place such as "Manali, Himachal Pradesh" or "Paris, France"."""
    _, by_name, by_iso3, _, state_names = _world()
    raw_parts = [part.strip() for part in re.split(r"[,;/|\n]+", str(text or "")) if part.strip()]
    if not raw_parts:
        return None
    parts = [(raw, _key(raw)) for raw in raw_parts]
    if len(parts) > 1:
        parts.append((str(text), _key(text)))
    country, country_part = None, None
    for raw, key in reversed(parts):
        country = by_name.get(key) or (by_iso3.get(raw) if raw.isupper() else None)
        if country:
            country_part = key
            break
    for raw, key in reversed(parts):
        if key == country_part:
            continue
        candidates = [s for s in state_names.get(key, []) if not country or s["country"] == country]
        if len(candidates) == 1:  # an ambiguous name such as "Punjab" with no country stays unmatched
            return _result(candidates[0]["country"], candidates[0])
    return _result(country) if country else None


def match_point(latitude, longitude):
    """Nearest state centroid to a coordinate."""
    # shortcut: centroid distance, not boundaries, so points near a border can land in the neighbour; use polygons if that matters.
    if latitude is None or longitude is None:
        return None
    lat, lng = radians(float(latitude)), radians(float(longitude))
    best, best_km = None, MAX_CENTROID_KM
    for state in _world()[3]:
        if state["lat"] is None or state["lng"] is None:
            continue
        b, c = radians(state["lat"]), radians(state["lng"])
        km = 6371 * 2 * asin(sqrt(sin((b - lat) / 2) ** 2 + cos(lat) * cos(b) * sin((c - lng) / 2) ** 2))
        if km < best_km:
            best, best_km = state, km
    return _result(best["country"], best) if best else None


def match_place(text="", latitude=None, longitude=None):
    """Prefer an exact name match; fall back to coordinates."""
    return match_text(text) or match_point(latitude, longitude)


def visited_regions(plans, logs):
    """Countries and states reached: every trip log, plus completed or ongoing plans."""
    places = [match_place(log.location_name, log.latitude, log.longitude) or match_text(log.travel_plan.destination) for log in logs]
    places += [match_text(plan.destination) for plan in plans if plan.status in {"completed", "on_trip"}]
    places = [place for place in places if place]
    return {
        "countries": len({place["country_code"] for place in places}),
        "states": len({(place["country_code"], place["state"]) for place in places if place["state"]}),
    }
