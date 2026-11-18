"""Backtest of the research desk: the same rules replayed on past days and scored three months later against NIFTY 50.

Follows TradingAgents' backtest.py idea (Apache-2.0, pin 9fa1196f): many (share, day) cells through the same decision
machinery, read in aggregate. Like it, this judges decisions and is not a portfolio simulator: no quantities, fills or
cash. Independently written. No look-ahead: each past day sees only closes up to that day and statements whose period
ended at least LAG_DAYS earlier (Yahoo gives period ends, not filing dates). Only public symbols go to Yahoo; nothing
about the owner is sent, stored online or changed.
"""
from __future__ import annotations

import logging
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import ROUND_HALF_UP, Decimal

from django.core.cache import cache
from django.utils import timezone

from .research_desk import FETCH_ERRORS, HELD_LABEL, NEW_LABEL, REVIEW_DAYS, rate
from .research_packet import fetch_fundamentals, fetch_prices

logger = logging.getLogger(__name__)
LAG_DAYS, YEARS, STEP_DAYS, WINDOW = 90, 4, 30, 252
BENCHMARK = "%5ENSEI"
BULLISH, BEARISH = ("buy", "overweight"), ("underweight", "sell")


def _history(symbol: str) -> dict:
    key = f"research-backtest:{symbol}"
    found = cache.get(key)
    if found is None:
        found = {"fundamentals": {} if symbol.startswith(("^", "%5E")) else fetch_fundamentals(symbol),
                 "prices": fetch_prices(symbol, years=YEARS)}
        cache.set(key, found, 12 * 3600)
    return found


def _days(prices: dict) -> list:
    return [datetime.fromtimestamp(stamp, dt_timezone.utc).date() for stamp in prices.get("timestamp") or []]


def _pct(before, after):
    return ((after / before - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)


def replay(symbol: str, fundamentals: dict, prices: dict, bench: dict | None, *, until: date) -> list:
    """One cell per month-start with a rating: the call, the share's move over the next REVIEW_DAYS, and NIFTY 50's."""
    closes, stamps, days = prices.get("close") or [], prices.get("timestamp") or [], _days(prices)
    bench_closes, bench_days = (bench or {}).get("close") or [], _days(bench or {})
    if len(closes) < WINDOW + 40:
        return []
    cells, day = [], days[WINDOW - 1] + timedelta(days=1)
    while day + timedelta(days=REVIEW_DAYS) <= min(days[-1], until):
        i = bisect_right(days, day) - 1
        window = {"close": closes[max(0, i - WINDOW + 1):i + 1], "timestamp": stamps[max(0, i - WINDOW + 1):i + 1],
                  "currency": prices.get("currency")}
        known = {name: [row for row in rows if row[0] + timedelta(days=LAG_DAYS) <= day] for name, rows in fundamentals.items()}
        rated = rate(symbol, known, window, today=day)
        exit_index = bisect_left(days, day + timedelta(days=REVIEW_DAYS))
        if rated and exit_index < len(days):
            move = _pct(closes[i], closes[exit_index])
            b_in, b_out = bisect_right(bench_days, day) - 1, bisect_left(bench_days, day + timedelta(days=REVIEW_DAYS))
            market = _pct(bench_closes[b_in], bench_closes[b_out]) if b_in >= 0 and b_out < len(bench_closes) else None
            cells.append({"symbol": symbol, "day": day.isoformat(), "rating": rated[2]["rating"], "return_pct": move,
                          "benchmark_pct": market, "alpha_pct": None if market is None else move - market})
        day += timedelta(days=STEP_DAYS)
    return cells


def summarise(cells: list) -> list:
    """Per rating: how many calls, the average move, the average move against NIFTY 50, and how often it went the call's way."""
    rows = []
    for rating in ("buy", "overweight", "hold", "underweight", "sell"):
        group = [cell for cell in cells if cell["rating"] == rating]
        if not group:
            continue
        average = lambda values: (sum(values) / len(values)).quantize(Decimal("0.1"), ROUND_HALF_UP) if values else None
        versus = [cell["alpha_pct"] for cell in group if cell["alpha_pct"] is not None]
        measure = lambda cell: cell["alpha_pct"] if cell["alpha_pct"] is not None else cell["return_pct"]
        right = (sum(measure(cell) > 0 for cell in group) if rating in BULLISH else
                 sum(measure(cell) < 0 for cell in group) if rating in BEARISH else None)
        rows.append({"rating": rating, "label": f"{NEW_LABEL[rating]} / {HELD_LABEL[rating]}", "calls": len(group),
                     "average_move_pct": str(average([cell["return_pct"] for cell in group])),
                     "average_vs_nifty_pct": None if not versus else str(average(versus)),
                     "went_its_way_pct": None if right is None else str((Decimal(right) * 100 / len(group)).quantize(Decimal("1")))})
    return rows


def replay_all(shares: list, today: date) -> dict:
    """Replay every share; one that fails never stops the rest. Returns what the page and report show."""
    try:
        bench = _history(BENCHMARK)["prices"]
    except FETCH_ERRORS:
        bench = None
    cells, skipped = [], []
    for symbol, name in shares:
        try:
            data = _history(symbol)
        except FETCH_ERRORS as error:
            logger.warning("Backtest could not read one symbol (%s)", type(error).__name__)
            skipped.append({"name": name, "reason": "No dated history came back from Yahoo Finance."})
            continue
        found = replay(symbol, data["fundamentals"], data["prices"] or {}, bench if symbol.endswith((".NS", ".BO")) else None, until=today)
        if not found:
            skipped.append({"name": name, "reason": "Too little dated history to replay."})
        cells += found
    judged = [cell for cell in cells if cell["rating"] not in ("hold",)]
    measure = lambda cell: cell["alpha_pct"] if cell["alpha_pct"] is not None else cell["return_pct"]
    right = sum((measure(cell) > 0) if cell["rating"] in BULLISH else (measure(cell) < 0) for cell in judged)
    return {"at": timezone.now().isoformat(), "shares": len(shares) - len(skipped), "calls": len(cells),
            "from": min((cell["day"] for cell in cells), default=None), "to": max((cell["day"] for cell in cells), default=None),
            "went_its_way_pct": str((Decimal(right) * 100 / len(judged)).quantize(Decimal("1"))) if judged else None,
            "by_rating": summarise(cells), "skipped": skipped,
            "recent": sorted(({**cell, **{key: str(cell[key]) if cell[key] is not None else None for key in ("return_pct", "benchmark_pct", "alpha_pct")}}
                              for cell in cells), key=lambda cell: cell["day"], reverse=True)[:30],
            "limits": [f"Past calls use today's rules on the prices and results known then, checked {REVIEW_DAYS} days later. "
                       "This judges the rules; it does not predict what comes next.",
                       f"Results are assumed public {LAG_DAYS} days after the period ended; Yahoo may have revised old figures since.",
                       "Calls a month apart overlap in time, so they are not independent tests.",
                       "Only shares on your list today are replayed, which leaves out companies that did badly and were dropped.",
                       "Headlines, ideas and personal fit are not part of the replay. No costs or taxes are counted."]}
