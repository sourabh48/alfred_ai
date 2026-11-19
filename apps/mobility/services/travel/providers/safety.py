"""Safety notes for a trip about to start (owner approved 2026-11-19): recent strong earthquakes near the destination
(USGS, public, no key) and current air quality there (Google Air Quality, with the same Google key as the map).

Only the destination's coordinates leave this PC. Notes only: ALFRED never cancels or changes a trip.
"""
from datetime import datetime, timedelta, timezone as dt_timezone

from alfred_ai.services import personal_keys
from django.utils import timezone

from .base import Provider, ProviderError, number, request_json
from .geocoding import GOOGLE_KEY, google_unavailable

QUAKE_RADIUS_KM, QUAKE_MAGNITUDE, QUAKE_DAYS = 300, 5.0, 7
POOR_AIR = 40  # Google's Universal AQI runs from 0 (poor) to 100 (excellent)


class UsgsEarthquakes(Provider):
    name = "usgs_earthquakes"
    category = "earthquakes"
    source_url = "https://earthquake.usgs.gov/earthquakes/map/"
    attribution = "Earthquakes by the US Geological Survey; follow local authorities' advice"
    ttl = timedelta(hours=3)
    allowed_parameters = {"latitude", "longitude", "since"}
    limits = {"minute": 5, "hour": 30, "day": 200, "month": 3000}

    def unavailable_reason(self):
        return ""

    def fetch(self, p):
        params = {"format": "geojson", "latitude": number(p["latitude"], low=-90, high=90),
                  "longitude": number(p["longitude"], low=-180, high=180), "maxradiuskm": QUAKE_RADIUS_KM,
                  "minmagnitude": QUAKE_MAGNITUDE, "starttime": p["since"], "orderby": "magnitude", "limit": 5}
        return request_json("GET", "https://earthquake.usgs.gov/fdsnws/event/1/query", params=params)

    def normalize(self, raw, p):
        quakes = []
        for feature in raw.get("features") or []:
            props = feature.get("properties") or {}
            magnitude = number(props.get("mag"), low=0, high=10)
            when = datetime.fromtimestamp(int(props["time"]) / 1000, tz=dt_timezone.utc)
            quakes.append({"magnitude": round(magnitude, 1), "place": str(props.get("place") or "")[:120],
                           "when": timezone.localtime(when).strftime("%d %b %H:%M"), "tsunami": bool(props.get("tsunami")),
                           "url": str(props.get("url") or "") if str(props.get("url") or "").startswith("https://earthquake.usgs.gov/") else ""})
        return {"quakes": quakes}


class GoogleAirQuality(Provider):
    name = "google_air_quality"
    category = "air_quality"
    source_url = "https://developers.google.com/maps/documentation/air-quality"
    attribution = "Air quality by Google"
    ttl = timedelta(hours=3)
    allowed_parameters = {"latitude", "longitude"}
    limits = {"minute": 5, "hour": 30, "day": 100, "month": 2000}

    def unavailable_reason(self):
        return google_unavailable()

    def fetch(self, p):
        body = {"location": {"latitude": number(p["latitude"], low=-90, high=90), "longitude": number(p["longitude"], low=-180, high=180)}}
        return request_json("POST", "https://airquality.googleapis.com/v1/currentConditions:lookup", json=body,
                            headers={"X-Goog-Api-Key": personal_keys.get(GOOGLE_KEY)})

    def normalize(self, raw, p):
        for index in raw.get("indexes") or []:
            if index.get("code") == "uaqi":
                return {"aqi": int(number(index.get("aqi"), low=0, high=100)), "category": str(index.get("category") or "")[:60],
                        "pollutant": str(index.get("dominantPollutant") or "")[:20]}
        raise ProviderError("no_air_quality_index")


def destination_point(plan):
    """The trip's destination (the map's overnight point), or None before research has placed it."""
    for feature in ((plan.itinerary or {}).get("map") or {}).get("features") or []:
        if (feature.get("properties") or {}).get("kind") == "overnight":
            lon, lat = (feature.get("geometry") or {}).get("coordinates") or (None, None)
            try:
                return round(number(lat, low=-90, high=90), 3), round(number(lon, low=-180, high=180), 3)
            except (TypeError, ValueError):
                return None
    return None
