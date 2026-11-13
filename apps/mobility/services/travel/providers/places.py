from datetime import timedelta
import math

from alfred_ai.services.public_http import normalized_link
from .base import Provider, ProviderError, number, request_json
from .geocoding import google_headers, google_unavailable


GOOGLE_TYPES = {"attraction": ["tourist_attraction", "museum"], "camping": ["campground"], "fuel": ["gas_station"],
                "hospital": ["hospital"], "restaurant": ["restaurant"], "service": ["car_repair"]}


class GooglePlacesNearby(Provider):
    """Places near the destination (the only places source). Key in a header; only basic (Pro) fields, to stay in Google's cheaper tier."""
    name = "google_places_nearby"
    category = "places"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google; opening hours and access not checked"
    ttl = timedelta(days=1)  # Google limits keeping its place content; a day spares repeat calls while you plan
    limits = {"minute": 10, "hour": 60, "day": 200, "month": 3000}
    allowed_parameters = {"latitude", "longitude", "radius_m", "categories"}

    def unavailable_reason(self):
        return google_unavailable()

    def types(self, p):
        categories = sorted(set(p.get("categories") or ["attraction", "camping", "fuel", "hospital", "service"]))
        if any(c not in GOOGLE_TYPES for c in categories):
            raise ProviderError("unsupported_poi_category")
        return [t for c in categories for t in GOOGLE_TYPES.get(c, [])]

    def fetch(self, p):
        center = {"latitude": number(p["latitude"], low=-90, high=90), "longitude": number(p["longitude"], low=-180, high=180)}
        body = {"includedTypes": self.types(p), "maxResultCount": 20,
                "locationRestriction": {"circle": {"center": center, "radius": float(number(p.get("radius_m", 15000), low=100, high=25000))}}}
        return request_json("POST", "https://places.googleapis.com/v1/places:searchNearby", json=body,
            headers=google_headers("places.id,places.displayName,places.formattedAddress,places.location,places.primaryType,places.types,places.googleMapsUri"))

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


class GoogleDestinations(GooglePlacesNearby):
    """Places worth a trip within a day's travel of the start city, from Google Places text search."""
    name = "google_destinations"
    category = "destinations"
    attribution = "Powered by Google; access and current conditions not checked"
    allowed_parameters = {"latitude", "longitude", "radius_km", "interest"}
    interests = {"camping", "hiking", "beach", "waterfall", "heritage", "nature"}

    def parameters(self, parameters):
        p = Provider.parameters(self, parameters)
        return {"latitude": round(number(p["latitude"], low=-90, high=90), 3), "longitude": round(number(p["longitude"], low=-180, high=180), 3),
                "radius_km": int(number(p.get("radius_km", 300), low=25, high=600)),
                "interest": p.get("interest") if p.get("interest") in self.interests else ""}

    def fetch(self, p):
        # A box around the start city; one degree of latitude is about 111 km.
        lat, lon, span = p["latitude"], p["longitude"], p["radius_km"] / 111
        wide = span / max(0.2, math.cos(math.radians(lat)))
        box = {"low": {"latitude": max(-90, lat - span), "longitude": max(-180, lon - wide)},
               "high": {"latitude": min(90, lat + span), "longitude": min(180, lon + wide)}}
        body = {"textQuery": f"{p['interest']} tourist destinations".strip(), "pageSize": 20, "locationRestriction": {"rectangle": box}}
        return request_json("POST", "https://places.googleapis.com/v1/places:searchText", json=body,
                            headers=google_headers("places.id,places.displayName,places.formattedAddress,places.location,places.googleMapsUri"))

    def normalize(self, raw, p):
        places, seen = [], set()
        for place in self.listings(raw):
            if place["name"].casefold() in seen:
                continue
            seen.add(place["name"].casefold())
            places.append({"id": place["id"], "name": place["name"], "lat": place["lat"], "lon": place["lon"],
                "source": place["source_url"], "authority": "Google Maps", "source_type": "map_listing",
                "styles": [], "activities": [], "stay": "Search stays near the destination; inventory unverified",
                "nightly": 1500, "nightly_freshness": "ESTIMATED",
                "caution": "Google Maps listing; verify access and current conditions with the local authority.",
                "verification_state": "destination_reference", "popularity": "UNKNOWN"})
        return {"destinations": places, "coverage": "Google Maps listings in a box around your start city; not an official list."}
