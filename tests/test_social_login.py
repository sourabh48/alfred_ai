"""Sign in with Google, GitHub or Microsoft: the state must match, only a verified email is accepted, an identity
signs in to the same person every time, a new account needs a provider once one is set up, and connecting from
Settings verifies the signed-in person's email. Provider responses are synthetic; nothing goes to the network."""
import os
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services import social_login
from alfred_ai.services.public_http import PublicHTTPError
from apps.users.models import EmailIdentity

KEYS = {f"ALFRED_{p}_CLIENT_{k}": f"x-{p.lower()}-{k.lower()}" for p in ("GOOGLE", "GITHUB", "MICROSOFT") for k in ("ID", "SECRET")}


class Provider:
    """Answers the token and profile calls the way each provider does."""
    def __init__(self, google=None, github_emails=None):
        self.google = google or {"sub": "g-1", "email": "Owner@Example.org", "email_verified": True}
        self.github_emails = github_emails if github_emails is not None else [{"email": "dev@example.org", "primary": True, "verified": True}]
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        body = ({"access_token": "t"} if method == "POST" else self.google if "googleapis" in url
                else self.github_emails if url.endswith("/emails") else {"id": 42} if "api.github.com" in url
                else {"sub": "m-1", "email": "me@outlook.com"})
        return SimpleNamespace(json=lambda: body)


class SocialLoginTests(TestCase):
    def setUp(self):
        p = patch.dict(os.environ, KEYS)
        p.start()
        self.addCleanup(p.stop)
        self.users = get_user_model().objects

    def sign_in(self, provider="google", answers=None, start_query=""):
        answers = answers or Provider()
        start = self.client.get(f"/auth/{provider}/start/{start_query}")
        state = parse_qs(urlsplit(start["Location"]).query)["state"][0]
        with patch.object(social_login.public_http, "request", answers):
            return self.client.get(f"/auth/{provider}/callback/", {"code": "c", "state": state}), answers

    def test_google_signs_up_once_then_signs_in_the_same_person_with_pkce(self):
        start = self.client.get("/auth/google/start/?next=/travel/")
        query = parse_qs(urlsplit(start["Location"]).query)
        self.assertEqual((query["code_challenge_method"], query["redirect_uri"]), (["S256"], ["http://testserver/auth/google/callback/"]))
        self.client.logout()
        response, answers = self.sign_in(start_query="?next=/travel/")
        self.assertEqual(response["Location"], "/travel/")
        user = self.users.get()
        self.assertEqual((user.email, user.has_usable_password()), ("owner@example.org", False))
        self.assertTrue(social_login.is_verified(user))
        token_call = answers.calls[0][2]["data"]
        self.assertTrue(token_call["code_verifier"] and token_call["client_secret"] == "x-google-secret")
        self.client.logout()
        self.sign_in()
        self.assertEqual((self.users.count(), int(self.client.session["_auth_user_id"])), (1, user.pk))

    def test_a_wrong_state_unverified_email_or_unknown_provider_signs_nobody_in(self):
        self.client.get("/auth/google/start/")
        with patch.object(social_login.public_http, "request", Provider()) as answers:
            response = self.client.get("/auth/google/callback/", {"code": "c", "state": "forged"})
        self.assertEqual((response["Location"], answers.calls), ("/login/", []))
        for provider, answers in (("google", Provider(google={"sub": "g-2", "email": "x@example.org", "email_verified": False})),
                                  ("github", Provider(github_emails=[{"email": "x@example.org", "primary": True, "verified": False}]))):
            self.sign_in(provider, answers)
        self.assertFalse(self.users.exists())
        self.assertIn("no verified email", self.client.get("/login/").context["sign_in_error"])
        self.assertEqual(self.client.get("/auth/yahoo/start/")["Location"], "/login/")

    def test_a_rejected_secret_is_explained(self):
        def refuse(method, url, **kwargs):
            raise PublicHTTPError("authorization_failed")
        self.sign_in("github", refuse)
        self.assertIn("did not accept", self.client.get("/login/").context["sign_in_error"])

    def test_password_signup_closes_once_a_provider_is_set_up_and_settings_connect_verifies_the_email(self):
        owner = self.users.create_user("owner", "old@example.org", "x-synthetic-1")
        page = self.client.get("/signup/")
        self.assertFalse(page.context["password_signup_open"])
        self.assertEqual(self.client.post("/signup/", {"username": "late", "email": "l@example.org"}).status_code, 403)
        self.client.force_login(owner)
        self.assertFalse(self.client.get("/settings/").context["email_verified"])
        response, _ = self.sign_in("microsoft", start_query="?connect=1")
        self.assertEqual(response["Location"], "/settings/#settingsSignIn")
        owner.refresh_from_db()
        self.assertEqual((owner.email, self.users.count()), ("me@outlook.com", 1))
        self.assertTrue(self.client.get("/settings/").context["email_verified"])
        # The same Microsoft account cannot then be connected to someone else.
        other = self.users.create_user("other", "o@example.org", "x-synthetic-2")
        self.client.force_login(other)
        self.sign_in("microsoft", start_query="?connect=1")
        self.assertEqual(EmailIdentity.objects.get().user, owner)
        with patch.dict(os.environ, {k: "" for k in KEYS}):
            self.assertTrue(social_login.password_signup_open())

    def test_a_verified_email_from_another_provider_reaches_the_same_person(self):
        self.sign_in("google", Provider(google={"sub": "g-9", "email": "dev@example.org", "email_verified": True}))
        self.client.logout()
        self.sign_in("github")
        self.assertEqual((self.users.count(), EmailIdentity.objects.count()), (1, 2))
