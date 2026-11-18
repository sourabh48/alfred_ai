"""US visa sponsor history (career-ops fe9cb888, MIT, the H-1B sponsor signal; owner approval 2026-11-18).

The US Department of Labor publishes yearly LCA disclosure files, but its site refuses automated downloads, so ALFRED never
fetches them. The owner downloads a file in the browser, puts it in ALFRED's `imports` folder, and ALFRED reads it here,
on this PC, into a small per-employer summary. A history of filings is evidence an employer has sponsored before; it is
not a promise to sponsor anyone, and without PERM files it says nothing about green cards.
"""
from __future__ import annotations

import csv
import json
import os
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path
from xml.etree.ElementTree import iterparse

from django.conf import settings
from django.utils import timezone

DOL_PAGE = "https://www.dol.gov/agencies/eta/foreign-labor/performance"
COLUMNS = ("EMPLOYER_NAME", "CASE_STATUS", "RECEIVED_DATE", "VISA_CLASS", "SECONDARY_ENTITY")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SUFFIX = re.compile(r"\b(inc|llc|llp|ltd|limited|pvt|private|corp|corporation|co|company|plc|lp|na|usa|us|the)\b")


def data_dir() -> Path:
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR)


def imports_dir() -> Path:
    return data_dir() / "imports"


def index_path() -> Path:
    return data_dir() / "artifacts" / "career" / "h1b-index.json"


def key(name: str) -> str:
    return " ".join(SUFFIX.sub(" ", re.sub(r"[^a-z0-9 ]", " ", (name or "").casefold())).split())


def _day(value: str) -> str:
    value = (value or "").strip()
    if re.fullmatch(r"\d+(\.\d+)?", value):  # an Excel date serial
        return (date(1899, 12, 30) + timedelta(days=int(float(value)))).isoformat()
    if re.match(r"\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    hit = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
    return f"{hit[3]}-{int(hit[1]):02d}-{int(hit[2]):02d}" if hit else ""


def _xlsx_rows(path: Path):
    """Rows of the first sheet as lists of strings, streamed so a large file never sits in memory as a table."""
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            with book.open("xl/sharedStrings.xml") as handle:
                for _, element in iterparse(handle):
                    if element.tag == f"{NS}si":
                        shared.append("".join(t.text or "" for t in element.iter(f"{NS}t")))
                        element.clear()
        sheet = next(n for n in sorted(book.namelist()) if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        with book.open(sheet) as handle:
            for _, element in iterparse(handle):
                if element.tag != f"{NS}row":
                    continue
                row = {}
                for cell in element.iter(f"{NS}c"):
                    column = re.sub(r"\d", "", cell.get("r", ""))
                    index = 0
                    for letter in column:
                        index = index * 26 + ord(letter) - 64
                    kind, value = cell.get("t"), cell.find(f"{NS}v")
                    if kind == "inlineStr":
                        text = "".join(t.text or "" for t in cell.iter(f"{NS}t"))
                    elif value is None:
                        text = ""
                    else:
                        text = shared[int(value.text)] if kind == "s" else value.text or ""
                    row[index - 1] = text
                element.clear()
                yield [row.get(i, "") for i in range(max(row) + 1)] if row else []


def _csv_rows(path: Path):
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        yield from csv.reader(handle)


def files() -> list:
    folder = imports_dir()
    return sorted(p for p in folder.glob("*") if p.suffix.lower() in {".xlsx", ".csv"} and "lca" in p.name.casefold()) \
        if folder.is_dir() else []


def build_index() -> dict:
    """Read every LCA file in the imports folder into per-employer H-1B counts and save them under artifacts."""
    found = files()
    if not found:
        raise ValueError(f"No LCA file found. Download one from {DOL_PAGE} in your browser and put it in {imports_dir()}.")
    employers, read = {}, []
    for path in found:
        rows = _xlsx_rows(path) if path.suffix.lower() == ".xlsx" else _csv_rows(path)
        header = [h.strip().upper() for h in next(rows, [])]
        if any(c not in header for c in COLUMNS):
            raise ValueError(f"{path.name} is not an LCA disclosure file (missing {', '.join(c for c in COLUMNS if c not in header)}).")
        at = {c: header.index(c) for c in COLUMNS}
        count = 0
        for row in rows:
            value = lambda c: row[at[c]] if at[c] < len(row) else ""
            name = key(value("EMPLOYER_NAME"))
            if not name or value("VISA_CLASS").strip().upper() != "H-1B":
                continue
            entry = employers.setdefault(name, {"name": value("EMPLOYER_NAME").strip()[:160], "filings": 0, "certified": 0,
                                                "secondary": 0, "latest": ""})
            entry["filings"] += 1
            entry["certified"] += value("CASE_STATUS").strip().upper().startswith("CERTIFIED")
            entry["secondary"] += value("SECONDARY_ENTITY").strip().upper() in {"Y", "YES"}
            entry["latest"] = max(entry["latest"], _day(value("RECEIVED_DATE")))
            count += 1
        read.append({"file": path.name, "h1b_rows": count})
    index = {"built_at": timezone.now().isoformat(), "files": read, "employers": employers}
    index_path().parent.mkdir(parents=True, exist_ok=True)
    index_path().write_text(json.dumps(index), encoding="utf-8")
    return status()


def _index() -> dict | None:
    try:
        return json.loads(index_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def status() -> dict:
    index = _index()
    return {"imports_folder": str(imports_dir()), "dol_page": DOL_PAGE, "waiting": [p.name for p in files()],
            "built_at": index["built_at"] if index else None, "files": index["files"] if index else [],
            "employers": len(index["employers"]) if index else 0}


def tier(entry: dict, today: date) -> tuple[str, str]:
    share = entry["secondary"] / entry["filings"] if entry["filings"] else 0
    recent = entry["latest"] and entry["latest"] >= (today - timedelta(days=730)).isoformat()
    if share >= 0.5:
        return "staffing", (f"{share:.0%} of its filings place workers at another company's site, a pattern of staffing firms. "
                            "Ask who the end client is.")
    if entry["filings"] >= 5 and recent:
        return "active", "Files H-1B applications regularly and recently."
    return "weak", "Few or old filings: it has sponsored, but rarely or not lately. Ask before you rely on it."


def check(company: str) -> dict:
    index = _index()
    if not index:
        raise ValueError("Import an LCA file first.")
    wanted = key(company)
    if not wanted:
        raise ValueError("Enter a company name.")
    employers = index["employers"]
    matches = [employers[wanted]] if wanted in employers else \
        sorted((e for k, e in employers.items() if k.startswith(wanted + " ")), key=lambda e: -e["filings"])[:5]
    today = timezone.localdate()
    out = []
    for entry in matches:
        level, why = tier(entry, today)
        out.append({**entry, "tier": level, "why": why})
    return {"company": company, "matches": out, "files": [f["file"] for f in index["files"]],
            "basis": ("No filings found in the imported files. That is not proof the company never sponsors: the name may be "
                      "spelt differently, or its filings may be in another year's file." if not out else
                      "Counts from the DOL LCA files you imported. Past filings are evidence, not a promise to sponsor you, "
                      "and say nothing about green cards. This is not legal advice.")}
