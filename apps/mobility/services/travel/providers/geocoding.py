from datetime import timedelta
import os

from .base import Provider, ProviderError, number, request_json
from .web import public_place


class OpenMeteoGeocoding(Provider):
    name = "open_meteo"
    category = "geocoding"
    source_url = "https://open-meteo.com/en/docs/geocoding-api"
    attribution = "Open-Meteo / GeoNames, CC BY 4.0"
    ttl = timedelta(days=90)
    allowed_parameters = {"name", "country_code"}
    min_interval = 0
    limits = {"minute": 60, "hour": 500, "day": 2000, "month": 50000}

    def unavailable_reason(self):
        if os.getenv("TRAVEL_OPEN_METEO_API_KEY"):
            return ""
        return "" if os.getenv("TRAVEL_USE_MODE") == "personal_noncommercial" else "set_TRAVEL_USE_MODE_or_TRAVEL_OPEN_METEO_API_KEY"

    def parameters(self, parameters):
        # Rejected before query() logs a network call, so a bad name never uses budget or backs off the provider.
        clean = super().parameters(parameters)
        if self.category == "geocoding" and not public_place(clean.get("name")):
            raise ProviderError("invalid_location")
        return clean

    def fetch(self, p):
        name = public_place(p.get("name"))
        if not name:
            raise ProviderError("invalid_location")
        params = {"name": name, "count": 5, "language": "en", "format": "json"}
        if p.get("country_code"):
            params["countryCode"] = p["country_code"]
        key = os.getenv("TRAVEL_OPEN_METEO_API_KEY")
        if key:
            params["apikey"] = key
        host = "customer-geocoding-api" if key else "geocoding-api"
        return request_json("GET", f"https://{host}.open-meteo.com/v1/search", params=params)

    def normalize(self, raw, p):
        places = []
        for item in raw.get("results", [])[:5]:
            places.append({"id": str(item["id"]), "name": str(item["name"])[:160],
                "lat": number(item["latitude"], low=-90, high=90),
                "lon": number(item["longitude"], low=-180, high=180),
                "region": str(item.get("admin1", "")), "country": str(item.get("country", "")),
                "country_code": str(item.get("country_code", ""))})
        return {"locations": places, "ambiguous": len(places) > 1}


class GooglePlaceSearch(OpenMeteoGeocoding):
    """Paid fallback for place names Open-Meteo cannot find; key sent in a header, capped under Google's free use."""
    name = "google_places"
    source_url = "https://www.google.com/maps"
    attribution = "Powered by Google"
    ttl = timedelta(days=30)  # Google allows keeping latitude and longitude for up to 30 days
    min_interval = 1
    limits = {"minute": 5, "hour": 20, "day": 40, "month": 400}

    def unavailable_reason(self):
        return "" if os.getenv("TRAVEL_GOOGLE_MAPS_API_KEY") else "missing_TRAVEL_GOOGLE_MAPS_API_KEY"

    def fetch(self, p):
        name = public_place(p.get("name"))
        if not name:
            raise ProviderError("invalid_location")
        body = {"textQuery": name, "pageSize": 5}
        if p.get("country_code"):
            body["regionCode"] = p["country_code"]
        return request_json("POST", "https://places.googleapis.com/v1/places:searchText", json=body,
            headers={"X-Goog-Api-Key": os.environ["TRAVEL_GOOGLE_MAPS_API_KEY"], "Content-Type": "application/json",
                     "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location"})

    def normalize(self, raw, p):
        places = []
        for item in (raw.get("places") or [])[:5]:
            places.append({"id": str(item["id"])[:200], "name": str((item.get("displayName") or {}).get("text") or "")[:160],
                "lat": number(item["location"]["latitude"], low=-90, high=90), "lon": number(item["location"]["longitude"], low=-180, high=180),
                "region": str(item.get("formattedAddress") or "")[:200], "country": "", "country_code": ""})
        return {"locations": places, "ambiguous": len(places) > 1}
