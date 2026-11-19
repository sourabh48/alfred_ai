import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services.public_http import PublicResponse
from apps.mobility.models import TravelPlanningSession
from apps.mobility.planner_views import gallery_places
from apps.mobility.services.travel.cache import query
from apps.mobility.services.travel.providers.photos import GooglePlacePhoto
from apps.mobility.services.travel.providers.base import ProviderError
from apps.integrations.models import VerifiedExternalInsight


class TravelPhotoTests(TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-key"}))
        self.network = self.enterContext(patch("apps.mobility.services.travel.providers.photos.request"))
        self.network.return_value = PublicResponse(b"synthetic-image", "image/jpeg", 200)
        self.api = self.enterContext(patch("apps.mobility.services.travel.providers.photos.request_json"))
        self.photo = {"name": "places/p1/photos/ref1", "authorAttributions": [{"displayName": "Synthetic photographer", "uri": "https://example.com/credit"}]}
        self.api.side_effect = [({"id": "p1", "photos": [self.photo]}, ""), ({"photoUri": "https://lh3.googleusercontent.com/photo"}, "")]*2

    def test_fresh_metadata_credits_and_no_persisted_image_or_reference(self):
        for _ in range(2):
            result = query(GooglePlacePhoto(), {"place_id": "p1", "index": 0})
            self.assertTrue(result.success, result.error)
            self.assertEqual(result.payload["authors"][0]["name"], "Synthetic photographer")
            self.assertTrue(result.payload["image"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(self.api.call_count, 4)
        self.assertFalse(VerifiedExternalInsight.objects.filter(source_name="google_place_photos").exists())
        self.assertNotIn("headers", self.network.call_args.kwargs)

    def test_identity_path_and_photo_index_are_validated_before_network(self):
        for params in ({"place_id": "../bad", "index": 0}, {"place_id": "p1", "index": -1}, {"place_id": "p1", "index": True}):
            with self.subTest(params=params), self.assertRaises(ProviderError):
                GooglePlacePhoto().parameters(params)
        self.api.assert_not_called()

    def test_photo_resource_and_image_host_cannot_redirect_to_private_services(self):
        for resource, uri in (("places/p2/photos/ref", "https://lh3.googleusercontent.com/photo"), ("places/p1/photos/ref", "https://127.0.0.1/photo")):
            self.api.side_effect = [({"id": "p1", "photos": [{"name": resource}]}, ""), ({"photoUri": uri}, "")]
            with self.subTest(resource=resource), self.assertRaises(ProviderError):
                GooglePlacePhoto().fetch({"place_id": "p1", "index": 0})
        self.network.assert_not_called()

    def test_no_key_means_no_network(self):
        with patch.dict(os.environ, {"TRAVEL_GOOGLE_MAPS_API_KEY": ""}):
            result = query(GooglePlacePhoto(), {"place_id": "p1", "index": 0})
        self.assertFalse(result.success)
        self.api.assert_not_called()

    def test_owner_and_trip_place_boundary_and_no_store_response(self):
        owner = get_user_model().objects.create_user("photo-owner")
        stranger = get_user_model().objects.create_user("photo-stranger")
        session = TravelPlanningSession.objects.create(user=owner, candidates=[{"id": "google:p1", "name": "Synthetic place", "lat": 12, "lon": 77}])
        key = gallery_places(session)[0][0]
        path = f"/api/mobility/planner/sessions/{session.pk}/photos/"
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(path, {"place": key}).status_code, 404)
        self.client.force_login(owner)
        self.assertEqual(self.client.get(path, {"place": "not-in-trip"}).status_code, 400)
        response = self.client.get(path, {"place": key})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ready")
        self.assertIn("no-store", response["Cache-Control"])
        session.refresh_from_db()
        self.assertNotIn("photos", str(session.candidates))

    def test_name_lookup_uses_the_nearest_same_named_place_that_has_photos(self):
        """Owner check 2026-11-19: Sakleshpur showed no photo because Google returned more than one place with that name."""
        def place(identity, name, km, photos=True):
            return {"id": identity, "displayName": {"text": name}, "location": {"latitude": 12.944 + km / 111, "longitude": 75.788},
                    **({"photos": [{"name": f"places/{identity}/photos/ref", "authorAttributions": []}]} if photos else {})}
        found = [place("station", "Sakleshpur", 1, photos=False), place("town", "Sakleshpur", 3), place("far", "Sakleshpur", 60),
                 place("stand", "Sakleshpur Bus Stand", 0.5), place("other", "SAKLESHPUR", 8)]
        self.api.side_effect = [({"places": found}, ""), ({"photoUri": "https://lh3.googleusercontent.com/photo"}, "")]
        payload, _ = GooglePlacePhoto().fetch({"name": "Sakleshpur", "latitude": 12.944, "longitude": 75.788, "index": 0})
        self.assertEqual(payload["count"], 1)
        self.assertIn("places/town/photos/ref", str(self.api.call_args_list[1]))
        for places in ([place("far", "Sakleshpur", 60)], [place("stand", "Sakleshpur Bus Stand", 0.5)], []):
            self.api.side_effect = [({"places": places}, "")]
            with self.subTest(places=[p["displayName"]["text"] for p in places]), self.assertRaisesRegex(ProviderError, "place_identity_unconfirmed"):
                GooglePlacePhoto().fetch({"name": "Sakleshpur", "latitude": 12.944, "longitude": 75.788, "index": 0})

    def test_a_local_spelling_of_the_same_name_still_finds_the_photo(self):
        """Owner check 2026-11-20: Sakleshpur still had no photo because Google names the town "Sakleshpura"."""
        from apps.mobility.services.travel.providers.photos import same_place
        self.assertTrue(all(same_place(a, "Sakleshpur") for a in ("Sakleshpura", "SAKLESHPUR", "Sakleshpur ")))
        self.assertFalse(any(same_place(a, "Sakleshpur") for a in ("Sakleshpur Bus Stand", "Sakle", "Hassan")))
        self.assertFalse(same_place("Goas", "Goa"))  # too short to guess
        town = {"id": "town", "displayName": {"text": "Sakleshpura"}, "location": {"latitude": 12.95, "longitude": 75.79},
                "photos": [{"name": "places/town/photos/ref", "authorAttributions": []}]}
        self.api.side_effect = [({"places": [town]}, ""), ({"photoUri": "https://lh3.googleusercontent.com/photo"}, "")]
        payload, _ = GooglePlacePhoto().fetch({"name": "Sakleshpur", "latitude": 12.944, "longitude": 75.788, "index": 0})
        self.assertEqual(payload["count"], 1)

    def test_a_photo_turned_away_while_another_loads_says_busy_so_the_page_retries(self):
        from apps.mobility.services.travel.providers.base import ProviderResult
        owner = get_user_model().objects.create_user("photo-busy-owner")
        session = TravelPlanningSession.objects.create(user=owner, candidates=[{"id": "google:p1", "name": "Synthetic place", "lat": 12, "lon": 77}])
        self.client.force_login(owner)
        path, key = f"/api/mobility/planner/sessions/{session.pk}/photos/", gallery_places(session)[0][0]
        for error, busy in (("provider_busy_or_backoff", True), ("local_quota_exhausted", False)):
            with self.subTest(error=error), patch("apps.mobility.planner_views.query", return_value=ProviderResult("google_place_photos", "photos", error=error)):
                data = self.client.get(path, {"place": key}).json()
            self.assertEqual((data["status"], data["busy"]), ("unavailable", busy))

    def test_weekend_idea_photo_looks_up_only_offline_guide_places(self):
        from apps.mobility.services.travel_catalog import DESTINATIONS
        owner = get_user_model().objects.create_user("photo-guide-owner")
        session = TravelPlanningSession.objects.create(user=owner)
        path = f"/api/mobility/planner/sessions/{session.pk}/photos/"
        self.client.force_login(owner)
        self.assertEqual(self.client.get(path, {"name": "Somewhere not in the guide"}).status_code, 400)
        self.api.assert_not_called()
        guide = DESTINATIONS[0]
        with patch("apps.mobility.planner_views.query") as provider:
            provider.return_value.success = False
            provider.return_value.error = "provider_busy_or_backoff"
            response = self.client.get(path, {"name": guide["name"].upper()})
        self.assertEqual(response.json()["place"], guide["name"])
        self.assertEqual(provider.call_args.args[1], {"name": guide["name"], "latitude": guide["lat"], "longitude": guide["lon"], "index": 0})
