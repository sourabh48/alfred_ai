"""WEALTH2-001: look through the owner's funds using the monthly portfolio file each fund house publishes.

The owner downloads the file (SEBI requires every scheme to disclose its portfolio monthly) and uploads it here;
ALFRED does not fetch it. The file is read in memory. Only when the owner asks to save are the parsed rows kept
(FundPortfolioSnapshot, the latest KEEP_PER_HOLDING per holding); the file itself is never stored. Company, sector and country exposure
comes only from the file's dated weights; rows without a security ISIN (cash, TREPS, receivables, derivatives) and
any weight the file does not account for are shown as opaque. Each security's currency is not in these files, so
currency exposure is reported as unavailable rather than guessed.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

from django.db import transaction

from alfred_ai.services.upload_limits import UploadFormatError, check_document_resources

from ..models import FundPortfolioSnapshot, Investment
from ..money import investment_money

MAX_FILES = 5
MAX_ROWS = 5000
STALE_DAYS = 45
KEEP_PER_HOLDING = 3
PARSER_VERSION = 1
ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec|january|february|march|april|june|july|august|september|october|november|december"
DATE_PATTERNS = (
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?[\s\-/.]+({MONTHS})[a-z]*[\s\-/.,]+(\d{{4}})\b", re.I), ("d", "m", "y")),
    (re.compile(rf"\b({MONTHS})[a-z]*\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.I), ("m", "d", "y")),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), ("y", "m", "d")),
    (re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b"), ("d", "m", "y")),  # Indian day-first
)


class LookThroughError(ValueError):
    pass


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _xml(archive, name):
    try:
        raw = archive.read(name)
    except KeyError:
        return None
    if b"<!DOCTYPE" in raw[:4096].upper():
        raise UploadFormatError()
    return ElementTree.fromstring(raw)


def _column(reference):
    letters = re.match(r"[A-Z]+", reference or "")
    number = 0
    for letter in letters.group(0) if letters else "":
        number = number * 26 + ord(letter) - 64
    return number - 1


def _xlsx_sheets(raw):
    """Rows of each worksheet, in workbook order, from the spreadsheet XML (no third-party reader)."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        strings = []
        shared = _xml(archive, "xl/sharedStrings.xml")
        for item in shared if shared is not None else []:
            strings.append("".join(node.text or "" for node in item.iter() if _local(node.tag) == "t"))
        workbook, rels = _xml(archive, "xl/workbook.xml"), _xml(archive, "xl/_rels/workbook.xml.rels")
        if workbook is None or rels is None:
            raise UploadFormatError()
        targets = {rel.get("Id"): rel.get("Target", "").lstrip("/") for rel in rels}
        sheets = []
        for sheet in (node for node in workbook.iter() if _local(node.tag) == "sheet"):
            target = targets.get(sheet.get(REL), "")
            target = target if target.startswith("xl/") else "xl/" + target
            data = _xml(archive, target)
            rows = []
            for row in (node for node in data.iter() if _local(node.tag) == "row") if data is not None else []:
                cells = {}
                for cell in (node for node in row if _local(node.tag) == "c"):
                    kind, value = cell.get("t"), None
                    if kind == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iter() if _local(node.tag) == "t")
                    else:
                        found = next((node.text for node in cell if _local(node.tag) == "v"), None)
                        value = strings[int(found)] if kind == "s" and found is not None and found.isdigit() and int(found) < len(strings) else found
                    cells[_column(cell.get("r"))] = value
                rows.append([cells.get(index) for index in range(max(cells, default=-1) + 1)] if cells else [])
                if len(rows) > MAX_ROWS:
                    raise LookThroughError("The file has too many rows. Upload one scheme's portfolio.")
            sheets.append((sheet.get("name") or "", rows))
        return sheets


def _csv_rows(raw):
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) > MAX_ROWS:
        raise LookThroughError("The file has too many rows. Upload one scheme's portfolio.")
    return rows


def _text(value):
    return " ".join(str(value or "").split())


def _weight(value):
    text = _text(value).replace("%", "").replace(",", "")
    if not text or text in {"-", "$"}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None
    return number if number.is_finite() and abs(number) <= 1000 else None


def _date(text):
    for pattern, order in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        parts = dict(zip(order, match.groups()))
        month = parts["m"]
        try:
            month = int(month) if month.isdigit() else datetime.strptime(month[:3].title(), "%b").month
            return date(int(parts["y"]), month, int(parts["d"]))
        except ValueError:
            continue
    return None


def _header(rows):
    for index, row in enumerate(rows[:40]):
        labels = [_text(cell).lower() for cell in row]
        isin = next((i for i, label in enumerate(labels) if "isin" in label), None)
        weight = next((i for i, label in enumerate(labels) if "% to" in label or "net asset" in label
                       or label.replace(" ", "") in {"%", "%tonav", "weight", "weight(%)", "%ofnav"}), None)
        if isin is None or weight is None:
            continue
        name = next((i for i, label in enumerate(labels) if any(word in label for word in (
            "instrument", "name of", "company", "issuer", "security", "scrip"))), None)
        sector = next((i for i, label in enumerate(labels) if "industry" in label or "sector" in label), None)
        if name is None:
            name = next((i for i in range(len(labels)) if i not in {isin, weight} and labels[i]), None)
        if name is not None:
            return index, name, isin, sector, weight
    return None


def parse_portfolio(raw: bytes, filename: str) -> dict:
    """One scheme's dated weights from its monthly portfolio file (.xlsx or .csv)."""
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if extension not in {"xlsx", "csv"}:
        raise LookThroughError("Upload the fund's monthly portfolio as .xlsx or .csv (save an .xls file as .xlsx first).")
    try:
        check_document_resources(raw, filename)  # bounds the archive's members and expanded size before reading
        sheets = _xlsx_sheets(raw) if extension == "xlsx" else [("", _csv_rows(raw))]
    except (zipfile.BadZipFile, ElementTree.ParseError, KeyError):
        raise UploadFormatError() from None
    # shortcut: the first sheet with a portfolio table is read; workbooks listing many schemes need one upload per sheet later.
    for sheet_name, rows in sheets:
        found = _header(rows)
        if found:
            break
    else:
        raise LookThroughError("No portfolio table was found. The file needs ISIN and % to net assets columns.")
    start, name_col, isin_col, sector_col, weight_col = found
    # Rows above the table, each joined: a CSV splits "August 31, 2026" at its comma.
    above = [text for row in rows[:start] if (text := _text(" ".join(_text(cell) for cell in row)))]
    scheme = next((text for text in above if re.search(r"\b(fund|scheme|etf|plan)\b", text, re.I)), sheet_name or None)
    as_of = next((found_date for text in above if (found_date := _date(text))), None)
    cell = lambda row, index: row[index] if index is not None and index < len(row) else None
    securities, opaque = defaultdict(lambda: {"weight_pct": Decimal(0)}), []
    for row in rows[start + 1:]:
        name, weight = _text(cell(row, name_col)), _weight(cell(row, weight_col))
        if not name or weight is None or re.search(r"\btotal\b", name, re.I):
            continue
        isin = _text(cell(row, isin_col)).upper()
        if ISIN.match(isin) and not isin.startswith("INF"):  # INF… ISINs are fund units (e.g. a fund of funds holding)
            entry = securities[isin]
            entry.update(isin=isin, name=entry.get("name") or name[:160],
                         sector=entry.get("sector") or (_text(cell(row, sector_col))[:80] or None), country=isin[:2])
            entry["weight_pct"] += weight
        else:
            opaque.append({"name": name[:160], "weight_pct": weight,
                           "reason": "Another fund's units; its holdings are not in this file" if isin.startswith("INF") else "No security ISIN"})
    if not securities and not opaque:
        raise LookThroughError("The portfolio table has no rows with a weight.")
    weights = [item["weight_pct"] for item in securities.values()] + [item["weight_pct"] for item in opaque]
    if max(abs(value) for value in weights) <= 1 and sum(weights) <= Decimal("1.05"):  # weights stored as fractions of one
        for item in [*securities.values(), *opaque]:
            item["weight_pct"] *= 100
    total = sum(item["weight_pct"] for item in [*securities.values(), *opaque])
    return {"scheme": scheme[:160] if scheme else None, "as_of": as_of, "securities": list(securities.values()),
            "opaque": opaque, "total_pct": total}


def _pct(value):
    return str(value.quantize(Decimal("0.01")))


def _holdings(user, ids):
    if not 1 <= len(ids) <= MAX_FILES:
        raise LookThroughError(f"Choose between one and {MAX_FILES} funds.")
    if len(set(ids)) != len(ids):
        raise LookThroughError("Choose a different fund for each file.")
    holdings = {item.pk: item for item in Investment.objects.filter(user=user, pk__in=ids)}
    if len(holdings) != len(ids):
        raise LookThroughError("Choose one of your own holdings for each file.")
    return holdings


def look_through(user, uploads: list[tuple[int, bytes, str]], *, today: date, save: bool = False) -> dict:
    """uploads: (investment id, file bytes, file name). Owner's chosen holdings only; parsed rows are kept only if save."""
    if not 1 <= len(uploads) <= MAX_FILES:
        raise LookThroughError(f"Upload between one and {MAX_FILES} fund portfolio files.")
    holdings = _holdings(user, [identity for identity, _, _ in uploads])
    parsed = [(identity, parse_portfolio(raw, filename), None) for identity, raw, filename in uploads]
    result = _combine(holdings, parsed, today)
    if save:
        with transaction.atomic():
            saved = [_save(user, holdings[identity], portfolio, raw)
                     for (identity, raw, _), (_, portfolio, _) in zip(uploads, parsed)]
        for fund, snapshot in zip(result["funds"], saved):
            fund["saved_snapshot"] = snapshot.pk if snapshot else None
            if snapshot is None:
                fund["warnings"].append(f"Not saved: you already keep {KEEP_PER_HOLDING} newer portfolios for this holding.")
        result["limits"][-1] = ("Only each file's parsed rows were saved on this computer, not the file itself; "
                                f"the latest {KEEP_PER_HOLDING} per holding are kept.")
    return result


def look_through_saved(user, ids: list[int], *, today: date) -> dict:
    """The latest saved portfolio of each chosen holding, combined exactly as freshly uploaded files are."""
    holdings = _holdings(user, ids)
    parsed = []
    for identity in ids:
        snapshot = FundPortfolioSnapshot.objects.filter(user=user, investment_id=identity).first()
        if snapshot is None:
            raise LookThroughError(f"No saved portfolio for {holdings[identity].asset_name}; upload its file first.")
        parsed.append((identity, _from_snapshot(snapshot), snapshot))
    result = _combine(holdings, parsed, today)
    result["limits"][-1] = "Uses the portfolios you saved earlier; upload a newer file each month to keep this current."
    return result


def _row(item):
    return {**item, "weight_pct": str(item["weight_pct"])}


def _save(user, holding, portfolio, raw):
    digest = hashlib.sha256(raw).hexdigest()
    snapshot, _ = FundPortfolioSnapshot.objects.update_or_create(
        user=user, investment=holding, source_sha256=digest,
        defaults={"scheme": portfolio["scheme"] or "", "as_of": portfolio["as_of"], "parser_version": PARSER_VERSION,
                  "securities": [_row(item) for item in portfolio["securities"]],
                  "opaque": [_row(item) for item in portfolio["opaque"]]})
    stale = list(FundPortfolioSnapshot.objects.filter(user=user, investment=holding).values_list("pk", flat=True)[KEEP_PER_HOLDING:])
    FundPortfolioSnapshot.objects.filter(pk__in=stale).delete()
    return None if snapshot.pk in stale else snapshot  # an older file than the kept ones is not kept


def _from_snapshot(snapshot):
    weigh = lambda items: [{**item, "weight_pct": Decimal(item["weight_pct"])} for item in items]
    securities, opaque = weigh(snapshot.securities), weigh(snapshot.opaque)
    return {"scheme": snapshot.scheme or None, "as_of": snapshot.as_of, "securities": securities, "opaque": opaque,
            "total_pct": sum((item["weight_pct"] for item in [*securities, *opaque]), Decimal(0))}


def _combine(holdings, portfolios, today):
    ids = [identity for identity, _, _ in portfolios]
    currencies = {holdings[identity].currency for identity in ids}
    if len(currencies) != 1:
        raise LookThroughError("Choose funds recorded in the same currency; amounts are never converted here.")
    funds, companies, sectors, countries = [], {}, defaultdict(Decimal), defaultdict(Decimal)
    opaque_total, total_value = Decimal(0), Decimal(0)
    for identity, parsed, snapshot in portfolios:
        holding = holdings[identity]
        value = investment_money(holding.current_value)
        total_value += value
        warnings = []
        if parsed["as_of"] is None:
            warnings.append("The file's portfolio date was not found; check that it is recent.")
        elif parsed["as_of"] > today:
            warnings.append("The file's portfolio date is in the future; check the file.")
        elif (today - parsed["as_of"]).days > STALE_DAYS:
            warnings.append(f"This portfolio is from {parsed['as_of']:%d %b %Y}; the fund house publishes a newer one monthly.")
        if not Decimal(90) <= parsed["total_pct"] <= Decimal(110):
            warnings.append(f"The file's weights add up to {_pct(parsed['total_pct'])}%, not about 100%.")
        unaccounted = Decimal(100) - parsed["total_pct"]
        fund_opaque = sum((item["weight_pct"] for item in parsed["opaque"]), Decimal(0)) + max(unaccounted, Decimal(0))
        opaque_total += value * fund_opaque / 100
        for item in parsed["securities"]:
            amount = value * item["weight_pct"] / 100
            company = companies.setdefault(item["isin"], {"isin": item["isin"], "name": item["name"], "country": item["country"],
                                                          "sector": item["sector"], "amount": Decimal(0), "funds": []})
            company["amount"] += amount
            company["funds"].append({"investment_id": identity, "weight_pct": _pct(item["weight_pct"])})
            sectors[item["sector"] or "Not stated in the file"] += amount
            countries[item["country"]] += amount
        funds.append({"investment_id": identity, "holding": holding.asset_name, "value": str(value),
                      "scheme_in_file": parsed["scheme"], "as_of": parsed["as_of"].isoformat() if parsed["as_of"] else None,
                      "securities": len(parsed["securities"]), "weights_total_pct": _pct(parsed["total_pct"]),
                      "opaque_pct": _pct(fund_opaque),
                      "opaque_rows": [{**item, "weight_pct": _pct(item["weight_pct"])} for item in parsed["opaque"][:20]],
                      "unaccounted_pct": _pct(max(unaccounted, Decimal(0))), "weights": {item["isin"]: item["weight_pct"] for item in parsed["securities"]},
                      "warnings": warnings,
                      "source": {"saved_snapshot": snapshot.pk, "saved_at": snapshot.uploaded_at.isoformat()} if snapshot else "uploaded file"})
    share = lambda amount: _pct(amount * 100 / total_value) if total_value else None
    ranked = lambda groups: [{"name": key, "amount": str(investment_money(amount)), "share_pct": share(amount)}
                             for key, amount in sorted(groups.items(), key=lambda pair: -pair[1])]
    overlaps = []
    for index, first in enumerate(funds):
        for second in funds[index + 1:]:
            common = first["weights"].keys() & second["weights"].keys()
            overlaps.append({"funds": [first["investment_id"], second["investment_id"]], "common_securities": len(common),
                             "overlap_pct": _pct(sum((min(first["weights"][key], second["weights"][key]) for key in common), Decimal(0)))})
    for fund in funds:
        del fund["weights"]
    top = sorted(companies.values(), key=lambda item: -item["amount"])
    return {
        "currency": next(iter(currencies)), "total_value": str(investment_money(total_value)), "funds": funds,
        "companies": [{**item, "amount": str(investment_money(item["amount"])), "share_pct": share(item["amount"])} for item in top[:50]],
        "companies_count": len(top), "sectors": ranked(sectors), "countries": ranked(countries),
        "opaque": {"amount": str(investment_money(opaque_total)), "share_pct": share(opaque_total)},
        "currency_exposure": "Not available: these portfolio files do not state each security's currency.",
        "overlaps": overlaps,
        "limits": ["Weights come from the files you uploaded and are only as current as their portfolio dates.",
                   "Amounts use each holding's recorded current value; no prices or exchange rates are fetched.",
                   "Country is read from each security's ISIN prefix (IN is India).",
                   "Nothing was saved; the files were read once and discarded."],
    }
