"""CAREER2-002: attachment manifest, explicit per-email confirmation, stale review rejection and retry without resending."""
import hashlib
import smtplib
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
SMTP = {**MAILBOX, "ALFRED_SMTP_BACKEND": "django.core.mail.backends.smtp.EmailBackend", "ALFRED_SMTP_SSL": False}


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
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.open", side_effect=OSError("refused")):
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

    def test_csrf_and_hostile_header_values_cannot_send_or_add_recipients(self):
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.owner)
        for action in ("review", "send"):
            self.assertEqual(strict.post(self.base + action + "/", {**EMAIL, "confirm": True}, content_type="application/json").status_code, 403)
        for to in ("hr@synthetic.example.test, extra@evil.example.test", "hr@synthetic.example.test\nBcc: extra@evil.example.test"):
            self.assertIn("Enter one valid recipient email address.", self.reviewed(to=to)["blockers"])
        review = self.reviewed(subject="Application\r\nBcc: extra@evil.example.test")
        self.assertEqual(review["subject"], "Application Bcc: extra@evil.example.test")  # one header line, never a new header
        sent = self.post("send", **{**EMAIL, "subject": "Application\r\nBcc: extra@evil.example.test"}, confirmation=review["confirmation"], confirm=True)
        self.assertLess(sent.status_code, 300, sent.content)
        self.assertEqual([message.recipients() for message in mail.outbox], [["hr@synthetic.example.test"]])
        self.assertEqual(len(mail.outbox), 1)

    def test_recruiter_reply_draft_cannot_be_sent_until_every_answer_is_filled(self):
        self.item.extracted_payload = {**self.item.extracted_payload, "source_kind": "recruiter_message",
                                       "intake_message_text": "Please share your CV and expected CTC. What is your notice period?"}
        self.item.save(update_fields=["extracted_payload"])
        draft = self.client.get(f"/api/career/job-analyses/{self.item.pk}/kit/", {"type": "email", "kind": "recruiter_reply"}).json()
        review = self.reviewed(subject=draft["subject"], body=draft["text"])
        self.assertFalse(review["ready"])
        self.assertIn("Pay: [your expected pay", draft["text"])
        self.assertTrue(any(item.startswith("Fill or remove the bracketed parts") for item in review["blockers"]))
        self.assertEqual(review["confirmation"], "")
        self.assertEqual(len(mail.outbox), 0)

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

    def test_an_interrupted_send_is_not_resent_until_the_owner_checks(self):
        class Stopped(BaseException):
            """ALFRED stopping mid-send: the mail server may or may not have taken the email."""
        token = self.reviewed()["confirmation"]
        with mock.patch("django.core.mail.backends.locmem.EmailBackend.send_messages", side_effect=Stopped()):
            with self.assertRaises(Stopped):
                self.post("send", **EMAIL, confirmation=token, confirm=True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.extracted_payload["sent_messages"][0]["status"], "sending")
        review = self.reviewed()
        self.assertTrue(review["ready"] and review["unconfirmed_send"])
        self.assertTrue(any("Sent folder" in item for item in review["warnings"]))
        refused = self.post("send", **EMAIL, confirmation=review["confirmation"], confirm=True)
        self.assertEqual(refused.status_code, 409)
        self.assertIn("Sent folder", refused.json()["detail"])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.post("send", **EMAIL, confirmation=review["confirmation"], confirm=True, resend_unconfirmed="yes").status_code, 409)
        sent = self.post("send", **EMAIL, confirmation=review["confirmation"], confirm=True, resend_unconfirmed=True)
        self.assertEqual(sent.status_code, 201, sent.content)
        self.assertEqual(len(mail.outbox), 1)
        self.item.refresh_from_db()
        self.assertEqual([item["status"] for item in self.item.extracted_payload["sent_messages"]], ["sent"])
        self.assertFalse(self.reviewed(subject="Another subject")["unconfirmed_send"])

    def smtp_send(self, **failures):
        """Django's real SMTP backend against a fake smtplib.SMTP; no connection leaves the machine."""
        server = mock.MagicMock()
        for method, error in failures.items():
            getattr(server, method).side_effect = error
        token = self.reviewed()["confirmation"]
        with override_settings(**SMTP), mock.patch("smtplib.SMTP", return_value=server):
            response = self.post("send", **EMAIL, confirmation=token, confirm=True)
        self.item.refresh_from_db()
        return response, server, [item["status"] for item in self.item.extracted_payload["sent_messages"]]

    def test_an_error_after_the_server_took_the_email_still_counts_as_sent(self):
        response, server, statuses = self.smtp_send(quit=smtplib.SMTPResponseException(421, b"closing"))
        self.assertEqual((response.status_code, statuses), (201, ["sent"]))
        self.assertEqual(server.sendmail.call_count, 1)
        self.assertTrue(any("already sent" in item for item in self.reviewed()["blockers"]))

    def test_a_connection_lost_mid_send_is_not_called_nothing_sent(self):
        response, _, statuses = self.smtp_send(sendmail=smtplib.SMTPServerDisconnected("lost"))
        self.assertEqual((response.status_code, statuses), (502, ["unknown"]))
        self.assertNotIn("Nothing was sent", response.json()["detail"])
        self.assertIn("Sent folder", response.json()["detail"])
        review = self.reviewed()
        self.assertTrue(review["unconfirmed_send"])
        self.assertTrue(any("connection to your mail server broke" in item for item in review["warnings"]))
        self.assertEqual(self.post("send", **EMAIL, confirmation=review["confirmation"], confirm=True).status_code, 409)
        self.assertEqual(len(mail.outbox), 0)
        sent = self.post("send", **EMAIL, confirmation=review["confirmation"], confirm=True, resend_unconfirmed=True)
        self.assertEqual(sent.status_code, 201, sent.content)

    def test_a_refusal_is_failed_and_can_be_retried(self):
        response, _, statuses = self.smtp_send(sendmail=smtplib.SMTPRecipientsRefused({"hr@synthetic.example.test": (550, b"no")}))
        self.assertEqual((response.status_code, statuses), (502, ["failed"]))
        self.assertIn("Nothing was sent", response.json()["detail"])
        self.assertFalse(self.reviewed()["unconfirmed_send"])

    def test_edits_made_during_the_send_are_kept(self):
        from datetime import timedelta

        def notes_saved_meanwhile(message):
            row = CareerJobAnalysis.objects.get(pk=self.item.pk)
            CareerJobAnalysis.objects.filter(pk=row.pk).update(
                extracted_payload={**row.extracted_payload, "interview_notes": {"stories": ["kept"]}},
                updated_at=row.updated_at + timedelta(seconds=1))
            return "sent"
        token = self.reviewed()["confirmation"]
        with mock.patch.object(application_send, "_deliver", side_effect=notes_saved_meanwhile):
            self.assertEqual(self.post("send", **EMAIL, confirmation=token, confirm=True).status_code, 201)
        self.item.refresh_from_db()
        payload = self.item.extracted_payload
        self.assertEqual((payload["interview_notes"], [item["status"] for item in payload["sent_messages"]]), ({"stories": ["kept"]}, ["sent"]))
