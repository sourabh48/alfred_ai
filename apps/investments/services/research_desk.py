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
from decimal import ROUND_HALF_UP, Decimal
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
from .research_packet import SYMBOL, USER_AGENT, beginner_view, build_packet, price_metrics, research_data

logger = logging.getLogger(__name__)
SCOPE = "research_desk"
PENDING, ACCEPTED, REJECTED, SUPERSEDED = (f"research_suggestion_{state}" for state in ("pending", "accepted", "rejected", "superseded"))
SETTINGS, RUN, IDEAS, BACKTEST = "research_desk_settings", "research_desk_run", "research_desk_ideas", "research_desk_backtest"
NIFTY50_URL = "https://archives.nseindia.com/content/indices/ind_nifty50list.csv"
IDEA_DAYS, IDEA_LIMIT = 7, 5
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

# The owner's own answers; ALFRED never guesses them. Single shares can fall a fifth or more in a year.
LOSS = {"low": "A fall of more than a tenth would worry me", "medium": "I can sit through a fall of about a fifth",
        "high": "I can sit through a fall of a third or more"}
HORIZON = {"under_3": "Within 3 years", "3_to_5": "In 3 to 5 years", "over_5": "After 5 years or more"}
RESERVE_MONTHS, RUN_HOUR, SNOOZE_DAYS = 6, 13, 7


def desk_settings(user) -> dict:
    saved = _records(user).filter(event_type=SETTINGS).order_by("-created_at", "-id").first()
    current = {"watch": [{"symbol": symbol, "name": name} for symbol, name in DEFAULT_WATCH.items()], "include_holdings": False,
               "enabled": True, "discover": False, "profile": {"loss": None, "horizon": None}}
    if saved:
        current.update({key: saved.payload[key] for key in current if key in saved.payload})
        current["include_holdings"] = bool(current["include_holdings"])
        current["discover"] = current["discover"] is True  # opt-in: ideas read about 45 more companies each week
    return current


def save_settings(user, *, watch=None, include_holdings=None, enabled=None, profile=None, discover=None) -> dict:
    current = desk_settings(user)
    if watch is not None:
        current["watch"] = watch[:WATCH_LIMIT]
    if include_holdings is not None:
        current["include_holdings"] = include_holdings is True
    if enabled is not None:
        current["enabled"] = enabled is True
    if discover is not None:
        current["discover"] = discover is True
    if profile is not None:
        if not isinstance(profile, dict) or profile.get("loss") not in (*LOSS, None) or profile.get("horizon") not in (*HORIZON, None):
            raise ValueError("Choose one of the listed answers, or leave it blank.")
        current["profile"] = {"loss": profile.get("loss"), "horizon": profile.get("horizon")}
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
    """([(symbol, name, holding or None, why)], [owned shares without a symbol]): your shares (if allowed), recent searches, the watch list."""
    from apps.investments.models import Investment, ResearchSearch

    current, rows, unmatched = desk_settings(user), {}, []
    if current["include_holdings"]:
        for holding in Investment.objects.filter(user=user, asset_type="equity").order_by("-current_value", "id"):
            symbol = listed(holding.asset_name)
            if symbol and holding.asset_name.strip().upper() == symbol:  # the packet's own rule for a matching holding
                rows.setdefault(symbol, (symbol, symbol, holding, "You own it."))
            else:
                unmatched.append(holding.asset_name)
    for symbol in ResearchSearch.objects.filter(user=user).values_list("symbol", flat=True)[:10]:
        if listed(symbol):
            rows.setdefault(symbol, (symbol, symbol, None, "You looked it up recently."))
    for item in current["watch"]:
        rows.setdefault(item["symbol"], (item["symbol"], item["name"], None, "It is on your watch list."))
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


def rate(symbol: str, fundamentals: dict, prices: dict, *, holding=None, portfolio_total=None, today=None):
    """Analysts to portfolio manager on one day's data: (packet, tech, decision), or None when it cannot be rated.

    The live desk and the backtest both call this, so a past call is made by exactly the rules used today.
    """
    packet = build_packet(symbol, fundamentals, prices, holding=holding, portfolio_total=portfolio_total, today=today)
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
    return None if decision is None else (packet, tech, decision)


def levels(prices: dict, rating: str, held: bool, currency) -> dict | None:
    """Trader's example levels, grounded like TradingAgents' Trader in the average daily range (ATR) and recent support and
    resistance. A common rule of thumb shown for reference: not advice, not an order, never placed by ALFRED."""
    closes, highs, lows = prices.get("close") or [], prices.get("high") or [], prices.get("low") or []
    if len(closes) < 21 or len(highs) != len(closes) or len(lows) != len(closes):
        return None
    recent = list(zip(highs[-21:], lows[-21:], closes[-21:]))
    if any(high is None or low is None for high, low, _ in recent):
        return None
    ranges = [max(high - low, abs(high - before), abs(low - before)) for (high, low, _), (_, _, before) in zip(recent[-14:], recent[-15:-1])]
    cent = Decimal("0.01")
    atr, last = sum(ranges) / len(ranges), closes[-1]
    support, resistance = min(low for _, low, _ in recent[-20:]), max(high for high, _, _ in recent[-20:])
    stop = last - 2 * atr
    if stop <= 0:
        return None
    money = lambda value: f"{currency or ''} {value.quantize(cent, ROUND_HALF_UP):,}".strip()
    drop = ((stop / last - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
    if rating in ("buy", "overweight"):
        text = (f"Near the last close of {money(last)}. A common stop-loss rule, twice the average daily range (ATR {money(atr)}) below "
                f"the close, is {money(stop)} ({drop}%). Recent support {money(support)}, resistance {money(resistance)}.")
    elif held and rating in ("sell", "underweight"):
        text = f"If you keep it for now, a common rule is to sell if it closes below {money(stop)} ({drop}%), twice the average daily range below the last close."
    else:
        text = f"Over the last 20 sessions it traded between {money(support)} and {money(resistance)}."
    return {"atr14": str(atr.quantize(cent, ROUND_HALF_UP)), "stop": str(stop.quantize(cent, ROUND_HALF_UP)), "stop_pct": str(drop),
            "support": str(support.quantize(cent, ROUND_HALF_UP)), "resistance": str(resistance.quantize(cent, ROUND_HALF_UP)),
            "text": text + " An example from a common rule, not advice; ALFRED never places orders."}


def macro() -> list:
    """Macro analyst: India's latest annual inflation and GDP growth from the World Bank, as context only (no rating change)."""
    from apps.integrations.services.verified_intelligence import verified_intelligence

    lines = []
    for code, label in (("FP.CPI.TOTL.ZG", "inflation"), ("NY.GDP.MKTP.KD.ZG", "economic growth")):
        try:
            payload = verified_intelligence.world_bank_indicator(code, f"India {label}").payload or {}
        except Exception:  # offline or the World Bank is down: the call is made without macro context
            continue
        if payload.get("latest_value") is not None and payload.get("latest_year"):
            value, year = round(float(payload["latest_value"]), 1), payload["latest_year"]
            lines.append(f"India's {label} was {value}% in {year} (World Bank, yearly).")
    return lines


def analyse(symbol: str, name: str, *, holding=None, portfolio_total=None, bench=None, news=True) -> dict | None:
    data = research_data(symbol)
    prices = data["prices"] or {}
    rated = rate(symbol, data["fundamentals"], prices, holding=holding, portfolio_total=portfolio_total)
    if rated is None:
        return None
    packet, tech, decision = rated
    price = packet["metrics"]["price"]
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
            "news": headlines(name) if news and name != symbol else [],
            "levels": levels(prices, decision["rating"], holding is not None, packet["price_currency"]),
            "macro": macro() if indian else [],
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
    suggestion = {**suggestion, "fingerprint": _fingerprint(suggestion), "for_date": today.isoformat(), "first_seen": today.isoformat()}
    previous = _records(user).filter(payload__symbol=suggestion["symbol"]).exclude(event_type__in=(SETTINGS, RUN)) \
        .exclude(payload__fingerprint=suggestion["fingerprint"]).order_by("-created_at", "-id").first()
    if previous:  # what changed since the last call on this share
        old = previous.payload
        suggestion["changed_from"] = old["label"]
        suggestion["change"] = (f"Changed from {old['label']} ({old['for_date']}): good signs {len(old['good'])} to {len(suggestion['good'])}, "
                                f"warning signs {len(old['bad'])} to {len(suggestion['bad'])}"
                                + (", with newer company results." if old.get("latest_period_end") != suggestion["latest_period_end"] else "."))
    same = None
    for record in _records(user).select_for_update().filter(event_type=PENDING, payload__symbol=suggestion["symbol"]):
        if same is None and record.payload["fingerprint"] == suggestion["fingerprint"]:
            same = record
            kept = {key: record.payload[key] for key in ("id", "snoozed_until", "changed_from", "change", "first_seen") if key in record.payload}
            record.payload = {**suggestion, **kept}  # the same call with fresher numbers
            record.save(update_fields=["payload"])
        else:
            record.event_type = SUPERSEDED
            record.save(update_fields=["event_type"])
    answered = _records(user).filter(event_type__in=(ACCEPTED, REJECTED), payload__fingerprint=suggestion["fingerprint"]).exists()
    if same is None and not answered:  # an answered call comes back only when its rating or the company's results change
        _log(user, PENDING, f"Research desk suggests {suggestion['label']} for {suggestion['symbol']}; nothing changes until the owner decides.",
             {**suggestion, "id": uuid4().hex})


def refresh(user, today=None, *, resume=False) -> dict:
    """Research every share in the owner's list once. One share that fails never stops the rest.

    resume: the scheduled run skips shares already researched today, so a run cut short by a restart continues
    where it stopped instead of fetching everything again. Research now always reads every share.
    """
    from apps.investments.models import Investment

    today = today or timezone.localdate()
    rows, unmatched = universe(user)
    total = Investment.objects.filter(user=user).in_rupee_totals().aggregate(total=Sum("current_value"))["total"] or None
    bench, researched = benchmark(), 0
    skipped = [{"name": name, "reason": "Record this holding's name as its exchange symbol (for example INFY.NS) to include it."}
               for name in unmatched]
    done = set(_records(user).filter(payload__for_date=today.isoformat()).exclude(event_type__in=(SETTINGS, RUN, IDEAS, BACKTEST))
               .values_list("payload__symbol", flat=True)) if resume else set()
    for symbol, name, holding, why in rows:
        if symbol in done:
            researched += 1
            continue
        try:
            suggestion = analyse(symbol, name, holding=holding, portfolio_total=total, bench=bench)
        except FETCH_ERRORS as error:
            logger.warning("Research desk could not read one symbol (%s)", type(error).__name__)
            skipped.append({"name": name, "reason": "No dated data came back from Yahoo Finance."})
            continue
        if suggestion is None:
            skipped.append({"name": name, "reason": "Too little recent dated data to rate it."})
            continue
        _store(user, {**suggestion, "why": why}, today)
        researched += 1
    _records(user).filter(event_type=PENDING).exclude(payload__symbol__in=[row[0] for row in rows]).exclude(payload__idea=True) \
        .update(event_type=SUPERSEDED)
    run = {"researched": researched, "skipped": skipped, "at": timezone.now().isoformat()}
    _log(user, RUN, f"Research desk read {researched} share(s).", run)
    return run


def run_now(user, today=None, *, resume=False) -> dict:
    """Owner pressed Research now, or the daily job ran; one run at a time per owner."""
    lock = f"research-desk:running:{user.pk}"
    if not cache.add(lock, 1, RUN_LOCK_SECONDS):
        raise ValueError("Research is already running. Wait a minute.")
    try:
        return refresh(user, today, resume=resume)
    finally:
        cache.delete(lock)


def nifty50() -> list:
    """[(symbol, company)] in NIFTY 50 from NSE's public list, without banks, lenders and insurers (the screens misjudge them)."""
    import csv
    import io

    found = cache.get("research-desk:nifty50")
    if found is None:
        text = public_http.request("GET", NIFTY50_URL, headers={"User-Agent": USER_AGENT}, content_types=("text/csv",),
                                   max_bytes=50_000).content.decode("utf-8-sig")
        found = [(row["Symbol"].strip().upper() + ".NS", row["Company Name"].strip()[:120]) for row in csv.DictReader(io.StringIO(text))
                 if row.get("Series", "").strip() == "EQ" and row.get("Industry", "").strip() != "Financial Services"
                 and SYMBOL.fullmatch(row.get("Symbol", "").strip().upper() + ".NS")]
        if not found:
            raise ValueError("NSE's NIFTY 50 list came back empty.")
        cache.set("research-desk:nifty50", found, 7 * 86400)
    return found


def discover(user, today=None, *, force=False) -> dict | None:
    """Ideas beyond the owner's list: rate the NIFTY 50 companies not on it and keep up to five Buy calls to accept,
    reject or watch. Weekly unless forced; only public symbols go online. None when not due or switched off."""
    today = today or timezone.localdate()
    last = _records(user).filter(event_type=IDEAS).order_by("-created_at", "-id").first()
    if not force and (not desk_settings(user)["discover"] or (last and (today - timezone.localtime(last.created_at).date()).days < IDEA_DAYS)):
        return None
    try:
        companies = nifty50()
    except FETCH_ERRORS as error:
        raise ValueError("NSE's public NIFTY 50 list could not be read. Try again later.") from error
    own, found, checked = {row[0] for row in universe(user)[0]}, [], 0
    for symbol, name in companies:
        if symbol in own:
            continue
        try:
            suggestion = analyse(symbol, name, news=False)
        except FETCH_ERRORS:
            continue
        checked += 1
        if suggestion and suggestion["rating"] in ("buy", "overweight"):
            found.append(suggestion)
    found.sort(key=lambda s: (-s["score"], s["symbol"]))
    keep = found[:IDEA_LIMIT]
    bench = benchmark()
    for s in keep:
        _store(user, {**s, "news": headlines(s["name"]), "idea": True, "benchmark": "NIFTY 50" if bench else "",
                      "benchmark_level": bench["level"] if bench else None,
                      "why": "A NIFTY 50 company ALFRED found by itself; it is not on your list."}, today)
    _records(user).filter(event_type=PENDING, payload__idea=True).exclude(payload__symbol__in=[s["symbol"] for s in keep]) \
        .update(event_type=SUPERSEDED)
    run = {"checked": checked, "found": len(keep), "at": timezone.now().isoformat()}
    _log(user, IDEAS, f"Research desk checked {checked} NIFTY 50 companies for ideas.", run)
    return run


def backtest(user, today=None) -> dict:
    """Owner pressed Check past calls: replay the rules on past days for every share on the list (see research_backtest)."""
    from .research_backtest import replay_all

    lock = f"research-desk:backtest:{user.pk}"
    if not cache.add(lock, 1, 600):
        raise ValueError("The past-calls check is already running. Wait a few minutes.")
    try:
        result = replay_all([(symbol, name) for symbol, name, _, _ in universe(user)[0]], today or timezone.localdate())
    finally:
        cache.delete(lock)
    _log(user, BACKTEST, f"Research desk replayed {result['calls']} past call(s).", result, category="api")
    return result


def personal_fit(user, settings, today) -> dict:
    """Whether putting more money into one share suits the owner now. Fixed rules on local records; never an amount.
    Missing answers or records make it unknown, never a yes."""
    from apps.budgets.models import SavingsGoal
    from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline

    profile, missing, against = settings["profile"], [], []
    if not profile.get("loss"):
        missing.append("how big a fall you could sit through")
    if not profile.get("horizon"):
        missing.append("when you may need this money")
    baseline, months = resolve_canonical_financial_baseline(user), None
    if baseline.get("metric_states", {}).get("liquid_runway_months", {}).get("status") == "derived":
        try:
            exact = baseline["decimal_amounts"]
            months = (Decimal(exact["liquid_cash"]) / Decimal(exact["essential_monthly_outflow"])).quantize(Decimal("0.1"))
        except (KeyError, TypeError, ArithmeticError):
            months = None
    if months is None:
        missing.append("your current bank balances and monthly spending (add a recent statement)")
    elif months < RESERVE_MONTHS:
        against.append(f"Your bank balances cover about {months} months of essential spending and loan payments; "
                       f"keep at least {RESERVE_MONTHS} months aside before buying single shares.")
    if profile.get("loss") == "low":
        against.append("You said a fall of more than a tenth would worry you; single shares often fall a fifth or more in a year.")
    if profile.get("horizon") == "under_3":
        against.append("You may need this money within 3 years; a single share can stay down for longer than that.")
    goals = [goal.name for goal in SavingsGoal.objects.filter(user=user, target_date__isnull=False, target_date__gte=today,
                                                              target_date__lte=today + timedelta(days=3 * 365))
             if goal.saved_amount < goal.target_amount]
    if goals:
        against.append(f"{len(goals)} savings goal(s) due within 3 years still need money ({', '.join(goals[:2])}); fund them first.")
    if against:
        return {"state": "does_not_fit", "reasons": against, "missing": missing}
    if missing:
        return {"state": "unknown", "reasons": ["ALFRED needs " + "; ".join(missing) + " to check this."], "missing": missing}
    return {"state": "fits", "missing": [], "reasons": [
        f"Your bank balances cover about {months} months of essentials, no savings goal is due within 3 years, "
        f"and you said: {LOSS[profile['loss']].lower()}; money needed {HORIZON[profile['horizon']].lower()}."]}


CHANGE_IF = {
    "buy": "A close below the 200-day average, or the next yearly results showing lower revenue or profit.",
    "overweight": "The risk flags clearing would make it a Buy; a close below the 200-day average or weaker results would make it Wait.",
    "hold": "Two more good signs and the price above both averages would make it a candidate; more warning signs would make it Avoid.",
    "underweight": "Revenue and profit growing again with the price back above its 200-day average.",
    "sell": "Revenue and profit growing again with the price back above its 200-day average.",
}


def _status(s):
    if s["rating"] in ("buy", "overweight"):
        return "Investment candidate"
    if s["rating"] == "hold":
        return "Watch"
    return "Review" if s["held"] else "Avoid"


def _open(user, today):
    """Pending calls the owner has not put off."""
    rows = [record.payload for record in _records(user).filter(event_type=PENDING).order_by("-created_at", "-id")[:UNIVERSE_LIMIT]]
    return [s for s in rows if s.get("snoozed_until", "") <= today.isoformat()], [s for s in rows if s.get("snoozed_until", "") > today.isoformat()]


def next_run(settings, last, now=None) -> str | None:
    """When the daily job next runs (13:00 local), or None while paused. A missed run is caught up at the next start."""
    if not settings["enabled"]:
        return None
    now = timezone.localtime(now)
    slot = now.replace(hour=RUN_HOUR, minute=0, second=0, microsecond=0)
    ran_today = last is not None and timezone.localtime(last.created_at).date() == now.date()
    if ran_today:
        slot += timedelta(days=1)
    elif now >= slot:
        return now.isoformat()  # due now: the background worker catches it up
    return slot.isoformat()


def notices(user, today):
    """New or changed calls that ask for the owner's decision, for the Home review list. Routine Wait calls stay quiet."""
    from apps.ml_engine.services.task_bots import _item

    open_calls, _ = _open(user, today)
    buys = [s for s in open_calls if s["rating"] in ("buy", "overweight")]
    not_now = bool(buys) and personal_fit(user, desk_settings(user), today)["state"] == "does_not_fit"
    return [_item(f"desk:{s['fingerprint']}", f"{s['symbol']}: {s['label']}" + (f" (was {s['changed_from']})" if s.get("changed_from") else " (new)")
                  + (", but not for you yet" if not_now and s in buys else ""),
                  f"{s.get('why', '')} {s['summary']} Accept or reject it on Investments; ALFRED never buys or sells.",
                  "/investments/#researchDeskSection")
            for s in open_calls if s["rating"] != "hold" or s.get("changed_from")]


@transaction.atomic
def later(user, identity, today=None) -> dict:
    """Put a call off for a week; it comes back sooner only if the evidence changes."""
    today, record = today or timezone.localdate(), _pending(user, identity)
    until = (today + timedelta(days=SNOOZE_DAYS)).isoformat()
    record.payload = {**record.payload, "snoozed_until": until}
    record.save(update_fields=["payload"])
    return {"message": f"Put off until {until}. It comes back sooner if its evidence changes."}


def desk(user, today=None) -> dict:
    """What the page shows; reading it fetches nothing online."""
    today, settings = today or timezone.localdate(), desk_settings(user)
    last = _records(user).filter(event_type=RUN).order_by("-created_at", "-id").first()
    suggestions, snoozed = _open(user, today)
    fit = None
    for s in suggestions:
        s["status"] = _status(s)
        s["against"] = (s["risks"] or [item["point"] for item in s["bad"]] or
                        ["No warning sign in the numbers ALFRED reads; that does not mean there is no risk."])[0]
        s["change_if"] = CHANGE_IF[s["rating"]]
        if s["rating"] in ("buy", "overweight"):
            fit = fit or personal_fit(user, settings, today)
            s["fit"] = fit
            if fit["state"] == "does_not_fit":
                s["status"] = "Not for you yet"  # the personal answer outranks a general research call for someone deciding alone
        else:
            s["fit"] = {"state": "not_needed", "reasons": [], "missing": []}
    suggestions.sort(key=lambda s: (s["rating"] == "hold", -abs(s["score"]), s["symbol"]))
    answered = [{"symbol": r.payload["symbol"], "label": r.payload["label"], "state": "accepted" if r.event_type == ACCEPTED else "rejected",
                 "decided_at": r.payload.get("decided_at")}
                for r in _records(user).filter(event_type__in=(ACCEPTED, REJECTED)).order_by("-created_at", "-id")[:10]]
    ideas = _records(user).filter(event_type=IDEAS).order_by("-created_at", "-id").first()
    tested = _records(user).filter(event_type=BACKTEST).order_by("-created_at", "-id").first()
    return {"settings": settings, "watch_limit": WATCH_LIMIT, "answered": answered, "snoozed": len(snoozed),
            "loss_choices": LOSS, "horizon_choices": HORIZON, "next_run": next_run(settings, last),
            "last_run": {key: last.payload[key] for key in ("researched", "skipped", "at")} if last else None, "suggestions": suggestions,
            "last_ideas": ideas.payload if ideas else None, "backtest": tested.payload if tested else None}


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
        if not desk_settings(user)["enabled"]:
            continue  # paused by the owner
        try:
            run_now(user, today, resume=True)
            ran += 1
        except Exception as error:
            failed += 1
            logger.warning("Research desk failed for one account (%s)", type(error).__name__)
        try:
            discover(user, today)  # weekly; off when the owner switches ideas off
        except Exception as error:
            logger.warning("Research desk ideas failed for one account (%s)", type(error).__name__)
    return {"status": "completed", "processed": ran, "failed": failed, "settled": settle_due(today)}
