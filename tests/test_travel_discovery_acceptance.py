"""Bounded destination discovery with synthetic sources and owner-only history."""
from copy import deepcopy
from datetime import timedelta

from django.test import TestCase

from apps.mobility.models import TravelPlan, TripLog, TripPhoto
from apps.mobility.services.travel.discovery import remember
from apps.mobility.services.travel_catalog import DESTINATIONS
from apps.mobility.services.travel_discovery import candidates_for, fact
from tests import test_travel_planner as fixtures


class TravelDiscoveryAcceptanceTests(TestCase):
    setUp = fixtures.TravelPlannerTests.setUp

    def options(self, name, **state):
        seed = dict(deepcopy(DESTINATIONS[1]), name=name)
        return candidates_for(self.user, {"origin": fact("Bengaluru"), **state}, destinations=[seed])

    def test_recorded_dynamic_visits_match_case_and_spacing_and_explicit_request_wins(self):
        remember(self.user, {"name": "  Synthetic   Valley "}, "visited")
        self.assertEqual(self.options("synthetic valley")[0]["novelty"], "Previously recorded")
        self.assertEqual(self.options("SYNTHETIC VALLEY", only_new_places=fact(True)), [])
        self.assertEqual(len(self.options("Synthetic Valley", only_new_places=fact(True),
            requested_destination=fact("synthetic valley"))), 1)

    def test_all_rejection_records_apply_across_source_ids_without_affecting_another_owner(self):
        remember(self.user, {"id": "guide:1", "name": "Synthetic Valley"}, "rejected")
        remember(self.user, {"id": "guide:2", "name": "synthetic valley"}, "shown")
        self.assertEqual(self.options("Synthetic Valley"), [])
        remember(self.other, {"name": "Other Valley"}, "visited")
        self.assertEqual(self.options("Other Valley", only_new_places=fact(True))[0]["novelty"], "New in your records")

    def test_dynamic_trip_log_and_photo_locations_are_recorded_without_claiming_unknown_visits(self):
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination="Somewhere else")
        TripLog.objects.create(user=self.user, travel_plan=plan, log_date=self.today,
            title="Synthetic log", location_name="Synthetic Log Valley")
        TripPhoto.objects.create(user=self.user, image="synthetic-unwritten.jpg", location_name="Synthetic Photo Valley")
        for name in ("synthetic log valley", "SYNTHETIC PHOTO VALLEY"):
            with self.subTest(name=name):
                self.assertEqual(self.options(name, only_new_places=fact(True)), [])
        option = self.options("Unknown Valley")[0]
        self.assertIn("not proof you have never been", " ".join(option["why"]))

    def test_dynamic_completed_trip_variants_share_visit_and_recent_counts(self):
        for name in ("Synthetic Valley", " synthetic   valley "):
            TravelPlan.objects.create(user=self.user, title="Synthetic trip", destination=name, status="completed",
                start_date=self.today-timedelta(days=3), end_date=self.today-timedelta(days=1))
        option = self.options("SYNTHETIC VALLEY")[0]
        self.assertIn("2 recorded visit(s), 2 within the last year", " ".join(option["why"]))
