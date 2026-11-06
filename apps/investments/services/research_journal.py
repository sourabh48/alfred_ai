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


def lessons(user, instrument: str) -> dict:
    from apps.investments.models import ResearchDecision

    settled = ResearchDecision.objects.filter(user=user, settled_on__isnull=False).exclude(lesson="").order_by("-settled_on", "-id")
    key = instrument.strip().casefold()
    same = [item for item in settled.filter(instrument__iexact=instrument.strip())[:SAME_INSTRUMENT_LESSONS]]
    others = [item for item in settled.exclude(instrument__iexact=instrument.strip())[:OTHER_LESSONS]] if key else []
    row = lambda item: {"id": item.pk, "instrument": item.instrument, "rating": item.rating, "decided_on": item.decided_on.isoformat(),
                        "settled_on": item.settled_on.isoformat(), "lesson": item.lesson, **outcome(item)}
    return {"same_instrument": [row(item) for item in same], "other_instruments": [row(item) for item in others]}
