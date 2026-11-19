"""Travel additions the owner approved on 2026-11-19: past-years climate for far-off trips, flight status for booked
flights, and earthquake and air-quality alerts before a trip. Synthetic replies only; no network."""
from datetime import date, timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.mobility.services.travel.providers.base import ProviderError
from apps.mobility.services.travel.providers.weather import OpenMeteoClimate


def archive(start, end, high=28.0, low=18.0, rain=lambda day: 2.0 if day.day % 2 else 0.0, missing=()):
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    keep = [d for d in days if d not in missing]
    return {"daily": {"time": [d.isoformat() for d in keep], "temperature_2m_max": [high] * len(keep),
                      "temperature_2m_min": [low] * len(keep), "precipitation_sum": [rain(d) for d in keep]}}


class ClimateTests(SimpleTestCase):
    def setUp(self):
        self.provider = OpenMeteoClimate()
        self.today = patch("apps.mobility.services.travel.providers.weather.timezone.localdate", return_value=date(2026, 11, 19))
        self.today.start()
        self.addCleanup(self.today.stop)

    def test_one_request_covers_the_same_dates_in_each_of_five_past_years(self):
        trip = {"latitude": 12.42, "longitude": 75.74, "start_date": "2027-07-10", "end_date": "2027-07-13"}
        windows = self.provider.windows(trip)
        self.assertEqual(windows[0], (date(2026, 7, 10), date(2026, 7, 13)))  # already in the archive
        self.assertEqual(windows[-1], (date(2022, 7, 10), date(2022, 7, 13)))
        with patch("apps.mobility.services.travel.providers.weather.request_json", return_value=({}, "hash")) as sent:
            self.provider.fetch(trip)
        params = sent.call_args.kwargs["params"]
        self.assertEqual((params["start_date"], params["end_date"]), ("2022-07-10", "2026-07-13"))
        self.assertEqual(set(params) - {"daily", "timezone"}, {"latitude", "longitude", "start_date", "end_date"})  # nothing personal

    def test_dates_not_yet_in_the_archive_use_the_year_before(self):
        windows = self.provider.windows({"start_date": "2026-12-20", "end_date": "2026-12-24"})
        self.assertEqual(windows[0], (date(2025, 12, 20), date(2025, 12, 24)))
        windows = self.provider.windows({"start_date": "2027-11-15", "end_date": "2027-11-18"})
        self.assertEqual(windows[0], (date(2025, 11, 15), date(2025, 11, 18)))  # 2026-11-18 is still too recent

    def test_29_february_falls_back_to_the_28th(self):
        windows = self.provider.windows({"start_date": "2028-02-29", "end_date": "2028-03-02"})
        self.assertEqual(windows[0], (date(2026, 2, 28), date(2026, 3, 2)))
        self.assertIn((date(2024, 2, 29), date(2024, 3, 2)), windows)  # a leap year keeps the 29th

    def test_summary_averages_years_and_needs_at_least_three(self):
        trip = {"start_date": "2027-07-10", "end_date": "2027-07-13"}
        raw = archive(date(2022, 7, 10), date(2026, 7, 13))
        result = self.provider.normalize(raw, trip)
        self.assertEqual((result["years"], result["average_max_temp"], result["average_min_temp"]), (5, 28.0, 18.0))
        self.assertEqual((result["average_rain_total"], result["rainy_day_percent"]), (4.0, 50))
        self.assertIn("Past weather, not a forecast", result["summary"])
        gaps = {date(2026, 7, 11), date(2025, 7, 11), date(2024, 7, 11)}
        with self.assertRaises(ProviderError):
            self.provider.normalize(archive(date(2022, 7, 10), date(2026, 7, 13), missing=gaps), trip)

    def test_long_or_backwards_windows_are_refused_before_any_call(self):
        for start, end in (("2027-07-13", "2027-07-10"), ("2027-01-01", "2027-04-01")):
            with self.assertRaises(ProviderError):
                self.provider.parameters({"latitude": 1, "longitude": 1, "start_date": start, "end_date": end})


def flight_reply(day, *, revised="10:15", status="Delayed"):
    return [{"number": "AI 504", "status": status,
             "departure": {"airport": {"iata": "BLR"}, "scheduledTime": {"local": f"{day} 09:30+05:30"},
                           "revisedTime": {"local": f"{day} {revised}+05:30"}, "terminal": "2", "gate": "12"},
             "arrival": {"airport": {"iata": "DEL"}}},
            {"number": "AI 504", "departure": {"scheduledTime": {"local": "2020-01-01 09:30+05:30"}}}]  # another day


class FlightStatusTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.mobility.models import TravelPlan
        from apps.mobility.services.travel import trip_tools

        self.today = timezone.localdate()
        self.user = get_user_model().objects.create_user("synthetic-flyer", password="Test12345!")
        self.plan = TravelPlan.objects.create(user=self.user, title="Synthetic Delhi trip", destination="Delhi", status="booked",
                                              start_date=self.today, end_date=self.today + timedelta(days=3))
        trip_tools.add_booking(self.user, self.plan, {"kind": "flight", "title": "AI 504 BLR-DEL", "confirmation": "SYN123",
                                                      "start": f"{self.today.isoformat()}T09:30"})
        trip_tools.add_booking(self.user, self.plan, {"kind": "hotel", "title": "Synthetic Inn 12", "start": self.today.isoformat()})

    def test_flight_numbers_are_read_from_booking_titles(self):
        from apps.mobility.services.travel.providers.flight_status import flight_number
        self.assertEqual([flight_number(t) for t in ("AI 504 BLR-DEL", "6E-2131", "uk0815", "Flight to Goa", "2026-11-20")],
                         ["AI504", "6E2131", "UK815", None, None])

    def test_a_delayed_flight_today_becomes_a_trip_step_and_sends_only_number_and_date(self):
        from apps.mobility.services.travel.proactive import next_steps
        from apps.mobility.services.travel.providers import flight_status

        with patch.object(flight_status, "request_json", return_value=(flight_reply(self.today.isoformat()), "hash")) as sent:
            with patch.dict("os.environ", {"ALFRED_AERODATABOX_API_KEY": "synthetic-rapidapi-key"}):
                steps = [s for s in next_steps(self.plan, self.today) if s["kind"] == "flight"]
        self.assertEqual(len(steps), 1)  # the hotel booking is not a flight
        self.assertEqual(steps[0]["title"], "Flight change: AI504")
        self.assertEqual(steps[0]["detail"], "AI504 BLR→DEL: Delayed, now 10:15 (was 09:30, 45 min late); terminal 2, gate 12. "
                                             "Recheck with the airline before you leave.")
        url, kwargs = sent.call_args.args[1], sent.call_args.kwargs
        self.assertEqual(url, f"https://aerodatabox.p.rapidapi.com/flights/number/AI504/{self.today.isoformat()}")
        self.assertNotIn("SYN123", str(sent.call_args))  # the booking reference never leaves the PC
        self.assertEqual(kwargs["headers"]["X-RapidAPI-Key"], "synthetic-rapidapi-key")

    def test_no_key_or_a_far_off_flight_makes_no_call(self):
        from apps.mobility.services.travel.proactive import next_steps
        from apps.mobility.services.travel.providers import flight_status

        with patch.object(flight_status, "request_json") as sent:
            self.assertFalse([s for s in next_steps(self.plan, self.today) if s["kind"] == "flight"])  # no key
            with patch.dict("os.environ", {"ALFRED_AERODATABOX_API_KEY": "synthetic-rapidapi-key"}):
                later = self.today - timedelta(days=5)  # the flight is five days after "today"
                self.plan.start_date = later
                self.assertFalse([s for s in next_steps(self.plan, later) if s["kind"] == "flight"])
        sent.assert_not_called()

    def test_on_time_flight_reads_as_status_not_change(self):
        from apps.mobility.services.travel.providers.flight_status import AeroDataBoxStatus, describe
        status = AeroDataBoxStatus().normalize(flight_reply("2026-11-20", revised="09:32", status="Expected"),
                                               {"number": "AI504", "date": "2026-11-20"})
        self.assertEqual(status["delay_minutes"], 2)
        self.assertEqual(describe(status), "AI504 BLR→DEL: Expected, departs 09:32; terminal 2, gate 12. Recheck with the airline before you leave.")
        with self.assertRaises(ProviderError):
            AeroDataBoxStatus().normalize(flight_reply("2026-11-20"), {"number": "AI504", "date": "2026-11-21"})



class SafetyTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.mobility.models import TravelPlan

        self.today = timezone.localdate()
        user = get_user_model().objects.create_user("synthetic-safety", password="Test12345!")
        coast = {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [75.7412, 12.4244]},
                                                          "properties": {"name": "Coorg", "kind": "overnight"}}]}
        self.plan = TravelPlan.objects.create(user=user, title="Synthetic Coorg ride", destination="Coorg", status="planned",
                                              start_date=self.today + timedelta(days=2), end_date=self.today + timedelta(days=4),
                                              itinerary={"map": coast})

    def replies(self, method, url, **kwargs):
        if "earthquake.usgs.gov" in url:
            self.assertEqual(kwargs["params"]["minmagnitude"], 5.0)
            return {"features": [{"properties": {"mag": 5.6, "place": "40 km W of Synthetic Town", "time": 1795000000000,
                                                 "tsunami": 0, "url": "https://earthquake.usgs.gov/earthquakes/eventpage/syn1"}}]}, "h1"
        self.assertEqual(kwargs["json"], {"location": {"latitude": 12.424, "longitude": 75.741}})  # rounded; nothing else
        return {"indexes": [{"code": "uaqi", "aqi": 31, "category": "Low air quality", "dominantPollutant": "pm25"}]}, "h2"

    def test_trip_in_two_days_gets_quake_and_poor_air_notes(self):
        from apps.mobility.services.travel.proactive import next_steps
        from apps.mobility.services.travel.providers import safety

        with patch.object(safety, "request_json", side_effect=self.replies), \
                patch.dict("os.environ", {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-google-key"}):
            steps = {s["kind"]: s for s in next_steps(self.plan, self.today) if s["kind"] in ("safety", "air")}
        self.assertIn("Magnitude 5.6 40 km W of Synthetic Town", steps["safety"]["detail"])
        self.assertEqual(steps["safety"]["links"], [{"label": "USGS details", "url": "https://earthquake.usgs.gov/earthquakes/eventpage/syn1"}])
        self.assertEqual(steps["air"]["title"], "Poor air in Coorg")
        self.assertIn("Low air quality right now (Universal AQI 31 of 100; main pollutant pm25)", steps["air"]["detail"])

    def test_far_off_trips_and_trips_without_a_map_make_no_call(self):
        from apps.mobility.services.travel.proactive import next_steps
        from apps.mobility.services.travel.providers import safety

        with patch.object(safety, "request_json") as sent:
            self.assertFalse([s for s in next_steps(self.plan, self.today - timedelta(days=5)) if s["kind"] in ("safety", "air")])
            self.plan.itinerary = {}
            self.assertFalse([s for s in next_steps(self.plan, self.today) if s["kind"] in ("safety", "air")])
        sent.assert_not_called()

    def test_clean_air_and_a_quiet_week_add_nothing(self):
        from apps.mobility.services.travel.proactive import next_steps
        from apps.mobility.services.travel.providers import safety

        calm = lambda method, url, **kwargs: (({"features": []}, "h1") if "usgs" in url else
                                              ({"indexes": [{"code": "uaqi", "aqi": 78, "category": "Good air quality"}]}, "h2"))
        with patch.object(safety, "request_json", side_effect=calm), \
                patch.dict("os.environ", {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-google-key"}):
            self.assertFalse([s for s in next_steps(self.plan, self.today) if s["kind"] in ("safety", "air")])
