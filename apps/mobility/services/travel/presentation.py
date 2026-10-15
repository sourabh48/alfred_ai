"""Age saved evidence at read time; polling a saved session is never a live call."""
from copy import deepcopy

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from alfred_ai.services.public_http import normalized_link
from .providers.base import ProviderResult


def invalidate_trip_dates(destination):
    """Keep date-independent evidence; historical research rows remain unchanged."""
    result = deepcopy(destination)
    volatile = {"weather", "hotels", "flights", "trains", "buses", "permits", "web", "budget"}
    for key, category in (("weather", "weather"), ("hotels", "hotels"), ("flights", "flights"),
                          ("trains", "trains"), ("buses", "buses"), ("permit", "permits")):
        old = result.get(key + "_result", {})
        result[key + "_result"] = ProviderResult(old.get("provider", "unknown"), category,
            status="needs_refresh", error="trip_dates_changed").as_dict()
    result["weather"] = {"summary": "Dates changed. Recheck weather for the revised window.", "confidence": "UNKNOWN"}
    if result.get("weather_proposals") and "score" in result:
        result["score"] += 8
    result["weather_proposals"] = []
    if "factors" in result:
        result["factors"]["Weather"] = "Unknown"
    result["web_research"] = []
    result["selected_price_snapshots"] = []
    if result.get("budget"):
        result["budget"]["verified_prices"] = []
    for comparison in result.get("mode_comparison", []):
        comparison.get("budget", {})["verified_prices"] = []
    result["sources"] = [s for s in result.get("sources", [])
                         if s.get("data_type") not in volatile | {"stay", "restrictions"}]
    quality = result.get("quality", {})
    for key in ("verified", "research_leads"):
        quality[key] = [c for c in quality.get(key, []) if c not in volatile]
    for key in ("freshness", "unavailable"):
        quality[key] = [c for c in quality.get(key, []) if c.get("category") not in volatile]
    quality["recheck"] = ["Dates changed; refresh volatile research"]
    result["quality"] = quality
    if result.get("map"):
        result["map"]["features"] = [f for f in result["map"].get("features", [])
                                     if f.get("properties", {}).get("kind") != "hotel"]
    return result


def age_saved_facts(payload):
    result = deepcopy(payload)
    now = timezone.now()

    def walk(node):
        if isinstance(node,list):
            for item in node:
                walk(item)
        elif isinstance(node,dict):
            if node.get("freshness") == "ESTIMATE":
                node["freshness"] = "ESTIMATED"  # Read older saved plans safely.
            for key in ("source_url","booking_url","url"):
                if key in node and node[key]:
                    node[key] = normalized_link(node[key])
            expiry = parse_datetime(str(node.get("expires_at") or node.get("valid_until") or ""))
            if expiry and timezone.is_aware(expiry) and expiry <= now:
                node.update(freshness="CACHED",stale=True,confidence="UNKNOWN")
                if "availability" in node:
                    node["availability"] = "UNKNOWN; cached offer expired"
                if "payload" in node:
                    for option in node["payload"].get("options",[]):
                        option["availability"] = "UNKNOWN; cached offer expired"
            elif node.get("freshness") == "LIVE":
                node["freshness"] = "RECENTLY_VERIFIED"
            for item in list(node.values()):
                if isinstance(item,(dict,list)):
                    walk(item)
    walk(result)
    for d in [*result.get("candidates",[]),result.get("itinerary",{})]:
        if d.get("weather_result",{}).get("stale"):
            d.setdefault("weather",{}).update(summary="Cached forecast has expired. Refresh before relying on it.",confidence="UNKNOWN",freshness="CACHED")
            d["weather_proposals"] = []
        if d.get("quality"):
            d["quality"]["verified"] = [key for key in d["quality"].get("verified",[]) if not any(
                r.get("category") == key and r.get("stale") for name,r in d.items() if name.endswith("_result") and isinstance(r,dict))]
    return result
