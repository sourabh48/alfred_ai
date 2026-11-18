"""Paper trader: the research desk's simulated portfolio (owner request 2026-11-18).

When the owner accepts a call and ticks "also paper trade it", ALFRED's trader places a pretend order in a separate
paper account the owner opened with pretend money. Nothing here touches real holdings, a broker or any bank record:
paper trades live only in the desk's own log records. Fills are at the call's last daily close, with no fees or
taxes, in rupees only, so the result is a rough test of the calls, not a forecast of real returns.
"""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

ACCOUNT, TRADE = "research_paper_account", "research_paper_trade"
CURRENCY, CENT = "INR", Decimal("0.01")
MAX_CASH = Decimal("1000000000")  # ten thousand lakh (100 crore) of pretend money is plenty
# rating: (side, share of paper cash for a buy, or share of the paper position for a sale)
ORDER = {"buy": ("buy", Decimal("0.10")), "overweight": ("buy", Decimal("0.05")),
         "underweight": ("sell", Decimal("0.5")), "sell": ("sell", Decimal("1"))}


def _records(user):
    from .research_desk import _records as desk_records
    return desk_records(user)


def _money(value) -> Decimal:
    return Decimal(value).quantize(CENT, ROUND_HALF_UP)


def account(user, *, lock=False):
    rows = _records(user).filter(event_type=ACCOUNT)
    return (rows.select_for_update() if lock else rows).order_by("-created_at", "-id").first()


def open_account(user, cash) -> dict:
    """Start (or start again) with an amount of pretend money the owner chooses. Old paper trades are kept but closed."""
    from .research_desk import _log

    try:
        amount = _money(str(cash).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        amount = None
    if amount is None or not amount.is_finite() or not Decimal("1000") <= amount <= MAX_CASH:
        raise ValueError("Enter pretend money between 1,000 and 100 crore rupees.")
    with transaction.atomic():
        _records(user).filter(event_type=ACCOUNT).update(event_type=ACCOUNT + "_closed")
        _records(user).filter(event_type=TRADE).update(event_type=TRADE + "_closed")
        _log(user, ACCOUNT, "Paper trading account opened with pretend money.",
             {"start_cash": str(amount), "cash": str(amount), "currency": CURRENCY, "opened_at": timezone.now().isoformat()},
             category="api")
    return portfolio(user)


def _price(value) -> Decimal | None:
    """A usable last close: a finite amount above zero, else None (a bad quote never fills or values a paper trade)."""
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return price if price.is_finite() and price > 0 else None


def _positions(user) -> dict:
    held = {}
    for trade in _records(user).filter(event_type=TRADE).order_by("created_at", "id"):
        t = trade.payload
        quantity, cost = held.get(t["symbol"], (0, Decimal(0)))
        if t["side"] == "buy":
            held[t["symbol"]] = (quantity + t["quantity"], cost + Decimal(t["value"]))
        else:  # average cost leaves with the shares sold
            held[t["symbol"]] = (quantity - t["quantity"], cost - (cost / quantity * t["quantity"] if quantity else Decimal(0)))
    return {symbol: pair for symbol, pair in held.items() if pair[0] > 0}


def proposal(user, suggestion, book=None) -> dict | None:
    """What the paper trader would do if the owner accepts this call, or None (no account, no order, other currency)."""
    book = book or account(user)
    if book is None or suggestion.get("rating") not in ORDER:
        return None
    if suggestion.get("currency") != CURRENCY:
        return {"possible": False, "text": "Paper trading uses rupees; this share is priced in another currency."}
    side, share = ORDER[suggestion["rating"]]
    price = _price(suggestion.get("price"))
    if price is None:
        return {"possible": False, "text": "This call has no usable last close, so the paper trader waits for the next daily research."}
    if side == "buy":
        quantity = int((Decimal(book.payload["cash"]) * share / price).to_integral_value(ROUND_DOWN))
        if quantity < 1:
            return {"possible": False, "text": "Not enough paper cash for one share."}
    else:
        owned = _positions(user).get(suggestion["symbol"], (0, 0))[0]
        quantity = max(1, int((owned * share).to_integral_value(ROUND_DOWN))) if owned else 0
        if not quantity:
            return None  # nothing to sell on paper
    value = _money(price * quantity)
    verb = "buy" if side == "buy" else "sell"
    return {"possible": True, "side": side, "quantity": quantity, "price": str(price), "value": str(value),
            "text": f"Paper trader would {verb} {quantity} share(s) at the last close, about {value} pretend rupees."}


def place(user, suggestion, today) -> dict:
    """Called inside accept(): the owner approved this call and asked for the paper trade too."""
    from .research_desk import _log

    book = account(user, lock=True)
    order = proposal(user, suggestion, book)
    if book is None:
        raise ValueError("Open a paper trading account first, with the pretend money you want to start with.")
    if not order or not order["possible"]:
        raise ValueError((order or {}).get("text") or "There is nothing to paper trade for this call.")
    cash, value = Decimal(book.payload["cash"]), Decimal(order["value"])
    cash = cash - value if order["side"] == "buy" else cash + value
    if cash < 0:
        raise ValueError("Not enough paper cash for this paper trade.")
    # Compare-and-set: the write lands only if the account is still open with the cash this order was priced on, so a
    # reset or a second order in between can never attach this trade to another account or spend the same cash twice.
    if not _records(user).filter(pk=book.pk, event_type=ACCOUNT, payload__cash=book.payload["cash"]).update(
            payload={**book.payload, "cash": str(_money(cash))}):
        raise ValueError("The paper account changed while this order was placed. Nothing was traded; try again.")
    trade = {key: order[key] for key in ("side", "quantity", "price", "value")} | {
        "symbol": suggestion["symbol"], "name": suggestion["name"], "rating": suggestion["rating"], "on": today.isoformat(),
        "price_as_of": suggestion["price_as_of"], "suggestion_id": suggestion["id"]}
    _log(user, TRADE, f"Paper trade: {order['side']} {order['quantity']} {suggestion['symbol']} (pretend money).", trade, category="api")
    return trade


def portfolio(user) -> dict | None:
    """Paper cash, positions valued at the desk's latest daily close for each share, and the gain or loss so far."""
    from .research_desk import ACCEPTED, PENDING, SUPERSEDED

    book = account(user)
    if book is None:
        return None
    latest = {}  # symbol -> (date, price): the latest-dated usable rupee close, whatever order the records were made in
    for row in _records(user).filter(event_type__in=(PENDING, ACCEPTED, SUPERSEDED)).order_by("created_at", "id"):
        p = row.payload
        price, as_of = _price(p.get("price")), str(p.get("price_as_of") or "")
        if p.get("symbol") and price is not None and p.get("currency") == CURRENCY and as_of >= latest.get(p["symbol"], ("", None))[0]:
            latest[p["symbol"]] = (as_of, price)
    rows, value, at_cost = [], Decimal(book.payload["cash"]), []
    for symbol, (quantity, cost) in sorted(_positions(user).items()):
        as_of, price = latest.get(symbol, (None, None))
        worth = _money(price * quantity) if price is not None else None
        value += worth if worth is not None else cost
        if worth is None:
            at_cost.append(symbol)
        rows.append({"symbol": symbol, "quantity": quantity, "cost": str(_money(cost)), "value": None if worth is None else str(worth),
                     "price_as_of": as_of})
    start = Decimal(book.payload["start_cash"])
    trades = [r.payload for r in _records(user).filter(event_type=TRADE).order_by("-created_at", "-id")[:20]]
    return {"currency": CURRENCY, "start_cash": str(start), "cash": book.payload["cash"], "value": str(_money(value)),
            "change_pct": str(((value / start - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)), "positions": rows,
            "trades": trades, "opened_at": book.payload["opened_at"],
            "limits": ["Pretend money only: nothing was bought or sold, and your real holdings are untouched.",
                       "Fills at the last daily close, with no brokerage, taxes or slippage, so real results would be lower.",
                       "Values use each share's latest close from the daily research."]
                      + ([f"No usable close for {', '.join(at_cost)}, so it is counted at what it cost."] if at_cost else [])}
