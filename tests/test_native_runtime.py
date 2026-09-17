"""Boundary checks that do not require the long-running native integration drill."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from alfred_ai.services.ocr_process import ocr_command
from apps.integrations.models import _encrypt_token, _decrypt_token
from alfred_native import InstanceLock, data_directory, parent_is_running


class NativeRuntimeBoundaryTests(SimpleTestCase):
    def test_process_monitor_recognizes_its_own_process(self):
        self.assertTrue(parent_is_running(os.getpid()))
        self.assertFalse(parent_is_running(2147483647))

    def test_singleton_lock_releases_after_exit(self):
        with TemporaryDirectory() as directory:
            data = Path(directory)
            with InstanceLock(data):
                with self.assertRaises(OSError):
                    with InstanceLock(data):
                        self.fail("A second supervisor acquired the same data folder")
            with InstanceLock(data):
                pass

    def test_explicit_data_folder_wins_over_environment(self):
        with patch.dict(os.environ, {"ALFRED_DATA_DIR": "wrong-folder"}):
            self.assertEqual(data_directory("chosen-folder"), Path("chosen-folder").resolve())

    def test_packaged_ocr_uses_worker_entry_point(self):
        with patch("sys.frozen", True, create=True):
            result = ocr_command("document", "do not execute arbitrary source", "sample.pdf", 2)
        self.assertEqual(result[1:], ["--ocr-worker", "document", "sample.pdf", "2"])

    def test_email_tokens_survive_native_secret_rotation(self):
        with override_settings(SECRET_KEY="previous-key", SECRET_KEY_FALLBACKS=[]):
            token = _encrypt_token("synthetic-email-token")
        with override_settings(SECRET_KEY="new-native-key", SECRET_KEY_FALLBACKS=["previous-key"]):
            self.assertEqual(_decrypt_token(token), "synthetic-email-token")
            new_token = _encrypt_token("new-token")
        with override_settings(SECRET_KEY="new-native-key", SECRET_KEY_FALLBACKS=[]):
            self.assertEqual(_decrypt_token(new_token), "new-token")
