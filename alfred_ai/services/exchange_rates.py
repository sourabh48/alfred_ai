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
    region = _profile_region(user)
    if region:
        return REGIONS[region][1], "country"
    for tag in str(accept_language or "")[:200].split(","):
        parts = tag.split(";")[0].strip().replace("_", "-").split("-")
        if len(parts) > 1 and parts[-1].upper() in REGIONS:
            return REGIONS[parts[-1].upper()][1], "language"
    return RUPEE, "default"


def _profile_region(user):
    country = str(getattr(user, "country", "") or "").strip()
    return COUNTRY_NAMES.get(country.lower()) or (country.upper() if country.upper() in REGIONS else None)


def _zone_region(zone):
    """The country of an IANA time zone, from the pinned tzdata zone table; None when unknown."""
    try:
        from importlib.resources import files
        rows = files("tzdata").joinpath("zoneinfo/zone.tab").read_text(encoding="utf-8").splitlines()
    except (ImportError, OSError, ValueError):
        return None
    # Asia/Calcutta is the old name some Windows mappings still give for Asia/Kolkata.
    zone = {"Asia/Calcutta": "Asia/Kolkata"}.get(zone, zone)
    return next((cols[0] for cols in (row.split("\t") for row in rows if not row.startswith("#"))
                 if len(cols) > 2 and cols[2] == zone and cols[0] in REGIONS), None)


def home_currency(user) -> tuple[str | None, str, str]:
    """(currency, country name, why) the owner lives in: profile country, then this PC's time zone; (None, "", "unknown").

    Owner decision 2026-11-18: a record with no currency is read in this currency. A recorded currency always wins,
    so a salary paid abroad into a foreign account stays in that currency and is never added to home-currency sums.
    """
    from django.conf import settings

    region, why = _profile_region(user), "your country in Settings"
    if not region:
        region, why = _zone_region(settings.TIME_ZONE), "this PC's time zone"
    if not region:
        return None, "", "unknown"
    name, currency = REGIONS[region]
    return currency, name, why


def rate_table(on=None):
    """The stored ECB table for a day (the newest business day on or before it), else the newest; None without one.

    Reads only: the Exchange rates bot fetches. Rates change daily, so an amount from a past date uses that day's
    table, and `stale` says the table is over a week older than the day asked for.
    """
    from apps.integrations.models import VerifiedExternalInsight

    rows = VerifiedExternalInsight.objects.filter(is_active=True).exclude(status__in=["failed", "rejected"])
    record = rows.filter(scope="fx", cache_key="ecb-daily").order_by("-verified_at", "-id").first()
    table = _table(record)
    day = on or timezone.localdate()
    if on and (table is None or on < date.fromisoformat(table["date"])):
        table = _table(rows.filter(scope="fx-history", cache_key__startswith="ecb:", cache_key__lte=f"ecb:{on.isoformat()}")
                       .order_by("-cache_key").first())
    if table:
        table["stale"] = (day - date.fromisoformat(table["date"])).days > STALE_DAYS
    return table


def _table(record):
    payload = record.payload if record and isinstance(record.payload, dict) else {}
    try:
        rates = {code: Decimal(value) for code, value in payload["rates"].items()}
        rate_date = date.fromisoformat(payload["date"])
    except (KeyError, TypeError, ValueError, ArithmeticError, AttributeError):
        return None
    return {"rates": rates, "date": rate_date.isoformat(), "source": record.source_name}


def convert(amount, code, target: str, table) -> Decimal | None:
    """Approximate amount in target, or None without a rate. Not recorded counts as INR (FIN-15)."""
    code = code or RUPEE
    if code == target:
        return Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP)
    if not table or code not in table["rates"] or target not in table["rates"]:
        return None
    return (Decimal(str(amount)) * table["rates"][target] / table["rates"][code]).quantize(CENT, ROUND_HALF_UP)


def approximate(request, groups, fields, totals=None, *, currency_key="currency", date_key=None):
    """Add an `approximate` block in the viewer's currency to each group and sum `totals` across currencies.

    groups: dicts holding `currency_key` and the money `fields`. totals: name -> [(amount, code)].
    A total is None unless every part could be converted. Rates are read only when something differs.
    date_key: a group's ISO date (a transaction's), converted at that day's rate; otherwise today's rate (balances).
    """
    target, basis = display_currency(request.user, request.META.get("HTTP_ACCEPT_LANGUAGE", ""))
    totals = totals or {}
    codes = {group.get(currency_key) or RUPEE for group in groups} | {code or RUPEE for parts in totals.values() for _, code in parts}
    table = rate_table() if codes - {target} else None
    dated = {}
    out = []
    for group in groups:
        same = (group.get(currency_key) or RUPEE) == target
        day = str(group.get(date_key) or "")[:10] if date_key and not same else ""
        if day and day not in dated:
            try:
                dated[day] = rate_table(on=date.fromisoformat(day))
            except ValueError:
                dated[day] = None
        used = dated[day] if day else table
        values = {field: convert(group.get(field) or 0, group.get(currency_key), target, used) for field in fields}
        out.append({**group, "approximate": None if same or None in values.values()
                    else {"currency": target, **{field: format(value, "f") for field, value in values.items()},
                          **({"rate_date": used["date"]} if day else {})}})
    combined = {}
    for name, parts in totals.items():
        converted = [convert(amount or 0, code, target, table) for amount, code in parts]
        exact = all((code or RUPEE) == target for _, code in parts)
        combined[name] = None if exact or not parts or None in converted else format(sum(converted), "f")
    display = {"currency": target, "basis": basis, "approximate": True, "totals": combined,
               "rate_date": table["date"] if table else None, "source": table["source"] if table else None,
               "stale": table["stale"] if table else False, "rates_available": table is not None}
    return out, display
