import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from alfred_ai.services import backup_key
from alfred_ai.services.public_http import PublicHTTPError, PublicResponse
from scripts import release_recovery

PASS = "four unrelated synthetic words"


class FakeDrive:
    """Google Drive's app folder, in memory."""
    def __init__(self):
        self.files, self.calls, self.corrupt = {}, [], False

    def __call__(self, method, url, *, headers=None, params=None, data=None, **kwargs):
        self.calls.append((method, url, params))
        assert headers["Authorization"] == "Bearer synthetic-access"
        if method == "GET" and url == backup_key.FILES:
            assert params["spaces"] == "appDataFolder"
            return PublicResponse(json.dumps({"files": [{"id": i} for i in self.files]}).encode(), "application/json")
        if method == "POST" and url == backup_key.UPLOAD:
            assert params == {"uploadType": "multipart", "fields": "id"} and b'"parents": ["appDataFolder"]' in data
            body = data.split(b"Content-Type: application/json\r\n\r\n", 1)[1].rsplit(b"\r\n--", 1)[0]
            ident = f"file-{len(self.calls)}"
            self.files[ident] = body + (b" " if self.corrupt else b"")
            return PublicResponse(json.dumps({"id": ident}).encode(), "application/json")
        if method == "GET" and url.startswith(backup_key.FILES + "/"):
            return PublicResponse(self.files[url.rsplit("/", 1)[1]], "application/json")
        if method == "DELETE":
            del self.files[url.rsplit("/", 1)[1]]
            return PublicResponse(b"", "", 204)
        raise AssertionError((method, url))


class BackupKeyTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-backup-key-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root / "pc1")}))
        self.enterContext(patch.object(backup_key, "SCRYPT_N", 2 ** 10))  # fast in tests; real copies use 2**17
        self.drive = FakeDrive()
        self.enterContext(patch("alfred_ai.services.backup_key.public_http.request", side_effect=self.drive))

    def test_lock_and_open_round_trip_and_wrong_passphrase(self):
        doc = backup_key.seal(b"x" * 43 + b"=", PASS)
        self.assertNotIn(PASS, json.dumps(doc))
        with self.assertRaises(backup_key.BackupKeyError):
            backup_key.unseal(doc, PASS + "!")
        with self.assertRaises(backup_key.BackupKeyError):
            backup_key.unseal({**doc, "n": 2 ** 30}, PASS)  # a copy may not demand unbounded memory

    def test_make_needs_a_long_matching_passphrase_and_never_replaces_the_key(self):
        for words, repeat in (("short", "short"), (PASS, PASS + "x")):
            with self.assertRaises(backup_key.BackupKeyError):
                backup_key.make(words, repeat)
        self.assertFalse(backup_key.key_path().exists())
        first = backup_key.make(PASS, PASS)
        key = backup_key.key_path().read_bytes()
        self.assertTrue(first["key"] and first["locked_copy"] and not first["in_drive"])
        backup_key.make(PASS + " again", PASS + " again")
        self.assertEqual(backup_key.key_path().read_bytes(), key)
        self.assertEqual(release_recovery.cipher_from_file(backup_key.key_path())[1], "PORTABLE_FORMAT_UNVERIFIED")

    def test_save_to_drive_then_restore_on_a_new_pc(self):
        backup_key.make(PASS, PASS)
        key = backup_key.key_path().read_bytes()
        saved = backup_key.upload("synthetic-access", "owner@example.invalid")
        self.assertTrue(saved["in_drive"])
        self.assertEqual(len(self.drive.files), 1)
        self.assertNotIn(key, next(iter(self.drive.files.values())))  # only the locked copy leaves the PC
        backup_key.upload("synthetic-access", "owner@example.invalid")  # saving again keeps one copy
        self.assertEqual(len(self.drive.files), 1)
        with patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root / "pc2")}):
            self.assertFalse(backup_key.status()["key"])
            fetched = backup_key.fetch("synthetic-access", "owner@example.invalid")
            self.assertTrue(fetched["locked_copy"] and not fetched["key"])
            with self.assertRaises(backup_key.BackupKeyError):
                backup_key.restore("wrong synthetic passphrase")
            self.assertFalse(backup_key.key_path().exists())
            self.assertTrue(backup_key.restore(PASS)["key"])
            self.assertEqual(backup_key.key_path().read_bytes(), key)

    def test_a_damaged_upload_is_reported_and_an_empty_drive_says_so(self):
        backup_key.make(PASS, PASS)
        self.drive.corrupt = True
        with self.assertRaises(backup_key.BackupKeyError):
            backup_key.upload("synthetic-access", "owner@example.invalid")
        self.assertFalse(backup_key.status()["in_drive"])
        self.drive.files.clear()
        with patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root / "pc3")}), self.assertRaises(backup_key.BackupKeyError):
            backup_key.fetch("synthetic-access", "owner@example.invalid")

    def test_a_different_existing_key_is_never_replaced(self):
        backup_key.make(PASS, PASS)
        backup_key.upload("synthetic-access", "owner@example.invalid")
        with patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root / "pc4")}):
            backup_key.make("another synthetic passphrase", "another synthetic passphrase")
            other = backup_key.key_path().read_bytes()
            backup_key.fetch("synthetic-access", "owner@example.invalid")
            with self.assertRaises(backup_key.BackupKeyError):
                backup_key.restore(PASS)
            self.assertEqual(backup_key.key_path().read_bytes(), other)

    def test_drive_refusal_is_a_plain_message(self):
        backup_key.make(PASS, PASS)
        with patch("alfred_ai.services.backup_key.public_http.request", side_effect=PublicHTTPError("authorization_failed")), \
                self.assertRaisesRegex(backup_key.BackupKeyError, "Google Drive API"):
            backup_key.upload("synthetic-access", "owner@example.invalid")


@override_settings(ALFRED_GOOGLE_CLIENT_ID="synthetic-google", ALFRED_GOOGLE_CLIENT_SECRET="synthetic")
class BackupKeySettingsTests(TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-backup-key-ui-synthetic-")))
        self.enterContext(patch.dict(os.environ, {"ALFRED_DATA_DIR": str(self.root), "ALFRED_GOOGLE_CLIENT_ID": "synthetic-google",
                                                  "ALFRED_GOOGLE_CLIENT_SECRET": "synthetic"}))
        self.enterContext(patch.object(backup_key, "SCRYPT_N", 2 ** 10))
        users = get_user_model().objects
        self.owner = users.create_user("synthetic-key-owner", is_superuser=True)
        self.family = users.create_user("synthetic-key-family")
        from apps.users.models import EmailIdentity  # with sign-in set up, only verified people use ALFRED
        for n, user in enumerate((self.owner, self.family)):
            EmailIdentity.objects.create(user=user, provider="google", subject=f"synthetic-{n}", email=f"person{n}@example.invalid")
        self.client = Client(enforce_csrf_checks=True)

    def csrf(self, user):
        self.client.force_login(user)
        self.client.get("/settings/")
        return self.client.cookies["csrftoken"].value

    def test_only_the_manager_uses_it_with_csrf_and_the_passphrase_is_never_returned(self):
        token = self.csrf(self.family)
        self.assertEqual(self.client.get("/api/settings/backup-key/").status_code, 403)
        start = self.client.get("/auth/google/start/?purpose=backupkey&mode=save")
        self.assertEqual(start["Location"], "/settings/#settingsBackupKey")
        token = self.csrf(self.owner)
        body = json.dumps({"action": "make", "passphrase": PASS, "repeat": PASS})
        self.assertEqual(self.client.post("/api/settings/backup-key/", body, content_type="application/json").status_code, 403)
        made = self.client.post("/api/settings/backup-key/", body, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(made.status_code, 200)
        self.assertTrue(made.json()["locked_copy"])
        self.assertNotIn(PASS, made.content.decode())
        self.assertNotIn(backup_key.key_path().read_text(), made.content.decode())
        page = self.client.get("/settings/").content.decode()
        self.assertIn('id="settingsBackupKey"', page)

    def test_google_is_asked_only_for_the_drive_app_folder_and_the_callback_saves_the_copy(self):
        self.csrf(self.owner)
        backup_key.make(PASS, PASS)
        start = self.client.get("/auth/google/start/?purpose=backupkey&mode=save")
        query = parse_qs(urlsplit(start["Location"]).query)
        self.assertIn(backup_key.SCOPE, query["scope"][0].split())
        self.assertNotIn("access_type", query)  # no lasting access
        self.assertNotIn("https://www.googleapis.com/auth/drive ", query["scope"][0] + " ")
        identity = {"provider": "google", "subject": "1", "email": "owner@example.invalid"}
        state = self.client.session["alfred_social_login"]["state"] if "alfred_social_login" in self.client.session else None
        with patch("alfred_ai.services.social_login.finish",
                   return_value=(identity, {"hint": "save", "access_token": "synthetic-access", "granted": f"openid {backup_key.SCOPE}"})), \
                patch("alfred_ai.services.backup_key.upload") as upload:
            done = self.client.get("/auth/google/callback/?code=x&state=" + str(state))
        upload.assert_called_once_with("synthetic-access", "owner@example.invalid")
        self.assertEqual(done["Location"], "/settings/#settingsBackupKey")
