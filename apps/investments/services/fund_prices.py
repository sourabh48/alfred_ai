"""Mutual fund values kept current from AMFI's official daily NAV file (INV-05; owner 2026-11-14: automatic, and tell the person).

One download covers every fund. Only holdings with an AMFI scheme code, units and rupee amounts are revalued; the value
before each update is kept so Home can say what changed. Nothing is bought or sold.
"""
from django.db import transaction

from ..models import Investment
from ..money import investment_money
from .portfolio_intelligence import portfolio_intelligence_service


def _latest():
    return {item["scheme_code"]: item for item in portfolio_intelligence_service._get_amfi_latest_nav_report()["items"]}


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
    """Revalue fund holdings from the latest AMFI NAV; a holding edited meanwhile is left for the next run."""
    holdings = list(Investment.objects.exclude(amfi_scheme_code="").filter(units__gt=0, currency="INR"))
    if not holdings:
        return {"checked": 0, "updated": 0}
    latest, updated = _latest(), 0
    for holding in holdings:
        item = latest.get(holding.amfi_scheme_code)
        if not item or (holding.nav_date and item["nav_date"] <= holding.nav_date):
            continue
        with transaction.atomic():
            row = Investment.objects.select_for_update().get(pk=holding.pk)
            if (row.units, row.amfi_scheme_code, row.currency) != (holding.units, holding.amfi_scheme_code, "INR"):
                continue
            row.value_before_nav, row.current_value = row.current_value, investment_money(row.units * item["nav"])
            row.nav, row.nav_date = item["nav"], item["nav_date"]
            row.save(update_fields=["value_before_nav", "current_value", "nav", "nav_date", "updated_at"])
        updated += 1
    return {"checked": len(holdings), "updated": updated}
