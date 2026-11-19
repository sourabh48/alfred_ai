"""Career email from each person's own sign-in address (owner decision 2026-11-19): the person ticks one of their own
verified addresses, the address's own provider (Google or Microsoft) grants sending and, if ticked, reading; nothing is
typed and only an encrypted refresh token is kept. Providers are faked; no network."""
import base64
import json
import os
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage
from django.test import TestCase

from alfred_ai.services import social_login
from alfred_ai.services.public_http import PublicHTTPError
from apps.career.services import career_mail

KEYS = {"ALFRED_GOOGLE_CLIENT_ID": "x-google-id", "ALFRED_GOOGLE_CLIENT_SECRET": "x-google-secret",
        "ALFRED_MICROSOFT_CLIENT_ID": "x-ms-id", "ALFRED_MICROSOFT_CLIENT_SECRET": "x-ms-secret-value"}


class Provider:
    """Token, userinfo, Gmail and Graph endpoints, recording every call."""
    def __init__(self, email, sub, scope, refresh="lasting-secret", fail=None):
        self.email, self.sub, self.scope, self.refresh, self.fail, self.calls = email, sub, scope, refresh, fail, []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url in (social_login.PROVIDERS["google"][2], social_login.PROVIDERS["microsoft"][2]):
            body = {"access_token": "short-lived", "scope": self.scope, **({"refresh_token": self.refresh} if self.refresh else {})}
        elif url.endswith("/userinfo"):
            body = {"sub": self.sub, "email": self.email, "email_verified": True}
        elif self.fail:
            raise PublicHTTPError(self.fail)
        elif "/mailFolders/inbox/messages" in url:
            body = {"value": [{"from": {"emailAddress": {"name": "Priya", "address": "priya@syntheticpay.com"}}, "subject": "Next steps",
                               "receivedDateTime": "2026-11-18T09:00:00Z", "body": {"content": "Please share your\r\n availability."}}]}
        else:
            body = {"id": "synthetic"}
        return SimpleNamespace(status=202 if url.endswith("/sendMail") else 200, json=lambda: body)


class CareerMailTests(TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        for env in (KEYS, {"ALFRED_DATA_DIR": folder.name}):
            p = patch.dict(os.environ, env)
            p.start()
            self.addCleanup(p.stop)
        self.owner = get_user_model().objects.create_user("mail-owner", password="pw-12345678")
        self.owner.email_identities.create(provider="google", subject="g-1", email="owner@gmail.com")
        self.owner.email_identities.create(provider="microsoft", subject="m-1", email="owner@outlook.com")
        self.owner.email_identities.create(provider="github", subject="gh-1", email="owner@example.org")
        self.client.force_login(self.owner)

    def choose(self, provider, email, fake):
        start = self.client.get(f"/auth/{provider}/start/", {"purpose": "mail", "email": email})
        query = parse_qs(urlsplit(start["Location"]).query)
        with patch.object(social_login.public_http, "request", fake):
            done = self.client.get(f"/auth/{provider}/callback/", {"code": "c", "state": query["state"][0]})
        return query, done

    def mail_status(self):
        return self.client.get("/api/settings/online-services/").json()["mail"]

    def test_the_choices_are_the_person_s_own_sign_in_addresses(self):
        found = {c["email"]: (c["via"], c["can_send"], c["signed_in_with"]) for c in career_mail.choices(self.owner)}
        self.assertEqual(found, {"owner@gmail.com": ("google", True, ["Google"]), "owner@outlook.com": ("microsoft", True, ["Microsoft"]),
                                 "owner@example.org": ("", False, ["GitHub"])})
        # A GitHub address at Gmail sends through Google, which proves the mailbox again when it is chosen.
        other = get_user_model().objects.create_user("mail-other")
        other.email_identities.create(provider="github", subject="gh-2", email="dev@gmail.com")
        self.assertEqual([(c["via"], c["can_send"]) for c in career_mail.choices(other)], [("google", True)])
        # Someone else's address, or one no mail service sends from, cannot even start.
        for email, provider in (("dev@gmail.com", "google"), ("owner@example.org", "github"), ("owner@gmail.com", "microsoft")):
            with self.subTest(email=email):
                response = self.client.get(f"/auth/{provider}/start/", {"purpose": "mail", "email": email})
                self.assertEqual(response["Location"], "/settings/#settingsCareerMail")
        self.assertIn("Choose one of your own sign-in addresses", self.mail_status()["error"])

    def test_choosing_gmail_asks_google_to_send_and_read_as_that_address_and_keeps_only_an_encrypted_token(self):
        query, done = self.choose("google", "owner@gmail.com", Provider("owner@gmail.com", "g-1", f"openid email {career_mail.scope('google')}"))
        self.assertEqual(done["Location"], "/settings/#settingsCareerMail")
        self.assertEqual((query["login_hint"], query["access_type"], query["prompt"]), (["owner@gmail.com"], ["offline"], ["consent"]))
        self.assertIn("auth/gmail.send", query["scope"][0])
        self.assertNotIn("mail.google.com", query["scope"][0])  # never full mailbox control
        self.assertNotIn("lasting-secret", career_mail._path(self.owner).read_text(encoding="utf-8"))
        status = self.mail_status()
        self.assertEqual((status["address"], status["via"], status["ready"], status["reads_replies"], status["error"]),
                         ("owner@gmail.com", "google", True, True, ""))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.owner.pk)  # still the same person, nothing new signed in

    def test_a_different_account_or_missing_permission_stores_nothing(self):
        for fake, message in ((Provider("someone@gmail.com", "g-9", f"openid email {career_mail.scope('google')}"), "not owner@gmail.com"),
                              (Provider("owner@gmail.com", "g-1", f"openid email {career_mail.READ['google']}"), "send email"),
                              (Provider("owner@gmail.com", "g-1", f"openid email {career_mail.scope('google')}", refresh=None), "lasting access")):
            with self.subTest(message=message):
                self.choose("google", "owner@gmail.com", fake)
                status = self.mail_status()
                self.assertFalse(status["ready"])
                self.assertIn(message, status["error"])

    def test_outlook_sends_through_graph_reads_the_inbox_and_keeps_the_new_refresh_token(self):
        outlook = Provider("owner@outlook.com", "m-1", "Mail.Send Mail.Read openid email offline_access", refresh="ms-refresh-1")
        query, _ = self.choose("microsoft", "owner@outlook.com", outlook)
        self.assertIn("https://graph.microsoft.com/Mail.Send", query["scope"][0])
        self.assertIn("offline_access", query["scope"][0])
        self.assertTrue(self.mail_status()["reads_replies"])
        outlook.refresh = "ms-refresh-2"  # Microsoft hands out a new refresh token as the old one is used
        message = EmailMessage("Application", "Hello", "owner@outlook.com", ["hr@synthetic.example.test"])
        with patch.object(career_mail.public_http, "request", outlook):
            self.assertEqual(career_mail.deliver(self.owner, message), "sent")
            inbox = career_mail.read_inbox(self.owner, days=30)
        method, url, kwargs = outlook.calls[-3]
        self.assertEqual((method, url, kwargs["headers"]["Content-Type"]), ("POST", "https://graph.microsoft.com/v1.0/me/sendMail", "text/plain"))
        self.assertIn(b"To: hr@synthetic.example.test", base64.b64decode(kwargs["data"]))
        self.assertEqual(inbox, [{"id": "", "attachment": False, "from_name": "Priya", "from": "priya@syntheticpay.com", "subject": "Next steps", "on": "2026-11-18",
                                  "body": "Please share your availability."}])
        self.assertEqual(outlook.calls[-1][2]["headers"]["Prefer"], 'outlook.body-content-type="text"')
        from apps.integrations.models import _decrypt_token
        self.assertEqual(_decrypt_token(career_mail._load(self.owner)["refresh"]), "ms-refresh-2")

    def test_outlook_refuses_a_cv_too_large_for_one_request(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.career.models import CareerJobAnalysis, CareerResume
        from apps.career.services import application_send
        from tests.test_career_application_kit import CV, JD, analysis
        self.choose("microsoft", "owner@outlook.com", Provider("owner@outlook.com", "m-1", "Mail.Send openid email"))
        big = b"%PDF-" + b"0" * career_mail.OUTLOOK_MAX_BYTES
        resume = CareerResume.objects.create(user=self.owner, uploaded_file=SimpleUploadedFile("cv.pdf", big), file_name="cv.pdf",
                                             parser_status="parsed", extracted_text=CV, extracted_payload={})
        item = CareerJobAnalysis.objects.create(user=self.owner, job_url="https://jobs.example.test/1", job_title="Engineer",
                                                extracted_text=JD, extracted_payload=analysis().extracted_payload)
        review = application_send.review(self.owner, item, resume, to="hr@synthetic.example.test", subject="Hi", body="Hello", attach_cv=True)
        self.assertIn("Outlook sends a CV of up to 3 MB", " ".join(review["blockers"]))
        self.assertEqual(review["from"], "owner@outlook.com")
        self.assertFalse(self.mail_status()["reads_replies"])  # reading was not ticked, so reply watch stays off

    def test_turning_off_revokes_at_google_and_removes_the_token(self):
        self.choose("google", "owner@gmail.com", Provider("owner@gmail.com", "g-1", f"openid email {career_mail.scope('google')}"))
        google = Provider("owner@gmail.com", "g-1", "")
        with patch.object(career_mail.public_http, "request", google):
            response = self.client.post("/api/settings/online-services/", json.dumps({"mail_off": True}), content_type="application/json")
        self.assertEqual((response.status_code, response.json()["mail"]["ready"]), (200, False))
        self.assertEqual(google.calls[0][1], "https://oauth2.googleapis.com/revoke")
        self.assertFalse(career_mail._path(self.owner).exists())
        self.assertEqual(career_mail.deliver(self.owner, EmailMessage("s", "b", "owner@gmail.com", ["hr@synthetic.example.test"])), "failed")

    def test_a_refused_or_expired_permission_never_counts_as_sent(self):
        self.choose("google", "owner@gmail.com", Provider("owner@gmail.com", "g-1", f"openid email {career_mail.scope('google')}"))
        message = EmailMessage("s", "b", "owner@gmail.com", ["hr@synthetic.example.test"])

        def expired(method, url, **kwargs):
            raise PublicHTTPError("authorization_failed")
        with patch.object(career_mail.public_http, "request", expired):
            self.assertEqual(career_mail.deliver(self.owner, message), "failed")
            with self.assertRaisesRegex(career_mail.MailError, "choose your address again"):
                career_mail.read_inbox(self.owner, days=30)
        with patch.object(career_mail.public_http, "request", Provider("owner@gmail.com", "g-1", "", fail="timeout")):
            self.assertEqual(career_mail.deliver(self.owner, message), "unknown")  # it may have been taken: the person checks Sent
