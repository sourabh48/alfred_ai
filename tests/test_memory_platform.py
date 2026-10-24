"""Unsupported hosts must refuse private storage without fallback or data loss."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from apps.ml_engine.services import memory_key
from apps.ml_engine.services.persistent_memory import MemoryStore


class UnsupportedMemoryPlatformTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-unsupported-memory-"))
        self.root = Path(directory).resolve()
        self.vault = self.root / "vault"
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=self.vault,
            ALFRED_ABUSE_THROTTLE_DIR=str(self.root / "limits")))
        # Linux CI exercises the real platform; Windows also checks the refusal contract.
        if os.name == "nt":
            self.enterContext(patch.object(memory_key, "os", SimpleNamespace(name="posix")))
        self.owner = get_user_model().objects.create_user(username="synthetic-unsupported-memory")

    def test_directory_and_key_protection_refuse_before_writing(self):
        with self.assertRaises(memory_key.MemoryStorageUnavailable):
            memory_key.private_directory(self.vault)
        for decrypt in (False, True):
            with self.subTest(decrypt=decrypt), self.assertRaises(memory_key.MemoryStorageUnavailable):
                memory_key.protect_key(b"SYNTHETIC-PRIVATE-KEY", decrypt=decrypt)
        with patch("apps.ml_engine.services.persistent_memory.OllamaEmbeddings") as embeddings:
            with self.assertRaises(memory_key.MemoryStorageUnavailable):
                MemoryStore(self.vault)
            embeddings.assert_not_called()
        self.assertFalse(self.vault.exists())

    def test_api_refuses_reads_and_writes_and_preserves_existing_data(self):
        self.vault.mkdir()
        marker = self.vault / "preserved.bin"
        marker.write_bytes(b"SYNTHETIC-PRIVATE-DATA")
        self.client.force_login(self.owner)
        requests = (
            ("get", "/api/ai/memories/", None),
            ("post", "/api/ai/memories/", {"content": {"text": "SYNTHETIC-PRIVATE-DATA"},
                "provenance": {"source": "synthetic"}, "verified": True}),
            ("post", "/api/ai/memories/retrieve/", {"query": "SYNTHETIC-PRIVATE-DATA"}),
            ("post", "/api/ai/memories/reset/", {"confirm": True}),
            ("get", "/api/ai/document-corpus/", None),
            ("post", "/api/ai/document-corpus/", {"kind": "investment", "document_id": 1,
                "catalog_token": "synthetic", "consent": True, "days": 1}),
            ("post", "/api/ai/document-corpus/search/", {"ids": ["a" * 32], "query": "SYNTHETIC-PRIVATE-DATA"}),
            ("delete", "/api/ai/document-corpus/" + "a" * 32 + "/", {}),
            ("get", "/api/ai/document-corpus/" + "a" * 32 + "/original/", None),
        )
        for method, url, data in requests:
            with self.subTest(url=url, method=method):
                with self.assertLogs("apps.ml_engine.api.memory", level="ERROR") as logs:
                    response = getattr(self.client, method)(url, data=data, content_type="application/json")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response["Cache-Control"], "no-store, private")
                self.assertIn("Existing data is preserved", response.json()["detail"])
                exposed = response.content.decode() + "".join(logs.output)
                self.assertNotIn("SYNTHETIC-PRIVATE-DATA", exposed)
                self.assertNotIn(str(self.vault), exposed)
                self.assertEqual(marker.read_bytes(), b"SYNTHETIC-PRIVATE-DATA")
                self.assertEqual(list(self.vault.iterdir()), [marker])

    def test_authentication_and_csrf_remain_required_when_storage_is_unavailable(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.get("/api/ai/memories/").status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(client.post("/api/ai/memories/reset/", {"confirm": True}, content_type="application/json").status_code, 403)
        self.assertFalse(self.vault.exists())

    def test_document_upload_refuses_unsupported_vault_before_extraction(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        self.client.force_login(self.owner)
        with patch('apps.ml_engine.services.document_corpus.run_bounded_parser') as parser:
            response = self.client.post('/api/ai/document-corpus/upload/',
                dict(file=SimpleUploadedFile('synthetic.pdf',b'%PDF synthetic'),consent='true',days='1'))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        parser.assert_not_called()
        self.assertFalse(self.vault.exists())
