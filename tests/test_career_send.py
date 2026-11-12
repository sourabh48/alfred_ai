"""CAREER2-002: attachment manifest, explicit per-email confirmation, stale review rejection and retry without resending."""
import hashlib
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.career.models import CareerJobAnalysis, CareerResume
from apps.career.services import application_send
from tests.test_career_application_kit import CV, JD, analysis

MAILBOX = dict(ALFRED_SMTP_HOST="smtp.example.test", ALFRED_SMTP_USER="owner@example.test", ALFRED_SMTP_PASSWORD="app-password",
               ALFRED_SMTP_FROM="", ALFRED_SMTP_BACKEND="django.core.mail.backends.locmem.EmailBackend")
EMAIL = {"to": "hr@synthetic.example.test", "subject": "Application: Senior Backend Engineer",
         "body": "Hello,\n\nI would like to apply.\n\nRegards,\nAsha", "attach_cv": True}


@override_settings(**MAILBOX)
class SendTests(TestCase):
    def setUp(self):
        users = get_user_model()
        self.owner, self.other = users.objects.create_user("send-owner"), users.objects.create_user("send-other")
        self.resume = CareerResume.objects.create(user=self.owner, uploaded_file=SimpleUploadedFile("cv.pdf", b"%PDF-synthetic"),
                                                  file_name="cv.pdf", parser_status="parsed", extracted_text=CV, extracted_payload={})
        self.item = CareerJobAnalysis.objects.create(user=self.owner, job_url="https://jobs.example.test/1", job_title="Senior Backend Engineer",
                                                     extracted_text=JD, extracted_payload=analysis().extracted_payload)
        self.base = f"/api/career/job-analyses/{self.item.pk}/email/"
        self.client.force_login(self.owner)

    def post(self, action, **data):
        return self.client.post(self.base + action + "/", data, content_type="application/json")

    def reviewed(self, **changes):
        response = self.post("review", **{**EMAIL, **changes})
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_review_lists_the_attachment_and_sends_nothing(self):
        review = self.reviewed()
        self.assertTrue(review["ready"])
        self.assertEqual(review["attachments"], [{"name": "cv.pdf", "bytes": 14, "sha256": hashlib.sha256(b"%PDF-synthetic").hexdigest()}])
        self.assertEqual(review["from"], "owner@example.test")
        self.assertEqual(len(mail.outbox), 0)

    def test_checklist_blocks_placeholders_bad_recipient_and_missing_mailbox(self):
        review = self.reviewed(to="not-an-email", body="Hello [name], see [your result].")
        self.assertFalse(review["ready"])
        self.assertEqual(review["confirmation"], "")
        self.assertTrue(any("valid recipient" in item for item in review["blockers"]))
        self.assertTrue(any("[name]" in item for item in review["blockers"]))
        with override_settings(ALFRED_SMTP_PASSWORD=""):
            self.assertTrue(any("Sending is off" in item for item in self.reviewed()["blockers"]))

    def test_send_needs_explicit_confirm_and_a_matching_fresh_review(self):
        token = self.reviewed()["confirmation"]
        self.assertEqual(self.post("send", **EMAIL, confirmation=token).status_code, 400)
        self.assertEqual(self.post("send", **EMAIL, confirm=True).status_code, 409)
        changed = self.post("send", **{**EMAIL, "body": EMAIL["body"] + " P.S."}, confirmation=token, confirm=True)
        self.assertEqual(changed.status_code, 409)
        self.assertIn("changed since you reviewed", changed.json()["detail"])
        with mock.patch.object(application_send, "REVIEW_SECONDS", -1):  # every review is now too old
            self.assertEqual(self.post("send", **EMAIL, confirmation=token, confirm=True).status_code, 409)
        self.assertEqual(len(mail.outbox), 0)

    def test_a_changed_cv_file_makes_the_review_stale(self):
        token = self.reviewed()["confirmation"]
        CareerResume.objects.create(user=self.owner, uploaded_file=SimpleUploadedFile("cv2.pdf", b"%PDF-newer"), file_name="cv2.pdf",
                                    parser_status="parsed", extracted_text=CV, extracted_payload={})
        self.assertEqual(self.post("send", **EMAIL, confirmation=token, confirm=True).status_code, 409)
        self.assertEqual(len(mail.outbox), 0)

    def test_confirmed_send_goes_once_and_a_retry_does_not_resend(self):
        token = self.reviewed()["confirmation"]
        first = self.post("send", **EMAIL, confirmation=token, confirm=True)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual((sent.to, sent.subject, sent.from_email), (["hr@synthetic.example.test"], EMAIL["subject"], "owner@example.test"))
        self.assertEqual(sent.attachments[0][:2], ("cv.pdf", b"%PDF-synthetic"))
        retry = self.post("send", **EMAIL, confirmation=token, confirm=True)
        self.assertEqual((retry.status_code, retry.json()["already_sent"]), (200, True))
        self.assertEqual(len(mail.outbox), 1)
        self.item.refresh_from_db()
        record = self.item.extracted_payload["sent_messages"][0]
        self.assertEqual((record["status"], record["to"], record["attachment"]), ("sent", "hr@synthetic.example.test", "cv.pdf"))
        self.assertNotIn("I would like to apply", str(self.item.extracted_payload["sent_messages"]))
        self.assertIn("job_snapshot", self.item.extracted_payload)
        self.assertTrue(any("already sent" in item for item in self.reviewed()["blockers"]))

    def test_mail_server_failure_is_recorded_and_can_be_retried(self):
        token = self.reviewed(attach_cv=False)["confirmation"]
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=OSError("refused")):
            failed = self.post("send", **{**EMAIL, "attach_cv": False}, confirmation=token, confirm=True)
        self.assertEqual(failed.status_code, 502)
        self.item.refresh_from_db()
        self.assertEqual(self.item.extracted_payload["sent_messages"][0]["status"], "failed")
        token = self.reviewed(attach_cv=False)["confirmation"]
        self.assertEqual(self.post("send", **{**EMAIL, "attach_cv": False}, confirmation=token, confirm=True).status_code, 201)
        self.assertEqual(len(mail.outbox), 1)
        self.item.refresh_from_db()
        self.assertEqual([item["status"] for item in self.item.extracted_payload["sent_messages"]], ["sent"])

    def test_owner_scope_and_unknown_action(self):
        self.client.force_login(self.other)
        self.assertEqual(self.post("review", **EMAIL).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.post("blast", **EMAIL).status_code, 404)

    def test_missing_cv_file_blocks_only_when_attaching(self):
        self.resume.uploaded_file.storage.delete(self.resume.uploaded_file.name)
        self.assertTrue(any("no longer keeps" in item for item in self.reviewed()["blockers"]))
        self.assertTrue(self.reviewed(attach_cv=False)["ready"])

    def test_a_concurrent_change_stops_the_send(self):
        from datetime import timedelta
        token = self.reviewed()["confirmation"]
        real = application_send.review

        def changed_elsewhere(*args, **kwargs):
            CareerJobAnalysis.objects.filter(pk=self.item.pk).update(updated_at=self.item.updated_at + timedelta(seconds=5))
            return real(*args, **kwargs)
        with mock.patch.object(application_send, "review", side_effect=changed_elsewhere):
            response = self.post("send", **EMAIL, confirmation=token, confirm=True)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(len(mail.outbox), 0)
