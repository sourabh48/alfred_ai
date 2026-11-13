from datetime import date, timedelta
import os
from statistics import mean

from django.utils import timezone

from .base import Provider, ProviderError, number, request_json
from .geocoding import GOOGLE_KEY, google_unavailable

FORECAST_DAYS = 10  # Google's daily forecast covers today and the next nine days


class GoogleWeather(Provider):
    """Daily forecast from the Google Maps Platform Weather API (owner decision 2026-11-14: Google only)."""
    name = "google_weather"
    category = "weather"
    source_url = "https://developers.google.com/maps/documentation/weather"
    attribution = "Weather by Google; ALFRED summarizes the forecast"
    ttl = timedelta(hours=2)
    allowed_parameters = {"latitude", "longitude", "start_date", "end_date"}
    limits = {"minute": 10, "hour": 60, "day": 200, "month": 3000}

    def unavailable_reason(self):
        return google_unavailable()

    def parameters(self, parameters):
        # Checked before query() logs a network call: an unforecastable window must not use budget.
        clean = super().parameters(parameters)
        start, end = date.fromisoformat(clean["start_date"]), date.fromisoformat(clean["end_date"])
        today = timezone.localdate()
        if not today <= start <= end < today+timedelta(days=FORECAST_DAYS):
            raise ProviderError("outside_forecast_window")
        return clean

    def fetch(self, p):
        days = (date.fromisoformat(p["end_date"])-timezone.localdate()).days+1
        params = {"location.latitude": number(p["latitude"], low=-90, high=90),
                  "location.longitude": number(p["longitude"], low=-180, high=180), "days": days, "pageSize": days}
        return request_json("GET", "https://weather.googleapis.com/v1/forecast/days:lookup", params=params,
                            headers={"X-Goog-Api-Key": os.environ[GOOGLE_KEY]})

    def normalize(self, raw, p):
        start, end = date.fromisoformat(p["start_date"]), date.fromisoformat(p["end_date"])
        rows = {}
        for item in raw.get("forecastDays") or []:
            shown = item.get("displayDate") or {}
            day = date(int(shown["year"]), int(shown["month"]), int(shown["day"]))
            if not start <= day <= end:
                continue
            parts = [item.get("daytimeForecast") or {}, item.get("nighttimeForecast") or {}]
            rain = sum(number(((part.get("precipitation") or {}).get("qpf") or {}).get("quantity", 0), low=0, high=3000) for part in parts)
            wind = max(number((((part.get("wind") or {}).get("speed") or {}).get("value", 0)), low=0, high=500) for part in parts)
            condition = str(((parts[0].get("weatherCondition") or {}).get("type")) or "")
            sun = item.get("sunEvents") or {}
            row = {"date": day.isoformat(), "max_temp_c": number(item["maxTemperature"]["degrees"], low=-90, high=65),
                   "min_temp_c": number(item["minTemperature"]["degrees"], low=-100, high=65),
                   "rain_mm": round(rain, 1), "wind_kmh": wind, "condition": condition,
                   "sunrise": str(sun.get("sunriseTime") or "")[11:16], "sunset": str(sun.get("sunsetTime") or "")[11:16]}
            row["risks"] = weather_risks(row)
            rows[row["date"]] = row
        days = [rows.get((start+timedelta(days=i)).isoformat()) for i in range((end-start).days+1)]
        if not days or None in days:
            raise ProviderError("incomplete_forecast")
        return {"days": days, "timezone": str((raw.get("timeZone") or {}).get("id") or ""),
                "average_min_temp": round(mean(d["min_temp_c"] for d in days), 1),
                "average_max_temp": round(mean(d["max_temp_c"] for d in days), 1),
                "precipitation_total": round(sum(d["rain_mm"] for d in days), 1),
                "wind_max": max(d["wind_kmh"] for d in days),
                "official_alerts": "UNKNOWN", "mountain_conditions": "UNKNOWN",
                "summary": "Forecast, not observed conditions or an official severe-weather warning."}


def weather_risks(day):
    risks = []
    if day["rain_mm"] >= 20:
        risks.append("rain")
    if day["max_temp_c"] >= 35:
        risks.append("heat")
    if "THUNDER" in day.get("condition", ""):
        risks.append("thunderstorm")
    if "FOG" in day.get("condition", "") or "HAZE" in day.get("condition", ""):
        risks.append("fog")
    if day["wind_kmh"] >= 40:
        risks.append("wind")
    return risks


def replan_proposals(result):
    """Recommendations only; the user's itinerary is never silently cancelled."""
    if not result.success or result.stale:
        return []
    proposals = []
    for day in result.payload.get("days", []):
        if not day["risks"]:
            continue
        proposals.append({"date": day["date"], "risks": day["risks"], "requires_acceptance": True,
            "reason": f"Forecast: {day['rain_mm']} mm rain, {day['max_temp_c']} °C maximum, {day['wind_kmh']} km/h wind.",
            "alternative": "Move exposed viewpoints/treks to a clearer day; use a local indoor visit or rest block. Recheck road and official warnings before departure."})
    return proposals
