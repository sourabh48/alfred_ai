"""Crypto holdings kept current from CoinGecko's public prices (owner approved 2026-11-19).

Only coin ids (such as 'bitcoin') and currency codes leave this PC, never units, amounts or names of people. A holding is
revalued only when a coin was picked by name and its units and currency are recorded. Nothing is bought or sold.
"""
import hashlib
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from alfred_ai.services import public_http

from ..models import Investment
from ..money import investment_money

URL = "https://api.coingecko.com/api/v3"
COIN = re.compile(r"^[a-z0-9][a-z0-9-]{0,99}$")
MAX_AGE = timedelta(days=1)
STEP = Decimal("0.0001")  # the stored price keeps four decimals
ERRORS = (public_http.PublicHTTPError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation, OSError)


def price_is_fresh(price_date, today=None):
    return price_date is not None and 0 <= ((today or timezone.localdate()) - price_date).days <= MAX_AGE.days


def search_coins(text, limit=10):
    """Coins whose name or symbol matches, for picking the CoinGecko id by name. Results are kept a day."""
    text = " ".join(str(text or "").split())[:60]
    if len(text) < 2:
        return []
    key = "coingecko:search:" + hashlib.sha256(text.casefold().encode()).hexdigest()
    found = cache.get(key)
    if found is None:
        try:
            coins = public_http.request("GET", f"{URL}/search", params={"query": text}, max_bytes=1_000_000).json().get("coins") or []
        except ERRORS:
            return []
        found = [{"id": coin["id"], "name": str(coin.get("name") or "")[:80], "symbol": str(coin.get("symbol") or "").upper()[:20]}
                 for coin in coins if COIN.fullmatch(str(coin.get("id") or ""))][:limit]
        cache.set(key, found, 86400)
    return found


def _prices(ids, currencies):
    """{(coin, CUR): (price, date)} for prices CoinGecko updated within MAX_AGE; anything else is left out."""
    raw = public_http.request("GET", f"{URL}/simple/price", params={
        "ids": ",".join(sorted(ids)), "vs_currencies": ",".join(sorted(c.lower() for c in currencies)),
        "include_last_updated_at": "true", "precision": "full"}).json()
    now, found = timezone.now(), {}
    for coin, row in (raw or {}).items():
        try:
            when = datetime.fromtimestamp(int(row["last_updated_at"]), tz=dt_timezone.utc)
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
        if not timedelta(minutes=-10) <= now - when <= MAX_AGE:  # a price from the future or older than a day is not used
            continue
        for currency in currencies:
            try:
                price = Decimal(str(row[currency.lower()]))
            except (KeyError, InvalidOperation):
                continue
            if price.is_finite() and price > 0:
                found[(coin, currency)] = (price, timezone.localtime(when).date())
    return found


def refresh_crypto_values():
    """Revalue crypto holdings, each judged from its own locked row as fund_prices does.

    A missing, old or unusable price leaves the holding exactly as it was and is counted in without_fresh_price.
    """
    tracked = Investment.objects.filter(amfi_scheme_code="", units__gt=0, currency__isnull=False).exclude(coingecko_id="")
    rows = list(tracked.values_list("pk", "coingecko_id", "currency"))
    if not rows:
        return {"checked": 0, "updated": 0, "without_fresh_price": 0}
    try:
        prices = _prices({coin for _, coin, _ in rows}, {currency for _, _, currency in rows})
    except ERRORS:
        prices = {}
    updated = unpriced = 0
    for pk, _, _ in rows:
        with transaction.atomic():
            row = tracked.select_for_update().filter(pk=pk).first()
            if row is None:  # deleted, or edited so it is no longer a priced coin
                continue
            price, day = prices.get((row.coingecko_id, row.currency), (None, None))
            nav = price.quantize(STEP, ROUND_HALF_UP) if price else None
            if not nav:  # shortcut: a coin priced under 0.0001 cannot be stored; widen Investment.nav if such coins matter
                unpriced += 1
                continue
            if row.nav_date and day < row.nav_date:  # older evidence never replaces newer
                continue
            try:
                value = investment_money(row.units * price)
            except ValueError:  # outside the stored money range
                unpriced += 1
                continue
            if (row.nav, row.nav_date, row.current_value) == (nav, day, value):
                continue
            row.current_value, row.nav, row.nav_date = value, nav, day
            row.save(update_fields=["current_value", "nav", "nav_date", "updated_at"])
            updated += 1
    return {"checked": len(rows), "updated": updated, "without_fresh_price": unpriced}
