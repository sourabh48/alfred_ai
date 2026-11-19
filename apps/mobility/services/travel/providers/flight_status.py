"""Live status of a flight the owner already booked (owner approved 2026-11-19).

AeroDataBox, published by its maker on RapidAPI, with the person's own RapidAPI key. Only the flight number and its
date leave this PC; never the booking reference, name or price. Read-only: ALFRED shows the status and never rebooks.
"""
import re
from datetime import date, datetime, timedelta

from alfred_ai.services import personal_keys

from .base import Provider, ProviderError, request_json

KEY = "ALFRED_AERODATABOX_API_KEY"
HOST = "aerodatabox.p.rapidapi.com"
FLIGHT = re.compile(r"\b([A-Z][A-Z0-9]|[A-Z0-9][A-Z])\s?-?\s?(\d{1,4})\b")


def flight_number(title):
    """'AI 504 BLR-DEL' -> 'AI504'; None when the title holds no airline code and number."""
    found = FLIGHT.search(str(title or "").upper())
    return f"{found.group(1)}{int(found.group(2))}" if found else None


def _local(moment):
    """AeroDataBox gives local times as {'local': '2026-11-20 09:30+05:30'} (older replies: a plain string)."""
    text = (moment or {}).get("local") if isinstance(moment, dict) else moment
    try:
        return datetime.fromisoformat(str(text).replace(" ", "T")) if text else None
    except ValueError:
        return None


class AeroDataBoxStatus(Provider):
    name = "aerodatabox"
    category = "flight_status"
    source_url = "https://aerodatabox.com/"
    attribution = "Flight status by AeroDataBox; recheck with the airline before you leave"
    ttl = timedelta(minutes=30)
    allowed_parameters = {"number", "date"}
    limits = {"minute": 2, "hour": 10, "day": 20, "month": 250}  # stays inside the free plan

    def unavailable_reason(self):
        return "" if personal_keys.get(KEY) else f"missing_{KEY}"

    def parameters(self, parameters):
        clean = super().parameters(parameters)
        if not re.fullmatch(r"[A-Z0-9]{2}\d{1,4}", str(clean.get("number") or "")):
            raise ProviderError("invalid_flight_number")
        date.fromisoformat(str(clean.get("date")))
        return clean

    def fetch(self, p):
        return request_json("GET", f"https://{HOST}/flights/number/{p['number']}/{p['date']}",
                            params={"withAircraftImage": "false", "withLocation": "false"},
                            headers={"X-RapidAPI-Key": personal_keys.get(KEY), "X-RapidAPI-Host": HOST})

    def normalize(self, raw, p):
        for flight in raw if isinstance(raw, list) else []:
            leave, arrive = flight.get("departure") or {}, flight.get("arrival") or {}
            scheduled = _local(leave.get("scheduledTime") or leave.get("scheduledTimeLocal"))
            if scheduled is None or scheduled.date().isoformat() != p["date"]:
                continue
            revised = _local(leave.get("revisedTime") or leave.get("predictedTime") or leave.get("actualTimeLocal"))
            delay = round((revised - scheduled).total_seconds() / 60) if revised else 0
            where = lambda side: str(((side.get("airport") or {}).get("iata")) or "")[:3]
            return {"number": p["number"], "status": str(flight.get("status") or "Unknown")[:30],
                    "from": where(leave), "to": where(arrive), "scheduled": scheduled.strftime("%H:%M"),
                    "expected": revised.strftime("%H:%M") if revised else None, "delay_minutes": max(delay, 0),
                    "terminal": str(leave.get("terminal") or "")[:8], "gate": str(leave.get("gate") or "")[:8]}
        raise ProviderError("flight_not_found")


def describe(status):
    """One line for a trip step, e.g. 'AI504 BLR→DEL: Delayed, now 10:15 (was 09:30); terminal 2, gate 12.'"""
    line = f"{status['number']} {status['from']}→{status['to']}: {status['status']}"
    if status["delay_minutes"] >= 5 and status["expected"]:
        line += f", now {status['expected']} (was {status['scheduled']}, {status['delay_minutes']} min late)"
    else:
        line += f", departs {status['expected'] or status['scheduled']}"
    extra = [f"terminal {status['terminal']}" if status["terminal"] else "", f"gate {status['gate']}" if status["gate"] else ""]
    return line + ("; " + ", ".join(e for e in extra if e) if any(extra) else "") + ". Recheck with the airline before you leave."
