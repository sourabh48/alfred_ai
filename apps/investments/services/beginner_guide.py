"""Plain-language fund guide for a first-time investor (owner 2026-11-14: tell me what to buy, track it, tell me when to sell).

Picks are the top of the AMFI watchlist, already ranked and spread across fund houses. Owned funds with an AMFI code get
Hold / Review / Sell from the same official NAV history. Everything is computed on this PC from public AMFI prices; no
holding leaves it, and nothing is ever bought or sold for the person.
"""
from decimal import Decimal

from ..models import Investment
from .portfolio_intelligence import WATCHLIST_HISTORY_DAYS, portfolio_intelligence_service

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


def beginner_guide(user, watchlist):
    picks = [_pick(item) for item in (watchlist.get("items") or [])[:PICKS]] if watchlist.get("available") else []
    owned = list(Investment.objects.filter(user=user, currency="INR").exclude(amfi_scheme_code="").only("id", "asset_name", "amfi_scheme_code"))
    holdings = []
    if owned:
        # The watchlist has just loaded this window, so this normally reads the cache rather than downloading again.
        history = portfolio_intelligence_service._get_amfi_history_report(days=WATCHLIST_HISTORY_DAYS)["series"]
        codes = {item.amfi_scheme_code for item in owned}
        series = {}
        for row in history:
            if row["scheme_code"] in codes:
                series.setdefault(row["scheme_code"], {})[row["nav_date"]] = row["nav"]
        for item in owned:
            navs = [nav for _, nav in sorted(series.get(item.amfi_scheme_code, {}).items())]
            signal = holding_signal(navs)
            action, text = signal or ("unknown", "No recent AMFI prices for this fund yet, so ALFRED cannot judge it.")
            holdings.append({"id": item.id, "name": item.asset_name, "action": action, "text": text})
    return {"picks": picks, "holdings": holdings, "note": NOTE}
