"""Safety notes for a trip about to start (owner approved 2026-11-19): recent strong earthquakes near the destination
(USGS, public, no key), current air quality there (Google Air Quality, with the same Google key as the map) and,
since 2026-11-25, official NDMA SACHET alerts covering it (public domain, no key).

Only the destination's coordinates (and, for SACHET, its state name) leave this PC. Notes only: ALFRED never cancels
or changes a trip.
"""
from datetime import datetime, timedelta, timezone as dt_timezone

import hashlib
import json

from alfred_ai.services import personal_keys
from alfred_ai.services.public_http import PublicHTTPError, request
from django.utils import timezone

from .base import Provider, ProviderError, number, request_json
from .geocoding import GOOGLE_KEY, google_unavailable

QUAKE_RADIUS_KM, QUAKE_MAGNITUDE, QUAKE_DAYS = 300, 5.0, 7
POOR_AIR = 40  # Google's Universal AQI runs from 0 (poor) to 100 (excellent)


class UsgsEarthquakes(Provider):
    name = "usgs_earthquakes"
    category = "earthquakes"
    source_url = "https://earthquake.usgs.gov/earthquakes/map/"
    attribution = "Earthquakes by the US Geological Survey; follow local authorities' advice"
    ttl = timedelta(hours=3)
    allowed_parameters = {"latitude", "longitude", "since"}
    limits = {"minute": 5, "hour": 30, "day": 200, "month": 3000}

    def unavailable_reason(self):
        return ""

    def fetch(self, p):
        params = {"format": "geojson", "latitude": number(p["latitude"], low=-90, high=90),
                  "longitude": number(p["longitude"], low=-180, high=180), "maxradiuskm": QUAKE_RADIUS_KM,
                  "minmagnitude": QUAKE_MAGNITUDE, "starttime": p["since"], "orderby": "magnitude", "limit": 5}
        return request_json("GET", "https://earthquake.usgs.gov/fdsnws/event/1/query", params=params)

    def normalize(self, raw, p):
        quakes = []
        for feature in raw.get("features") or []:
            props = feature.get("properties") or {}
            magnitude = number(props.get("mag"), low=0, high=10)
            when = datetime.fromtimestamp(int(props["time"]) / 1000, tz=dt_timezone.utc)
            quakes.append({"magnitude": round(magnitude, 1), "place": str(props.get("place") or "")[:120],
                           "when": timezone.localtime(when).strftime("%d %b %H:%M"), "tsunami": bool(props.get("tsunami")),
                           "url": str(props.get("url") or "") if str(props.get("url") or "").startswith("https://earthquake.usgs.gov/") else ""})
        return {"quakes": quakes}


class GoogleAirQuality(Provider):
    name = "google_air_quality"
    category = "air_quality"
    source_url = "https://developers.google.com/maps/documentation/air-quality"
    attribution = "Air quality by Google"
    ttl = timedelta(hours=3)
    allowed_parameters = {"latitude", "longitude"}
    limits = {"minute": 5, "hour": 30, "day": 100, "month": 2000}

    def unavailable_reason(self):
        return google_unavailable()

    def fetch(self, p):
        body = {"location": {"latitude": number(p["latitude"], low=-90, high=90), "longitude": number(p["longitude"], low=-180, high=180)}}
        return request_json("POST", "https://airquality.googleapis.com/v1/currentConditions:lookup", json=body,
                            headers={"X-Goog-Api-Key": personal_keys.get(GOOGLE_KEY)})

    def normalize(self, raw, p):
        for index in raw.get("indexes") or []:
            if index.get("code") == "uaqi":
                return {"aqi": int(number(index.get("aqi"), low=0, high=100)), "category": str(index.get("category") or "")[:60],
                        "pollutant": str(index.get("dominantPollutant") or "")[:20]}
        raise ProviderError("no_air_quality_index")


SACHET = "https://sachet.ndma.gov.in/cap_public_website/"
SACHET_PORTAL = "https://sachet.ndma.gov.in/"
SACHET_MAX_ALERTS = 6  # each alert costs two more requests (its CAP file and its area polygon)
XML_TYPES = ("application/xml", "text/xml", "application/rss+xml")


def _xml(url, params=None):
    """Bounded fetch of one official SACHET XML file. DTDs and entities are refused, so nothing can expand."""
    from xml.etree import ElementTree

    try:
        body = request("GET", url, params=params, content_types=XML_TYPES, max_bytes=2_000_000).content
    except PublicHTTPError as exc:
        raise ProviderError(exc.code, retry_after=exc.retry_after) from None
    if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
        raise ProviderError("malformed_response")
    try:
        return ElementTree.fromstring(body)
    except ElementTree.ParseError:
        raise ProviderError("malformed_response") from None


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _when(text):
    try:
        value = datetime.fromisoformat(str(text or "").strip())
    except ValueError:
        return None
    return value if value.tzinfo else None


def _inside(lat, lon, ring):
    """Ray casting over (lat, lon) pairs; alert areas are small enough for a flat plane."""
    inside = False
    for (a_lat, a_lon), (b_lat, b_lon) in zip(ring, ring[1:] + ring[:1]):
        if (a_lat > lat) != (b_lat > lat) and lon < (b_lon - a_lon) * (lat - a_lat) / (b_lat - a_lat) + a_lon:
            inside = not inside
    return inside


def _rings(root):
    rings = []
    for node in root.iter():
        if _local(node.tag) == "polygon" and node.text:
            try:
                ring = [(float(lat), float(lon)) for lat, lon in (pair.split(",") for pair in node.text.split())]
            except ValueError:
                continue
            if len(ring) >= 3:
                rings.append(ring)
    return rings


class SachetAlerts(Provider):
    """Current official warnings (CAP 1.2) from NDMA's SACHET feed whose area polygon covers the destination.

    The feed marks itself "public domain". Only the destination's state name (to pick the state feed) is sent; the
    coordinates stay on this PC, because each alert's polygon is downloaded and matched here.
    """
    name = "ndma_sachet"
    category = "official_alerts"
    source_url = SACHET_PORTAL
    attribution = "Official alerts from NDMA SACHET (public domain); the issuing agency is named on each alert"
    ttl = timedelta(minutes=30)  # nowcasts last about three hours
    allowed_parameters = {"latitude", "longitude", "state"}
    limits = {"minute": 4, "hour": 20, "day": 100, "month": 2000}

    def unavailable_reason(self):
        return ""

    def fetch(self, p):
        lat, lon = number(p["latitude"], low=-90, high=90), number(p["longitude"], low=-180, high=180)
        slug = "".join(ch for ch in str(p.get("state") or "").lower() if "a" <= ch <= "z")
        feed, scope = None, "India"
        if slug:
            try:
                feed, scope = _xml(f"{SACHET}rss/rss_{slug}.xml"), str(p["state"])[:60]
            except ProviderError:
                feed = None  # states without a feed of their own (two-word names, for one) use the national feed
        feed = feed if feed is not None else _xml(f"{SACHET}rss/rss_india.xml")
        now, alerts, unplaced = timezone.now(), [], 0
        ids = [node.text.strip() for node in feed.iter() if _local(node.tag) == "guid" and (node.text or "").strip().isdigit()]
        for identifier in ids[:SACHET_MAX_ALERTS]:
            cap = _xml(f"{SACHET}FetchXMLFile", {"identifier": identifier})
            fields = {_local(n.tag): (n.text or "").strip() for n in cap if len(n) == 0}
            infos = [i for i in cap if _local(i.tag) == "info"]
            if fields.get("status") != "Actual" or fields.get("msgType") == "Cancel" or not infos:
                continue
            english = [i for i in infos if any(_local(n.tag) == "language" and (n.text or "").lower().startswith("en") for n in i)]
            info = (english or infos)[0]
            values = {_local(n.tag): (n.text or "").strip() for n in info if len(n) == 0}
            expires = _when(values.get("expires"))
            if expires is None or expires <= now:
                continue
            try:
                rings = _rings(_xml(f"{SACHET}FetchPolygonXMLFile", {"identifier": identifier}))
            except ProviderError:
                rings = []
            if not rings:
                unplaced += 1  # an alert we cannot place is never shown as "not here"
                continue
            if any(_inside(lat, lon, ring) for ring in rings):
                alerts.append({"event": values.get("event", "")[:80], "severity": values.get("severity", "")[:20],
                               "headline": values.get("headline", "")[:300], "agency": fields.get("sender", "")[:80],
                               "area": " / ".join((n.text or "").strip() for n in info.iter() if _local(n.tag) == "areaDesc")[:200],
                               "expires": expires.isoformat()})
        raw = {"alerts": alerts, "unplaced": unplaced, "checked": len(ids[:SACHET_MAX_ALERTS]), "feed": scope}
        return raw, hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()

    def normalize(self, raw, p):
        return raw


def destination_point(plan):
    """The trip's destination (the map's overnight point), or None before research has placed it."""
    for feature in ((plan.itinerary or {}).get("map") or {}).get("features") or []:
        if (feature.get("properties") or {}).get("kind") == "overnight":
            lon, lat = (feature.get("geometry") or {}).get("coordinates") or (None, None)
            try:
                return round(number(lat, low=-90, high=90), 3), round(number(lon, low=-180, high=180), 3)
            except (TypeError, ValueError):
                return None
    return None
