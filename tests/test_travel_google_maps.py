"""Travel map, places and hotels come from Google only (owner decision 2026-11-13): used only with the owner's key, the key
never reaches the browser, and hotel listings never show a price or a free room that Google did not give."""
import json
import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from apps.mobility.services.travel import google_tiles
from apps.mobility.services.travel.cache import query
from apps.mobility.services.travel.mapping import map_configuration
from apps.mobility.services.travel.providers.places import GoogleLodging, GooglePlacesNearby

KEY = {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-google-key-0000"}
RAW = {"places": [
    {"id": "p1", "displayName": {"text": "Synthetic Fort"}, "formattedAddress": "Synthetic Road", "location": {"latitude": 12.1, "longitude": 77.1},
     "primaryType": "tourist_attraction", "types": ["tourist_attraction"], "googleMapsUri": "https://maps.google.com/?cid=1"},
    {"id": "p2", "displayName": {"text": "Synthetic Fuel"}, "location": {"latitude": 12.2, "longitude": 77.2}, "types": ["gas_station"]},
    {"id": "p3", "displayName": {"text": "Synthetic Shop"}, "location": {"latitude": 12.3, "longitude": 77.3}, "types": ["store"]}]}


def reply(body, content_type="application/json"):
    return PublicResponse(body if isinstance(body, bytes) else json.dumps(body).encode(), content_type, 200)


class GooglePlacesTests(TestCase):
    def test_off_without_a_key_and_nothing_is_sent(self):
        with patch.dict(os.environ, {}, clear=False), patch("apps.mobility.services.travel.providers.base.request") as sent:
            os.environ.pop("TRAVEL_GOOGLE_MAPS_API_KEY", None)
            result = query(GooglePlacesNearby(), {"latitude": 12, "longitude": 77})
        self.assertEqual(result.error, "missing_TRAVEL_GOOGLE_MAPS_API_KEY")
        sent.assert_not_called()

    @patch.dict(os.environ, KEY)
    def test_places_keep_the_place_shape_and_send_only_the_destination_with_the_key_in_a_header(self):
        with patch("apps.mobility.services.travel.providers.base.request", return_value=reply(RAW)) as sent:
            result = query(GooglePlacesNearby(), {"latitude": 12, "longitude": 77, "categories": ["attraction", "fuel"]})
        self.assertTrue(result.success, result.error)
        places = result.payload["places"]
        self.assertEqual([(p["name"], p["category"]) for p in places], [("Synthetic Fort", "attraction"), ("Synthetic Fuel", "fuel")])
        self.assertEqual(places[0]["source_url"], "https://maps.google.com/?cid=1")
        self.assertIn("place_id:p2", places[1]["source_url"])
        args, kwargs = sent.call_args
        self.assertEqual(kwargs["headers"]["X-Goog-Api-Key"], KEY["TRAVEL_GOOGLE_MAPS_API_KEY"])
        self.assertNotIn("synthetic-google-key", args[1])
        self.assertEqual(kwargs["json_body"]["includedTypes"], ["tourist_attraction", "museum", "gas_station"])
        self.assertEqual(set(kwargs["json_body"]), {"includedTypes", "maxResultCount", "locationRestriction"})

    @patch.dict(os.environ, KEY)
    def test_hotels_from_google_have_no_price_or_free_room(self):
        with patch("apps.mobility.services.travel.providers.base.request", return_value=reply(RAW)):
            result = query(GoogleLodging(), {"latitude": 12, "longitude": 77, "check_in": "2026-12-01"})
        options = result.payload["options"]
        self.assertEqual(len(options), 3)
        self.assertTrue(all(o["total_price"] is None and o["nightly_rate"] is None and o["availability"] == "UNKNOWN" for o in options))
        self.assertEqual(options[0]["booking_url"], "https://maps.google.com/?cid=1")


@patch.dict(os.environ, KEY)
class GoogleMapTileTests(TestCase):
    def setUp(self):
        for key in (google_tiles.SESSION, f"travel-google-tiles-{timezone.localdate()}"):
            cache.delete(key)
        self.user = get_user_model().objects.create_user("synthetic-map-owner", password="pw-synthetic-1")

    def test_map_is_google_only_through_alfred_and_never_carries_the_key(self):
        config = map_configuration()
        self.assertEqual((config["provider"], config["tile_url"]), ("google", "/mobility/map-tiles/{z}/{x}/{y}.png"))
        self.assertNotIn("synthetic-google-key", json.dumps(config))
        self.assertNotIn("openstreetmap", json.dumps(config))
        os.environ.pop("TRAVEL_GOOGLE_MAPS_API_KEY")
        self.assertEqual(map_configuration()["tile_url"], "")

    def test_tiles_come_through_alfred_for_signed_in_people_only(self):
        self.assertEqual(self.client.get("/mobility/map-tiles/1/0/0.png").status_code, 302)
        self.client.force_login(self.user)
        with patch.object(google_tiles, "request", side_effect=[reply({"session": "s1"}), reply(b"\x89PNG", "image/png")]) as sent:
            response = self.client.get("/mobility/map-tiles/1/0/1.png")
        self.assertEqual((response.status_code, response["Content-Type"], response.content), (200, "image/png", b"\x89PNG"))
        self.assertTrue(response["Cache-Control"].startswith("private"))
        tile_call = sent.call_args_list[1]
        self.assertEqual(tile_call.kwargs["params"], {"session": "s1"})
        self.assertEqual(tile_call.kwargs["headers"], {"X-Goog-Api-Key": KEY["TRAVEL_GOOGLE_MAPS_API_KEY"]})
        self.assertNotIn("synthetic-google-key", tile_call.args[1])

    def test_out_of_range_over_the_cap_or_refused_is_no_tile(self):
        with patch.object(google_tiles, "request", side_effect=AssertionError("no call")):
            self.assertIsNone(google_tiles.tile(1, 2, 0))
            self.assertIsNone(google_tiles.tile(21, 0, 0))
        cache.set(google_tiles.SESSION, "old")
        with patch.object(google_tiles, "request", side_effect=PublicHTTPError("api_error")):
            self.assertIsNone(google_tiles.tile(0, 0, 0))
        self.assertIsNone(cache.get(google_tiles.SESSION))  # an expired session is dropped and renewed next time
        with patch.object(google_tiles, "DAILY_TILES", 1), patch.object(google_tiles, "request", side_effect=AssertionError("no call")):
            self.assertIsNone(google_tiles.tile(0, 0, 0))
