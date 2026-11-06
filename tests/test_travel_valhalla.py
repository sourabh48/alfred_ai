"""Opt-in Valhalla routing with a real motorcycle profile (TREK idea, independently written)."""
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.mobility.services.travel.providers.base import ProviderError
from apps.mobility.services.travel.providers.routing import OpenRouteService, ValhallaRouting, decode_polyline6, routing_provider

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

    def test_provider_choice(self):
        cases = [({}, "ride", OpenRouteService), (URL, "ride", ValhallaRouting), (URL, "car", ValhallaRouting),
                 ({**URL, "TRAVEL_ORS_API_KEY": "fixture"}, "car", OpenRouteService), ({**URL, "TRAVEL_ORS_API_KEY": "fixture"}, "motorcycle", ValhallaRouting)]
        for env, mode, expected in cases:
            with self.subTest(env=sorted(env), mode=mode), patch.dict("os.environ", env, clear=True):
                self.assertIsInstance(routing_provider(mode), expected)
