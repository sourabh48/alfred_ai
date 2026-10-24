import builtins
from concurrent.futures import ThreadPoolExecutor
from email.message import EmailMessage
import importlib
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from apps.integrations.services import email_integration as mail
from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service
from apps.ml_engine.api import views


class ExperimentalRetirementTests(SimpleTestCase):
    def test_packaged_module_inventory_has_no_unrouted_experimental_processors(self):
        root = Path(__file__).resolve().parents[1]
        modules = {".".join(p.relative_to(root).with_suffix("").parts)
                   for p in (root / "apps").rglob("*.py") if "__pycache__" not in p.parts}
        self.assertFalse(any(name.startswith("apps.ml_engine.self_improve.") for name in modules))
        self.assertNotIn("apps.ml_engine.services.voice_assistant", modules)
        self.assertIn("apps.ml_engine.services.hybrid_intelligence", modules)
        self.assertIn("apps.ml_engine.training.orchestrator", modules)

    def test_retired_prototype_is_not_a_callable_or_routed_api(self):
        self.assertFalse(hasattr(views, "SelfImproveAPI"))
        with self.assertRaises(Resolver404):
            resolve("/api/ai/self-improve/")

    def test_supported_mail_import_does_not_load_optional_oauth_processors(self):
        original_import = builtins.__import__
        def guarded_import(name, *args, **kwargs):
            if name.split(".")[0] in {"google", "google_auth_oauthlib", "googleapiclient", "msal", "transformers"}:
                raise AssertionError("Unsupported processor import")
            return original_import(name, *args, **kwargs)
        with patch("builtins.__import__", side_effect=guarded_import):
            importlib.reload(mail)
        self.assertTrue(callable(mail.EmailIntegrationService.connect_imap))

    def test_no_plaintext_oauth_setup_or_fake_import_success(self):
        service = mail.EmailIntegrationService()
        for method in ("setup_gmail_oauth", "setup_outlook_oauth", "auto_import_statements"):
            self.assertFalse(hasattr(service, method), method)

    def test_unsupported_attachment_refetch_fails_closed_without_diagnostics(self):
        service = mail.EmailIntegrationService()
        service.imap_connection = Mock()
        with self.assertNoLogs(mail.__name__, level="WARNING"):
            self.assertIsNone(service.download_statement("synthetic-message", 0))
        service.imap_connection.fetch.assert_not_called()

    def test_mail_failures_keep_safe_references_without_credentials_or_document_text(self):
        marker = r"C:\synthetic\statement.pdf token=fake-sensitive-value owner@example.org OCR private text"
        service = mail.EmailIntegrationService()
        connection = Mock()
        connection.login.side_effect = RuntimeError(marker)
        connection.close.side_effect = RuntimeError(marker)
        with patch.object(mail.imaplib, "IMAP4_SSL", return_value=connection), self.assertLogs(mail.__name__, level="ERROR") as logs:
            result = service.connect_imap("owner@example.org", "synthetic-only", "imap.example.org")
        self.assertFalse(result["success"])
        self.assertEqual(len(result["error_id"]), 32)
        self.assertNotIn(marker, str(result) + str(logs.output))
        self.assertTrue(all(record.exception_type == "RuntimeError" and not record.exc_info for record in logs.records))
        connection.logout.assert_called_once()
        self.assertIsNone(service.imap_connection)
        service.imap_connection = Mock()
        service.imap_connection.select.side_effect = RuntimeError(marker)
        with self.assertLogs(mail.__name__, level="ERROR") as logs:
            result = service.scan_financial_emails(SimpleNamespace(id=1))
        self.assertEqual(len(result["error_id"]), 32)
        self.assertNotIn(marker, str(result) + str(logs.output))

    def test_parallel_portfolio_imports_use_separate_mail_connections(self):
        barrier = threading.Barrier(2)
        parsed = {}
        lock = threading.Lock()

        class FakeIMAP:
            def __init__(self, *args, **kwargs):
                self.address = ""
                self.closed = False
            def login(self, address, password):
                self.address = address
                barrier.wait(timeout=5)
            def select(self, folder):
                return "OK", []
            def search(self, *args):
                return "OK", [b"1"]
            def fetch(self, *args):
                message = EmailMessage()
                message["Subject"] = "Portfolio statement"
                message["From"] = "broker@example.org"
                message.set_content("Synthetic fixture")
                message.add_attachment(self.address.encode(), maintype="application", subtype="octet-stream", filename="holdings.csv")
                return "OK", [(b"1 RFC822", message.as_bytes())]
            def close(self):
                self.closed = True
            def logout(self):
                pass

        connections = []
        def imap_factory(*args, **kwargs):
            connection = FakeIMAP()
            connections.append(connection)
            return connection
        def parse(file_obj, *, user, filename):
            with lock:
                parsed[user.id] = file_obj.read()
            return {"success": True, "created": 1, "updated": 0}
        def scan(identity):
            return portfolio_intelligence_service.scrape_email_for_investments(SimpleNamespace(id=identity), {
                "imap_server": "imap.example.org", "email_address": f"owner{identity}@example.org",
                "password": "synthetic-only", "days_back": 7})

        with patch.object(mail.imaplib, "IMAP4_SSL", side_effect=imap_factory), \
             patch.object(portfolio_intelligence_service, "parse_portfolio_pdf", side_effect=parse):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(scan, (1, 2)))
        self.assertEqual(parsed, {1: b"owner1@example.org", 2: b"owner2@example.org"})
        self.assertTrue(all(r["success"] and r["imported"] == 1 for r in results))
        self.assertEqual(len(connections), 2)
        self.assertTrue(all(c.closed for c in connections))
