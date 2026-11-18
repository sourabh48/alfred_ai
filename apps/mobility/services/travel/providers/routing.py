from datetime import timedelta
from decimal import Decimal
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
    allowed_parameters = {"start", "end", "mode", "avoid_expressways", "avoid_tolls", "preference", "alternatives", "via"}
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
        if p.get("via") is not None:
            if body["computeAlternativeRoutes"]:  # Google computes no alternatives through a stop
                raise ProviderError("unsupported_route_alternatives")
            via = _coordinate(p["via"])
            body["intermediates"] = [{"location": {"latLng": {"latitude": via[1], "longitude": via[0]}}}]
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


class GoogleTransit(Provider):
    """Public transport door to door from the Google Routes API, TRANSIT mode (owner approval 2026-11-18).

    Lines, stops, times and Google's fare estimate when it has one. The owner's two addresses go to Google; nothing else.
    """
    name = "google_transit"
    category = "transit"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google"
    ttl = timedelta(minutes=30)  # timetables change; Google limits storing its content
    limits = {"minute": 5, "hour": 30, "day": 100, "month": 1500}
    allowed_parameters = {"origin", "destination", "departure"}
    FIELDS = ("routes.duration,routes.distanceMeters,routes.travelAdvisory.transitFare,routes.legs.steps.travelMode,"
              "routes.legs.steps.staticDuration,routes.legs.steps.distanceMeters,routes.legs.steps.transitDetails,"
              "routes.legs.steps.navigationInstruction.instructions")

    def unavailable_reason(self):
        return "" if os.getenv(GOOGLE_KEY) else "missing_TRAVEL_GOOGLE_MAPS_API_KEY"

    def fetch(self, p):
        body = {"origin": {"address": str(p["origin"])[:200]}, "destination": {"address": str(p["destination"])[:200]},
                "travelMode": "TRANSIT", "computeAlternativeRoutes": True}
        if p.get("departure"):
            body["departureTime"] = p["departure"]
        return request_json("POST", "https://routes.googleapis.com/directions/v2:computeRoutes", json=body,
            headers={"X-Goog-Api-Key": os.environ[GOOGLE_KEY], "X-Goog-FieldMask": self.FIELDS, "Content-Type": "application/json"})

    @staticmethod
    def _minutes(value):
        value = str(value or "")
        return round(number(value[:-1], low=0) / 60) if value.endswith("s") else None

    def normalize(self, raw, p):
        routes = []
        for item in (raw.get("routes") or [])[:3]:
            steps = []
            for step in (s for leg in item.get("legs") or [] for s in leg.get("steps") or []):
                transit = step.get("transitDetails") or {}
                if transit:
                    line, stops = transit.get("transitLine") or {}, transit.get("stopDetails") or {}
                    steps.append({"mode": "TRANSIT", "line": str(line.get("nameShort") or line.get("name") or "")[:80],
                        "vehicle": str(((line.get("vehicle") or {}).get("name") or {}).get("text") or "")[:40],
                        "agency": str(((line.get("agencies") or [{}])[0]).get("name") or "")[:80],
                        "headsign": str(transit.get("headsign") or "")[:80],
                        "from": str((stops.get("departureStop") or {}).get("name") or "")[:120],
                        "to": str((stops.get("arrivalStop") or {}).get("name") or "")[:120],
                        "depart": str(stops.get("departureTime") or "")[:30], "arrive": str(stops.get("arrivalTime") or "")[:30],
                        "stops": int(transit.get("stopCount") or 0), "minutes": self._minutes(step.get("staticDuration"))})
                elif steps and steps[-1]["mode"] == "WALK":
                    steps[-1]["minutes"] = (steps[-1]["minutes"] or 0) + (self._minutes(step.get("staticDuration")) or 0)
                else:
                    steps.append({"mode": "WALK", "minutes": self._minutes(step.get("staticDuration")),
                                  "note": str((step.get("navigationInstruction") or {}).get("instructions") or "")[:160]})
            fare = (item.get("travelAdvisory") or {}).get("transitFare") or {}
            fare_text = None
            if fare.get("currencyCode"):
                amount = Decimal(str(fare.get("units") or 0)) + Decimal(int(fare.get("nanos") or 0)) / Decimal(10 ** 9)
                fare_text = {"amount": str(amount.quantize(Decimal("0.01"))), "currency": str(fare["currencyCode"])[:3]}
            if not any(s["mode"] == "TRANSIT" for s in steps):
                continue  # walking only is not a public-transport answer
            routes.append({"minutes": self._minutes(item.get("duration")), "distance_km": round(number(item.get("distanceMeters") or 0, low=0) / 1000, 1),
                           "fare": fare_text, "steps": steps[:30]})
        if not routes:
            raise ProviderError("no_route")
        return {"routes": routes, "note": "Google's timetable and fare estimate. Check the operator before you travel."}
