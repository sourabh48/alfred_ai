"""Settings > Online services: each person's own keys for paid or limited services; the manager's switches and Career email."""
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

    def test_every_person_saves_their_own_keys_but_only_the_manager_changes_shared_settings(self):
        """Owner decision 2026-11-19: paid or limited services take each person's own key; switches and Career email stay with the manager."""
        from alfred_ai.services import personal_keys
        self.assertTrue(online.can_manage(self.owner))
        self.assertFalse(online.can_manage(self.family))
        admin = get_user_model().objects.create_superuser(username="synthetic-online-admin", password="pw-synthetic-3")
        self.assertEqual((online.can_manage(admin), online.can_manage(self.owner)), (True, False))
        self.assertEqual(self.post(self.family, {"switches": {"ALFRED_PRICES_ALPHA_VANTAGE_FIRST": True}}).status_code, 403)
        self.assertEqual(self.post(self.family, {"mail": {"address": "synthetic@gmail.com", "password": "abcdefghij"}}).status_code, 403)
        response = self.post(self.family, {"keys": {"TRAVEL_SKYSCANNER_API_KEY": "synthetic-family-sky-5678"}})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("synthetic-family-sky-5678", response.content.decode())
        self.assertEqual([(k["name"], k["hint"]) for k in response.json()["keys"] if k["saved"]], [("TRAVEL_SKYSCANNER_API_KEY", "…5678")])
        self.assertFalse((self.root / "config" / "local.env").exists())  # never the shared file
        self.assertNotIn("TRAVEL_SKYSCANNER_API_KEY", os.environ)
        stored = (self.root / "artifacts" / "personal-keys" / f"user-{self.family.pk}.json").read_text(encoding="utf-8")
        self.assertNotIn("synthetic-family-sky-5678", stored)  # encrypted at rest
        with personal_keys.acting_for(self.family):
            self.assertEqual(personal_keys.get("TRAVEL_SKYSCANNER_API_KEY"), "synthetic-family-sky-5678")
        with personal_keys.acting_for(admin):
            self.assertEqual(personal_keys.get("TRAVEL_SKYSCANNER_API_KEY"), "")  # nobody else uses it
        self.client.force_login(admin)
        self.assertEqual([k["saved"] for k in self.client.get("/api/settings/online-services/").json()["keys"]], [False, False, False])

    def test_input_is_checked_before_anything_is_written(self):
        for bad in ({"keys": {"DJANGO_SECRET_KEY": "x" * 20}}, {"keys": {"TRAVEL_SKYSCANNER_API_KEY": "has space inside"}},
                    {"keys": {"TRAVEL_SKYSCANNER_API_KEY": "quote'injected\nDJANGO_SECRET_KEY=x"}}, {"switches": {"TRAVEL_VALHALLA_URL": True}},
                    {"switches": {"ALFRED_MEMORY_CLOUD_AUTHORIZED": True}}, {"mail": {"address": "me@unknown-provider.example", "password": "abcdefghij"}},
                    {"mail": {"address": "me@gmail.com", "password": "abcdefghij", "port": "99999"}}, {"mail": {"address": "not-an-email", "password": "abcdefghij"}},
                    # Free keys are built in and never changed in Settings (owner decision 2026-11-19).
                    {"keys": {"ALFRED_MICROSOFT_CLIENT_SECRET": "synthetic-value-12345"}}, {"keys": {"ALFRED_FRED_API_KEY": "synthetic-fred-123"}},
                    {"keys": {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-maps-1234"}, "switches": {"TRAVEL_VALHALLA_URL": True}}):
            with self.subTest(bad=bad):
                self.assertEqual(self.post(self.owner, bad).status_code, 400)
        self.assertEqual(self.post(self.owner, ["not", "a", "dict"]).status_code, 400)
        self.assertFalse((self.root / "config" / "local.env").exists())
        self.assertFalse((self.root / "artifacts" / "personal-keys").exists())

    def test_saved_values_work_at_once_survive_a_restart_and_are_never_sent_back(self):
        from alfred_ai.services import personal_keys
        path = self.root / "config" / "local.env"
        private_directory(path.parent)
        path.write_text("DJANGO_SECRET_KEY=keep-this-synthetic\nTRAVEL_SKYSCANNER_API_KEY=shared-synthetic-key\n# a comment\n", encoding="utf-8")
        load_local_environment(self.root)
        key = "synthetic-sky-key-1234"
        response = self.post(self.owner, {"keys": {"TRAVEL_SKYSCANNER_API_KEY": key},
                                          "mail": {"address": "synthetic.owner@gmail.com", "password": "abcd efgh ijkl mnop"}})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(key, response.content.decode())
        self.assertNotIn("abcdefghijklmnop", response.content.decode())
        self.assertNotIn("shared-synthetic-key", response.content.decode())
        body = response.json()
        self.assertEqual([k["hint"] for k in body["keys"] if k["saved"]], ["…1234"])
        self.assertTrue(body["mail"]["ready"])
        # in use straight away: the owner's own key for the owner, the shared PC-wide key for everyone else
        with personal_keys.acting_for(self.owner):
            self.assertEqual(personal_keys.get("TRAVEL_SKYSCANNER_API_KEY"), key)
        with personal_keys.acting_for(self.family):
            self.assertEqual(personal_keys.get("TRAVEL_SKYSCANNER_API_KEY"), "shared-synthetic-key")
        self.assertEqual((settings.ALFRED_SMTP_HOST, settings.ALFRED_SMTP_PORT, settings.ALFRED_SMTP_SSL, settings.ALFRED_SMTP_PASSWORD),
                         ("smtp.gmail.com", 587, False, "abcdefghijklmnop"))
        from apps.career.services.application_send import mail_configured
        self.assertTrue(mail_configured())
        text = path.read_text(encoding="utf-8")
        self.assertIn("DJANGO_SECRET_KEY=keep-this-synthetic", text)
        self.assertIn("# a comment", text)
        self.assertNotIn(key, text)
        # and read back the same way at the next start
        for name in NAMES:
            os.environ.pop(name, None)
        personal_keys._cache.clear()
        load_local_environment(self.root)
        self.assertEqual(os.environ["ALFRED_SMTP_USER"], "synthetic.owner@gmail.com")
        with personal_keys.acting_for(self.owner.pk):
            self.assertEqual(personal_keys.get("TRAVEL_SKYSCANNER_API_KEY"), key)
        # family members see that a shared key exists, but no part of it, and not the address
        self.client.force_login(self.family)
        family_view = self.client.get("/api/settings/online-services/").json()
        self.assertEqual((family_view["can_manage"], family_view["mail"]["address"]), (False, ""))
        sky = next(k for k in family_view["keys"] if k["name"] == "TRAVEL_SKYSCANNER_API_KEY")
        self.assertEqual((sky["saved"], sky["shared"], sky["hint"]), (False, True, ""))

    def test_switching_off_and_removing_clears_the_line_and_the_running_value(self):
        from alfred_ai.services import personal_keys
        self.post(self.owner, {"keys": {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-google-key"},
                               "mail": {"address": "synthetic@yahoo.com", "password": "abcdefghij"}})
        self.assertEqual((settings.ALFRED_SMTP_PORT, settings.ALFRED_SMTP_SSL), (465, True))
        self.post(self.owner, {"keys": {"TRAVEL_GOOGLE_MAPS_API_KEY": ""}, "mail": {}})
        with personal_keys.acting_for(self.owner):
            self.assertEqual(personal_keys.get("TRAVEL_GOOGLE_MAPS_API_KEY"), "")
        self.assertNotIn("TRAVEL_GOOGLE_MAPS_API_KEY", os.environ)
        self.assertEqual((settings.ALFRED_SMTP_HOST, settings.ALFRED_SMTP_PORT), ("", 587))

    def test_a_page_and_a_background_job_use_their_own_person_s_key(self):
        from alfred_ai.services import personal_keys
        from apps.mobility.services.travel import google_tiles
        personal_keys.save(self.family, {"TRAVEL_GOOGLE_MAPS_API_KEY": "synthetic-family-maps-key"})
        with personal_keys.acting_for(self.family):
            self.assertEqual(google_tiles._headers(), {"X-Goog-Api-Key": "synthetic-family-maps-key"})
        self.assertFalse(google_tiles.available())  # outside any person, and no PC-wide key
        seen = []
        with patch.object(google_tiles, "tile", side_effect=lambda z, x, y: seen.append(personal_keys.get("TRAVEL_GOOGLE_MAPS_API_KEY"))):
            self.client.force_login(self.family)
            self.client.get("/mobility/map-tiles/1/0/0.png")
            self.client.force_login(self.owner)
            self.client.get("/mobility/map-tiles/1/0/0.png")
        self.assertEqual(seen, ["synthetic-family-maps-key", ""])


class BuiltInFreeKeysTests(TestCase):
    """Owner decision 2026-11-19: free keys ship encrypted in the installer; a person's own key wins; none is ever shown."""

    def setUp(self):
        from alfred_ai import bundled_keys
        self.keys = bundled_keys
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-built-in-keys-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root)}))
        for name in NAMES:
            os.environ.pop(name, None)
        self.enterContext(patch.dict(bundled_keys._built_in, clear=True))
        self.owner = get_user_model().objects.create_user(username="synthetic-built-in-owner", password="pw-synthetic-1")

    def test_only_free_keys_are_sealed_unreadable_and_a_saved_key_wins(self):
        env = self.root / "local.env"
        env.write_text("ALFRED_FRED_API_KEY='synthetic-fred-free-123'\nTRAVEL_GOOGLE_MAPS_API_KEY=synthetic-paid-maps-456\n"
                       "export ALFRED_GITHUB_CLIENT_ID=\"synthetic-gh-id-789\"\n", encoding="utf-8")
        blob = self.keys.seal(self.keys.read_env_file(env))
        self.assertNotIn(b"synthetic", blob)  # nothing in plain text
        self.assertEqual(self.keys.unseal(blob), {"ALFRED_FRED_API_KEY": "synthetic-fred-free-123", "ALFRED_GITHUB_CLIENT_ID": "synthetic-gh-id-789"})
        self.assertEqual(self.keys.unseal(blob[:-3] + b"xyz"), {})  # damaged file: no keys, no crash
        sealed = self.root / self.keys.FILE_NAME
        sealed.write_bytes(blob)
        os.environ["ALFRED_GITHUB_CLIENT_ID"] = "synthetic-own-github-id"
        self.keys.load(sealed)
        self.assertEqual(os.environ["ALFRED_FRED_API_KEY"], "synthetic-fred-free-123")
        self.assertEqual(os.environ["ALFRED_GITHUB_CLIENT_ID"], "synthetic-own-github-id")
        self.assertNotIn("TRAVEL_GOOGLE_MAPS_API_KEY", os.environ)
        # Free keys are built in and not listed in Settings at all, so nobody can find or change them there.
        listed = json.dumps(online.status(self.owner))
        for hidden in ("ALFRED_FRED_API_KEY", "ALFRED_GITHUB_CLIENT_ID", "ALFRED_GOOGLE_CLIENT_SECRET", "ALFRED_REDDIT_CLIENT_ID", "123", "b-id"):
            self.assertNotIn(hidden, listed)
        online.save({"ALFRED_FRED_API_KEY": "synthetic-own-fred-key"})
        self.assertEqual(os.environ["ALFRED_FRED_API_KEY"], "synthetic-own-fred-key")
        online.save({"ALFRED_FRED_API_KEY": ""})  # removing your own key falls back to the built-in one
        self.assertEqual(os.environ["ALFRED_FRED_API_KEY"], "synthetic-fred-free-123")
        self.assertNotIn("synthetic-fred-free-123", (self.root / "config" / "local.env").read_text(encoding="utf-8"))
