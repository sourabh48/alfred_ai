from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, TransactionTestCase, override_settings

from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord
from apps.mobility.services.bike_document_ai import ParsedDocument


def synthetic_service_pdf():
    import fitz
    lines=["SYNTHETIC TEST DOCUMENT - NOT A REAL INVOICE", "Service Invoice", "Service Center: Synthetic Workshop",
        "Invoice No: SYN-BROWSER-001", "Invoice Date: 31/03/2026", "Vehicle Number: KA05MN4321",
        "Royal Enfield Hunter 350", "Odometer: 26021 KM", "Work Done: Routine service and chain inspection", "Grand Total: 2.68"]
    with fitz.open() as pdf:
        page=pdf.new_page(); page.insert_text((40,40),"\n".join(lines))
        return pdf.tobytes()


class ServiceImportReceiptTests(TestCase):
    def setUp(self):
        self.media = Path(self.enterContext(TemporaryDirectory(prefix="alfred-invoice-test-")))
        self.enterContext(override_settings(MEDIA_ROOT=str(self.media), ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=True))
        self.owner = get_user_model().objects.create_user(username="invoice_receipt_owner")
        self.other = get_user_model().objects.create_user(username="invoice_receipt_private")
        self.profile = BikeProfile.objects.create(user=self.owner, display_name="Synthetic Scooter", vehicle_number="KA05MN4321")
        self.parsed = ParsedDocument(document_type="invoice", title="Synthetic invoice", confidence=0.85,
            fields={"document_number":"SYN-INV-01", "issuer":"Synthetic Workshop", "vehicle_number":"KA05MN4321"},
            parser_status="parsed", parser_notes="Synthetic test evidence", source_text="SYNTHETIC Scooter KA05MN4321 Service Invoice",
            service_payload={"service_date":"2026-03-31", "cost":"2432.925", "odometer_km":26021, "service_type":"routine", "service_center":"Synthetic Workshop"})
        self.parser = self.enterContext(patch("apps.mobility.views.bike_document_ai.parse", side_effect=lambda *a,**k:deepcopy(self.parsed)))
        self.client.force_login(self.owner)

    def upload(self, content=b"%PDF-1.4 synthetic invoice", name="synthetic-invoice.pdf", profile=None):
        return self.client.post("/api/mobility/bike-services/import/", {
            "bike_profile_id":profile or self.profile.pk,
            "service_file":SimpleUploadedFile(name,content,content_type="application/pdf"),
        })

    def test_byte_replay_renamed_file_keeps_reviewed_cents_and_source(self):
        first = self.upload()
        self.assertEqual(first.status_code,201)
        document=BikeDocument.objects.get(user=self.owner)
        record=BikeServiceRecord.objects.get(user=self.owner)
        self.assertEqual(record.cost,Decimal("2432.93"))
        correction=self.client.post("/api/documents/review-queue/resolve/", {
            "scope":"vehicle_document", "id":document.pk, "corrections":{"cost":"2000.01", "service_center":"Owner corrected"},
        },content_type="application/json")
        self.assertEqual(correction.status_code,200)
        document.refresh_from_db(); record.refresh_from_db()
        before=(document.source_text,deepcopy(document.extracted_payload),record.cost,record.service_center)
        replay=self.upload(name="renamed-synthetic.pdf")
        self.assertEqual(replay.status_code,200)
        self.assertTrue(replay.json()["duplicate"])
        self.assertEqual(replay.json()["service_record"]["id"],record.pk)
        self.assertEqual(replay.json()["service_record"]["cost"],2000.01)
        document.refresh_from_db(); record.refresh_from_db()
        self.assertEqual(before,(document.source_text,document.extracted_payload,record.cost,record.service_center))
        self.assertEqual(BikeDocument.objects.count(),1)
        self.assertEqual(BikeServiceRecord.objects.count(),1)

    def test_same_invoice_identity_with_changed_bytes_requires_review(self):
        self.assertEqual(self.upload().status_code,201)
        response=self.upload(content=b"%PDF-1.4 different synthetic scan")
        self.assertEqual(response.status_code,409)
        self.parsed.fields["vehicle_number"]="KA-05 MN-4321"
        self.assertEqual(self.upload(content=b"%PDF-1.4 reformatted synthetic scan").status_code,409)
        self.assertEqual(BikeDocument.objects.count(),1)
        self.assertEqual(BikeServiceRecord.objects.count(),1)

    def test_foreign_profile_denied_before_parser_and_owner_replay_is_isolated(self):
        foreign=BikeProfile.objects.create(user=self.other,display_name="Private",vehicle_number="KA05MN4321")
        self.assertEqual(self.upload(profile=foreign.pk).status_code,400)
        self.parser.assert_not_called()
        self.assertEqual(self.upload().status_code,201)
        self.client.force_login(self.other)
        response=self.upload(profile=foreign.pk)
        self.assertEqual(response.status_code,201)
        self.assertNotEqual(response.json()["document"]["id"],BikeDocument.objects.get(user=self.owner).pk)
        self.assertEqual(BikeServiceRecord.objects.count(),2)

    def test_invalid_extraction_and_failed_posting_leave_no_document_or_file(self):
        self.parsed.service_payload["cost"]="NaN"
        response=self.upload()
        self.assertEqual(response.status_code,400)
        self.assertFalse(BikeDocument.objects.exists())
        self.assertFalse(BikeServiceRecord.objects.exists())
        self.assertFalse([p for p in self.media.rglob("*") if p.is_file()])
        self.parsed.service_payload["cost"]="2.68"
        with override_settings(ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=False), patch("apps.mobility.models.BikeServiceRecord.save", side_effect=RuntimeError("synthetic save failure")):
            self.assertEqual(self.upload().status_code,500)
        self.assertFalse(BikeDocument.objects.exists())
        self.assertFalse([p for p in self.media.rglob("*") if p.is_file()])

    def test_deleted_log_is_not_silently_reposted_and_source_cannot_be_replaced(self):
        self.assertEqual(self.upload().status_code,201)
        document=BikeDocument.objects.get(user=self.owner)
        from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
        response=self.client.patch(f"/api/mobility/bike-documents/{document.pk}/", {
            "notes":"unchanged",
        },content_type="application/json")
        self.assertEqual(response.status_code,200)
        response=self.client.patch(f"/api/mobility/bike-documents/{document.pk}/", encode_multipart(BOUNDARY,{
            "document_file":SimpleUploadedFile("replacement.pdf",b"%PDF-1.4 replaced",content_type="application/pdf"),
        }),content_type=MULTIPART_CONTENT)
        self.assertEqual(response.status_code,400)
        BikeServiceRecord.objects.get(user=self.owner).delete()
        self.assertEqual(self.upload().status_code,409)
        self.assertFalse(BikeServiceRecord.objects.exists())

    def test_vehicle_edit_during_extraction_abstains_without_losing_owner_edit(self):
        def changed_profile(*args,**kwargs):
            profile=BikeProfile.objects.get(pk=self.profile.pk)
            profile.display_name="Owner renamed vehicle"
            profile.save()
            return deepcopy(self.parsed)
        self.parser.side_effect=changed_profile
        self.assertEqual(self.upload().status_code,409)
        self.assertFalse(BikeDocument.objects.exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.display_name,"Owner renamed vehicle")

    def test_recorded_legacy_invoice_identity_requires_review_without_backfill(self):
        document=BikeDocument.objects.create(user=self.owner,bike_profile=self.profile,bike_name=self.profile.display_name,
            document_type="invoice",document_number="SYN-INV-01",issuer="Synthetic Workshop",issue_date="2026-03-31")
        self.assertEqual(self.upload().status_code,409)
        document.refresh_from_db()
        self.assertEqual(document.extracted_payload,{})
        self.assertFalse(BikeServiceRecord.objects.exists())

    def test_real_pdf_keeps_absent_next_checkpoint_distinct_from_an_odometer(self):
        from apps.mobility.services.bike_document_ai import BikeDocumentAI
        with patch("apps.mobility.views.bike_document_ai.parse",wraps=BikeDocumentAI().parse):
            response=self.upload(content=synthetic_service_pdf())
        self.assertEqual(response.status_code,201,response.json())
        record=BikeServiceRecord.objects.get(user=self.owner)
        self.assertEqual(record.cost,Decimal("2.68"))
        self.assertEqual(record.odometer_km,26021)
        self.assertIsNone(record.next_service_km)


class ServiceImportConcurrencyTests(TransactionTestCase):
    def setUp(self):
        # Reuse the isolated upload fixture without TestCase's outer database transaction.
        ServiceImportReceiptTests.setUp(self)

    def test_simultaneous_imports_post_one_log_and_can_replay_after_conflict(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        from rest_framework.test import APIRequestFactory, force_authenticate
        from apps.mobility.views import BikeServiceImportView
        barrier=Barrier(2)
        def parse(*args,**kwargs):
            barrier.wait(timeout=15)
            return deepcopy(self.parsed)
        self.parser.side_effect=parse
        def send():
            close_old_connections()
            try:
                request=APIRequestFactory().post("/api/mobility/bike-services/import/", {
                    "bike_profile_id":self.profile.pk,
                    "service_file":SimpleUploadedFile("same.pdf",b"%PDF-1.4 same concurrent source",content_type="application/pdf"),
                },format="multipart")
                force_authenticate(request,self.owner)
                return BikeServiceImportView.as_view()(request).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(lambda _:send(),range(2)))
        self.assertEqual(statuses.count(201),1,statuses)
        self.assertTrue(all(code in (200,201,409) for code in statuses),statuses)
        self.assertEqual(BikeDocument.objects.count(),1)
        self.assertEqual(BikeServiceRecord.objects.count(),1)
        self.parser.side_effect=lambda *args,**kwargs:deepcopy(self.parsed)
        response=self.upload(b"%PDF-1.4 same concurrent source")
        self.assertEqual(response.status_code,200)

    upload=ServiceImportReceiptTests.upload
