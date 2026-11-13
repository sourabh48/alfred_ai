"""Rebuild apps/mobility/services/travel/country_boxes.json from Natural Earth (public domain).

Usage: python -I scripts/build_country_boxes.py <ne_50m_admin_0_countries.geojson> <ne_50m_admin_0_breakaway_disputed_areas.geojson>
Each country gets the boxes around its land, plus every disputed area that any side claims for it,
so its offline map never leaves out an area the country claims. Nearby boxes are merged.
"""
import json
import re
import sys
from pathlib import Path

SOURCE = "https://github.com/nvkelso/natural-earth-vector/tree/ca96624a56bd078437bca8184e78163e5039ad19/geojson"
GAP = 2.0  # degrees: boxes closer than this become one


def polygons(geometry):
    return geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]


def box(polygon):
    lons, lats = [p[0] for p in polygon[0]], [p[1] for p in polygon[0]]
    return [min(lons), min(lats), max(lons), max(lats)]


def merge(boxes):
    boxes = [list(b) for b in boxes]
    changed = True
    while changed:
        changed = False
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i], boxes[j]
                if a[0] - GAP <= b[2] and b[0] - GAP <= a[2] and a[1] - GAP <= b[3] and b[1] - GAP <= a[3]:
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del boxes[j]
                    changed = True
                    break
            if changed:
                break
    pad = lambda b: [round(max(-180, b[0] - 0.1), 2), round(max(-85, b[1] - 0.1), 2), round(min(180, b[2] + 0.1), 2), round(min(85, b[3] + 0.1), 2)]
    return sorted(pad(b) for b in boxes)


def main(countries_path, disputed_path):
    countries = json.loads(Path(countries_path).read_text(encoding="utf-8"))["features"]
    disputed = json.loads(Path(disputed_path).read_text(encoding="utf-8"))["features"]
    by_a3, names, boxes = {}, {}, {}
    for feature in countries:
        p = feature["properties"]
        code = p["ISO_A2_EH"]
        if not re.fullmatch(r"[A-Z]{2}", code or ""):
            continue
        by_a3[p["ADM0_A3"]] = by_a3[p["ISO_A3_EH"]] = code
        names[code] = p["NAME"]
        boxes.setdefault(code, []).extend(box(poly) for poly in polygons(feature["geometry"]))
    for feature in disputed:
        p = feature["properties"]
        note = str(p.get("NOTE_BRK") or "")
        claimants = {by_a3.get(v) for k, v in p.items() if k in {"SOV_A3", "ADM0_A3"} or k.startswith("ADM0_A3_")}
        claimants |= {code for code, name in names.items() if re.search(rf"\b{re.escape(name)}\b", note)}
        for code in claimants - {None}:
            boxes[code].extend(box(poly) for poly in polygons(feature["geometry"]))
    data = {"source": SOURCE, "countries": {code: {"name": names[code], "boxes": merge(boxes[code])} for code in sorted(names)}}
    out = Path(__file__).resolve().parents[1] / "apps/mobility/services/travel/country_boxes.json"
    out.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(len(data["countries"]), "countries")


if __name__ == "__main__":
    main(*sys.argv[1:3])
