"""Synthetic PDFs exercise the real extractor, upload transaction and owner API."""
from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from apps.investments.models import Investment, InvestmentDocumentEvidence, InvestmentImportDocument
from apps.investments.services.document_evidence import capture_import, evidence
from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service


ASSET = "Synthetic Reserve Liquid Cash Portfolio Alpha Beta Fund"


def portfolio_pdf(rows):
    import fitz
    with fitz.open() as pdf:
        page = pdf.new_page()
        for index, (account, invested, current) in enumerate(rows):
            page.insert_text((36, 60 + index * 24),
                f"{ASSET} Account: {account} {invested} {current}", fontsize=9)
        return pdf.tobytes()


class InvestmentImportAcceptanceTests(TestCase):
    def setUp(self):
        media = self.enterContext(TemporaryDirectory())
        self.enterContext(override_settings(MEDIA_ROOT=media))
        self.user = get_user_model().objects.create_user(username="synthetic-import-owner")
        self.other = get_user_model().objects.create_user(username="synthetic-import-other")
        self.client.force_login(self.user)
        self.rows = [("SYNTH-A", "100.25", "110.20"), ("SYNTH-B", "200.50", "220.40")]

    def upload(self, rows=None, client=None):
        return (client or self.client).post("/api/investments/import-pdf/", {
            "file": SimpleUploadedFile("synthetic-portfolio.pdf", portfolio_pdf(self.rows if rows is None else rows),
                content_type="application/pdf"),
        })

    def test_equal_holdings_in_different_accounts_are_not_deduplicated(self):
        rows = [("SYNTH-A", "100.25", "110.20"), ("SYNTH-B", "100.25", "110.20")]
        parsed = portfolio_intelligence_service.parse_portfolio_document(
            BytesIO(portfolio_pdf([*rows, rows[0]])), user=self.user, filename="synthetic.pdf")
        self.assertEqual([row["account_number"] for row in parsed["investments"]], ["SYNTH-A", "SYNTH-B"])

    def test_import_reimport_and_receipts_keep_accounts_and_owners_separate(self):
        legacy = Investment.objects.create(user=self.user, asset_name=ASSET, asset_type="cash", current_value="9.99")
        foreign = Investment.objects.create(user=self.other, asset_name=ASSET, asset_type="cash",
            account_number="SYNTH-A", current_value="42.00")
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.content)
        document = InvestmentImportDocument.objects.get(pk=response.json()["upload"]["id"])
        self.assertEqual(document.linked_investments.count(), 2)
        owned = {row.account_number: row for row in document.linked_investments.all()}
        self.assertEqual(set(owned), {"SYNTH-A", "SYNTH-B"})
        for account, invested, current in self.rows:
            row = owned[account]
            self.assertEqual(row.invested_amount, Decimal(invested))
            self.assertEqual(row.current_value, Decimal(current))
            detail = evidence(self.user, document.pk, row.pk)
            self.assertEqual(Decimal(detail["fields"]["current_value"]["original"]), Decimal(current))
            self.assertIsNone(detail["fields"]["current_value"]["currency"])
            self.assertEqual(self.client.get(detail["citation_url"]).status_code, 200)
        for _ in range(2):
            retry = self.upload([("SYNTH-A", "100.25", "120.10")])
            self.assertEqual(retry.status_code, 201, retry.content)
        self.assertEqual(Investment.objects.filter(user=self.user).count(), 3)
        owned["SYNTH-A"].refresh_from_db()
        owned["SYNTH-B"].refresh_from_db()
        legacy.refresh_from_db(); foreign.refresh_from_db()
        self.assertEqual(owned["SYNTH-A"].current_value, Decimal("120.10"))
        self.assertEqual(owned["SYNTH-B"].current_value, Decimal("220.40"))
        self.assertEqual(legacy.current_value, Decimal("9.99"))
        self.assertEqual(foreign.current_value, Decimal("42.00"))
        self.assertEqual(evidence(self.user, document.pk, owned["SYNTH-A"].pk)["fields"]["current_value"]["original"], "110.2")

    def test_receipt_failure_rolls_back_register_and_retry_succeeds(self):
        self.client.raise_request_exception = False
        with patch("apps.investments.services.document_evidence.capture_import", side_effect=RuntimeError("synthetic receipt failure")):
            response = self.upload()
        self.assertEqual(response.status_code, 500)
        self.assertFalse(Investment.objects.filter(user=self.user).exists())
        self.assertFalse(InvestmentImportDocument.objects.filter(user=self.user).exists())
        self.assertFalse(InvestmentDocumentEvidence.objects.exists())
        self.assertEqual(self.upload().status_code, 201)
        self.assertEqual(Investment.objects.filter(user=self.user).count(), 2)

    def test_source_receipts_require_exact_account_identity(self):
        row = Investment.objects.create(user=self.user, asset_name=ASSET, asset_type="cash", account_number="SYNTH-A")
        for account in ("SYNTH-B", None, ["SYNTH-A"], True, ""):
            with self.subTest(account=account):
                document = InvestmentImportDocument.objects.create(user=self.user, file_name="synthetic-receipt.pdf")
                raw = dict(asset_name=ASSET, institution="", account_number=account, current_value="110.20")
                if account == "":
                    raw.pop("account_number")
                capture_import(document, [row], extraction=[raw])
                self.assertEqual(document.field_evidence.get().source_values, {})

    def test_owned_sources_and_csrf_do_not_disclose_or_mutate_foreign_data(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.content)
        document = InvestmentImportDocument.objects.get(pk=response.json()["upload"]["id"])
        row = document.linked_investments.first()
        detail = evidence(self.user, document.pk, row.pk)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(detail["citation_url"]).status_code, 404)
        self.assertEqual(self.client.get("/api/investments/import-uploads/").json(), [])
        self.assertIn(self.client.get(detail["source_download_url"]).status_code, (403, 404))
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.user)
        self.assertEqual(self.upload(client=protected).status_code, 403)
        self.assertEqual(self.upload(client=Client()).status_code, 403)
        self.assertEqual(InvestmentImportDocument.objects.count(), 1)

    def test_corrected_zero_and_decimal_cents_survive_actual_pdf_retry(self):
        response = self.upload(self.rows[:1])
        self.assertEqual(response.status_code, 201, response.content)
        document = InvestmentImportDocument.objects.get(pk=response.json()["upload"]["id"])
        row = document.linked_investments.get()
        original_text = document.extracted_text
        correction = self.client.post("/api/documents/review-queue/resolve/", {
            "scope": "investment_document", "id": document.pk,
            "corrections": {"invested_amount": "2.675", "current_value": "0"},
        }, content_type="application/json")
        self.assertEqual(correction.status_code, 200, correction.content)
        document.refresh_from_db()
        self.assertEqual(document.linked_investments.get().pk, row.pk)
        retry = self.client.post("/api/documents/review-queue/retry/", {
            "scope": "investment_document", "id": document.pk,
        }, content_type="application/json")
        self.assertEqual(retry.status_code, 200, retry.content)
        row.refresh_from_db(); document.refresh_from_db()
        self.assertEqual(row.invested_amount, Decimal("2.68"))
        self.assertEqual(row.current_value, Decimal("0.00"))
        self.assertEqual(document.linked_investments.get().pk, row.pk)
        self.assertEqual(document.extracted_text, original_text)
        self.assertEqual(evidence(self.user, document.pk, row.pk)["fields"]["current_value"]["original"], "110.2")
