"""Google toll estimates for car routes (owner chose Google tolls for P3, 2026-11-26). Synthetic responses only; no network."""
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.mobility.services.travel.costs import calculate_budget
from apps.mobility.services.travel.providers.routing import GoogleRoutes
from apps.mobility.services.travel_itinerary import leg_text, legs_tolls

GOOGLE = {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-g-0000"}
CAR = {"start": [77.59, 12.97], "end": [75.74, 12.42], "mode": "roadtrip"}
ROUTE = {"distanceMeters": 250000, "duration": "18000s"}


def priced(*prices):
    return {**ROUTE, "travelAdvisory": {"tollInfo": {"estimatedPrice": list(prices)}}}


class GoogleTollRequestTests(SimpleTestCase):
    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_car_routes_ask_for_fastag_tolls_and_others_do_not(self, request):
        GoogleRoutes().fetch(CAR)
        body, fields = request.call_args.kwargs["json"], request.call_args.kwargs["headers"]["X-Goog-FieldMask"]
        self.assertEqual(body["extraComputations"], ["TOLLS"])
        self.assertEqual(body["routeModifiers"]["tollPasses"], ["IN_FASTAG"])
        self.assertIn("routes.travelAdvisory.tollInfo", fields)
        # Motorcycles (exempt on national highways) and detour checks stay on the cheaper request.
        for p in ({**CAR, "mode": "ride"}, {**CAR, "via": [76.5, 12.6]}):
            GoogleRoutes().fetch(p)
            self.assertNotIn("extraComputations", request.call_args.kwargs["json"])
            self.assertNotIn("tollInfo", request.call_args.kwargs["headers"]["X-Goog-FieldMask"])

    def test_toll_findings_are_decimal_and_keep_the_route_id(self):
        provider = GoogleRoutes()
        plain = provider.normalize({"routes": [ROUTE]}, CAR)["routes"][0]
        self.assertEqual(plain["tolls"]["status"], "not_reported")  # never "no tolls": India coverage is unconfirmed
        self.assertNotIn("no tolls on", plain["tolls"]["note"])
        tolled = provider.normalize({"routes": [priced({"currencyCode": "INR", "units": "235", "nanos": 500000000})]}, CAR)["routes"][0]
        self.assertEqual((tolled["tolls"]["status"], tolled["tolls"]["amount"], tolled["tolls"]["currency"]), ("estimated", "235.50", "INR"))
        self.assertEqual(tolled["route_id"], plain["route_id"])  # a saved choice survives a toll price change
        unknown = provider.normalize({"routes": [priced()]}, CAR)["routes"][0]
        self.assertEqual(unknown["tolls"]["status"], "unknown_price")
        self.assertIsNone(provider.normalize({"routes": [ROUTE]}, {**CAR, "mode": "ride"})["routes"][0]["tolls"])


class TollBudgetTests(SimpleTestCase):
    state = {"transport_mode": {"value": "roadtrip"}, "trip_duration": {"value": 3}}

    def budget(self, tolls, state=None):
        route = {"route_id": "r1", "tolls": tolls}
        destination = {"distance_km": 250, "selected_route_id": "r1", "route_result": {"payload": {"routes": [route]}}}
        result = calculate_budget(state or self.state, destination)
        return result["categories"]["Tolls"], next(i["formula"] for i in result["line_items"] if i["category"] == "Tolls")

    def test_google_rupee_estimate_replaces_the_allowance(self):
        amount, formula = self.budget({"status": "estimated", "amount": "235.50", "currency": "INR"})
        self.assertEqual(amount, 471)
        self.assertIn("INR 235.50 one way × 2", formula)

    def test_unknown_or_foreign_prices_keep_the_allowance(self):
        for tolls in ({"status": "unknown_price"}, {"status": "not_reported"}, {"status": "estimated", "amount": "4.40", "currency": "USD"}, None):
            self.assertEqual(self.budget(tolls)[0], 400)
        ride = {**self.state, "transport_mode": {"value": "ride"}}
        self.assertEqual(self.budget({"status": "estimated", "amount": "235.50", "currency": "INR"}, ride)[0], 0)

    def test_multi_stop_total_needs_every_leg(self):
        legs = [{"tolls": {"status": "estimated", "amount": "120.00", "currency": "INR"}},
                {"tolls": {"status": "estimated", "amount": "80.25", "currency": "INR"}}]
        self.assertEqual(legs_tolls(legs), {"status": "estimated", "amount": "200.25", "currency": "INR"})
        self.assertIsNone(legs_tolls(legs + [{"confidence": "ESTIMATED"}]))
        self.assertIsNone(legs_tolls(legs + [{"tolls": {"status": "not_reported"}}]))
        result = calculate_budget(self.state, {"route_tolls": legs_tolls(legs)}, route_distance_km=600)
        self.assertEqual(result["categories"]["Tolls"], 200)
        leg = {"confidence": "PROVIDER", "distance_km": 120, "hours": 2.5, **legs[0]}
        self.assertIn("tolls about INR 120.00", leg_text(leg))
