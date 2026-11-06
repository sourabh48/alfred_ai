"""TRAVEL-20: trip videos are stored locally, checked by header and visible only to their owner."""
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import path

from alfred_ai.native_views import private_media
from alfred_ai.urls import urlpatterns as application_urls
from apps.mobility.models import TravelPlan, TripVideo
from apps.users.services import clear_user_fed_data

urlpatterns = [path("media/<path:path>", private_media)] + application_urls
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64
WEBM = bytes.fromhex("1a45dfa3") + b"\x00" * 64


def clip(name="ride.mp4", data=MP4, kind="video/mp4"):
    return SimpleUploadedFile(name, data, content_type=kind)


@override_settings(ROOT_URLCONF=__name__)
class TripVideoTests(TestCase):
    def setUp(self):
        self.media = self.enterContext(TemporaryDirectory(prefix="alfred-trip-video-"))
        self.enterContext(override_settings(MEDIA_ROOT=self.media))
        users = get_user_model().objects
        self.owner = users.create_user(username="synthetic-video-owner")
        self.other = users.create_user(username="synthetic-video-other")
        self.plan = TravelPlan.objects.create(user=self.owner, title="Synthetic coast ride", destination="Gokarna")
        self.client.force_login(self.owner)

    def upload(self, **fields):
        return self.client.post("/api/mobility/trip-videos/", {"video": clip(), **fields})

    def test_owner_uploads_lists_watches_and_renames_a_video(self):
        response = self.upload(travel_plan=self.plan.pk, caption="Sunset <b>ride</b>")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertNotIn("video", response.json())  # the stored path is only exposed as the private URL
        listed = self.client.get("/api/mobility/trip-videos/").json()
        self.assertEqual([(v["caption"], v["travel_plan_title"]) for v in listed], [("Sunset <b>ride</b>", "Synthetic coast ride")])
        watched = self.client.get(listed[0]["video_url"])
        self.assertEqual((watched.status_code, watched["Cache-Control"]), (200, "private, no-store"))
        self.assertEqual(b"".join(watched.streaming_content), MP4)
        self.assertEqual(self.client.post("/api/mobility/trip-videos/", {"video": clip("clip.webm", WEBM, "video/webm")}).status_code, 201)
        renamed = self.client.patch(f"/api/mobility/trip-videos/{listed[0]['id']}/", {"caption": "Coast"}, content_type="application/json")
        self.assertEqual(renamed.json()["caption"], "Coast")

    def test_files_that_are_not_videos_are_refused(self):
        for upload in (clip("ride.mp4", b"MZ" + b"\x00" * 64), clip("ride.webm", MP4), clip("ride.exe", MP4), clip("ride.mov", b"")):
            with self.subTest(name=upload.name):
                self.assertEqual(self.client.post("/api/mobility/trip-videos/", {"video": upload}).status_code, 400)
        self.assertFalse(TripVideo.objects.exists())

    def test_other_accounts_cannot_see_attach_or_delete(self):
        video = TripVideo.objects.get(pk=self.upload().json()["id"])
        url = self.client.get("/api/mobility/trip-videos/").json()[0]["video_url"]
        foreign_plan = TravelPlan.objects.create(user=self.other, title="Foreign", destination="Coorg")
        self.assertEqual(self.upload(travel_plan=foreign_plan.pk).status_code, 400)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get("/api/mobility/trip-videos/").json(), [])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/mobility/trip-videos/{video.pk}/").status_code, 404)
        self.assertTrue(Path(video.video.path).exists())

    def test_deleting_removes_the_file_and_a_video_cannot_be_swapped(self):
        video = TripVideo.objects.get(pk=self.upload().json()["id"])
        swap = self.client.patch(f"/api/mobility/trip-videos/{video.pk}/", encode_multipart(BOUNDARY, {"video": clip("other.mp4")}), content_type=MULTIPART_CONTENT)
        self.assertEqual(swap.status_code, 400)
        file = Path(video.video.path)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(f"/api/mobility/trip-videos/{video.pk}/").status_code, 204)
        self.assertFalse(file.exists())

    def test_account_data_reset_removes_videos_and_files(self):
        video = TripVideo.objects.get(pk=self.upload().json()["id"])
        file = Path(video.video.path)
        with self.captureOnCommitCallbacks(execute=True):
            counts = clear_user_fed_data(self.owner)
        self.assertEqual(counts.get("trip_videos"), 1)
        self.assertFalse(TripVideo.objects.exists())
        self.assertFalse(file.exists())
