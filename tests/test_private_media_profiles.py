import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import clear_url_caches, resolve

from apps.expenses.models import StatementUpload


class PrivateMediaProfilesTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory(prefix="alfred-media-synthetic-")
        self.addCleanup(self.directory.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.directory.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.owner = get_user_model().objects.create_user(username="media-owner")
        self.other = get_user_model().objects.create_user(username="media-other")
        self.document = StatementUpload.objects.create(user=self.owner,
            original_file=ContentFile(b"synthetic-document", name="owned.txt"))
        self.url = self.document.original_file.url

    def test_anonymous_and_invalid_session_cannot_read_direct_media(self):
        for client in (Client(), Client()):
            client.cookies["sessionid"] = "invalid-synthetic-session"
            response = client.get(self.url)
            self.assertEqual(response.status_code, 302)
            self.assertNotIn(b"synthetic-document", response.content)

    def test_only_owner_can_download_with_private_no_store_headers(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        try:
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            self.assertEqual(b"".join(response.streaming_content), b"synthetic-document")
        finally:
            response.close()

    def test_traversal_unregistered_and_deleted_files_are_unavailable(self):
        self.client.force_login(self.owner)
        (Path(self.directory.name) / "unregistered.txt").write_text("synthetic-only")
        self.assertEqual(self.client.get("/media/unregistered.txt").status_code, 404)
        self.assertEqual(self.client.get("/media/../outside.txt").status_code, 404)
        self.assertEqual(self.client.get("/media/%2e%2e/outside.txt").status_code, 404)
        Path(self.document.original_file.path).unlink()
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_missing_permissions_or_deleted_between_check_and_open_are_safe(self):
        self.client.force_login(self.owner)
        for error in (PermissionError, FileNotFoundError):
            with patch("alfred_ai.native_views.Path.open", side_effect=error("synthetic")):
                self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_source_debug_and_native_urls_both_use_owner_handler(self):
        from alfred_ai.native_views import private_media
        import alfred_ai.urls as urls
        try:
            for native, debug in ((False, True), (False, False), (True, False)):
                with override_settings(ALFRED_NATIVE_RUNTIME=native, DEBUG=debug):
                    importlib.reload(urls)
                    clear_url_caches()
                    self.assertIs(resolve(self.url).func, private_media)
                    self.assertEqual(Client().get(self.url).status_code, 302)
        finally:
            importlib.reload(urls)
            clear_url_caches()
