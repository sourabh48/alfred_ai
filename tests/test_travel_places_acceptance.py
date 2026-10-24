"""Offline synthetic POI evidence, never booking or permit verification."""
from copy import deepcopy
from datetime import timedelta
from unittest.mock import patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.integrations.models import VerifiedExternalInsight
from apps.mobility.services.travel.cache import query
from apps.mobility.services.travel.presentation import age_saved_facts
from apps.mobility.services.travel.providers.places import OverpassPlaces
from apps.mobility.services.travel_conversation import new_session


def synthetic_place_result():
    now = timezone.now()
    return {"provider": "overpass", "category": "places", "success": True, "status": "ok",
        "freshness": "LIVE", "confidence": "LIKELY", "source_url": "https://www.openstreetmap.org/copyright",
        "attribution": "Synthetic OSM fixture; not a real site or availability check",
        "retrieved_at": (now-timedelta(hours=1)).isoformat(), "verified_at": (now-timedelta(hours=1)).isoformat(),
        "expires_at": (now+timedelta(hours=1)).isoformat(), "payload": {"coverage": "Mapping coverage is incomplete.",
        "places": [{"id": "osm:node:1", "name": "Synthetic camp <img src=x onerror=alert(1)>",
            "category": "camping", "lat": 12, "lon": 77, "source_url": "https://www.openstreetmap.org/node/1",
            "opening_hours": "24/7", "access": "yes", "availability": "UNKNOWN", "permit_status": "unverified"}]}}


class TravelPlacesAcceptanceTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user("synthetic_poi_owner")
        self.other = get_user_model().objects.create_user("synthetic_poi_other")
        self.client.force_login(self.owner)
        self.enterContext(patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("No provider activation")))

    def candidate(self, result=None):
        return {"name": "Synthetic destination", "factors": {}, "sources": [],
                "places_result": result or synthetic_place_result(), "quality": {"verified": ["places"]}}

    def test_saved_fresh_result_keeps_source_times_and_is_never_live_on_read(self):
        candidate = self.candidate()
        before = deepcopy(candidate)
        result = age_saved_facts({"candidates": [candidate]})["candidates"][0]
        self.assertEqual(result["places_result"]["freshness"], "RECENTLY_VERIFIED")
        self.assertEqual(result["places_result"]["retrieved_at"], candidate["places_result"]["retrieved_at"])
        self.assertEqual(result["places_result"]["payload"]["places"][0]["availability"], "UNKNOWN")
        self.assertEqual(candidate, before)

    def test_expired_result_is_explicitly_stale_and_not_in_verified_categories(self):
        source = synthetic_place_result()
        source["expires_at"] = (timezone.now()-timedelta(seconds=1)).isoformat()
        result = age_saved_facts({"candidates": [self.candidate(source)]})["candidates"][0]
        self.assertTrue(result["places_result"]["stale"])
        self.assertEqual(result["places_result"]["status"], "stale")
        self.assertEqual(result["places_result"]["confidence"], "UNKNOWN")
        self.assertNotIn("places", result["quality"]["verified"])

    def test_unusable_clock_or_source_abstains_instead_of_claiming_verification(self):
        for field, value in (("expires_at", None), ("expires_at", "2026-99-99T12:00:00Z"),
                ("expires_at", "2026-10-24T12:00:00"), ("retrieved_at", None),
                ("retrieved_at", (timezone.now()+timedelta(days=2)).isoformat()), ("source_url", "javascript:alert(1)")):
            with self.subTest(field=field, value=value):
                source = synthetic_place_result(); source[field] = value
                result = age_saved_facts({"candidates": [self.candidate(source)]})["candidates"][0]
                self.assertEqual(result["places_result"]["confidence"], "UNKNOWN")
                self.assertNotIn("places", result["quality"]["verified"])

    def test_api_read_is_owner_scoped_and_does_not_rewrite_saved_evidence(self):
        session = new_session(self.owner)
        session.candidates = [self.candidate()]; session.save()
        before = deepcopy(session.candidates)
        url = f"/api/mobility/planner/sessions/{session.pk}/"
        self.assertEqual(self.client.get(url).status_code, 200)
        session.refresh_from_db(); self.assertEqual(session.candidates, before)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def provider(self):
        provider = OverpassPlaces(); provider.min_interval = 0
        self.enterContext(patch.object(provider, "unavailable_reason", return_value=""))
        self.enterContext(patch.object(provider, "fetch", return_value=({"elements": [{"type": "node", "id": 1,
            "lat": 12, "lon": 77, "tags": {"name": "Synthetic camp", "tourism": "camp_site", "opening_hours": "24/7"}}]}, "synthetic-response")))
        return provider

    def test_cache_reuse_and_offline_fallback_preserve_original_provenance(self):
        provider = self.provider(); parameters = {"latitude": 12, "longitude": 77}
        first = query(provider, parameters)
        cached = query(provider, parameters)
        self.assertEqual(cached.freshness, "RECENTLY_VERIFIED")
        self.assertEqual(provider.fetch.call_count, 1)
        self.assertEqual(cached.payload["places"][0]["permit_status"], "unverified")
        VerifiedExternalInsight.objects.update(stale_after=timezone.now()-timedelta(seconds=1))
        provider.fetch.side_effect = requests.Timeout("Synthetic offline")
        stale = query(provider, parameters)
        self.assertTrue(stale.stale)
        self.assertEqual((stale.retrieved_at, stale.source_url, stale.response_hash), (first.retrieved_at, first.source_url, first.response_hash))
        self.assertEqual(stale.error, "timeout")
        self.assertEqual(stale.payload["places"][0]["availability"], "UNKNOWN")

    def test_partial_or_unconfigured_results_cannot_invent_places(self):
        provider = self.provider()
        provider.fetch.return_value = ({"remark": "Synthetic partial response", "elements": []}, "partial")
        result = query(provider, {"latitude": 12, "longitude": 77})
        self.assertFalse(result.success)
        self.assertEqual(result.error, "incomplete_poi_response")
        self.assertFalse(VerifiedExternalInsight.objects.exists())
        with patch.dict("os.environ", {"TRAVEL_OVERPASS_URL": ""}):
            unavailable = query(OverpassPlaces(), {"latitude": 13, "longitude": 78})
        self.assertFalse(unavailable.success)
        self.assertEqual(unavailable.payload, {})
