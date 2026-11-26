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

    def test_weak_resume_extraction_never_fills_the_profile(self):
        from apps.career.models import CareerProfile
        from apps.career.services.resume_intelligence import ParsedResume

        weak = ParsedResume("needs_review", 0.4, "Python SQL", {"role": "Guessed Role", "experience_years": 9, "skills": ["Python", "SQL"]}, "", [], [])
        with patch("apps.career.views.resume_intelligence.parse", return_value=weak):
            response = self.client.post("/api/career/resumes/upload/", data={"resume": SimpleUploadedFile("resume.pdf", b"x", content_type="application/pdf")})
        self.assertEqual(response.status_code, 201)
        self.assertIn("profile was not changed", response.json()["detail"])
        profile = CareerProfile.objects.get(user=self.user)
        self.assertNotEqual(profile.role, "Guessed Role")
        self.assertFalse(profile.experience_years)
        self.assertNotIn("Python", profile.skills or "")
        self.assertEqual(CareerResume.objects.get().extracted_payload["skills"], ["Python", "SQL"])  # kept for review

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


class CareerResumeUseDetailsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="career_owner", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

    def resume(self, user, status="needs_review", payload=None):
        return CareerResume.objects.create(user=user, file_name="resume.pdf", parser_status=status, parse_confidence=0.4,
                                           extracted_payload={"role": "Data Analyst", "experience_years": 4, "skills": ["Python", "SQL"]} if payload is None else payload)

    def test_owner_confirmation_fills_only_empty_fields_and_is_recorded(self):
        from apps.career.models import CareerProfile

        CareerProfile.objects.create(user=self.user, role="Owner Typed Role", experience_years=0, skills="Excel")
        resume = self.resume(self.user)
        response = self.client.post(f"/api/career/resumes/{resume.pk}/use-details/", data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 200)
        profile = CareerProfile.objects.get(user=self.user)
        self.assertEqual(profile.role, "Owner Typed Role")  # owner-entered value kept
        self.assertEqual(profile.experience_years, 4)
        self.assertTrue(all(skill in profile.skills for skill in ("Excel", "Python", "SQL")))
        resume.refresh_from_db()
        self.assertTrue(resume.extracted_payload["profile_confirmed_at"])
        again = self.client.post(f"/api/career/resumes/{resume.pk}/use-details/", data="{}", content_type="application/json")
        self.assertEqual(again.status_code, 200)
        self.assertEqual(CareerProfile.objects.get(user=self.user).skills, profile.skills)  # replay changes nothing

    def test_other_owners_clean_and_empty_resumes_are_refused(self):
        from apps.career.models import CareerProfile

        other = get_user_model().objects.create_user(username="career_other", password="Pass12345!")
        foreign = self.resume(other)
        self.assertEqual(self.client.post(f"/api/career/resumes/{foreign.pk}/use-details/").status_code, 404)
        self.assertFalse(CareerProfile.objects.filter(user=other).exists())
        self.assertEqual(self.client.post(f"/api/career/resumes/{self.resume(self.user, status='parsed').pk}/use-details/").status_code, 409)
        self.assertEqual(self.client.post(f"/api/career/resumes/{self.resume(self.user, payload={}).pk}/use-details/").status_code, 400)
        self.client.logout()
        self.assertIn(self.client.post(f"/api/career/resumes/{foreign.pk}/use-details/").status_code, (401, 403))

    def test_confirmation_keeps_every_owner_skill_and_refreshes_the_dashboard_key(self):
        from apps.career.models import CareerProfile

        owner_skills = [f"Skill{number}" for number in range(32)]
        CareerProfile.objects.create(user=self.user, role="Owner Role", experience_years=2, skills=", ".join(owner_skills))
        resume = self.resume(self.user)
        before = resume.updated_at
        self.assertEqual(self.client.post(f"/api/career/resumes/{resume.pk}/use-details/").status_code, 200)
        saved = [item.strip() for item in CareerProfile.objects.get(user=self.user).skills.split(",")]
        self.assertEqual(saved, owner_skills)  # nothing dropped; the list was already at the cap, so nothing new was added
        resume.refresh_from_db()
        self.assertGreater(resume.updated_at, before)


class CvExperienceTests(TestCase):
    """Years worked come from the CV's job dates; the CV's own "N years" claim is checked against them."""

    CV = ("Summary\nJava backend developer with 4+ years of experience in Spring Boot.\n"
          "Work Experience\nT ata Consultancy ServicesJune 2022 - Present\nSystem Engineer\n"
          "Infosys Limited\nJan 2020 – Mar 2021\nProject: payments, Feb 2020 - Jun 2020\n"
          "Education\nB.Tech, 2015 - 2019\n")

    def test_job_dates_are_counted_once_and_education_is_left_out(self):
        from datetime import date
        from apps.career.services.resume_intelligence import experience_from_cv
        found = experience_from_cv(self.CV, date(2026, 11, 26))
        # Jan 2020-Mar 2021 is 15 months (the project inside it counts once), Jun 2022-Nov 2026 is 54.
        self.assertEqual(found, {"years": 5.8, "months": 69, "stated_years": 4.0, "periods": [
            {"where": "Tata Consultancy Services", "dates": "June 2022 - Present", "months": 54},
            {"where": "Infosys Limited", "dates": "Jan 2020 – Mar 2021", "months": 15},
            {"where": "Project: payments", "dates": "Feb 2020 - Jun 2020", "months": 5}]})
        self.assertIsNone(experience_from_cv("Education\nB.Tech, 2015 - 2019\n", date(2026, 11, 26)))  # unknown, not zero

    def test_dashboard_warns_when_the_cv_claim_or_profile_is_stale(self):
        from datetime import date
        from apps.career.models import CareerProfile
        user = get_user_model().objects.create_user(username="cv_years")
        CareerProfile.objects.create(user=user, role="Java Backend Developer", experience_years=5, skills="Java")
        CareerResume.objects.create(user=user, file_name="cv.pdf", parser_status="parsed", extracted_text=self.CV)
        client = Client()
        client.force_login(user)
        with patch("apps.career.views.timezone.localdate", return_value=date(2026, 11, 26)):
            check = client.get("/api/career/dashboard/").json()["experience_check"]
        self.assertEqual(check["years"], 5.8)
        self.assertEqual(len(check["warnings"]), 2)
        self.assertIn("Your CV says 4+ years of experience, but its job dates add up to 5.8 years as of November 2026. Update the CV.",
                      check["warnings"][0])
        self.assertIn("Your profile says 5 years", check["warnings"][1])
        self.assertEqual(check["suggested_profile_years"], 5.8)
        self.assertEqual(CareerProfile.objects.get(user=user).experience_years, 5)  # only the owner's button changes it
