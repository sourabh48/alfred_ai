"""Capital gains tax for a resident individual, tax year 2026-27 (Income-tax Act, 2025).

Read by hand on 2026-11-25 from the gazetted Income-tax Act, 2025 and Finance Act, 2026:
s.2(101) holding periods (12 months for listed securities, equity-oriented fund and UTI units and
zero-coupon bonds; 24 months otherwise), s.76 (specified mutual funds bought on/after 1 April 2023,
market-linked debentures and unlisted bonds/debentures from 23 July 2024: always short-term, slab
rates), s.196 (short-term equity with STT, 20%), s.197 (other long-term, 12.5%; land or building bought
before 23 July 2024 may use 20% on indexed gains instead), s.198 (long-term equity with STT, 12.5% above
INR 1,25,000), s.108(2) (short-term losses against any capital gain, long-term losses only against
long-term gains), s.156 (rebates; new-regime rebate only against slab tax, s.198(7) none against s.198
tax) and Finance Act, 2026 Part I-B Paragraph F / Table Sl. 10 (surcharge on these gains at most 15%;
25%/37% bands tested on income excluding them). Amounts stay Decimal; this is a planning estimate.
"""
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, localcontext
from itertools import permutations

from .tax_policy import (
    D, FINANCE_ACT_2026_SOURCE, INCOME_TAX_ACT_2025_SOURCE, PAISE, ZERO, TaxPolicyError,
    _slab_tax, amount, get_policy, slabs_for,
)

TAX_YEAR = "2026-27"
YEAR_START, YEAR_END = date(2026, 4, 1), date(2027, 3, 31)
POLICY_VERSION = "india-capital-gains-2026-27-v1"
EQUITY_EXEMPTION = D("125000")
RATES = {"s196": D("0.20"), "s197": D("0.125"), "s198": D("0.125")}
INDEXED_RATE = D("0.20")
LAND_OPTION_CUTOFF = date(2024, 7, 23)
SPECIFIED_FUND_CUTOFF = date(2023, 4, 1)
ASSET_TYPES = {
    "listed_equity": "Listed shares, equity-oriented fund or business trust units",
    "listed_other": "Other listed securities, UTI units or zero-coupon bonds",
    "debt_fund": "Debt fund bought on or after 1 April 2023",
    "unlisted_bond": "Market-linked debenture, or unlisted bond or debenture",
    "land_building": "Land or building",
    "other": "Other assets (gold, unlisted shares, other funds)",
}
MAX_SALES = 200
SHORT_BUCKETS, LONG_BUCKETS = ("slab", "s196"), ("s197", "s198")
BUCKET_LABELS = {
    "slab": "Short-term gains taxed at slab rates", "s196": "Short-term equity gains (section 196, 20%)",
    "s197": "Long-term gains (section 197, 12.5%)", "s198": "Long-term equity gains (section 198, 12.5% above INR 1,25,000)",
}


@dataclass(frozen=True)
class Sale:
    asset_type: str
    bought: date
    sold: date
    cost: object
    sale_value: object
    stt_paid: bool
    indexed_cost: object
    bucket: str
    long_term: bool

    @property
    def gain(self):
        return self.sale_value - self.cost


def _date(value, field):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise TaxPolicyError(f"{field} must be a date (YYYY-MM-DD).") from None


def _held_longer_than(bought, sold, months):
    total = bought.month - 1 + months
    year, month = bought.year + total // 12, total % 12 + 1
    day = min(bought.day, [31, 29 if year % 4 == 0 and (year % 100 or year % 400 == 0) else 28,
                           31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return sold > date(year, month, day)


def classify(raw):
    if not isinstance(raw, dict):
        raise TaxPolicyError("Each sale must be an object.")
    asset_type = raw.get("asset_type")
    if asset_type not in ASSET_TYPES:
        raise TaxPolicyError("Choose a supported asset type for each sale.")
    bought, sold = _date(raw.get("bought"), "Purchase date"), _date(raw.get("sold"), "Sale date")
    if bought > sold:
        raise TaxPolicyError("A sale date cannot be before its purchase date.")
    if not YEAR_START <= sold <= YEAR_END:
        raise TaxPolicyError("Only sales made in tax year 2026-27 (1 April 2026 to 31 March 2027) are supported.")
    stt_paid = raw.get("stt_paid", False)
    if not isinstance(stt_paid, bool):
        raise TaxPolicyError("Say whether securities transaction tax was paid (true or false).")
    cost, sale_value = amount(raw.get("cost"), "Cost"), amount(raw.get("sale_value"), "Sale value")
    indexed = raw.get("indexed_cost")
    indexed = amount(indexed, "Indexed cost") if indexed not in (None, "") else None
    if indexed is not None and not (asset_type == "land_building" and bought < LAND_OPTION_CUTOFF):
        raise TaxPolicyError("Indexed cost applies only to land or building bought before 23 July 2024.")
    if asset_type == "debt_fund" and bought < SPECIFIED_FUND_CUTOFF:
        raise TaxPolicyError("Debt funds bought before 1 April 2023 follow the usual rules; choose 'Other assets'.")
    if asset_type in ("debt_fund", "unlisted_bond"):
        bucket, long_term = "slab", False
    else:
        months = 12 if asset_type in ("listed_equity", "listed_other") else 24
        long_term = _held_longer_than(bought, sold, months)
        equity = asset_type == "listed_equity" and stt_paid
        bucket = ("s198" if equity else "s197") if long_term else ("s196" if equity else "slab")
    return Sale(asset_type, bought, sold, cost, sale_value, stt_paid, indexed, bucket, long_term)


def _net_buckets(sales, short_order, long_order):
    """Net each bucket, then set off remaining losses in the given orders (s.108(2))."""
    net = {key: sum((s.gain for s in sales if s.bucket == key), ZERO) for key in BUCKET_LABELS}
    setoffs = []
    # Long-term losses first: they can only use long-term gains, short-term losses can use any.
    for loss_buckets, order in ((LONG_BUCKETS, long_order), (SHORT_BUCKETS, short_order)):
        for source in loss_buckets:
            for target in order:
                if net[source] >= 0:
                    break
                if target != source and net[target] > 0:
                    used = min(-net[source], net[target])
                    net[source] += used
                    net[target] -= used
                    setoffs.append({"loss_from": source, "set_off_against": target, "amount": used})
    unused = {"short_term": -sum(min(net[k], ZERO) for k in SHORT_BUCKETS),
              "long_term": -sum(min(net[k], ZERO) for k in LONG_BUCKETS)}
    return {k: max(v, ZERO) for k, v in net.items()}, setoffs, unused


def _land_relief(sales, setoffs):
    """s.197(3): ignore the excess over 20% on indexed gains, per land/building sold (no losses involved)."""
    eligible = [s for s in sales if s.bucket == "s197" and s.asset_type == "land_building" and s.indexed_cost is not None]
    if not eligible:
        return ZERO, False
    if setoffs or any(s.gain < 0 for s in sales if s.bucket == "s197"):
        return ZERO, True  # shortcut: the indexed option with loss set-off needs a per-asset recomputation; shown for review
    relief = sum((max(ZERO, s.gain * RATES["s197"] - max(ZERO, s.sale_value - s.indexed_cost) * INDEXED_RATE)
                  for s in eligible), ZERO)
    return relief, False


def _surcharge_rates(total, excluding_gains, regime):
    rate = D("0.10") if total > 5000000 else ZERO
    rate = D("0.15") if total > 10000000 else rate
    if excluding_gains > 20000000:
        rate = D("0.25")
    if regime == "old" and excluding_gains > 50000000:
        rate = D("0.37")
    return rate, min(rate, D("0.15"))


def _tax(net, *, ordinary_taxable, regime, resident, age_group, land_relief):
    policy = get_policy(regime, financial_year=TAX_YEAR)
    slabs = slabs_for(policy, resident=resident, age_group=age_group)
    ordinary = ordinary_taxable + net["slab"]
    special_gains = net["s196"] + net["s197"] + net["s198"]
    total = ordinary + special_gains
    exempt = D(slabs[0][0]) if slabs[0][1] == 0 else ZERO
    shortfall = max(ZERO, exempt - ordinary) if resident else ZERO
    taxable = {"s196": net["s196"], "s197": net["s197"], "s198": max(ZERO, net["s198"] - EQUITY_EXEMPTION)}
    shortfall_used = {}
    for key in ("s196", "s197", "s198"):  # highest rate first
        used = min(shortfall, taxable[key])
        taxable[key] -= used
        shortfall -= used
        shortfall_used[key] = used
    slab_tax, slab_breakdown = _slab_tax(ordinary, slabs)
    special = {key: taxable[key] * RATES[key] for key in taxable}
    special["s197"] = max(ZERO, special["s197"] - land_relief)
    rebate_base = slab_tax + special["s196"] + special["s197"]  # s.198(7): never against s.198 tax
    rebate = ZERO
    if resident and regime == "old" and total <= policy.rebate_threshold:
        rebate = min(rebate_base, policy.rebate_limit)
    elif resident and regime == "new":
        if total <= policy.rebate_threshold:
            rebate = min(rebate_base, policy.rebate_limit)
        else:
            rebate = max(ZERO, rebate_base - (total - policy.rebate_threshold))
        rebate = min(rebate, slab_tax)  # s.156(3): only against tax at the s.202(1) rates
    ordinary_after = max(ZERO, slab_tax - rebate)
    left = rebate - (slab_tax - ordinary_after)
    gains_after = {}
    for key in ("s196", "s197", "s198"):
        cut = min(left, special[key]) if key != "s198" else ZERO
        gains_after[key] = special[key] - cut
        left -= cut
    gains_tax = sum(gains_after.values(), ZERO)
    ordinary_rate, gains_rate = _surcharge_rates(total, total - special_gains, regime)
    surcharge = ordinary_after * ordinary_rate + gains_tax * gains_rate
    before_cess = ordinary_after + gains_tax + surcharge
    cess = (before_cess * policy.cess_rate).quantize(PAISE, rounding=ROUND_HALF_UP)
    return {
        "regime": regime, "total_income": total, "ordinary_taxable_income": ordinary,
        "slab_tax": slab_tax, "slab_breakdown": slab_breakdown,
        "basic_exemption_used_against_gains": shortfall_used,
        "taxable_special_gains": taxable, "special_rate_tax": special, "land_indexation_relief": land_relief,
        "rebate": rebate, "surcharge_rate_ordinary": ordinary_rate, "surcharge_rate_gains": gains_rate,
        "surcharge": surcharge, "cess": cess,
        "final_tax": (before_cess + cess).quantize(PAISE, rounding=ROUND_HALF_UP),
        "surcharge_marginal_relief": "not applied when capital gains are present",
    }


def calculate_capital_gains_tax(sales, *, annual_income=0, deductions_total=0, regime="new", income_type="salary",
                                resident=True, age_group="under_60"):
    """Total tax for ordinary income plus the tax year's capital gains, choosing the cheapest legal set-off order."""
    if regime not in ("old", "new") or income_type not in ("salary", "ordinary"):
        raise TaxPolicyError("Choose the old or new regime and salary or ordinary income.")
    if not isinstance(resident, bool) or age_group not in ("under_60", "60_to_79", "80_plus"):
        raise TaxPolicyError("Provide a valid residency flag and age group.")
    if not isinstance(sales, list) or not 1 <= len(sales) <= MAX_SALES:
        raise TaxPolicyError(f"Enter between 1 and {MAX_SALES} sales.")
    parsed = [classify(raw) for raw in sales]
    policy = get_policy(regime, financial_year=TAX_YEAR)
    income, deductions = amount(annual_income, "Annual income"), amount(deductions_total, "Deductions")
    with localcontext() as context:
        context.prec = 40
        standard = min(income, policy.standard_deduction) if income_type == "salary" else ZERO
        ordinary_taxable = max(ZERO, income - standard - deductions)
        best = None
        for short_order in permutations(BUCKET_LABELS):
            for long_order in permutations(LONG_BUCKETS):
                net, setoffs, unused = _net_buckets(parsed, short_order, long_order)
                relief, review = _land_relief(parsed, setoffs)
                result = _tax(net, ordinary_taxable=ordinary_taxable, regime=regime, resident=resident,
                              age_group=age_group, land_relief=relief)
                if best is None or result["final_tax"] < best[0]["final_tax"]:
                    best = (result, net, setoffs, unused, review)
    result, net, setoffs, unused, review = best
    review = review or bool(result["land_indexation_relief"] and result["basic_exemption_used_against_gains"]["s197"])
    return {
        **result,
        "tax_year": TAX_YEAR, "calculation_status": "ESTIMATED", "standard_deduction": standard,
        "sales": [{"asset_type": s.asset_type, "bought": s.bought.isoformat(), "sold": s.sold.isoformat(),
                   "gain": s.gain, "term": "long" if s.long_term else "short", "bucket": s.bucket,
                   "bucket_label": BUCKET_LABELS[s.bucket]} for s in parsed],
        "net_gains": net, "loss_setoffs": setoffs, "unused_losses": unused,
        "needs_review": ["The land or building indexation option interacts with loss set-off or the unused basic "
                         "exemption here; check it with the indexed cost by hand."] if review else [],
        "policy": {"version": POLICY_VERSION, "act": "Income-tax Act, 2025", "verified_at": "2026-11-25",
                   "sources": [INCOME_TAX_ACT_2025_SOURCE, FINANCE_ACT_2026_SOURCE],
                   "sections": {"holding_period": "2(101)", "specified_funds": "76", "short_term_equity": "196",
                                "long_term_other": "197", "long_term_equity": "198", "loss_set_off": "108(2)",
                                "rebate": "156"},
                   "not_covered": ["carried-forward losses from earlier years", "exemptions for reinvestment",
                                   "non-residents", "grandfathered cost for equity bought before 1 February 2018",
                                   "surcharge marginal relief", "dividend income"]},
    }
