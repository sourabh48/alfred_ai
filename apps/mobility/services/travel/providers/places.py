from datetime import timedelta
import os
import hashlib
from urllib.parse import urlparse

from .base import Provider, ProviderError, number, request_json


class OverpassPlaces(Provider):
    name = "overpass"
    category = "places"
    source_url = "https://www.openstreetmap.org/copyright"
    attribution = "© OpenStreetMap contributors, ODbL; opening/access tags may be outdated"
    ttl = timedelta(days=7)
    min_interval = 1
    allowed_parameters = {"latitude", "longitude", "radius_m", "categories"}
    filters = {"attraction": 'tourism~"attraction|viewpoint|museum"', "camping": 'tourism="camp_site"',
               "fuel": 'amenity="fuel"', "hospital": 'amenity="hospital"', "restaurant": 'amenity="restaurant"',
               "service": 'shop~"motorcycle_repair|car_repair"', "permit_office": 'office="forestry"'}

    @property
    def cache_partition(self):
        return hashlib.sha256(os.getenv("TRAVEL_OVERPASS_URL", "").encode()).hexdigest()

    def unavailable_reason(self):
        endpoint = os.getenv("TRAVEL_OVERPASS_URL", "")
        if not endpoint:
            return "missing_TRAVEL_OVERPASS_URL_authorized_instance"
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return "invalid_TRAVEL_OVERPASS_URL"
        # Shared public instances explicitly discourage being an application's backend.
        if parsed.hostname == "overpass-api.de" or parsed.hostname.endswith(".overpass-api.de"):
            return "public_overpass_backend_not_enabled_use_authorized_instance"
        return ""

    def fetch(self, p):
        lat = number(p["latitude"], low=-90, high=90)
        lon = number(p["longitude"], low=-180, high=180)
        radius = int(number(p.get("radius_m", 15000), low=100, high=25000))
        categories = sorted(set(p.get("categories", ["attraction", "camping", "fuel", "hospital", "service"])))
        if not categories or any(c not in self.filters for c in categories):
            raise ProviderError("unsupported_poi_category")
        clauses = "".join(f"nwr[{self.filters[c]}](around:{radius},{lat},{lon});" for c in categories)
        query = f"[out:json][timeout:12][maxsize:16777216];({clauses});out center 100;"
        return request_json("POST", os.environ["TRAVEL_OVERPASS_URL"], data={"data": query},
            headers={"User-Agent": "ALFRED-travel/1.2 (+https://github.com/sourabh48/alfred_ai)"})

    def normalize(self, raw, p):
        if raw.get("remark"):
            raise ProviderError("incomplete_poi_response")
        places = []
        for item in raw["elements"][:100]:
            tags = item.get("tags", {})
            if not tags.get("name"):
                continue
            center = item.get("center", item)
            category = {"camp_site": "camping"}.get(tags.get("tourism"), tags.get("tourism")) or tags.get("amenity") or ("service" if tags.get("shop") else "permit_office")
            places.append({"id": f"osm:{item['type']}:{int(item['id'])}", "name": str(tags["name"])[:200],
                "category": category, "lat": number(center["lat"], low=-90, high=90),
                "lon": number(center["lon"], low=-180, high=180),
                "source_url": f"https://www.openstreetmap.org/{item['type']}/{int(item['id'])}",
                "opening_hours": tags.get("opening_hours"), "access": tags.get("access", "unknown"),
                "wheelchair": tags.get("wheelchair", "unknown"), "fee": tags.get("fee", "unknown"),
                "wikidata": tags.get("wikidata"), "wikipedia": tags.get("wikipedia"),
                "availability": "UNKNOWN", "permit_status": "unverified",
                "season": tags.get("seasonal", "unknown"), "review_density": None})
        return {"places": places, "coverage": "OSM mapping coverage varies; absence is not evidence that no place exists."}
