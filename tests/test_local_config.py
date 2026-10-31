from datetime import date, datetime, timezone as utc_timezone
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
from unittest import TestCase, skipUnless
from unittest.mock import patch

from django.apps import apps
from django.test import override_settings
from django.utils import timezone

from alfred_ai import system_time_zone
from alfred_ai.local_config import is_public_default_secret, load_local_environment, native_secret_file
from alfred_ai.system_time_zone import FALLBACK_TIME_ZONE, iana_for_windows_zone, resolve_time_zone
from alfred_private_storage import private_directory
from apps.loans.models import Loan


class RuntimeTimeZoneTests(TestCase):
    def detected(self, windows_name, zone="", override=""):
        with patch.object(system_time_zone, "windows_zone_name", return_value=windows_name), patch.object(
                system_time_zone, "iana_for_windows_zone", return_value=zone) as mapping:
            return resolve_time_zone(override), mapping

    @override_settings(TIME_ZONE="Asia/Kolkata")
    def test_early_morning_in_india_already_has_the_india_date(self):
        # 00:30 IST on 1 November, while it is still 31 October in UTC and Chicago.
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 31, 19, 0, tzinfo=utc_timezone.utc)):
            self.assertEqual(timezone.localdate(), date(2026, 11, 1))
            # A money path that used the UTC date would still count from October and report 2.
            self.assertEqual(Loan(start_date=date(2026, 11, 1), tenure_months=1).months_remaining, 1)

    def test_detected_system_zone_is_used_without_a_warning(self):
        (zone, warning), _ = self.detected("India Standard Time", "Asia/Calcutta")
        self.assertEqual((zone, warning), ("Asia/Calcutta", ""))

    @skipUnless(sys.platform == "win32", "Windows ICU holds the mapping")
    def test_windows_icu_maps_known_names_and_rejects_unknown_ones(self):
        self.assertEqual(iana_for_windows_zone("India Standard Time"), "Asia/Calcutta")
        self.assertEqual(iana_for_windows_zone("Synthetic Unknown Zone"), "")

    def test_unknown_windows_name_falls_back_with_a_warning(self):
        (zone, warning), _ = self.detected("Synthetic Unknown Zone")
        self.assertEqual(zone, FALLBACK_TIME_ZONE)
        self.assertNotEqual(zone, "America/Chicago")
        self.assertIn("Synthetic Unknown Zone", warning)
        self.assertIn(FALLBACK_TIME_ZONE, warning)

    def test_detection_failure_falls_back_with_a_warning(self):
        with patch.object(system_time_zone, "windows_zone_name", side_effect=ImportError):
            zone, warning = resolve_time_zone()
        self.assertEqual(zone, FALLBACK_TIME_ZONE)
        self.assertIn("ImportError", warning)

    def test_valid_override_wins_over_detection(self):
        (zone, warning), mapping = self.detected("India Standard Time", "Asia/Calcutta", override="Europe/London")
        self.assertEqual((zone, warning), ("Europe/London", ""))
        mapping.assert_not_called()

    def test_invalid_override_warns_and_uses_detection(self):
        for override in ("Synthetic/Unknown", "../secret", "Asia"):
            with self.subTest(override=override):
                (zone, warning), _ = self.detected("India Standard Time", "Asia/Calcutta", override=override)
                self.assertEqual(zone, "Asia/Calcutta")
                self.assertIn(repr(override), warning)

    @override_settings(TIME_ZONE_WARNING="Synthetic time zone warning")
    def test_startup_logs_the_fallback_warning(self):
        with self.assertLogs("apps.users.apps", "WARNING") as logs:
            apps.get_app_config("users").ready()
        self.assertIn("Synthetic time zone warning", logs.output[0])


class LocalEnvironmentTests(TestCase):
    def test_process_then_local_then_legacy_precedence(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = private_directory(Path(directory))
            private_directory(root / "config")
            (root / "config" / "local.env").write_text(
                "TRAVEL_WEB_ENABLED=false\nTRAVEL_ORS_API_KEY=local-fixture\n", encoding="utf-8")
            (root / ".env").write_text(
                "TRAVEL_WEB_ENABLED=true\nTRAVEL_ORS_API_KEY=legacy-fixture\nTRAVEL_USE_MODE=personal_noncommercial\n",
                encoding="utf-8")
            os.environ["TRAVEL_ORS_API_KEY"] = "process-fixture"
            load_local_environment(root)
            self.assertEqual(os.environ["TRAVEL_WEB_ENABLED"], "false")
            self.assertEqual(os.environ["TRAVEL_ORS_API_KEY"], "process-fixture")
            self.assertEqual(os.environ["TRAVEL_USE_MODE"], "personal_noncommercial")

    def test_reads_only_selected_runtime_and_accepts_missing_files(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = private_directory(Path(directory))
            private_directory(root / "config")
            (root / "config" / "local.env").write_text("TRAVEL_ORS_API_KEY=other-runtime\n", encoding="utf-8")
            load_local_environment(root / "isolated-runtime")
            self.assertNotIn("TRAVEL_ORS_API_KEY", os.environ)

    def test_native_secret_file_retains_precedence(self):
        from alfred_native import configure
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = private_directory(Path(directory))
            private_directory(root / "config")
            (root / "config" / "local.env").write_text(
                "DJANGO_SECRET_KEY=local-fixture\nTRAVEL_ORS_API_KEY=local-provider-fixture\n", encoding="utf-8")
            native = root / "config" / "native.env"
            native.write_text('DJANGO_SECRET_KEY=native-fixture\nDJANGO_SECRET_KEY_FALLBACKS=["previous-fixture"]\n', encoding="utf-8")
            before = native.read_bytes()
            with patch("alfred_native.os.chdir"), patch("django.setup"):
                configure(root)
            self.assertEqual(os.environ["DJANGO_SECRET_KEY"], "native-fixture")
            self.assertEqual(json.loads(os.environ["DJANGO_SECRET_KEY_FALLBACKS"]), ["previous-fixture"])
            self.assertEqual(os.environ["TRAVEL_ORS_API_KEY"], "local-provider-fixture")
            self.assertEqual(os.environ["ALFRED_DATA_DIR"], str(root))
            self.assertEqual(native.read_bytes(), before)

    def test_fresh_source_key_is_persisted_and_explicit_key_wins(self):
        from alfred_ai.settings import _default_secret_key
        with TemporaryDirectory() as directory, patch.dict(os.environ, {"ALFRED_DATA_DIR": directory}, clear=True):
            root = Path(directory)
            key = _default_secret_key(True)
            self.assertGreaterEqual(len(key), 50)
            native = root / "config/native.env"
            before = native.read_bytes()
            os.environ.pop("DJANGO_SECRET_KEY")
            self.assertEqual(_default_secret_key(True), key)
            os.environ["DJANGO_SECRET_KEY"] = "explicit-synthetic-key"
            self.assertEqual(_default_secret_key(True), "explicit-synthetic-key")
            self.assertEqual(native.read_bytes(), before)

    def test_retained_database_requires_previous_key_and_preserves_tokens(self):
        from django.test import override_settings
        from apps.integrations.models import _decrypt_token, _encrypt_token
        import environ

        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = private_directory(Path(directory))
            (root / "db.sqlite3").write_bytes(b"retained synthetic database")
            with self.assertRaisesRegex(RuntimeError, "previous DJANGO_SECRET_KEY"):
                native_secret_file(root)
            self.assertFalse((root / "config/native.env").exists())
            with override_settings(SECRET_KEY="previous-synthetic-key", SECRET_KEY_FALLBACKS=[]):
                token = _encrypt_token("synthetic-email-token")
            os.environ["DJANGO_SECRET_KEY"] = "previous-synthetic-key"
            environ.Env.read_env(native_secret_file(root), overwrite=True)
            fallbacks = json.loads(os.environ["DJANGO_SECRET_KEY_FALLBACKS"])
            self.assertEqual(fallbacks, ["previous-synthetic-key"])
            with override_settings(SECRET_KEY=os.environ["DJANGO_SECRET_KEY"], SECRET_KEY_FALLBACKS=fallbacks):
                self.assertEqual(_decrypt_token(token), "synthetic-email-token")
            self.assertEqual((root / "db.sqlite3").read_bytes(), b"retained synthetic database")

    def test_public_key_fingerprint_rejects_known_value_without_plaintext_constant(self):
        key = "synthetic-public-key"
        fingerprint = hashlib.sha256(key.encode()).hexdigest()
        with patch("alfred_ai.local_config.PUBLIC_DEFAULT_SECRET_SHA256", fingerprint):
            self.assertTrue(is_public_default_secret(key))
            self.assertFalse(is_public_default_secret("different-synthetic-key"))
