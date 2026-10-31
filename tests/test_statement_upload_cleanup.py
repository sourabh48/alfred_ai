"""Only a byte-identical re-upload may replace an earlier unimported statement."""
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from alfred_private_storage import private_directory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from apps.expenses.models import StatementUpload
from apps.expenses.services.statement_import import StatementParseResult
from apps.reports.models import OperationalLog


def parsed(bank_name="", account_number=""):
    return StatementParseResult(
        bank_name=bank_name, account_holder="", account_number=account_number, statement_start=None,
        statement_end=None, transactions=[], statement_kind="other_statement", parser_status="failed",
        confidence=0.08, source_text="", loan_hints={},
    )


class StatementUploadCleanupTests(TestCase):
    def setUp(self):
        media = tempfile.mkdtemp(prefix="alfred-upload-cleanup-")
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        limits = self.enterContext(tempfile.TemporaryDirectory(prefix="alfred-upload-cleanup-limits-"))
        private_directory(limits)
        override = override_settings(MEDIA_ROOT=media, ALFRED_ABUSE_THROTTLE_DIR=limits)
        override.enable()
        self.addCleanup(override.disable)
        self.user = get_user_model().objects.create_user(username="cleanup_owner", password="Pass12345!")

    def upload(self, name, raw, *, user=None, result=None):
        client = Client()
        client.force_login(user or self.user)
        with patch("apps.expenses.views.parse_bank_statement", return_value=result or parsed()):
            response = client.post("/api/expenses/import-statement/", data={
                "statement": SimpleUploadedFile(name, raw, content_type="application/pdf")})
        self.assertEqual(response.status_code, 201)
        return StatementUpload.objects.get(pk=response.json()["upload"]["id"])

    def assert_kept(self, upload):
        upload.refresh_from_db()
        self.assertTrue(Path(upload.original_file.path).exists())

    def test_unrelated_unreadable_uploads_both_survive(self):
        first = self.upload("rent-receipt.pdf", b"%PDF-1.4 synthetic first")
        second = self.upload("insurance-policy.pdf", b"%PDF-1.4 synthetic second")
        self.assert_kept(first)
        self.assert_kept(second)
        self.assertFalse(OperationalLog.objects.filter(event_type="redundant_upload_removed").exists())

    def test_spoofed_metadata_does_not_replace_a_different_file(self):
        result = parsed("HDFC Bank", "50100000000001")
        first = self.upload("genuine.pdf", b"%PDF-1.4 synthetic genuine", result=result)
        self.upload("spoof.pdf", b"%PDF-1.4 synthetic spoof", result=result)
        self.assert_kept(first)

    def test_identical_reupload_replaces_the_earlier_one_and_is_logged(self):
        first = self.upload("statement.pdf", b"%PDF-1.4 synthetic same")
        first_id, first_path = first.id, first.original_file.path
        second = self.upload("statement-again.pdf", b"%PDF-1.4 synthetic same")
        self.assertFalse(StatementUpload.objects.filter(pk=first_id).exists())
        self.assertFalse(Path(first_path).exists())
        log = OperationalLog.objects.get(event_type="redundant_upload_removed")
        self.assertEqual(log.document_id, second.id)
        self.assertEqual(log.payload["removed_upload_id"], first_id)

    def test_identical_file_of_another_owner_is_untouched(self):
        other = get_user_model().objects.create_user(username="cleanup_other", password="Pass12345!")
        theirs = self.upload("statement.pdf", b"%PDF-1.4 synthetic same", user=other)
        self.upload("statement.pdf", b"%PDF-1.4 synthetic same")
        self.assert_kept(theirs)

    def test_earlier_upload_without_its_file_is_not_treated_as_identical(self):
        kept = StatementUpload.objects.create(user=self.user, source="other_statement", file_name="purged.pdf",
                                              parser_status="failed", parse_confidence=0.08)
        self.upload("statement.pdf", b"%PDF-1.4 synthetic same")
        self.assertTrue(StatementUpload.objects.filter(pk=kept.pk).exists())
