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

from alfred_private_storage import private_directory

# name: (label, what ALFRED uses it for, where to get one)
KEYS = {
    "TRAVEL_GOOGLE_MAPS_API_KEY": ("Google Maps", "Travel: the map, places and hotels (Google only), plus routes and travel times when the free services have no answer.",
                                   "https://console.cloud.google.com/google/maps-apis/credentials"),
    "TRAVEL_ORS_API_KEY": ("OpenRouteService", "Travel: driving, cycling and walking routes (it has a free plan).",
                           "https://openrouteservice.org/dev/#/signup"),
    "TRAVEL_BRAVE_API_KEY": ("Brave Search", "Travel: web search for places, with your OK for paid searches below.",
                             "https://brave.com/search/api/"),
    "TRAVEL_TRAVELPAYOUTS_TOKEN": ("Travelpayouts (Aviasales)", "Travel: free flight prices other travellers found recently (not live). Free partner sign-up; the token is under Profile > API token.",
                                   "https://www.travelpayouts.com/"),
    "TRAVEL_DUFFEL_API_KEY": ("Duffel", "Travel: flight prices, with your OK for paid searches below.", "https://app.duffel.com/join"),
    "TRAVEL_OPEN_METEO_API_KEY": ("Open-Meteo (commercial)", "Travel: weather and place names. Not needed for personal use.",
                                  "https://open-meteo.com/en/pricing"),
}
# name: (value written when on, what the switch means)
SWITCHES = {
    "TRAVEL_USE_MODE": ("personal_noncommercial",
                        "I use ALFRED for myself, not for a business. Turns on free weather and place search from Open-Meteo."),
    "TRAVEL_VALHALLA_URL": ("https://valhalla1.openstreetmap.de",
                            "Free car and motorcycle routes from the FOSSGIS server. Each route sends only the trip's start and end points."),
    "TRAVEL_BRAVE_ALLOW_PAID_SEARCH": ("true", "Brave Search may run searches that count against your Brave plan."),
    "TRAVEL_DUFFEL_ALLOW_PAID_SEARCH": ("true", "Duffel may run flight searches that Duffel may charge for. Check its fees first."),
}
# Mail for Career emails you approve one at a time: an address and an app password; the server is filled in for known providers.
MAIL_PROVIDERS = {"gmail.com": ("smtp.gmail.com", 587, False), "googlemail.com": ("smtp.gmail.com", 587, False),
                  "yahoo.com": ("smtp.mail.yahoo.com", 465, True), "yahoo.co.in": ("smtp.mail.yahoo.com", 465, True),
                  "zoho.com": ("smtp.zoho.com", 465, True), "zoho.in": ("smtp.zoho.in", 465, True)}
MAIL = ("ALFRED_SMTP_HOST", "ALFRED_SMTP_PORT", "ALFRED_SMTP_SSL", "ALFRED_SMTP_USER", "ALFRED_SMTP_PASSWORD", "ALFRED_SMTP_FROM")
VALUE = re.compile(r"^[\x21-\x26\x28-\x7e]{8,512}$")  # printable, no spaces or quotes, so the env file stays one value a line
EMAIL = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@([A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}$")
HOST = re.compile(r"^(?=.{4,253}$)([A-Za-z0-9-]{1,63}\.)+[A-Za-z]{2,24}$")


def config_path() -> Path:
    # The same file settings.py loads at start-up.
    return Path(os.environ.get("ALFRED_DATA_DIR") or settings.BASE_DIR) / "config" / "local.env"


def can_manage(user) -> bool:
    """The superuser, or on a PC with none, the first account (the person who set ALFRED up). Keys are shared app-wide."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    if user.is_superuser:
        return True
    users = get_user_model().objects
    return not users.filter(is_superuser=True).exists() and users.filter(is_active=True).order_by("date_joined", "pk").first() == user


def status(user) -> dict:
    hint = lambda name: ("…" + os.environ[name][-4:]) if os.environ.get(name) else ""
    mail_user = os.environ.get("ALFRED_SMTP_USER", "")
    return {
        "can_manage": can_manage(user),
        "keys": [{"name": name, "label": label, "use": use, "signup": url, "saved": bool(os.environ.get(name)), "hint": hint(name)}
                 for name, (label, use, url) in KEYS.items()],
        "switches": [{"name": name, "detail": detail, "on": os.environ.get(name) == value} for name, (value, detail) in SWITCHES.items()],
        "mail": {"address": mail_user if can_manage(user) else "", "ready": bool(mail_user and os.environ.get("ALFRED_SMTP_PASSWORD")),
                 "host": os.environ.get("ALFRED_SMTP_HOST", "")},
        "openai": "Saved per person under Memory and AI below: each person can add their own OpenAI key.",
    }


def _mail_values(data) -> dict:
    address = str(data.get("address") or "").strip()
    password = "".join(str(data.get("password") or "").split())  # app passwords are often shown in groups of four
    if not address and not password:
        return {name: "" for name in MAIL}  # both empty: mail sending off
    if not EMAIL.fullmatch(address) or not VALUE.fullmatch(password):
        raise ValueError("Enter your email address and its app password (at least 8 characters, no quotes).")
    known = MAIL_PROVIDERS.get(address.rsplit("@", 1)[1].lower())
    host = str(data.get("host") or "").strip().lower() or (known[0] if known else "")
    if not HOST.fullmatch(host):
        raise ValueError("ALFRED does not know this email provider's server. Enter its SMTP server name.")
    port = str(data.get("port") or (known[1] if known and host == known[0] else 587))
    port = int(port) if port.isdigit() and len(port) < 6 else 0
    if port not in (25, 465, 587, 2525):
        raise ValueError("Use SMTP port 465 or 587.")
    return {"ALFRED_SMTP_HOST": host, "ALFRED_SMTP_PORT": str(port), "ALFRED_SMTP_SSL": "true" if port == 465 else "false",
            "ALFRED_SMTP_USER": address, "ALFRED_SMTP_PASSWORD": password, "ALFRED_SMTP_FROM": address}


def changes_from(data: dict) -> dict:
    """{name: value or ''} from a request; '' removes the line. Raises ValueError before anything is written."""
    changes = {}
    for name, value in (data.get("keys") or {}).items():
        if name not in KEYS:
            raise ValueError("Unknown service.")
        value = str(value or "").strip()
        if value and not VALUE.fullmatch(value):
            raise ValueError(f"That {KEYS[name][0]} key does not look right: paste it without spaces or quotes.")
        changes[name] = value
    for name, on in (data.get("switches") or {}).items():
        if name not in SWITCHES or not isinstance(on, bool):
            raise ValueError("Unknown switch.")
        changes[name] = SWITCHES[name][0] if on else ""
    if "mail" in data:
        changes |= _mail_values(data["mail"] if isinstance(data["mail"], dict) else {})
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
        if name in MAIL:  # settings.py read these at start-up; refresh the running copy
            default = {"ALFRED_SMTP_PORT": 587, "ALFRED_SMTP_SSL": False}.get(name, "")
            typed = int(value) if name == "ALFRED_SMTP_PORT" and value else value == "true" if name == "ALFRED_SMTP_SSL" and value else value
            setattr(settings, name, typed if value else default)
