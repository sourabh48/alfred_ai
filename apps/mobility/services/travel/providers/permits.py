"""Dated official references, not a fabricated live permit/booking API.

No website HTML is copied or automatically scraped. Extend via an authorized
adapter when a department publishes an API with suitable terms.
"""
from datetime import date, timedelta
import re

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .base import ProviderResult

# Each entry was read by hand on the official page named in "source" on its "reviewed" date (Indian visitors).
# Ladakh, Sikkim and Rohtang are left out: their official permit portals could not be read on 2026-11-25.
REFERENCES = (
    {"places": ("chembra",),
     "source": "https://www.keralatourism.org/destination/chembra-peak-wayanad/508/",
     "authority": "Kerala Forest Department (referenced by Kerala Tourism)",
     "requirement": "Trekking permit from the Forest Department at the base camp; entry and guide fees apply.",
     "booking_url": "https://forest.kerala.gov.in/en/ecotourism/", "reviewed": "2026-11-25T06:00:00+00:00"},
    {"places": ("kudremukh",),
     "source": "https://aranyavihaara.karnataka.gov.in/",
     "authority": "Karnataka Forest Department (Aranya Vihaara)",
     "requirement": "Trek must be booked online 1 to 30 days ahead for a time slot; carry an original photo ID.",
     "booking_url": "https://aranyavihaara.karnataka.gov.in/", "reviewed": "2026-11-25T06:00:00+00:00"},
    {"places": ("arunachal", "tawang", "ziro", "bomdila", "dirang", "itanagar", "mechuka", "sela pass", "pasighat", "roing"),
     "source": "https://eilp.arunachal.gov.in/",
     "authority": "Government of Arunachal Pradesh (Tourist e-ILP, Bengal Eastern Frontier Regulation, 1873)",
     "requirement": "Tourist Inner Line Permit (e-ILP) needed by visitors from outside Arunachal Pradesh.",
     "booking_url": "https://eilp.arunachal.gov.in/", "reviewed": "2026-11-25T06:00:00+00:00"},
    {"places": ("nagaland", "kohima", "dzukou", "mokokchung", "mon", "chumoukedima", "niuland", "dimapur"),
     "source": "https://ilp.nagaland.gov.in/",
     "authority": "Government of Nagaland (ILP portal)",
     "requirement": "Inner Line Permit needed by visitors from outside Nagaland; extended to Chumoukedima and Niuland in 2025.",
     "booking_url": "https://ilp.nagaland.gov.in/ilp/apply", "reviewed": "2026-11-25T06:00:00+00:00"},
    {"places": ("manipur", "imphal", "loktak", "moirang", "ukhrul"),
     "source": "https://manipurilponline.mn.gov.in/",
     "authority": "Government of Manipur (ILP under the Bengal Eastern Frontier Regulation, 1873)",
     "requirement": "Inner Line Permit needed by every Indian citizen from outside Manipur; tourist temporary permit 30 days, INR 100.",
     "booking_url": "https://manipurilponline.mn.gov.in/forms/aadhaarotp.aspx", "reviewed": "2026-11-25T06:00:00+00:00"},
    {"places": ("mizoram", "aizawl", "lunglei", "champhai"),
     "source": "https://ilp.mizoram.gov.in/",
     "authority": "Government of Mizoram (Inner Line Pass)",
     "requirement": "Inner Line Pass needed by everyone who is not indigenous to Mizoram; temporary passes are applied for online.",
     "booking_url": "https://ilp.mizoram.gov.in/", "reviewed": "2026-11-25T06:00:00+00:00"},
    {"places": ("lakshadweep", "agatti", "kavaratti", "bangaram", "minicoy", "kadmat"),
     "source": "https://epermit.utl.gov.in/",
     "authority": "U.T. Administration of Lakshadweep (entry permit, 1967 Rules)",
     "requirement": "Entry permit needed by every visitor who is not a native of the islands; apply in the Tourist category.",
     "booking_url": "https://epermit.utl.gov.in/", "reviewed": "2026-11-25T06:00:00+00:00"},
)


def reference_for(place):
    text = place.casefold()
    return next((ref for ref in REFERENCES if any(re.search(rf"\b{re.escape(word)}\b", text) for word in ref["places"])), None)


class PermitProvider:
    name = "official_reference"
    category = "permits"

    def lookup(self, place, *, start_date=None):
        ref = reference_for(place) or {}
        source, authority = ref.get("source", ""), ref.get("authority", "")
        reviewed = parse_datetime(ref["reviewed"]) if ref else None
        requirement = ref.get("requirement", "UNKNOWN")
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
                     "booking_url": ref.get("booking_url", ""),
                     "recheck": "Confirm current opening, permit process, quota, fees and closures shortly before departure."})
