from datetime import timedelta
from hashlib import sha256
import json
import os
from urllib.parse import urlsplit

from alfred_ai.services.public_http import normalized_link

from .base import Provider, ProviderError, number, request_json


def _coordinate(value):
    if not isinstance(value,(list,tuple)) or len(value) not in (2,3):
        raise ValueError('Invalid coordinate shape.')
    point=[number(value[0],low=-180,high=180),number(value[1],low=-90,high=90)]
    if len(value)==3: number(value[2])
    return point


class OpenRouteService(Provider):
    name = "openrouteservice"
    category = "routing"
    source_url = "https://openrouteservice.org/"
    attribution = "© openrouteservice by HeiGIT, CC BY-SA 4.0 | Data © OpenStreetMap contributors"
    ttl = timedelta(days=5)
    version = 3  # Route identities and alternative requests need separate cache entries.
    allowed_parameters = {"start", "end", "mode", "avoid_expressways", "avoid_tolls", "preference", "alternatives"}

    def unavailable_reason(self):
        return "" if os.getenv("TRAVEL_ORS_API_KEY") else "missing_TRAVEL_ORS_API_KEY"

    def fetch(self, p):
        mode = p.get("mode", "car")
        if mode not in {"car", "roadtrip", "motorcycle", "ride", "walking"}:
            raise ProviderError("transport_profile_unsupported")
        profile = "foot-walking" if mode == "walking" else "driving-car"
        coordinates = [_coordinate(point) for point in (p["start"],p["end"])]
        avoid = []
        if p.get("avoid_expressways") and profile == "driving-car":
            avoid.append("highways")
        if p.get("avoid_tolls") and profile == "driving-car":
            avoid.append("tollways")
        preference = p.get("preference", "recommended")
        if preference not in {"recommended", "fastest", "shortest"}:
            raise ProviderError("unsupported_route_preference")
        body = {"coordinates": coordinates, "preference": preference, "instructions": False,
                "elevation": True, "extra_info": ["steepness", "surface", "waytype"]}
        if type(p.get("alternatives", False)) is not bool:
            raise ProviderError("unsupported_route_alternatives")
        if p.get("alternatives"):
            body["alternative_routes"] = {"target_count": 3, "share_factor": 0.6, "weight_factor": 1.4}
        if avoid:
            body["options"] = {"avoid_features": avoid}
        return request_json("POST", f"https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson",
            json=body, headers={"Authorization": os.environ["TRAVEL_ORS_API_KEY"], "Content-Type": "application/json"})

    def normalize(self, raw, p):
        routes = []
        for feature in raw["features"][:3]:
            props, geometry = feature["properties"], feature["geometry"]
            if (geometry["type"] != "LineString" or not isinstance(geometry["coordinates"],(list,tuple))
                    or len(geometry["coordinates"]) < 2):
                raise ProviderError("malformed_response")
            coords = [_coordinate(point) for point in geometry["coordinates"]]
            routes.append({"distance_km": round(number(props["summary"]["distance"], low=0)/1000, 1),
                "duration_hours": round(number(props["summary"]["duration"], low=0)/3600, 2),
                "geometry": {"type": "LineString", "coordinates": coords}, "extras": props.get("extras", {}),
                "ascent_m": props.get("ascent"), "descent_m": props.get("descent"),
                "profile": "foot-walking" if p.get("mode") == "walking" else "driving-car",
                "motorcycle_legal": "UNKNOWN", "closures": "UNKNOWN", "traffic": "UNKNOWN",
                "constraints_requested": {"avoid_expressways": bool(p.get("avoid_expressways")), "avoid_tolls": bool(p.get("avoid_tolls"))},
                "note": "Car routing is only a reference for motorcycles; verify vehicle legality and current closures. Highway avoidance is broader than expressway avoidance."})
        if not routes:
            raise ProviderError("no_route")
        distinct = {}
        for route in routes:
            route["route_id"] = sha256(json.dumps(route, sort_keys=True, allow_nan=False).encode()).hexdigest()
            geometry = json.dumps(route["geometry"], sort_keys=True)
            distinct.setdefault(geometry, route)
        return {"routes": list(distinct.values())}


def decode_polyline6(encoded):
    """Valhalla's encoded shape (Google polyline algorithm, 1e6 precision) as [lon, lat] points."""
    points, index, lat, lon = [], 0, 0, 0
    while index < len(encoded):
        deltas = []
        for _ in range(2):
            shift = result = 0
            while True:
                if index >= len(encoded):
                    raise ProviderError("malformed_response")
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            deltas.append(~(result >> 1) if result & 1 else result >> 1)
        lat, lon = lat + deltas[0], lon + deltas[1]
        points.append(_coordinate([lon / 1e6, lat / 1e6]))
    return points


class ValhallaRouting(Provider):
    """Road-network routing with a real motorcycle profile (idea from TREK pin d4da05bb, independently written).

    Off until the owner sets TRAVEL_VALHALLA_URL, because each request sends the trip's start and end points to that
    server. The FOSSGIS public server (https://valhalla1.openstreetmap.de) allows light personal use: one request a
    second with an identifying User-Agent.
    """
    name = "valhalla"
    category = "routing"
    source_url = "https://www.openstreetmap.org/copyright"
    attribution = "Routing by Valhalla | Data © OpenStreetMap contributors, ODbL"
    ttl = timedelta(days=5)
    min_interval = 1
    limits = {"minute": 10, "hour": 60, "day": 200, "month": 2000}
    allowed_parameters = OpenRouteService.allowed_parameters
    COSTING = {"motorcycle": "motorcycle", "ride": "motorcycle", "car": "auto", "roadtrip": "auto", "walking": "pedestrian"}

    @property
    def cache_partition(self):
        return sha256(os.getenv("TRAVEL_VALHALLA_URL", "").encode()).hexdigest()

    def unavailable_reason(self):
        endpoint = os.getenv("TRAVEL_VALHALLA_URL", "")
        if not endpoint:
            return "missing_TRAVEL_VALHALLA_URL"
        safe = normalized_link(endpoint)
        return "" if safe and not urlsplit(safe).fragment and not urlsplit(safe).query else "invalid_TRAVEL_VALHALLA_URL"

    def fetch(self, p):
        costing = self.COSTING.get(p.get("mode", "car"))
        if costing is None:
            raise ProviderError("transport_profile_unsupported")
        if p.get("preference", "recommended") not in {"recommended", "fastest", "shortest"}:
            raise ProviderError("unsupported_route_preference")
        if type(p.get("alternatives", False)) is not bool:
            raise ProviderError("unsupported_route_alternatives")
        start, end = (_coordinate(point) for point in (p["start"], p["end"]))
        options = {}
        if costing != "pedestrian":
            # 0 asks Valhalla to avoid motorways/trunk roads and tolls where any other road exists; it is not a ban.
            options = {"use_highways": 0.0 if p.get("avoid_expressways") else 0.5, "use_tolls": 0.0 if p.get("avoid_tolls") else 0.5}
            if p.get("preference") == "shortest":
                options["shortest"] = True
        body = {"locations": [{"lon": start[0], "lat": start[1]}, {"lon": end[0], "lat": end[1]}], "costing": costing,
                "costing_options": {costing: options}, "units": "kilometers", "directions_type": "none"}
        if p.get("alternatives"):
            body["alternates"] = 2
        return request_json("POST", os.environ["TRAVEL_VALHALLA_URL"].rstrip("/") + "/route", json=body,
            headers={"User-Agent": "ALFRED-travel/1.2 (+https://github.com/sourabh48/alfred_ai)", "Content-Type": "application/json"})

    def normalize(self, raw, p):
        costing = self.COSTING.get(p.get("mode", "car"))
        trips = [raw.get("trip")] + [item.get("trip") for item in raw.get("alternates") or [] if isinstance(item, dict)]
        routes = []
        for trip in [trip for trip in trips if isinstance(trip, dict)][:3]:
            coords = [point for leg in trip.get("legs") or [] for point in decode_polyline6(str(leg.get("shape") or ""))]
            if len(coords) < 2:
                raise ProviderError("malformed_response")
            summary = trip.get("summary") or {}
            avoided = {"expressways": not summary.get("has_highway"), "tolls": not summary.get("has_toll")}
            route = {"distance_km": round(number(summary["length"], low=0), 1), "duration_hours": round(number(summary["time"], low=0) / 3600, 2),
                "geometry": {"type": "LineString", "coordinates": coords}, "extras": {}, "ascent_m": None, "descent_m": None, "profile": costing,
                # Valhalla's motorcycle profile follows OpenStreetMap access tags (motorcycle=no and similar); tags can be missing or old.
                "motorcycle_legal": "OSM_ACCESS_TAGS" if costing == "motorcycle" else "UNKNOWN", "closures": "UNKNOWN", "traffic": "UNKNOWN",
                "constraints_requested": {"avoid_expressways": bool(p.get("avoid_expressways")), "avoid_tolls": bool(p.get("avoid_tolls"))},
                "constraints_met": {name: avoided[name] for name, asked in (("expressways", p.get("avoid_expressways")), ("tolls", p.get("avoid_tolls"))) if asked},
                "note": ("Motorcycle route on mapped roads that allow motorcycles in OpenStreetMap; check signs, closures and road condition before riding."
                         if costing == "motorcycle" else "Road route; closures, traffic and motorcycle legality are unverified.")}
            routes.append(route)
        if not routes:
            raise ProviderError("no_route")
        distinct = {}
        for route in routes:
            route["route_id"] = sha256(json.dumps(route, sort_keys=True, allow_nan=False).encode()).hexdigest()
            distinct.setdefault(json.dumps(route["geometry"], sort_keys=True), route)
        return {"routes": list(distinct.values())}


GOOGLE_KEY = "TRAVEL_GOOGLE_MAPS_API_KEY"


class GoogleRoutes(Provider):
    """Paid fallback, used only after the free routers fail; capped well under Google's free monthly use.

    Google's terms forbid its content on a non-Google map, so no line is returned: distance and time only.
    """
    name = "google_routes"
    category = "routing"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google"
    # shortcut: Google limits storing its content; an hour keeps a planning session usable. Revisit if plans must keep it.
    ttl = timedelta(hours=1)
    limits = {"minute": 5, "hour": 20, "day": 40, "month": 400}
    allowed_parameters = OpenRouteService.allowed_parameters
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
                "note": "Google fallback: distance and time only; the line is not drawn on the OpenStreetMap map. Check signs and closures."}
            route["route_id"] = sha256(json.dumps(route, sort_keys=True, allow_nan=False).encode()).hexdigest()
            routes.append(route)
        if not routes:
            raise ProviderError("no_route")
        return {"routes": list({route["route_id"]: route for route in routes}.values())}


def routing_chain(mode):
    """Free routers first, Google last. Motorcycles start with Valhalla, the only free router with a motorcycle profile."""
    free = [ValhallaRouting(), OpenRouteService()] if mode in {"motorcycle", "ride"} else [OpenRouteService(), ValhallaRouting()]
    return [*free, GoogleRoutes()]
