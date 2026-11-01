"""BIKE-01 profile/catalog identity and BIKE-04 document/invoice review. Synthetic data only."""
from copy import deepcopy
from datetime import date
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from alfred_private_storage import private_directory
from apps.expenses.services.financial_intelligence import _build_vehicle_positions
from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord
from apps.mobility.services.bike_catalog import _catalog_items, best_catalog_match, build_profile_payload, catalog_coverage_summary
from apps.mobility.services.bike_document_ai import BikeDocumentAI, ParsedDocument


def parse_text(text, name="synthetic.pdf"):
    upload = BytesIO(b"synthetic")
    upload.name = name
    with patch.object(BikeDocumentAI, "_extract_text", return_value=text):
        return BikeDocumentAI().parse(upload, name)


COMPLETE_INVOICE = """
Service Invoice
Invoice No: SYN-100
Registration No: KA05MN4321
Service Center: Synthetic Workshop
Invoice Date: 31/03/2026
Odometer: 26021 km
Parts Description
Code Description Qty Customer Amount
BPK001 BRAKE PAD KIT 1 Rs 300.00
Total 300.00 300.00
Labour Description
Code Description Hrs Customer Amount
LAB001 PERIODIC SERVICE LABOUR 1 Rs 200.00
Total 200.00 200.00
{total}
""".strip()


class InvoiceExtractionReviewTests(SimpleTestCase):
    def test_labelled_grand_total_beats_an_earlier_rupee_amount(self):
        parsed = parse_text(COMPLETE_INVOICE.format(total="Grand Total: 500.00"))
        self.assertEqual(parsed.service_payload["cost"], 500.0)
        self.assertEqual(parsed.parser_status, "parsed", parsed.parser_notes)

    def test_payable_label_is_read_as_the_invoice_total(self):
        parsed = parse_text(COMPLETE_INVOICE.format(total="Amount Payable: Rs 500.00"))
        self.assertEqual(parsed.service_payload["cost"], 500.0)

    def test_missing_total_is_not_guessed_from_a_line_or_subtotal_amount(self):
        parsed = parse_text("""
Service Invoice
Invoice No: SYN-101
Registration No: KA05MN4321
Invoice Date: 31/03/2026
Brake pad kit fitted at Rs 300.00
""".strip())
        self.assertFalse(parsed.service_payload.get("cost"))
        self.assertEqual(parsed.parser_status, "needs_review")
        self.assertIn("total", parsed.parser_notes.lower())

    def test_total_that_disagrees_with_its_sections_needs_review(self):
        parsed = parse_text(COMPLETE_INVOICE.format(total="Grand Total: 5000.00"))
        self.assertEqual(parsed.parser_status, "needs_review")
        self.assertIn("does not match", parsed.parser_notes)

    def test_subtotal_read_as_cost_needs_review(self):
        parsed = parse_text(COMPLETE_INVOICE.format(total="Please pay the workshop"))
        self.assertEqual(parsed.parser_status, "needs_review", parsed.service_payload.get("cost"))

    def test_invoice_without_date_or_vehicle_needs_review(self):
        parsed = parse_text("Service Invoice\nInvoice No: SYN-102\nService Center: Synthetic Workshop\nGrand Total: 500.00")
        self.assertEqual(parsed.parser_status, "needs_review")
        self.assertIn("vehicle number", parsed.parser_notes)
        self.assertIn("service date", parsed.parser_notes)

    def test_next_service_date_is_not_read_as_the_service_date(self):
        parsed = parse_text("""
Service Invoice
Invoice No: SYN-103
Registration No: KA05MN4321
Next Service Date: 30/09/2026
Grand Total: 500.00
""".strip())
        self.assertEqual(parsed.service_payload.get("next_service_date"), "2026-09-30")
        self.assertFalse(parsed.service_payload.get("service_date"))
        self.assertEqual(parsed.parser_status, "needs_review")


class InsuranceExtractionTests(SimpleTestCase):
    HEADER = "Motor Insurance Policy\nPolicy No: SYN/POL/1\nRegistration No: KA05MN4321\nSynthetic Insurance Company\n"

    def test_declared_value_is_not_read_as_a_premium(self):
        parsed = parse_text(self.HEADER + "Insured Declared Value: Rs 120000")
        self.assertEqual(parsed.document_type, "insurance")
        self.assertFalse(parsed.fields.get("amount"))

    def test_total_premium_payable_is_read(self):
        parsed = parse_text(self.HEADER + "Insured Declared Value: Rs 120000\nTotal Premium Payable: Rs 2,345.50")
        self.assertEqual(parsed.fields["amount"], 2345.5)

    def test_policy_period_end_is_the_expiry_not_the_start(self):
        for line in ("Policy Period: 01/04/2026 to 31/03/2027", "Period of Insurance: From 01-Apr-2026 To 31-Mar-2027"):
            with self.subTest(line=line):
                self.assertEqual(parse_text(self.HEADER + line).fields["expiry_date"], "2027-03-31")

    def test_labelled_expiry_layouts_are_read(self):
        for line in ("Policy Expiry Date: 31/03/2027", "Date of Expiry: 31-Mar-2027", "Valid Until: 31 March 2027", "Policy End Date: 31-03-2027"):
            with self.subTest(line=line):
                self.assertEqual(parse_text(self.HEADER + line).fields["expiry_date"], "2027-03-31")

    def test_expiry_date_is_not_read_as_the_issue_date(self):
        fields = parse_text(self.HEADER + "Policy End Date: 31/03/2027").fields
        self.assertEqual(fields["expiry_date"], "2027-03-31")
        self.assertNotIn("issue_date", fields)
        fields = parse_text(self.HEADER + "Date: 01/04/2026\nPolicy End Date: 31/03/2027").fields
        self.assertEqual(fields["issue_date"], "2026-04-01")


class RelevanceEvidenceTests(SimpleTestCase):
    def parsed(self, number="KA05MN4321", text="Service Invoice job card"):
        return SimpleNamespace(source_text=text, confidence=0.7, document_type="invoice", fields={"vehicle_number": number}, service_payload={"cost": 1})

    def test_profile_without_a_number_does_not_claim_a_number_match(self):
        result = BikeDocumentAI().verify_relevance(SimpleNamespace(vehicle_number="", display_name="X"), self.parsed())
        self.assertFalse(any("matched" in reason for reason in result["reasons"]))
        self.assertEqual(result["score"], 0.7)

    def test_conflicting_number_is_rejected_whatever_its_format(self):
        result = BikeDocumentAI().verify_relevance(SimpleNamespace(vehicle_number="KA-05 MN 9999"), self.parsed())
        self.assertFalse(result["accepted"])
        self.assertTrue(BikeDocumentAI().verify_relevance(SimpleNamespace(vehicle_number="ka-05 mn 4321"), self.parsed())["accepted"])

    def test_vehicle_cues_need_whole_words(self):
        car = SimpleNamespace(vehicle_number="", make="", model_name="", display_name="", vehicle_type="car")
        result = BikeDocumentAI().verify_relevance(car, self.parsed(number=""))
        self.assertFalse(any("cues" in reason for reason in result["reasons"]))
        other = SimpleNamespace(vehicle_number="", vehicle_type="other")
        self.assertFalse(any("cues" in reason for reason in BikeDocumentAI().verify_relevance(other, self.parsed(number="", text="other charges"))["reasons"]))

    def test_document_without_a_number_says_it_was_not_compared(self):
        result = BikeDocumentAI().verify_relevance(SimpleNamespace(vehicle_number="KA05MN4321"), self.parsed(number=""))
        self.assertTrue(any("not compared" in reason for reason in result["reasons"]))


class CatalogIdentityTests(SimpleTestCase):
    def test_hunter_350_names_resolve_to_the_hunter_entry(self):
        for name in ("Hunter 350", "Royal Enfield Hunter 350", "royal-enfield hunter 350", "RE Hunter", "HUNTER 350 DAPPER GREEN", "Hunter 350 Metro Rebel"):
            with self.subTest(name=name):
                payload = build_profile_payload(name, make="" if "enfield" in name.lower() else "Royal Enfield")
                self.assertEqual(payload["catalog_key"], "royal-enfield-hunter-350")
                self.assertEqual(payload["official_source_name"], "Royal Enfield")

    def test_a_different_model_never_borrows_the_hunter_specs(self):
        for name in ("Royal Enfield Hunter 450", "Royal Enfield Scram 411", "Royal Enfield Shotgun 650", "Royal Enfield"):
            with self.subTest(name=name):
                payload = build_profile_payload(name)
                self.assertEqual(payload["catalog_key"], "")
                self.assertEqual(payload["verification_status"], "custom")
                self.assertEqual(payload["official_source_url"], "")
        self.assertEqual(build_profile_payload("Royal Enfield Bullet 350")["catalog_key"], "royal-enfield-bullet-350")

    def test_every_catalog_entry_still_finds_itself(self):
        for item in _catalog_items():
            for name in (item["display_name"], item["model_name"]):
                with self.subTest(name=name):
                    match, score = best_catalog_match(name)
                    self.assertGreaterEqual(score, 0.92)
                    self.assertEqual(match["model_name"], item["model_name"])

    def test_model_year_does_not_block_a_match(self):
        self.assertEqual(build_profile_payload("Royal Enfield Hunter 350 2024")["catalog_key"], "royal-enfield-hunter-350")

    def test_coverage_reports_source_age_without_claiming_fresh(self):
        with patch("apps.mobility.services.bike_catalog.timezone.localdate", return_value=date(2026, 11, 2)):
            refresh = catalog_coverage_summary()["source_refresh"]
        self.assertEqual(refresh["age_days"], 94)
        self.assertTrue(refresh["stale"])
        with patch("apps.mobility.services.bike_catalog.timezone.localdate", return_value=date(2026, 8, 1)):
            self.assertFalse(catalog_coverage_summary()["source_refresh"]["stale"])


class ProfileIdentityApiTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="bike01_owner")
        self.other = get_user_model().objects.create_user(username="bike01_other")
        self.client.force_login(self.owner)

    def send(self, method, url, body):
        return getattr(self.client, method)(url, data=json.dumps(body), content_type="application/json")

    def create(self, **body):
        response = self.send("post", "/api/mobility/bikes/", {"vehicle_type": "motorcycle", "make": "Royal Enfield", "model_name": "Hunter 350",
            "display_name": "Hunter 350", "vehicle_number": "KA05MN4321", **body})
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()

    def test_nickname_keeps_the_catalog_match_for_the_model(self):
        payload = self.create(display_name="Daily Ride")
        self.assertEqual(payload["display_name"], "Daily Ride")
        self.assertEqual(payload["catalog_key"], "royal-enfield-hunter-350")
        self.assertEqual(payload["verification_status"], "official")
        self.assertEqual(payload["fuel_tank_capacity_l"], 13.0)

    def test_later_edit_keeps_earlier_owner_values(self):
        url = f"/api/mobility/bikes/{self.create()['id']}/"
        self.assertEqual(self.send("patch", url, {"display_name": "Daily Ride", "service_interval_km": 6200, "fuel_tank_capacity_l": 12.5, "variant": "Dapper"}).status_code, 200)
        response = self.send("patch", url, {"vehicle_number": "KA05MN9999"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["vehicle_number"], "KA05MN9999")
        self.assertEqual(payload["display_name"], "Daily Ride")
        self.assertEqual(payload["service_interval_km"], 6200)
        self.assertEqual(payload["fuel_tank_capacity_l"], 12.5)
        self.assertEqual(payload["variant"], "Dapper")
        self.assertEqual(payload["catalog_key"], "royal-enfield-hunter-350")

    def test_changing_the_model_refreshes_catalog_specs_except_values_sent_with_it(self):
        url = f"/api/mobility/bikes/{self.create()['id']}/"
        payload = self.send("patch", url, {"model_name": "Meteor 350", "display_name": "Meteor 350", "service_interval_km": 7000}).json()
        self.assertEqual(payload["catalog_key"], "royal-enfield-meteor-350")
        self.assertEqual(payload["fuel_tank_capacity_l"], 15.0)
        self.assertEqual(payload["service_interval_km"], 7000)

    def test_changing_to_an_unknown_model_drops_the_official_claim(self):
        url = f"/api/mobility/bikes/{self.create()['id']}/"
        payload = self.send("patch", url, {"model_name": "Hunter 450", "display_name": "Hunter 450"}).json()
        self.assertEqual(payload["catalog_key"], "")
        self.assertEqual(payload["verification_status"], "custom")
        self.assertEqual(payload["official_source_url"], "")

    def test_client_cannot_claim_official_verification_or_edit_foreign_profile(self):
        payload = self.create(display_name="Unknown Machine", model_name="Unknown Machine", make="Nobody", verification_status="official", catalog_key="royal-enfield-hunter-350")
        self.assertEqual(payload["verification_status"], "custom")
        self.assertEqual(payload["catalog_key"], "")
        foreign = BikeProfile.objects.create(user=self.other, display_name="Foreign", model_name="Foreign")
        self.assertEqual(self.send("patch", f"/api/mobility/bikes/{foreign.pk}/", {"display_name": "Taken"}).status_code, 404)

    def test_primary_moves_to_one_vehicle(self):
        first = self.create()
        second = self.create(model_name="Meteor 350", display_name="Meteor 350", is_primary=True)
        self.assertEqual(list(BikeProfile.objects.filter(user=self.owner, is_primary=True).values_list("pk", flat=True)), [second["id"]])
        self.send("patch", f"/api/mobility/bikes/{first['id']}/", {"is_primary": True})
        self.assertEqual(list(BikeProfile.objects.filter(user=self.owner, is_primary=True).values_list("pk", flat=True)), [first["id"]])


class InvoiceReviewMoneyTests(TestCase):
    def setUp(self):
        self.media = Path(self.enterContext(TemporaryDirectory(prefix="alfred-bike-test-")))
        limits = self.enterContext(TemporaryDirectory(prefix="alfred-bike-limits-"))
        private_directory(limits)
        self.enterContext(override_settings(MEDIA_ROOT=str(self.media), ALFRED_ABUSE_THROTTLE_DIR=limits,
            ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=False))
        self.owner = get_user_model().objects.create_user(username="bike04_owner")
        self.profile = BikeProfile.objects.create(user=self.owner, display_name="Synthetic Bike", model_name="Synthetic Bike", vehicle_number="KA05MN4321")
        self.parsed = ParsedDocument(document_type="invoice", title="Synthetic invoice", confidence=0.85,
            fields={"document_number": "SYN-INV-9", "issuer": "Synthetic Workshop", "vehicle_number": "KA05MN4321"},
            parser_status="parsed", parser_notes="Synthetic", source_text="Synthetic Bike KA05MN4321 Service Invoice",
            service_payload={"service_date": "2026-03-31", "cost": 1234.56, "odometer_km": 26021, "service_type": "routine", "service_center": "Synthetic Workshop"})
        self.enterContext(patch("apps.mobility.views.bike_document_ai.parse", side_effect=lambda *a, **k: deepcopy(self.parsed)))
        self.retry_parse = self.enterContext(patch("alfred_ai.services.document_review.bike_document_ai.parse", side_effect=lambda *a, **k: deepcopy(self.parsed)))
        self.client.force_login(self.owner)

    def upload(self):
        return self.client.post("/api/mobility/bike-services/import/", {"bike_profile_id": self.profile.pk,
            "service_file": SimpleUploadedFile("synthetic.pdf", b"%PDF-1.4 synthetic", content_type="application/pdf")})

    def post_review(self, action, **body):
        document = BikeDocument.objects.get(user=self.owner)
        return self.client.post(f"/api/documents/review-queue/{action}/", data=json.dumps({"scope": "vehicle_document", "id": document.pk, **body}), content_type="application/json")

    def state(self):
        record = BikeServiceRecord.objects.get(user=self.owner)
        return record, BikeDocument.objects.get(user=self.owner)

    def hold(self):
        self.parsed.parser_status = "needs_review"
        self.parsed.confidence = 0.55
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.content)
        return response

    def test_trusted_invoice_posts_exact_decimal_cost(self):
        self.assertEqual(self.upload().status_code, 201)
        record, document = self.state()
        self.assertEqual(record.cost, Decimal("1234.56"))
        self.assertEqual(document.premium_amount, Decimal("1234.56"))
        self.assertNotIn("cost_held_for_review", record.parsed_payload)

    def test_invoice_needing_review_holds_its_cost_out_of_recorded_spending(self):
        response = self.hold().json()
        record, document = self.state()
        self.assertEqual(record.cost, Decimal("0.00"))
        self.assertEqual(document.premium_amount, Decimal("0.00"))
        self.assertTrue(response["cost_held_for_review"])
        self.assertTrue(response["service_record"]["parsed_payload"]["cost_held_for_review"])
        # The read value waits in the source evidence and the review form.
        self.assertEqual(document.extracted_payload["service_payload"]["cost"], 1234.56)
        queue = self.client.get("/api/documents/review-queue/").json()["results"]
        self.assertEqual([item["fields"]["cost"] for item in queue if item["scope"] == "vehicle_document"], [1234.56])
        self.profile.refresh_from_db()
        position = _build_vehicle_positions([self.profile], list(BikeServiceRecord.objects.filter(user=self.owner)), [])[0]
        self.assertEqual(position["recorded_running_cost_total"], 0)

    def test_review_acceptance_posts_the_held_or_corrected_cost(self):
        for corrections, expected in (({}, "1234.56"), ({"cost": "1000.10"}, "1000.10"), ({"cost": 0}, "0.00")):
            with self.subTest(corrections=corrections):
                BikeServiceRecord.objects.all().delete()
                BikeDocument.objects.all().delete()
                self.hold()
                self.assertEqual(self.post_review("resolve", corrections=corrections).status_code, 200)
                record, document = self.state()
                self.assertEqual(record.cost, Decimal(expected))
                self.assertEqual(document.premium_amount, Decimal(expected))
                self.assertNotIn("cost_held_for_review", record.parsed_payload)

    def test_retry_that_stays_unsure_keeps_the_hold_and_a_confident_one_posts(self):
        self.hold()
        self.assertEqual(self.post_review("retry").status_code, 200)
        record, _ = self.state()
        self.assertEqual(record.cost, Decimal("0.00"))
        self.assertTrue(record.parsed_payload["cost_held_for_review"])
        self.parsed.parser_status = "parsed"
        self.parsed.confidence = 0.9
        self.assertEqual(self.post_review("retry").status_code, 200)
        record, document = self.state()
        self.assertEqual(record.cost, Decimal("1234.56"))
        self.assertEqual(document.premium_amount, Decimal("1234.56"))
        self.assertNotIn("cost_held_for_review", record.parsed_payload)

    def test_retry_never_replaces_or_wipes_a_posted_cost(self):
        self.assertEqual(self.upload().status_code, 201)
        for cost in (9999.0, 0.0):
            with self.subTest(cost=cost):
                self.parsed.service_payload["cost"] = cost
                self.parsed.fields["amount"] = cost
                self.assertEqual(self.post_review("retry").status_code, 200)
                record, document = self.state()
                self.assertEqual(record.cost, Decimal("1234.56"))
                self.assertEqual(document.premium_amount, Decimal("1234.56"))

    def test_owner_edit_survives_retry_and_a_review_that_leaves_cost_alone(self):
        self.assertEqual(self.upload().status_code, 201)
        record, _ = self.state()
        edit = self.client.patch(f"/api/mobility/bike-services/{record.pk}/", data=json.dumps({"cost": "777.70"}), content_type="application/json")
        self.assertEqual(edit.status_code, 200)
        self.assertEqual(self.post_review("retry").status_code, 200)
        self.assertEqual(self.post_review("resolve", corrections={"service_center": "Owner Workshop"}).status_code, 200)
        record, document = self.state()
        self.assertEqual(record.cost, Decimal("777.70"))
        self.assertEqual(record.service_center, "Owner Workshop")
        self.assertEqual(document.premium_amount, Decimal("777.70"))

    def test_owner_edit_of_a_held_cost_releases_the_hold(self):
        self.hold()
        record, _ = self.state()
        edit = self.client.patch(f"/api/mobility/bike-services/{record.pk}/", data=json.dumps({"cost": "500.50"}), content_type="application/json")
        self.assertEqual(edit.status_code, 200)
        self.assertNotIn("cost_held_for_review", edit.json()["parsed_payload"])
        self.assertEqual(self.post_review("resolve", corrections={"service_center": "Owner Workshop"}).status_code, 200)
        record, _ = self.state()
        self.assertEqual(record.cost, Decimal("500.50"))

    def test_invalid_review_values_are_refused_without_changing_anything(self):
        self.assertEqual(self.upload().status_code, 201)
        for corrections in ({"cost": "NaN"}, {"cost": "Infinity"}, {"cost": "-5"}, {"cost": "abc"}, {"cost": True},
                            {"odometer_km": "Infinity"}, {"odometer_km": "-1"}, {"next_service_km": "-1"}):
            with self.subTest(corrections=corrections):
                response = self.post_review("resolve", corrections=corrections)
                self.assertEqual(response.status_code, 400, response.content)
                record, document = self.state()
                self.assertEqual(record.cost, Decimal("1234.56"))
                self.assertEqual(record.odometer_km, 26021)
                self.assertNotIn("accepted_corrections", document.extracted_payload)

    def test_unknown_document_type_override_is_refused(self):
        response = self.client.post("/api/mobility/bike-documents/upload/", {"bike_profile_id": self.profile.pk, "document_type_override": "<img src=x>",
            "document_file": SimpleUploadedFile("synthetic.pdf", b"%PDF-1.4 synthetic", content_type="application/pdf")})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BikeDocument.objects.exists())
