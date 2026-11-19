from alfred_ai.services import personal_keys
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
                            headers={"X-Goog-Api-Key": personal_keys.get(GOOGLE_KEY)})

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


CLIMATE_YEARS = 5


def _same_dates(day, years_back):
    try:
        return day.replace(year=day.year-years_back)
    except ValueError:  # 29 February in a year without one
        return day.replace(year=day.year-years_back, day=28)


class OpenMeteoClimate(Provider):
    """What the trip's dates were like in each of the last five years, for trips beyond Google's 10-day forecast.
    Open-Meteo's historical archive needs no key; free use is non-commercial (owner approved 2026-11-19, the one
    exception to Google-only travel data, because Google has no history). Only coordinates and dates leave this PC."""
    name = "open_meteo_climate"
    category = "climate"
    source_url = "https://open-meteo.com/en/docs/historical-weather-api"
    attribution = "Weather data by Open-Meteo.com (CC BY 4.0); ALFRED averages past years"
    ttl = timedelta(days=30)  # past weather does not change
    allowed_parameters = {"latitude", "longitude", "start_date", "end_date"}
    limits = {"minute": 5, "hour": 30, "day": 200, "month": 3000}

    def unavailable_reason(self):
        return ""

    def parameters(self, parameters):
        clean = super().parameters(parameters)
        start, end = date.fromisoformat(clean["start_date"]), date.fromisoformat(clean["end_date"])
        if not start <= end or (end-start).days > 60:
            raise ProviderError("invalid_dates")
        return clean

    def windows(self, p):
        start, end = date.fromisoformat(p["start_date"]), date.fromisoformat(p["end_date"])
        # The archive trails today by a few days, so a window that has not fully passed yet starts one year further back.
        recent = timezone.localdate()-timedelta(days=7)
        first = 1 if _same_dates(end, 1) <= recent else 2
        return [(_same_dates(start, years), _same_dates(end, years)) for years in range(first, first+CLIMATE_YEARS)]

    def fetch(self, p):
        windows = self.windows(p)
        params = {"latitude": number(p["latitude"], low=-90, high=90), "longitude": number(p["longitude"], low=-180, high=180),
                  "start_date": windows[-1][0].isoformat(), "end_date": windows[0][1].isoformat(),
                  "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum", "timezone": "auto"}
        return request_json("GET", "https://archive-api.open-meteo.com/v1/archive", params=params, max_bytes=2_000_000)

    def normalize(self, raw, p):
        daily = raw.get("daily") or {}
        rows = {}
        for day, high, low, rain in zip(daily.get("time") or [], daily.get("temperature_2m_max") or [],
                                        daily.get("temperature_2m_min") or [], daily.get("precipitation_sum") or []):
            if None not in (high, low, rain):
                rows[str(day)] = (number(high, low=-90, high=65), number(low, low=-100, high=65), number(rain, low=0, high=3000))
        years = []
        for start, end in self.windows(p):
            days = [rows.get((start+timedelta(days=i)).isoformat()) for i in range((end-start).days+1)]
            if days and None not in days:
                years.append(days)
        if len(years) < 3:
            raise ProviderError("incomplete_history")
        every = [day for year in years for day in year]
        rain_total = round(mean(sum(d[2] for d in year) for year in years), 1)
        wet = round(100*sum(d[2] >= 1 for d in every)/len(every))
        high, low = round(mean(d[0] for d in every), 1), round(mean(d[1] for d in every), 1)
        return {"years": len(years), "average_max_temp": high, "average_min_temp": low,
                "average_rain_total": rain_total, "rainy_day_percent": wet,
                "summary": f"Typical for these dates over the last {len(years)} years: {low}–{high} °C, about {rain_total} mm of rain "
                           f"in total, rain on {wet}% of days. Past weather, not a forecast; Google's forecast opens 10 days before."}


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
