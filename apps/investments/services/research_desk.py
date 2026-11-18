"""Automatic research desk (owner request 2026-11-18): ALFRED researches by itself and suggests; the owner accepts or rejects.

The order of roles follows TradingAgents (Apache-2.0, pin 9fa1196f: graph/setup.py, agents/rating.py, memory/settlement.py):
analysts, bull and bear cases, research manager, trader, risk team, portfolio manager, decision log, then settlement and
a lesson. Independently written, and different on purpose in one way: every role here is a fixed rule over the packet's
dated numbers, so the same data always gives the same rating and no model can invent a figure. The local model's bull,
bear and risk arguments stay one click away (research_challenge) and cannot change a rating. Like TradingAgents' REVIEW
signal, thin or stale evidence gives no rating at all. Nothing is bought, sold or written to holdings: an accepted
suggestion becomes a research-journal entry, which ALFRED later checks against Yahoo's closing price.

Suggestions and settings live in OperationalLog, like the task-bot proposals, so this needs no migration.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from uuid import uuid4

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from alfred_ai.services import public_http
from alfred_ai.services.currency import CURRENCY_CHOICES
from apps.reports.models import OperationalLog
from apps.reports.services import operational_logging_service
from .research_journal import outcome
from .research_packet import SYMBOL, beginner_view, build_packet, price_metrics, research_data

logger = logging.getLogger(__name__)
SCOPE = "research_desk"
PENDING, ACCEPTED, REJECTED, SUPERSEDED = (f"research_suggestion_{state}" for state in ("pending", "accepted", "rejected", "superseded"))
SETTINGS, RUN = "research_desk_settings", "research_desk_run"
# A starting list so there is something to compare, not a recommendation. No banks or lenders: they carry debt by
# design, so the packet's debt and cash screens would misjudge them.
DEFAULT_WATCH = {"RELIANCE.NS": "Reliance Industries", "TCS.NS": "Tata Consultancy Services", "INFY.NS": "Infosys",
                 "HINDUNILVR.NS": "Hindustan Unilever", "ITC.NS": "ITC", "BHARTIARTL.NS": "Bharti Airtel", "LT.NS": "Larsen & Toubro",
                 "MARUTI.NS": "Maruti Suzuki India", "SUNPHARMA.NS": "Sun Pharmaceutical", "ASIANPAINT.NS": "Asian Paints"}
WATCH_LIMIT, UNIVERSE_LIMIT, STALE_DAYS, REVIEW_DAYS, RUN_LOCK_SECONDS = 15, 20, 7, 91, 120
HELD_LABEL = {"buy": "Buy more", "overweight": "Add a little", "hold": "Keep", "underweight": "Reduce", "sell": "Sell"}
NEW_LABEL = {"buy": "Buy", "overweight": "Buy a little", "hold": "Wait and watch", "underweight": "Avoid", "sell": "Avoid"}
FETCH_ERRORS = (public_http.PublicHTTPError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError, OSError)


def _records(user):
    return OperationalLog.objects.filter(user=user, module="investments", scope=SCOPE)


def _log(user, event, message, payload, category="background"):
    return operational_logging_service.log(user=user, module="investments", category=category, scope=SCOPE,
                                           event_type=event, message=message, payload=payload)


def listed(text) -> str | None:
    """An exchange symbol such as INFY.NS, or None. Indices and bare names are not researched automatically."""
    symbol = str(text or "").strip().upper()
    return symbol if SYMBOL.fullmatch(symbol) and "." in symbol and not symbol.startswith("^") else None


# ---- what to research -------------------------------------------------------------------------------------------

def desk_settings(user) -> dict:
    saved = _records(user).filter(event_type=SETTINGS).order_by("-created_at", "-id").first()
    if saved:
        return {"watch": saved.payload["watch"], "include_holdings": bool(saved.payload["include_holdings"])}
    return {"watch": [{"symbol": symbol, "name": name} for symbol, name in DEFAULT_WATCH.items()], "include_holdings": False}


def save_settings(user, *, watch=None, include_holdings=None) -> dict:
    current = desk_settings(user)
    if watch is not None:
        current["watch"] = watch[:WATCH_LIMIT]
    if include_holdings is not None:
        current["include_holdings"] = include_holdings is True
    _log(user, SETTINGS, "Research desk settings saved.", current, category="api")
    return current


def watch_add(user, text) -> dict:
    symbol = listed(text)
    if not symbol:
        raise ValueError("Enter an exchange symbol such as INFY.NS (NSE) or 500209.BO (BSE). Look a company up below to find it.")
    current = desk_settings(user)
    if symbol in {item["symbol"] for item in current["watch"]}:
        return current
    if len(current["watch"]) >= WATCH_LIMIT:
        raise ValueError(f"The watch list holds at most {WATCH_LIMIT} shares. Remove one first.")
    research_data(symbol)  # ValueError when Yahoo has no dated data for it
    return save_settings(user, watch=current["watch"] + [{"symbol": symbol, "name": DEFAULT_WATCH.get(symbol, symbol)}])


def watch_remove(user, symbol) -> dict:
    current = desk_settings(user)
    return save_settings(user, watch=[item for item in current["watch"] if item["symbol"] != symbol])


def universe(user) -> tuple[list, list]:
    """([(symbol, name, holding or None)], [owned shares without a symbol]): your shares (if allowed), recent searches, the watch list."""
    from apps.investments.models import Investment, ResearchSearch

    current, rows, unmatched = desk_settings(user), {}, []
    if current["include_holdings"]:
        for holding in Investment.objects.filter(user=user, asset_type="equity").order_by("-current_value", "id"):
            symbol = listed(holding.asset_name)
            if symbol and holding.asset_name.strip().upper() == symbol:  # the packet's own rule for a matching holding
                rows.setdefault(symbol, (symbol, symbol, holding))
            else:
                unmatched.append(holding.asset_name)
    for symbol in ResearchSearch.objects.filter(user=user).values_list("symbol", flat=True)[:10]:
        if listed(symbol):
            rows.setdefault(symbol, (symbol, symbol, None))
    for item in current["watch"]:
        rows.setdefault(item["symbol"], (item["symbol"], item["name"], None))
    return list(rows.values())[:UNIVERSE_LIMIT], unmatched


# ---- analysts ---------------------------------------------------------------------------------------------------

def _ema(values, span):
    k, out = 2 / (span + 1), [values[0]]
    for value in values[1:]:
        out.append(value * k + out[-1] * (1 - k))
    return out


def technical(closes: list, stamps: list) -> dict:
    """Market analyst: 50 and 200-day averages, 14-day RSI and MACD from the daily closes, plus a weekly series to draw."""
    values = [float(value) for value in closes]
    if len(values) < 60:
        return {}
    sums = [0.0]
    for value in values:
        sums.append(sums[-1] + value)
    average = lambda end, days: (sums[end + 1] - sums[end + 1 - days]) / days if end + 1 >= days else None
    last = len(values) - 1
    moves = [b - a for a, b in zip(values[-15:], values[-14:])]
    gains, losses = sum(m for m in moves if m > 0), -sum(m for m in moves if m < 0)
    rsi = 100.0 if not losses else 100 - 100 / (1 + gains / losses)
    macd = [fast - slow for fast, slow in zip(_ema(values, 12), _ema(values, 26))]
    picks = sorted(range(last, -1, -5))
    day = lambda index: datetime.fromtimestamp(stamps[index], dt_timezone.utc).date().isoformat()
    rounded = lambda value: None if value is None else round(value, 2)
    return {"sma50": rounded(average(last, 50)), "sma200": rounded(average(last, 200)), "rsi14": round(rsi, 1),
            "macd_histogram": round(macd[-1] - _ema(macd, 9)[-1], 2),
            "series": {"labels": [day(i) for i in picks], "close": [rounded(values[i]) for i in picks],
                       "sma50": [rounded(average(i, 50)) for i in picks], "sma200": [rounded(average(i, 200)) for i in picks]}}


def results_chart(fundamentals: dict, currency) -> dict:
    """Fundamentals analyst's picture: revenue and profit for up to four years that both series report, in that currency."""
    pick = lambda name: {row[0]: row[1] for row in fundamentals.get(name) or [] if row[2] == currency}
    revenue, profit = pick("TotalRevenue"), pick("NetIncome")
    periods = sorted(set(revenue) & set(profit))[-4:]
    scale, unit = (Decimal(10) ** 7, "crore") if currency == "INR" else (Decimal(10) ** 6, "million")
    return {"labels": [period.isoformat()[:7] for period in periods], "unit": f"{currency or 'currency not recorded'} {unit}",
            "revenue": [float(round(revenue[p] / scale, 1)) for p in periods], "profit": [float(round(profit[p] / scale, 1)) for p in periods]}


def headlines(name: str) -> list:
    """News analyst: up to three dated headlines, shown as they are. ALFRED does not score them."""
    from apps.ml_engine.services import web_lookup

    key = "research-desk:news:" + hashlib.sha256(name.encode()).hexdigest()[:32]
    found = cache.get(key)
    if found is None:
        try:
            found = [{"title": item["title"], "source": item["source"], "published": item["published"], "url": item["url"]}
                     for item in web_lookup._news(web_lookup.check_public(f"{name} share news"), None)
                     if item["title"] and str(item["url"]).startswith("https://")][:3]
        except (PermissionError, *FETCH_ERRORS):
            found = []
        cache.set(key, found, 6 * 3600)
    return found


def benchmark() -> dict | None:
    """NIFTY 50's last close, to compare a call with the market. None when Yahoo has no level."""
    found = cache.get("research-desk:nifty")
    if found is None:
        from apps.integrations.services.verified_intelligence import VerifiedIntelligenceService
        try:
            chart = VerifiedIntelligenceService()._fetch_yahoo_chart("%5ENSEI", range_value="5d", interval="1d")
            found = {"level": str(chart["close"][-1].quantize(Decimal("0.0001"))),
                     "as_of": datetime.fromtimestamp(chart["timestamp"][-1], dt_timezone.utc).date().isoformat()}
        except FETCH_ERRORS:
            return None
        cache.set("research-desk:nifty", found, 6 * 3600)
    return found


# ---- research manager, trader, risk team, portfolio manager -------------------------------------------------------

def decide(packet: dict, tech: dict, held: bool) -> dict | None:
    """The final five-tier rating and the step each role took, or None when the evidence is too thin or stale to rate."""
    price, lean = packet["metrics"].get("price"), packet["beginner"]["lean"]
    if lean == "not_enough" or not price or price.get("above_200_day_average") is None:
        return None
    good, bad, labels = len(packet["bullish"]), len(packet["bearish"]), HELD_LABEL if held else NEW_LABEL
    strong = lean == "positive" and good >= bad + 3 and price["above_200_day_average"]
    falling = lean == "caution" and not price["above_200_day_average"] and (tech.get("sma50") or 0) < (tech.get("sma200") or 0)
    if held:
        proposal = "buy" if strong else {"positive": "overweight", "mixed": "hold", "caution": "sell" if falling else "underweight"}[lean]
    else:
        proposal = "buy" if strong else {"positive": "overweight", "mixed": "hold", "caution": "sell"}[lean]
    risks = []
    if price["volatility_pct"] > 40:
        risks.append(f"The price swings widely ({price['volatility_pct']}% a year).")
    if price["max_drawdown_pct"] < -30:
        risks.append(f"It fell {abs(price['max_drawdown_pct'])}% from a peak in the past year.")
    if tech.get("rsi14", 0) > 70:
        risks.append(f"It has risen fast lately (14-day RSI {tech['rsi14']}), so buying now risks paying a high price.")
    concentrated = any(point["metric"] == "portfolio_weight_pct" for point in packet["bearish"])
    if concentrated:
        risks.append("It is already more than a fifth of your holdings.")
    rating = proposal
    if rating in ("buy", "overweight") and risks:
        rating = "overweight" if rating == "buy" and len(risks) == 1 and not concentrated else "hold"
    steps = [
        ("Analysts", f"Read the dated company results and a year of daily prices: {good} good sign(s), {bad} warning sign(s)."),
        ("Bull and bear researchers", "For: " + (packet["bullish"][0]["point"] if packet["bullish"] else "nothing in the numbers.")
            + " Against: " + (packet["bearish"][0]["point"] if packet["bearish"] else "nothing in the numbers.")),
        ("Research manager", f"{packet['beginner']['label']}: {packet['beginner']['headline']}"),
        ("Trader", f"Proposes: {labels[proposal]}."),
        ("Risk team", " ".join(risks) or "No extra risk flag."),
        ("Portfolio manager", f"Final suggestion: {labels[rating]}." + (" The risk flags held the proposal back." if rating != proposal else "")),
    ]
    return {"rating": rating, "label": labels[rating], "risks": risks, "score": good - bad,
            "steps": [{"role": role, "text": text} for role, text in steps]}


def analyse(symbol: str, name: str, *, holding=None, portfolio_total=None, bench=None) -> dict | None:
    data = research_data(symbol)
    prices = data["prices"] or {}
    packet = build_packet(symbol, data["fundamentals"], prices, holding=holding, portfolio_total=portfolio_total)
    fresh = packet["freshness"]["price_status"] == "recent_close" and packet["freshness"]["statement_status"] == "recent"
    tech = technical(prices.get("close") or [], prices.get("timestamp") or [])
    price = packet["metrics"].get("price") or {}
    if not fresh or not price:
        return None
    if tech.get("sma50") and tech.get("sma200"):
        up = tech["sma50"] > tech["sma200"]
        (packet["bullish"] if up else packet["bearish"]).append({
            "point": f"The 50-day average is {'above' if up else 'below'} the 200-day average: {'an upward' if up else 'a downward'} trend.",
            "metric": "trend", "value": up, "as_of": price["as_of"]})
        packet["beginner"] = beginner_view(packet["bullish"], packet["bearish"], packet["portfolio"])
    decision = decide(packet, tech, holding is not None)
    if decision is None:
        return None
    indian, valuation = symbol.endswith((".NS", ".BO")), packet["valuation"]
    point = lambda item: {"point": item["point"], "as_of": item["as_of"]}
    return {**decision, "symbol": symbol, "name": name, "held": holding is not None,
            "summary": f"{len(packet['bullish'])} good sign(s) against {len(packet['bearish'])} warning sign(s) in the dated numbers.",
            "good": [point(item) for item in packet["bullish"]], "bad": [point(item) for item in packet["bearish"]],
            "price": str(price["last_close"].quantize(Decimal("0.0001"))), "price_as_of": price["as_of"],
            "currency": packet["price_currency"], "benchmark": "NIFTY 50" if indian and bench else "",
            "benchmark_level": bench["level"] if indian and bench else None,
            "valuation": (f"The price is about {valuation['price_to_earnings']} times last year's profit per share."
                          if valuation["status"] == "estimated" else valuation["reason"]),
            "indicators": {key: tech.get(key) for key in ("sma50", "sma200", "rsi14", "macd_histogram")},
            "news": headlines(name) if name != symbol else [],
            "charts": {"price": tech.get("series"), "results": results_chart(data["fundamentals"], packet["statement_currency"])},
            "latest_period_end": packet["latest_period_end"], "source_url": packet["source_url"],
            "limits": ["Fixed rules of thumb on dated public numbers, not a forecast or licensed advice.",
                       "The screens suit ordinary companies; banks, insurers and lenders can look worse than they are.",
                       "No social-media sentiment is read. Yahoo data is daily, not a live quote, and is not independently verified.",
                       "ALFRED never buys or sells. If you agree, place the order yourself with your broker."]}


# ---- suggestions ------------------------------------------------------------------------------------------------

def _fingerprint(suggestion):
    encoded = json.dumps([suggestion["symbol"], suggestion["rating"], suggestion["held"], suggestion["latest_period_end"]])
    return hashlib.sha256(encoded.encode()).hexdigest()[:32]


@transaction.atomic
def _store(user, suggestion, today):
    suggestion = {**suggestion, "fingerprint": _fingerprint(suggestion), "for_date": today.isoformat()}
    same = None
    for record in _records(user).select_for_update().filter(event_type=PENDING, payload__symbol=suggestion["symbol"]):
        if same is None and record.payload["fingerprint"] == suggestion["fingerprint"]:
            same = record
            record.payload = {**suggestion, "id": record.payload["id"]}  # the same call with fresher numbers
            record.save(update_fields=["payload"])
        else:
            record.event_type = SUPERSEDED
            record.save(update_fields=["event_type"])
    answered = _records(user).filter(event_type__in=(ACCEPTED, REJECTED), payload__fingerprint=suggestion["fingerprint"]).exists()
    if same is None and not answered:  # an answered call comes back only when its rating or the company's results change
        _log(user, PENDING, f"Research desk suggests {suggestion['label']} for {suggestion['symbol']}; nothing changes until the owner decides.",
             {**suggestion, "id": uuid4().hex})


def refresh(user, today=None) -> dict:
    """Research every share in the owner's list once. One share that fails never stops the rest."""
    from apps.investments.models import Investment

    today = today or timezone.localdate()
    rows, unmatched = universe(user)
    total = Investment.objects.filter(user=user).in_rupee_totals().aggregate(total=Sum("current_value"))["total"] or None
    bench, researched = benchmark(), 0
    skipped = [{"name": name, "reason": "Record this holding's name as its exchange symbol (for example INFY.NS) to include it."}
               for name in unmatched]
    for symbol, name, holding in rows:
        try:
            suggestion = analyse(symbol, name, holding=holding, portfolio_total=total, bench=bench)
        except FETCH_ERRORS as error:
            logger.warning("Research desk could not read one symbol (%s)", type(error).__name__)
            skipped.append({"name": name, "reason": "No dated data came back from Yahoo Finance."})
            continue
        if suggestion is None:
            skipped.append({"name": name, "reason": "Too little recent dated data to rate it."})
            continue
        _store(user, suggestion, today)
        researched += 1
    _records(user).filter(event_type=PENDING).exclude(payload__symbol__in=[row[0] for row in rows]).update(event_type=SUPERSEDED)
    run = {"researched": researched, "skipped": skipped, "at": timezone.now().isoformat()}
    _log(user, RUN, f"Research desk read {researched} share(s).", run)
    return run


def run_now(user) -> dict:
    """Owner pressed Research now; one run at a time per owner."""
    lock = f"research-desk:running:{user.pk}"
    if not cache.add(lock, 1, RUN_LOCK_SECONDS):
        raise ValueError("Research is already running. Wait a minute.")
    try:
        return refresh(user)
    finally:
        cache.delete(lock)


def desk(user) -> dict:
    """What the page shows; reading it fetches nothing."""
    last = _records(user).filter(event_type=RUN).order_by("-created_at", "-id").first()
    suggestions = [record.payload for record in _records(user).filter(event_type=PENDING).order_by("-created_at", "-id")[:UNIVERSE_LIMIT]]
    suggestions.sort(key=lambda s: (s["rating"] == "hold", -abs(s["score"]), s["symbol"]))
    answered = [{"symbol": r.payload["symbol"], "label": r.payload["label"], "state": "accepted" if r.event_type == ACCEPTED else "rejected",
                 "decided_at": r.payload.get("decided_at")}
                for r in _records(user).filter(event_type__in=(ACCEPTED, REJECTED)).order_by("-created_at", "-id")[:10]]
    return {"settings": desk_settings(user), "watch_limit": WATCH_LIMIT, "answered": answered,
            "last_run": {key: last.payload[key] for key in ("researched", "skipped", "at")} if last else None, "suggestions": suggestions}


def _pending(user, identity):
    record = _records(user).select_for_update().filter(event_type=PENDING, payload__id=identity).first() \
        if isinstance(identity, str) and len(identity) == 32 else None
    if record is None:
        raise ValueError("This suggestion is no longer open. Refresh the page.")
    return record


@transaction.atomic
def accept(user, identity, today=None) -> dict:
    """The owner agrees: the call goes into the research journal to be checked later. Holdings are never touched."""
    from apps.investments.models import ResearchDecision

    today, record = today or timezone.localdate(), _pending(user, identity)
    s = record.payload
    if (today - date.fromisoformat(s["price_as_of"])).days > STALE_DAYS:
        raise ValueError("This research is more than a week old. Press Research now, then decide.")
    reasons = " ".join(item["point"] for item in (s["good"] if s["rating"] in ("buy", "overweight", "hold") else s["bad"])[:3])
    decision = ResearchDecision.objects.create(
        user=user, instrument=s["symbol"], rating=s["rating"], decided_on=today, review_on=today + timedelta(days=REVIEW_DAYS),
        thesis=f"ALFRED research desk: {s['label']}. {s['summary']} {reasons}"[:4000],
        currency=s["currency"] if s["currency"] in dict(CURRENCY_CHOICES) else None, entry_price=Decimal(s["price"]),
        benchmark=s["benchmark"], benchmark_entry=Decimal(s["benchmark_level"]) if s["benchmark_level"] else None)
    record.event_type, record.payload = ACCEPTED, {**s, "decision_id": decision.pk, "decided_at": timezone.now().isoformat()}
    record.save(update_fields=["event_type", "payload"])
    return {"decision_id": decision.pk, "review_on": decision.review_on.isoformat(),
            "message": f"Saved to your journal. ALFRED checks it against the price on {decision.review_on.isoformat()}. Nothing was bought or sold."}


@transaction.atomic
def reject(user, identity) -> dict:
    record = _pending(user, identity)
    record.event_type, record.payload = REJECTED, {**record.payload, "decided_at": timezone.now().isoformat()}
    record.save(update_fields=["event_type", "payload"])
    return {"message": "Rejected. ALFRED suggests this share again only when its rating or its results change."}


# ---- settlement and lesson ---------------------------------------------------------------------------------------

def settle_due(today=None) -> int:
    """Check every accepted desk call whose date has come against Yahoo's latest close, and write the lesson."""
    from apps.investments.models import ResearchDecision

    today, settled = today or timezone.localdate(), 0
    accepted = OperationalLog.objects.filter(module="investments", scope=SCOPE, event_type=ACCEPTED)
    owners = {row.payload.get("decision_id"): row.user_id for row in accepted.only("payload", "user_id")}
    for decision in ResearchDecision.objects.filter(pk__in=[key for key in owners if key], settled_on__isnull=True, review_on__lte=today):
        if owners[decision.pk] != decision.user_id:
            continue
        try:
            prices = research_data(decision.instrument)["prices"] or {}
            price = price_metrics(prices.get("close") or [], prices.get("timestamp") or [])
        except FETCH_ERRORS:
            continue
        bench = benchmark() if decision.benchmark_entry is not None else None
        if not price or date.fromisoformat(price["as_of"]) < decision.review_on:
            continue  # no close on or after the check date yet
        if decision.benchmark_entry is not None and (not bench or date.fromisoformat(bench["as_of"]) < decision.review_on):
            continue
        decision.settled_on = date.fromisoformat(price["as_of"])
        decision.exit_price = price["last_close"].quantize(Decimal("0.0001"))
        decision.benchmark_exit = Decimal(bench["level"]) if bench else None
        result = outcome(decision)
        verdict = {"supported": "The call held up.", "not_supported": "The call did not hold up.",
                   "not_judged": "A Keep or Wait call makes no direction to judge."}[result["direction"]]
        market = f" {decision.benchmark} moved {result['benchmark_return_percent']}%." if result["benchmark_return_percent"] is not None else ""
        decision.lesson = decision.lesson or (f"Checked by ALFRED with Yahoo's close of {price['as_of']}: the price moved "
                                              f"{result['return_percent']}%.{market} {verdict}")
        decision.save(update_fields=["settled_on", "exit_price", "benchmark_exit", "lesson", "updated_at"])
        settled += 1
    return settled


def run_scheduled(today=None) -> dict:
    """Daily job: research for every active account, then check the calls that are due."""
    from django.contrib.auth import get_user_model

    ran = failed = 0
    for user in get_user_model().objects.filter(is_active=True).order_by("id"):
        try:
            refresh(user, today)
            ran += 1
        except Exception as error:
            failed += 1
            logger.warning("Research desk failed for one account (%s)", type(error).__name__)
    return {"status": "completed", "processed": ran, "failed": failed, "settled": settle_due(today)}
