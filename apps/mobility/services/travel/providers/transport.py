from alfred_ai.services import personal_keys
from datetime import date, datetime, timedelta
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
        return "" if personal_keys.get("TRAVEL_SKYSCANNER_API_KEY") else "missing_TRAVEL_SKYSCANNER_API_KEY"

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
        headers = {"x-api-key": personal_keys.get("TRAVEL_SKYSCANNER_API_KEY"), "Content-Type": "application/json"}
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


AMADEUS = "https://api.amadeus.com/api/v3/search/"
AMADEUS_CABINS = {"economy": "ECONOMY", "premium_economy": "PREMIUM_ECONOMY", "business": "BUSINESS", "first": "FIRST"}


def _minutes(start, end):
    """Elapsed minutes between two of Amadeus's local times with offsets (the bound's own duration can be an hour off)."""
    try:
        return int((datetime.fromisoformat(end.replace("Z", "+00:00")) - datetime.fromisoformat(start.replace("Z", "+00:00"))).total_seconds() // 60)
    except (AttributeError, TypeError, ValueError):
        return None


class AmadeusFlights(Provider):
    """Live flight prices from the free Amadeus Travel Builder beta (each person's own key; owner request 2026-11-19).
    Search only: every offer links to the airline's own site, where the person buys. Amadeus covers a subset of airlines;
    which Indian carriers are included is UNVERIFIED until a live key is tried. Its terms allow only short caching."""
    name = "amadeus"
    category = "flights"
    source_url = "https://github.com/AmadeusITGroup/amadeus-travel-toolkit"
    attribution = "Live airline prices; check the airline's site before you book"
    ttl = timedelta(minutes=15)
    limits = {"minute": 5, "hour": 30, "day": 100, "month": 2000}
    allowed_parameters = SkyscannerFlights.allowed_parameters

    def unavailable_reason(self):
        return "" if personal_keys.get("TRAVEL_AMADEUS_API_KEY") else "missing_TRAVEL_AMADEUS_API_KEY"

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
        cabin = AMADEUS_CABINS.get(p.get("cabin_class", "economy"))
        if not cabin:
            raise ProviderError("invalid_cabin_class")
        # Only airports, dates, traveller count and cabin are sent; the key goes in a header. Lists are positional, one per leg.
        params = {"origins": ",".join(a for a, _, _ in legs), "destinations": ",".join(b for _, b, _ in legs),
                  "dates": ",".join(d.isoformat() for _, _, d in legs), "locale": "en-IN", "flow": "NETWORK", "currency": "INR",
                  "adults": int(number(p.get("adults", 1), low=1, high=9)), "travel_class": cabin, "number_of_results": 5}
        return request_json("GET", AMADEUS, params=params, headers={"X-API-Key": personal_keys.get("TRAVEL_AMADEUS_API_KEY")})

    def normalize(self, raw, p):
        names = {code: str((item or {}).get("name") or code) for code, item in ((raw.get("meta") or {}).get("carriers") or {}).items()}
        options = []
        for result in raw.get("results") or []:
            fare = result.get("fare") or {}
            first = (((result.get("bounds") or [{}])[0]) or {}).get("flights") or []
            total = (fare.get("itinerary_price") or {}).get("total_fare")
            if total in (None, "") or isinstance(total, bool) or fare.get("currency") != "INR" or not first:
                continue  # no price, or a currency other than the one asked for: left out, never converted
            try:
                amount = quoted_amount(Decimal(str(total)))
            except (ArithmeticError, ValueError):
                continue
            link = str(result.get("deep_link") or "")
            options.append({"provider": "Amadeus",
                "carrier": ", ".join(dict.fromkeys(names.get(f.get("marketing_airline"), str(f.get("marketing_airline") or "")) for f in first))[:120],
                "origin": str((first[0].get("origin") or {}).get("airport") or p["origin"])[:3],
                "destination": str((first[-1].get("destination") or {}).get("airport") or p["destination"])[:3],
                # local airport times as returned, never shifted to the viewer's zone
                "departure": str(first[0].get("departs_at") or "")[:16] or None, "arrival": str(first[-1].get("arrives_at") or "")[:16] or None,
                "duration": _minutes(first[0].get("departs_at"), first[-1].get("arrives_at")), "transfers": len(first) - 1,
                "fare": amount, "currency": "INR",
                "fare_scope": "all requested travellers; the airline's page shows the final price",
                "availability": "price_returned_recheck_before_purchase", "booking_url": link if link.startswith("https://") else None})
        options.sort(key=lambda o: Decimal(o["fare"]))
        # Checked live 2026-11-19 (BLR-DEL, BLR-GOI, DEL-BOM, BLR-CCU): Air India is the only Indian airline in the beta.
        return {"options": options[:10], "coverage": "Some airlines only. Of Indian airlines only Air India is included; IndiGo, Akasa, "
                                                      "SpiceJet and Air India Express are not, so cheaper domestic fares may exist."}


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
