"""INVEST2-001 evidence packet: the case for and against one listed stock, from dated public data only.

Analyst roles follow TradingAgents (Apache-2.0, pin e8f5503e: fundamentals, market, risk, bull and bear researchers,
portfolio manager), written here as deterministic rules rather than LLM agents: every point cites a dated number, and
the screens are ALFRED's rules of thumb, not predictions. TradingAgents' point-in-time idea is kept: statements are dated
by their period end, and figures with no date are not used. Data: Yahoo's dated annual fundamentals and one year of
daily closes, through ALFRED's pinned public HTTPS boundary. No rating, price target or order is produced.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache
from django.utils import timezone

from alfred_ai.services import public_http

SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,19}$")
SOURCE = "https://finance.yahoo.com/quote/{}/financials/"
TYPES = ("TotalRevenue", "NetIncome", "OperatingIncome", "OperatingCashFlow", "FreeCashFlow", "TotalDebt",
         "StockholdersEquity", "CurrentAssets", "CurrentLiabilities", "DilutedAverageShares")
USER_AGENT = "AlfredAI/1.0 (verified-intelligence)"
CACHE_SECONDS = 6 * 3600
TENTH = Decimal("0.1")


def _pct(value):
    return None if value is None else (value * 100).quantize(TENTH, rounding=ROUND_HALF_UP)


def _ratio(top, bottom):
    return None if top is None or not bottom else top / bottom


def fetch_fundamentals(symbol: str) -> dict:
    """{type: [(period_end, Decimal value, currency)]} oldest first; undated or non-numeric rows are dropped."""
    now = int(timezone.now().timestamp())
    response = public_http.request("GET", f"https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}",
        params={"type": ",".join("annual" + name for name in TYPES), "period1": now - 6 * 366 * 86400, "period2": now},
        headers={"User-Agent": USER_AGENT})
    series = {}
    for item in (response.json().get("timeseries") or {}).get("result") or []:
        kind = ((item.get("meta") or {}).get("type") or [""])[0]
        if not kind.startswith("annual") or kind[6:] not in TYPES:
            continue
        rows = []
        for row in item.get(kind) or []:
            try:
                rows.append((datetime.strptime(row["asOfDate"], "%Y-%m-%d").date(), Decimal(str(row["reportedValue"]["raw"])),
                             str(row.get("currencyCode") or "").upper()[:3] or None))
            except (KeyError, TypeError, ValueError, ArithmeticError):
                continue
        if rows:
            series[kind[6:]] = sorted({row[0]: row for row in rows if row[1].is_finite()}.values())
    return series


def fetch_prices(symbol: str) -> dict:
    from apps.integrations.services.verified_intelligence import VerifiedIntelligenceService
    return VerifiedIntelligenceService()._fetch_yahoo_chart(symbol, range_value="1y", interval="1d")


def price_metrics(closes: list, stamps: list) -> dict:
    values = [float(value) for value in closes]
    if len(values) < 30:
        return {}
    returns = [math.log(b / a) for a, b in zip(values, values[1:])]
    mean = sum(returns) / len(returns)
    volatility = math.sqrt(sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)) * math.sqrt(252)
    peak, drawdown = values[0], 0.0
    for value in values:
        peak = max(peak, value)
        drawdown = min(drawdown, value / peak - 1)
    average = sum(values[-200:]) / len(values[-200:]) if len(values) >= 200 else None
    as_of = datetime.fromtimestamp(stamps[-1], dt_timezone.utc).date().isoformat()
    return {"last_close": Decimal(str(values[-1])), "as_of": as_of, "observations": len(values),
            "return_pct": _pct(Decimal(str(values[-1] / values[0] - 1))),
            "volatility_pct": _pct(Decimal(str(volatility))), "max_drawdown_pct": _pct(Decimal(str(drawdown))),
            "above_200_day_average": None if average is None else values[-1] > average}


def _common_period(series, *names, back=0):
    """The newest (or back-th newest) period end that every named series reports, so ratios never mix years."""
    dates = set.intersection(*({row[0] for row in series.get(name) or []} for name in names))
    dates = sorted(dates, reverse=True)
    return dates[back] if len(dates) > back else None


INDIAN_FIRST = {"NSE": 0, "Bombay": 1, "BSE": 1}
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9 &.'-]{1,59}$")


def find_symbols(name: str) -> list[dict]:
    """A company name to up to five listed symbols (Indian exchanges first), so a newcomer need not know the ticker.

    Only the typed company name goes to Yahoo's public search; anything that looks private is not sent.
    """
    from apps.ml_engine.services.web_lookup import PRIVATE_IN_QUESTION

    name = " ".join(str(name or "").split())
    if not NAME.fullmatch(name) or PRIVATE_IN_QUESTION.search(name):
        return []
    response = public_http.request("GET", "https://query2.finance.yahoo.com/v1/finance/search",
        params={"q": name, "quotesCount": 8, "newsCount": 0}, headers={"User-Agent": USER_AGENT})
    found = [{"symbol": str(q["symbol"]), "name": str(q.get("longname") or q.get("shortname") or "")[:120],
              "exchange": str(q.get("exchDisp") or "")[:40]}
             for q in response.json().get("quotes") or []
             if q.get("quoteType") in ("EQUITY", "ETF", "MUTUALFUND") and SYMBOL.fullmatch(str(q.get("symbol") or ""))]
    return sorted(found, key=lambda item: INDIAN_FIRST.get(item["exchange"], 2))[:5]


BEGINNER = {
    "not_enough": ("Not enough data", "ALFRED found too little dated data to judge this one.",
                   ["Try the company's NSE symbol (ending .NS) or look it up again later.",
                    "If you are new, a broad index fund needs far less research than one company."]),
    "positive": ("Looks healthy", "More good signs than warning signs in the company's numbers.",
                 ["Healthy numbers do not make a share cheap or safe; prices can still fall.",
                  "If you buy, start small, with money you will not need for at least five years.",
                  "Do not put a big part of your savings in one company; a broad index fund spreads the risk.",
                  "Write down your view in step 2 so ALFRED reminds you to check it."]),
    "mixed": ("Mixed", "The good signs and warning signs are about even.",
              ["A beginner would usually wait and learn more before buying.",
               "Ask the research team below for the case for, the case against and the risks.",
               "A broad index fund is a simpler way to own many companies at once."]),
    "caution": ("Be careful", "More warning signs than good signs in the company's numbers.",
                ["A beginner would usually stay away from this one for now.",
                 "Read the warning signs below; check again after the next annual results.",
                 "A broad index fund carries less single-company risk."]),
}


def beginner_view(bullish: list, bearish: list, portfolio: dict) -> dict:
    """Plain-language lean for someone new to markets, counted from the packet's own screens (a rule of thumb, not a forecast)."""
    good, bad = len(bullish), len(bearish)
    lean = "not_enough" if good + bad < 2 else "caution" if bad >= good + 2 else "positive" if good >= bad + 2 else "mixed"
    label, headline, steps = BEGINNER[lean]
    if portfolio.get("status") == "held" and any(p["metric"] == "portfolio_weight_pct" for p in bearish):
        steps = ["You already have a lot of your money in this one; adding more raises your risk."] + steps
    return {"lean": lean, "label": label, "headline": headline, "steps": steps, "good_signs": good, "warning_signs": bad,
            "note": "Counted from the signs below by fixed rules. Not a forecast or financial advice; nothing is bought or sold."}


def build_packet(symbol: str, fundamentals: dict, prices: dict, *, holding=None, portfolio_total=None) -> dict:
    point = lambda text, metric, value, as_of: {"point": text, "metric": metric, "value": value, "as_of": as_of}
    bullish, bearish, changes, missing, metrics = [], [], [], [], {}
    statement_currency = next((rows[-1][2] for rows in fundamentals.values() if rows and rows[-1][2]), None)

    def at(name, period):
        return next((row[1] for row in fundamentals.get(name) or [] if row[0] == period), None) if period else None

    latest, before = _common_period(fundamentals, "TotalRevenue"), _common_period(fundamentals, "TotalRevenue", back=1)
    if latest and before and at("TotalRevenue", before):
        growth = _pct((at("TotalRevenue", latest) - at("TotalRevenue", before)) / abs(at("TotalRevenue", before)))
        metrics["revenue_growth_pct"] = {"value": growth, "as_of": latest.isoformat()}
        (bullish if growth > 0 else bearish).append(point(f"Revenue {'grew' if growth > 0 else 'fell'} {abs(growth)}% in the latest year.", "revenue_growth_pct", growth, latest.isoformat()))
        changes.append("Annual revenue falls year on year." if growth > 0 else "Annual revenue returns to growth.")
    else:
        missing.append("Two years of dated revenue")
    period, previous = _common_period(fundamentals, "NetIncome", "TotalRevenue"), _common_period(fundamentals, "NetIncome", "TotalRevenue", back=1)
    margin, margin_before = _pct(_ratio(at("NetIncome", period), at("TotalRevenue", period))), _pct(_ratio(at("NetIncome", previous), at("TotalRevenue", previous)))
    if margin is not None:
        as_of = period.isoformat()
        metrics["net_margin_pct"] = {"value": margin, "as_of": as_of, "previous": margin_before}
        if margin_before is not None and margin < margin_before:
            bearish.append(point(f"Net margin slipped from {margin_before}% to {margin}%.", "net_margin_pct", margin, as_of))
        elif margin > 10:
            bullish.append(point(f"Net margin is {margin}%, above the 10% screen.", "net_margin_pct", margin, as_of))
        if margin < 0:
            bearish.append(point(f"The company lost money: net margin {margin}%.", "net_margin_pct", margin, as_of))
    else:
        missing.append("Dated net income and revenue")
    period = _common_period(fundamentals, "FreeCashFlow", "NetIncome")
    cash_quality = _ratio(at("FreeCashFlow", period), at("NetIncome", period))
    if cash_quality is not None and at("NetIncome", period) > 0:
        cash_quality = cash_quality.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        as_of = period.isoformat()
        metrics["free_cash_flow_to_profit"] = {"value": cash_quality, "as_of": as_of}
        if cash_quality >= Decimal("0.8"):
            bullish.append(point(f"Free cash flow is {cash_quality}x profit, so earnings are backed by cash.", "free_cash_flow_to_profit", cash_quality, as_of))
        elif cash_quality < Decimal("0.5"):
            bearish.append(point(f"Free cash flow is only {cash_quality}x profit.", "free_cash_flow_to_profit", cash_quality, as_of))
    else:
        missing.append("Dated free cash flow with positive profit")
    period = _common_period(fundamentals, "TotalDebt", "StockholdersEquity")
    leverage = _ratio(at("TotalDebt", period), at("StockholdersEquity", period))
    if leverage is not None and at("StockholdersEquity", period) > 0:
        leverage = leverage.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        as_of = period.isoformat()
        metrics["debt_to_equity"] = {"value": leverage, "as_of": as_of}
        if leverage < Decimal("0.5"):
            bullish.append(point(f"Debt is {leverage}x equity, a light load.", "debt_to_equity", leverage, as_of))
        elif leverage > 1:
            bearish.append(point(f"Debt is {leverage}x equity, above the 1x screen.", "debt_to_equity", leverage, as_of))
        changes.append("Debt rises above 1x equity." if leverage <= 1 else "Debt falls below 1x equity.")
    else:
        missing.append("Dated debt and positive shareholders' equity")
    period = _common_period(fundamentals, "CurrentAssets", "CurrentLiabilities")
    liquidity = _ratio(at("CurrentAssets", period), at("CurrentLiabilities", period))
    if liquidity is not None:
        liquidity = liquidity.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        as_of = period.isoformat()
        metrics["current_ratio"] = {"value": liquidity, "as_of": as_of}
        if liquidity < 1:
            bearish.append(point(f"Current assets cover only {liquidity}x the bills due within a year.", "current_ratio", liquidity, as_of))
        elif liquidity >= Decimal("1.5"):
            bullish.append(point(f"Current assets cover {liquidity}x the bills due within a year.", "current_ratio", liquidity, as_of))
    else:
        missing.append("Dated current assets and liabilities")

    price = price_metrics(prices.get("close") or [], prices.get("timestamp") or []) if prices else {}
    if price:
        metrics["price"] = price
        if price["volatility_pct"] > 40:
            bearish.append(point(f"The price swings widely: {price['volatility_pct']}% annualised volatility.", "volatility_pct", price["volatility_pct"], price["as_of"]))
        if price["max_drawdown_pct"] < -30:
            bearish.append(point(f"It fell {abs(price['max_drawdown_pct'])}% from a peak in the past year.", "max_drawdown_pct", price["max_drawdown_pct"], price["as_of"]))
        if price["above_200_day_average"] is not None:
            (bullish if price["above_200_day_average"] else bearish).append(point(
                f"The last close is {'above' if price['above_200_day_average'] else 'below'} its 200-day average.", "above_200_day_average", price["above_200_day_average"], price["as_of"]))
            changes.append("The price closes " + ("below" if price["above_200_day_average"] else "back above") + " its 200-day average.")
    else:
        missing.append("A year of daily prices")

    period = _common_period(fundamentals, "DilutedAverageShares", "NetIncome")
    shares, profit = at("DilutedAverageShares", period), at("NetIncome", period)
    price_currency = prices.get("currency") if prices else None
    if not (price and shares and profit):
        valuation = {"status": "unavailable", "reason": "Needs a recent price, diluted shares and profit."}
    elif not statement_currency or statement_currency != price_currency:
        valuation = {"status": "unavailable", "reason": f"The statements are in {statement_currency or 'an unrecorded currency'} and the price in "
                     f"{price_currency or 'an unrecorded currency'}; ALFRED does not convert currencies."}
    elif profit <= 0:
        valuation = {"status": "unavailable", "reason": "No price-to-earnings ratio while the company is losing money."}
    else:
        earnings = (price["last_close"] * shares / profit).quantize(TENTH, rounding=ROUND_HALF_UP)
        valuation = {"status": "estimated", "price_to_earnings": earnings, "earnings_yield_pct": _pct(profit / (price["last_close"] * shares)),
                     "as_of": price["as_of"], "basis": "Last close x diluted average shares / latest annual profit.",
                     "uncertainty": "One year of profit; cyclical or one-off profit can make this look cheap or dear."}

    if holding is None:
        portfolio = {"status": "not_selected", "detail": "Choose the matching holding to see its share of your portfolio."}
    elif not portfolio_total or holding.current_value is None:
        portfolio = {"status": "unknown", "detail": "No current value recorded for your holdings in this currency."}
    else:
        weight = _pct(Decimal(holding.current_value) / portfolio_total)
        portfolio = {"status": "held", "holding_id": holding.pk, "weight_pct": weight,
                     "detail": f"This holding is {weight}% of your holdings recorded in the same currency."}
        if weight > 20:
            bearish.append(point(f"It is already {weight}% of your holdings, above the 20% concentration screen.", "portfolio_weight_pct", weight, timezone.localdate().isoformat()))

    missing += ["News and management commentary", "Sector and competitor comparison", "Filing dates (statements are dated by period end)"]
    latest_period = max((rows[-1][0] for rows in fundamentals.values() if rows), default=None)
    review = (latest_period.replace(year=latest_period.year + 1) + timedelta(days=60)).isoformat() if latest_period else None
    return {"symbol": symbol, "retrieved_at": timezone.now().isoformat(), "source_url": SOURCE.format(symbol),
            "statement_currency": statement_currency, "price_currency": price_currency,
            "latest_period_end": latest_period.isoformat() if latest_period else None,
            "metrics": metrics, "bullish": bullish, "bearish": bearish, "valuation": valuation, "portfolio": portfolio,
            "thesis_changes": changes, "missing_evidence": missing, "beginner": beginner_view(bullish, bearish, portfolio),
            "options": ["Do nothing for now.", "Write down your view in step 2 and check it later.",
                        f"Look again after the next annual results{f', around {review}' if review else ''}."],
            "limits": ["Screens are rules of thumb, not forecasts; there is no rating or price target.",
                       "Yahoo data is not independently verified and may be revised.", "Nothing is bought, sold or changed."]}


def research_packet(symbol: str, *, holding=None, portfolio_total=None) -> dict:
    """Fetch (cached six hours) and build; raises ValueError for a bad symbol or when no dated data came back."""
    symbol = str(symbol or "").strip().upper()
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Enter an exchange symbol such as INFY.NS or TCS.BO.")
    key = f"invest2-packet:{symbol}"
    data = cache.get(key)
    if data is None:
        fundamentals = fetch_fundamentals(symbol)
        try:
            prices = fetch_prices(symbol)
        except ValueError:
            prices = {}
        if not fundamentals and not prices:
            raise ValueError("No dated data came back for that symbol.")
        data = {"fundamentals": fundamentals, "prices": prices}
        cache.set(key, data, CACHE_SECONDS)
    return build_packet(symbol, data["fundamentals"], data["prices"], holding=holding, portfolio_total=portfolio_total)
