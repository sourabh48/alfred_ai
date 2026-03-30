from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

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
