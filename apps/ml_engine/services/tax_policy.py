"""Versioned Indian ordinary-income planning rules; no request-time rule fetching.

Amounts stay Decimal until the API renderer. This is a planning calculation before
statutory return-filing rounding. Special-rate income/credits/loss set-offs need a
separate computation and must not be passed as ordinary income.
"""
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from types import MappingProxyType

from django.utils import timezone


D = Decimal
ZERO = D("0")
PAISE = D("0.01")
POLICY_VERSION = "india-ordinary-income-2025-26-v1"
OFFICIAL_SOURCE = "https://www.incometax.gov.in/iec/foportal/help/individual/return-applicable-1"
BUDGET_FAQ_SOURCE = (
    "https://www.incometaxindia.gov.in/documents/20117/15766092/FAQs-Budget-2026.pdf/"
    "ff3d0e10-88a0-b11f-3c27-b58375974227?download=true&t=1770036575267&version=1.0"
)
INCOME_TAX_ACT_2025_SOURCE = "https://egazette.gov.in/WriteReadData/2025/265620.pdf"
FINANCE_ACT_2026_SOURCE = "https://egazette.gov.in/WriteReadData/2026/271439.pdf"


class TaxPolicyError(ValueError):
    """Safe, user-facing validation error (never includes supplied input)."""


def amount(value, field="Amount") -> Decimal:
    """Bound untrusted numbers before Decimal arithmetic/formatting."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise TaxPolicyError(f"{field} must be a finite, non-negative amount.")
    text = str(value)
    if len(text) > 64:
        raise TaxPolicyError(f"{field} is outside the supported amount range.")
    try:
        number = D(text)
    except InvalidOperation:
        raise TaxPolicyError(f"{field} must be a finite, non-negative amount.") from None
    if not number.is_finite() or number < ZERO or number > D("9999999999999999.99"):
        raise TaxPolicyError(f"{field} must be between 0 and 9999999999999999.99.")
    # Tiny exponents are harmless but should not propagate into calculations.
    with localcontext() as context:
        context.prec = 40
        return number.quantize(PAISE, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class TaxPolicy:
    financial_year: str
    assessment_year: str
    regime: str
    slabs: tuple
    standard_deduction: Decimal
    rebate_threshold: Decimal
    rebate_limit: Decimal
    rebate_marginal_relief: bool
    surcharge_bands: tuple
    deduction_limits: Mapping
    cess_rate: Decimal = D("0.04")
    effective_date: str = "2025-04-01"
    verified_at: str = "2026-10-01"
    version: str = POLICY_VERSION
    act: str = "Income-tax Act, 1961"
    sources: tuple = (OFFICIAL_SOURCE, BUDGET_FAQ_SOURCE)
    # Legal section for each supported deduction key, plus rebate/standard deduction/new regime.
    sections: Mapping = MappingProxyType({
        "rebate": "87A", "standard_deduction": "16(ia)", "new_regime": "115BAC",
        "80C": "80C", "80CCD(1B)": "80CCD(1B)", "80D": "80D", "80E": "80E", "80G": "80G",
        "24B": "24(b)", "HRA": "10(13A)", "80CCD(2)": "80CCD(2)", "80CCH": "80CCH",
    })

    def metadata(self):
        return {
            "version": self.version,
            "financial_year": self.financial_year,
            "assessment_year": self.assessment_year,
            "act": self.act,
            "legal_sections": dict(self.sections),
            "regime": self.regime,
            "effective_date": self.effective_date,
            "verified_at": self.verified_at,
            "source_url": self.sources[0],
            "sources": list(self.sources),
            "source_type": "official_tax_authority",
            "freshness": "STATIC_REFERENCE",
            "standard_deduction_limit": self.standard_deduction,
            "rebate_threshold": self.rebate_threshold,
            "rebate_limit": self.rebate_limit,
            "rebate_residents_only": True,
            "rebate_marginal_relief": self.rebate_marginal_relief,
            "surcharge_marginal_relief": True,
            "cess_rate": self.cess_rate,
            "slabs": [{"upper_limit": limit, "rate_percent": rate} for limit, rate in self.slabs],
            "surcharge_bands": [
                {"above_income": threshold, "rate": rate} for threshold, rate in self.surcharge_bands
            ],
            "deduction_limits": dict(self.deduction_limits),
            "scope": "Ordinary slab-rate income only; salary standard deduction only for salary income.",
            "deduction_basis": "Amounts must already qualify under the section; gross payments are not proof of eligibility.",
            "rounding": "Paise, half up; statutory return-filing rounding is not applied.",
            "excluded": ["special-rate income", "capital gains", "lottery winnings", "agricultural integration", "loss set-offs", "tax credits"],
        }


OLD = TaxPolicy(
    "2025-26", "2026-27", "old",
    ((250000, 0), (500000, 5), (1000000, 20), (None, 30)),
    D("50000"), D("500000"), D("12500"), False,
    ((5000000, D("0.10")), (10000000, D("0.15")), (20000000, D("0.25")), (50000000, D("0.37"))),
    MappingProxyType({"80C": D("150000"), "80CCD(1B)": D("50000"), "80D": D("100000"),
                      "80E": None, "80G": None, "24B": D("200000"), "HRA": None,
                      "80CCD(2)": None, "80CCH": None}),
)
NEW = TaxPolicy(
    "2025-26", "2026-27", "new",
    ((400000, 0), (800000, 5), (1200000, 10), (1600000, 15), (2000000, 20), (2400000, 25), (None, 30)),
    D("75000"), D("1200000"), D("60000"), True,
    ((5000000, D("0.10")), (10000000, D("0.15")), (20000000, D("0.25"))),
    MappingProxyType({"80CCD(2)": None, "80CCH": None}),
)
# Tax year 2026-27 (1 April 2026 - 31 March 2027) under the Income-tax Act, 2025, which
# has no assessment year. Verified 2026-11-06 against the gazetted Act (s.19 standard
# deduction, s.22(2) house-property interest, ss.123-126/129/133 deductions, s.156 rebate,
# s.202 new-regime slabs) and the enacted Finance Act, 2026 (s.3: Part I-B Paragraph A
# old-regime slabs, Paragraph F and s.202 surcharge, 4% cess). Every figure is unchanged.
_ACT_2025 = dict(
    financial_year="2026-27", assessment_year=None, effective_date="2026-04-01", verified_at="2026-11-06",
    version="india-ordinary-income-2026-27-v1", act="Income-tax Act, 2025",
    sources=(FINANCE_ACT_2026_SOURCE, INCOME_TAX_ACT_2025_SOURCE, BUDGET_FAQ_SOURCE),
    sections=MappingProxyType({
        "rebate": "156", "standard_deduction": "19(1) Table Sl. 2", "new_regime": "202",
        "80C": "123 (Schedule XV)", "80CCD(1B)": "124(3)", "80D": "126", "80E": "129", "80G": "133",
        "24B": "22(2)", "HRA": None, "80CCD(2)": "124(1)-(2)", "80CCH": "125",
    }),
)
OLD_2026 = replace(OLD, **_ACT_2025)
NEW_2026 = replace(NEW, **_ACT_2025)
POLICIES = MappingProxyType({
    ("2025-26", "old"): OLD, ("2025-26", "new"): NEW,
    ("2026-27", "old"): OLD_2026, ("2026-27", "new"): NEW_2026,
})
SUPPORTED_YEARS = tuple(sorted({year for year, _ in POLICIES}))
BUDGET_DAY = (2, 1)  # The Union Budget is normally presented on 1 February.


def tax_year_for(day: date) -> str:
    """Indian tax/financial year (April-March) containing `day`, e.g. '2026-27'."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def default_financial_year(today: date | None = None) -> str:
    """Current tax year when its rules are verified, otherwise the latest verified year."""
    current = tax_year_for(today or timezone.localdate())
    return current if current in SUPPORTED_YEARS else SUPPORTED_YEARS[-1]


def policy_coverage(today: date | None = None) -> dict:
    """Tell the owner when a Budget or tax year has outrun ALFRED's verified rules.

    Rules are never fetched or inferred: a new year needs its enacted Finance Act checked
    and added here. The notice says which year's rules an estimate uses.
    """
    today = today or timezone.localdate()
    current, latest = tax_year_for(today), SUPPORTED_YEARS[-1]
    following = tax_year_for(date(today.year + (today.month >= 4), 4, 1))
    previous = tax_year_for(date(today.year - (today.month < 4) - 1, 4, 1))
    status, notice = "CURRENT", ""
    if current not in SUPPORTED_YEARS:
        status = "CURRENT_YEAR_UNVERIFIED"
        notice = (f"Tax year {current} has started, but ALFRED has verified rules only up to {latest}. "
                  f"Estimates use the {latest} rules. Check the Budget and Finance Act for {current} "
                  "with the Income Tax Department before planning or filing.")
    elif today.month < 4 and (today.month, today.day) >= BUDGET_DAY and following not in SUPPORTED_YEARS:
        status = "NEXT_BUDGET_UNVERIFIED"
        notice = (f"The Budget for tax year {following} is normally presented on 1 February. ALFRED has not "
                  f"verified its rules yet; estimates use the {current} rules. Check the announced changes "
                  f"before planning for {following}.")
    filing = ""
    if 4 <= today.month <= 12 and previous in SUPPORTED_YEARS:
        filing = (f"Filing your return for tax year {previous}? Choose {previous} under Financial Year so the "
                  "estimate uses that year's rules.")
    return {"current_tax_year": current, "latest_verified_year": latest, "supported_years": list(SUPPORTED_YEARS),
            "status": status, "notice": notice, "filing_hint": filing}


def get_policy(regime="old", *, financial_year=None, assessment_year=None) -> TaxPolicy:
    if regime not in ("old", "new"):
        raise TaxPolicyError("Tax regime must be old or new.")
    if financial_year is None:
        if assessment_year is None:
            financial_year = default_financial_year()
        elif assessment_year == "2026-27":
            financial_year = "2025-26"
        else:
            raise TaxPolicyError("Unsupported assessment year. Supported: AY 2026-27 (FY 2025-26); "
                                 "from tax year 2026-27 choose the tax year instead.")
    if financial_year not in SUPPORTED_YEARS:
        raise TaxPolicyError("Unsupported financial year. Supported: " + ", ".join(SUPPORTED_YEARS) + ".")
    policy = POLICIES[(financial_year, regime)]
    if assessment_year is not None and assessment_year != policy.assessment_year:
        raise TaxPolicyError("Assessment year does not match the financial year; tax year 2026-27 onwards has none.")
    return policy


def _slab_tax(taxable, slabs):
    tax, lower, breakdown = ZERO, ZERO, []
    for upper, rate in slabs:
        if taxable <= lower:
            break
        part = min(taxable, D(upper)) - lower if upper is not None else taxable - lower
        slab_tax = part * D(rate) / 100
        breakdown.append({
            "range": f"₹{lower:,.0f} - ₹{upper:,.0f}" if upper is not None else f"Above ₹{lower:,.0f}",
            "rate": rate, "income_in_slab": part, "tax": slab_tax,
        })
        tax += slab_tax
        if upper is None:
            break
        lower = D(upper)
    return tax, breakdown


def _surcharge_rate(taxable, policy):
    return next((rate for threshold, rate in reversed(policy.surcharge_bands) if taxable > threshold), ZERO)


def calculate_income_tax(annual_income, regime="old", deductions=None, *, financial_year=None,
                         assessment_year=None, income_type="salary", resident=True,
                         age_group="under_60", special_rate_income=0):
    """Calculate a bounded, explicitly dated ordinary-income planning estimate.

    `deductions` contains eligible deductible amounts, not gross expenditure.
    Conditional eligibility (e.g. HRA, donations, NPS salary caps, 80D age splits)
    must be established before calling. Unavailable new-regime sections are
    explicitly returned in ignored_deductions, never silently applied.
    """
    policy = get_policy(regime, financial_year=financial_year, assessment_year=assessment_year)
    income = amount(annual_income, "Annual income")
    if income_type not in ("salary", "ordinary"):
        raise TaxPolicyError("Income type must be salary or ordinary slab-rate income.")
    if not isinstance(resident, bool) or age_group not in ("under_60", "60_to_79", "80_plus"):
        raise TaxPolicyError("Provide a valid residency flag and age group.")
    if amount(special_rate_income, "Special-rate income"):
        raise TaxPolicyError("Special-rate income requires a separate tax calculation and is not supported here.")
    if deductions is None:
        deductions = {}
    if not isinstance(deductions, Mapping) or len(deductions) > len(OLD.deduction_limits):
        raise TaxPolicyError("Deductions must be a mapping of supported sections to eligible amounts.")
    accepted, ignored, capped = {}, {}, {}
    for section, value in deductions.items():
        if section not in OLD.deduction_limits:
            raise TaxPolicyError("Unsupported deduction section.")
        requested = amount(value, "Deduction")
        if section not in policy.deduction_limits:
            ignored[section] = requested
            continue
        cap = policy.deduction_limits[section]
        # Under-60 self/family cap 25k + senior-parent cap 50k. Within this
        # aggregate ceiling, callers must supply the actual eligible split.
        if section == "80D" and age_group == "under_60":
            cap = D("75000")
        accepted[section] = min(requested, cap) if cap is not None else requested
        if accepted[section] != requested:
            capped[section] = requested - accepted[section]
    slabs = policy.slabs
    if regime == "old" and resident and age_group != "under_60":
        exemption = 300000 if age_group == "60_to_79" else 500000
        slabs = ((exemption, 0),) + tuple(slab for slab in slabs[1:] if slab[0] is None or slab[0] > exemption)
    with localcontext() as context:
        context.prec = 40
        standard = min(income, policy.standard_deduction) if income_type == "salary" else ZERO
        total_deductions = sum(accepted.values(), ZERO)
        taxable = max(ZERO, income - standard - total_deductions)
        base, breakdown = _slab_tax(taxable, slabs)
        rebate = min(base, policy.rebate_limit) if resident and taxable <= policy.rebate_threshold else ZERO
        rebate_relief = ZERO
        if resident and policy.rebate_marginal_relief and taxable > policy.rebate_threshold:
            rebate_relief = max(ZERO, base - (taxable - policy.rebate_threshold))
        after_rebate = base - rebate - rebate_relief
        rate = _surcharge_rate(taxable, policy)
        surcharge = after_rebate * rate
        surcharge_relief = ZERO
        if rate:
            threshold = next(D(threshold) for threshold, band_rate in reversed(policy.surcharge_bands)
                             if taxable > threshold and band_rate == rate)
            threshold_tax, _ = _slab_tax(threshold, slabs)
            threshold_total = threshold_tax * (1 + _surcharge_rate(threshold, policy))
            surcharge_relief = max(ZERO, after_rebate + surcharge - threshold_total - (taxable - threshold))
        before_cess = after_rebate + surcharge - surcharge_relief
        cess = (before_cess * policy.cess_rate).quantize(PAISE, rounding=ROUND_HALF_UP)
        final = (before_cess + cess).quantize(PAISE, rounding=ROUND_HALF_UP)
        return {
            "annual_income": income, "regime": regime,
            "financial_year": policy.financial_year, "assessment_year": policy.assessment_year,
            "policy": policy.metadata(), "calculation_status": "ESTIMATED",
            "income_type": income_type, "resident": resident, "age_group": age_group,
            "standard_deduction": standard, "total_deductions": total_deductions,
            "deduction_breakdown": accepted, "ignored_deductions": ignored, "capped_deductions": capped,
            "taxable_income": taxable, "base_tax": base, "slab_breakdown": breakdown,
            "rebate_87a": rebate, "rebate_marginal_relief": rebate_relief,
            "surcharge_rate": rate, "surcharge_before_relief": surcharge,
            "surcharge_marginal_relief": surcharge_relief, "surcharge": surcharge - surcharge_relief,
            "tax_before_cess": before_cess, "cess": cess,
            "total_tax_before_rebate": ((base + surcharge) * (1 + policy.cess_rate)).quantize(PAISE, rounding=ROUND_HALF_UP),
            "final_tax": final,
            "effective_tax_rate": (final / income * 100).quantize(PAISE, rounding=ROUND_HALF_UP) if income else ZERO,
            "monthly_tax": (final / 12).quantize(PAISE, rounding=ROUND_HALF_UP),
            "take_home_monthly": ((income - final) / 12).quantize(PAISE, rounding=ROUND_HALF_UP),
        }
