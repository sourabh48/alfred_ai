"""Generated images only: private media, metadata and reviewed associations."""
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from apps.mobility.models import TravelPlan, TravelPreferenceProfile, TripPhoto


def synthetic_trip_jpeg(date, *, timestamp=None, latitude_ref="N", latitude=(12, 25, 30)):
    exif = Image.Exif()
    exif[306] = timestamp or date.strftime("%Y:%m:%d 00:15:00")
    exif[34853] = {1: latitude_ref, 2: tuple(map(IFDRational, latitude)),
                   3: "E", 4: tuple(map(IFDRational, (75, 44, 16)))}
    data = BytesIO()
    Image.new("RGB", (32, 24), "navy").save(data, format="JPEG", exif=exif)
    return data.getvalue()


@override_settings(TIME_ZONE="Asia/Kolkata")
class TravelMediaAcceptanceTests(TestCase):
    def setUp(self):
        self.media = Path(self.enterContext(TemporaryDirectory(prefix="alfred-synthetic-media-")))
        self.enterContext(override_settings(MEDIA_ROOT=str(self.media)))
        self.enterContext(patch("apps.mobility.services.travel.providers.base.request", side_effect=AssertionError("Private media must stay local")))
        self.user = get_user_model().objects.create_user("synthetic_media_owner")
        self.other = get_user_model().objects.create_user("synthetic_media_other")
        self.client.force_login(self.user)
        self.past = timezone.localdate() - timedelta(days=5)
        self.plan = TravelPlan.objects.create(user=self.user, title="Synthetic private trip", destination="Coorg",
                                              start_date=self.past, end_date=self.past, status="completed")

    def upload(self, **data):
        image = data.pop("image", synthetic_trip_jpeg(self.past))
        return self.client.post("/api/mobility/trip-photos/", {
            "image": SimpleUploadedFile("synthetic-private.jpg", image, content_type="image/jpeg"), **data})

    def action(self, photo, action, plan=None):
        return self.client.post("/api/mobility/planner/media-suggestions/", {
            "photo_id": photo.pk, "plan_id": (plan or self.plan).pk, "action": action}, content_type="application/json")

    def test_exif_local_first_day_proposes_without_association_and_requires_confirmation(self):
        response = self.upload(caption="Synthetic photo")
        self.assertEqual(response.status_code, 201, response.content)
        photo = TripPhoto.objects.get(user=self.user)
        self.assertEqual(timezone.localtime(photo.taken_at).date(), self.past)
        self.assertAlmostEqual(photo.latitude, 12.425)
        self.assertAlmostEqual(photo.longitude, 75.7377778)
        suggestions = self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"]
        self.assertEqual([(s["photo_id"], s["plan_id"]) for s in suggestions], [(photo.pk, self.plan.pk)])
        self.assertIsNone(photo.travel_plan_id)
        self.assertEqual(self.action(photo, "add").status_code, 200)
        photo.refresh_from_db()
        self.assertEqual(photo.travel_plan_id, self.plan.pk)
        self.assertEqual(self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"], [])

    def test_explicit_metadata_wins_and_last_local_day_is_inclusive(self):
        at = timezone.make_aware(datetime.combine(self.past, datetime.min.time())).replace(hour=23, minute=59)
        self.assertEqual(self.upload(taken_at=at.isoformat(), latitude="12.425", longitude="75.738").status_code, 201)
        photo = TripPhoto.objects.get(user=self.user)
        self.assertEqual(photo.taken_at, at)
        self.assertEqual(photo.longitude, 75.738)
        self.assertEqual(len(self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"]), 1)
        photo.taken_at = at + timedelta(days=1); photo.save()
        self.assertEqual(self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"], [])

    def test_bad_timestamp_does_not_discard_valid_gps_and_bad_hemisphere_abstains(self):
        self.assertEqual(self.upload(image=synthetic_trip_jpeg(self.past, timestamp="not-a-date")).status_code, 201)
        photo = TripPhoto.objects.get(user=self.user)
        self.assertIsNone(photo.taken_at)
        self.assertAlmostEqual(photo.latitude, 12.425)
        self.assertEqual(self.upload(image=synthetic_trip_jpeg(self.past, latitude_ref="X")).status_code, 201)
        invalid = TripPhoto.objects.latest("pk")
        self.assertIsNone(invalid.latitude)
        self.assertIsNone(invalid.longitude)
        self.assertEqual(self.upload(image=synthetic_trip_jpeg(self.past, latitude=(12,))).status_code, 201)
        truncated = TripPhoto.objects.latest("pk")
        self.assertEqual(timezone.localtime(truncated.taken_at).date(), self.past)
        self.assertIsNone(truncated.latitude)
        self.assertEqual(self.upload(image=synthetic_trip_jpeg(self.past, latitude=(12, 60, 30))).status_code, 201)
        self.assertIsNone(TripPhoto.objects.latest("pk").latitude)

    def test_png_without_metadata_remains_private_and_unassigned(self):
        data = BytesIO()
        Image.new("RGB", (16, 16), "purple").save(data, format="PNG")
        self.assertEqual(self.upload(image=data.getvalue()).status_code, 201)
        photo = TripPhoto.objects.get(user=self.user)
        self.assertIsNone(photo.taken_at)
        self.assertIsNone(photo.latitude)
        self.assertIsNone(photo.longitude)
        self.assertIsNone(photo.travel_plan_id)
        self.assertEqual(self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"], [])

    def test_invalid_image_and_coordinates_rejected_before_storage(self):
        self.assertEqual(self.upload(image=b"<html>not an image</html>").status_code, 400)
        self.assertFalse(TripPhoto.objects.exists())
        self.assertFalse([p for p in self.media.rglob("*") if p.is_file()])
        for lat, lon in (("NaN", "75"), ("91", "75"), ("12", "181"), ("12", "")):
            with self.subTest(latitude=lat, longitude=lon):
                self.assertEqual(self.upload(latitude=lat, longitude=lon).status_code, 400)
        self.assertFalse(TripPhoto.objects.exists())

    def test_legacy_nonfinite_coordinates_do_not_manufacture_matches(self):
        from types import SimpleNamespace
        from apps.mobility.services.travel_media import near_destination
        for lat, lon in ((float("nan"), 75), (12, float("inf")), (91, 75), (-12.425, -104.262)):
            with self.subTest(latitude=lat, longitude=lon):
                self.assertFalse(near_destination(SimpleNamespace(latitude=lat, longitude=lon), "Coorg"))

    def test_private_bytes_owner_links_and_csrf(self):
        foreign = TravelPlan.objects.create(user=self.other, title="Foreign trip", destination="Coorg")
        self.assertEqual(self.upload(travel_plan=foreign.pk).status_code, 400)
        response = self.upload()
        self.assertEqual(response.status_code, 201)
        photo = TripPhoto.objects.get(user=self.user)
        served = self.client.get(photo.image.url)
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Cache-Control"], "private, no-store")
        self.assertEqual(b"".join(served.streaming_content), synthetic_trip_jpeg(self.past))
        served.close()
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.user)
        self.assertEqual(csrf.post("/api/mobility/planner/media-suggestions/", {"photo_id": photo.pk, "plan_id": self.plan.pk, "action": "add"}).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(photo.image.url).status_code, 404)
        self.assertEqual(self.client.get(f"/api/mobility/trip-photos/{photo.pk}/").status_code, 404)
        self.assertEqual(self.action(photo, "add").status_code, 404)
        self.assertEqual(self.client.get("/api/mobility/planner/media-suggestions/").json()["suggestions"], [])
        self.client.logout()
        self.assertEqual(self.client.get(photo.image.url).status_code, 302)

    def test_ignore_and_changed_date_do_not_silently_associate(self):
        self.assertEqual(self.upload(location_name="Coorg", taken_at=self.past.isoformat()+"T12:00:00+05:30").status_code, 201)
        photo = TripPhoto.objects.get(user=self.user)
        self.assertEqual(self.action(photo, "ignore").status_code, 200)
        self.assertEqual(self.action(photo, "add").status_code, 400)
        photo.refresh_from_db(); self.assertIsNone(photo.travel_plan_id)
        photo.ignored_plan_ids = []; photo.taken_at += timedelta(days=1); photo.save()
        self.assertEqual(self.action(photo, "add").status_code, 400)

    def test_cached_gallery_reflects_association_and_reviewed_caption_immediately(self):
        self.assertEqual(self.upload().status_code, 201)
        photo = TripPhoto.objects.get(user=self.user)
        url = "/api/mobility/dashboard/"
        self.assertIsNone(self.client.get(url).json()["trip_photos"][0]["travel_plan"])
        self.assertEqual(self.action(photo, "add").status_code, 200)
        self.assertEqual(self.client.get(url).json()["trip_photos"][0]["travel_plan"], self.plan.pk)
        self.assertEqual(self.client.patch(f"/api/mobility/trip-photos/{photo.pk}/", {"caption": "Owner reviewed caption"}, content_type="application/json").status_code, 200)
        self.assertEqual(self.client.get(url).json()["trip_photos"][0]["caption"], "Owner reviewed caption")

    def test_media_learning_requires_both_opt_ins_favorite_and_explicit_tags(self):
        self.assertEqual(self.upload(is_favorite="true", preference_tags='["photography"]').status_code, 201)
        profile = TravelPreferenceProfile.objects.get(user=self.user)
        self.assertNotIn("photography", profile.preferences)
        profile.media_learning_enabled = True; profile.learning_enabled = False; profile.save()
        photo = TripPhoto.objects.get(user=self.user)
        url = f"/api/mobility/trip-photos/{photo.pk}/"
        self.assertEqual(self.client.patch(url, {"caption": "Reviewed locally"}, content_type="application/json").status_code, 200)
        profile.refresh_from_db(); self.assertNotIn("photography", profile.preferences)
        profile.learning_enabled = True; profile.save()
        self.assertEqual(self.client.patch(url, {"preference_tags": ["photography"]}, content_type="application/json").status_code, 200)
        profile.refresh_from_db()
        self.assertFalse(profile.preferences["photography"]["confirmed_by_user"])
