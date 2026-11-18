"""Extra research sources the owner turned on (2026-11-18): FRED, Alpha Vantage and SEC EDGAR.

Each adds dated context lines to a research card and never changes a rating, so the past-calls check still replays
exactly the rules the desk uses. Each is skipped quietly when its key (Settings > Online services) or the owner's
email is missing, or when the service is unavailable. Only public symbols, the keys and, for SEC EDGAR, the account's
own email (the SEC asks every automated client for a contact address; owner decision 2026-11-18) leave this PC.
"""
from __future__ import annotations

import os
import re
from datetime import date, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from django.utils import timezone

from alfred_ai.services import public_http

FETCH_ERRORS = (public_http.PublicHTTPError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError, OSError)
FRED_URL = "https://api.stlouisfed.org/fred/series/observations"
ALPHA_URL = "https://www.alphavantage.co/query"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
POLYMARKET_URL = "https://gamma-api.polymarket.com/public-search"  # public, no key (owner approved 2026-11-18)
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


def alpha_vantage_prices(symbol: str, *, years: int = 1) -> dict:
    """Daily closes, highs and lows from Alpha Vantage, shaped like the Yahoo chart. Indian shares are read on BSE
    (Alpha Vantage lists RELIANCE.BSE, not NSE), so their closes can differ slightly from NSE's. Raises when unavailable."""
    from datetime import datetime as dt

    api_key = _key("ALFRED_ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise ValueError("No Alpha Vantage key is saved.")
    if symbol.endswith((".NS", ".BO")):
        query, currency = symbol.rsplit(".", 1)[0] + ".BSE", "INR"
    elif us_listed(symbol):
        query, currency = symbol, "USD"
    else:
        raise ValueError("Alpha Vantage is used here only for Indian and US shares.")
    payload = public_http.request("GET", ALPHA_URL, params={"function": "TIME_SERIES_DAILY", "symbol": query, "apikey": api_key,
                                                             "outputsize": "full" if years > 1 else "compact"}, max_bytes=12_000_000).json()
    series = payload.get("Time Series (Daily)") if isinstance(payload, dict) else None
    if not isinstance(series, dict) or not series:
        raise ValueError("Alpha Vantage gave no daily prices (daily limit, unknown symbol or bad key).")
    since = timezone.localdate() - timedelta(days=366 * years)
    rows = []
    for day, bar in sorted(series.items()):
        when = date.fromisoformat(day)
        close, high, low = (_number(bar.get(k)) for k in ("4. close", "2. high", "3. low"))
        if when >= since and close is not None and close > 0:
            rows.append((int(dt(when.year, when.month, when.day, tzinfo=dt_timezone.utc).timestamp()), close,
                         high if high and high > 0 else None, low if low and low > 0 else None))
    if not rows:
        raise ValueError("Alpha Vantage gave no recent daily prices.")
    return {"timestamp": [r[0] for r in rows], "close": [r[1] for r in rows], "high": [r[2] for r in rows],
            "low": [r[3] for r in rows], "currency": currency, "source": "Alpha Vantage"}


def _json_list(raw) -> list:
    """Polymarket sends outcomes and prices as JSON text inside the JSON."""
    import json
    try:
        found = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return []
    return found if isinstance(found, list) else []


def prediction_markets(name: str, limit: int = 3) -> list:
    """Open Polymarket markets that mention the company, by traded volume: what bettors price, read-only context.
    Like TradingAgents' Polymarket vendor (pin 9fa1196f), only open markets resolving in the future are kept."""
    if not name or len(name) < 3:
        return []

    def fetch():
        payload = public_http.request("GET", POLYMARKET_URL, params={"q": name, "limit_per_type": 20}, max_bytes=2_000_000).json()
        now, found = timezone.now(), []
        for event in payload.get("events") or []:
            for market in event.get("markets") or []:
                outcomes, prices = _json_list(market.get("outcomes")), _json_list(market.get("outcomePrices"))
                end = str(market.get("endDate") or "")[:10]
                if market.get("closed") or not outcomes or len(outcomes) != len(prices) or not end or end < now.date().isoformat():
                    continue
                best = max(range(len(prices)), key=lambda i: _number(prices[i]) or Decimal(0))
                chance = _number(prices[best])
                question = str(market.get("question") or "").strip()[:200]
                if chance is None or not question or name.lower().split()[0] not in question.lower():
                    continue  # a search hit that does not name the company is not about it
                volume = _number(market.get("volumeNum")) or Decimal(0)
                found.append((volume, {"text": f'Polymarket bettors price "{question}" at {(chance * 100).quantize(Decimal("1"))}% '
                                               f'for {str(outcomes[best])[:40]} (US${volume.quantize(Decimal("1")):,} traded, '
                                               f'resolves {end}). Betting odds, not a forecast.',
                                       "url": f"https://polymarket.com/event/{event.get('slug')}" if event.get("slug") else None}))
        return [item for _volume, item in sorted(found, key=lambda pair: -pair[0])[:limit]]

    try:
        return _cached(f"research-sources:polymarket:{re.sub(r'\W+', '-', name.lower())}", fetch, 6 * 3600)
    except (public_http.PublicHTTPError, ValueError, AttributeError, TypeError):
        return []
