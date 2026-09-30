from datetime import date, timedelta
import os
from statistics import mean

from django.utils import timezone

from .base import ProviderError, number, request_json
from .geocoding import OpenMeteoGeocoding


class OpenMeteoWeather(OpenMeteoGeocoding):
    category = "weather"
    source_url = "https://open-meteo.com/en/docs"
    attribution = "Weather data by Open-Meteo, CC BY 4.0; ALFRED summarizes forecasts"
    ttl = timedelta(hours=2)
    allowed_parameters = {"latitude", "longitude", "start_date", "end_date"}
    variables = ("temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max",
                 "weather_code", "sunrise", "sunset")

    def fetch(self, p):
        start, end = date.fromisoformat(p["start_date"]), date.fromisoformat(p["end_date"])
        today = timezone.localdate()
        if not today <= start <= end <= today+timedelta(days=15):
            raise ProviderError("outside_forecast_window")
        params = {"latitude": number(p["latitude"], low=-90, high=90),
                  "longitude": number(p["longitude"], low=-180, high=180),
                  "start_date": start.isoformat(), "end_date": end.isoformat(),
                  "daily": ",".join(self.variables), "timezone": "auto", "wind_speed_unit": "kmh"}
        key = os.getenv("TRAVEL_OPEN_METEO_API_KEY")
        if key:
            params["apikey"] = key
        host = "customer-api" if key else "api"
        return request_json("GET", f"https://{host}.open-meteo.com/v1/forecast", params=params)

    def normalize(self, raw, p):
        daily = raw["daily"]
        days = []
        expected = (date.fromisoformat(p["end_date"])-date.fromisoformat(p["start_date"])).days+1
        if len(daily["time"]) != expected or expected < 1:
            raise ProviderError("incomplete_forecast")
        for i, day in enumerate(daily["time"]):
            if day != (date.fromisoformat(p["start_date"])+timedelta(days=i)).isoformat():
                raise ProviderError("incomplete_forecast")
            row = {"date": day, "max_temp_c": number(daily["temperature_2m_max"][i], low=-90, high=65),
                   "min_temp_c": number(daily["temperature_2m_min"][i], low=-100, high=65),
                   "rain_mm": number(daily["precipitation_sum"][i], low=0, high=3000),
                   "wind_kmh": number(daily["wind_speed_10m_max"][i], low=0, high=500),
                   "weather_code": int(daily["weather_code"][i]),
                   "sunrise": daily["sunrise"][i], "sunset": daily["sunset"][i]}
            row["risks"] = weather_risks(row)
            days.append(row)
        return {"days": days, "timezone": raw.get("timezone", ""),
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
    if day["weather_code"] in {95, 96, 99}:
        risks.append("thunderstorm")
    if day["weather_code"] in {45, 48}:
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
