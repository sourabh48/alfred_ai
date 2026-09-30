import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from alfred_ai.local_config import load_local_environment


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
            (root / "config" / "native.env").write_text("DJANGO_SECRET_KEY=native-fixture\n", encoding="utf-8")
            with patch("alfred_native.os.chdir"), patch("django.setup"):
                configure(root)
            self.assertEqual(os.environ["DJANGO_SECRET_KEY"], "native-fixture")
            self.assertEqual(os.environ["TRAVEL_ORS_API_KEY"], "local-provider-fixture")
            self.assertEqual(os.environ["ALFRED_DATA_DIR"], str(root))
