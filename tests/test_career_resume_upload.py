from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from unittest.mock import patch

from alfred_ai.services.document_extraction import ExtractedDocumentText
from apps.career.models import CareerResume


class CareerResumeUploadTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="career_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def test_html_resume_upload_is_parsed(self):
        resume = SimpleUploadedFile(
            "resume.html",
            b"""
            <html><body>
            <h1>Soura Analyst</h1>
            <p>Data Analyst with 4 years experience in Python, SQL, Excel, Power BI and Tableau.</p>
            <p>Email: soura@example.com</p>
            <p>Phone: 9876543210</p>
            <p>Built dashboards and improved reporting efficiency by 25%.</p>
            </body></html>
            """,
            content_type="text/html",
        )

        response = self.client.post("/api/career/resumes/upload/", data={"resume": resume})

        self.assertEqual(response.status_code, 201)
        payload = response.json()["resume"]
        self.assertEqual(payload["parser_status"], "parsed")
        self.assertGreaterEqual(payload["parse_confidence"], 0.65)
        self.assertIn("Python", payload["extracted_payload"]["skills"])

    def test_weak_pdf_resume_is_stored_for_review(self):
        resume = SimpleUploadedFile(
            "resume.pdf",
            b"not-a-real-pdf",
            content_type="application/pdf",
        )

        response = self.client.post("/api/career/resumes/upload/", data={"resume": resume})

        self.assertEqual(response.status_code, 201)
        payload = response.json()["resume"]
        self.assertEqual(payload["parser_status"], "needs_review")
        self.assertLess(payload["parse_confidence"], 0.65)
        stored = CareerResume.objects.get()
        self.assertEqual(stored.parser_status, "needs_review")

    @patch("apps.career.services.resume_intelligence.extract_document_text")
    def test_scanned_resume_ocr_text_is_parsed_with_role_and_skills(self, mock_extract_document_text):
        mock_extract_document_text.return_value = ExtractedDocumentText(
            text="""
            SOURABH SARKAR
            Java Backend Developer
            sourabh.654321@outlook.com
            7077927159
            https://www.linkedin.com/in/sourabhsarkar
            Professional Summary
            Java Backend Developer with 5 years of experience building microservices using Spring Boot,
            Spring Cloud, Kafka, Oracle, MongoDB, Jenkins, Maven, REST API, SOAP, JUnit and Mockito.
            Built backend services, improved platform reliability by 25%, and optimized release workflows.
            """,
            method="isolated_rapidocr_pdf",
            confidence=0.78,
            notes=["OCR fallback recovered text using isolated_rapidocr_pdf."],
            review_payload={
                "ocr_pages": [
                    {
                        "page": 1,
                        "width": 1200,
                        "height": 1700,
                        "preview": "SOURABH SARKAR Java Backend Developer",
                        "line_count": 2,
                        "regions": [
                            {
                                "text": "SOURABH SARKAR",
                                "confidence": 0.98,
                                "bbox": [[10, 10], [220, 10], [220, 36], [10, 36]],
                                "origin": "isolated_rapidocr_pdf",
                            }
                        ],
                    }
                ]
            },
        )
        resume = SimpleUploadedFile(
            "resume.pdf",
            b"fake-image-pdf",
            content_type="application/pdf",
        )

        response = self.client.post("/api/career/resumes/upload/", data={"resume": resume})

        self.assertEqual(response.status_code, 201)
        payload = response.json()["resume"]
        self.assertEqual(payload["parser_status"], "parsed")
        self.assertGreaterEqual(payload["parse_confidence"], 0.65)
        self.assertEqual(payload["extracted_payload"]["role"], "Java Backend Developer")
        self.assertGreaterEqual(payload["extracted_payload"]["experience_years"], 5.0)
        self.assertIn("Java", payload["extracted_payload"]["skills"])
        self.assertIn("Spring Boot", payload["extracted_payload"]["skills"])
        self.assertIn("Kafka", payload["extracted_payload"]["skills"])
        self.assertEqual(payload["extracted_payload"]["extraction_method"], "isolated_rapidocr_pdf")
        self.assertEqual(payload["extracted_payload"]["extraction_review"]["ocr_pages"][0]["page"], 1)
        self.assertNotIn("OCR fallback is not active", payload["weaknesses"])
