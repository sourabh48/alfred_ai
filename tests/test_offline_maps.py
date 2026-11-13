"""Offline country maps: the owner sees the exact size before anything downloads, a download resumes, removing one
country leaves the others, only the manager can change maps, and tiles are served to signed-in people only.
Uses a small synthetic PMTiles archive; nothing goes to the network."""
import gzip
import json
import os
import struct
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from alfred_ai.services.public_http import PublicHTTPError
from apps.mobility.services.travel import offline_maps as om
from apps.mobility.services.travel.mapping import map_configuration

BOX = {"XX": {"name": "Testland", "boxes": [[0, 0, 90, 60]]}, "YY": {"name": "Otherland", "boxes": [[-90, -60, 0, 0]]}}


def varint(n):
    out = bytearray()
    while True:
        out.append((n & 0x7F) | (0x80 if n > 0x7F else 0))
        n >>= 7
        if not n:
            return bytes(out)


def packed(entries):
    out, last = varint(len(entries)), 0
    for tile, *_ in entries:
        out, last = out + varint(tile - last), tile
    for field in (3, 2):
        out += b"".join(varint(e[field]) for e in entries)
    return gzip.compress(out + b"".join(varint(e[1] + 1) for e in entries))


def archive():
    """Tiles 0-20 (zooms 0-2): the root lists 0-4 and one leaf holds 5-20; the target z2 tile shares its data with its neighbour."""
    target = om.zxy_to_id(2, 2, 1)
    data, entries, blobs = b"", [], {}
    for tile in range(21):
        if tile == target + 1:
            continue
        blob = gzip.compress(f"tile-{tile}".encode())
        blobs[tile] = blob
        entries.append((tile, len(data), len(blob), 2 if tile == target else 1))
        data += blob
    leaf = packed([e for e in entries if e[0] >= 5])
    root = packed([e for e in entries if e[0] < 5] + [(5, 0, len(leaf), 0)])
    head = bytearray(127)
    head[:8] = b"PMTiles\x03"
    struct.pack_into("<11Q", head, 8, 127, len(root), 0, 0, 127 + len(root), len(leaf), 127 + len(root) + len(leaf),
                     len(data), 21, len(entries), len(entries))
    head[96:102] = bytes([1, 2, 2, 1, 0, 2])
    return bytes(head) + root + leaf + data, blobs, target


class Now:
    """Runs the worker at once so the test sees its result."""
    def __init__(self, target, daemon, name):
        self.target = target

    def start(self):
        self.target()


class OfflineMapTests(TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        for p in (patch.dict(os.environ, {"ALFRED_DATA_DIR": self.folder.name}), patch.object(om, "countries", return_value=BOX),
                  patch.object(om, "MAX_ZOOM", 2), patch.object(om.threading, "Thread", Now),
                  patch.object(om, "latest_build", return_value="20990101.pmtiles"), patch.object(om.time, "sleep")):
            p.start()
            self.addCleanup(p.stop)
        om._jobs.clear()
        self.raw, self.blobs, self.target = archive()
        self.calls = []

    def fetch(self, build, start, length):
        self.calls.append((start, length))
        return self.raw[start:start + length]

    def test_tile_ids_follow_the_pmtiles_hilbert_order(self):
        for tile, zxy in enumerate([(0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0)]):
            self.assertEqual((om.id_to_zxy(tile), om.zxy_to_id(*zxy)), (zxy, tile))
        self.assertTrue(all(om.zxy_to_id(*om.id_to_zxy(t)) == t for t in range(0, 30000, 7)))
        # A box that holds a whole tile takes every deeper tile of it as one contiguous range.
        self.assertEqual(om.wanted([[0, 0, 180, 85.06]], 2), [(0, 0), (om.zxy_to_id(1, 1, 0), om.zxy_to_id(1, 1, 0))] +
                         [(5 + 4 * (om.zxy_to_id(1, 1, 0) - 1), 5 + 4 * (om.zxy_to_id(1, 1, 0) - 1) + 3)])

    def test_size_first_then_only_the_confirmed_size_downloads_and_tiles_serve_from_this_pc(self):
        wanted = [0, om.zxy_to_id(1, 1, 0), self.target]
        om.check_size("XX", fetch=self.fetch)
        job = om.status()["maps"][0]
        self.assertEqual((job["state"], job["bytes"]), ("ready", sum(len(self.blobs[t]) for t in wanted)))
        data_offset = om.header(self.raw)["data_offset"]
        self.assertTrue(all(start < data_offset for start, _ in self.calls), "sizing must not download map data")
        self.assertFalse((om.folder() / "XX.sqlite").exists())
        for build, size in (("20990101.pmtiles", job["bytes"] + 1), ("older.pmtiles", job["bytes"])):
            with self.assertRaises(ValueError):
                om.download("XX", build, size, fetch=self.fetch)
        om.download("XX", job["build"], job["bytes"], fetch=self.fetch)
        self.assertEqual(om.installed(), ["XX"])
        self.assertEqual(gzip.decompress(om.tile(2, 2, 1)), f"tile-{self.target}".encode())
        self.assertEqual(om.tile(*om.id_to_zxy(self.target + 1)), self.blobs[self.target])  # shares the target's data
        self.assertIsNone(om.tile(2, 0, 3))  # outside the country
        self.assertIsNone(om.tile(9, 0, 0))
        self.assertEqual(map_configuration()["offline_url"], "/mobility/offline-tiles/{z}/{x}/{y}.mvt")

    def test_a_broken_download_keeps_what_arrived_and_resumes(self):
        om.check_size("XX", fetch=self.fetch)
        job = om.status()["maps"][0]
        data_offset = om.header(self.raw)["data_offset"]
        def flaky(build, start, length):
            if start >= data_offset and any(s >= data_offset for s, _ in self.calls):
                raise PublicHTTPError("network_error")
            return self.fetch(build, start, length)
        with patch.object(om, "CHUNK", 1):
            om.download("XX", job["build"], job["bytes"], fetch=flaky)
            failed = om.status()["maps"][0]
            self.assertEqual((failed["state"], failed["error"]), ("failed", "network_error"))
            self.assertTrue((om.folder() / "XX.part.sqlite").exists())
            om.check_size("XX", fetch=self.fetch)
            self.calls.clear()
            om.download("XX", job["build"], job["bytes"], fetch=self.fetch)
        self.assertEqual(len(self.calls), 2, "only the two tiles that had not arrived are fetched again")
        self.assertEqual(om.installed(), ["XX"])

    def test_removing_one_country_keeps_the_others(self):
        for code in ("XX", "YY"):
            om.check_size(code, fetch=self.fetch)
            job = next(m for m in om.status()["maps"] if m["code"] == code)
            om.download(code, job["build"], job["bytes"], fetch=self.fetch)
        self.assertEqual(om.remove("XX"), "removed")
        self.assertEqual(om.installed(), ["YY"])
        with self.assertRaises(ValueError):
            om.remove("../XX")


class OfflineMapViewTests(TestCase):
    def setUp(self):
        users = get_user_model().objects
        self.owner = users.create_superuser("owner", "owner@example.invalid", "x-synthetic-1")
        self.member = users.create_user("member", "member@example.invalid", "x-synthetic-2")
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        p = patch.dict(os.environ, {"ALFRED_DATA_DIR": self.folder.name})
        p.start()
        self.addCleanup(p.stop)

    def test_only_the_manager_changes_maps_and_tiles_need_a_sign_in(self):
        url = "/api/settings/offline-maps/"
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.get("/mobility/offline-tiles/0/0/0.mvt").status_code, 302)
        self.client.force_login(self.member)
        data = self.client.get(url).json()
        self.assertFalse(data["can_manage"])
        self.assertIn("IN", [c["code"] for c in data["countries"]])
        with patch.object(om, "check_size") as size:
            self.assertEqual(self.client.post(url, json.dumps({"action": "size", "country": "IN"}), content_type="application/json").status_code, 403)
        size.assert_not_called()
        self.assertEqual(self.client.get("/mobility/offline-tiles/0/0/0.mvt").status_code, 404)
        self.client.force_login(self.owner)
        with patch.object(om, "check_size") as size:
            self.assertEqual(self.client.post(url, json.dumps({"action": "size", "country": "IN"}), content_type="application/json").status_code, 200)
        size.assert_called_once_with("IN")
        bad = self.client.post(url, json.dumps({"action": "download", "country": "IN", "build": "x", "bytes": 1}), content_type="application/json")
        self.assertEqual((bad.status_code, bad.json()["detail"]), (400, "Check the size again, then confirm the download."))
        self.assertEqual(self.client.post(url, json.dumps({"action": "remove", "country": "ZZ9"}), content_type="application/json").status_code, 400)
        with patch.object(om, "tile", return_value=b"\x1f\x8bsynthetic"):
            served = self.client.get("/mobility/offline-tiles/3/1/2.mvt")
        self.assertEqual((served.status_code, served["Content-Encoding"], served.content), (200, "gzip", b"\x1f\x8bsynthetic"))

    def test_home_country_follows_the_pc_time_zone(self):
        for zone in ("Asia/Kolkata", "Asia/Calcutta"):  # Windows reports the old name
            with self.settings(TIME_ZONE=zone):
                self.assertEqual(om.home_country(), "IN")
        with self.settings(TIME_ZONE="UTC"):
            self.assertEqual(om.home_country(), "")
