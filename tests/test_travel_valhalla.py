"""Free-first routing: opt-in Valhalla motorcycle profile (TREK idea), then ORS, then a capped Google fallback."""
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.mobility.services.travel.providers.base import ProviderError
from apps.mobility.services.travel.cache import query_with_fallback
from apps.mobility.services.travel.mapping import map_features
from apps.mobility.services.travel.providers.geocoding import GooglePlaceSearch, OpenMeteoGeocoding
from apps.mobility.services.travel.providers.routing import GoogleRoutes, OpenRouteService, ValhallaRouting, decode_polyline6, routing_chain

URL = {"TRAVEL_VALHALLA_URL": "https://valhalla.example.test"}


def _encode6(points):
    """Test-only encoder, so the decoder is checked against independent input."""
    out, last = [], (0, 0)
    for lon, lat in points:
        current = (round(lat * 1e6), round(lon * 1e6))
        for value in (current[0] - last[0], current[1] - last[1]):
            value = ~(value << 1) if value < 0 else value << 1
            while value >= 0x20:
                out.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            out.append(chr(value + 63))
        last = current
    return "".join(out)


class ValhallaRoutingTests(SimpleTestCase):
    def test_polyline6_decodes_known_and_round_trip_points(self):
        # Google's documented polyline example read at Valhalla's 1e6 precision.
        self.assertEqual(decode_polyline6("_p~iF~ps|U_ulLnnqC_mqNvxq`@"), [[-12.02, 3.85], [-12.095, 4.07], [-12.6453, 4.3252]])
        points = [[77.5946, 12.9716], [76.6394, 12.2958], [75.7139, 11.2588]]
        self.assertEqual(decode_polyline6(_encode6(points)), points)
        with self.assertRaises(ProviderError):
            decode_polyline6("_p~iF~ps|U_")

    def test_off_until_the_owner_sets_a_safe_url(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(ValhallaRouting().unavailable_reason(), "missing_TRAVEL_VALHALLA_URL")
        for bad in ("http://valhalla.example.test", "https://127.0.0.1", "https://valhalla.example.test/?key=x", "not a url"):
            with self.subTest(bad), patch.dict("os.environ", {"TRAVEL_VALHALLA_URL": bad}):
                self.assertEqual(ValhallaRouting().unavailable_reason(), "invalid_TRAVEL_VALHALLA_URL")
        with patch.dict("os.environ", URL):
            self.assertEqual(ValhallaRouting().unavailable_reason(), "")

    @patch.dict("os.environ", URL)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_motorcycle_request_avoids_expressways_and_reports_what_was_met(self, request):
        provider = ValhallaRouting()
        p = {"start": [77.59, 12.97], "end": [76.64, 12.3], "mode": "ride", "avoid_expressways": True, "avoid_tolls": True, "alternatives": True}
        provider.fetch(p)
        method, url = request.call_args.args
        body = request.call_args.kwargs["json"]
        self.assertEqual((method, url, body["costing"], body["alternates"]), ("POST", "https://valhalla.example.test/route", "motorcycle", 2))
        self.assertEqual(body["costing_options"]["motorcycle"], {"use_highways": 0.0, "use_tolls": 0.0})
        self.assertIn("ALFRED-travel", request.call_args.kwargs["headers"]["User-Agent"])
        shape = _encode6([[77.59, 12.97], [77.0, 12.6], [76.64, 12.3]])
        raw = {"trip": {"legs": [{"shape": shape}], "summary": {"length": 146.04, "time": 12600, "has_highway": False, "has_toll": True}},
               "alternates": [{"trip": {"legs": [{"shape": shape}], "summary": {"length": 146.04, "time": 12600}}}]}
        routes = provider.normalize(raw, p)["routes"]
        self.assertEqual(len(routes), 1)  # identical geometry is one route, not two
        route = routes[0]
        self.assertEqual((route["distance_km"], route["duration_hours"], route["profile"]), (146.0, 3.5, "motorcycle"))
        self.assertEqual(route["motorcycle_legal"], "OSM_ACCESS_TAGS")
        self.assertEqual(route["constraints_met"], {"expressways": True, "tolls": False})  # no toll-free road existed
        self.assertEqual(route["geometry"]["coordinates"][0], [77.59, 12.97])

    @patch.dict("os.environ", URL)
    def test_profiles_and_bad_responses(self):
        provider = ValhallaRouting()
        with self.assertRaisesMessage(ProviderError, "transport_profile_unsupported"):
            provider.fetch({"start": [1, 1], "end": [2, 2], "mode": "mixed"})
        with self.assertRaisesMessage(ProviderError, "malformed_response"):
            provider.normalize({"trip": {"legs": [{"shape": ""}], "summary": {"length": 1, "time": 1}}}, {"mode": "car"})
        with self.assertRaisesMessage(ProviderError, "no_route"):
            provider.normalize({}, {"mode": "car"})
        car = provider.normalize({"trip": {"legs": [{"shape": _encode6([[1, 1], [2, 2]])}], "summary": {"length": 5, "time": 600}}}, {"mode": "car"})
        self.assertEqual((car["routes"][0]["profile"], car["routes"][0]["motorcycle_legal"]), ("auto", "UNKNOWN"))

    def test_free_routers_come_first_and_google_last(self):
        self.assertEqual([p.name for p in routing_chain("ride")], ["valhalla", "openrouteservice", "google_routes"])
        self.assertEqual([p.name for p in routing_chain("car")], ["openrouteservice", "valhalla", "google_routes"])


GOOGLE = {"TRAVEL_GOOGLE_MAPS_API_KEY": "fixture-google-key"}


class GoogleFallbackTests(TestCase):
    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_two_wheeler_request_and_lineless_result(self, request):
        provider = GoogleRoutes()
        p = {"start": [77.59, 12.97], "end": [76.64, 12.3], "mode": "ride", "avoid_expressways": True}
        provider.fetch(p)
        body, headers = request.call_args.kwargs["json"], request.call_args.kwargs["headers"]
        self.assertEqual((body["travelMode"], body["routeModifiers"]), ("TWO_WHEELER", {"avoidHighways": True, "avoidTolls": False}))
        self.assertEqual(headers["X-Goog-Api-Key"], "fixture-google-key")
        self.assertNotIn("key=", request.call_args.args[1])  # key never in the URL
        route = provider.normalize({"routes": [{"distanceMeters": 142381, "duration": "12600s", "description": "NH275"}]}, p)["routes"][0]
        self.assertEqual((route["distance_km"], route["duration_hours"], route["geometry"], route["profile"]), (142.4, 3.5, None, "google-two_wheeler"))
        with self.assertRaisesMessage(ProviderError, "malformed_response"):
            provider.normalize({"routes": [{"distanceMeters": 1, "duration": "soon"}]}, p)
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(GoogleRoutes().unavailable_reason(), "missing_TRAVEL_GOOGLE_MAPS_API_KEY")
        features = map_features({"name": "X", "route_result": {"payload": {"routes": [route]}}})["features"]
        self.assertFalse([f for f in features if f["properties"]["kind"] == "route"])  # nothing drawn on the OSM map

    @patch.dict("os.environ", {**GOOGLE, "TRAVEL_ORS_API_KEY": "fixture-ors"}, clear=True)
    def test_google_is_called_only_after_the_free_routers_fail(self):
        p = {"start": [77.59, 12.97], "end": [76.64, 12.3], "mode": "car"}
        google = {"routes": [{"distanceMeters": 1000, "duration": "60s"}]}, "a" * 64
        with patch("apps.mobility.services.travel.providers.routing.request_json", side_effect=[ProviderError("upstream_unavailable"), google]) as request:
            second = query_with_fallback(routing_chain("car"), {**p, "avoid_tolls": True})
        self.assertEqual((second.provider, request.call_count), ("google_routes", 2))
        self.assertEqual([a["provider"] for a in second.fallback], ["openrouteservice", "valhalla"])

    @patch.dict("os.environ", {**GOOGLE, "TRAVEL_ORS_API_KEY": "fixture-ors"}, clear=True)
    def test_google_is_not_called_when_a_free_router_answers(self):
        ors = {"features": [{"geometry": {"type": "LineString", "coordinates": [[77.59, 12.97], [76.64, 12.3]]},
                             "properties": {"summary": {"distance": 1000, "duration": 60}}}]}, "b" * 64
        with patch("apps.mobility.services.travel.providers.routing.request_json", side_effect=[ors]) as request:
            first = query_with_fallback(routing_chain("car"), {"start": [77.59, 12.97], "end": [76.64, 12.3], "mode": "car"})
        self.assertEqual((first.provider, request.call_count), ("openrouteservice", 1))

    @patch.dict("os.environ", {**GOOGLE, "TRAVEL_USE_MODE": "personal_noncommercial"}, clear=True)
    def test_place_search_falls_back_to_google_when_open_meteo_finds_nothing(self):
        found = {"places": [{"id": "abc", "displayName": {"text": "Kodachadri"}, "formattedAddress": "Karnataka, India",
                             "location": {"latitude": 13.86, "longitude": 74.87}}]}, "c" * 64
        with patch("apps.mobility.services.travel.providers.geocoding.request_json", side_effect=[({"results": []}, "d" * 64), found]) as request:
            result = query_with_fallback([OpenMeteoGeocoding(), GooglePlaceSearch()], {"name": "Kodachadri"},
                                         found=lambda r: bool(r.payload.get("locations")))
        self.assertEqual((result.provider, result.payload["locations"][0]["lat"], request.call_count), ("google_places", 13.86, 2))
        self.assertIn("X-Goog-Api-Key", request.call_args.kwargs["headers"])
