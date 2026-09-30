from datetime import date
import re

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .accommodation import DuffelProvider
from .base import Provider, ProviderError, number, request_json
from ..money import quoted_amount


class DuffelFlights(DuffelProvider):
    category = "flights"
    allowed_parameters = {"origin", "destination", "departure_date", "return_date", "adults", "cabin_class"}

    def fetch(self, p):
        origin, destination = p["origin"].upper(), p["destination"].upper()
        if not re.fullmatch(r"[A-Z]{3}", origin) or not re.fullmatch(r"[A-Z]{3}", destination) or origin == destination:
            raise ProviderError("airport_codes_required")
        departure = date.fromisoformat(p["departure_date"])
        if departure < timezone.localdate():
            raise ProviderError("invalid_departure_date")
        slices = [{"origin":origin,"destination":destination,"departure_date":departure.isoformat()}]
        if p.get("return_date"):
            returning = date.fromisoformat(p["return_date"])
            if returning < departure:
                raise ProviderError("invalid_return_date")
            slices.append({"origin":destination,"destination":origin,"departure_date":returning.isoformat()})
        cabin = p.get("cabin_class", "economy")
        if cabin not in {"economy", "premium_economy", "business", "first"}:
            raise ProviderError("invalid_cabin_class")
        adults = int(number(p.get("adults",1),low=1,high=9))
        return request_json("POST", "https://api.duffel.com/air/offer_requests", headers=self.headers(),
            params={"return_offers":"true","supplier_timeout":10000},
            json={"data":{"slices":slices,"passengers":[{"type":"adult"} for _ in range(adults)],
                          "cabin_class":cabin,"max_connections":1}})

    def normalize(self, raw, p):
        if raw["data"].get("live_mode") is not True:
            raise ProviderError("sandbox_response_not_live_inventory")
        options = []
        for offer in raw["data"]["offers"][:20]:
            if offer.get("live_mode") is not True or offer.get("partial"):
                continue
            expiry = parse_datetime(offer["expires_at"])
            if not expiry or timezone.is_naive(expiry):
                raise ProviderError("missing_offer_expiry")
            if expiry <= timezone.now():
                continue
            slices = []
            for route in offer["slices"]:
                segments = route["segments"]
                slices.append({"origin":segments[0]["origin"]["iata_code"],
                    "destination":segments[-1]["destination"]["iata_code"],
                    "departure":segments[0]["departing_at"],"arrival":segments[-1]["arriving_at"],
                    "duration":route["duration"],"transfers":len(segments)-1,
                    "stops":sum(len(s.get("stops",[])) for s in segments),
                    "segments":[{"origin":s["origin"]["iata_code"],"destination":s["destination"]["iata_code"],
                        "departure":s["departing_at"],"arrival":s["arriving_at"],
                        "flight_number":str(s.get("marketing_carrier",{}).get("iata_code",""))+str(s.get("marketing_carrier_flight_number",""))} for s in segments]})
            if not slices:
                raise ProviderError("malformed_response")
            options.append({"id":offer["id"],"provider":"Duffel","carrier":offer.get("owner",{}).get("name"),
                "origin":slices[0]["origin"],"destination":slices[0]["destination"],
                "date":p.get("departure_date"),"departure":slices[0]["departure"],"arrival":slices[0]["arrival"],
                "duration":slices[0]["duration"],"transfers":slices[0]["transfers"],"slices":slices,
                "class":p.get("cabin_class","economy"),"fare":quoted_amount(offer["total_amount"]),
                "currency":offer["total_currency"],"fare_scope":"all requested passengers and slices; extras may cost more",
                "availability":"offer_returned_recheck_before_purchase","expires_at":expiry.isoformat(),
                "booking_url":None,"booking_note":"Provider supplied an API offer, not a public booking link. ALFRED does not issue tickets."})
        return {"options":options,"coverage":"Participating airlines and completed supplier searches only; not an exhaustive market comparison."}


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
