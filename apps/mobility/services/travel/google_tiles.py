"""Google map tiles as the travel map's backup background. The server fetches them, so the Google key never reaches the browser."""
import os

from django.core.cache import cache
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, request

API = "https://tile.googleapis.com/v1"
SESSION = "travel-google-tiles-session"
PROBLEM = "travel-google-tiles-problem"
PROBLEMS = {
    "no_key": "Add your Google Maps Platform key in Settings > Online services to see the map.",
    "authorization_failed": "Google refused the key for map tiles. In Google Cloud, enable the Map Tiles API for this key and allow it in the key's API restrictions; ALFRED tries again in 10 minutes.",
    "limit": "Today's map limit is used up; the Google map comes back tomorrow.",
}
DAILY_TILES = 3000  # shortcut: one fixed cap for the whole app, kept under Google's free monthly 2D tiles; make it a setting if people need more


def available():
    return bool(os.getenv("TRAVEL_GOOGLE_MAPS_API_KEY"))


def _headers():
    return {"X-Goog-Api-Key": os.environ["TRAVEL_GOOGLE_MAPS_API_KEY"]}


def _session():
    session = cache.get(SESSION)
    if not session:
        # Sends only the map style; Google sessions last about two weeks, renewed here well before.
        session = str(request("POST", f"{API}/createSession", headers=_headers(),
                              json_body={"mapType": "roadmap", "language": "en", "region": "IN"}).json()["session"])
        cache.set(SESSION, session, 12 * 3600)
    return session


def problem():
    """Why the Google map is not showing, in plain words; empty when nothing is known to be wrong."""
    if not available():
        return PROBLEMS["no_key"]
    code = cache.get(PROBLEM)
    return PROBLEMS.get(code, "Google map tiles could not be reached; check the internet connection." if code else "")


def tile(z, x, y):
    """(content type, image bytes), or None when off, out of range, over today's cap or refused by Google."""
    if not available() or not (0 <= z <= 20 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
        return None
    if cache.get(PROBLEM) == "authorization_failed":
        return None  # a refused key stays refused; asking again for every tile would only spend quota
    counter = f"travel-google-tiles-{timezone.localdate()}"
    cache.add(counter, 0, 2 * 86400)
    if cache.incr(counter) > DAILY_TILES:
        cache.set(PROBLEM, "limit", 3600)
        return None
    try:
        response = request("GET", f"{API}/2dtiles/{z}/{x}/{y}", params={"session": _session()}, headers=_headers(),
                           content_types=("image/png", "image/jpeg"), max_bytes=1_000_000)
    except (PublicHTTPError, KeyError, ValueError) as exc:
        cache.delete(SESSION)  # an expired session is the common cause; the next tile starts a new one
        cache.set(PROBLEM, getattr(exc, "code", "api_error"), 600)
        return None
    cache.delete(PROBLEM)
    return response.content_type, response.content
