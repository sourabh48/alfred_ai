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

    def test_password_signup_closes_once_a_provider_is_set_up_and_settings_connect_adds_another_provider(self):
        page = self.client.get("/signup/")
        self.assertFalse(page.context["password_signup_open"])
        self.assertEqual(self.client.post("/signup/", {"username": "late", "email": "l@example.org"}).status_code, 403)
        self.sign_in("google")  # a provider sign-in creates the account with a verified email
        owner = self.users.get()
        self.assertTrue(self.client.get("/settings/").context["email_verified"])
        response, _ = self.sign_in("microsoft", start_query="?connect=1")
        self.assertEqual(response["Location"], "/settings/#settingsSignIn")
        self.assertEqual((self.users.count(), sorted(owner.email_identities.values_list("provider", flat=True))), (1, ["google", "microsoft"]))
        # The same Microsoft account cannot then be connected to someone else.
        self.client.logout()
        self.sign_in("github")
        other = self.users.get(email="dev@example.org")
        self.sign_in("microsoft", start_query="?connect=1")
        self.assertEqual(EmailIdentity.objects.get(provider="microsoft").user, owner)
        self.assertNotEqual(other, owner)
        with patch.dict(os.environ, {k: "" for k in KEYS}):
            self.assertTrue(social_login.password_signup_open())

    def test_only_provider_sign_in_once_set_up_and_old_password_accounts_keep_their_records(self):
        """Owner decision 2026-11-19: no passwords once a provider exists; only a provider-verified email gets in."""
        old = self.users.create_user("old-owner", "Owner@example.org", "x-synthetic-1")
        refused = self.client.post("/login/", {"username": "old-owner", "password": "x-synthetic-1"})
        self.assertEqual((refused.status_code, refused["Location"]), (302, "/login/"))
        self.assertNotIn("_auth_user_id", self.client.session)
        page = self.client.get("/login/").content.decode()
        self.assertIn("Passwords are not used", page)
        self.assertNotIn('name="password"', page)
        self.assertNotIn('href="/signup/"', page)
        self.assertEqual(self.client.get("/admin/login/?next=/admin/")["Location"], "/login/?next=%2Fadmin%2F")
        # A session from before the change, without a verified email, is ended at the next page or API call.
        self.client.force_login(old)
        self.assertEqual(self.client.get("/settings/")["Location"], "/login/")
        self.client.force_login(old)
        self.assertEqual(self.client.get("/api/session/data-version/").status_code, 401)
        # Signing in with a provider whose verified email matches reaches the same account and its records.
        self.sign_in("google")
        self.assertEqual((self.users.count(), int(self.client.session["_auth_user_id"])), (1, old.pk))
        self.assertEqual(self.client.get("/settings/").status_code, 200)
        # This PC is reached as localhost, the only local address Google and Microsoft send sign-ins back to.
        moved = self.client.get("/travel/?x=1", HTTP_HOST="127.0.0.1:8000")
        self.assertEqual(moved["Location"], "http://localhost:8000/travel/?x=1")
        with patch.dict(os.environ, {k: "" for k in KEYS}):  # a copy with no provider at all still uses passwords
            self.assertEqual(self.client.get("/login/", HTTP_HOST="127.0.0.1:8000").status_code, 200)

    def test_a_verified_email_from_another_provider_reaches_the_same_person(self):
        self.sign_in("google", Provider(google={"sub": "g-9", "email": "dev@example.org", "email_verified": True}))
        self.client.logout()
        self.sign_in("github")
        self.assertEqual((self.users.count(), EmailIdentity.objects.count()), (1, 2))


class GoogleButtonTests(TestCase):
    def test_login_and_signup_always_show_google_greyed_out_until_it_is_set_up(self):
        empty = {k: "" for k in KEYS}
        for page in ("/login/", "/signup/"):
            with patch.dict(os.environ, empty):
                html = self.client.get(page).content.decode()
            self.assertIn("Continue with Google</span></button>", html)
            self.assertIn("Google sign-in is not set up yet", html)
            with patch.dict(os.environ, KEYS):
                html = self.client.get(page).content.decode()
            self.assertIn('href="/auth/google/start/"', html)
            self.assertNotIn("not set up yet", html)


class PhoneCodeSignInTests(TestCase):
    """Owner decision 2026-11-19: a phone on the home Wi-Fi shows a code and the signed-in PC approves it."""
    setUp, sign_in = SocialLoginTests.setUp, SocialLoginTests.sign_in

    def test_phone_code_is_approved_only_by_a_verified_person_once_and_signs_the_phone_in_as_them(self):
        import json
        from django.test import Client
        phone = Client()
        code = phone.get("/phone/").context["code"]
        self.assertRegex(code, r"^[A-HJ-NP-Z2-9]{4}-[A-HJ-NP-Z2-9]{4}$")
        self.assertEqual(phone.get("/phone/?check=1").json(), {"state": "waiting"})
        approve = lambda c: self.client.post("/phone/approve/", json.dumps({"code": c}), content_type="application/json")
        unverified = self.users.create_user("no-provider", "", "x-synthetic-1")
        self.client.force_login(unverified)
        self.assertEqual(approve(code).status_code, 401)
        self.sign_in("google")
        owner = self.users.get(email="owner@example.org")
        self.assertEqual(approve("ZZZZ-ZZZZ").status_code, 400)
        self.assertEqual(approve(code.lower()).status_code, 200)
        self.assertEqual(phone.get("/phone/?check=1").json()["state"], "approved")
        self.assertEqual(int(phone.session["_auth_user_id"]), owner.pk)
        self.assertEqual(approve(code).status_code, 400)  # one use only
        self.assertEqual(Client().get("/phone/?check=1").json(), {"state": "expired"})  # another device cannot borrow it
