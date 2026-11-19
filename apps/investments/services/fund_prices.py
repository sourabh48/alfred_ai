"""Mutual fund values kept current from AMFI's official daily NAV file (INV-05; owner 2026-11-14: automatic, and tell the person).

One download covers every fund. Only holdings with an AMFI scheme code, units and rupee amounts are revalued; the value
before each update is kept so Home can say what changed. Nothing is bought or sold.

A price is used only under the watchlist's own evidence rules: one agreed row per scheme, a real positive NAV, dated
within WATCHLIST_NAV_MAX_AGE_DAYS and never in the future. Otherwise the holding keeps the value it had.
"""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ..models import Investment
from ..money import investment_money
from .portfolio_intelligence import WATCHLIST_NAV_MAX_AGE_DAYS, portfolio_intelligence_service


def _latest():
    """One row per scheme. A scheme the file lists twice with different details is left out, as the watchlist does."""
    latest, conflicting = {}, set()
    for item in portfolio_intelligence_service._get_amfi_latest_nav_report()["items"]:
        code = item["scheme_code"]
        if code in latest and latest[code] != item:
            conflicting.add(code)
        latest[code] = item
    for code in conflicting:
        del latest[code]
    return latest


def nav_is_fresh(nav_date, today=None):
    """The accepted NAV age: a real date, not in the future, within the watchlist's limit."""
    return type(nav_date) is date and 0 <= ((today or timezone.localdate()) - nav_date).days <= WATCHLIST_NAV_MAX_AGE_DAYS


def nav_state(holding):
    """'' for a holding ALFRED does not price; otherwise waiting (no price yet), current or stale. Crypto prices
    (crypto_prices.py) count as current for a day, fund NAVs for the watchlist's limit."""
    if holding.amfi_scheme_code and holding.units and holding.currency == "INR":
        fresh = nav_is_fresh(holding.nav_date)
    elif holding.coingecko_id and holding.units and holding.currency:
        from .crypto_prices import price_is_fresh
        fresh = price_is_fresh(holding.nav_date)
    else:
        return ""
    return "waiting" if holding.nav_date is None else "current" if fresh else "stale"


def _usable(item):
    nav = item.get("nav") if item else None
    return isinstance(nav, Decimal) and nav.is_finite() and nav > 0 and nav_is_fresh(item.get("nav_date"))


def search_funds(text, limit=10):
    """Funds whose AMFI name holds every word typed, for picking a scheme code by name."""
    words = str(text or "").casefold().split()[:6]
    if not words or len(" ".join(words)) < 3:
        return []
    found = []
    for item in _latest().values():
        name = item["scheme_name"].casefold()
        if all(word in name for word in words):
            found.append({"scheme_code": item["scheme_code"], "name": item["scheme_name"], "fund_house": item["fund_house"],
                          "nav": str(item["nav"]), "nav_date": item["nav_date"].isoformat()})
            if len(found) >= limit:
                break
    return found


def refresh_fund_values():
    """Revalue fund holdings from a fresh AMFI NAV.

    Each holding is judged from its own locked row, not from an earlier read, so an edit, a deletion or a newer price
    recorded while the file downloaded is never overwritten. A stale, missing, conflicting or invalid price leaves the
    holding exactly as it was and is counted in without_fresh_price.
    """
    tracked = Investment.objects.exclude(amfi_scheme_code="").filter(units__gt=0, currency="INR")
    ids = list(tracked.values_list("pk", flat=True))
    if not ids:
        return {"checked": 0, "updated": 0, "without_fresh_price": 0}
    latest, updated, unpriced = _latest(), 0, 0
    for pk in ids:
        with transaction.atomic():
            row = tracked.select_for_update().filter(pk=pk).first()
            if row is None:  # deleted, or edited so it is no longer a priced fund
                continue
            item = latest.get(row.amfi_scheme_code)
            if not _usable(item):
                unpriced += 1
                continue
            if row.nav_date and item["nav_date"] < row.nav_date:  # older evidence never replaces newer
                continue
            try:
                value = investment_money(row.units * item["nav"])
            except ValueError:  # outside the stored money range: leave this holding, carry on with the rest
                unpriced += 1
                continue
            newer = row.nav_date is None or item["nav_date"] > row.nav_date
            if not newer and (row.nav, row.current_value) == (item["nav"], value):
                continue  # already consistent with this price and these units
            if newer:  # a correction on the same price date is not a price move, so Home's comparison is kept
                row.value_before_nav = row.current_value
            row.current_value, row.nav, row.nav_date = value, item["nav"], item["nav_date"]
            row.save(update_fields=["value_before_nav", "current_value", "nav", "nav_date", "updated_at"])
            updated += 1
    return {"checked": len(ids), "updated": updated, "without_fresh_price": unpriced}
