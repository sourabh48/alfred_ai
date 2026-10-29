"""The browser API uses sessions and enforces CSRF on authenticated writes."""
import base64
import codecs
import json
from io import BytesIO
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import URLResolver, get_resolver
from rest_framework.exceptions import ParseError
from rest_framework.views import APIView


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


class ApiParsingSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="parser_policy_user", first_name="Original")
        self.client = Client(enforce_csrf_checks=True)
        self.client.get("/login/")
        self.csrf = self.client.cookies[settings.CSRF_COOKIE_NAME].value
        self.client.force_login(self.user)

    def send(self, body, charset="utf-8"):
        return self.client.patch("/api/users/profile/", body,
            content_type="application/json; charset=" + charset, HTTP_X_CSRFTOKEN=self.csrf)

    def test_binary_json_codecs_cannot_expand_request_or_change_profile(self):
        raw = json.dumps({"first_name": "Changed", "noise": "A" * 65536}).encode()
        for codec in ("bz2_codec", "zlib_codec", "base64_codec", "hex_codec"):
            with self.subTest(codec=codec):
                response = self.send(codecs.encode(raw, codec), codec)
                self.assertEqual(response.status_code, 400)
                self.user.refresh_from_db()
                self.assertEqual(self.user.first_name, "Original")

    def test_non_text_codec_is_rejected_before_reading_stream(self):
        parser = next(p for p in APIView().get_parsers() if p.media_type == "application/json")
        stream = BytesIO(b"synthetic")
        with patch.object(stream, "read", side_effect=AssertionError("stream must not be read")):
            with self.assertRaises(ParseError):
                parser.parse(stream, parser_context={"encoding": "bz2_codec"})

    def test_configured_api_routes_reject_binary_json_before_reading(self):
        def callbacks(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLResolver):
                    yield from callbacks(pattern.url_patterns)
                else:
                    yield pattern.callback
        checked = set()
        for callback in callbacks(get_resolver().url_patterns):
            view = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
            for parser_type in getattr(view, "parser_classes", ()):
                if parser_type.media_type != "application/json" or (view, parser_type) in checked:
                    continue
                checked.add((view, parser_type))
                with self.subTest(view=view.__name__), self.assertRaises(ParseError):
                    stream = BytesIO(b"synthetic")
                    with patch.object(stream, "read", side_effect=AssertionError("stream must not be read")):
                        parser_type().parse(stream, parser_context={"encoding": "bz2_codec"})
        self.assertGreater(len(checked), 10)

    def test_large_accept_is_rejected_before_media_type_parsing(self):
        with patch("rest_framework.negotiation.order_by_precedence",
                   side_effect=AssertionError("oversized Accept must not be parsed")):
            response = self.client.get("/api/users/profile/", HTTP_ACCEPT="text/x-synthetic; x=\"" + ";" * 9000 + "\"")
        self.assertEqual(response.status_code, 406)

    def test_excess_accept_tokens_are_rejected_before_media_type_parsing(self):
        with patch("rest_framework.negotiation.order_by_precedence",
                   side_effect=AssertionError("excess Accept tokens must not be parsed")):
            response = self.client.get("/api/users/profile/", HTTP_ACCEPT=",".join(["application/json"] * 65))
        self.assertEqual(response.status_code, 406)

    def test_text_json_encodings_preserve_csrf_authenticated_writes(self):
        for charset in ("utf-8", "utf-16"):
            with self.subTest(charset=charset):
                response = self.send(json.dumps({"first_name": "Text"}).encode(charset), charset)
                self.assertEqual(response.status_code, 200)
                self.user.refresh_from_db()
                self.assertEqual(self.user.first_name, "Text")

    def test_normal_browser_accept_and_form_parser_remain_supported(self):
        response = self.client.get("/api/users/profile/", HTTP_ACCEPT="text/html,application/json;q=0.9,*/*;q=0.8")
        self.assertEqual(response.status_code, 200)
        response = self.client.patch("/api/users/profile/", "first_name=Form",
            content_type="application/x-www-form-urlencoded", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Form")
