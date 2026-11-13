"""Google map tiles as the travel map's backup background. The server fetches them, so the Google key never reaches the browser."""
import os

from django.core.cache import cache
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, request

API = "https://tile.googleapis.com/v1"
SESSION = "travel-google-tiles-session"
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


def tile(z, x, y):
    """(content type, image bytes), or None when off, out of range, over today's cap or refused by Google."""
    if not available() or not (0 <= z <= 20 and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
        return None
    counter = f"travel-google-tiles-{timezone.localdate()}"
    cache.add(counter, 0, 2 * 86400)
    if cache.incr(counter) > DAILY_TILES:
        return None
    try:
        response = request("GET", f"{API}/2dtiles/{z}/{x}/{y}", params={"session": _session()}, headers=_headers(),
                           content_types=("image/png", "image/jpeg"), max_bytes=1_000_000)
    except (PublicHTTPError, KeyError, ValueError):
        cache.delete(SESSION)  # an expired session is the common cause; the next tile starts a new one
        return None
    return response.content_type, response.content
