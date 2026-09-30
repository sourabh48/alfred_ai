from datetime import timedelta
import os

from .base import Provider, ProviderError, number, request_json


class OpenRouteService(Provider):
    name = "openrouteservice"
    category = "routing"
    source_url = "https://openrouteservice.org/"
    attribution = "© openrouteservice by HeiGIT, CC BY-SA 4.0 | Data © OpenStreetMap contributors"
    ttl = timedelta(days=5)
    allowed_parameters = {"start", "end", "mode", "avoid_expressways", "avoid_tolls", "preference"}

    def unavailable_reason(self):
        return "" if os.getenv("TRAVEL_ORS_API_KEY") else "missing_TRAVEL_ORS_API_KEY"

    def fetch(self, p):
        mode = p.get("mode", "car")
        if mode not in {"car", "roadtrip", "motorcycle", "ride", "walking"}:
            raise ProviderError("transport_profile_unsupported")
        profile = "foot-walking" if mode == "walking" else "driving-car"
        coordinates = [[number(c[0], low=-180, high=180), number(c[1], low=-90, high=90)] for c in (p["start"], p["end"])]
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
        if avoid:
            body["options"] = {"avoid_features": avoid}
        return request_json("POST", f"https://api.heigit.org/openrouteservice/v2/directions/{profile}/geojson",
            json=body, headers={"Authorization": os.environ["TRAVEL_ORS_API_KEY"], "Content-Type": "application/json"})

    def normalize(self, raw, p):
        routes = []
        for feature in raw["features"][:3]:
            props, geometry = feature["properties"], feature["geometry"]
            if geometry["type"] != "LineString" or len(geometry["coordinates"]) < 2:
                raise ProviderError("malformed_response")
            coords = [[number(c[0], low=-180, high=180), number(c[1], low=-90, high=90)] for c in geometry["coordinates"]]
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
        return {"routes": routes}
