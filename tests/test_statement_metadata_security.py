"""SEC-01: statement metadata comes from untrusted documents and must stay inert."""
from io import BytesIO
from unittest.mock import patch

import fitz
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.expenses.models import BankAccount, StatementUpload
from apps.expenses.services.statement_import import (
    clean_statement_file_name,
    clean_statement_text,
    parse_bank_statement,
)

# Numeric entities survive the parser's upper/title casing, as a real attacker's would.
ENTITY_PAYLOAD = "".join(f"&#{ord(char)};" for char in "window.__alfredXss=1")
HOSTILE_LINE = f"MR <IMG SRC=X ONERROR={ENTITY_PAYLOAD}>"
HOSTILE_FILE_NAME = "<img src=x onerror=alert(1)>.pdf"
QUOTAS = dict(ALFRED_API_ACCOUNT_LIMIT=10 ** 6, ALFRED_API_GLOBAL_LIMIT=10 ** 6,
              ALFRED_EXPENSIVE_ACCOUNT_LIMIT=10 ** 6, ALFRED_EXPENSIVE_GLOBAL_LIMIT=10 ** 6)


def statement_pdf(*lines):
    with fitz.open() as document:
        page = document.new_page(width=1400)
        for index, line in enumerate(lines):
            page.insert_text((20, 60 + index * 20), line, fontsize=7)
        return document.tobytes()


class StatementTextCleaningTests(SimpleTestCase):
    def test_markup_is_rejected_and_legitimate_names_are_preserved(self):
        for hostile in ("<B>Evil", "<Img Src=X Onerror=&#119;>", "Name`x`", 'Na"me', "a>b"):
            self.assertEqual(clean_statement_text(hostile), "")
        for legitimate in ("Rahul O'Brien", "Anne-Marie D'Souza", "A&B Traders", "M/S Kumar & Sons",
                           "Dr. S. Rao", "राहुल शर्मा", "José Núñez", "HDFC Bank", ""):
            self.assertEqual(clean_statement_text(legitimate), legitimate)

    def test_file_names_keep_legitimate_characters_and_lose_markup(self):
        self.assertEqual(clean_statement_file_name("Rahul & Sons (Jan 2026) #2.pdf"), "Rahul & Sons (Jan 2026) #2.pdf")
        self.assertEqual(clean_statement_file_name("O'Brien statement.pdf"), "O'Brien statement.pdf")
        cleaned = clean_statement_file_name(HOSTILE_FILE_NAME)
        self.assertNotRegex(cleaned, r'[<>"`]')
        self.assertTrue(cleaned.endswith(".pdf"))
        self.assertEqual(clean_statement_file_name('<>"`'), "statement.pdf")

    def parsed_holder(self, line):
        raw = statement_pdf("HDFC BANK", line, "Account Number: 123456789012")
        with patch("apps.expenses.services.statement_import.apply_parser_learning", return_value=(0.5, [])):
            return parse_bank_statement(BytesIO(raw)).account_holder

    def test_parser_rejects_hostile_holder_and_keeps_real_holders(self):
        self.assertEqual(self.parsed_holder(HOSTILE_LINE), "")
        self.assertEqual(self.parsed_holder("MR <B>EVIL"), "")
        self.assertEqual(self.parsed_holder("MR RAHUL KUMAR"), "Rahul Kumar")
        self.assertEqual(self.parsed_holder("MS ANNE-MARIE D'SOUZA"), "Anne-Marie D'Souza")


@override_settings(**QUOTAS)
class StatementImportSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("sec01_owner", password="Synthetic-Pass-1")
        self.client_api = APIClient()
        self.client_api.force_login(self.user)

    def upload(self, name="statement.pdf", lines=None, client=None, **data):
        raw = statement_pdf(*(lines or ("HDFC BANK", "MR RAHUL KUMAR", "Account Number: 123456789012")))
        payload = {"statement": SimpleUploadedFile(name, raw, content_type="application/pdf"), **data}
        return (client or self.client_api).post("/api/expenses/import-statement/", payload, format="multipart")

    def test_hostile_pdf_and_file_name_are_stored_without_markup(self):
        response = self.upload(HOSTILE_FILE_NAME, ("HDFC BANK", HOSTILE_LINE, "Account Number: 123456789012"))
        self.assertEqual(response.status_code, 201, response.content)
        row = StatementUpload.objects.get(user=self.user)
        self.assertEqual(row.account_holder, "")
        self.assertNotRegex(row.file_name, r'[<>"`]')
        self.assertEqual(row.bank_name, "HDFC Bank")
        self.assertFalse(BankAccount.objects.filter(user=self.user, account_holder__contains="<").exists())
        # The retained raw text excerpt is evidence and stays verbatim; its renderers escape it.
        listed = self.client_api.get("/api/expenses/uploads/").json()
        listed = listed["results"] if isinstance(listed, dict) else listed
        for field in ("file_name", "account_holder", "bank_name", "institution_name", "account_number", "source"):
            self.assertNotRegex(str(listed[0][field]), r'[<>"`]', field)

    def test_retry_path_and_saved_corrections_cannot_restore_markup(self):
        from apps.expenses.services.statement_lifecycle import _apply_saved_corrections, apply_parsed_statement_upload
        raw = statement_pdf("HDFC BANK", "MR RAHUL KUMAR", "Account Number: 123456789012")
        parsed = parse_bank_statement(BytesIO(raw), user=self.user)
        _apply_saved_corrections(parsed, {"accepted_corrections": {
            "account_holder": "<b>x", "bank_name": "<b>x", "account_number": "<b>x", "statement_kind": "<b>x"}})
        self.assertEqual((parsed.account_holder, parsed.bank_name, parsed.account_number),
                         ("Rahul Kumar", "HDFC Bank", "123456789012"))
        self.assertNotIn("<", parsed.statement_kind)
        _apply_saved_corrections(parsed, {"accepted_corrections": {"account_holder": "Anne-Marie D'Souza"}})
        self.assertEqual(parsed.account_holder, "Anne-Marie D'Souza")

        parsed.bank_name = "<svg onload=alert(1)>"
        parsed.account_holder = "<svg onload=alert(1)>"
        result = apply_parsed_statement_upload(
            user=self.user, parsed=parsed, statement_kind="bank_statement",
            statement_file=SimpleUploadedFile("statement.pdf", raw, content_type="application/pdf"))
        self.assertEqual((result.upload.bank_name, result.upload.account_holder, result.upload.institution_name), ("", "", ""))
        self.assertEqual(result.upload.account_number, "123456789012")

    def test_legitimate_statement_metadata_is_unchanged(self):
        response = self.upload("Rahul & Sons (Jan 2026).pdf")
        self.assertEqual(response.status_code, 201, response.content)
        row = StatementUpload.objects.get(user=self.user)
        self.assertEqual(row.file_name, "Rahul & Sons (Jan 2026).pdf")
        self.assertEqual(row.account_holder, "Rahul Kumar")
        self.assertEqual(row.account_number, "123456789012")

    def test_client_statement_kind_must_be_a_known_choice(self):
        response = self.upload(statement_kind="<svg onload=alert(1)>")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(StatementUpload.objects.filter(user=self.user).exists())
        response = self.upload(statement_kind="credit_card_statement")
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(StatementUpload.objects.get(user=self.user).source, "credit_card_statement")

    def test_pages_and_apis_carry_the_content_security_policy(self):
        for path in ("/expenses/", "/login/", "/api/expenses/uploads/", "/health/live/"):
            with self.subTest(path=path):
                response = self.client_api.get(path)
                enforced = response.headers["Content-Security-Policy"]
                for directive in ("default-src 'self'", "connect-src 'self'", "object-src 'none'", "base-uri 'self'",
                                  "form-action 'self'", "frame-ancestors 'none'"):
                    self.assertIn(directive, enforced)
                self.assertNotIn("img-src *", enforced)
                self.assertIn("https://tile.openstreetmap.org", enforced)
                report_only = response.headers["Content-Security-Policy-Report-Only"]
                self.assertRegex(report_only, r"script-src 'self'(;|$)")

    def test_review_correction_rejects_markup_and_keeps_real_values(self):
        from alfred_ai.services.document_review import apply_correction
        self.upload()
        row = StatementUpload.objects.get(user=self.user)
        for corrections in ({"account_holder": "<svg onload=alert(1)>"}, {"bank_name": "<b>x</b>"},
                            {"statement_kind": "<svg onload=alert(1)>"}):
            with self.assertRaises(ValueError):
                apply_correction(self.user, scope="statement_document", document_id=row.pk, corrections=corrections)
        row.refresh_from_db()
        self.assertEqual(row.account_holder, "Rahul Kumar")
        self.assertNotIn("<", str(row.extracted_payload))
        apply_correction(self.user, scope="statement_document", document_id=row.pk,
                         corrections={"account_holder": "Anne-Marie D'Souza", "bank_name": "HDFC Bank"})
        row.refresh_from_db()
        self.assertEqual(row.account_holder, "Anne-Marie D'Souza")
        self.assertEqual(row.bank_name, "HDFC Bank")

    def test_owner_isolation_and_csrf_still_apply(self):
        self.upload("private-owner.pdf")
        row = StatementUpload.objects.get(user=self.user)
        other = APIClient()
        other.force_login(get_user_model().objects.create_user("sec01_other", password="Synthetic-Pass-2"))
        self.assertEqual(other.get(f"/api/expenses/uploads/{row.pk}/").status_code, 404)
        self.assertNotIn("private-owner", other.get("/api/expenses/uploads/").content.decode())

        enforcing = Client(enforce_csrf_checks=True)
        enforcing.force_login(self.user)
        raw = statement_pdf("HDFC BANK", "MR RAHUL KUMAR")
        denied = enforcing.post("/api/expenses/import-statement/",
                                {"statement": SimpleUploadedFile("x.pdf", raw, content_type="application/pdf")})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(StatementUpload.objects.filter(user=self.user).count(), 1)
