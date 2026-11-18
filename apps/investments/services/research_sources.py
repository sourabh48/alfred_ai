"""Extra research sources the owner turned on (2026-11-18): FRED, Alpha Vantage and SEC EDGAR.

Each adds dated context lines to a research card and never changes a rating, so the past-calls check still replays
exactly the rules the desk uses. Each is skipped quietly when its key (Settings > Online services) or the owner's
email is missing, or when the service is unavailable. Only public symbols, the keys and, for SEC EDGAR, the account's
own email (the SEC asks every automated client for a contact address; owner decision 2026-11-18) leave this PC.
"""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from django.utils import timezone

from alfred_ai.services import public_http

FETCH_ERRORS = (public_http.PublicHTTPError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError, OSError)
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
ALPHA_URL = "https://www.alphavantage.co/query"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@([A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}$")
STALE_DAYS = 120
# series: (label, months back to compare for a yearly change, or 0 to show the level)
FRED_SERIES = {"india": [("INDIRLTLT01STM", "India's 10-year government bond yield", 0)],
               "us": [("FEDFUNDS", "The US Federal Reserve's policy rate", 0), ("CPIAUCSL", "US consumer prices", 12),
                      ("UNRATE", "US unemployment", 0), ("DGS10", "The US 10-year Treasury yield", 0)]}
FILING_FORMS = ("10-K", "10-Q", "8-K", "20-F", "6-K", "40-F")


def us_listed(symbol: str) -> bool:
    """Yahoo writes US shares without an exchange suffix (BRK-B, AAPL); other markets end in .NS, .L and so on."""
    return "." not in symbol and not symbol.startswith(("^", "%5E"))


def _key(name: str) -> str:
    return os.environ.get(name, "").strip()


def _cached(key: str, fetch, seconds: int):
    found = cache.get(key)
    if found is None:
        try:
            found, keep = fetch(), seconds
        except FETCH_ERRORS:
            found, keep = [], 3600  # try again in an hour, not on every card
        cache.set(key, found, keep)
    return found


def _number(raw):
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return value if value.is_finite() else None


# ---- FRED (St. Louis Fed) ---------------------------------------------------------------------------------------

def _fred_series(series_id: str, label: str, back: int, api_key: str, today: date) -> str | None:
    response = public_http.request("GET", FRED_URL, params={"series_id": series_id, "api_key": api_key, "file_type": "json",
                                                             "sort_order": "desc", "limit": back + 1})
    rows = [(date.fromisoformat(row["date"]), _number(row["value"])) for row in response.json()["observations"]]
    rows = [(day, value) for day, value in rows if value is not None]
    if not rows or (today - rows[0][0]).days > STALE_DAYS:
        return None
    day, value = rows[0]
    when = day.strftime("%b %Y") if back or series_id != "DGS10" else day.isoformat()
    if not back:
        return f"{label} was {value.quantize(Decimal('0.01'))}% in {when} (FRED)."
    earlier = [v for d, v in rows if (d.year, d.month) == (day.year - 1, day.month)]
    if not earlier or not earlier[0]:
        return None
    change = ((value / earlier[0] - 1) * 100).quantize(Decimal("0.1"))
    return f"{label} were {change}% higher than a year earlier in {when} (FRED)."


def fred_lines(region: str, today: date | None = None) -> list:
    """Interest-rate and inflation context for India or the US. Needs ALFRED_FRED_API_KEY."""
    api_key = _key("ALFRED_FRED_API_KEY")
    if not api_key or region not in FRED_SERIES:
        return []
    today = today or timezone.localdate()

    def fetch():
        lines = []
        for series_id, label, back in FRED_SERIES[region]:
            try:
                line = _fred_series(series_id, label, back, api_key, today)
            except FETCH_ERRORS:
                line = None
            if line:
                lines.append(line)
        return lines

    return _cached(f"research-sources:fred:{region}:{today.isoformat()}", fetch, 12 * 3600)


# ---- Alpha Vantage ----------------------------------------------------------------------------------------------

def _alpha(function: str, symbol: str, api_key: str, max_bytes=4_000_000) -> dict:
    payload = public_http.request("GET", ALPHA_URL, params={"function": function, "symbol": symbol, "apikey": api_key},
                                  max_bytes=max_bytes).json()
    if not isinstance(payload, dict) or {"Information", "Note", "Error Message"} & set(payload):
        raise ValueError("Alpha Vantage gave no data (daily limit, unknown symbol or bad key).")
    return payload


def _earnings_line(payload: dict) -> dict | None:
    latest = (payload.get("quarterlyEarnings") or [None])[0]
    if not isinstance(latest, dict):
        return None
    reported, expected = _number(latest.get("reportedEPS")), _number(latest.get("estimatedEPS"))
    if reported is None:
        return None
    text = f"Last quarter (ended {latest.get('fiscalDateEnding')}, reported {latest.get('reportedDate')}): earnings per share {reported}"
    if expected is not None and expected != 0:
        gap = ((reported - expected) / abs(expected) * 100).quantize(Decimal("0.1"))
        text += f" against an expected {expected} ({abs(gap)}% {'above' if gap >= 0 else 'below'})"
    return {"text": text + " (Alpha Vantage).", "url": None}


def _insider_line(payload: dict, today: date) -> dict | None:
    since, bought, sold = today - timedelta(days=90), 0, 0
    for row in payload.get("data") or []:
        try:
            day, price = date.fromisoformat(str(row["transaction_date"])[:10]), _number(row.get("share_price"))
        except (KeyError, ValueError, TypeError):
            continue
        if day < since or not price or price <= 0:  # grants and option awards carry no market price
            continue
        if row.get("acquisition_or_disposal") == "A":
            bought += 1
        elif row.get("acquisition_or_disposal") == "D":
            sold += 1
    if not bought and not sold:
        return None
    return {"text": f"Company insiders in the last 90 days: {bought} purchase(s) and {sold} sale(s) at a market price "
                    "(Alpha Vantage; grants left out; a sale is often for tax or diversification).", "url": None}


def alpha_vantage_lines(symbol: str, today: date | None = None) -> list:
    """The latest earnings surprise and insider trading for a US share. Needs ALFRED_ALPHA_VANTAGE_API_KEY.
    The free key allows 25 requests a day, so each share is read at most once a week."""
    api_key = _key("ALFRED_ALPHA_VANTAGE_API_KEY")
    if not api_key or not us_listed(symbol):
        return []
    today = today or timezone.localdate()

    def fetch():
        lines = [_earnings_line(_alpha("EARNINGS", symbol, api_key))]
        try:
            lines.append(_insider_line(_alpha("INSIDER_TRANSACTIONS", symbol, api_key, max_bytes=12_000_000), today))
        except FETCH_ERRORS:
            pass  # earnings alone are still worth showing
        return [line for line in lines if line]

    return _cached(f"research-sources:alpha:{symbol}", fetch, 7 * 86400)


# ---- SEC EDGAR --------------------------------------------------------------------------------------------------

def _sec_headers(email: str) -> dict:
    return {"User-Agent": f"ALFRED research desk {email}", "Accept-Encoding": "identity"}


def _sec_ciks(email: str) -> dict:
    found = cache.get("research-sources:sec-tickers")
    if found is None:
        rows = public_http.request("GET", SEC_TICKERS_URL, headers=_sec_headers(email), max_bytes=4_000_000).json()
        found = {str(row["ticker"]).upper(): int(row["cik_str"]) for row in rows.values()}
        cache.set("research-sources:sec-tickers", found, 7 * 86400)
    return found


def sec_filings(symbol: str, email: str) -> list:
    """The latest three annual, quarterly or current reports a US company filed, linked to the SEC's copy.
    Sends the account's email as the contact address the SEC requires; nothing else about the owner."""
    email = str(email or "").strip()
    if not us_listed(symbol) or not EMAIL.fullmatch(email):
        return []

    def fetch():
        cik = _sec_ciks(email).get(symbol.upper())
        if not cik:
            return []
        recent = public_http.request("GET", SEC_SUBMISSIONS_URL.format(cik=cik), headers=_sec_headers(email),
                                     max_bytes=12_000_000).json()["filings"]["recent"]
        lines = []
        for form, filed, period, accession, document in zip(recent["form"], recent["filingDate"], recent["reportDate"],
                                                             recent["accessionNumber"], recent["primaryDocument"]):
            if form in FILING_FORMS and re.fullmatch(r"[0-9-]{10,25}", accession) and re.fullmatch(r"[\w.-]{1,120}", document or ""):
                url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{document}"
                lines.append({"text": f"{form} filed {filed}" + (f" for the period to {period}" if period else "") + " (SEC EDGAR).",
                              "url": url})
            if len(lines) == 3:
                break
        return lines

    return _cached(f"research-sources:sec:{symbol}", fetch, 86400)
