"""Online services the PC's owner turns on from Settings, instead of editing config/local.env by hand.

Values go to the same private config/local.env that ALFRED reads at start-up, and take effect at once in the running
app. Only service keys and switches listed here can be written; nothing here touches banking or personal records,
and the privacy rules of each service (what it may be sent) stay where they are.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model

from alfred_ai import bundled_keys
from alfred_ai.services import personal_keys
from alfred_private_storage import private_directory

# Paid services and free ones with a usage limit: every person may save their own key (owner decision 2026-11-19).
# name: (label, what ALFRED uses it for, where to get one). Free keys without a practical limit are built in and not listed.
KEYS = {
    "TRAVEL_GOOGLE_MAPS_API_KEY": ("Google Maps Platform", "Travel: the map, places, hotels, routes, place names, weather and air quality. Enable Map Tiles, Places (New), Routes, Weather and Air Quality for this key.",
                                   "https://console.cloud.google.com/google/maps-apis/credentials"),
    "TRAVEL_SKYSCANNER_API_KEY": ("Skyscanner", "Travel: live flight prices, once Skyscanner approves your partner account. Until then each trip has a Google Flights link.",
                                  "https://www.partners.skyscanner.net/product/travel-api"),
    "ALFRED_ALPHA_VANTAGE_API_KEY": ("Alpha Vantage", "Investments research desk: the latest earnings against forecasts and insider trading for US shares. "
                                     "The shared free key allows 25 requests a day for everyone; your own key gives you your own 25.",
                                     "https://www.alphavantage.co/support/#api-key"),
    "ALFRED_FINNHUB_API_KEY": ("Finnhub", "Investments research desk: earnings against forecasts, analyst views, insider trading and this week's "
                               "company news for US shares. The free key allows 60 requests a minute; when saved it is used instead of Alpha Vantage.",
                               "https://finnhub.io/register"),
    "ALFRED_AERODATABOX_API_KEY": ("AeroDataBox (RapidAPI)", "Travel: live status of flights you booked (delays, gate, terminal), shown on the trip the day "
                                   "before and the day it leaves. Subscribe to AeroDataBox's free Basic plan on RapidAPI and paste your RapidAPI key; "
                                   "ALFRED keeps to 250 lookups a month.", "https://rapidapi.com/aedbx-aedbx/api/aerodatabox/pricing"),
}
# name: (value written when on, what the switch means). Google is the only travel source (owner decision 2026-11-14).
SWITCHES = {"ALFRED_PRICES_ALPHA_VANTAGE_FIRST": ("true", "Research desk: read daily share prices from Alpha Vantage first, and Yahoo Finance "
                                                          "only if that fails (needs the Alpha Vantage key; 25 requests a day on the free key).")}
VALUE = re.compile(r"^[\x21-\x26\x28-\x7e]{8,512}$")  # printable, no spaces or quotes, so the env file stays one value a line


def config_path() -> Path:
    # The same file settings.py loads at start-up.
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "config" / "local.env"


def can_manage(user) -> bool:
    """The superuser, or on a PC with none, the first account (the person who set ALFRED up). The free-service switch is
    shared app-wide; service keys (personal_keys) and Career email (career_mail) are each person's own."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    users = get_user_model().objects
    return not users.filter(is_superuser=True).exists() and users.filter(is_active=True).order_by("date_joined", "pk").first() == user


def status(user) -> dict:
    # Only the person's own key is hinted at; a shared PC-wide or built-in key is never shown, not even its last characters.
    from apps.career.services import career_mail
    keys = []
    for name, (label, use, url) in KEYS.items():
        mine = personal_keys.own(user, name)
        keys.append({"name": name, "label": label, "use": use, "signup": url, "saved": bool(mine), "hint": "…" + mine[-4:] if mine else "",
                     "shared": not mine and bool(os.environ.get(name))})
    return {
        "can_manage": can_manage(user),
        "keys": keys,
        "switches": [{"name": name, "detail": detail, "on": os.environ.get(name) == value} for name, (value, detail) in SWITCHES.items()],
        "mail": career_mail.status(user),
    }


def key_changes(data: dict) -> dict:
    """{name: value or ''} of the person's own keys from a request; '' removes theirs. Raises ValueError before anything is written."""
    changes = {}
    for name, value in (data.get("keys") or {}).items():
        if name not in KEYS:
            raise ValueError("Unknown service.")
        value = str(value or "").strip()
        if value and not VALUE.fullmatch(value):
            raise ValueError(f"That {KEYS[name][0]} key does not look right: paste it without spaces or quotes.")
        changes[name] = value
    return changes


def changes_from(data: dict) -> dict:
    """{name: value or ''} of the shared switches; '' removes the line. Raises ValueError before anything is written."""
    changes = {}
    for name, on in (data.get("switches") or {}).items():
        if name not in SWITCHES or not isinstance(on, bool):
            raise ValueError("Unknown switch.")
        changes[name] = SWITCHES[name][0] if on else ""
    return changes


def save(changes: dict) -> None:
    """Rewrite only the named lines of config/local.env (other lines kept), then apply them to the running app."""
    path = config_path()
    private_directory(path.parent)  # refuses a config folder whose permissions are not private, rather than repairing them
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    kept = [line for line in lines if line.split("=", 1)[0].strip().removeprefix("export ").strip() not in changes]
    kept += [f"{name}='{value}'" for name, value in changes.items() if value]
    temporary = path.with_name(path.name + ".saving")
    temporary.write_text("\n".join(kept) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    for name, value in changes.items():
        if value:
            os.environ[name] = value
        else:
            os.environ.pop(name, None)
            bundled_keys.restore(name)
