"""INV-07 value alerts: owner-set limits on a holding's value, checked by the hourly task bots after each price update.

A limit is kept in the holding's own recorded currency inside the encrypted local vault; nothing is converted (FX stays
out of the maths). A holding with no value, a fund price that is not current, or a currency changed since the limit was
set is reported as not checked, never as crossed. ALFRED only tells the owner; nothing is bought or sold.
"""
from copy import deepcopy
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.ml_engine.services.persistent_memory import _owner
from ..money import investment_money
from .fund_prices import nav_state
from .review_alerts import AlertConflict

KEY = "investment_value_alerts"
LIMIT = 50
LIMITATIONS = ("Limits compare each holding's current value in its own recorded currency. Fund values follow AMFI's daily "
               "price; other holdings use the value you recorded. Not a price forecast or trading signal; ALFRED never buys or sells.")


class ValidationError(APIException):
    """A 400 whose {"detail": text} the page shows as it is (DRF's own ValidationError sends a bare list)."""
    status_code = 400
    default_code = "invalid"


def _amount(value):
    if value is None or value == "":
        return None
    if isinstance(value, (bool, float)) or not isinstance(value, (int, str)):
        raise ValidationError("Enter each limit as an amount, or leave it empty.")
    try:
        amount = investment_money(value)
    except (ValueError, ArithmeticError):
        raise ValidationError("Enter each limit as an amount, or leave it empty.") from None
    if amount <= 0:
        raise ValidationError("A limit must be above zero.")
    return amount


def check(row, alert):
    """(status, reason): below, above, inside, or unknown when the value cannot be judged."""
    if (row.currency or "") != alert["currency"]:
        return "unknown", "The holding's currency changed after this limit was set. Set the limit again."
    if not row.current_value:
        return "unknown", "No current value is recorded for this holding."
    if nav_state(row) in ("waiting", "stale"):
        return "unknown", "The price is not current, so the limit was not checked."
    if alert["below"] is not None and row.current_value < Decimal(alert["below"]):
        return "below", ""
    if alert["above"] is not None and row.current_value > Decimal(alert["above"]):
        return "above", ""
    return "inside", ""


class ValueAlerts:
    def __init__(self, store):
        self.store = store

    def run(self, user, payload=None):
        from ..models import Investment
        rows = {row.pk: row for row in Investment.objects.filter(user=user).order_by("asset_name", "pk")}
        owner = _owner(user)
        with self.store._transaction() as db:
            state = self.store._sync_state(db, owner)
            saved = state.get(KEY)
            policy = deepcopy(saved if saved is not None else {"revision": 0, "items": {}})
            if (not isinstance(policy, dict) or type(policy.get("revision")) is not int or not isinstance(policy.get("items"), dict)
                    or len(policy["items"]) > LIMIT):
                raise RuntimeError("Value alert verification failed.")
            gone = [key for key in policy["items"] if not key.isdigit() or int(key) not in rows]
            for key in gone:  # a deleted holding takes its limit with it
                del policy["items"][key]
            if payload is not None:
                if type(payload.get("revision")) is not int or payload["revision"] != policy["revision"]:
                    raise AlertConflict()
                row = rows.get(payload["id"]) if type(payload.get("id")) is int else None
                if row is None:
                    raise ValidationError("Choose one of your holdings.")
                if payload.get("action") == "set":
                    if set(payload) - {"action", "revision", "id", "below", "above"}:
                        raise ValidationError("Send only the holding and its limits.")
                    below, above = _amount(payload.get("below")), _amount(payload.get("above"))
                    if below is None and above is None:
                        raise ValidationError("Enter a lower limit, an upper limit or both.")
                    if below is not None and above is not None and below >= above:
                        raise ValidationError("The lower limit must be below the upper limit.")
                    if str(row.pk) not in policy["items"] and len(policy["items"]) >= LIMIT:
                        raise ValidationError(f"Value alerts cover at most {LIMIT} holdings.")
                    policy["items"][str(row.pk)] = {"below": None if below is None else str(below),
                        "above": None if above is None else str(above), "currency": row.currency or "",
                        "set_at": timezone.now().isoformat()}
                elif payload.get("action") == "clear" and set(payload) == {"action", "revision", "id"}:
                    policy["items"].pop(str(row.pk), None)
                else:
                    raise ValidationError("Choose set or clear.")
            if payload is not None or gone:
                policy["revision"] += 1
                state[KEY] = policy
                self.store._write_sync_state(db, owner, state)
        items = []
        for key, alert in policy["items"].items():
            row = rows[int(key)]
            status, reason = check(row, alert)
            items.append({"id": row.pk, "name": row.asset_name, "currency": alert["currency"] or "INR", "below": alert["below"],
                          "above": alert["above"], "value": str(row.current_value) if row.current_value else None,
                          "nav_date": row.nav_date.isoformat() if row.nav_date else None, "status": status, "reason": reason})
        return {"revision": policy["revision"], "items": items, "limit": LIMIT, "limitations": LIMITATIONS,
                "holdings": [{"id": row.pk, "name": row.asset_name, "currency": row.currency or "INR"} for row in rows.values()]}


def crossed(user):
    from apps.ml_engine.api.memory import memory_store
    return [item for item in ValueAlerts(memory_store()).run(user)["items"] if item["status"] in ("below", "above")]
