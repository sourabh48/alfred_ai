"""The browser API uses sessions and enforces CSRF on authenticated writes."""
import base64
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class ApiSessionSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="api_policy_user", password="Synthetic-X9!Orbit", first_name="Original")
        self.client = Client(enforce_csrf_checks=True)
        credentials = base64.b64encode(b"api_policy_user:Synthetic-X9!Orbit").decode("ascii")
        self.basic_header = "Basic " + credentials

    def test_basic_credentials_do_not_authenticate_on_http_or_https(self):
        for secure in (False, True):
            with self.subTest(secure=secure):
                response = self.client.get("/api/users/profile/", secure=secure,
                                           HTTP_AUTHORIZATION=self.basic_header)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("username", response.json())

    def test_basic_credentials_cannot_bypass_session_and_csrf_for_writes(self):
        response = self.client.patch("/api/users/profile/", json.dumps({"first_name": "Unauthorized"}),
                                     content_type="application/json", HTTP_AUTHORIZATION=self.basic_header)
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Original")

    def test_session_authenticated_reads_still_work(self):
        self.client.force_login(self.user)
        response = self.client.get("/api/users/profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.user.pk)

    def test_session_authenticated_writes_without_csrf_are_rejected(self):
        self.client.force_login(self.user)
        response = self.client.patch("/api/users/profile/", json.dumps({"first_name": "Unauthorized"}),
                                     content_type="application/json", HTTP_AUTHORIZATION=self.basic_header)
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Original")

    def test_session_authenticated_writes_with_csrf_still_work(self):
        self.client.get("/login/")
        token = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        self.client.force_login(self.user)
        response = self.client.patch("/api/users/profile/", json.dumps({"first_name": "Authorized"}),
                                     content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Authorized")
