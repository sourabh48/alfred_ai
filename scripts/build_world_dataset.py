"""Build static/vendor/world/world.json from a pinned dr5hn countries-states-cities release.

Downloads only from raw.githubusercontent.com at the pinned tag, refuses files whose
SHA-256 differs, and keeps just the fields Travel needs. Pass a folder that already
holds countries.json and states.json to skip the download (the hashes are still checked).
"""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

TAG = "v6.2.0"
BASE_URL = f"https://raw.githubusercontent.com/dr5hn/countries-states-cities-database/{TAG}/json/"
SHA256 = {
    "countries.json": "43df689ce9303665de103f0643b2b633adb1dca8320bf49db5d1df4b30c3a182",
    "states.json": "9ff8201f31e374ba2a1173cd3203d45fc72a365d87e446d3c66ea9d90bda34c7",
}
OUTPUT = Path(__file__).resolve().parent.parent / "static" / "vendor" / "world" / "world.json"


def _load(name, folder):
    data = (folder / name).read_bytes() if folder else urllib.request.urlopen(BASE_URL + name, timeout=60).read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != SHA256[name]:
        raise SystemExit(f"{name}: SHA-256 {digest} does not match the pinned {SHA256[name]}")
    return json.loads(data.decode("utf-8"))


def _coord(value):
    return round(float(value), 2) if value not in (None, "") else None


def build(folder=None):
    countries = _load("countries.json", folder)
    states = _load("states.json", folder)
    return {
        "source": f"dr5hn/countries-states-cities-database {TAG} (ODbL-1.0)",
        "countries": [[c["iso2"], c["iso3"], c["name"], c.get("emoji") or "", _coord(c.get("latitude")), _coord(c.get("longitude"))]
                      for c in countries],
        # Top-level subdivisions only: child rows (counties under England, etc.) are not "states".
        "states": [[s["country_code"], s.get("iso2") or "", s["name"], _coord(s.get("latitude")), _coord(s.get("longitude"))]
                   for s in states if s.get("parent_id") is None],
    }


if __name__ == "__main__":
    payload = build(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUTPUT}: {len(payload['countries'])} countries, {len(payload['states'])} states")
