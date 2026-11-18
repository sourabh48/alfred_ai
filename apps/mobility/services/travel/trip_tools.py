"""Trip tools (TREK 2bcfc1bf ideas, AGPL, independent implementation; owner approval 2026-11-18).

Bookings the owner already made (ALFRED records them, it never books), a recorded GPX ride compared with the plan, with
its elevation profile and grades, and places imported from the owner's own KML, GPX or Google Takeout files. Everything
stays on this PC. A confirmation is read by the owner's local AI only, and a field is offered only when its words are in
the confirmation; the owner checks the form before anything is saved.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import time
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from django.utils import timezone

from apps.reports.models import OperationalLog
from apps.reports.services import operational_logging_service

SCOPE = "trip-tools"
KINDS = ("flight", "train", "bus", "hotel", "car", "event", "other")
BOOKING_LIMIT, PLACE_LIMIT, POINT_LIMIT, PROFILE_POINTS = 60, 300, 200_000, 150
CODE_RE = re.compile(r"\b(?:PNR|booking (?:reference|ref\.?|id|number)|confirmation (?:number|code|no\.?)|reservation (?:number|code))"
                     r"\s*[:#]?\s*([A-Z0-9]{5,12})\b", re.I)


def _records(user, event):
    return OperationalLog.objects.filter(user=user, module="travel", scope=SCOPE, event_type=event)


def _latest(user, event, default):
    row = _records(user, event).order_by("-created_at", "-id").first()
    return row.payload.get("items", default) if row else default


def _save(user, event, message, items):
    operational_logging_service.log(user=user, module="travel", category="api", scope=SCOPE, event_type=event,
                                     message=message, payload={"items": items})
    return items


def _clean(value, limit=200) -> str:
    return " ".join(str(value or "").split())[:limit]


def state(user, plan) -> dict:
    return {"plan_id": plan.pk, "bookings": _latest(user, f"bookings:{plan.pk}", []),
            "ride": _latest(user, f"ride:{plan.pk}", None), "places": _latest(user, f"places:{plan.pk}", []),
            "planned_km": planned_km(plan)}


# ---- bookings ------------------------------------------------------------------------------------------------------

def _when(value) -> str:
    value = _clean(value, 25)
    if not value:
        return ""
    for shape in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:16] if "T" in value else value[:10], shape).strftime(shape)
        except ValueError:
            continue
    raise ValueError("Write dates as YYYY-MM-DD, with an optional time (YYYY-MM-DDTHH:MM).")


def clean_booking(data: dict) -> dict:
    kind = _clean(data.get("kind"), 10).lower()
    if kind not in KINDS:
        raise ValueError(f"Choose a kind: {', '.join(KINDS)}.")
    title = _clean(data.get("title"), 160)
    if not title:
        raise ValueError("Give the booking a title, e.g. the flight number or hotel name.")
    start, end = _when(data.get("start")), _when(data.get("end"))
    if start and end and end[:10] < start[:10]:
        raise ValueError("The end comes before the start.")
    amount, currency = _clean(data.get("amount"), 20).replace(",", ""), _clean(data.get("currency"), 3).upper()
    if amount:
        try:
            parsed = Decimal(amount)
        except InvalidOperation:
            raise ValueError("The amount is not a number.") from None
        if not parsed.is_finite() or parsed < 0 or parsed > Decimal("100000000"):
            raise ValueError("The amount is out of range.")
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ValueError("Give the amount's 3-letter currency, e.g. INR.")
        amount = str(parsed.quantize(Decimal("0.01")))
    booking = {"kind": kind, "title": title, "confirmation": _clean(data.get("confirmation"), 40), "start": start, "end": end,
               "place": _clean(data.get("place")), "provider": _clean(data.get("provider"), 120), "amount": amount,
               "currency": currency if amount else "", "notes": _clean(data.get("notes"), 500)}
    booking["id"] = hashlib.sha1(json.dumps(booking, sort_keys=True).encode()).hexdigest()[:12]
    return booking


def add_booking(user, plan, data) -> list:
    bookings = _latest(user, f"bookings:{plan.pk}", [])
    booking = clean_booking(data if isinstance(data, dict) else {})
    if any(b["id"] == booking["id"] for b in bookings):
        return bookings
    if len(bookings) >= BOOKING_LIMIT:
        raise ValueError(f"A trip keeps up to {BOOKING_LIMIT} bookings.")
    bookings = sorted(bookings + [booking], key=lambda b: (b["start"] or "9999", b["title"]))
    return _save(user, f"bookings:{plan.pk}", "Booking recorded", bookings)


def remove_booking(user, plan, booking_id) -> list:
    bookings = _latest(user, f"bookings:{plan.pk}", [])
    kept = [b for b in bookings if b["id"] != booking_id]
    return _save(user, f"bookings:{plan.pk}", "Booking removed", kept) if len(kept) != len(bookings) else bookings


def _reasoner():
    from apps.investments.services.research_challenge import local_reasoner
    return local_reasoner()


def _squash(text: str) -> str:
    return " ".join(str(text).casefold().split())


def read_confirmation(text: str, *, reasoner=None) -> dict:
    """A draft booking from a confirmation's text. Only fields whose words are in the text survive; nothing is saved."""
    from apps.investments.services.research_challenge import wait_seconds

    text = str(text or "")[:20000]
    if len(text.strip()) < 30:
        raise ValueError("Paste the confirmation text, or load its PDF (at least a few lines).")
    source = _squash(text)
    code = CODE_RE.search(text)
    draft = {"confirmation": code.group(1) if code else ""}
    ask = {"task": "Copy booking details from this confirmation. Answer JSON only with keys kind (one of " + ", ".join(KINDS) +
                   "), title, confirmation, start_as_written, start (YYYY-MM-DD or YYYY-MM-DDTHH:MM), end_as_written, end, "
                   "place, provider, amount_as_written, currency (3 letters). Copy words exactly as they appear; use an "
                   "empty string for anything not in the text. Never guess.",
           "confirmation_text": text}
    note = "Read by your local AI. Fields not found word for word in the confirmation were left empty. Check every field."
    try:
        raw = (reasoner or _reasoner()).reason(ask, max_output_tokens=500, deadline=time.monotonic() + wait_seconds())
        match = re.search(r"\{.*\}", raw or "", re.S)
        found = json.loads(match.group(0)) if match else {}
        found = found if isinstance(found, dict) else {}
    except Exception:  # local AI off or broken: keep what the plain rules found
        found, note = {}, "Your local AI could not read it now; only the confirmation code was found by plain rules. Fill in the rest."
    there = lambda value: bool(_clean(value)) and _squash(value) in source
    for field in ("title", "confirmation", "place", "provider"):
        if there(found.get(field)) and not draft.get(field):
            draft[field] = _clean(found[field], 160)
    kind = _clean(found.get("kind"), 10).lower()
    draft["kind"] = kind if kind in KINDS else "other"
    for field in ("start", "end"):
        written, value = found.get(f"{field}_as_written"), _clean(found.get(field), 16)
        try:
            day = _when(value)
        except ValueError:
            day = ""
        # the ISO date must come from words in the text, and its day number must be in those words
        if day and there(written) and int(day[8:10]) in {int(d) for d in re.findall(r"\d+", str(written))}:
            draft[field] = day
    amount = re.sub(r"[^\d.]", "", str(found.get("amount_as_written") or ""))
    currency = _clean(found.get("currency"), 3).upper()
    if amount and there(found.get("amount_as_written")) and re.fullmatch(r"[A-Z]{3}", currency):
        draft["amount"], draft["currency"] = amount, currency
    return {"draft": draft, "basis": note}


# ---- recorded ride (GPX) -------------------------------------------------------------------------------------------

def _xml(raw: bytes):
    if re.search(rb"<!(?:DOCTYPE|ENTITY)", raw[:4096], re.I):
        raise ValueError("That file declares its own XML entities; ALFRED does not read those.")
    try:
        return ElementTree.fromstring(raw)
    except ElementTree.ParseError:
        raise ValueError("That file is not valid XML.") from None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _km(a, b) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 12742 * math.asin(math.sqrt(min(1, h)))


def _point(element):
    try:
        lat, lon = float(element.get("lat")), float(element.get("lon"))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    ele = when = None
    for child in element:
        name = _local(child.tag)
        if name == "ele":
            try:
                ele = float(child.text)
            except (TypeError, ValueError):
                ele = None
        elif name == "time" and child.text:
            try:
                when = datetime.fromisoformat(child.text.strip().replace("Z", "+00:00"))
            except ValueError:
                when = None
    return lat, lon, ele, when


def analyse_track(raw: bytes) -> dict:
    """Distance, climb, time, grades and an elevation profile from a GPX track (or route) the owner recorded."""
    root = _xml(raw)
    if _local(root.tag) != "gpx":
        raise ValueError("That is not a GPX file.")
    elements = [e for e in root.iter() if _local(e.tag) == "trkpt"] or [e for e in root.iter() if _local(e.tag) == "rtept"]
    if len(elements) > POINT_LIMIT:
        raise ValueError(f"The track has more than {POINT_LIMIT:,} points.")
    points = [p for p in map(_point, elements) if p]
    if len(points) < 2:
        raise ValueError("The file has fewer than two track points.")
    km = moving = 0.0
    ascent = descent = 0.0
    anchor = next((p[2] for p in points if p[2] is not None), None)
    profile, segment_start, climbs = [(0.0, points[0][2])], (0.0, points[0][2]), []
    for a, b in zip(points, points[1:]):
        step = _km(a, b)
        km += step
        if a[3] and b[3]:
            seconds = (b[3] - a[3]).total_seconds()
            if 0 < seconds <= 600 and step / (seconds / 3600) >= 1:  # stopped time and long gaps are not riding time
                moving += seconds
        if b[2] is not None and anchor is not None:
            if b[2] - anchor >= 3:  # a 3 m band hides GPS height noise
                ascent, anchor = ascent + b[2] - anchor, b[2]
            elif anchor - b[2] >= 3:
                descent, anchor = descent + anchor - b[2], b[2]
        profile.append((km, b[2]))
        if b[2] is not None and segment_start[1] is not None and km - segment_start[0] >= 0.1:
            climbs.append((b[2] - segment_start[1]) / ((km - segment_start[0]) * 1000) * 100)
            segment_start = (km, b[2])
        elif segment_start[1] is None:
            segment_start = (km, b[2])
    times = [p[3] for p in points if p[3]]
    total = (times[-1] - times[0]).total_seconds() if len(times) >= 2 else None
    heights = [p[2] for p in points if p[2] is not None]
    step = max(1, len(profile) // PROFILE_POINTS)
    sampled = [{"km": round(k, 2), "m": round(m)} for k, m in profile[::step] + [profile[-1]] if m is not None]
    return {"points": len(points), "distance_km": round(km, 2), "ascent_m": round(ascent) if heights else None,
            "descent_m": round(descent) if heights else None, "highest_m": round(max(heights)) if heights else None,
            "lowest_m": round(min(heights)) if heights else None, "total_hours": round(total / 3600, 2) if total else None,
            "moving_hours": round(moving / 3600, 2) if moving else None,
            "steepest_climb_pct": round(max(climbs), 1) if climbs and max(climbs) > 0 else None,
            "steepest_descent_pct": round(-min(climbs), 1) if climbs and min(climbs) < 0 else None,
            "started": times[0].isoformat() if times else None, "profile": sampled if heights else []}


def planned_km(plan):
    route = (plan.itinerary or {}).get("route") or {}
    for key in ("distance_km_total", "distance_km_one_way"):
        try:
            value = float(route.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return round(value, 1)
    return None


def save_ride(user, plan, raw: bytes, name: str) -> dict:
    ride = analyse_track(raw)
    ride["file"], ride["loaded_at"] = _clean(name, 120), timezone.now().isoformat()
    planned = planned_km(plan)
    ride["compare"] = None if planned is None else {
        "planned_km": planned, "difference_km": round(ride["distance_km"] - planned, 1),
        "basis": "The plan's distance is ALFRED's planning estimate; the ride is what your GPS recorded."}
    return _save(user, f"ride:{plan.pk}", "Recorded ride loaded", ride)


# ---- places import -------------------------------------------------------------------------------------------------

def _place(name, lat=None, lon=None, note="", link="", source=""):
    name = _clean(name, 160)
    if not name:
        return None
    if lat is not None:
        try:
            lat, lon = round(float(lat), 6), round(float(lon), 6)
        except (TypeError, ValueError):
            lat = lon = None
        if lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180):
            lat = lon = None
    link = link if isinstance(link, str) and re.match(r"https://(?:www\.)?(?:google\.[a-z.]+/maps|maps\.google\.[a-z.]+|maps\.app\.goo\.gl)/", link) else ""
    return {"id": hashlib.sha1(f"{name.casefold()}|{lat}|{lon}".encode()).hexdigest()[:12], "name": name, "lat": lat, "lon": lon,
            "note": _clean(note, 300), "link": link[:400], "source": source}


def read_places(raw: bytes, name: str) -> list:
    """Places from a KML, GPX, Google Takeout GeoJSON (Saved Places) or Takeout list CSV file."""
    extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    source = _clean(name, 120)
    if extension in {"kml", "gpx"}:
        root = _xml(raw)
        if extension == "gpx":
            return [p for p in (_place(next((c.text for c in w if _local(c.tag) == "name"), ""), w.get("lat"), w.get("lon"),
                                       next((c.text for c in w if _local(c.tag) == "desc"), ""), source=source)
                                for w in root.iter() if _local(w.tag) == "wpt") if p]
        places = []
        for mark in (e for e in root.iter() if _local(e.tag) == "Placemark"):
            label = next((c.text for c in mark if _local(c.tag) == "name"), "")
            coords = next((c.text for c in mark.iter() if _local(c.tag) == "coordinates"), "") or ""
            parts = coords.strip().split()[0].split(",") if coords.strip() else []
            places.append(_place(label, parts[1] if len(parts) > 1 else None, parts[0] if len(parts) > 1 else None,
                                 next((c.text for c in mark if _local(c.tag) == "description"), ""), source=source))
        return [p for p in places if p]
    text = raw.decode("utf-8-sig", "replace")
    if extension in {"json", "geojson"}:
        try:
            features = json.loads(text).get("features") or []
        except (ValueError, AttributeError):
            raise ValueError("That JSON file is not GeoJSON.") from None
        places = []
        for feature in features[:PLACE_LIMIT * 4]:
            props = feature.get("properties") or {}
            location = props.get("location") or {}
            coords = (feature.get("geometry") or {}).get("coordinates") or []
            label = location.get("name") or props.get("Title") or props.get("name") or location.get("address") or ""
            lat, lon = (coords[1], coords[0]) if len(coords) >= 2 and coords[:2] != [0, 0] else (None, None)
            places.append(_place(label, lat, lon, location.get("address") or "", props.get("google_maps_url") or "", source))
        return [p for p in places if p]
    if extension == "csv":
        rows = csv.DictReader(io.StringIO(text))
        return [p for p in (_place(r.get("Title"), note=r.get("Note") or "", link=r.get("URL") or "", source=source)
                            for r in rows) if p]
    raise ValueError("Load a .kml, .gpx, .geojson/.json (Google Takeout Saved Places) or .csv (Google Takeout saved list) file.")


def import_places(user, plan, raw: bytes, name: str) -> dict:
    found = read_places(raw, name)
    places = _latest(user, f"places:{plan.pk}", [])
    known = {p["id"] for p in places}
    added = [p for p in found if p["id"] not in known and not known.add(p["id"])][:max(0, PLACE_LIMIT - len(places))]
    _save(user, f"places:{plan.pk}", "Places imported", places + added)
    return {"found": len(found), "added": len(added)}


def remove_place(user, plan, place_id) -> list:
    places = _latest(user, f"places:{plan.pk}", [])
    kept = [p for p in places if p["id"] != place_id]
    return _save(user, f"places:{plan.pk}", "Place removed", kept) if len(kept) != len(places) else places


# ---- public transport and holidays (Google transit, Nager.Date) ----------------------------------------------------

def transit(origin, destination, departure="") -> dict:
    from .cache import query
    from .providers.routing import GoogleTransit

    origin, destination = _clean(origin), _clean(destination)
    if not origin or not destination:
        raise ValueError("Give a start and an end address.")
    params = {"origin": origin, "destination": destination}
    if departure:
        moment = _when(departure)
        if "T" not in moment:
            raise ValueError("Give a departure date and time.")
        aware = timezone.make_aware(datetime.strptime(moment, "%Y-%m-%dT%H:%M"))
        if aware < timezone.now():
            raise ValueError("Choose a departure time in the future.")
        params["departure"] = aware.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result = query(GoogleTransit(), params)
    if not result.success:
        raise ValueError({"missing_TRAVEL_GOOGLE_MAPS_API_KEY": "Add your Google Maps key in Settings to see public transport.",
                          "no_route": "Google found no public transport between those places."}.get(
            result.error, "Google public transport is not available right now. Try again later."))
    return {**result.payload, "stale": result.stale, "attribution": result.attribution}


def holidays(country="", year=None, user=None) -> dict:
    from .cache import query
    from .offline_maps import home_country
    from .providers.holidays import NagerHolidays

    country = (_clean(country, 2) or home_country()).upper()
    year = int(year or timezone.localdate().year)
    if not re.fullmatch(r"[A-Z]{2}", country):
        raise ValueError("Choose a country.")
    result = query(NagerHolidays(), {"country": country, "year": year})
    if not result.success and result.error in {"country_not_covered", "no_holidays"} and user is not None:
        from alfred_ai.services import google_sync  # owner decision 2026-11-19: Google's holiday calendar where Nager.Date has none
        try:
            found = google_sync.public_holidays(user, country, year)
        except google_sync.SyncError as exc:
            raise ValueError(f"Nager.Date has no holidays for {country}. {exc}") from None
        return {"country": country, "year": year, **found, "attribution": "Holidays from Google Calendar",
                "basis": "Public holidays from Google Calendar's holiday calendar; restricted and optional days are marked. Check your employer's list."}
    if not result.success:
        raise ValueError(f"Nager.Date has no holidays for {country}; it does not cover every country." if result.error in
                         {"country_not_covered", "no_holidays"} else "Nager.Date cannot be reached right now. Try again later.")
    return {"country": country, "year": year, **result.payload, "attribution": result.attribution,
            "basis": "Public holidays from Nager.Date; regional holidays apply only where listed. Check your employer's list."}
