"""Owner research decisions: pending until the review date, then settled against owner-entered prices.

Settlement and lesson recall follow TradingAgents (Apache-2.0, pin e8f5503e: memory/settlement.py, memory/log.py),
independently written: return and alpha against a benchmark once the full window has passed, and the most recent
settled lessons (5 for the same instrument, 3 from others) shown before a new call. No price is fetched or guessed.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

SAME_INSTRUMENT_LESSONS = 5
OTHER_LESSONS = 3
BULLISH, BEARISH = {"buy", "overweight"}, {"sell", "underweight"}


def _percent(entry, exit_):
    if entry is None or exit_ is None or entry <= 0:
        return None
    return ((Decimal(exit_) / Decimal(entry) - 1) * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def outcome(decision) -> dict:
    """Return, benchmark return and alpha in percent, and whether the move went the rating's way."""
    if decision.settled_on is None:
        return {"status": "pending", "review_on": decision.review_on.isoformat()}
    raw = _percent(decision.entry_price, decision.exit_price)
    bench = _percent(decision.benchmark_entry, decision.benchmark_exit)
    alpha = raw - bench if raw is not None and bench is not None else None
    measure = alpha if alpha is not None else raw
    if decision.rating in BULLISH:
        direction = "supported" if measure > 0 else "not_supported"
    elif decision.rating in BEARISH:
        direction = "supported" if measure < 0 else "not_supported"
    else:
        direction = "not_judged"  # a Hold makes no directional call
    return {"status": "settled", "return_percent": raw, "benchmark_return_percent": bench, "alpha_percent": alpha,
            "measured_against": "benchmark" if alpha is not None else "price only", "direction": direction}


def identity(name: str) -> str:
    """One instrument however its name was typed: case and runs of spaces do not make a different stock."""
    return " ".join(str(name or "").split()).casefold()


def thesis_history(user, *, today) -> list[dict]:
    """The owner's views grouped by instrument, oldest first, with which view replaced which and whether the
    current one is past its check date. Read-only; holdings are only read to say whether the owner also holds it."""
    from apps.investments.models import Investment, ResearchDecision

    held = {identity(name) for name in Investment.objects.filter(user=user).values_list("asset_name", flat=True)}
    groups: dict[str, list] = {}
    for item in ResearchDecision.objects.filter(user=user).order_by("decided_on", "id"):
        groups.setdefault(identity(item.instrument), []).append(item)
    rows = []
    for key, items in groups.items():
        versions = []
        for number, item in enumerate(items, start=1):
            later = items[number] if number < len(items) else None
            versions.append({"id": item.pk, "version": number, "rating": item.rating,
                             "previous_rating": items[number - 2].rating if number > 1 else None,
                             "thesis": item.thesis, "decided_on": item.decided_on.isoformat(), "review_on": item.review_on.isoformat(),
                             "replaced_on": later.decided_on.isoformat() if later else None,
                             "replaced_by": later.pk if later else None,
                             # replaced before anyone checked whether it was right
                             "replaced_unchecked": bool(later) and item.settled_on is None,
                             **outcome(item)})
        current = items[-1]
        if current.settled_on is not None:
            freshness = "checked"
        elif current.review_on <= today:
            freshness = "review_due"
        else:
            freshness = "current"
        rows.append({"key": key, "instrument": current.instrument, "held": key in held, "freshness": freshness,
                     "current_id": current.pk, "versions": versions[::-1]})
    return sorted(rows, key=lambda row: ({"review_due": 0, "current": 1, "checked": 2}[row["freshness"]], row["key"]))


def lessons(user, instrument: str) -> dict:
    from apps.investments.models import ResearchDecision

    settled = ResearchDecision.objects.filter(user=user, settled_on__isnull=False).exclude(lesson="").order_by("-settled_on", "-id")
    key = identity(instrument)
    same = [item for item in settled if identity(item.instrument) == key][:SAME_INSTRUMENT_LESSONS] if key else []
    others = [item for item in settled if identity(item.instrument) != key][:OTHER_LESSONS] if key else []
    row = lambda item: {"id": item.pk, "instrument": item.instrument, "rating": item.rating, "decided_on": item.decided_on.isoformat(),
                        "settled_on": item.settled_on.isoformat(), "lesson": item.lesson, **outcome(item)}
    return {"same_instrument": [row(item) for item in same], "other_instruments": [row(item) for item in others]}
