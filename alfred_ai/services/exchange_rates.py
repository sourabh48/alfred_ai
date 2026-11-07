"""Display-only conversion with stored ECB reference rates (owner decision 2026-11-07).

Records keep the currency they were entered in. A converted figure is never stored or fed into
calculations; it is always marked approximate with its rate date and source.
"""
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from alfred_ai.services.currency import RUPEE

STALE_DAYS = 7
CENT = Decimal("0.01")
EURO_AREA = "AT BE HR CY EE FI FR DE GR IE IT LV LT LU MT NL PT SK SI ES".split()
# Region code -> (country name, currency) for the ECB reference set. Euro countries share EUR.
REGIONS = {
    "IN": ("India", "INR"), "US": ("United States", "USD"), "GB": ("United Kingdom", "GBP"),
    "AU": ("Australia", "AUD"), "BG": ("Bulgaria", "BGN"), "BR": ("Brazil", "BRL"), "CA": ("Canada", "CAD"),
    "CH": ("Switzerland", "CHF"), "CN": ("China", "CNY"), "CZ": ("Czechia", "CZK"), "DK": ("Denmark", "DKK"),
    "HK": ("Hong Kong", "HKD"), "HU": ("Hungary", "HUF"), "ID": ("Indonesia", "IDR"), "IL": ("Israel", "ILS"),
    "IS": ("Iceland", "ISK"), "JP": ("Japan", "JPY"), "KR": ("South Korea", "KRW"), "MX": ("Mexico", "MXN"),
    "MY": ("Malaysia", "MYR"), "NO": ("Norway", "NOK"), "NZ": ("New Zealand", "NZD"), "PH": ("Philippines", "PHP"),
    "PL": ("Poland", "PLN"), "RO": ("Romania", "RON"), "SE": ("Sweden", "SEK"), "SG": ("Singapore", "SGD"),
    "TH": ("Thailand", "THB"), "TR": ("Turkey", "TRY"), "ZA": ("South Africa", "ZAR"),
    **{code: (name, "EUR") for code, name in zip(EURO_AREA, (
        "Austria Belgium Croatia Cyprus Estonia Finland France Germany Greece Ireland Italy Latvia "
        "Lithuania Luxembourg Malta Netherlands Portugal Slovakia Slovenia Spain").split())},
}
COUNTRY_NAMES = {name.lower(): code for code, (name, _) in REGIONS.items()} | {
    "usa": "US", "united states of america": "US", "uk": "GB", "england": "GB", "bharat": "IN"}
DISPLAY_CURRENCIES = sorted({currency for _, currency in REGIONS.values()} | {"EUR"})


def display_currency(user, accept_language: str = "") -> tuple[str, str]:
    """The viewer's display currency and why: their choice, then profile country, then browser locale."""
    chosen = getattr(user, "display_currency", None)
    if chosen in DISPLAY_CURRENCIES:
        return chosen, "chosen"
    country = str(getattr(user, "country", "") or "").strip()
    region = COUNTRY_NAMES.get(country.lower()) or (country.upper() if country.upper() in REGIONS else None)
    if region:
        return REGIONS[region][1], "country"
    for tag in str(accept_language or "")[:200].split(","):
        parts = tag.split(";")[0].strip().replace("_", "-").split("-")
        if len(parts) > 1 and parts[-1].upper() in REGIONS:
            return REGIONS[parts[-1].upper()][1], "language"
    return RUPEE, "default"


def rate_table():
    """The newest stored ECB table, or None. Reads only: the background task fetches (native_exchange_rate_refresh)."""
    from apps.integrations.models import VerifiedExternalInsight

    record = (VerifiedExternalInsight.objects.filter(scope="fx", cache_key="ecb-daily", is_active=True)
              .exclude(status__in=["failed", "rejected"]).order_by("-verified_at", "-id").first())
    payload = record.payload if record and isinstance(record.payload, dict) else {}
    try:
        rates = {code: Decimal(value) for code, value in payload["rates"].items()}
        rate_date = date.fromisoformat(payload["date"])
    except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
        return None
    return {"rates": rates, "date": rate_date.isoformat(), "source": record.source_name,
            "stale": (timezone.localdate() - rate_date).days > STALE_DAYS}


def convert(amount, code, target: str, table) -> Decimal | None:
    """Approximate amount in target, or None without a rate. Not recorded counts as INR (FIN-15)."""
    code = code or RUPEE
    if code == target:
        return Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP)
    if not table or code not in table["rates"] or target not in table["rates"]:
        return None
    return (Decimal(str(amount)) * table["rates"][target] / table["rates"][code]).quantize(CENT, ROUND_HALF_UP)


def approximate(request, groups, fields, totals=None, *, currency_key="currency"):
    """Add an `approximate` block in the viewer's currency to each group and sum `totals` across currencies.

    groups: dicts holding `currency_key` and the money `fields`. totals: name -> [(amount, code)].
    A total is None unless every part could be converted. Rates are read only when something differs.
    """
    target, basis = display_currency(request.user, request.META.get("HTTP_ACCEPT_LANGUAGE", ""))
    totals = totals or {}
    codes = {group.get(currency_key) or RUPEE for group in groups} | {code or RUPEE for parts in totals.values() for _, code in parts}
    table = rate_table() if codes - {target} else None
    out = []
    for group in groups:
        values = {field: convert(group.get(field) or 0, group.get(currency_key), target, table) for field in fields}
        same = (group.get(currency_key) or RUPEE) == target
        out.append({**group, "approximate": None if same or None in values.values()
                    else {"currency": target, **{field: format(value, "f") for field, value in values.items()}}})
    combined = {}
    for name, parts in totals.items():
        converted = [convert(amount or 0, code, target, table) for amount, code in parts]
        exact = all((code or RUPEE) == target for _, code in parts)
        combined[name] = None if exact or not parts or None in converted else format(sum(converted), "f")
    display = {"currency": target, "basis": basis, "approximate": True, "totals": combined,
               "rate_date": table["date"] if table else None, "source": table["source"] if table else None,
               "stale": table["stale"] if table else False, "rates_available": table is not None}
    return out, display
