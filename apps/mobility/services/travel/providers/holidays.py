"""Public holidays and long weekends from Nager.Date (free, no key; owner approval 2026-11-18).

Only a country code and a year leave this PC. Nager.Date does not cover every country (India is missing in 2026).
"""
from datetime import timedelta
from hashlib import sha256
import re

from .base import Provider, ProviderError, request_json

API = "https://date.nager.at/api/v3"


class NagerHolidays(Provider):
    name = "nager_date"
    category = "holidays"
    source_url = "https://date.nager.at/"
    attribution = "Holidays from Nager.Date"
    ttl = timedelta(days=7)
    limits = {"minute": 10, "hour": 60, "day": 200, "month": 2000}
    allowed_parameters = {"country", "year"}

    def unavailable_reason(self):
        return ""

    def fetch(self, p):
        country, year = str(p["country"]).upper(), int(p["year"])
        if not re.fullmatch(r"[A-Z]{2}", country) or not 2000 <= year <= 2100:
            raise ProviderError("invalid_parameters")
        countries, _ = request_json("GET", f"{API}/AvailableCountries")
        if country not in {str(c.get("countryCode")) for c in countries or []}:
            raise ProviderError("country_not_covered", retry_after=1)  # another country may be asked next
        holidays, first = request_json("GET", f"{API}/PublicHolidays/{year}/{country}")
        weekends, second = request_json("GET", f"{API}/LongWeekend/{year}/{country}")
        return {"holidays": holidays, "long_weekends": weekends}, sha256(f"{first}{second}".encode()).hexdigest()

    def normalize(self, raw, p):
        holidays = [{"date": str(h.get("date"))[:10], "name": str(h.get("localName") or h.get("name") or "")[:120],
                     "english": str(h.get("name") or "")[:120], "national": bool(h.get("global")),
                     "regions": [str(c)[:10] for c in h.get("counties") or []][:40]}
                    for h in raw.get("holidays") or [] if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(h.get("date"))[:10])]
        weekends = [{"start": str(w.get("startDate"))[:10], "end": str(w.get("endDate"))[:10], "days": int(w.get("dayCount") or 0),
                     "leave_days": [str(d)[:10] for d in w.get("bridgeDays") or []][:5]}
                    for w in raw.get("long_weekends") or []]
        if not holidays:
            raise ProviderError("no_holidays", retry_after=1)
        return {"holidays": holidays, "long_weekends": weekends}
