"""Settings > Online services: the PC's owner adds keys and free switches without editing files; nothing else can be written."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from alfred_ai.local_config import load_local_environment
from alfred_private_storage import private_directory
from alfred_ai.services import online_services as online

SMTP = dict(ALFRED_SMTP_HOST="", ALFRED_SMTP_PORT=587, ALFRED_SMTP_SSL=False, ALFRED_SMTP_USER="", ALFRED_SMTP_PASSWORD="", ALFRED_SMTP_FROM="")
NAMES = [*online.KEYS, *online.SWITCHES, *online.MAIL]


class OnlineServicesTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-online-services-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root)}))  # restores every variable afterwards
        for name in NAMES:
            os.environ.pop(name, None)
        self.enterContext(override_settings(**SMTP))
        users = get_user_model().objects
        self.owner = users.create_user(username="synthetic-online-owner", password="pw-synthetic-1")
        self.family = users.create_user(username="synthetic-online-family", password="pw-synthetic-2")

    def post(self, user, body):
        self.client.force_login(user)
        return self.client.post("/api/settings/online-services/", json.dumps(body), content_type="application/json")

    def test_only_the_superuser_or_else_the_first_account_may_change_shared_keys(self):
        self.assertTrue(online.can_manage(self.owner))
        self.assertFalse(online.can_manage(self.family))
        admin = get_user_model().objects.create_superuser(username="synthetic-online-admin", password="pw-synthetic-3")
        self.assertEqual((online.can_manage(admin), online.can_manage(self.owner)), (True, False))
        self.assertEqual(self.post(self.family, {"keys": {"TRAVEL_SKYSCANNER_API_KEY": "synthetic-sky-key"}}).status_code, 403)
        self.assertFalse((self.root / "config" / "local.env").exists())

    def test_input_is_checked_before_anything_is_written(self):
        for bad in ({"keys": {"DJANGO_SECRET_KEY": "x" * 20}}, {"keys": {"TRAVEL_SKYSCANNER_API_KEY": "has space inside"}},
                    {"keys": {"TRAVEL_SKYSCANNER_API_KEY": "quote'injected\nDJANGO_SECRET_KEY=x"}}, {"switches": {"TRAVEL_VALHALLA_URL": True}},
                    {"switches": {"ALFRED_MEMORY_CLOUD_AUTHORIZED": True}}, {"mail": {"address": "me@unknown-provider.example", "password": "abcdefghij"}},
                    {"mail": {"address": "me@gmail.com", "password": "abcdefghij", "port": "99999"}}, {"mail": {"address": "not-an-email", "password": "abcdefghij"}}):
            with self.subTest(bad=bad):
                self.assertEqual(self.post(self.owner, bad).status_code, 400)
        self.assertEqual(self.post(self.owner, ["not", "a", "dict"]).status_code, 400)
        self.assertFalse((self.root / "config" / "local.env").exists())

    def test_saved_values_work_at_once_survive_a_restart_and_are_never_sent_back(self):
        path = self.root / "config" / "local.env"
        private_directory(path.parent)
        path.write_text("DJANGO_SECRET_KEY=keep-this-synthetic\nTRAVEL_SKYSCANNER_API_KEY=old-synthetic-key\n# a comment\n", encoding="utf-8")
        key = "synthetic-sky-key-1234"
        response = self.post(self.owner, {"keys": {"TRAVEL_SKYSCANNER_API_KEY": key},
                                          "mail": {"address": "synthetic.owner@gmail.com", "password": "abcd efgh ijkl mnop"}})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(key, response.content.decode())
        self.assertNotIn("abcdefghijklmnop", response.content.decode())
        body = response.json()
        self.assertEqual([k["hint"] for k in body["keys"] if k["saved"]], ["…1234"])
        self.assertTrue(body["mail"]["ready"])
        # in use straight away
        self.assertEqual(os.environ["TRAVEL_SKYSCANNER_API_KEY"], key)
        self.assertEqual((settings.ALFRED_SMTP_HOST, settings.ALFRED_SMTP_PORT, settings.ALFRED_SMTP_SSL, settings.ALFRED_SMTP_PASSWORD),
                         ("smtp.gmail.com", 587, False, "abcdefghijklmnop"))
        from apps.career.services.application_send import mail_configured
        self.assertTrue(mail_configured())
        text = path.read_text(encoding="utf-8")
        self.assertIn("DJANGO_SECRET_KEY=keep-this-synthetic", text)
        self.assertIn("# a comment", text)
        self.assertNotIn("old-synthetic-key", text)
        # and read back the same way at the next start
        for name in NAMES:
            os.environ.pop(name, None)
        load_local_environment(self.root)
        self.assertEqual((os.environ["TRAVEL_SKYSCANNER_API_KEY"], os.environ["ALFRED_SMTP_USER"]), (key, "synthetic.owner@gmail.com"))
        # family members see the state but not the address
        self.client.force_login(self.family)
        family_view = self.client.get("/api/settings/online-services/").json()
        self.assertEqual((family_view["can_manage"], family_view["mail"]["address"]), (False, ""))

    def test_switching_off_and_removing_clears_the_line_and_the_running_value(self):
        self.post(self.owner, {"keys": {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-google-key"},
                               "mail": {"address": "synthetic@yahoo.com", "password": "abcdefghij"}})
        self.assertEqual((settings.ALFRED_SMTP_PORT, settings.ALFRED_SMTP_SSL), (465, True))
        self.post(self.owner, {"keys": {"TRAVEL_GOOGLE_MAPS_API_KEY": ""}, "mail": {}})
        self.assertNotIn("TRAVEL_GOOGLE", (self.root / "config" / "local.env").read_text(encoding="utf-8"))
        self.assertNotIn("TRAVEL_GOOGLE_MAPS_API_KEY", os.environ)
        self.assertEqual((settings.ALFRED_SMTP_HOST, settings.ALFRED_SMTP_PORT), ("", 587))
