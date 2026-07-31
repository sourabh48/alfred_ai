from io import BytesIO
from unittest.mock import patch

import fitz
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from alfred_ai.services.pdf_recovery import RecoveredPdf
from apps.career.models import CareerJobAnalysis, CareerResume
from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.expenses.services.statement_import import parse_bank_statement
from apps.integrations.models import CreditReportUpload, CreditScore
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument
from apps.ml_engine.models import DocumentParserLearningMemory
from apps.mobility.models import BikeDocument, BikeProfile, BikeServiceRecord
from apps.mobility.services.bike_document_ai import ParsedDocument
from apps.reports.models import OperationalLog, SystemTicket


class DocumentReviewAndRetryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="review_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def _unknown_layout_review_payload(self, *, method, text, field_candidates):
        return {
            "extraction_method": method,
            "raw_text_excerpt": text,
            "extraction_review": {
                "field_candidates": field_candidates,
                "ocr_pages": [
                    {
                        "page": 1,
                        "width": 900,
                        "height": 1200,
                        "preview": text,
                        "variant": "real_unknown_mobile_layout",
                        "regions": [
                            {
                                "text": text[:160],
                                "confidence": 0.42,
                                "bbox": [[20, 40], [840, 40], [840, 96], [20, 96]],
                                "origin": method,
                            }
                        ],
                    }
                ],
                "recovery_steps": [{"step": "cross_family_unknown_layout", "status": "mapped"}],
                "attempts": [{"method": method, "quality": 0.68}],
            },
        }

    def test_parse_bank_statement_uses_isolated_ocr_preview_when_inprocess_ocr_is_unavailable(self):
        preview_text = """
        HDFC BANK
        Statement of account
        Account No : 50100244137504 PRIME
        MR SOURABH SARKAR
        Statement of accountFrom : 31/03/2025 To : 30/03/2026
        """.strip()

        with patch("apps.expenses.services.statement_import._extract_with_pypdf", return_value=""), patch(
            "apps.expenses.services.statement_import._extract_with_fitz",
            return_value="",
        ), patch(
            "apps.expenses.services.statement_import.rebuild_orphaned_pdf",
            return_value=RecoveredPdf(repaired_bytes=b"%PDF-1.7 repaired", page_count=123),
        ), patch(
            "apps.expenses.services.statement_import._extract_with_ocr",
            return_value="",
        ), patch(
            "apps.expenses.services.statement_import._extract_with_isolated_ocr",
            return_value=preview_text,
        ):
            parsed = parse_bank_statement(BytesIO(b"%PDF-1.7 broken"), enable_isolated_ocr=True)

        self.assertEqual(parsed.bank_name, "HDFC Bank")
        self.assertEqual(parsed.account_number, "50100244137504 PRIME")
        self.assertEqual(parsed.account_holder, "Sourabh Sarkar")
        self.assertEqual(parsed.parser_status, "needs_review")
        self.assertIn("Isolated OCR worker recovered readable text", parsed.parser_notes)

    def test_statement_upload_is_marked_for_background_retry(self):
        statement_file = SimpleUploadedFile("hdfc statement.pdf", b"%PDF-1.7 broken", content_type="application/pdf")

        with patch(
            "apps.expenses.views.parse_bank_statement",
            return_value=parse_bank_statement(BytesIO(b""), enable_isolated_ocr=False),
        ), patch(
            "apps.expenses.tasks.retry_statement_upload_task.delay",
            return_value=None,
        ):
            response = self.client.post("/api/expenses/import-statement/", data={"statement": statement_file})

        self.assertEqual(response.status_code, 201)
        upload = StatementUpload.objects.get()
        self.assertEqual(upload.extracted_payload["background_retry"]["state"], "queued")
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="statement_document",
                event_type="metadata_only_import",
            ).exists()
        )

    def test_review_queue_lists_low_confidence_statement_and_accepts_correction(self):
        upload = StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="hdfc statement.pdf",
            parser_status="failed",
            parse_confidence=0.08,
            extracted_payload={"parser_notes": "broken pdf"},
        )

        queue_response = self.client.get("/api/documents/review-queue/")
        self.assertEqual(queue_response.status_code, 200)
        self.assertEqual(queue_response.json()["results"][0]["scope"], "statement_document")

        with patch("alfred_ai.services.document_review.retry_statement_upload", return_value=None):
            response = self.client.post(
                "/api/documents/review-queue/resolve/",
                data={
                    "scope": "statement_document",
                    "id": upload.id,
                    "corrections": {
                        "bank_name": "HDFC Bank",
                        "account_holder": "Sourabh Sarkar",
                        "account_number": "50100244137504",
                        "statement_kind": "bank_statement",
                    },
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        upload.refresh_from_db()
        self.assertEqual(upload.bank_name, "HDFC Bank")
        self.assertEqual(upload.account_number, "50100244137504")
        self.assertEqual(upload.extracted_payload["accepted_corrections"]["account_holder"], "Sourabh Sarkar")
        self.assertTrue(upload.extracted_payload["review_queue_resolved"])
        queue_after = self.client.get("/api/documents/review-queue/")
        self.assertEqual(queue_after.status_code, 200)
        self.assertFalse(
            any(entry["id"] == upload.id and entry["scope"] == "statement_document" for entry in queue_after.json()["results"])
        )

    def test_statement_correction_uses_deeper_retry_window_for_partial_ocr_upload(self):
        upload = StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="hdfc statement.pdf",
            parser_status="needs_review",
            parse_confidence=0.68,
            extracted_payload={
                "parser_notes": "Partial OCR preview retained.",
                "ocr_progress": {"processed_pages": 2, "total_pages": 123, "is_partial": True},
            },
            imported_count=0,
        )

        with patch("alfred_ai.services.document_review.retry_statement_upload", return_value=None) as retry_mock:
            response = self.client.post(
                "/api/documents/review-queue/resolve/",
                data={
                    "scope": "statement_document",
                    "id": upload.id,
                    "corrections": {
                        "bank_name": "HDFC Bank",
                        "account_holder": "Sourabh Sarkar",
                        "account_number": "50100244137504",
                    },
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        retry_mock.assert_called_once()
        self.assertEqual(retry_mock.call_args.kwargs["ocr_page_limit"], 24)

    def test_review_queue_includes_loan_closure_and_investment_documents(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXIS-CL-001",
            principal=250000,
            interest_rate=12.5,
            emi=8450,
            tenure_months=36,
            remaining_balance=174000,
            start_date="2025-01-10",
        )
        LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="closure.pdf",
            extracted_text="Axis Bank foreclosure letter",
            extracted_payload={"matched_keyword": "Foreclosure"},
            parser_status="needs_review",
            parse_confidence=0.31,
            verification_status="pending",
        )
        InvestmentImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("portfolio.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="portfolio.pdf",
            broker_name="Groww",
            parser_status="needs_review",
            parse_confidence=0.28,
            extracted_payload={"investments": [{"asset_name": "Axis Bluechip Fund"}]},
            summary="Needs review",
        )

        response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(response.status_code, 200)
        scopes = {item["scope"] for item in response.json()["results"]}
        self.assertIn("loan_closure_document", scopes)
        self.assertIn("investment_document", scopes)

    def test_review_queue_includes_low_confidence_recruiter_documents(self):
        CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="Recruiter Mail Intake",
            source_document_name="recruiter_message.txt",
            job_url="https://alfred.local/recruiter/demo",
            apply_url="https://alfred.local/recruiter/demo",
            parser_status="needs_review",
            parse_confidence=0.31,
            extracted_text="Looking for a data analyst in Bengaluru with SQL and Python.",
            summary="Recruiter intake retained for review.",
            extracted_payload={
                "source_kind": "recruiter_message",
                "job_snapshot": {
                    "title": "Data Analyst",
                    "company": "Example Analytics",
                    "location": "Bengaluru",
                    "required_skills": ["SQL", "Python"],
                    "experience_years": 3,
                },
            },
        )

        response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(response.status_code, 200)
        scopes = {item["scope"] for item in response.json()["results"]}
        self.assertIn("recruiter_document", scopes)

    def test_review_queue_exposes_ocr_overlay_artifacts_for_resume_documents(self):
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="resume.pdf",
            parser_status="needs_review",
            parse_confidence=0.41,
            extracted_text="Sourabh Sarkar Java Backend Developer",
            summary="Resume retained for review.",
            extracted_payload={
                "role": "Java Backend Developer",
                "skills": ["Java", "Spring Boot"],
                "extraction_method": "rapidocr_image",
                "raw_text_excerpt": "Sourabh Sarkar Java Backend Developer",
                "extraction_review": {
                    "field_candidates": [
                        {
                            "field_type": "role",
                            "field_name": "role",
                            "label": "Role",
                            "value": "Java Backend Developer",
                            "confidence": 0.96,
                            "source": "rapidocr_image",
                            "page": 1,
                        }
                    ],
                    "ocr_pages": [
                        {
                            "page": 1,
                            "width": 1200,
                            "height": 1700,
                            "preview": "Sourabh Sarkar Java Backend Developer",
                            "line_count": 2,
                            "regions": [
                                {
                                    "text": "Java Backend Developer",
                                    "confidence": 0.96,
                                    "bbox": [[12, 40], [260, 40], [260, 72], [12, 72]],
                                    "origin": "rapidocr_image",
                                }
                            ],
                        }
                    ],
                    "recovery_steps": [{"step": "image_bytes_fallback", "status": "recovered"}],
                    "attempts": [{"method": "rapidocr_image", "quality": 0.84}],
                },
            },
        )

        response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(response.status_code, 200)
        item = next(entry for entry in response.json()["results"] if entry["scope"] == "resume_document")
        self.assertEqual(item["review_artifacts"]["extraction_method"], "rapidocr_image")
        self.assertEqual(item["review_artifacts"]["ocr_pages"][0]["page"], 1)
        self.assertEqual(item["review_artifacts"]["recovery_steps"][0]["step"], "image_bytes_fallback")
        self.assertIn("Java Backend Developer", item["review_artifacts"]["raw_text_excerpt"])
        self.assertEqual(item["review_artifacts"]["field_candidates"][0]["value"], "Java Backend Developer")

    def test_review_queue_promotes_accepted_corrections_into_overlay_candidates(self):
        CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="resume.pdf",
            parser_status="needs_review",
            parse_confidence=0.41,
            extracted_text="Sourabh Sarkar Jav Backend Devel0per",
            summary="Resume retained for review.",
            extracted_payload={
                "role": "Jav Backend Devel0per",
                "accepted_corrections": {
                    "role": "Java Backend Developer",
                    "skills": ["Java", "Spring Boot"],
                },
                "background_retry": {
                    "retry_count": 2,
                    "state": "needs_review",
                    "resolution": "still_needs_review",
                },
                "extraction_review": {
                    "best_method": "rapidocr_image",
                    "raw_text_excerpt": "Sourabh Sarkar Jav Backend Devel0per",
                    "field_candidates": [
                        {
                            "field_type": "role",
                            "field_name": "role",
                            "label": "Role",
                            "value": "Jav Backend Devel0per",
                            "confidence": 0.42,
                            "source": "rapidocr_image",
                            "page": 1,
                        }
                    ],
                    "ocr_pages": [
                        {
                            "page": 1,
                            "width": 1200,
                            "height": 1700,
                            "preview": "Sourabh Sarkar Java Backend Developer",
                            "line_count": 2,
                            "regions": [
                                {
                                    "text": "Java Backend Developer",
                                    "confidence": 0.42,
                                    "bbox": [[12, 40], [260, 40], [260, 72], [12, 72]],
                                    "origin": "rapidocr_image",
                                }
                            ],
                        }
                    ],
                },
            },
        )

        response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(response.status_code, 200)
        item = next(entry for entry in response.json()["results"] if entry["scope"] == "resume_document")
        artifacts = item["review_artifacts"]
        accepted_candidates = [
            candidate
            for candidate in artifacts["field_candidates"]
            if candidate.get("source") == "accepted_correction"
        ]
        self.assertEqual({candidate["field_name"] for candidate in accepted_candidates}, {"role", "skills"})
        self.assertTrue(all(candidate["accepted"] for candidate in accepted_candidates))
        self.assertIn("role", artifacts["ocr_pages"][0]["regions"][0]["field_matches"])
        self.assertTrue(artifacts["ocr_pages"][0]["regions"][0]["needs_correction"])
        self.assertEqual(artifacts["overlay_summary"]["accepted_correction_count"], 2)
        self.assertEqual(artifacts["overlay_summary"]["retry_count"], 2)
        self.assertEqual(artifacts["overlay_summary"]["retry_resolution"], "still_needs_review")
        self.assertEqual(artifacts["overlay_summary"]["low_confidence_regions"], 1)

    def test_review_queue_maps_generic_ocr_candidates_to_vehicle_review_fields(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa 6G",
            model_name="Activa 6G",
            vehicle_type="scooter",
            bike_class="scooter",
        )
        BikeDocument.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            document_type="invoice",
            parser_status="needs_review",
            parse_confidence=0.43,
            source_text="Invoice Date 2026-03-31 Total Customer Amount Rs 2432.92",
            extracted_payload={
                "raw_text_excerpt": "Invoice Date 2026-03-31 Total Customer Amount Rs 2432.92",
                "extraction_review": {
                    "field_candidates": [
                        {
                            "field_type": "amount",
                            "field_name": "amount",
                            "label": "Amount",
                            "value": "2432.92",
                            "confidence": 0.82,
                            "source": "raw_text",
                            "context": "Total Customer Amount Rs 2432.92",
                            "page": 1,
                        },
                        {
                            "field_type": "date",
                            "field_name": "document_date",
                            "label": "Date",
                            "value": "2026-03-31",
                            "confidence": 0.79,
                            "source": "ocr_region",
                            "context": "Invoice Date 2026-03-31",
                            "page": 1,
                        },
                    ],
                    "ocr_pages": [
                        {
                            "page": 1,
                            "width": 1000,
                            "height": 1400,
                            "preview": "Invoice Date 2026-03-31 Total Customer Amount Rs 2432.92",
                            "regions": [
                                {
                                    "text": "Total Customer Amount Rs 2432.92",
                                    "confidence": 0.48,
                                    "bbox": [[20, 60], [620, 60], [620, 96], [20, 96]],
                                    "origin": "rapidocr_image",
                                }
                            ],
                        }
                    ],
                },
            },
        )

        response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(response.status_code, 200)
        item = next(entry for entry in response.json()["results"] if entry["scope"] == "vehicle_document")
        artifacts = item["review_artifacts"]
        candidate_names = [candidate["field_name"] for candidate in artifacts["field_candidates"]]
        for field_name in ["cost", "total_customer_amount", "service_date"]:
            self.assertIn(field_name, candidate_names)
        self.assertLess(candidate_names.index("cost"), candidate_names.index("amount"))
        schema_aliases = [candidate for candidate in artifacts["field_candidates"] if candidate.get("source", "").endswith("_schema_alias")]
        self.assertTrue(any(candidate["label"] == "Service Cost" and candidate["value"] == "2432.92" for candidate in schema_aliases))
        self.assertIn("cost", artifacts["ocr_pages"][0]["candidate_fields"])
        self.assertEqual(artifacts["overlay_summary"]["low_confidence_regions"], 1)
        self.assertGreaterEqual(artifacts["overlay_summary"]["field_candidate_count"], 6)

    def test_review_queue_maps_unknown_vehicle_invoice_layout_aliases(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Suzuki V-Strom SX",
            make="Suzuki",
            model_name="V-Strom SX",
            vehicle_type="motorcycle",
            bike_class="adventure",
            vehicle_number="KA05MN4321",
        )
        layouts = [
            {
                "title": "jagadamba-thermal-strip.jpg",
                "text": "\n".join(
                    [
                        "JAGADAMBA AUTOMOBILES",
                        "Retail Bill / Job Slip",
                        "JC RJC011402IJ11758 DATE 31-03-2026",
                        "KM 26021",
                        "Part BRAKE PAD KIT 820",
                        "Labour PERIODIC SERVICE LABOUR 640",
                        "Customer Payable 2432.92",
                    ]
                ),
                "field_candidates": [
                    {
                        "field_type": "grand_total",
                        "field_name": "customer_payable",
                        "label": "Customer Payable",
                        "value": "2432.92",
                        "confidence": 0.91,
                        "source": "unknown_invoice_ocr",
                        "context": "Customer Payable 2432.92",
                        "page": 1,
                    },
                    {
                        "field_type": "document_date",
                        "field_name": "service_on",
                        "label": "Date",
                        "value": "2026-03-31",
                        "confidence": 0.89,
                        "source": "unknown_invoice_ocr",
                        "context": "DATE 31-03-2026",
                        "page": 1,
                    },
                    {
                        "field_type": "odometer",
                        "field_name": "km",
                        "label": "KM",
                        "value": "26021",
                        "confidence": 0.87,
                        "source": "unknown_invoice_ocr",
                        "context": "KM 26021",
                        "page": 1,
                    },
                    {
                        "field_type": "parts_amount",
                        "field_name": "part_total",
                        "label": "Part Total",
                        "value": "820",
                        "confidence": 0.83,
                        "source": "unknown_invoice_ocr",
                        "context": "Part BRAKE PAD KIT 820",
                        "page": 1,
                    },
                    {
                        "field_type": "labour_amount",
                        "field_name": "labour_total",
                        "label": "Labour Total",
                        "value": "640",
                        "confidence": 0.81,
                        "source": "unknown_invoice_ocr",
                        "context": "Labour PERIODIC SERVICE LABOUR 640",
                        "page": 1,
                    },
                ],
                "regions": [
                    {
                        "text": "JC RJC011402IJ11758 DATE 31-03-2026",
                        "confidence": 0.46,
                        "bbox": [[18, 56], [520, 56], [520, 88], [18, 88]],
                        "origin": "mobile_crop",
                    },
                    {
                        "text": "Customer Payable 2432.92",
                        "confidence": 0.42,
                        "bbox": [[18, 250], [560, 250], [560, 286], [18, 286]],
                        "origin": "mobile_crop",
                    },
                ],
                "expected": {
                    "cost": "2432.92",
                    "total_customer_amount": "2432.92",
                    "service_date": "2026-03-31",
                    "odometer_km": "26021",
                    "parts_customer_amount": "820",
                    "labour_customer_amount": "640",
                },
            },
            {
                "title": "gst-two-column-service-invoice.png",
                "text": "\n".join(
                    [
                        "AUTH DEALER TAX INV",
                        "Inv no SI-22071",
                        "Service Dt 2026/04/12",
                        "Odomtr 31580",
                        "Parts Amt 1520.50",
                        "Labour Amt 900",
                        "Invoice Total 2420.50",
                    ]
                ),
                "field_candidates": [
                    {
                        "field_type": "invoice_number",
                        "field_name": "invoice_number",
                        "label": "Invoice Number",
                        "value": "SI-22071",
                        "confidence": 0.84,
                        "source": "unknown_invoice_ocr",
                        "context": "Inv no SI-22071",
                        "page": 1,
                    },
                    {
                        "field_type": "date",
                        "field_name": "service_dt",
                        "label": "Service Dt",
                        "value": "2026-04-12",
                        "confidence": 0.88,
                        "source": "unknown_invoice_ocr",
                        "context": "Service Dt 2026/04/12",
                        "page": 1,
                    },
                    {
                        "field_type": "kilometer",
                        "field_name": "odomtr",
                        "label": "Odomtr",
                        "value": "31580",
                        "confidence": 0.8,
                        "source": "unknown_invoice_ocr",
                        "context": "Odomtr 31580",
                        "page": 1,
                    },
                    {
                        "field_type": "parts_amount",
                        "field_name": "parts_amount",
                        "label": "Parts Amt",
                        "value": "1520.50",
                        "confidence": 0.79,
                        "source": "unknown_invoice_ocr",
                        "context": "Parts Amt 1520.50",
                        "page": 1,
                    },
                    {
                        "field_type": "labor_amount",
                        "field_name": "labor_amount",
                        "label": "Labour Amt",
                        "value": "900",
                        "confidence": 0.78,
                        "source": "unknown_invoice_ocr",
                        "context": "Labour Amt 900",
                        "page": 1,
                    },
                    {
                        "field_type": "invoice_total",
                        "field_name": "invoice_total",
                        "label": "Invoice Total",
                        "value": "2420.50",
                        "confidence": 0.86,
                        "source": "unknown_invoice_ocr",
                        "context": "Invoice Total 2420.50",
                        "page": 1,
                    },
                ],
                "regions": [
                    {
                        "text": "Service Dt 2026/04/12 Odomtr 31580",
                        "confidence": 0.49,
                        "bbox": [[42, 135], [710, 135], [710, 171], [42, 171]],
                        "origin": "two_column_table",
                    },
                    {
                        "text": "Invoice Total 2420.50",
                        "confidence": 0.51,
                        "bbox": [[430, 530], [840, 530], [840, 568], [430, 568]],
                        "origin": "two_column_table",
                    },
                ],
                "expected": {
                    "document_number": "SI-22071",
                    "cost": "2420.50",
                    "total_customer_amount": "2420.50",
                    "service_date": "2026-04-12",
                    "odometer_km": "31580",
                    "parts_customer_amount": "1520.50",
                    "labour_customer_amount": "900",
                },
            },
            {
                "title": "mobile-photo-crumpled-invoice.webp",
                "text": "\n".join(
                    [
                        "Work Order",
                        "No: WO-441",
                        "Dt. 29 Mar 2026",
                        "KMs 18204",
                        "Grand Total Rs. 1187.00",
                    ]
                ),
                "field_candidates": [
                    {
                        "field_type": "invoice_number",
                        "field_name": "invoice_number",
                        "label": "Work Order No",
                        "value": "WO-441",
                        "confidence": 0.82,
                        "source": "unknown_invoice_ocr",
                        "context": "No: WO-441",
                        "page": 1,
                    },
                    {
                        "field_type": "document_date",
                        "field_name": "date",
                        "label": "Date",
                        "value": "2026-03-29",
                        "confidence": 0.77,
                        "source": "unknown_invoice_ocr",
                        "context": "Dt. 29 Mar 2026",
                        "page": 1,
                    },
                    {
                        "field_type": "kms",
                        "field_name": "kilometers",
                        "label": "KMs",
                        "value": "18204",
                        "confidence": 0.76,
                        "source": "unknown_invoice_ocr",
                        "context": "KMs 18204",
                        "page": 1,
                    },
                    {
                        "field_type": "grand_total",
                        "field_name": "total",
                        "label": "Grand Total",
                        "value": "1187.00",
                        "confidence": 0.79,
                        "source": "unknown_invoice_ocr",
                        "context": "Grand Total Rs. 1187.00",
                        "page": 1,
                    },
                ],
                "regions": [
                    {
                        "text": "Dt. 29 Mar 2026 KMs 18204",
                        "confidence": 0.39,
                        "bbox": [[30, 90], [498, 90], [498, 123], [30, 123]],
                        "origin": "creased_photo",
                    },
                    {
                        "text": "Grand Total Rs. 1187.00",
                        "confidence": 0.44,
                        "bbox": [[30, 330], [565, 330], [565, 368], [30, 368]],
                        "origin": "creased_photo",
                    },
                ],
                "expected": {
                    "document_number": "WO-441",
                    "cost": "1187.00",
                    "total_customer_amount": "1187.00",
                    "service_date": "2026-03-29",
                    "odometer_km": "18204",
                },
            },
        ]
        for layout in layouts:
            BikeDocument.objects.create(
                user=self.user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                document_type="invoice",
                document_title=layout["title"],
                parser_status="needs_review",
                parse_confidence=0.37,
                source_text=layout["text"],
                extracted_payload={
                    "extraction_method": "real_unknown_invoice_ocr",
                    "raw_text_excerpt": layout["text"],
                    "invoice_review": {"recovered_edge_rows": 1, "compact_ocr_rows": 2},
                    "extraction_review": {
                        "field_candidates": layout["field_candidates"],
                        "ocr_pages": [
                            {
                                "page": 1,
                                "width": 1000,
                                "height": 1400,
                                "preview": layout["text"],
                                "variant": "unknown_mobile_layout",
                                "regions": layout["regions"],
                            }
                        ],
                        "recovery_steps": [{"step": "unknown_layout_alias_review", "status": "mapped"}],
                        "attempts": [{"method": "rapidocr_mobile_layout", "quality": 0.71}],
                    },
                },
            )

        response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(response.status_code, 200)
        vehicle_items = {
            item["file_name"]: item
            for item in response.json()["results"]
            if item["scope"] == "vehicle_document"
        }
        self.assertEqual(set(vehicle_items), {layout["title"] for layout in layouts})
        for layout in layouts:
            with self.subTest(layout=layout["title"]):
                artifacts = vehicle_items[layout["title"]]["review_artifacts"]
                alias_candidates = [
                    candidate
                    for candidate in artifacts["field_candidates"]
                    if candidate.get("source", "").endswith("_schema_alias")
                ]
                alias_values = {
                    (candidate.get("field_name"), candidate.get("value"))
                    for candidate in alias_candidates
                }
                for field_name, value in layout["expected"].items():
                    self.assertIn((field_name, value), alias_values)
                self.assertIn("unknown_layout_alias_review", [step["step"] for step in artifacts["recovery_steps"]])
                self.assertGreaterEqual(artifacts["overlay_summary"]["field_candidate_count"], 10)
                self.assertGreaterEqual(artifacts["overlay_summary"]["low_confidence_regions"], 2)
                self.assertIn("odometer_km", artifacts["ocr_pages"][0]["candidate_fields"])

    def test_review_queue_maps_cross_family_unknown_layouts_and_records_corrections(self):
        statement = StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="statement-mobile-photo.jpg",
            parser_status="needs_review",
            parse_confidence=0.34,
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_statement_ocr",
                text="Institution HDFC Bank Acct No 50100244137504 Period Start 2026-03-01 Period End 2026-03-31",
                field_candidates=[
                    {
                        "field_type": "institution",
                        "field_name": "bank",
                        "label": "Institution",
                        "value": "HDFC Bank",
                        "confidence": 0.77,
                        "source": "unknown_statement_ocr",
                    },
                    {
                        "field_type": "account no",
                        "field_name": "acct-no",
                        "label": "Acct No",
                        "value": "50100244137504",
                        "confidence": 0.75,
                        "source": "unknown_statement_ocr",
                    },
                    {
                        "field_type": "from date",
                        "field_name": "period start",
                        "label": "Period Start",
                        "value": "2026-03-01",
                        "confidence": 0.74,
                        "source": "unknown_statement_ocr",
                    },
                    {
                        "field_type": "to date",
                        "field_name": "period end",
                        "label": "Period End",
                        "value": "2026-03-31",
                        "confidence": 0.74,
                        "source": "unknown_statement_ocr",
                    },
                ],
            ),
        )
        loan_import = LoanImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("loan-whatsapp.jpg", b"loan", content_type="image/jpeg"),
            file_name="loan-whatsapp.jpg",
            parser_status="needs_review",
            parse_confidence=0.3,
            extracted_text="Lender Name Axis Bank Loan No AXIS-PL-001 Product Type Personal Doc Type Sanction Letter",
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_loan_ocr",
                text="Lender Name Axis Bank Loan No AXIS-PL-001 Product Type Personal Doc Type Sanction Letter",
                field_candidates=[
                    {
                        "field_type": "lender-name",
                        "field_name": "bank",
                        "label": "Lender Name",
                        "value": "Axis Bank",
                        "confidence": 0.72,
                        "source": "unknown_loan_ocr",
                    },
                    {
                        "field_type": "loan no",
                        "field_name": "loan no",
                        "label": "Loan No",
                        "value": "AXIS-PL-001",
                        "confidence": 0.73,
                        "source": "unknown_loan_ocr",
                    },
                    {
                        "field_type": "product type",
                        "field_name": "product type",
                        "label": "Product Type",
                        "value": "personal",
                        "confidence": 0.7,
                        "source": "unknown_loan_ocr",
                    },
                    {
                        "field_type": "doc type",
                        "field_name": "doc type",
                        "label": "Doc Type",
                        "value": "sanction_letter",
                        "confidence": 0.69,
                        "source": "unknown_loan_ocr",
                    },
                ],
            ),
        )
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISCLOSE123",
            principal=220000,
            interest_rate=12.0,
            emi=7100,
            tenure_months=36,
            remaining_balance=84500,
            start_date="2025-04-01",
        )
        closure = LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure-sms.pdf", b"closure", content_type="application/pdf"),
            file_name="closure-sms.pdf",
            parser_status="needs_review",
            parse_confidence=0.33,
            verification_status="pending",
            extracted_text="Axis Bank FORECLOSURE statement Loan No AXISCLOSE123 Total Due 84500 Closure On 2026-03-30",
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_closure_ocr",
                text="Axis Bank FORECLOSURE statement Loan No AXISCLOSE123 Total Due 84500 Closure On 2026-03-30",
                field_candidates=[
                    {
                        "field_type": "loan-no",
                        "field_name": "loan no",
                        "label": "Loan No",
                        "value": "AXISCLOSE123",
                        "confidence": 0.76,
                        "source": "unknown_closure_ocr",
                    },
                    {
                        "field_type": "total due",
                        "field_name": "amount payable",
                        "label": "Total Due",
                        "value": "84500",
                        "confidence": 0.75,
                        "source": "unknown_closure_ocr",
                    },
                    {
                        "field_type": "closure on",
                        "field_name": "closure on",
                        "label": "Closure On",
                        "value": "2026-03-30",
                        "confidence": 0.74,
                        "source": "unknown_closure_ocr",
                    },
                    {
                        "field_type": "matched status",
                        "field_name": "status",
                        "label": "Status",
                        "value": "Foreclosure",
                        "confidence": 0.8,
                        "source": "unknown_closure_ocr",
                    },
                ],
            ),
        )
        investment_doc = InvestmentImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("folio-screenshot.png", b"folio", content_type="image/png"),
            file_name="folio-screenshot.png",
            parser_status="needs_review",
            parse_confidence=0.35,
            extracted_text="Broker Groww Folio No FOLIO7788 Scheme Axis Bluechip Market Value 56200 Purchase Value 50000",
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_portfolio_ocr",
                text="Broker Groww Folio No FOLIO7788 Scheme Axis Bluechip Market Value 56200 Purchase Value 50000",
                field_candidates=[
                    {
                        "field_type": "broker",
                        "field_name": "dp name",
                        "label": "Broker",
                        "value": "Groww",
                        "confidence": 0.78,
                        "source": "unknown_portfolio_ocr",
                    },
                    {
                        "field_type": "folio no",
                        "field_name": "folio no",
                        "label": "Folio No",
                        "value": "FOLIO7788",
                        "confidence": 0.77,
                        "source": "unknown_portfolio_ocr",
                    },
                    {
                        "field_type": "scheme",
                        "field_name": "scheme name",
                        "label": "Scheme",
                        "value": "Axis Bluechip Fund",
                        "confidence": 0.76,
                        "source": "unknown_portfolio_ocr",
                    },
                    {
                        "field_type": "market value",
                        "field_name": "valuation",
                        "label": "Market Value",
                        "value": "56200",
                        "confidence": 0.75,
                        "source": "unknown_portfolio_ocr",
                    },
                    {
                        "field_type": "purchase value",
                        "field_name": "purchase value",
                        "label": "Purchase Value",
                        "value": "50000",
                        "confidence": 0.75,
                        "source": "unknown_portfolio_ocr",
                    },
                ],
            ),
        )
        resume = CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("resume-scan.jpg", b"resume", content_type="image/jpeg"),
            file_name="resume-scan.jpg",
            parser_status="needs_review",
            parse_confidence=0.4,
            extracted_text="Current Title Backend Engineer Years Exp 5 Key Skills Java Spring Boot SQL",
            summary="Unknown resume scan retained for review.",
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_resume_ocr",
                text="Current Title Backend Engineer Years Exp 5 Key Skills Java Spring Boot SQL",
                field_candidates=[
                    {
                        "field_type": "current title",
                        "field_name": "current-title",
                        "label": "Current Title",
                        "value": "Backend Engineer",
                        "confidence": 0.76,
                        "source": "unknown_resume_ocr",
                    },
                    {
                        "field_type": "years exp",
                        "field_name": "years exp",
                        "label": "Years Exp",
                        "value": "5",
                        "confidence": 0.74,
                        "source": "unknown_resume_ocr",
                    },
                    {
                        "field_type": "key skills",
                        "field_name": "key-skills",
                        "label": "Key Skills",
                        "value": "Java, Spring Boot, SQL",
                        "confidence": 0.73,
                        "source": "unknown_resume_ocr",
                    },
                ],
            ),
        )
        recruiter = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="Recruiter WhatsApp",
            source_document_name="recruiter-whatsapp.txt",
            job_url="https://example.com/recruiter/backend",
            apply_url="https://example.com/recruiter/backend",
            parser_status="needs_review",
            parse_confidence=0.37,
            extracted_text="Role Title Senior Backend Engineer Employer Acme Location Pune CTC Min 1800000 CTC Max 2600000",
            summary="Recruiter chat retained for review.",
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_recruiter_ocr",
                text="Role Title Senior Backend Engineer Employer Acme Location Pune CTC Min 1800000 CTC Max 2600000",
                field_candidates=[
                    {
                        "field_type": "role title",
                        "field_name": "role-title",
                        "label": "Role Title",
                        "value": "Senior Backend Engineer",
                        "confidence": 0.78,
                        "source": "unknown_recruiter_ocr",
                    },
                    {
                        "field_type": "employer",
                        "field_name": "employer",
                        "label": "Employer",
                        "value": "Acme",
                        "confidence": 0.76,
                        "source": "unknown_recruiter_ocr",
                    },
                    {
                        "field_type": "work location",
                        "field_name": "work location",
                        "label": "Work Location",
                        "value": "Pune",
                        "confidence": 0.75,
                        "source": "unknown_recruiter_ocr",
                    },
                    {
                        "field_type": "ctc min",
                        "field_name": "ctc-min",
                        "label": "CTC Min",
                        "value": "1800000",
                        "confidence": 0.74,
                        "source": "unknown_recruiter_ocr",
                    },
                    {
                        "field_type": "ctc max",
                        "field_name": "ctc-max",
                        "label": "CTC Max",
                        "value": "2600000",
                        "confidence": 0.74,
                        "source": "unknown_recruiter_ocr",
                    },
                ],
            )
            | {"source_kind": "recruiter_message", "job_snapshot": {}},
        )
        credit = CreditReportUpload.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("cibil-mobile.jpg", b"credit", content_type="image/jpeg"),
            file_name="cibil-mobile.jpg",
            parser_status="needs_review",
            parse_confidence=0.36,
            extracted_text="Credit Bureau CIBIL Customer Name Sourabh Sarkar Control Number CN998877 Generated Date 2026-03-28",
            extracted_payload=self._unknown_layout_review_payload(
                method="unknown_credit_ocr",
                text="Credit Bureau CIBIL Customer Name Sourabh Sarkar Control Number CN998877 Generated Date 2026-03-28",
                field_candidates=[
                    {
                        "field_type": "credit bureau",
                        "field_name": "credit-bureau",
                        "label": "Credit Bureau",
                        "value": "CIBIL",
                        "confidence": 0.8,
                        "source": "unknown_credit_ocr",
                    },
                    {
                        "field_type": "customer name",
                        "field_name": "customer-name",
                        "label": "Customer Name",
                        "value": "Sourabh Sarkar",
                        "confidence": 0.78,
                        "source": "unknown_credit_ocr",
                    },
                    {
                        "field_type": "control number",
                        "field_name": "control-number",
                        "label": "Control Number",
                        "value": "CN998877",
                        "confidence": 0.77,
                        "source": "unknown_credit_ocr",
                    },
                    {
                        "field_type": "generated date",
                        "field_name": "generated-date",
                        "label": "Generated Date",
                        "value": "2026-03-28",
                        "confidence": 0.76,
                        "source": "unknown_credit_ocr",
                    },
                ],
            ),
        )

        queue_response = self.client.get("/api/documents/review-queue/")

        self.assertEqual(queue_response.status_code, 200)
        items = {(item["scope"], item["file_name"]): item for item in queue_response.json()["results"]}
        expected_aliases = {
            ("statement_document", statement.file_name): {"bank_name", "account_number", "statement_start", "statement_end"},
            ("loan_document", loan_import.file_name): {"lender", "loan_account_number", "loan_type", "document_type"},
            ("loan_closure_document", closure.file_name): {"loan_account_number", "closure_amount", "closure_date", "matched_keyword"},
            ("investment_document", investment_doc.file_name): {"broker_name", "account_number", "asset_name", "invested_amount", "current_value"},
            ("resume_document", resume.file_name): {"role", "experience_years", "skills"},
            ("recruiter_document", recruiter.source_document_name): {"job_title", "company", "location", "salary_min", "salary_max"},
            ("credit_report", credit.file_name): {"bureau", "applicant_name", "report_number", "report_date"},
        }
        for key, field_names in expected_aliases.items():
            with self.subTest(queue_item=key):
                self.assertIn(key, items)
                alias_field_names = {
                    candidate["field_name"]
                    for candidate in items[key]["review_artifacts"]["field_candidates"]
                    if candidate.get("source", "").endswith("_schema_alias")
                }
                self.assertTrue(field_names.issubset(alias_field_names))

        with patch("alfred_ai.services.document_review.retry_statement_upload", return_value=None):
            statement_response = self.client.post(
                "/api/documents/review-queue/resolve/",
                data={
                    "scope": "statement_document",
                    "id": statement.id,
                    "corrections": {
                        "bank_name": "HDFC Bank",
                        "account_holder": "Sourabh Sarkar",
                        "account_number": "50100244137504",
                        "statement_start": "2026-03-01",
                        "statement_end": "2026-03-31",
                    },
                },
                content_type="application/json",
            )
        loan_response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "loan_document",
                "id": loan_import.id,
                "corrections": {
                    "document_type": "sanction_letter",
                    "lender": "Axis Bank",
                    "loan_type": "personal",
                    "loan_account_number": "AXIS-PL-001",
                },
            },
            content_type="application/json",
        )
        closure_response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "loan_closure_document",
                "id": closure.id,
                "corrections": {
                    "loan_account_number": "AXISCLOSE123",
                    "matched_keyword": "Foreclosure",
                    "closure_amount": "84500",
                    "closure_date": "2026-03-30",
                },
            },
            content_type="application/json",
        )
        investment_response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "investment_document",
                "id": investment_doc.id,
                "corrections": {
                    "broker_name": "Groww",
                    "asset_name": "Axis Bluechip Fund",
                    "asset_type": "mutual_fund",
                    "account_number": "FOLIO7788",
                    "invested_amount": "50000",
                    "current_value": "56200",
                },
            },
            content_type="application/json",
        )
        resume_response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "resume_document",
                "id": resume.id,
                "corrections": {
                    "role": "Backend Engineer",
                    "experience_years": "5",
                    "skills": "Java, Spring Boot, SQL",
                },
            },
            content_type="application/json",
        )
        recruiter_response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "recruiter_document",
                "id": recruiter.id,
                "corrections": {
                    "job_title": "Senior Backend Engineer",
                    "company": "Acme",
                    "location": "Pune",
                    "experience_years": "5",
                    "salary_min": "1800000",
                    "salary_max": "2600000",
                },
            },
            content_type="application/json",
        )
        credit_response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "credit_report",
                "id": credit.id,
                "corrections": {
                    "bureau": "CIBIL",
                    "applicant_name": "Sourabh Sarkar",
                    "report_number": "CN998877",
                    "report_date": "2026-03-28",
                },
            },
            content_type="application/json",
        )

        for response in [
            statement_response,
            loan_response,
            closure_response,
            investment_response,
            resume_response,
            recruiter_response,
            credit_response,
        ]:
            self.assertEqual(response.status_code, 200, response.content)

        statement.refresh_from_db()
        loan_import.refresh_from_db()
        closure.refresh_from_db()
        investment_doc.refresh_from_db()
        resume.refresh_from_db()
        recruiter.refresh_from_db()
        credit.refresh_from_db()

        self.assertEqual(statement.bank_name, "HDFC Bank")
        self.assertEqual(statement.account_number, "50100244137504")
        self.assertEqual(str(statement.statement_start), "2026-03-01")
        self.assertTrue(statement.extracted_payload["review_queue_resolved"])
        self.assertEqual(loan_import.document_type, "sanction_letter")
        self.assertEqual(loan_import.extracted_payload["accepted_corrections"]["loan_account_number"], "AXIS-PL-001")
        self.assertEqual(closure.verification_status, "verified")
        self.assertEqual(closure.parser_status, "parsed")
        self.assertEqual(closure.closure_amount, 84500)
        self.assertEqual(investment_doc.parser_status, "parsed")
        self.assertEqual(investment_doc.broker_name, "Groww")
        self.assertTrue(investment_doc.linked_investments.filter(asset_name="Axis Bluechip Fund").exists())
        self.assertEqual(resume.parser_status, "parsed")
        self.assertEqual(resume.extracted_payload["skills"], ["Java", "Spring Boot", "SQL"])
        self.assertEqual(recruiter.parser_status, "parsed")
        self.assertEqual(recruiter.job_title, "Senior Backend Engineer")
        self.assertEqual(recruiter.extracted_payload["job_snapshot"]["salary_min"], 1800000.0)
        self.assertEqual(credit.parser_status, "parsed")
        self.assertEqual(credit.report_number, "CN998877")
        self.assertEqual(str(credit.report_date), "2026-03-28")
        self.assertGreaterEqual(
            DocumentParserLearningMemory.objects.filter(correction_count__gt=0).values("scope").distinct().count(),
            7,
        )
        recruiter_memory = DocumentParserLearningMemory.objects.get(
            scope="recruiter_document",
            last_resolution="accepted_correction_recruiter_document",
        )
        self.assertTrue({"salary_min", "salary_max"}.issubset(set(recruiter_memory.accepted_field_hints)))

    def test_statement_retry_creates_internal_retry_ticket_when_still_unresolved(self):
        upload = StatementUpload.objects.create(
            user=self.user,
            source="bank_statement",
            file_name="hdfc statement.pdf",
            parser_status="needs_review",
            parse_confidence=0.18,
            imported_count=0,
            extracted_payload={"background_retry": {"retry_count": 0}},
        )

        unresolved_result = type(
            "RetryResult",
            (),
            {
                "upload": upload,
                "new_import_count": 0,
                "summary": {},
            },
        )()

        with patch("alfred_ai.services.document_review.retry_statement_upload", return_value=unresolved_result):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "statement_document", "id": upload.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        ticket = SystemTicket.objects.latest("id")
        self.assertEqual(ticket.module, "expenses")
        self.assertEqual(ticket.severity, "low")
        self.assertEqual(ticket.handled_by, "alfred")
        self.assertEqual(ticket.context_payload["retry_count"], 1)
        self.assertEqual(ticket.context_payload["document_scope"], "statement_document")

    def test_document_center_delete_removes_statement_and_derived_expenses(self):
        account = BankAccount.objects.create(
            user=self.user,
            bank_name="HDFC Bank",
            account_number="50100244137504",
        )
        upload = StatementUpload.objects.create(
            user=self.user,
            bank_account=account,
            source="bank_statement",
            file_name="hdfc.pdf",
            parser_status="parsed",
            parse_confidence=0.88,
            imported_count=1,
        )
        Expense.objects.create(
            user=self.user,
            bank_account=account,
            statement_upload=upload,
            amount=450,
            classification="expense",
            category="food",
            payment_mode="UPI",
            merchant="Cafe",
            description="Cafe spend",
            raw_description="Cafe spend",
            transaction_date="2026-03-31",
            direction="debit",
            source="bank_statement",
        )

        response = self.client.delete(f"/api/documents/items/statement_document/{upload.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(StatementUpload.objects.filter(pk=upload.id).exists())
        self.assertEqual(Expense.objects.count(), 0)

    def test_document_center_delete_removes_imported_service_record_with_source_document(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa 6G",
            model_name="Activa 6G",
            vehicle_type="scooter",
            bike_class="scooter",
        )
        document = BikeDocument.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            document_type="invoice",
            parser_status="parsed",
            parse_confidence=0.8,
        )
        record = BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date="2026-03-31",
            source_document=document,
            source_mode="bill_import",
        )

        response = self.client.delete(f"/api/documents/items/vehicle_document/{document.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(BikeDocument.objects.filter(pk=document.id).exists())
        self.assertFalse(BikeServiceRecord.objects.filter(pk=record.id).exists())

    def test_vehicle_document_correction_updates_linked_service_record_fields(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa 6G",
            model_name="Activa 6G",
            vehicle_type="scooter",
            bike_class="scooter",
        )
        document = BikeDocument.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            document_type="invoice",
            parser_status="needs_review",
            parse_confidence=0.38,
            extracted_payload={"service_payload": {"service_center": "Old Workshop"}},
        )
        record = BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date="2026-03-20",
            service_center="Old Workshop",
            source_document=document,
            source_mode="bill_import",
        )

        response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "vehicle_document",
                "id": document.id,
                "corrections": {
                    "service_date": "2026-03-31",
                    "service_center": "Jagadamba Automobiles",
                    "service_type": "periodic_service",
                    "odometer_km": 26021,
                    "cost": 2432.92,
                    "extracted_work_summary": "Engine oil, chain cleaning, brake inspection",
                    "parts_items": [{"description": "Brake Pad Kit", "customer_amount": 820}],
                    "labour_items": [{"description": "Periodic Service Labour", "customer_amount": 640}],
                    "line_item_count": 2,
                    "systems_impacted": ["brakes", "engine"],
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        record.refresh_from_db()
        self.assertEqual(document.parser_status, "parsed")
        self.assertEqual(document.extracted_payload["service_payload"]["service_center"], "Jagadamba Automobiles")
        self.assertEqual(record.service_center, "Jagadamba Automobiles")
        self.assertEqual(str(record.service_date), "2026-03-31")
        self.assertEqual(record.odometer_km, 26021)
        self.assertAlmostEqual(record.cost, 2432.92)
        self.assertIn("brake inspection", record.extracted_work_summary.lower())
        self.assertEqual(record.parsed_payload["service_payload"]["parts_items"][0]["description"], "Brake Pad Kit")
        self.assertEqual(record.parsed_payload["service_payload"]["labour_items"][0]["description"], "Periodic Service Labour")
        self.assertEqual(record.parsed_payload["service_payload"]["line_item_count"], 2)
        self.assertEqual(record.parsed_payload["service_payload"]["systems_impacted"], ["brakes", "engine"])
        self.assertEqual(record.parsed_payload["review_trace"]["review_queue_resolution"], "accepted_correction")
        self.assertIn("service_center", record.parsed_payload["review_trace"]["corrected_fields"])
        self.assertEqual(
            record.parsed_payload["review_trace"]["accepted_corrections"]["service_center"],
            "Jagadamba Automobiles",
        )

    def test_retry_endpoint_supports_loan_documents(self):
        upload = LoanImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("sanction-letter.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="sanction-letter.pdf",
            parser_status="needs_review",
            parse_confidence=0.22,
            extracted_payload={},
            summary="Needs review",
        )

        with patch(
            "alfred_ai.services.document_review.loan_pdf_parser.parse_document",
            return_value={
                "document_type": "sanction_letter",
                "confidence": 0.84,
                "extracted_text": "Axis Bank sanction letter",
                "loans": [
                    {
                        "lender": "Axis Bank",
                        "loan_type": "personal",
                        "loan_account_number": "AXIS-PL-001",
                        "principal": 250000,
                        "interest_rate": 11.5,
                        "emi": 8450,
                        "tenure_months": 36,
                        "remaining_balance": 250000,
                        "start_date": "2026-03-30",
                    }
                ],
            },
        ):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "loan_document", "id": upload.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        upload.refresh_from_db()
        self.assertEqual(upload.parser_status, "parsed")
        self.assertEqual(upload.linked_loans.count(), 1)
        self.assertTrue(Loan.objects.filter(user=self.user, loan_account_number="AXIS-PL-001").exists())
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="loan_document",
                event_type="retry_document",
            ).exists()
        )

    def test_repeated_loan_retry_escalates_to_developer_ticket(self):
        upload = LoanImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("loan-book.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="loan-book.pdf",
            parser_status="needs_review",
            parse_confidence=0.22,
            extracted_payload={"background_retry": {"retry_count": 5}},
            summary="Needs review",
        )

        with patch(
            "alfred_ai.services.document_review.loan_pdf_parser.parse_document",
            return_value={
                "document_type": "loan_statement",
                "confidence": 0.31,
                "extracted_text": "Loan statement without row table",
                "loans": [],
            },
        ):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "loan_document", "id": upload.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        ticket = SystemTicket.objects.latest("id")
        self.assertEqual(ticket.module, "loans")
        self.assertEqual(ticket.severity, "high")
        self.assertEqual(ticket.handled_by, "developer")
        self.assertEqual(ticket.status, "open")
        self.assertEqual(ticket.context_payload["retry_count"], 6)
        self.assertEqual(ticket.context_payload["document_scope"], "loan_document")

    def test_review_queue_accepts_loan_closure_correction_and_marks_loan_foreclosure_pending(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISCLOSE123",
            principal=220000,
            interest_rate=12.0,
            emi=7100,
            tenure_months=36,
            remaining_balance=84500,
            start_date="2025-04-01",
        )
        document = LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="closure.pdf",
            extracted_text="Axis Bank loan closure letter for account AXISCLOSE123. Full and final settlement completed.",
            extracted_payload={},
            parser_status="needs_review",
            parse_confidence=0.33,
            verification_status="pending",
        )

        response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "loan_closure_document",
                "id": document.id,
                "corrections": {
                    "loan_account_number": "AXISCLOSE123",
                    "matched_keyword": "Full And Final",
                    "closure_amount": 84500,
                    "closure_date": "2026-03-29",
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        loan.refresh_from_db()
        snapshot = LoanForeclosureSnapshot.objects.get(closure_document=document)
        self.assertEqual(document.verification_status, "verified")
        self.assertEqual(document.parser_status, "parsed")
        self.assertEqual(loan.status, "foreclosure_pending")
        self.assertFalse(loan.is_active)
        self.assertEqual(snapshot.reconciliation_status, "unmatched")
        self.assertEqual(snapshot.matched_payment_total, 0.0)

    def test_retry_endpoint_supports_loan_closure_documents(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISFORE123",
            principal=180000,
            interest_rate=11.5,
            emi=6400,
            tenure_months=30,
            remaining_balance=62000,
            start_date="2025-06-01",
        )
        document = LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("no-due.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="no-due.pdf",
            extracted_payload={"background_retry": {"retry_count": 0}},
            parser_status="needs_review",
            parse_confidence=0.24,
            verification_status="pending",
        )

        with patch(
            "alfred_ai.services.document_review.loan_closure_parser.parse_document",
            return_value={
                "payload": {
                    "loan_account_number": "AXISFORE123",
                    "closure_amount": 62000,
                    "closure_date": "2026-03-30",
                    "matched_keyword": "No Due",
                },
                "extracted_text": "Axis Bank no due certificate for loan account AXISFORE123.",
                "confidence": 0.86,
                "parser_status": "parsed",
                "parser_notes": "Recovered closure details.",
            },
        ):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "loan_closure_document", "id": document.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        loan.refresh_from_db()
        snapshot = LoanForeclosureSnapshot.objects.get(closure_document=document)
        self.assertEqual(document.verification_status, "verified")
        self.assertEqual(loan.status, "foreclosure_pending")
        self.assertFalse(loan.is_active)
        self.assertEqual(snapshot.reconciliation_status, "unmatched")
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="loan_closure_document",
                event_type="retry_document",
            ).exists()
        )

    def test_review_queue_accepts_investment_correction_and_links_holding(self):
        document = InvestmentImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("portfolio.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="portfolio.pdf",
            broker_name="Groww",
            parser_status="needs_review",
            parse_confidence=0.25,
            extracted_payload={},
            summary="Needs review",
        )

        response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "investment_document",
                "id": document.id,
                "corrections": {
                    "broker_name": "Groww",
                    "asset_name": "Axis Bluechip Fund",
                    "asset_type": "mutual_fund",
                    "account_number": "FOLIO12345",
                    "invested_amount": 50000,
                    "current_value": 56200,
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.parser_status, "parsed")
        self.assertEqual(document.linked_investments.count(), 1)
        investment = Investment.objects.get(user=self.user, asset_name="Axis Bluechip Fund")
        self.assertEqual(investment.current_value, 56200)

    def test_retry_endpoint_supports_investment_documents(self):
        document = InvestmentImportDocument.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile("holdings.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            file_name="holdings.pdf",
            broker_name="Zerodha",
            parser_status="needs_review",
            parse_confidence=0.22,
            extracted_payload={"background_retry": {"retry_count": 0}},
            summary="Needs review",
        )

        with patch(
            "alfred_ai.services.document_review.portfolio_intelligence_service.parse_portfolio_document",
            return_value={
                "broker": "Zerodha",
                "confidence": 0.82,
                "parser_status": "parsed",
                "parser_notes": "Recovered holdings table.",
                "extracted_text": "Zerodha holdings statement",
                "summary": "1 investment extracted.",
                "investments": [
                    {
                        "asset_type": "equity",
                        "asset_name": "Infosys Ltd",
                        "institution": "Zerodha",
                        "account_number": "DEMAT12345",
                        "invested_amount": 120000,
                        "current_value": 136500,
                        "annual_return_rate": 12.5,
                    }
                ],
                "payload": {
                    "broker_name": "Zerodha",
                    "account_number": "DEMAT12345",
                    "investments": [
                        {
                            "asset_type": "equity",
                            "asset_name": "Infosys Ltd",
                            "institution": "Zerodha",
                            "account_number": "DEMAT12345",
                            "invested_amount": 120000,
                            "current_value": 136500,
                            "annual_return_rate": 12.5,
                        }
                    ],
                },
            },
        ):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "investment_document", "id": document.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.parser_status, "parsed")
        self.assertEqual(document.linked_investments.count(), 1)
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="investment_document",
                event_type="retry_document",
            ).exists()
        )

    def test_retry_endpoint_supports_resume_documents(self):
        resume = CareerResume.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile(
                "resume.html",
                b"<html><body><h1>Soura Analyst</h1><p>Data Analyst with 4 years experience in Python SQL Power BI.</p></body></html>",
                content_type="text/html",
            ),
            file_name="resume.html",
            parser_status="needs_review",
            parse_confidence=0.2,
            extracted_payload={},
            summary="Needs review",
        )

        response = self.client.post(
            "/api/documents/review-queue/retry/",
            data={"scope": "resume_document", "id": resume.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        resume.refresh_from_db()
        self.assertEqual(resume.parser_status, "parsed")
        self.assertGreaterEqual(resume.parse_confidence, 0.65)
        self.assertIn("Python", resume.extracted_payload["skills"])
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="resume_document",
                event_type="retry_document",
            ).exists()
        )

    def test_review_queue_accepts_recruiter_document_correction(self):
        analysis = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="Recruiter Mail Intake",
            source_document_name="recruiter_message.txt",
            job_url="https://alfred.local/recruiter/demo",
            apply_url="https://alfred.local/recruiter/demo",
            parser_status="needs_review",
            parse_confidence=0.28,
            extracted_text="Role for analyst with SQL",
            summary="Needs review",
            extracted_payload={
                "source_kind": "recruiter_message",
                "job_snapshot": {
                    "title": "",
                    "company": "",
                    "location": "",
                    "required_skills": ["SQL"],
                    "experience_years": 0,
                    "salary_min": 0,
                    "salary_max": 0,
                    "salary_currency": "INR",
                    "salary_period": "annual",
                    "employment_type": "Full-time",
                    "source_kind": "recruiter_message",
                },
            },
        )

        response = self.client.post(
            "/api/documents/review-queue/resolve/",
            data={
                "scope": "recruiter_document",
                "id": analysis.id,
                "corrections": {
                    "job_title": "Senior Data Analyst",
                    "company": "Example Analytics",
                    "location": "Bengaluru",
                    "experience_years": 4,
                    "salary_min": 1800000,
                    "salary_max": 2200000,
                },
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        analysis.refresh_from_db()
        self.assertEqual(analysis.parser_status, "parsed")
        self.assertEqual(analysis.job_title, "Senior Data Analyst")
        self.assertEqual(analysis.company, "Example Analytics")

    def test_retry_endpoint_supports_recruiter_documents(self):
        analysis = CareerJobAnalysis.objects.create(
            user=self.user,
            source_name="Recruiter Mail Intake",
            source_document_name="recruiter_message.txt",
            job_url="https://alfred.local/recruiter/demo",
            apply_url="https://alfred.local/recruiter/demo",
            parser_status="needs_review",
            parse_confidence=0.22,
            extracted_text="Please review the JD.",
            summary="Needs review",
            extracted_payload={
                "source_kind": "recruiter_message",
                "intake_message_text": "\n".join(
                    [
                        "Role: Senior Data Analyst",
                        "Company: Example Analytics",
                        "Location: Bengaluru",
                        "Need Python, SQL, Power BI",
                        "Compensation: 18-22 LPA",
                        "Apply here: https://example.com/jobs/1",
                    ]
                ),
                "intake_combined_text": "\n".join(
                    [
                        "Role: Senior Data Analyst",
                        "Company: Example Analytics",
                        "Location: Bengaluru",
                        "Need Python, SQL, Power BI",
                        "Compensation: 18-22 LPA",
                        "Apply here: https://example.com/jobs/1",
                    ]
                ),
                "job_snapshot": {
                    "source_kind": "recruiter_message",
                    "required_skills": [],
                },
                "background_retry": {"retry_count": 0},
            },
        )

        response = self.client.post(
            "/api/documents/review-queue/retry/",
            data={"scope": "recruiter_document", "id": analysis.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        analysis.refresh_from_db()
        self.assertEqual(analysis.parser_status, "parsed")
        self.assertEqual(analysis.company, "Example Analytics")
        self.assertIn("Data Analyst", analysis.job_title)
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="recruiter_document",
                event_type="retry_document",
            ).exists()
        )

    def test_retry_endpoint_supports_credit_reports(self):
        upload = CreditReportUpload.objects.create(
            user=self.user,
            uploaded_file=SimpleUploadedFile(
                "cibil-report.pdf",
                self._build_credit_pdf(),
                content_type="application/pdf",
            ),
            file_name="cibil-report.pdf",
            parser_status="needs_review",
            parse_confidence=0.18,
            extracted_payload={},
            summary="Needs review",
        )

        response = self.client.post(
            "/api/documents/review-queue/retry/",
            data={"scope": "credit_report", "id": upload.id},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        upload.refresh_from_db()
        self.assertEqual(upload.parser_status, "parsed")
        self.assertTrue(CreditScore.objects.filter(user=self.user, score=782).exists())
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="credit_report",
                event_type="retry_document",
            ).exists()
        )

    def test_retry_endpoint_supports_vehicle_documents(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa 6G",
            model_name="Activa 6G",
            vehicle_type="scooter",
            bike_class="scooter",
            vehicle_number="KA01AB1234",
        )
        document = BikeDocument.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            vehicle_number=profile.vehicle_number,
            document_type="insurance",
            document_file=SimpleUploadedFile("insurance.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            parser_status="needs_review",
            parse_confidence=0.24,
            extracted_payload={},
        )

        parsed = ParsedDocument(
            document_type="insurance",
            title="Insurance Policy POLICY-123",
            confidence=0.86,
            fields={
                "issuer": "Example Insurance",
                "document_number": "POLICY-123",
                "vehicle_number": "KA01AB1234",
                "issue_date": "2026-03-01",
                "expiry_date": "2027-02-28",
                "amount": 3200.0,
            },
            parser_status="parsed",
            parser_notes="Parsed insurance document.",
            source_text="Insurance Policy Policy No POLICY-123 KA01AB1234",
            service_payload={},
        )

        with patch("alfred_ai.services.document_review.bike_document_ai.parse", return_value=parsed), patch(
            "alfred_ai.services.document_review.bike_document_ai.verify_relevance",
            return_value={"accepted": True, "score": 0.92, "reasons": ["Vehicle number matched."]},
        ):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "vehicle_document", "id": document.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        document.refresh_from_db()
        self.assertEqual(document.parser_status, "parsed")
        self.assertEqual(document.document_number, "POLICY-123")
        self.assertTrue(
            OperationalLog.objects.filter(
                user=self.user,
                scope="vehicle_document",
                event_type="retry_document",
            ).exists()
        )

    def test_vehicle_retry_updates_existing_service_record_review_trace_without_new_service_payload(self):
        profile = BikeProfile.objects.create(
            user=self.user,
            display_name="Honda Activa 6G",
            model_name="Activa 6G",
            vehicle_type="scooter",
            bike_class="scooter",
            vehicle_number="KA01AB1234",
        )
        document = BikeDocument.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            vehicle_number=profile.vehicle_number,
            document_type="invoice",
            document_file=SimpleUploadedFile("invoice.pdf", b"%PDF-1.4 fake", content_type="application/pdf"),
            parser_status="needs_review",
            parse_confidence=0.31,
            extracted_payload={
                "service_payload": {"service_center": "Old Workshop", "cost": 1850.0},
                "background_retry": {"retry_count": 0},
                "extraction_review": {
                    "best_method": "rapidocr_image",
                    "ocr_pages": [{"page": 1, "preview": "blurred invoice", "regions": []}],
                },
            },
        )
        record = BikeServiceRecord.objects.create(
            user=self.user,
            bike_profile=profile,
            bike_name=profile.display_name,
            service_date="2026-03-20",
            service_center="Old Workshop",
            cost=1850.0,
            source_document=document,
            source_mode="bill_import",
            parsed_payload={"service_payload": {"service_center": "Old Workshop", "cost": 1850.0}},
        )

        parsed = ParsedDocument(
            document_type="invoice",
            title="Invoice EDGE-2002",
            confidence=0.54,
            fields={
                "issuer": "Jagadamba Automobiles",
                "document_number": "EDGE-2002",
                "vehicle_number": "KA01AB1234",
            },
            parser_status="needs_review",
            parser_notes="Invoice still needs review after retry.",
            source_text="Blurred invoice text",
            service_payload={},
            review_payload={
                "extraction_method": "rapidocr_image",
                "extraction_review": {
                    "best_method": "rapidocr_image",
                    "ocr_pages": [{"page": 1, "preview": "blurred invoice", "regions": []}],
                    "recovery_steps": [{"step": "image_bytes_fallback", "status": "recovered"}],
                },
            },
        )

        with patch("alfred_ai.services.document_review.bike_document_ai.parse", return_value=parsed), patch(
            "alfred_ai.services.document_review.bike_document_ai.verify_relevance",
            return_value={"accepted": True, "score": 0.76, "reasons": ["Vehicle number matched."]},
        ):
            response = self.client.post(
                "/api/documents/review-queue/retry/",
                data={"scope": "vehicle_document", "id": document.id},
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        record.refresh_from_db()
        self.assertEqual(record.service_center, "Old Workshop")
        self.assertEqual(record.parsed_payload["review_trace"]["document_parser_status"], "needs_review")
        self.assertEqual(record.parsed_payload["review_trace"]["background_retry"]["retry_count"], 1)
        self.assertEqual(record.parsed_payload["review_trace"]["background_retry"]["resolution"], "still_needs_review")
        self.assertEqual(record.parsed_payload["review_trace"]["extraction_method"], "rapidocr_image")
        self.assertEqual(record.parsed_payload["review_trace"]["extraction_review"]["ocr_pages"][0]["page"], 1)

    def test_document_diagnostics_endpoint_and_client_log_capture(self):
        response = self.client.post(
            "/api/operational/logs/client/",
            data={
                "module": "documents",
                "category": "visualization",
                "scope": "document_center",
                "event_type": "render_failure",
                "severity": "error",
                "message": "Chart root was missing.",
                "payload": {"page_path": "/documents/"},
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        diagnostics = self.client.get("/api/documents/diagnostics/")
        self.assertEqual(diagnostics.status_code, 200)
        self.assertEqual(diagnostics.json()["results"][0]["event_type"], "render_failure")

    def _build_credit_pdf(self) -> bytes:
        document = fitz.open()
        page = document.new_page()
        point = fitz.Point(72, 72)
        for line in [
            "TransUnion CIBIL Credit Report",
            "Credit Score: 782",
            "Consumer Name: Soura Sarkar",
            "Report Number: CIBIL-2026-001",
            "Report Date: 30/03/2026",
            "Total Accounts: 5",
            "Active Accounts: 4",
            "Closed Accounts: 1",
            "Delinquent Accounts: 0",
            "Credit Utilization: 18%",
            "Total Credit Limit: INR 500000",
        ]:
            page.insert_text(point, line, fontsize=12)
            point = fitz.Point(point.x, point.y + 22)
        return document.tobytes()
