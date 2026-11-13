from datetime import timedelta
import os

from .base import Provider, ProviderError, number, request_json
from .web import public_place

GOOGLE_KEY = "TRAVEL_GOOGLE_MAPS_API_KEY"


def google_headers(field_mask):
    return {"X-Goog-Api-Key": os.environ[GOOGLE_KEY], "Content-Type": "application/json", "X-Goog-FieldMask": field_mask}


def google_unavailable():
    return "" if os.getenv(GOOGLE_KEY) else "missing_TRAVEL_GOOGLE_MAPS_API_KEY"


class GooglePlaceSearch(Provider):
    """Place names to map positions with Google Places text search (owner decision 2026-11-14: Google only)."""
    name = "google_places"
    category = "geocoding"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google"
    ttl = timedelta(days=30)  # Google allows keeping latitude and longitude for up to 30 days
    allowed_parameters = {"name", "country_code"}
    limits = {"minute": 10, "hour": 60, "day": 200, "month": 3000}

    def unavailable_reason(self):
        return google_unavailable()

    def parameters(self, parameters):
        # Rejected before query() logs a network call, so a bad name never uses budget or backs off the provider.
        clean = super().parameters(parameters)
        if not public_place(clean.get("name")):
            raise ProviderError("invalid_location")
        return clean

    def fetch(self, p):
        body = {"textQuery": public_place(p.get("name")), "pageSize": 5}
        if p.get("country_code"):
            body["regionCode"] = p["country_code"]
        return request_json("POST", "https://places.googleapis.com/v1/places:searchText", json=body,
                            headers=google_headers("places.id,places.displayName,places.formattedAddress,places.location"))

    def normalize(self, raw, p):
        places = []
        for item in (raw.get("places") or [])[:5]:
            places.append({"id": str(item["id"])[:200], "name": str((item.get("displayName") or {}).get("text") or "")[:160],
                "lat": number(item["location"]["latitude"], low=-90, high=90), "lon": number(item["location"]["longitude"], low=-180, high=180),
                "region": str(item.get("formattedAddress") or "")[:200], "country": "", "country_code": ""})
        return {"locations": places, "ambiguous": len(places) > 1}
