from datetime import date, timedelta
from decimal import Decimal
import os
import re

from django.utils import timezone

from .base import Provider, ProviderError, number, request_json
from ..money import quoted_amount

SKYSCANNER = "https://partners.api.skyscanner.net/apiservices/v3/flights/live/search"
PRICE_UNITS = {"PRICE_UNIT_WHOLE": 1, "PRICE_UNIT_CENTI": 100, "PRICE_UNIT_MILLI": 1000, "PRICE_UNIT_MICRO": 1000000}
CABINS = {"economy": "CABIN_CLASS_ECONOMY", "premium_economy": "CABIN_CLASS_PREMIUM_ECONOMY",
          "business": "CABIN_CLASS_BUSINESS", "first": "CABIN_CLASS_FIRST"}


def _when(value):
    """Skyscanner's {year, month, day, hour, minute} as an ISO date-time."""
    if not isinstance(value, dict) or not value.get("year"):
        return None
    return f"{int(value['year']):04d}-{int(value['month']):02d}-{int(value['day']):02d}T{int(value.get('hour', 0)):02d}:{int(value.get('minute', 0)):02d}"


class SkyscannerFlights(Provider):
    """Live flight prices from the Skyscanner Travel API (partner key, flights only). Until the key is approved the
    planner shows a Google Flights link instead. Built from Skyscanner's Flights Live Prices v3 documentation;
    UNVERIFIED against a live key."""
    name = "skyscanner"
    category = "flights"
    source_url = "https://www.skyscanner.net/"
    attribution = "Prices by Skyscanner; check the airline or agent before you book"
    ttl = timedelta(minutes=15)
    limits = {"minute": 5, "hour": 30, "day": 100, "month": 2000}
    allowed_parameters = {"origin", "destination", "departure_date", "return_date", "adults", "cabin_class"}

    def unavailable_reason(self):
        return "" if os.getenv("TRAVEL_SKYSCANNER_API_KEY") else "missing_TRAVEL_SKYSCANNER_API_KEY"

    def fetch(self, p):
        origin, destination = str(p["origin"]).upper(), str(p["destination"]).upper()
        if not re.fullmatch(r"[A-Z]{3}", origin) or not re.fullmatch(r"[A-Z]{3}", destination) or origin == destination:
            raise ProviderError("airport_codes_required")
        departure = date.fromisoformat(p["departure_date"])
        if departure < timezone.localdate():
            raise ProviderError("invalid_departure_date")
        legs = [(origin, destination, departure)]
        if p.get("return_date"):
            returning = date.fromisoformat(p["return_date"])
            if returning < departure:
                raise ProviderError("invalid_return_date")
            legs.append((destination, origin, returning))
        cabin = CABINS.get(p.get("cabin_class", "economy"))
        if not cabin:
            raise ProviderError("invalid_cabin_class")
        # Only airports, dates, traveller count and cabin are sent; the key goes in a header.
        query = {"market": "IN", "locale": "en-GB", "currency": "INR", "adults": int(number(p.get("adults", 1), low=1, high=8)),
                 "cabinClass": cabin, "queryLegs": [{"originPlaceId": {"iata": a}, "destinationPlaceId": {"iata": b},
                                                    "date": {"year": d.year, "month": d.month, "day": d.day}} for a, b, d in legs]}
        headers = {"x-api-key": os.environ["TRAVEL_SKYSCANNER_API_KEY"], "Content-Type": "application/json"}
        raw, digest = request_json("POST", f"{SKYSCANNER}/create", json={"query": query}, headers=headers)
        for _ in range(2):  # a search fills in over a few seconds; two polls keep the request short
            if raw.get("status") != "RESULT_STATUS_INCOMPLETE" or not raw.get("sessionToken"):
                break
            raw, digest = request_json("POST", f"{SKYSCANNER}/poll/{raw['sessionToken']}", headers=headers)
        return raw, digest

    def normalize(self, raw, p):
        results = (raw.get("content") or {}).get("results") or {}
        itineraries, legs = results.get("itineraries") or {}, results.get("legs") or {}
        places, carriers = results.get("places") or {}, results.get("carriers") or {}
        cheapest = ((raw.get("content") or {}).get("sortingOptions") or {}).get("cheapest") or []
        options = []
        for ranked in cheapest[:10]:
            itinerary = itineraries.get(ranked.get("itineraryId")) or {}
            pricing = (itinerary.get("pricingOptions") or [{}])[0]
            price = pricing.get("price") or {}
            scale = PRICE_UNITS.get(price.get("unit"))
            if not scale or price.get("amount") in (None, ""):
                continue
            first = legs.get((itinerary.get("legIds") or [""])[0]) or {}
            link = next((item.get("deepLink") for item in pricing.get("items") or [] if str(item.get("deepLink", "")).startswith("https://")), None)
            options.append({"provider": "Skyscanner",
                "carrier": ", ".join(str((carriers.get(c) or {}).get("name") or "") for c in first.get("marketingCarrierIds") or [])[:120],
                "origin": str((places.get(first.get("originPlaceId")) or {}).get("iata") or p["origin"])[:3],
                "destination": str((places.get(first.get("destinationPlaceId")) or {}).get("iata") or p["destination"])[:3],
                "departure": _when(first.get("departureDateTime")), "arrival": _when(first.get("arrivalDateTime")),
                "duration": first.get("durationInMinutes"), "transfers": first.get("stopCount"),
                "fare": quoted_amount(Decimal(str(price["amount"])) / scale), "currency": "INR",
                "fare_scope": "all requested travellers; the agent's page shows the final price",
                "availability": "price_returned_recheck_before_purchase", "booking_url": link})
        return {"options": options, "coverage": "Airlines and agents in Skyscanner's search; not every fare on the market."}


class IndianRailProvider(Provider):
    name = "indian_rail_authorized"
    category = "trains"
    source_url = "https://www.irctc.co.in/"
    allowed_parameters = {"origin", "destination", "date", "class"}

    def unavailable_reason(self):
        return "authorized_rail_provider_contract_and_documented_API_required"

    def normalize(self, raw, p):
        # Domain contract for a future authorized adapter. Schedule is independent
        # from inventory. Never derive seat availability or waitlist from a timetable.
        options = []
        for item in raw["options"]:
            options.append({"provider":self.name,"origin":item["origin"],"destination":item["destination"],
                "date":item.get("date"),"departure":item.get("departure"),"arrival":item.get("arrival"),
                "duration":item.get("duration"),"transfers":item.get("transfers"),"class":item.get("class"),
                "schedule_status":"USER_PROVIDED", "availability":"UNKNOWN", "waitlist":None,
                "fare":item.get("fare_estimate"),"fare_freshness":"ESTIMATED","currency":"INR",
                "retrieved_at":None,"booking_url":"https://www.irctc.co.in/"})
        return {"options":options}
