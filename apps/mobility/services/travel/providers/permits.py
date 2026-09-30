"""Dated official references, not a fabricated live permit/booking API.

No website HTML is copied or automatically scraped. Extend via an authorized
adapter when a department publishes an API with suitable terms.
"""
from datetime import date, timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .base import ProviderResult


class PermitProvider:
    name = "official_reference"
    category = "permits"

    def lookup(self, place, *, start_date=None):
        source = ""
        authority = ""
        reviewed = None
        requirement = "UNKNOWN"
        if "chembra" in place.casefold():
            source = "https://www.keralatourism.org/destination/chembra-peak-wayanad/508/"
            authority = "Kerala Forest Department (referenced by Kerala Tourism)"
            reviewed = parse_datetime("2026-09-29T12:40:00+00:00")
            requirement = "Forest Department permit required according to the dated tourism reference."
        now = timezone.now()
        near = bool(start_date and 0 <= (date.fromisoformat(start_date)-timezone.localdate()).days <= 7)
        expires = reviewed+timedelta(hours=6 if near else 24) if reviewed else None
        stale = bool(expires and expires <= now)
        return ProviderResult(self.name, self.category, success=bool(reviewed),
            status="reference_only" if reviewed else "unverified",
            freshness="CACHED" if stale else "STATIC_REFERENCE" if reviewed and reviewed <= now else "UNKNOWN",
            confidence="LIKELY" if reviewed and not stale else "UNKNOWN", source_url=source,
            attribution="Official reference manually reviewed; no live access/permit inventory verified",
            retrieved_at=reviewed.isoformat() if reviewed else None,
            verified_at=reviewed.isoformat() if reviewed else None,
            expires_at=expires.isoformat() if expires else None, stale=stale, cached=bool(reviewed),
            request_parameters={"place": place, "start_date": start_date}, error="live_permit_verification_unavailable",
            payload={"place": place, "requirement": requirement, "authority": authority,
                     "status": "unverified", "opening_status": "UNKNOWN", "validity": "UNKNOWN",
                     "booking_process": "Verify directly with the authority", "opening_period": "UNKNOWN",
                     "daily_quota": None, "id_requirements": "UNKNOWN", "vehicle_restrictions": "UNKNOWN",
                     "contact_details": None, "last_verification": reviewed.isoformat() if reviewed else None,
                     "booking_url": "https://forest.kerala.gov.in/en/ecotourism/" if reviewed else "",
                     "recheck": "Confirm current opening, permit process, quota, fees and closures shortly before departure."})
