"""Amadeus Travel Builder terms allow keeping its offers only while the app needs them: expired offers are removed
from every place ALFRED saved them, other providers and fresh offers stay, and the search itself is kept."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.mobility.models import TravelPlan, TravelPlanningSession, TravelResearchEvidence, TravelResearchSession
from apps.mobility.services.travel.short_keep import NOTE, purge
from apps.mobility.tasks import cleanup_travel_request_history


def result(provider, expires):
    return {"provider": provider, "category": "flights", "success": True, "expires_at": expires.isoformat(),
            "request_parameters": {"origin": "BLR", "destination": "DEL"},
            "payload": {"options": [{"provider": provider.title(), "fare": "7450"}], "coverage": "Some airlines only."}}


class ShortKeepTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.old, self.fresh = self.now - timedelta(minutes=1), self.now + timedelta(minutes=10)
        self.user = get_user_model().objects.create_user("synthetic-short-keep")

    def test_expired_amadeus_offers_are_removed_everywhere_and_everything_else_stays(self):
        session = TravelPlanningSession.objects.create(user=self.user, candidates=[
            {"name": "Delhi", "flights_result": result("amadeus", self.old), "hotels_result": result("google_lodging", self.old)},
            {"name": "Goa", "flights_result": result("amadeus", self.fresh)}],
            itinerary={"flights_result": result("amadeus", self.old)})
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", itinerary={"flights_result": result("amadeus", self.old)})
        sky = TravelPlan.objects.create(user=self.user, title="Other trip", itinerary={"flights_result": result("skyscanner", self.old)})
        run = TravelResearchSession.objects.create(session=session, result=[result("amadeus", self.old)])
        evidence = TravelResearchEvidence.objects.create(research=run, destination="Delhi", data_type="flights", source_name="amadeus",
                                                         provider="amadeus", valid_until=self.old,
                                                         finding={"options": [{"fare": "7450"}], "attribution": "Live airline prices"})
        kept = TravelResearchEvidence.objects.create(research=run, destination="Goa", data_type="flights", source_name="amadeus",
                                                     provider="amadeus", valid_until=self.fresh, finding={"options": [{"fare": "5000"}]})
        for key, stale in (("amadeus:flights:1:old", self.old), ("amadeus:flights:1:new", self.fresh)):
            VerifiedExternalInsight.objects.create(scope="travel_provider", cache_key=key, title="flights from amadeus",
                                                   source_name="amadeus", source_url="https://example.test/", payload={}, stale_after=stale)

        self.assertEqual(purge(self.now), 5)  # one cache row, one evidence, the planning chat, its research run and one plan
        session.refresh_from_db(); plan.refresh_from_db(); sky.refresh_from_db(); run.refresh_from_db()
        evidence.refresh_from_db(); kept.refresh_from_db()
        gone = session.candidates[0]["flights_result"]
        self.assertEqual(gone["payload"], {"options": [], "coverage": "Some airlines only.", "removed": NOTE})
        self.assertEqual(gone["request_parameters"], {"origin": "BLR", "destination": "DEL"})  # the search itself stays
        self.assertEqual(len(session.candidates[0]["hotels_result"]["payload"]["options"]), 1)  # other providers untouched
        self.assertEqual(len(session.candidates[1]["flights_result"]["payload"]["options"]), 1)  # not yet expired
        self.assertEqual(session.itinerary["flights_result"]["payload"]["options"], [])
        self.assertEqual((plan.itinerary["flights_result"]["payload"]["options"], run.result[0]["payload"]["options"]), ([], []))
        self.assertEqual(len(sky.itinerary["flights_result"]["payload"]["options"]), 1)
        self.assertEqual((evidence.finding["options"], evidence.finding["removed"], len(kept.finding["options"])), ([], NOTE, 1))
        self.assertEqual(list(VerifiedExternalInsight.objects.values_list("cache_key", flat=True)), ["amadeus:flights:1:new"])
        self.assertEqual(purge(self.now), 0)  # nothing left to remove

    def test_the_fifteen_minute_cleanup_job_runs_it(self):
        plan = TravelPlan.objects.create(user=self.user, title="Synthetic trip", itinerary={"flights_result": result("amadeus", self.old)})
        self.assertEqual(cleanup_travel_request_history()["short_keep_removed"], 1)
        plan.refresh_from_db()
        self.assertEqual(plan.itinerary["flights_result"]["payload"]["options"], [])
