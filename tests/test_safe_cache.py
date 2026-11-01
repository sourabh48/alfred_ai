"""CVE-2025-69872: a row planted in a cache file must not reach pickle, in throttling or the shared cache."""
from contextlib import closing
from datetime import date, datetime, time, timedelta, timezone as utc
from decimal import Decimal
import json
import os
from pathlib import Path
import pickle
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import skipUnless
from unittest.mock import patch
from uuid import UUID

from diskcache import Cache, FanoutCache
from diskcache.core import MODE_PICKLE, MODE_TEXT
from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from alfred_ai.safe_cache import CacheIntegrityError, SafeDisk, StrictDisk
from alfred_ai.services.throttling import STORE, reserve_attempts
from alfred_private_storage import PrivateStorageUnavailable, private_directory, replace_acl, verify_private


class Planted:
    """Unpickling this creates a marker folder, which is how these tests would see code running."""

    def __init__(self, marker):
        self.marker = str(marker)

    def __reduce__(self):
        return (os.mkdir, (self.marker,))


class Base(SimpleTestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-safe-cache-", ignore_cleanup_errors=True))).resolve()
        self.marker = self.root / "code-ran"
        # A second line of defence: fail loudly if anything reaches pickle at all.
        self.enterContext(patch("diskcache.core.pickle.load", side_effect=AssertionError("pickle.load was reached")))

    def plant(self, database, key, *, mode=MODE_PICKLE, value=None, filename=None, raw=1, expire=None):
        payload = pickle.dumps(Planted(self.marker)) if value is None and filename is None else value
        with closing(sqlite3.connect(database)) as db, db:
            now = timezone.now().timestamp()
            db.execute("INSERT OR REPLACE INTO Cache(key, raw, store_time, expire_time, access_time, access_count, tag, size, mode, filename, value)"
                       " VALUES(?,?,?,?,?,0,NULL,0,?,?,?)", (key, raw, now, expire, now, mode, filename, payload))

    def assert_nothing_ran(self):
        self.assertFalse(self.marker.exists(), "planted pickle was executed")


class SafeDiskTests(Base):
    def cache(self, disk=SafeDisk):
        return Cache(str(self.root / "cache"), disk=disk)

    def test_values_round_trip_with_their_types(self):
        samples = [None, True, False, 0, -7, 2 ** 70, 1.5, "text", "1", "null", "", [1, [2]], {"a": {"b": 1}}, (1, 2), {1, 2}, frozenset({3}), {1: "int key"},
                   {"__alfred_cache__": "plain"}, Decimal("12.3400"), date(2026, 11, 1), datetime(2026, 11, 1, 1, 2, tzinfo=utc.utc), time(1, 2), timedelta(days=1, seconds=2),
                   UUID("12345678123456781234567812345678"), b"bytes", {"nested": [Decimal("1.10"), (date(2026, 1, 1),)]}, "x" * 100000, b"y" * 100000]
        with self.cache() as store:
            for index, value in enumerate(samples):
                with self.subTest(value=repr(value)[:40]):
                    store.set(index, value)
                    got = store.get(index)
                    self.assertEqual(got, value)
                    self.assertIs(type(got), type(value))

    def test_increment_and_add_still_work(self):
        with self.cache() as store:
            store.add("n", 0)
            self.assertEqual(store.incr("n"), 1)
            self.assertFalse(store.add("n", 5))

    def test_a_value_with_no_safe_form_is_refused_at_write(self):
        with self.cache() as store, self.assertRaises(TypeError):
            store.set("key", object())

    def test_a_key_needing_pickle_is_refused(self):
        with self.cache() as store, self.assertRaises(TypeError):
            store.set(("tuple", "key"), 1)

    def test_a_planted_pickled_value_is_a_miss_and_never_runs(self):
        with self.cache() as store:
            store.set("real", 1)
            self.plant(self.root / "cache" / "cache.db", "evil")
            self.assertEqual(store.get("evil", "default"), "default")
            self.assertEqual(store.get("real"), 1)
        self.assert_nothing_ran()

    def test_the_read_paths_alfred_uses_treat_a_planted_value_as_a_miss(self):
        with self.cache() as store:
            self.plant(self.root / "cache" / "cache.db", "evil")
            self.assertEqual(store.pop("evil", "default"), "default")
            self.plant(self.root / "cache" / "cache.db", "evil")
            self.assertFalse(store.delete("missing"))
            self.assertTrue(store.delete("evil"))
        self.assert_nothing_ran()

    def test_queue_style_reads_stop_instead_of_running_or_looping(self):
        # shortcut: under SafeDisk these three retry forever on a refused row, because diskcache reads OSError as a
        # lost race. ALFRED never calls them; use StrictDisk if that changes.
        for name, read in (("pull", lambda store: store.pull()), ("peek", lambda store: store.peek()), ("peekitem", lambda store: store.peekitem(last=True))):
            with self.subTest(name=name), Cache(str(self.root / name), disk=StrictDisk) as store:
                self.plant(self.root / name / "cache.db", 500000000000000, raw=1)
                with self.assertRaises(CacheIntegrityError):
                    read(store)
        self.assert_nothing_ran()

    def test_alfred_never_calls_the_queue_style_reads(self):
        root = Path(__file__).resolve().parents[1]
        for path in [*(root / "apps").rglob("*.py"), *(root / "alfred_ai").rglob("*.py")]:
            if path.name != "safe_cache.py" and "migrations" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="replace")
                if "cache" in text.lower() and "diskcache" in text:
                    self.assertNotRegex(text, r"\b(?:store|cache)\.(?:pull|peek|peekitem)\(", str(path))

    def test_a_planted_pickled_file_never_runs(self):
        with self.cache() as store:
            (self.root / "cache" / "evil.val").write_bytes(pickle.dumps(Planted(self.marker)))
            self.plant(self.root / "cache" / "cache.db", "evil-file", filename="evil.val", value=None)
            self.assertIsNone(store.get("evil-file"))
        self.assert_nothing_ran()

    def test_a_planted_pickled_key_never_runs(self):
        with self.cache() as store:
            self.plant(self.root / "cache" / "cache.db", sqlite3.Binary(pickle.dumps(Planted(self.marker))), raw=0, mode=1, value=1)
            with self.assertRaises(OSError):
                list(store)
        self.assert_nothing_ran()

    def test_a_planted_file_path_cannot_leave_the_cache(self):
        outside = self.root / "outside.txt"
        outside.write_text('"secret"', encoding="utf-8")
        with self.cache() as store:
            self.plant(self.root / "cache" / "cache.db", "escape", mode=MODE_TEXT, filename="../outside.txt", value=None)
            self.assertEqual(store.get("escape", "default"), "default")
            store.delete("escape")
        self.assertEqual(outside.read_text(encoding="utf-8"), '"secret"')

    def test_corrupt_text_is_a_miss(self):
        with self.cache() as store:
            for number, text in enumerate(("{not json", '{"__alfred_cache__":"unknown","v":1}', '{"__alfred_cache__":"decimal","v":"x"}')):
                self.plant(self.root / "cache" / "cache.db", f"bad{number}", mode=1, value=text)
                self.assertEqual(store.get(f"bad{number}", "default"), "default")

    def test_strict_disk_reports_instead_of_missing(self):
        with self.cache(StrictDisk) as store:
            self.plant(self.root / "cache" / "cache.db", "evil")
            with self.assertRaises(CacheIntegrityError):
                store.get("evil", "default")
        self.assert_nothing_ran()

    def test_the_django_backend_refuses_a_planted_value(self):
        from diskcache import DjangoCache
        cache = DjangoCache(str(self.root / "django"), {"SHARDS": 1, "DATABASE_TIMEOUT": 5, "TIMEOUT": 300, "KEY_PREFIX": "alfred", "OPTIONS": {"disk": SafeDisk}})
        cache.set("real", {"amount": Decimal("1.50")})
        self.assertEqual(cache.get("real"), {"amount": Decimal("1.50")})
        database = next((self.root / "django").rglob("cache.db"))
        self.plant(database, cache.make_key("evil"))
        self.assertEqual(cache.get("evil", "default"), "default")
        cache.close()
        self.assert_nothing_ran()

    def test_native_settings_use_this_disk_in_a_new_folder(self):
        source = (Path(__file__).resolve().parents[1] / "alfred_ai" / "native_settings.py").read_text(encoding="utf-8")
        self.assertIn('"disk": SafeDisk', source)
        self.assertIn('"cache" / "json-v1"', source)


class ThrottlingStoreTests(Base):
    BUCKET = [(("scope", "user"), 2, 60)]

    def database(self):
        return self.root / "limits" / STORE / "cache.db"

    def reserve(self, buckets=None):
        return reserve_attempts(str(self.root / "limits"), buckets or self.BUCKET)

    def key(self):
        return json.dumps(self.BUCKET[0][0], sort_keys=True)

    def test_records_are_json_text_under_a_text_key(self):
        self.assertEqual(self.reserve(), 0)
        with closing(sqlite3.connect(self.database())) as db:
            key, raw, mode, value = db.execute("select key, raw, mode, value from Cache").fetchone()
        self.assertEqual((key, raw), (self.key(), 1))
        self.assertNotEqual(mode, MODE_PICKLE)
        self.assertEqual(len(json.loads(value)), 1)

    def test_a_planted_record_fails_closed_runs_nothing_and_then_recovers(self):
        self.assertEqual(self.reserve(), 0)
        self.plant(self.database(), self.key())
        self.assertEqual(self.reserve(), 60)
        self.assert_nothing_ran()
        self.assertEqual(self.reserve(), 0)

    def test_a_record_of_the_wrong_shape_fails_closed(self):
        for text in ('"text"', '{"a":1}', '["text"]', "[NaN]", "{bad"):
            with self.subTest(text=text):
                self.assertIs(self.reserve() >= 0, True)
                self.plant(self.database(), self.key(), mode=1, value=text)
                self.assertEqual(self.reserve(), 60)

    def test_older_pickled_rows_beside_the_new_folder_are_never_opened(self):
        (self.root / "limits").mkdir()
        with Cache(str(self.root / "limits")) as legacy:
            legacy.set(("scope", "user"), [1.0])
        self.plant(self.root / "limits" / "cache.db", "evil")
        before = (self.root / "limits" / "cache.db").read_bytes()
        with patch("alfred_ai.services.throttling.private_directory", side_effect=lambda path: Path(path).mkdir(exist_ok=True) or Path(path)):
            self.assertEqual(self.reserve(), 0)
        self.assertEqual((self.root / "limits" / "cache.db").read_bytes(), before)
        self.assert_nothing_ran()

    def test_limit_expiry_and_restart(self):
        self.assertEqual(self.reserve(), 0)
        self.assertEqual(self.reserve(), 0)
        self.assertGreater(self.reserve(), 0)
        code = ("import os,sys,django;os.environ['DJANGO_SETTINGS_MODULE']='alfred_ai.settings';django.setup();"
                "from alfred_ai.services.throttling import reserve_attempts;"
                f"print(reserve_attempts({str(self.root / 'limits')!r},[(('scope','user'),2,60)]))")
        fresh = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120, cwd=str(Path(__file__).resolve().parents[1]))
        self.assertEqual(fresh.returncode, 0, fresh.stderr[-500:])
        self.assertGreater(float(fresh.stdout.strip().splitlines()[-1]), 0)
        later = timezone.now() + timedelta(seconds=61)
        with patch("alfred_ai.services.throttling.timezone.now", return_value=later):
            self.assertEqual(self.reserve(), 0)

    def test_a_corrupt_store_fails_closed(self):
        self.assertEqual(self.reserve(), 0)
        self.database().write_bytes(b"this is not a database")
        with self.assertRaises(sqlite3.DatabaseError):
            self.reserve()


@skipUnless(os.name == "nt", "Windows access control")
class CachePermissionTests(SimpleTestCase):
    LOOSE = "D:P(A;OICI;FA;;;WD)"

    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory(prefix="alfred-cache-acl-", ignore_cleanup_errors=True))).resolve()

    def loose(self, name):
        path = self.root / name
        path.mkdir()
        (path / "existing.txt").write_text("x", encoding="utf-8")
        replace_acl(path, self.LOOSE)
        return path

    def test_a_new_configured_location_is_created_private(self):
        path = self.root / "external" / "limits"
        self.assertEqual(reserve_attempts(str(path), [("key", 1, 60)]), 0)
        self.assertTrue(verify_private(path))
        self.assertTrue(verify_private(path / STORE))
        self.assertTrue(verify_private(path / STORE / "cache.db"))

    def test_a_location_others_can_write_is_refused(self):
        with self.assertRaises(PrivateStorageUnavailable):
            reserve_attempts(str(self.loose("limits")), [("key", 1, 60)])

    def test_loosening_the_store_later_is_refused(self):
        path = self.root / "limits"
        self.assertEqual(reserve_attempts(str(path), [("key", 2, 60)]), 0)
        replace_acl(path / STORE, self.LOOSE)
        with self.assertRaises(PrivateStorageUnavailable):
            reserve_attempts(str(path), [("key", 2, 60)])

    def test_startup_refuses_a_loose_throttle_or_invitation_folder(self):
        config = apps.get_app_config("users")
        for setting in ("ALFRED_ABUSE_THROTTLE_DIR", "ALFRED_FAMILY_INVITE_THROTTLE_DIR"):
            with self.subTest(setting=setting), override_settings(**{setting: str(self.loose(setting))}), self.assertRaises(ImproperlyConfigured):
                config.ready()

    def test_shared_cache_shards_are_private(self):
        path = self.root / "shared"
        private_directory(path)
        cache = FanoutCache(str(path), shards=2, disk=SafeDisk)
        cache.set("key", "value")
        cache.close()
        shards = [item for item in path.iterdir() if item.is_dir()]
        self.assertEqual(len(shards), 2)
        self.assertTrue(all(verify_private(item) and verify_private(item / "cache.db") for item in shards))
