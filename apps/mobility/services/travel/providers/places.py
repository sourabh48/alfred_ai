from datetime import timedelta
import os
import hashlib
from urllib.parse import urlsplit

from alfred_ai.services.public_http import normalized_link
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
        # The same check as the transport, so status can't say configured for a URL it refuses.
        safe = normalized_link(endpoint)
        if not safe or urlsplit(safe).fragment:
            return "invalid_TRAVEL_OVERPASS_URL"
        host = urlsplit(safe).hostname
        # Shared public instances explicitly discourage being an application's backend.
        if host == "overpass-api.de" or host.endswith(".overpass-api.de"):
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


# Google place types for each ALFRED place category; permit offices have no Google type.
GOOGLE_TYPES = {"attraction": ["tourist_attraction", "museum"], "camping": ["campground"], "fuel": ["gas_station"],
                "hospital": ["hospital"], "restaurant": ["restaurant"], "service": ["car_repair"]}


class GooglePlacesNearby(Provider):
    """Places near the destination (the only places source). Key in a header; only basic (Pro) fields, to stay in Google's cheaper tier."""
    name = "google_places_nearby"
    category = "places"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google; opening hours and access not checked"
    ttl = timedelta(days=1)  # Google limits keeping its place content; a day spares repeat calls while you plan
    limits = {"minute": 5, "hour": 20, "day": 40, "month": 400}
    allowed_parameters = {"latitude", "longitude", "radius_m", "categories"}

    def unavailable_reason(self):
        return "" if os.getenv("TRAVEL_GOOGLE_MAPS_API_KEY") else "missing_TRAVEL_GOOGLE_MAPS_API_KEY"

    def types(self, p):
        categories = sorted(set(p.get("categories") or ["attraction", "camping", "fuel", "hospital", "service"]))
        if any(c not in OverpassPlaces.filters for c in categories):
            raise ProviderError("unsupported_poi_category")
        return [t for c in categories for t in GOOGLE_TYPES.get(c, [])]

    def fetch(self, p):
        center = {"latitude": number(p["latitude"], low=-90, high=90), "longitude": number(p["longitude"], low=-180, high=180)}
        body = {"includedTypes": self.types(p), "maxResultCount": 20,
                "locationRestriction": {"circle": {"center": center, "radius": float(number(p.get("radius_m", 15000), low=100, high=25000))}}}
        return request_json("POST", "https://places.googleapis.com/v1/places:searchNearby", json=body,
            headers={"X-Goog-Api-Key": os.environ["TRAVEL_GOOGLE_MAPS_API_KEY"], "Content-Type": "application/json",
                     "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.primaryType,places.types,places.googleMapsUri"})

    @staticmethod
    def listings(raw):
        for item in (raw.get("places") or [])[:20]:
            name = str((item.get("displayName") or {}).get("text") or "")[:200]
            if name:
                place_id = str(item["id"])[:200]
                yield {"id": f"google:{place_id}", "name": name, "address": str(item.get("formattedAddress") or "")[:200],
                       "lat": number(item["location"]["latitude"], low=-90, high=90), "lon": number(item["location"]["longitude"], low=-180, high=180),
                       "source_url": normalized_link(str(item.get("googleMapsUri") or "")) or f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                       "types": [item.get("primaryType"), *(item.get("types") or [])]}

    def normalize(self, raw, p):
        category_of = {t: c for c, types in GOOGLE_TYPES.items() for t in types}
        places = []
        for place in self.listings(raw):
            category = next((category_of[t] for t in place.pop("types") if t in category_of), None)
            if category:
                places.append({**place, "category": category, "opening_hours": None, "access": "unknown", "wheelchair": "unknown",
                               "fee": "unknown", "wikidata": None, "wikipedia": None, "availability": "UNKNOWN",
                               "permit_status": "unverified", "season": "unknown", "review_density": None})
        return {"places": places, "coverage": "Google Maps listings near the destination. Open each place on Google Maps for hours and access."}


class GoogleLodging(GooglePlacesNearby):
    """Hotels near the destination (the only hotels source): names and Google Maps links, never a price or a free room."""
    name = "google_lodging"
    category = "hotels"
    attribution = "Powered by Google; prices and free rooms not checked"
    allowed_parameters = {"latitude", "longitude"}

    def types(self, p):
        return ["lodging"]

    def normalize(self, raw, p):
        return {"options": [{"name": place["name"], "provider": "Google Maps", "address": place["address"], "lat": place["lat"],
                             "lon": place["lon"], "category": "hotel", "source_url": place["source_url"], "booking_url": place["source_url"],
                             "total_price": None, "nightly_rate": None, "currency": None, "availability": "UNKNOWN"}
                            for place in self.listings(raw)]}
