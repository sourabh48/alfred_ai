from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.mobility.models import TravelProviderRequest, TravelProviderState
from apps.mobility.services.travel.cache import budget_status, query, query_with_fallback, usage_summary
from apps.mobility.services.travel.providers.base import Provider, ProviderError
from apps.mobility.services.travel.providers.geocoding import GooglePlaceSearch
from apps.mobility.services.travel.providers.routing import GoogleRoutes
from apps.mobility.services.travel.mapping import map_features
from apps.mobility.services.travel.providers.weather import GoogleWeather, replan_proposals
from apps.mobility.services.travel.providers.base import ProviderResult
from apps.mobility.services.travel.discovery import rank_places, remember
from apps.mobility.services.travel.providers.places import GoogleDestinations, GooglePlacesNearby
from apps.mobility.services.travel.providers.permits import PermitProvider
from apps.mobility.services.travel.costs import calculate_budget
from apps.mobility.services.travel.money import quoted_amount
from apps.mobility.services.travel.bike import bike_context
from apps.mobility.services.travel_discovery import fact
from apps.mobility.models import BikeProfile, BikeDocument, BikeIssueReport, BikeServiceRecord, FuelRefillLog
from apps.mobility.services.travel.providers.transport import IndianRailProvider, SkyscannerFlights

GOOGLE = {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-g-0000"}


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

    def test_usage_summary_uses_the_local_day_on_both_sides_of_utc_midnight(self):
        for zone, utc_now in (
            ("America/Chicago", datetime(2026, 10, 5, 0, 30, tzinfo=datetime_timezone.utc)),
            ("Asia/Kolkata", datetime(2026, 10, 4, 20, 0, tzinfo=datetime_timezone.utc)),
        ):
            with self.subTest(timezone=zone), timezone.override(zone), patch(
                "apps.mobility.services.travel.cache.timezone.now", return_value=utc_now,
            ):
                TravelProviderRequest.objects.all().delete()
                local_start = timezone.localtime(utc_now).replace(
                    hour=0, minute=0, second=0, microsecond=0,
                ).astimezone(datetime_timezone.utc)
                for created, status, network in (
                    (local_start - timedelta(seconds=1), "ok", True),
                    (utc_now - timedelta(minutes=10), "ok", True),
                    (utc_now, "cache_hit", False),
                    (local_start + timedelta(days=1), "ok", True),
                ):
                    event = TravelProviderRequest.objects.create(
                        provider=self.provider.name, category="weather", cache_key="fixture-day",
                        parameters={}, status=status, network_call=network,
                    )
                    TravelProviderRequest.objects.filter(pk=event.pk).update(created_at=created)

                rows = usage_summary()

                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["provider"], self.provider.name)
                self.assertEqual(rows[0]["requests"], 2)
                self.assertEqual(rows[0]["calls_today"], 1)
                self.assertEqual(rows[0]["cache_hits"], 1)
                self.assertEqual(rows[0]["cache_hit_ratio"], .5)

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

    def test_budget_status_matches_enforcement_in_every_window(self):
        now = timezone.now()
        self.provider.min_interval = 0
        for period, age in (("minute", timedelta(seconds=10)), ("hour", timedelta(minutes=5)),
                            ("day", timedelta(seconds=0)), ("month", timedelta(seconds=0))):
            with self.subTest(period):
                TravelProviderRequest.objects.all().delete()
                self.provider.limits = {period: 1}
                self.assertEqual(budget_status(self.provider)[period],
                                 {"limit": 1, "used": 0, "remaining": 1, "exhausted": False})
                call_count = self.provider.fetch.call_count
                self.assertTrue(query(self.provider, {}, force=True).success)
                TravelProviderRequest.objects.update(created_at=now-age)
                self.assertEqual(budget_status(self.provider)[period],
                                 {"limit": 1, "used": 1, "remaining": 0, "exhausted": True})
                self.assertEqual(query(self.provider, {}, force=True).error, "local_quota_exhausted")
                self.assertEqual(self.provider.fetch.call_count, call_count+1)

    def test_budget_windows_expire_and_ignore_other_requests(self):
        # Noon today: "two minutes ago" must not cross local midnight into yesterday.
        now = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        self.provider.limits = {"minute": 1, "hour": 1, "day": 3, "month": 3}
        query(self.provider, {"latitude": 1})
        query(self.provider, {"latitude": 1})
        status = budget_status(self.provider)
        self.assertEqual(status["minute"]["used"], 1)
        TravelProviderRequest.objects.filter(network_call=True).update(created_at=now-timedelta(minutes=2))
        status = budget_status(self.provider, now=now)
        self.assertEqual((status["minute"]["used"], status["hour"]["used"]), (0, 1))
        TravelProviderRequest.objects.create(provider="other", category="weather", cache_key="x", status="ok", network_call=True)
        self.assertEqual(budget_status(self.provider, now=now)["day"]["used"], 1)
        first_of_month = timezone.localtime(now).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        TravelProviderRequest.objects.filter(provider=self.provider.name).update(created_at=first_of_month-timedelta(seconds=1))
        status = budget_status(self.provider, now=now)
        self.assertEqual((status["month"]["used"], status["month"]["remaining"]), (0, 3))

    def test_exhausted_budget_keeps_cached_evidence_and_makes_no_call(self):
        query(self.provider, {"latitude": 1})
        self.provider.limits = {"month": 1}
        self.provider.fetch.reset_mock()
        result = query(self.provider, {"latitude": 1}, force=True)
        self.assertEqual(result.error, "local_quota_exhausted")
        self.assertTrue(result.cached)
        self.provider.fetch.assert_not_called()

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
        provider = GooglePlaceSearch()
        row = {"id": "p1", "displayName": {"text": "Springfield"}, "location": {"latitude": 12, "longitude": 77}}
        self.assertTrue(provider.normalize({"places": [row, {**row, "id": "p2"}]}, {})["ambiguous"])
        with self.assertRaises(ValueError):
            provider.normalize({"places": [{**row, "location": {"latitude": 999, "longitude": 77}}]}, {})

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_motorcycle_route_constraints_do_not_claim_legality(self, request):
        provider = GoogleRoutes()
        p = {"start": [77, 12], "end": [76, 11], "mode": "ride", "avoid_expressways": True, "avoid_tolls": True}
        provider.fetch(p)
        body = request.call_args.kwargs["json"]
        self.assertEqual((body["travelMode"], body["routeModifiers"]), ("TWO_WHEELER", {"avoidHighways": True, "avoidTolls": True}))
        self.assertEqual(request.call_args.kwargs["headers"]["X-Goog-Api-Key"], "synthetic-g-0000")
        data = provider.normalize({"routes": [{"distanceMeters": 250000, "duration": "18000s"}]}, p)
        self.assertEqual((data["routes"][0]["motorcycle_legal"], data["routes"][0]["distance_km"]), ("UNKNOWN", 250))
        features = map_features({"name": "Wayanad", "lat": 11, "lon": 76, "route_result": {"payload": data, "freshness": "LIVE"}})
        self.assertFalse(any(f["geometry"]["type"] == "LineString" for f in features["features"]))  # Google routes draw no line
        with self.assertRaises(ProviderError):
            provider.fetch({**p, "mode": "train"})

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_invalid_request_point_shapes_never_reach_transport(self, request):
        for field in ("start", "end"):
            for point in ("77", None, {0: 77, 1: 12}, [77], [77, 12, 0, 1]):
                with self.subTest(field=field, point=point), self.assertRaises((ValueError, TypeError, ProviderError)):
                    GoogleRoutes().fetch({"start": [77, 12], "end": [76, 11], field: point})
        request.assert_not_called()

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_malformed_route_is_unavailable_not_cached_or_mapped_as_live(self, request):
        request.return_value = ({"routes": [{"distanceMeters": 250000, "duration": "five hours"}]}, "synthetic-route-response")
        result = query(GoogleRoutes(), {"start": [77, 12], "end": [76, 11], "mode": "car"})
        self.assertFalse(result.success); self.assertEqual(result.error, "malformed_response")
        self.assertNotEqual(result.freshness, "LIVE")
        self.assertFalse(VerifiedExternalInsight.objects.filter(scope="travel_provider").exists())
        self.assertFalse(TravelProviderRequest.objects.filter(provider="google_routes", status="ok").exists())

    def test_explicit_zero_route_remains_supported(self):
        route = GoogleRoutes().normalize({"routes": [{"distanceMeters": 0, "duration": "0s"}]}, {"mode": "walking"})["routes"][0]
        self.assertEqual((route["distance_km"], route["duration_hours"], route["closures"]), (0, 0, "UNKNOWN"))

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.routing.request_json")
    def test_legacy_route_cache_cannot_bypass_validation_and_is_preserved(self, request):
        request.return_value = ({"routes": [{"distanceMeters": 250000, "duration": "bad"}]}, "synthetic-legacy-route-response")
        parameters = {"start": [77, 12], "end": [76, 11], "mode": "car"}
        legacy = GoogleRoutes(); legacy.version = 0; legacy.min_interval = 0
        with patch.object(legacy, "normalize", return_value={"routes": [{"distance_km": 1}]}):
            self.assertTrue(query(legacy, parameters).success)
        snapshot = VerifiedExternalInsight.objects.get(scope="travel_provider")
        before = snapshot.payload.copy()
        result = query(GoogleRoutes(), parameters)
        self.assertFalse(result.success); self.assertEqual(result.error, "malformed_response")
        self.assertEqual(request.call_count, 2)
        snapshot.refresh_from_db(); self.assertEqual(snapshot.payload, before)


def google_day(day, high=30, low=20, rain=0, wind=10, condition="CLEAR"):
    half = {"precipitation": {"qpf": {"quantity": rain / 2, "unit": "MILLIMETERS"}}, "wind": {"speed": {"value": wind, "unit": "KILOMETERS_PER_HOUR"}},
            "weatherCondition": {"type": condition}}
    return {"displayDate": {"year": day.year, "month": day.month, "day": day.day}, "daytimeForecast": half, "nighttimeForecast": half,
            "maxTemperature": {"degrees": high}, "minTemperature": {"degrees": low},
            "sunEvents": {"sunriseTime": f"{day.isoformat()}T00:45:00Z", "sunsetTime": f"{day.isoformat()}T12:40:00Z"}}


class TravelWeatherTests(TestCase):
    def test_daily_weather_and_replan_does_not_cancel(self):
        today = timezone.localdate()
        payload = GoogleWeather().normalize({"timeZone": {"id": "Asia/Kolkata"}, "forecastDays": [
            google_day(today, high=36, low=22, rain=35, wind=45, condition="THUNDERSTORM")]},
            {"start_date": today.isoformat(), "end_date": today.isoformat()})
        result = ProviderResult("google_weather", "weather", success=True, payload=payload)
        proposals = replan_proposals(result)
        self.assertEqual(proposals[0]["risks"], ["rain", "heat", "thunderstorm", "wind"])
        self.assertEqual((payload["days"][0]["rain_mm"], payload["timezone"]), (35, "Asia/Kolkata"))
        self.assertTrue(proposals[0]["requires_acceptance"])
        self.assertEqual(payload["official_alerts"], "UNKNOWN")
        result.stale = True
        self.assertEqual(replan_proposals(result), [])

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.weather.request_json")
    def test_outside_forecast_window_makes_no_request(self, request):
        far = (timezone.localdate() + timedelta(days=10)).isoformat()  # Google forecasts today and the next nine days
        for window in ({"start_date": "2099-01-01", "end_date": "2099-01-03"}, {"start_date": far, "end_date": far}):
            self.assertEqual(query(GoogleWeather(), {"latitude": 12, "longitude": 77, **window}).error, "invalid_parameters")
        request.assert_not_called()

    def test_incomplete_forecast_is_unknown_not_dry(self):
        today = timezone.localdate()
        with self.assertRaises(ProviderError):
            GoogleWeather().normalize({"forecastDays": [google_day(today)]},
                                      {"start_date": today.isoformat(), "end_date": (today + timedelta(days=1)).isoformat()})


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

    def test_places_normalization_and_destinations_from_google(self):
        raw = {"places": [{"id": "c1", "displayName": {"text": "Camp"}, "location": {"latitude": 12, "longitude": 77},
                           "primaryType": "campground", "googleMapsUri": "https://maps.google.com/?cid=1"},
                          {"id": "x1", "displayName": {"text": "Office"}, "location": {"latitude": 12, "longitude": 77}, "primaryType": "accounting"}]}
        places = GooglePlacesNearby().normalize(raw, {})["places"]
        self.assertEqual([(p["name"], p["category"], p["availability"]) for p in places], [("Camp", "camping", "UNKNOWN")])
        with self.assertRaises(ProviderError):
            GooglePlacesNearby().types({"categories": ["nightclub"]})
        found = GoogleDestinations().normalize({"places": raw["places"] * 2}, {})["destinations"]
        self.assertEqual(([d["name"] for d in found], found[0]["source"]), (["Camp", "Office"], "https://maps.google.com/?cid=1"))


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


class TravelTransportTests(TestCase):
    def test_train_schedule_never_implies_inventory_or_verified_fare(self):
        provider = IndianRailProvider()
        option = provider.normalize({"options":[{"origin":"SBC","destination":"CLT","departure":"21:00",
                                                  "availability":"available","waitlist":0,"fare_estimate":600}]},{})["options"][0]
        self.assertEqual(option["availability"],"UNKNOWN")
        self.assertIsNone(option["waitlist"])
        self.assertEqual(option["fare_freshness"],"ESTIMATED")
        self.assertFalse(query(provider,{}).success)


class TravelProviderPolicyBoundaryTests(TestCase):
    """Google needs its key, and the older advisor uses the same budgeted path."""

    geocoding = {"places": [{"id": "g1", "displayName": {"text": "Synthetic Town"}, "formattedAddress": "Synthetic State, India",
                             "location": {"latitude": 12.5, "longitude": 77.5}}]}

    @patch("apps.mobility.services.travel.providers.geocoding.request_json")
    def test_without_the_google_key_nothing_is_sent(self, request_json):
        with patch.dict("os.environ", {"TRAVEL_GOOGLE_MAPS_API_KEY": ""}):
            result = query(GooglePlaceSearch(), {"name": "Synthetic Town"})
        self.assertEqual((result.success, result.error), (False, "missing_TRAVEL_GOOGLE_MAPS_API_KEY"))
        request_json.assert_not_called()

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.geocoding.request_json")
    def test_advisor_lookups_use_the_budgeted_provider_with_no_second_cache(self, request_json):
        from apps.integrations.services.verified_intelligence import verified_intelligence
        request_json.return_value = (self.geocoding, "hash")
        live = verified_intelligence.geocode_destination("Synthetic Town")
        cached = verified_intelligence.geocode_destination("Synthetic Town")
        self.assertEqual(live.payload["display_name"], "Synthetic Town, Synthetic State, India")
        self.assertIn("Google", live.evidence["source_name"])
        self.assertEqual((live.cached, cached.cached), (False, True))
        self.assertEqual(TravelProviderRequest.objects.filter(provider="google_places", network_call=True).count(), 1)
        self.assertFalse(VerifiedExternalInsight.objects.filter(scope="travel").exists())

    @patch("alfred_ai.services.public_http.request")
    def test_advisor_offbeat_search_makes_no_call_and_old_travel_records_retire(self, request):
        from apps.integrations.services.verified_intelligence import verified_intelligence
        old = VerifiedExternalInsight.objects.create(scope="travel", cache_key="offbeat:synthetic-town",
            title="Offbeat suggestions near Synthetic Town", source_name="OpenStreetMap Nominatim",
            source_url="https://nominatim.openstreetmap.org/search", query="Synthetic Town", summary="old",
            payload={"results": [{"title": "Old place"}]}, checksum="x", status="fresh", fetched_at=timezone.now(),
            verified_at=timezone.now(), stale_after=timezone.now()+timedelta(days=1))
        self.assertEqual(verified_intelligence.offbeat_suggestions("Synthetic Town").payload, {"results": []})
        self.assertEqual(verified_intelligence._refresh_record(old), "skipped")
        old.refresh_from_db()
        self.assertFalse(old.is_active)
        request.assert_not_called()

    @patch.dict("os.environ", GOOGLE)
    @patch("apps.mobility.services.travel.providers.weather.request_json")
    def test_unforecastable_window_uses_no_budget_or_backoff(self, request_json):
        result = query(GoogleWeather(), {"latitude": 12.5, "longitude": 77.5, "start_date": "2001-01-01", "end_date": "2001-01-02"})
        self.assertFalse(result.success)
        request_json.assert_not_called()
        self.assertFalse(TravelProviderRequest.objects.filter(network_call=True).exists())
        self.assertFalse(TravelProviderState.objects.filter(provider="google_weather", next_allowed_at__isnull=False).exists())
        self.assertEqual(query(GoogleWeather(), {"latitude": 1, "longitude": 1}).error, "invalid_parameters")

    def test_geocoded_origin_keeps_its_source_and_is_not_labelled_static(self):
        from copy import deepcopy
        from apps.mobility.services.travel.research import enrich_candidate
        from apps.mobility.services.travel_catalog import DESTINATIONS
        now = timezone.now()

        def fake_query(provider, parameters, **kwargs):
            if provider.category == "geocoding":
                return ProviderResult("google_places", "geocoding", success=True, status="ok", freshness="LIVE",
                    confidence="LIKELY", source_url=provider.source_url, attribution=provider.attribution,
                    retrieved_at=now.isoformat(), expires_at=(now+timedelta(days=1)).isoformat(),
                    payload={"locations": [{"name": "Synthetic Origin", "lat": 13.0, "lon": 77.0}]})
            return ProviderResult(provider.name, provider.category, error="offline")
        from apps.mobility.services.travel_discovery import candidates_for
        owner = get_user_model().objects.create_user("origin-owner", password="x-Unused-12345")
        destination = candidates_for(owner, {"origin": fact("Bengaluru")}, destinations=[deepcopy(DESTINATIONS[0])])[0]
        with patch("apps.mobility.services.travel.research.query", side_effect=fake_query), patch("apps.mobility.services.travel.cache.query", side_effect=fake_query):
            d, _ = enrich_candidate(owner, {"origin": fact("Synthetic Origin")}, destination)
        self.assertIn("Google", d["origin_geocoding_result"]["attribution"])
        origin = next(f for f in map_features(d)["features"] if f["properties"]["kind"] == "origin")
        self.assertEqual(origin["properties"]["freshness"], "LIVE")

    def test_day_budget_starts_at_local_midnight(self):
        from zoneinfo import ZoneInfo
        zone = ZoneInfo("Asia/Kolkata")
        now = datetime(2026, 11, 4, 1, 0, tzinfo=zone).astimezone(datetime_timezone.utc)  # timezone.now() is UTC: 3 November.
        event = TravelProviderRequest.objects.create(provider="google_places", category="geocoding", cache_key="k",
                                                     parameters={}, status="ok", network_call=True)
        TravelProviderRequest.objects.filter(pk=event.pk).update(created_at=datetime(2026, 11, 4, 0, 30, tzinfo=zone))
        with timezone.override(zone):
            self.assertEqual(budget_status(GooglePlaceSearch(), now=now)["day"]["used"], 1)
        TravelProviderRequest.objects.filter(pk=event.pk).update(created_at=datetime(2026, 11, 3, 23, 30, tzinfo=zone))
        with timezone.override(zone):
            self.assertEqual(budget_status(GooglePlaceSearch(), now=now)["day"]["used"], 0)


class SkyscannerFlightTests(TestCase):
    """Live fares once the partner key exists: off without it, only airports, dates and travellers sent, and the
    cheapest itineraries priced exactly from Skyscanner's scaled whole numbers."""
    def setUp(self):
        self.day = timezone.localdate() + timedelta(days=20)
        self.back = timezone.localdate() + timedelta(days=24)

    def test_off_without_a_key_and_nothing_is_sent(self):
        with patch("apps.mobility.services.travel.providers.base.request") as sent, patch.dict("os.environ", {"TRAVEL_SKYSCANNER_API_KEY": ""}):
            result = query(SkyscannerFlights(), {"origin": "BLR", "destination": "GOI", "departure_date": self.day.isoformat()})
        self.assertEqual(result.error, "missing_TRAVEL_SKYSCANNER_API_KEY")
        sent.assert_not_called()

    @patch.dict("os.environ", {"TRAVEL_SKYSCANNER_API_KEY": "synthetic-sky-0000"})
    def test_search_polls_until_complete_and_prices_the_cheapest_exactly(self):
        leg = {"originPlaceId": "p1", "destinationPlaceId": "p2", "durationInMinutes": 75, "stopCount": 0, "marketingCarrierIds": ["c1"],
               "departureDateTime": {"year": self.day.year, "month": self.day.month, "day": self.day.day, "hour": 6, "minute": 5},
               "arrivalDateTime": {"year": self.day.year, "month": self.day.month, "day": self.day.day, "hour": 7, "minute": 20}}
        done = {"status": "RESULT_STATUS_COMPLETE", "content": {"results": {
            "itineraries": {"i1": {"legIds": ["l1"], "pricingOptions": [{"price": {"amount": "3499500", "unit": "PRICE_UNIT_MILLI"},
                                                                         "items": [{"deepLink": "https://www.skyscanner.net/transport_deeplink/x"}]}]},
                            "i2": {"legIds": ["l1"], "pricingOptions": [{"price": {"amount": "", "unit": "PRICE_UNIT_MILLI"}}]}},
            "legs": {"l1": leg}, "places": {"p1": {"iata": "BLR"}, "p2": {"iata": "GOI"}}, "carriers": {"c1": {"name": "Synthetic Air"}}},
            "sortingOptions": {"cheapest": [{"itineraryId": "i1"}, {"itineraryId": "i2"}]}}}
        answers = [{"status": "RESULT_STATUS_INCOMPLETE", "sessionToken": "tok"}, done]
        responses = [Mock(response_hash="h", **{"json.return_value": a}) for a in answers]
        with patch("apps.mobility.services.travel.providers.base.request", side_effect=responses) as sent:
            result = query(SkyscannerFlights(), {"origin": "blr", "destination": "GOI", "departure_date": self.day.isoformat(),
                                                 "return_date": self.back.isoformat(), "adults": 2})
        self.assertTrue(result.success, result.error)
        self.assertEqual(len(result.payload["options"]), 1)  # an itinerary with no price is left out
        option = result.payload["options"][0]
        self.assertEqual((option["fare"], option["carrier"], option["origin"], option["transfers"]), ("3499.5", "Synthetic Air", "BLR", 0))
        self.assertEqual(option["booking_url"], "https://www.skyscanner.net/transport_deeplink/x")
        create, poll = sent.call_args_list
        self.assertTrue(create.args[1].endswith("/create") and poll.args[1].endswith("/poll/tok"))
        self.assertEqual(create.kwargs["headers"]["x-api-key"], "synthetic-sky-0000")
        query_sent = create.kwargs["json_body"]["query"]
        self.assertEqual((query_sent["adults"], len(query_sent["queryLegs"]), query_sent["queryLegs"][1]["originPlaceId"]), (2, 2, {"iata": "GOI"}))
        self.assertNotIn("synthetic-sky", str(create.kwargs["json_body"]))

    @patch.dict("os.environ", {"TRAVEL_SKYSCANNER_API_KEY": "synthetic-sky-0000"})
    def test_bad_input_makes_no_call(self):
        with patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("no call")):
            for p in ({"origin": "Bangalore", "destination": "GOI", "departure_date": self.day.isoformat()},
                      {"origin": "BLR", "destination": "GOI", "departure_date": "2020-01-01"},
                      {"origin": "BLR", "destination": "GOI", "departure_date": self.day.isoformat(), "cabin_class": "deluxe"}):
                self.assertFalse(query(SkyscannerFlights(), p).success)
