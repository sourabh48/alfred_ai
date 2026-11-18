"""One on-demand Google place photo. Photo names, credits and bytes are never persisted.

Places Photos (New), reviewed 2026-11-16:
https://developers.google.com/maps/documentation/places/web-service/place-photos
The shared boundary retains only public query metadata and applies its lease/budget.
"""
import base64
import re
from time import monotonic
from urllib.parse import urlsplit

from alfred_ai.services.public_http import PublicHTTPError, normalized_link, request
from ..discovery import km_between
from .base import Provider, ProviderError, number, request_json
from .geocoding import google_headers, google_unavailable
from .web import public_place


MAX_PHOTOS = 6
PLACE_ID = re.compile(r"[A-Za-z0-9_-]{1,200}\Z")
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


class GooglePlacePhoto(Provider):
    name = "google_place_photos"
    category = "photos"
    source_url = "https://www.google.com/maps"
    attribution = "Google Maps"
    cacheable = False  # Google photo resource names must be obtained afresh, never stored in evidence/cache.
    allowed_parameters = {"place_id", "name", "latitude", "longitude", "index"}
    # Photo loads, each bounded to two Google API calls and one image download.
    limits = {"minute": 12, "hour": 40, "day": 100, "month": 1000}
    min_interval = 0

    def unavailable_reason(self):
        return google_unavailable()

    def parameters(self, parameters):
        p = super().parameters(parameters)
        if type(p.get("index")) is not int or not 0 <= p["index"] < MAX_PHOTOS:
            raise ProviderError("invalid_photo_index")
        if p.get("place_id"):
            if not isinstance(p["place_id"], str) or not PLACE_ID.fullmatch(p["place_id"]):
                raise ProviderError("invalid_place_id")
        else:
            p["name"] = public_place(p.get("name"))
            if not p["name"]:
                raise ProviderError("invalid_location")
            p["latitude"] = number(p.get("latitude"), low=-90, high=90)
            p["longitude"] = number(p.get("longitude"), low=-180, high=180)
        return p

    def fetch(self, p):
        deadline = monotonic() + 25
        if p.get("place_id"):
            place, _ = request_json("GET", f"https://places.googleapis.com/v1/places/{p['place_id']}",
                headers=google_headers("id,photos"), deadline=deadline)
            if place.get("id") != p["place_id"]:
                raise ProviderError("place_identity_mismatch")
        else:
            raw, _ = request_json("POST", "https://places.googleapis.com/v1/places:searchText",
                json={"textQuery": p["name"], "pageSize": 5,
                      "locationBias": {"circle": {"center": {"latitude": p["latitude"], "longitude": p["longitude"]}, "radius": 20000}}},
                headers=google_headers("places.id,places.displayName,places.location,places.photos"), deadline=deadline)
            # A town often comes back with a same-named station or taluk nearby: use the nearest same-named place
            # that has photos, rather than showing none.
            matches = []
            for item in raw.get("places", []):
                if (item.get("displayName", {}).get("text") or "").casefold() != p["name"].casefold():
                    continue
                distance = km_between((p["latitude"], p["longitude"]),
                                      (number(item["location"]["latitude"], low=-90, high=90),
                                       number(item["location"]["longitude"], low=-180, high=180)))
                if distance <= 20:
                    matches.append((not item.get("photos"), distance, len(matches), item))
            if not matches:
                raise ProviderError("place_identity_unconfirmed")
            place = min(matches)[3]
        photos = place.get("photos", [])[:MAX_PHOTOS]
        if not photos:
            return {"count": 0, "index": 0}, ""
        if p["index"] >= len(photos):
            raise ProviderError("photo_no_longer_available")
        photo = photos[p["index"]]
        name = photo.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(r"places/[A-Za-z0-9_-]{1,200}/photos/[A-Za-z0-9_-]{1,1500}", name) or name.split("/")[1] != place["id"]:
            raise ProviderError("invalid_photo_resource")
        media, _ = request_json("GET", f"https://places.googleapis.com/v1/{name}/media",
            params={"maxWidthPx": 1200, "maxHeightPx": 800, "skipHttpRedirect": "true"},
            headers={"X-Goog-Api-Key": google_headers("")["X-Goog-Api-Key"]}, deadline=deadline)
        uri = normalized_link(media.get("photoUri"))
        host = urlsplit(uri).hostname or ""
        if host not in {"lh3.googleusercontent.com", "lh4.googleusercontent.com", "lh5.googleusercontent.com", "lh6.googleusercontent.com", "lh3.ggpht.com"}:
            raise ProviderError("invalid_photo_host")
        try:
            response = request("GET", uri, content_types=IMAGE_TYPES, max_bytes=2_000_000, deadline=deadline)
        except PublicHTTPError as exc:
            raise ProviderError(exc.code, retry_after=exc.retry_after) from None
        mime = response.content_type.split(";", 1)[0]
        if mime not in IMAGE_TYPES:
            raise ProviderError("invalid_photo_type")
        authors = []
        for author in photo.get("authorAttributions", []):
            link = str(author.get("uri") or "")
            authors.append({"name": str(author.get("displayName") or "Photo contributor")[:200],
                            "url": normalized_link("https:" + link if link.startswith("//") else link)})
        return {"count": len(photos), "index": p["index"], "authors": authors,
                "image": f"data:{mime};base64," + base64.b64encode(response.content).decode("ascii")}, response.response_hash

    def normalize(self, raw, parameters):
        return raw
