from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.mobility.models import TravelProviderRequest, TravelProviderState
from apps.mobility.services.travel.cache import query, query_with_fallback, usage_summary
from apps.mobility.services.travel.providers.base import Provider, ProviderError
from apps.mobility.services.travel.providers.geocoding import OpenMeteoGeocoding
from apps.mobility.services.travel.providers.routing import OpenRouteService
from apps.mobility.services.travel.mapping import map_features
from apps.mobility.services.travel.providers.weather import OpenMeteoWeather, replan_proposals
from apps.mobility.services.travel.providers.base import ProviderResult
from apps.mobility.services.travel.discovery import rank_places, remember
from apps.mobility.services.travel.providers.places import OverpassPlaces
from apps.mobility.services.travel.providers.permits import PermitProvider
from apps.mobility.services.travel.costs import calculate_budget
from apps.mobility.services.travel.money import quoted_amount
from apps.mobility.services.travel.bike import bike_context
from apps.mobility.services.travel_discovery import fact
from apps.mobility.models import BikeProfile, BikeDocument, BikeIssueReport, BikeServiceRecord, FuelRefillLog
from apps.mobility.services.travel.providers.accommodation import DuffelAccommodation
from apps.mobility.services.travel.providers.transport import DuffelFlights, IndianRailProvider


class FakeProvider(Provider):
    name = "fixture"
    category = "weather"
    source_url = "https://example.org/weather"
    min_interval = 0
    allowed_parameters = {"latitude"}

    def unavailable_reason(self):
        return ""

    def fetch(self, params):
        return {"temperature": 22}, "a"*64

    def normalize(self, raw, params):
        return {"temperature": float(raw["temperature"])}


class TravelProviderTests(TestCase):
    def setUp(self):
        self.provider = FakeProvider()
        self.provider.fetch = Mock(wraps=self.provider.fetch)

    def test_cache_reuses_fresh_data_and_does_not_claim_live(self):
        a = query(self.provider, {"latitude": 12, "apikey": "never-store"})
        b = query(self.provider, {"latitude": 12})
        self.assertEqual(a.freshness, "LIVE")
        self.assertEqual(b.freshness, "RECENTLY_VERIFIED")
        self.assertEqual(a.retrieved_at, b.retrieved_at)
        self.assertEqual(self.provider.fetch.call_count, 1)
        self.assertEqual(b.request_parameters, {"latitude": 12})
        self.assertNotIn("never-store", str(list(TravelProviderRequest.objects.values())))
        self.assertEqual(usage_summary()[0]["cache_hit_ratio"], .5)

    def test_expiry_and_explicit_refresh_call_provider(self):
        query(self.provider, {})
        VerifiedExternalInsight.objects.update(stale_after=timezone.now()-timedelta(seconds=1))
        self.assertFalse(query(self.provider, {}).cached)
        query(self.provider, {}, force=True)
        self.assertEqual(self.provider.fetch.call_count, 3)

    def test_stale_failure_keeps_original_timestamp(self):
        first = query(self.provider, {})
        VerifiedExternalInsight.objects.update(stale_after=timezone.now()-timedelta(seconds=1))
        self.provider.fetch.side_effect = requests.Timeout("URL?apikey=secret")
        result = query(self.provider, {})
        self.assertTrue(result.stale)
        self.assertEqual(result.freshness, "CACHED")
        self.assertEqual(result.retrieved_at, first.retrieved_at)
        self.assertEqual(result.error, "timeout")
        self.assertNotIn("secret", str(list(TravelProviderRequest.objects.values())))

    def test_timeout_network_api_and_malformed_errors(self):
        for exc, code in [(requests.Timeout(), "timeout"), (requests.ConnectionError(), "network_error"),
                          (ProviderError("api_error"), "api_error"), (ValueError(), "malformed_response")]:
            with self.subTest(code=code):
                TravelProviderState.objects.all().delete()
                self.provider.fetch.side_effect = exc
                result = query(self.provider, {})
                self.assertFalse(result.success)
                self.assertEqual(result.error, code)
        self.provider.fetch.side_effect = None
        self.provider.fetch.return_value = ({"unexpected": 5}, "hash")
        TravelProviderState.objects.all().delete()
        self.assertEqual(query(self.provider, {}).error, "malformed_response")

    def test_quota_and_provider_backoff(self):
        self.provider.limits = {"day": 1}
        query(self.provider, {})
        self.assertEqual(query(self.provider, {}, force=True).error, "local_quota_exhausted")
        self.assertEqual(self.provider.fetch.call_count, 1)
        self.provider.limits = {"day": 100}
        self.provider.fetch.side_effect = ProviderError("quota_exhausted", retry_after=120)
        query(self.provider, {}, force=True)
        result = query(self.provider, {}, force=True)
        self.assertEqual(result.error, "provider_busy_or_backoff")
        self.assertEqual(self.provider.fetch.call_count, 2)

    def test_fallback_and_missing_configuration(self):
        missing = Provider()
        result = query_with_fallback([missing, self.provider], {})
        self.assertTrue(result.success)
        self.assertEqual(result.fallback[0]["error"], "provider_not_configured")

    def test_active_lease_does_not_duplicate_network_call(self):
        TravelProviderState.objects.create(provider=self.provider.name, lease_until=timezone.now()+timedelta(minutes=1))
        self.assertEqual(query(self.provider, {}).error, "provider_busy_or_backoff")
        self.provider.fetch.assert_not_called()


class TravelRoutingTests(TestCase):
    def test_geocoding_global_ambiguity_and_invalid_coordinates(self):
        provider = OpenMeteoGeocoding()
        row = {"id": 1, "name": "Springfield", "latitude": 12, "longitude": 77}
        self.assertTrue(provider.normalize({"results": [row, {**row, "id": 2}]}, {})["ambiguous"])
        with self.assertRaises(ValueError):
            provider.normalize({"results": [{**row, "latitude": 999}]}, {})

    @patch.dict("os.environ", {"TRAVEL_ORS_API_KEY": "fixture-secret"})
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_motorcycle_route_constraints_do_not_claim_legality(self, request):
        provider = OpenRouteService()
        p = {"start": [77, 12], "end": [76, 11], "mode": "ride", "avoid_expressways": True, "avoid_tolls": True}
        provider.fetch(p)
        self.assertEqual(request.call_args.kwargs["json"]["options"]["avoid_features"], ["highways", "tollways"])
        self.assertIn("api.heigit.org/openrouteservice", request.call_args.args[1])
        data = provider.normalize({"features": [{"geometry": {"type": "LineString", "coordinates": [[77,12], [76,11]]},
            "properties": {"summary": {"distance": 250000, "duration": 18000}}}]}, p)
        self.assertEqual(data["routes"][0]["motorcycle_legal"], "UNKNOWN")
        self.assertEqual(data["routes"][0]["distance_km"], 250)
        features = map_features({"name": "Wayanad", "lat": 11, "lon": 76, "route_result": {"payload": data, "freshness": "LIVE"}})
        self.assertEqual(features["features"][1]["geometry"]["type"], "LineString")
        with self.assertRaises(ProviderError):
            provider.fetch({**p, "mode": "train"})


class TravelWeatherTests(TestCase):
    def test_daily_weather_and_replan_does_not_cancel(self):
        provider = OpenMeteoWeather()
        today = timezone.localdate().isoformat()
        payload = provider.normalize({"timezone": "Asia/Kolkata", "daily": {"time": [today],
            "temperature_2m_max": [36], "temperature_2m_min": [22], "precipitation_sum": [35],
            "wind_speed_10m_max": [45], "weather_code": [95], "sunrise": [today+"T06:00"], "sunset": [today+"T18:00"]}},
            {"start_date": today, "end_date": today})
        result = ProviderResult("open_meteo", "weather", success=True, payload=payload)
        proposals = replan_proposals(result)
        self.assertEqual(proposals[0]["risks"], ["rain", "heat", "thunderstorm", "wind"])
        self.assertTrue(proposals[0]["requires_acceptance"])
        self.assertEqual(payload["official_alerts"], "UNKNOWN")
        result.stale = True
        self.assertEqual(replan_proposals(result), [])

    @patch("apps.mobility.services.travel.providers.weather.request_json")
    def test_outside_forecast_window_makes_no_request(self, request):
        with self.assertRaises(ProviderError):
            OpenMeteoWeather().fetch({"start_date": "2099-01-01", "end_date": "2099-01-03"})
        request.assert_not_called()

    def test_incomplete_forecast_is_unknown_not_dry(self):
        with self.assertRaises(ProviderError):
            OpenMeteoWeather().normalize({"daily": {"time": []}}, {"start_date": "2026-10-01", "end_date": "2026-10-01"})


class TravelDiscoveryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("discovery")
        self.places = [{"id": f"osm:node:{i}", "name": f"Viewpoint {i}", "lat": 12+i*.01, "lon": 77,
                       "category": "viewpoint", "access": "yes"} for i in range(1, 5)]

    def test_deduplication_visited_rejected_and_repeat_suppression(self):
        remember(self.user, self.places[0], "visited")
        remember(self.user, self.places[1], "rejected")
        remember(self.user, self.places[2], "shown")
        result = rank_places(self.user, self.places+[self.places[3]], only_new=True)
        self.assertEqual([p["name"] for p in result], ["Viewpoint 4", "Viewpoint 3"])
        other = get_user_model().objects.create_user("other-discovery")
        self.assertEqual(len(rank_places(other, self.places, only_new=True)), 4)

    def test_route_interest_weather_scores_and_access_uncertainty(self):
        result = rank_places(self.user, self.places, interests=["photography"], route=[[77,12],[77,13]], weather_risks=["rain"])
        self.assertIn("route_distance_basis", result[0])
        self.assertEqual(result[0]["opening_status"], "UNKNOWN")
        self.assertEqual(result[0]["popularity"], "UNKNOWN")
        self.assertIn("Matches your interests", result[0]["reasons"])

    def test_places_normalization_and_partial_response(self):
        raw = {"elements": [{"id": 1, "type": "way", "center": {"lat":12,"lon":77},
                             "tags": {"name":"Camp", "tourism":"camp_site", "opening_hours":"24/7"}}]}
        place = OverpassPlaces().normalize(raw, {})["places"][0]
        self.assertEqual(place["category"], "camping")
        self.assertEqual(place["availability"], "UNKNOWN")
        with self.assertRaises(ProviderError):
            OverpassPlaces().normalize({**raw,"remark":"runtime error"}, {})


class TravelPermitTests(TestCase):
    def test_official_reference_is_not_live_opening_or_availability(self):
        result = PermitProvider().lookup("Chembra Peak")
        self.assertNotEqual(result.freshness, "LIVE")
        self.assertEqual(result.payload["status"], "unverified")
        self.assertEqual(result.payload["opening_status"], "UNKNOWN")
        self.assertIsNone(result.payload["daily_quota"])
        self.assertIn("keralatourism.org", result.source_url)

    def test_unknown_permit_is_not_invented(self):
        result = PermitProvider().lookup("Unknown forest")
        self.assertFalse(result.success)
        self.assertEqual(result.payload["requirement"], "UNKNOWN")
        self.assertIsNone(result.retrieved_at)


class TravelCostBikeTests(TestCase):
    def test_multiday_budget_formula_ranges_and_stale_fuel(self):
        state = {k: fact(v) for k,v in {"trip_duration":3,"number_of_travelers":2,"transport_mode":"ride",
                 "vehicle_mileage":30,"fuel_price_per_litre":105,
                 "fuel_price_date":(timezone.localdate()-timedelta(days=10)).isoformat()}.items()}
        result = calculate_budget(state, {"distance_km":300,"nightly":1500})
        self.assertEqual(result["categories"]["Fuel"], 2363)  # 2362.50, explicit half-up rounding
        self.assertEqual(result["categories"]["Stay"], 3000)
        self.assertEqual(result["expected"], sum(result["categories"].values()))
        self.assertLess(result["low"], result["expected"])
        self.assertGreater(result["high"], result["expected"])
        fuel = next(i for i in result["line_items"] if i["category"] == "Fuel")
        self.assertEqual(fuel["input_freshness"], "CACHED")
        self.assertIn("÷ 30", fuel["formula"])
        self.assertEqual(result["verified_prices"], [])

    def test_current_quote_preserves_decimal_precision_without_replacing_estimates(self):
        quote = {"category": "Stay", "currency": "INR", "scope": "whole_trip", "availability": "available",
                 "source_url": "https://example.org", "total": "1000.123456789",
                 "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat()}
        estimate = calculate_budget({}, {})
        result = calculate_budget({}, {"selected_price_snapshots": [quote]})
        self.assertEqual(result["verified_prices"], [quote])
        self.assertEqual(result["categories"], estimate["categories"])
        self.assertEqual(result["expected"], estimate["expected"])
        self.assertEqual(result["freshness"], "ESTIMATED")
        for amount, expected in ((1000, "1000"), (1000.1, "1000.1"), ("0.00", "0.00")):
            with self.subTest(amount=amount):
                current = {**quote, "total": amount}
                result = calculate_budget({}, {"selected_price_snapshots": [current]})
                self.assertEqual(result["verified_prices"][0]["total"], expected)
                self.assertEqual(current["total"], amount)

    def test_malformed_and_incompatible_quotes_do_not_break_estimated_budget(self):
        quote = {"category": "Stay", "currency": "INR", "scope": "whole_trip", "availability": "available",
                 "source_url": "https://example.org", "total": "1000.10",
                 "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat()}
        invalid = [{**quote, "total": amount} for amount in
                   (None, True, False, "invalid", "NaN", "Infinity", "-0.01", "100000000",
                    "1e-1000000", "0e-1000000", [], {})]
        invalid.extend({**quote, field: value} for field, value in (
            ("category", "Unknown"), ("category", []), ("currency", "USD"), ("scope", "per_person"),
            ("availability", "search_result_requires_rate_confirmation"), ("source_url", ""),
            ("source_url", {}), ("expires_at", "invalid"), ("expires_at", "2026-99-99T00:00:00Z"),
            ("expires_at", 123), ("expires_at", "2026-10-01T00:00:00"),
            ("expires_at", (timezone.now() - timedelta(minutes=1)).isoformat())))
        invalid.extend((None, "not a quote", []))
        for candidate in invalid:
            with self.subTest(quote=candidate):
                result = calculate_budget({}, {"selected_price_snapshots": [candidate]})
                self.assertEqual(result["verified_prices"], [])
                self.assertEqual(result["freshness"], "ESTIMATED")
                self.assertEqual(result["expected"], sum(result["categories"].values()))

    def test_quote_serialization_preserves_precision_and_bounds_exponent_expansion(self):
        exact = "0." + "1" * 28
        self.assertEqual(quoted_amount(exact), exact)
        for amount in ("1e-29", "1e-1000000", "0e-1000000"):
            with self.subTest(amount=amount), self.assertRaisesRegex(ValueError, "precision"):
                quoted_amount(amount)

    def test_stale_or_incompatible_quote_does_not_become_verified_price(self):
        quote = {"category":"Stay","currency":"INR","scope":"whole_trip","availability":"available",
                 "source_url":"https://example.org","total":1000,
                 "expires_at":(timezone.now()-timedelta(minutes=1)).isoformat()}
        self.assertEqual(calculate_budget({}, {"selected_price_snapshots":[quote]})["verified_prices"], [])

    def test_bike_records_are_owner_scoped_and_warn_without_guarantees(self):
        user = get_user_model().objects.create_user("bike-travel")
        other = get_user_model().objects.create_user("bike-other")
        bike = BikeProfile.objects.create(user=user, display_name="My bike", model_name="Fixture")
        BikeServiceRecord.objects.create(user=user,bike_profile=bike,bike_name="My bike",service_date=timezone.localdate(),
                                        next_service_date=timezone.localdate(),odometer_km=1000,next_service_km=1200)
        BikeDocument.objects.create(user=user,bike_profile=bike,bike_name="My bike",document_type="insurance",expiry_date=timezone.localdate())
        BikeIssueReport.objects.create(user=user,bike_profile=bike,title="Brake concern",severity="high",symptom="Saved concern")
        FuelRefillLog.objects.create(user=user,bike_profile=bike,bike_name="My bike",refill_date=timezone.localdate(),fuel_liters=10,total_cost=1050)
        BikeIssueReport.objects.create(user=other,bike_profile=bike,title="Private other record",symptom="Excluded")
        result = bike_context(bike,distance_km=300)
        warnings = " ".join(result["warnings"])
        self.assertIn("service mileage",warnings)
        self.assertIn("INSURANCE",warnings)
        self.assertIn("Brake concern",warnings)
        self.assertNotIn("Private other",warnings)
        self.assertEqual(result["fuel_price_per_litre"],"105.00")
        self.assertIn("not a mechanical inspection",result["note"])


class TravelAccommodationTests(TestCase):
    def test_search_price_is_not_confirmed_availability_and_expiry_caps_cache(self):
        expiry = timezone.now()+timedelta(minutes=4)
        raw = {"data":{"results":[{"id":"srr_1","expires_at":expiry.isoformat(),
                "check_in_date":"2026-10-01","check_out_date":"2026-10-03", "cheapest_rate_total_amount":"4000",
                "cheapest_rate_currency":"INR", "cheapest_rate_due_at_accommodation_amount":"200",
                "cheapest_rate_due_at_accommodation_currency":"INR",
                "accommodation":{"name":"Fixture hotel","rating":3,"location":{"geographic_coordinates":{"latitude":12,"longitude":77}}}}]}}
        provider = DuffelAccommodation()
        payload = provider.normalize(raw,{})
        option = payload["options"][0]
        self.assertEqual(option["nightly_rate"],"2000.00")
        self.assertEqual(option["due_at_property"],"200")
        self.assertEqual(option["availability"],"search_result_requires_rate_confirmation")
        self.assertIsNone(option["booking_url"])
        self.assertEqual(provider.expires_at(payload,{},timezone.now()),expiry)
        raw["data"]["results"][0]["expires_at"] = (timezone.now()-timedelta(seconds=1)).isoformat()
        self.assertEqual(provider.normalize(raw,{})["options"],[])

    @patch.dict("os.environ", {"TRAVEL_DUFFEL_API_KEY":"duffel_test_fixture","TRAVEL_DUFFEL_ALLOW_PAID_SEARCH":"true"})
    def test_sandbox_is_never_live(self):
        result = query(DuffelAccommodation(),{})
        self.assertEqual(result.freshness,"UNKNOWN")
        self.assertEqual(result.error,"sandbox_token_not_live_inventory")


class TravelTransportTests(TestCase):
    def test_flight_normalization_roundtrip_price_and_sandbox_rejection(self):
        segment = {"origin":{"iata_code":"BLR"},"destination":{"iata_code":"CCJ"},
                   "departing_at":"2026-10-01T08:00:00","arriving_at":"2026-10-01T09:00:00"}
        offer = {"id":"off_1","live_mode":True,"expires_at":(timezone.now()+timedelta(minutes=10)).isoformat(),
                 "total_amount":"6000","total_currency":"INR","slices":[{"duration":"PT1H","segments":[segment]}]}
        provider = DuffelFlights()
        raw = {"data":{"live_mode":True,"offers":[offer]}}
        option = provider.normalize(raw,{"departure_date":"2026-10-01"})["options"][0]
        self.assertEqual(option["fare"],"6000")
        self.assertEqual(option["transfers"],0)
        self.assertEqual(option["availability"],"offer_returned_recheck_before_purchase")
        self.assertIsNone(option["booking_url"])
        raw["data"]["live_mode"] = False
        with self.assertRaises(ProviderError):
            provider.normalize(raw,{})

    def test_train_schedule_never_implies_inventory_or_verified_fare(self):
        provider = IndianRailProvider()
        option = provider.normalize({"options":[{"origin":"SBC","destination":"CLT","departure":"21:00",
                                                  "availability":"available","waitlist":0,"fare_estimate":600}]},{})["options"][0]
        self.assertEqual(option["availability"],"UNKNOWN")
        self.assertIsNone(option["waitlist"])
        self.assertEqual(option["fare_freshness"],"ESTIMATED")
        self.assertFalse(query(provider,{}).success)
