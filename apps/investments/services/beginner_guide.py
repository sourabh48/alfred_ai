"""Plain-language fund guide for a first-time investor (owner 2026-11-14: tell me what to buy, track it, tell me when to sell).

Picks are the top of the AMFI watchlist, already ranked and spread across fund houses. Owned funds with an AMFI code get
Hold / Review / Sell from the same official NAV history. Everything is computed on this PC from public AMFI prices; no
holding leaves it, and nothing is ever bought or sold for the person.
"""
from decimal import Decimal

from django.utils import timezone

from ..models import Investment
from .fund_prices import nav_is_fresh
from .portfolio_intelligence import WATCHLIST_HISTORY_DAYS, WATCHLIST_MIN_OBSERVATIONS, portfolio_intelligence_service

PICKS = 3
SELL_DROP_PCT = Decimal("15")    # this far below its recent high: think about selling or switching
REVIEW_DROP_PCT = Decimal("8")   # this far below: keep an eye on it
NOTE = ("A guide built from official AMFI prices, not financial advice. Past prices do not promise future returns. "
        "ALFRED never buys or sells for you.")


def _risk_word(volatility):
    return "Low" if volatility < 3 else "Medium" if volatility < 6 else "High"


def _pick(item):
    return {"scheme_code": item["scheme_code"], "name": item["scheme_name"], "fund_house": item["fund_house"],
            "kind": item["family_label"], "nav": item["nav_source_value"], "nav_date": item["nav_date"],
            "risk": _risk_word(item["realized_volatility_pct"]),
            "why": (f"Up {item['return_30d_pct']:.1f}% in the last month. Its worst fall in the last "
                    f"{item['history_days']} days was {abs(item['max_drawdown_pct']):.1f}%."),
            "how": "Start small with a monthly SIP, buy the Direct Growth plan, and plan to stay invested for years."}


def holding_signal(navs):
    """Hold / Review / Sell from a fund's NAVs in date order; the drop is measured from its highest NAV in the window."""
    if len(navs) < 2:
        return None
    drop = (1 - navs[-1] / max(navs)) * 100
    if drop >= SELL_DROP_PCT:
        return "sell", f"It is {drop:.1f}% below its recent high. Think about selling or switching to a steadier fund."
    if drop >= REVIEW_DROP_PCT:
        return "review", f"It is {drop:.1f}% below its recent high. Nothing to do yet; ALFRED keeps checking it every day."
    return "hold", "It is close to its recent high. Keep holding and keep your SIP going."


def dated_navs(rows, today):
    """A fund's NAVs in date order with their latest date, or the reason its history cannot support a signal.

    The watchlist's evidence rules: one agreed identity, one price per day, nothing dated in the future, a latest price
    within the accepted age, and enough observations inside the history window.
    """
    by_day, identities = {}, set()
    for row in rows:
        day = row["nav_date"]
        if day > today:
            return None, None, "AMFI sent a price dated in the future"
        if (today - day).days > WATCHLIST_HISTORY_DAYS:
            continue
        if by_day.setdefault(day, row["nav"]) != row["nav"]:
            return None, None, f"AMFI lists two different prices for {day:%d %b %Y}"
        identities.add(tuple(str(row.get(field, "")).casefold() for field in ("scheme_name", "isin_growth", "isin_reinvestment")))
    if len(identities) > 1:
        return None, None, "its AMFI records do not agree on which fund this is"
    if not by_day:
        return None, None, "AMFI has no recent prices for it"
    days = sorted(by_day)
    if not nav_is_fresh(days[-1], today):
        return None, days[-1], f"its latest AMFI price is from {days[-1]:%d %b %Y}, which is too old"
    if len(days) < WATCHLIST_MIN_OBSERVATIONS:
        return None, days[-1], f"AMFI has only {len(days)} recent prices for it"
    return [by_day[day] for day in days], days[-1], ""


def beginner_guide(user, watchlist):
    picks = [_pick(item) for item in (watchlist.get("items") or [])[:PICKS]] if watchlist.get("available") else []
    owned = list(Investment.objects.filter(user=user, currency="INR").exclude(amfi_scheme_code="").only("id", "asset_name", "amfi_scheme_code"))
    holdings = []
    if owned:
        # The watchlist has just loaded this window, so this normally reads the cache rather than downloading again.
        report = portfolio_intelligence_service._get_amfi_history_report(days=WATCHLIST_HISTORY_DAYS)
        history = report["series"]
        missing = "" if history else str(report.get("evidence", {}).get("summary", "")).rstrip(".")
        codes = {item.amfi_scheme_code for item in owned}
        series, today = {}, timezone.localdate()
        for row in history:
            if row["scheme_code"] in codes:
                series.setdefault(row["scheme_code"], []).append(row)
        for item in owned:
            navs, as_of, reason = dated_navs(series.get(item.amfi_scheme_code, []), today)
            reason = missing or reason  # no history at all: say why (downloading, or AMFI failed), not "no recent prices"
            signal = holding_signal(navs) if navs else None
            if signal:
                action, text = signal[0], f"{signal[1]} Based on AMFI prices up to {as_of:%d %b %Y}."
            else:  # no hold, review or sell without dated, complete evidence
                action, text = "unknown", f"ALFRED cannot judge this fund now: {reason or 'its prices are incomplete'}. No signal is given."
            holdings.append({"id": item.id, "name": item.asset_name, "action": action, "text": text,
                             "as_of": as_of.isoformat() if as_of else None})
    return {"picks": picks, "holdings": holdings, "note": NOTE,
            "picks_reason": "" if watchlist.get("available") else watchlist.get("summary") or ""}
