"""Local intent enrichment: public search slots, explicit followups and constraints."""
import re
import math
from rest_framework.exceptions import ValidationError

from ..travel_catalog import lookup
from ..travel_discovery import fact, value


PROFILE_KEYS = {"origin", "transport_mode", "pillion", "maximum_daily_driving", "earliest_departure_hour",
    "avoid_expressways", "avoid_tolls", "highway_tolerance", "budget_type", "preferred_accommodation",
    "camping_interest", "trekking_interest", "food_preferences", "adventure_interest", "nightlife_interest",
    "weather_tolerance", "trip_pace", "preferred_trip_style", "luggage", "favorite_routes"}


def validate_preference(key, val):
    booleans = {"pillion","avoid_expressways","avoid_tolls","camping_interest","trekking_interest","adventure_interest","nightlife_interest","scenic_preference"}
    ranges = {"trip_duration":(1,30),"typical_duration":(1,30),"maximum_daily_driving":(20,1500),
              "daily_distance":(20,1500),"earliest_departure_hour":(0,23),"typical_spend":(0,100000000)}
    choices = {"transport_mode":{"ride","roadtrip","train","flight","bus","mixed"},
               "preferred_transport":{"ride","roadtrip","train","flight","bus","mixed"},
               "trip_pace":{"relaxed","balanced","active"},"budget_type":{"budget","balanced","premium"}}
    if key in booleans:
        if not isinstance(val,bool):
            raise ValidationError("This preference must be true or false.")
    elif key in ranges:
        low, high = ranges[key]
        if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val) or not low <= val <= high:
            raise ValidationError(f"This preference must be a number between {low} and {high}.")
    elif key in choices:
        if not isinstance(val,str) or val not in choices[key]:
            raise ValidationError("Choose a supported preference value.")
    elif key in {"preferred_trip_style","favorite_routes"}:
        if not isinstance(val,list) or len(val) > 12 or any(not isinstance(v,str) or len(v)>100 for v in val):
            raise ValidationError("Use a short list of travel preferences.")
    elif key == "origin":
        from .providers.web import public_place
        if not public_place(val):
            raise ValidationError("Use a city or place name, without personal information.")
    elif not isinstance(val,(bool,str,int,float)) or len(str(val))>160 or (isinstance(val,float) and not math.isfinite(val)):
        raise ValidationError("Use a short preference value.")
    return val


def augment(state, text):
    lower = text.casefold().strip()
    def put(key, val):
        state[key] = fact(val)
    # Explicit destination, including names outside the curated catalogue.
    match = re.search(r"\b(?:trip\s+(?:from\s+.+?\s+)?to|travel\s+to|visit|going\s+to|destination(?:\s+is)?|around|near)\s+([a-z][a-z .,'-]{1,100}?)(?=\s+(?:for|on|with|under|and|by|from|in\s+\d)\b|[.!?]|$)", lower)
    if not match:
        match = re.search(r"\bfrom\s+[a-z .'-]+?\s+to\s+([a-z][a-z .,'-]{1,100}?)(?=\s+(?:for|on|with|under|and|by)\b|[.!?]|$)", lower)
    if match:
        name = match[1].strip(" ,")
        if name not in {"me", "that", "there", "home"}:
            put("requested_destination", (lookup(name) or {}).get("name", name.title()))
    permit = re.search(r"\b(?:is|check)\s+([a-z][a-z '-]{2,80}?)\s+(?:open|closed|accessible)", lower)
    if permit:
        put("permit_place", permit[1].title())
    for field, pattern in (("avoid_expressways", r"expressways?|motorways?"), ("avoid_tolls", r"tolls?|toll roads?")):
        if re.search(r"(?:avoid|no|without)\s+"+pattern, lower):
            put(field, True)
        elif re.search(r"(?:allow|include|use)\s+"+pattern, lower):
            put(field, False)
    modes = [mode for pattern, mode in [(r"\bbike|motorcycle\b", "ride"), (r"\bcar\b", "roadtrip"),
                                         (r"\btrain\b", "train"), (r"\bbus\b", "bus"), (r"\bflight|fly\b", "flight")] if re.search(pattern, lower)]
    if len(modes) > 1 and re.search(r"\b(?:compare|vs|versus|or)\b", lower):
        put("compare_modes", modes)
        # The caller restores the selected transport; a comparison is not a switch.
    if "cheapest" in lower or "lowest budget" in lower:
        put("budget_type", "budget")
        put("sort_by", "cost")
    if any(w in lower for w in ("unexplored", "less explored", "hidden", "offbeat")):
        put("discover_places", True)
        put("preferred_trip_style", sorted(set(value(state,"preferred_trip_style",[])+["offbeat places"])))
    if any(w in lower for w in ("not visited", "haven't visited", "never visited")):
        put("only_new_places", True)
        put("novelty", "mostly_new")
    if "scenic" in lower:
        put("scenic_preference", True)
    for tolerance in ("avoid rain", "rain is okay", "avoid heat"):
        if tolerance in lower:
            put("weather_tolerance", tolerance)
    if "luggage" in lower:
        put("luggage", "Travelling with luggage; verify load capacity")
    if "relaxed" in lower or "slow pace" in lower:
        put("trip_pace", "relaxed")
    if "restaurant" in lower or "food options" in lower:
        put("find_restaurants", True)
    airports = re.search(r"\b([A-Z]{3})\s*(?:to|→|-)\s*([A-Z]{3})\b", text)
    if airports:
        put("origin_airport", airports[1])
        put("destination_airport", airports[2])
    categories = set(value(state,"research_categories",[]))
    for terms, category in [(r"weather|forecast|rain", "weather"), (r"hotel|stay|availability", "hotels"),
                            (r"flight|fly", "flights"), (r"train|rail", "trains"), (r"\bbus\b", "buses"),
                            (r"permit|permission|\bopen\b|closure", "permits"),
                            (r"discover|unexplored|camp|hidden|restaurant", "places"),
                            (r"route|expressway|toll", "routing")]:
        if re.search(terms, lower):
            categories.add(category)
    if categories:
        put("research_categories", sorted(categories))
    return state
