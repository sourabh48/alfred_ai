"""Offline world dataset: trips matched to countries and states without a network call."""
from datetime import date
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.mobility.models import TravelPlan, TripLog
from apps.mobility.services.travel import world


class WorldMatchingTests(SimpleTestCase):
    def test_names_match_a_state_and_its_country(self):
        place = world.match_text("Manali, Himachal Pradesh")
        self.assertEqual((place["country_code"], place["state"], place["flag"]), ("IN", "Himachal Pradesh", "\U0001F1EE\U0001F1F3"))
        self.assertEqual(world.match_text("goa")["country"], "India")
        self.assertEqual(world.match_text("São Paulo, Brazil")["state"], "São Paulo")

    def test_a_country_name_alone_or_with_a_city_gives_no_state(self):
        self.assertEqual((world.match_text("Paris, France")["country_code"], world.match_text("Paris, France")["state"]), ("FR", ""))
        self.assertIsNone(world.match_text("Trip around NPL"))  # ISO codes count only as a whole upper-case part
        self.assertEqual(world.match_text("Kathmandu, NPL")["country_code"], "NP")

    def test_ambiguous_or_unknown_names_stay_unmatched_unless_the_country_settles_them(self):
        self.assertIsNone(world.match_text("Punjab"))  # India and Pakistan both have one
        self.assertEqual(world.match_text("Punjab, Pakistan")["country_code"], "PK")
        self.assertEqual(world.match_text("Georgia")["country_code"], "GE")
        self.assertEqual(world.match_text("Atlanta, Georgia, United States")["state"], "Georgia")
        self.assertIsNone(world.match_text("Somewhere quiet"))
        self.assertIsNone(world.match_text(""))

    def test_coordinates_use_the_nearest_state_and_open_sea_matches_nothing(self):
        place = world.match_point(32.24, 77.19)  # Manali
        self.assertEqual((place["country_code"], place["state"]), ("IN", "Himachal Pradesh"))
        self.assertIsNone(world.match_point(-40.0, -130.0))
        self.assertIsNone(world.match_point(None, 77.0))
        self.assertEqual(world.match_place("Hotel Snow View", 15.49, 73.82)["state"], "Goa")


class VisitedTotalsTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="synthetic-world-owner")
        self.client.force_login(self.owner)

    def test_dashboard_counts_countries_and_states_and_flags_each_plan_offline(self):
        done = TravelPlan.objects.create(user=self.owner, title="Hills", destination="Shimla, Himachal Pradesh", status="completed",
                                         start_date=date(2026, 5, 1), end_date=date(2026, 5, 4))
        TravelPlan.objects.create(user=self.owner, title="Coast", destination="Goa", status="on_trip",
                                            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3))
        abroad = TravelPlan.objects.create(user=self.owner, title="Abroad", destination="Kathmandu, Nepal", status="planned",
                                           start_date=date(2027, 1, 1), end_date=date(2027, 1, 5))
        TravelPlan.objects.create(user=self.owner, title="Someday", destination="Punjab", status="draft")
        # A log on a plan not yet travelled still counts: here its coordinates place it in Bagmati.
        TripLog.objects.create(user=self.owner, travel_plan=abroad, log_date=date(2026, 12, 1), title="Scouting",
                               location_name="Thamel guest house", latitude=27.71, longitude=85.31)
        TripLog.objects.create(user=self.owner, travel_plan=done, log_date=date(2026, 5, 2), title="Day 2", location_name="Shimla")
        other = get_user_model().objects.create_user(username="synthetic-world-other")
        TravelPlan.objects.create(user=other, title="Not mine", destination="France", status="completed")

        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network call")), \
                mock.patch("socket.create_connection", side_effect=AssertionError("network call")):
            payload = self.client.get("/api/mobility/dashboard/").json()

        self.assertEqual((payload["summary"]["countries_visited"], payload["summary"]["states_visited"]), (2, 3))
        places = {plan["title"]: plan["place"] for plan in payload["travel_plans"]}
        self.assertEqual(places["Abroad"]["flag"], "\U0001F1F3\U0001F1F5")
        self.assertEqual(places["Coast"]["state"], "Goa")
        self.assertIsNone(places["Someday"])
        self.assertNotIn("Not mine", places)

    def test_no_trips_means_zero_totals(self):
        summary = self.client.get("/api/mobility/dashboard/").json()["summary"]
        self.assertEqual((summary["countries_visited"], summary["states_visited"]), (0, 0))
