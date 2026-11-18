"""'Can I afford X?' answered from the canonical baseline every page uses, with no model arithmetic.

The local model's money sums are not reliable, so this question gets a fixed, checkable answer instead.
Cash counts rupee accounts only (the FIN-15 rule baseline_source applies, with the owner's home currency for
unlabelled rows); accounts in other currencies are named, not added. Otherwise the owner is told what to record. Nothing is bought, moved or saved.
"""
import re
from decimal import Decimal, ROUND_HALF_UP

from alfred_ai.services.currency import rupee_text

ASK = re.compile(r"\bafford\b|\bcan i (?:buy|spend|pay for)\b|\bshould i (?:buy|spend)\b", re.I)
AMOUNT = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(k|thousand|lakhs?|lacs?)?\b", re.I)
SCALE = {"k": 1000, "thousand": 1000, "lakh": 100000, "lakhs": 100000, "lac": 100000, "lacs": 100000}
RESERVE_MONTHS = 6


def asked_amount(query):
    """The price in an affordability question, or None when it is not one."""
    if not ASK.search(query):
        return None
    for number, unit in AMOUNT.findall(query):
        amount = Decimal(number.replace(",", "")) * SCALE.get(unit.lower(), 1)
        if amount > 0:
            return amount
    return None


def affordability_answer(user, query):
    amount = asked_amount(query)
    if amount is None:
        return None
    from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
    from .canonical_evidence import baseline_source

    source = baseline_source(user) | {"ref": "canonical-finance", "classification": "canonical_financial_baseline"}
    cash = source["data"]["amounts"]["liquid_cash"]["amount"]
    reply = dict(provider="local_evidence", classification="owner_recorded_fact", financial_authority=False,
                 grounding="canonical_affordability", sources=[source], narrative_withheld=False, context_omitted=0,
                 memory_retrieval_available=None)
    if cash is None:
        from alfred_ai.services.exchange_rates import home_currency
        fix = ("Set your country in Settings so ALFRED knows which currency an unlabelled balance is in, "
               "or open Spending, go to Bank accounts and set each account's currency" if home_currency(user)[0] is None else
               "Open Spending, go to Bank accounts, check each balance and set its currency to INR")
        return reply | {"answer": "ALFRED cannot answer this yet, because it does not know your bank balance in rupees. "
                        f"{fix}, then ask again."}
    cash = Decimal(str(cash))
    base = resolve_canonical_financial_baseline(user)
    essentials = Decimal(str(base["decimal_amounts"].get("essential_monthly_outflow") or 0))
    known = (base["metric_states"].get("essential_monthly_outflow") or {}).get("status", "unavailable") != "unavailable"
    lines = [f"You hold {rupee_text(cash)} in your bank accounts [canonical-finance]."]
    abroad = source["data"].get("other_currencies", {}).get("cash") or []
    if abroad:
        lines.append(f"You also hold {', '.join(row['currency'] + ' ' + row['amount'] for row in abroad)} in other currencies; "
                     "that is not counted here, because exchange rates change and ALFRED does not convert your records.")
    if amount > cash:
        lines.append(f"{rupee_text(amount)} is more than that, so paying it now would need a loan or card debt.")
    elif known and essentials > 0:
        months = lambda value: (value / essentials).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        left = cash - amount
        lines.append(f"Your usual essential costs (rent, EMIs and day-to-day spending) are about {rupee_text(essentials)} a month, "
                     f"so that covers about {months(cash)} months.")
        lines.append(f"After paying {rupee_text(amount)} you would have {rupee_text(left)}, about {months(left)} months.")
        cushion = essentials * RESERVE_MONTHS
        lines.append(f"A safe cushion is {RESERVE_MONTHS} months ({rupee_text(cushion)}). " + (
            "You would still have that, so this fits." if left >= cushion else
            "You would be below it, so it is safer to wait or save up for it first."))
    else:
        lines.append(f"After paying {rupee_text(amount)} you would have {rupee_text(cash - amount)}. "
                     "Add a month of spending so ALFRED can tell how long that lasts.")
    lines.append("This is a guide from your own records; the choice is yours, and ALFRED buys nothing.")
    return reply | {"answer": " ".join(lines)}
