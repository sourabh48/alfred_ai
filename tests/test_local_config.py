import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from alfred_ai.local_config import is_public_default_secret, load_local_environment, native_secret_file


class LocalEnvironmentTests(TestCase):
    def test_process_then_local_then_legacy_precedence(self):
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root / "config").mkdir()
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
            root = Path(directory)
            (root / "config").mkdir()
            (root / "config" / "local.env").write_text("TRAVEL_ORS_API_KEY=other-runtime\n", encoding="utf-8")
            load_local_environment(root / "isolated-runtime")
            self.assertNotIn("TRAVEL_ORS_API_KEY", os.environ)

    def test_native_secret_file_retains_precedence(self):
        from alfred_native import configure
        with TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root / "config").mkdir()
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
            root = Path(directory)
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
