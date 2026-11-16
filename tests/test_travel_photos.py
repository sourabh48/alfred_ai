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
