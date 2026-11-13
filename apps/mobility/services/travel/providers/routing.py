from datetime import timedelta
from hashlib import sha256
import json
import os

from .base import Provider, ProviderError, number, request_json


def _coordinate(value):
    if not isinstance(value,(list,tuple)) or len(value) not in (2,3):
        raise ValueError('Invalid coordinate shape.')
    point=[number(value[0],low=-180,high=180),number(value[1],low=-90,high=90)]
    if len(value)==3: number(value[2])
    return point


GOOGLE_KEY = "TRAVEL_GOOGLE_MAPS_API_KEY"


class GoogleRoutes(Provider):
    """Routes from the Google Routes API, the only router (owner decision 2026-11-14).

    Distance and time only: the offline country map is not a Google map, and Google's terms forbid its route there.
    """
    name = "google_routes"
    category = "routing"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google"
    # shortcut: Google limits storing its content; an hour keeps a planning session usable. Revisit if plans must keep it.
    ttl = timedelta(hours=1)
    limits = {"minute": 10, "hour": 60, "day": 200, "month": 3000}
    allowed_parameters = {"start", "end", "mode", "avoid_expressways", "avoid_tolls", "preference", "alternatives"}
    MODES = {"motorcycle": "TWO_WHEELER", "ride": "TWO_WHEELER", "car": "DRIVE", "roadtrip": "DRIVE", "walking": "WALK"}

    def unavailable_reason(self):
        return "" if os.getenv(GOOGLE_KEY) else "missing_TRAVEL_GOOGLE_MAPS_API_KEY"

    def fetch(self, p):
        travel_mode = self.MODES.get(p.get("mode", "car"))
        if travel_mode is None:
            raise ProviderError("transport_profile_unsupported")
        if type(p.get("alternatives", False)) is not bool:
            raise ProviderError("unsupported_route_alternatives")
        start, end = (_coordinate(point) for point in (p["start"], p["end"]))
        body = {"origin": {"location": {"latLng": {"latitude": start[1], "longitude": start[0]}}},
                "destination": {"location": {"latLng": {"latitude": end[1], "longitude": end[0]}}},
                "travelMode": travel_mode, "computeAlternativeRoutes": bool(p.get("alternatives"))}
        if travel_mode != "WALK":
            body["routeModifiers"] = {"avoidHighways": bool(p.get("avoid_expressways")), "avoidTolls": bool(p.get("avoid_tolls"))}
        return request_json("POST", "https://routes.googleapis.com/directions/v2:computeRoutes", json=body,
            headers={"X-Goog-Api-Key": os.environ[GOOGLE_KEY], "X-Goog-FieldMask": "routes.distanceMeters,routes.duration,routes.description",
                     "Content-Type": "application/json"})

    def normalize(self, raw, p):
        travel_mode = self.MODES.get(p.get("mode", "car"))
        routes = []
        for item in (raw.get("routes") or [])[:3]:
            seconds = str(item.get("duration") or "")
            if not seconds.endswith("s"):
                raise ProviderError("malformed_response")
            route = {"distance_km": round(number(item["distanceMeters"], low=0) / 1000, 1),
                "duration_hours": round(number(seconds[:-1], low=0) / 3600, 2), "geometry": None, "extras": {},
                "ascent_m": None, "descent_m": None, "profile": f"google-{travel_mode.lower()}", "via": str(item.get("description") or "")[:120],
                "motorcycle_legal": "UNKNOWN", "closures": "UNKNOWN", "traffic": "UNKNOWN",
                "constraints_requested": {"avoid_expressways": bool(p.get("avoid_expressways")), "avoid_tolls": bool(p.get("avoid_tolls"))},
                "note": "Google route: distance and time only. Check signs and closures."}
            route["route_id"] = sha256(json.dumps(route, sort_keys=True, allow_nan=False).encode()).hexdigest()
            routes.append(route)
        if not routes:
            raise ProviderError("no_route")
        return {"routes": list({route["route_id"]: route for route in routes}.values())}


def routing_chain(mode):
    return [GoogleRoutes()]
