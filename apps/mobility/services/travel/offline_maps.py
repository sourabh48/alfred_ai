"""Offline country maps: one country's vector tiles cut from the free Protomaps OpenStreetMap build.

Two steps, both started by the owner in Settings. Checking the size reads only the build's tile
index. The map itself downloads only after the owner confirmed that exact size. Each country is
one SQLite file under ALFRED_DATA_DIR/maps; removing a country deletes only its file. Requests
carry byte ranges of the public build, never anything about the owner or their trips.
"""
from __future__ import annotations

import gzip
import json
import math
import os
import sqlite3
import struct
import threading
import time
from bisect import bisect_right
from datetime import datetime, timezone as dt_timezone
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

from django.conf import settings

from alfred_ai.services.public_http import PublicHTTPError, request

BUILDS = "https://build-metadata.protomaps.dev/builds.json"
BUILD = "https://build.protomaps.com/"
MAX_ZOOM = 14  # the build goes to 15; the map overzooms 14, so streets stay readable at about half the size
CHUNK = 4_000_000  # one public_http request must finish within its 20 seconds
ATTRIBUTION = "© OpenStreetMap contributors, Protomaps"
COUNTRIES = Path(__file__).with_name("country_boxes.json")
_lock = threading.Lock()
_running: set[str] = set()
# shortcut: job state lives in this process; after a restart the owner checks the size again and the download resumes
_jobs: dict[str, dict] = {}


# --- PMTiles v3 (https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md) ---

def _rotate(n, x, y, rx, ry):
    if ry == 0:
        if rx == 1:
            x, y = n - 1 - x, n - 1 - y
        x, y = y, x
    return x, y


def zxy_to_id(z, x, y):
    n, d, s = 2 ** z, 0, 2 ** z // 2
    while s > 0:
        rx, ry = int(x & s > 0), int(y & s > 0)
        d += s * s * ((3 * rx) ^ ry)
        x, y = _rotate(n, x, y, rx, ry)
        s //= 2
    return (4 ** z - 1) // 3 + d


def id_to_zxy(tile_id):
    z = 0
    while tile_id >= (4 ** (z + 1) - 1) // 3:
        z += 1
    t, n, x, y, s = tile_id - (4 ** z - 1) // 3, 2 ** z, 0, 0, 1
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        x, y = _rotate(s, x, y, rx, ry)
        x, y, t, s = x + s * rx, y + s * ry, t // 4, s * 2
    return z, x, y


def header(raw):
    if len(raw) < 127 or raw[:7] != b"PMTiles" or raw[7] != 3:
        raise PublicHTTPError("unexpected_build")
    names = ("root_offset", "root_length", "metadata_offset", "metadata_length", "leaf_offset", "leaf_length",
             "data_offset", "data_length", "addressed_tiles", "tile_entries", "tile_contents")
    h = dict(zip(names, struct.unpack_from("<11Q", raw, 8)))
    h.update(clustered=raw[96], internal_compression=raw[97], tile_compression=raw[98], tile_type=raw[99],
             min_zoom=raw[100], max_zoom=raw[101])
    return h


def _varints(raw):
    value = shift = 0
    for byte in raw:
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            yield value
            value = shift = 0


def directory(raw, compression):
    """Entries (tile_id, offset, length, run_length); run_length 0 points to a leaf directory."""
    if compression == 2:
        raw = gzip.decompress(raw)
    elif compression != 1:
        raise PublicHTTPError("unexpected_build")
    try:
        numbers = _varints(raw)
        count = next(numbers)
        ids, last = [], 0
        for _ in range(count):
            last += next(numbers)
            ids.append(last)
        runs = [next(numbers) for _ in range(count)]
        lengths = [next(numbers) for _ in range(count)]
        entries = []
        for i in range(count):
            value = next(numbers)
            offset = entries[-1][1] + entries[-1][2] if value == 0 and i > 0 else value - 1
            entries.append((ids[i], offset, lengths[i], runs[i]))
    except StopIteration:
        raise PublicHTTPError("unexpected_build") from None
    return entries


# --- Which tiles a country needs ---

def _tile_box(z, x, y):
    n = 2 ** z
    lat = lambda v: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * v / n))))
    return x / n * 360 - 180, lat(y + 1), (x + 1) / n * 360 - 180, lat(y)


def wanted(boxes, max_zoom=MAX_ZOOM):
    """Sorted, merged tile-id ranges covering the boxes (west, south, east, north) on every zoom up to max_zoom."""
    ranges = []

    def visit(z, x, y):
        w, s, e, n = _tile_box(z, x, y)
        hits = [b for b in boxes if b[0] < e and b[2] > w and b[1] < n and b[3] > s]
        if not hits:
            return
        tile = zxy_to_id(z, x, y)
        ranges.append((tile, tile))
        if z == max_zoom:
            return
        if any(b[0] <= w and b[2] >= e and b[1] <= s and b[3] >= n for b in hits):
            # Hilbert order keeps each deeper zoom of one tile in one contiguous run of ids.
            position = tile - (4 ** z - 1) // 3
            for k in range(1, max_zoom - z + 1):
                base = (4 ** (z + k) - 1) // 3
                ranges.append((base + position * 4 ** k, base + (position + 1) * 4 ** k - 1))
            return
        for dx in (0, 1):
            for dy in (0, 1):
                visit(z + 1, 2 * x + dx, 2 * y + dy)

    visit(0, 0, 0)
    merged = []
    for low, high in sorted(ranges):
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def _overlaps(ranges, low, high):
    i = bisect_right(ranges, (high, math.inf)) - 1
    return i >= 0 and ranges[i][1] >= low


def _fetch(build, start, length):
    response = request("GET", BUILD + build, headers={"Range": f"bytes={start}-{start + length - 1}"},
                       content_types=("application/octet-stream",), accepted_statuses=(206,), max_bytes=length)
    if len(response.content) != length:
        raise PublicHTTPError("incomplete_response")
    return response.content


def latest_build():
    builds = request("GET", BUILDS, max_bytes=2_000_000).json()
    good = sorted(str(b.get("key")) for b in builds if isinstance(b, dict) and str(b.get("key", "")).endswith(".pmtiles"))
    if not good or "/" in good[-1]:
        raise PublicHTTPError("api_error")
    return good[-1]


def plan(boxes, sink, build=None, fetch=None):
    """Read only the build's index and hand each batch of this country's tile entries to sink."""
    fetch = fetch or _fetch
    build = build or latest_build()
    h = header(_retry(lambda: fetch(build, 0, 127)))
    if h["tile_type"] != 1 or h["tile_compression"] != 2 or not h["clustered"]:
        raise PublicHTTPError("unexpected_build")
    ranges = wanted(boxes, min(MAX_ZOOM, h["max_zoom"]))
    read = lambda offset, length: directory(_retry(lambda: fetch(build, offset, length)), h["internal_compression"])
    pending = [read(h["root_offset"], h["root_length"])]
    while pending:
        entries, tiles = pending.pop(), []
        for i, (tile, offset, length, run) in enumerate(entries):
            if run:
                if _overlaps(ranges, tile, tile + run - 1):
                    tiles.append((tile, run, offset, length))
                continue
            end = entries[i + 1][0] - 1 if i + 1 < len(entries) else 2 ** 63
            if _overlaps(ranges, tile, end):
                pending.append(read(h["leaf_offset"] + offset, length))
        sink(tiles)
    return {"build": build, "data_offset": h["data_offset"]}


def _retry(call, tries=3):
    for attempt in range(tries):
        try:
            return call()
        except PublicHTTPError as exc:
            if attempt == tries - 1 or exc.code in {"authorization_failed", "unsafe_url", "redirect_blocked", "unexpected_build"}:
                raise
            time.sleep(2 * (attempt + 1))


# --- Countries and files ---

@lru_cache(maxsize=1)
def countries():
    return json.loads(COUNTRIES.read_text(encoding="utf-8"))["countries"]


def home_country():
    """The country of this PC's time zone (ALFRED follows the Windows zone), or "" when none matches."""
    try:
        data = files("tzdata").joinpath("zoneinfo")
        rows = data.joinpath("zone.tab").read_text(encoding="utf-8").splitlines()
        links = dict(line.split()[2:0:-1] for line in data.joinpath("tzdata.zi").read_text(encoding="utf-8").splitlines()
                     if line.startswith("L ") and len(line.split()) == 3)
    except (ModuleNotFoundError, OSError):
        return ""
    zone = links.get(str(settings.TIME_ZONE), str(settings.TIME_ZONE))  # Windows gives old names such as Asia/Calcutta
    for row in rows:
        parts = row.split("\t")
        if not row.startswith("#") and len(parts) >= 3 and parts[2] == zone and parts[0] in countries():
            return parts[0]
    return ""


def folder():
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "maps"


def _file(code, part=False):
    if code not in countries():
        raise ValueError("Choose a country from the list.")
    return folder() / f"{code}{'.part' if part else ''}.sqlite"


def installed():
    return sorted(p.stem for p in folder().glob("*.sqlite") if p.stem in countries())


def _open_part(code):
    folder().mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(_file(code, part=True))
    db.executescript("CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);"
                     "CREATE TABLE IF NOT EXISTS blobs(offset INTEGER PRIMARY KEY, data BLOB NOT NULL);"
                     "CREATE TABLE IF NOT EXISTS tiles(id INTEGER PRIMARY KEY, run INTEGER NOT NULL, offset INTEGER NOT NULL, length INTEGER NOT NULL);"
                     "CREATE INDEX IF NOT EXISTS tiles_offset ON tiles(offset, length);")
    return db


def _meta(db, key):
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row[0] if row else None


# --- What the owner does in Settings ---

def status():
    rows = []
    for code in sorted(set(installed()) | set(_jobs)):
        path, job = _file(code), _jobs.get(code, {})
        rows.append({"code": code, "name": countries()[code]["name"], "installed_bytes": path.stat().st_size if path.exists() else 0,
                     **{k: job[k] for k in ("state", "bytes", "done", "build", "error") if k in job}})
    return {"countries": [{"code": c, "name": v["name"]} for c, v in sorted(countries().items(), key=lambda i: i[1]["name"])],
            "home": home_country(), "maps": rows, "attribution": ATTRIBUTION, "max_zoom": MAX_ZOOM}


def _start(code, job, work):
    with _lock:
        if code in _running:
            raise ValueError("This country's map is already being checked or downloaded.")
        _running.add(code)
        _jobs[code] = job

    def go():
        try:
            work()
        except Exception as exc:  # noqa: BLE001 - shown as a plain message; files stay as they were
            if _jobs.get(code, {}).get("cancel"):
                _file(code, part=True).unlink(missing_ok=True)
                _jobs.pop(code, None)
            else:
                _jobs[code] = {**_jobs.get(code, {}), "state": "failed",
                               "error": exc.code if isinstance(exc, PublicHTTPError) else "failed"}
        finally:
            with _lock:
                _running.discard(code)
    threading.Thread(target=go, daemon=True, name=f"offline-map-{code}").start()


def check_size(code, fetch=None):
    """Step one: read the index and record the exact download size. No map data is downloaded."""
    boxes = countries()[_file(code).stem]["boxes"]

    def work():
        db = _open_part(code)
        try:
            with db:
                db.execute("DELETE FROM tiles")
            def sink(tiles):
                if _jobs.get(code, {}).get("cancel"):
                    raise PublicHTTPError("cancelled")
                with db:
                    db.executemany("INSERT OR REPLACE INTO tiles VALUES(?,?,?,?)", tiles)
            p = plan(boxes, sink, fetch=fetch)
            size = db.execute("SELECT COALESCE(SUM(length),0) FROM (SELECT DISTINCT offset, length FROM tiles)").fetchone()[0]
            with db:
                if _meta(db, "build") not in (None, p["build"]):
                    db.execute("DELETE FROM blobs")  # a newer build moved every tile; an older partial download is useless
                db.executemany("INSERT OR REPLACE INTO meta VALUES(?,?)", [("build", p["build"]), ("data_offset", str(p["data_offset"])),
                               ("bytes", str(size)), ("attribution", ATTRIBUTION), ("max_zoom", str(MAX_ZOOM))])
        finally:
            db.close()
        _jobs[code] = {"state": "ready", "bytes": size, "build": p["build"]}
    _start(code, {"state": "sizing"}, work)


def download(code, build, size, fetch=None):
    """Step two, only for the exact build and size the owner confirmed."""
    job = _jobs.get(code, {})
    if job.get("state") != "ready" or job.get("build") != build or job.get("bytes") != size:
        raise ValueError("Check the size again, then confirm the download.")
    _start(code, {"state": "downloading", "bytes": size, "build": build, "done": 0},
           lambda: _store(code, lambda done: _jobs[code].update(done=done), fetch or _fetch))


def _store(code, progress, fetch):
    db = _open_part(code)
    try:
        build, data_offset = _meta(db, "build"), int(_meta(db, "data_offset"))
        done = db.execute("SELECT COALESCE(SUM(length(data)),0) FROM blobs").fetchone()[0]  # resume what an earlier try saved
        after = -1
        while True:
            spans = db.execute("SELECT DISTINCT offset, length FROM tiles WHERE offset>? AND offset NOT IN (SELECT offset FROM blobs) "
                               "ORDER BY offset LIMIT 5000", (after,)).fetchall()
            if not spans:
                break
            after = spans[-1][0]
            group = []
            for span in spans + [None]:
                if group and (span is None or span[0] != group[-1][0] + group[-1][1] or span[0] + span[1] - group[0][0] > CHUNK):
                    if _jobs.get(code, {}).get("cancel"):
                        raise PublicHTTPError("cancelled")
                    start = group[0][0]
                    raw = _retry(lambda: fetch(build, data_offset + start, group[-1][0] + group[-1][1] - start))
                    rows = [(o, raw[o - start:o - start + n]) for o, n in group]
                    if any(data[:2] != b"\x1f\x8b" for _, data in rows):
                        raise PublicHTTPError("unexpected_build")
                    with db:
                        db.executemany("INSERT OR REPLACE INTO blobs VALUES(?,?)", rows)
                    done += sum(n for _, n in group)
                    progress(done)
                    group = []
                if span:
                    group.append(span)
        with db:
            db.execute("INSERT OR REPLACE INTO meta VALUES('finished',?)", (datetime.now(dt_timezone.utc).isoformat(),))
    finally:
        db.close()
    _file(code, part=True).replace(_file(code))
    _jobs.pop(code, None)


def remove(code):
    """Delete only this country's map, a partial download included. Other countries stay."""
    _file(code)
    with _lock:
        if code in _running:
            _jobs.setdefault(code, {})["cancel"] = True  # the worker deletes the partial file when it stops
            return "stopping"
        for path in (_file(code), _file(code, part=True)):
            path.unlink(missing_ok=True)
        _jobs.pop(code, None)
    return "removed"


def tile(z, x, y):
    """A stored gzip vector tile from any downloaded country, or None."""
    if not (0 <= z <= MAX_ZOOM and 0 <= x < 2 ** z and 0 <= y < 2 ** z):
        return None
    tile_id = zxy_to_id(z, x, y)
    for code in installed():
        db = sqlite3.connect(f"{_file(code).as_uri()}?mode=ro", uri=True)
        try:
            row = db.execute("SELECT t.id, t.run, b.data FROM tiles t JOIN blobs b ON b.offset=t.offset "
                             "WHERE t.id<=? ORDER BY t.id DESC LIMIT 1", (tile_id,)).fetchone()
        except sqlite3.DatabaseError:
            row = None
        finally:
            db.close()
        if row and tile_id < row[0] + row[1]:
            return row[2]
    return None
