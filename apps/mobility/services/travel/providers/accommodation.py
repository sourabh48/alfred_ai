from datetime import date, timedelta
import os
import hashlib

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .base import Provider, ProviderError, number, request_json
from ..money import quoted_amount, estimated_nightly


class DuffelProvider(Provider):
    version = 2
    name = "duffel"
    source_url = "https://duffel.com/"
    attribution = "Search supplied by Duffel; recheck price and terms before purchase"
    ttl = timedelta(minutes=15)
    limits = {"minute": 8, "hour": 20, "day": 40, "month": 100}
    min_interval = 0

    @property
    def cache_partition(self):
        # Account-specific offers must not survive a credential/account change.
        return hashlib.sha256(os.getenv("TRAVEL_DUFFEL_API_KEY", "").encode()).hexdigest()

    def unavailable_reason(self):
        key = os.getenv("TRAVEL_DUFFEL_API_KEY", "")
        if not key:
            return "missing_TRAVEL_DUFFEL_API_KEY"
        if key.startswith("duffel_test_"):
            return "sandbox_token_not_live_inventory"
        if os.getenv("TRAVEL_DUFFEL_ALLOW_PAID_SEARCH") != "true":
            return "set_TRAVEL_DUFFEL_ALLOW_PAID_SEARCH_after_reviewing_fees"
        return ""

    def headers(self):
        return {"Authorization": "Bearer "+os.environ["TRAVEL_DUFFEL_API_KEY"],
                "Accept": "application/json", "Content-Type": "application/json", "Duffel-Version": "v2"}

    def expires_at(self, payload, parameters, retrieved):
        expiries = [parse_datetime(o["expires_at"]) for o in payload.get("options", [])]
        return min([retrieved+self.ttl]+[d for d in expiries if d and timezone.is_aware(d)])


class DuffelAccommodation(DuffelProvider):
    category = "hotels"
    allowed_parameters = {"latitude", "longitude", "check_in", "check_out", "adults", "rooms"}

    def fetch(self, p):
        check_in, check_out = date.fromisoformat(p["check_in"]), date.fromisoformat(p["check_out"])
        if not timezone.localdate() <= check_in <= timezone.localdate()+timedelta(days=330) or not 1 <= (check_out-check_in).days <= 30:
            raise ProviderError("invalid_stay_dates")
        adults = int(number(p.get("adults", 1), low=1, high=9))
        rooms = int(number(p.get("rooms", 1), low=1, high=9))
        return request_json("POST", "https://api.duffel.com/stays/search", headers=self.headers(), json={"data": {
            "location": {"radius": 10, "geographic_coordinates": {
                "latitude": number(p["latitude"], low=-90, high=90), "longitude": number(p["longitude"], low=-180, high=180)}},
            "check_in_date": check_in.isoformat(), "check_out_date": check_out.isoformat(),
            "rooms": rooms, "guests": [{"type": "adult"} for _ in range(adults)]}})

    def normalize(self, raw, p):
        options = []
        for item in raw["data"]["results"][:15]:
            expires = parse_datetime(item["expires_at"])
            if not expires or timezone.is_naive(expires):
                raise ProviderError("missing_offer_expiry")
            if expires <= timezone.now():
                continue
            hotel = item["accommodation"]
            coords = hotel["location"]["geographic_coordinates"]
            total = quoted_amount(item["cheapest_rate_total_amount"])
            due = item.get("cheapest_rate_due_at_accommodation_amount")
            due = quoted_amount(due) if due is not None else None
            currency = item["cheapest_rate_currency"]
            nights = (date.fromisoformat(item["check_out_date"])-date.fromisoformat(item["check_in_date"])).days
            if nights <= 0:
                raise ProviderError("invalid_stay_dates")
            options.append({"id": str(item["id"]), "name": str(hotel["name"])[:200], "provider": "Duffel",
                "availability": "search_result_requires_rate_confirmation", "total_price": total,
                "currency": currency, "taxes_fees": "UNKNOWN", "due_at_property": due,
                "due_at_property_currency": item.get("cheapest_rate_due_at_accommodation_currency"),
                "nightly_rate": estimated_nightly(total,nights), "nightly_rate_basis": "Estimated nightly average: search total divided by nights, rounded to 2 decimals for display, for all requested rooms; extra property charges may apply",
                "cancellation_policy": "UNKNOWN; fetch a selected rate before commitment",
                "rating": hotel.get("rating"), "review_score": hotel.get("review_score"),
                "lat": number(coords["latitude"], low=-90, high=90), "lon": number(coords["longitude"], low=-180, high=180),
                "distance_from_itinerary_km": None, "parking": "UNKNOWN", "bike_friendly": "UNKNOWN",
                "check_in": item["check_in_date"], "check_out": item["check_out_date"],
                "booking_url": None, "booking_note": "No public booking URL supplied. Confirm the rate with the provider or property; ALFRED does not book.",
                "expires_at": expires.isoformat()})
        return {"options": options, "coverage": "Matching provider inventory only; no matches do not establish that the destination is sold out."}
