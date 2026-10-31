from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
import re

from django.utils import timezone

from apps.expenses.models import Expense
from apps.expenses.services.statement_import import CREDIT_CARD_KEYWORDS, INVESTMENT_KEYWORDS
from apps.users.models import IncomeBasis


SALARY_KEYWORDS = (
    "SALARY",
    "PAYROLL",
    "PAYDAY",
    "MONTHLY PAY",
    "WAGES",
    "STIPEND",
    "EMPLOYER",
)
NON_SALARY_CREDIT_KEYWORDS = (
    "REFUND",
    "REVERSAL",
    "CASHBACK",
    "INTEREST",
    "REWARD",
    "REWARDS",
    "TRANSFER",
    "SELF",
    "REIMBURSE",
    "REIMB",
    "UPI",
)
NON_SALARY_CATEGORIES = {"transfer", "loan", "investment", "credit_card"}
# These credits are never pay, whatever else their text says.
NEVER_PAY_RE = re.compile(
    r"REFUND|REVERSAL|REVERSED|CASHBACK|REDEMPTION|LOANS?\W+DISBURS|SALARY\W+(?:ADVANCE\W+)?LOANS?\b(?!\W+(?:RECOVERY|DEDUCT|EMI|ADJ))|PAYDAY\W+LOAN"
    r"|LOANS?\W+(?:AGAINST|ON|FROM)\W+(?:SALARY|EMPLOYER)"
)
# Lenders, brokers and card issuers can also be employers, so a credit that says salary still counts.
# Statement text runs words together, so only STOCK and MF need edges.
NOT_PAY_UNLESS_SALARY_RE = re.compile(
    r"LOAN|\bSTOCKS?\b|MF\b|"
    + "|".join(re.escape(word) for word in (*INVESTMENT_KEYWORDS, *CREDIT_CARD_KEYWORDS) if word.strip() not in {"STOCK", "MF"})
)
# Money sent to a salary account says where it landed, not what it was.
SALARY_ACCOUNT_RE = re.compile(r"SALARY\W*(?:A/?C|ACC(?:OUN)?T)\b")
# A lender's disbursal is not pay, but pensions and commissions are paid out in the same words.
PAID_OUT_INCOME_RE = re.compile(r"PENSION|COMMISSION|INCENTIVE|HONORARIUM")
# Older salary credits may belong to a job that has ended.
SALARY_EVIDENCE_MAX_AGE = timedelta(days=92)
# A payer this far behind the newest credit has stopped; paydays can shift by a few days each month.
ACTIVE_PAYER_GAP = timedelta(days=45)
# Pay from an old and a new job overlaps for a month or two, so real second jobs need longer.
CONCURRENT_JOB_MONTHS = 3
# Confirmed income divided by salary credits. Take-home sits well below gross, but credits
# far above a confirmed income are not explained by deductions, so that side is narrow.
INCOME_AGREEMENT_RATIO = (0.9, 1.8)
EMPLOYER_NOISE_TOKENS = {
    "BANK",
    "PAYMENT",
    "CREDIT",
    "ACCOUNT",
    "TRANSFER",
    "SALARY",
    "PAYROLL",
    "EMPLOYER",
    "PRIVATE",
    "PVT",
    "LIMITED",
    "LTD",
}


def is_never_pay(item) -> bool:
    """Statement import files refunds and redemptions as income too, so read the text as well as the category."""
    if item.category in NON_SALARY_CATEGORIES:
        return True
    text = " ".join(str(value or "") for value in (item.company_name, item.counterparty, item.merchant, item.description, item.raw_description)).upper()
    if NEVER_PAY_RE.search(text):
        return True
    described = SALARY_ACCOUNT_RE.sub(" ", text)
    lender_text = NOT_PAY_UNLESS_SALARY_RE.search(text) or ("DISBURS" in text and not PAID_OUT_INCOME_RE.search(text))
    return bool(lender_text) and not any(keyword in described for keyword in SALARY_KEYWORDS)


def build_employment_income_signals(*, user, latest_resume=None, profile=None, today: date | None = None) -> dict:
    today = today or timezone.localdate()
    resume_payload = (latest_resume.extracted_payload or {}) if latest_resume and latest_resume.parser_status == "parsed" else {}
    resume_employer = str(
        resume_payload.get("current_company")
        or resume_payload.get("company")
        or ""
    ).strip()
    credits = list(
        Expense.objects.filter(user=user, direction="credit", transaction_date__lte=today)
        .only(
            "id",
            "amount",
            "merchant",
            "company_name",
            "counterparty",
            "description",
            "raw_description",
            "transaction_date",
            "category",
        )
        .order_by("-transaction_date", "-id")[:240]
    )
    salary_candidates = _build_salary_credit_candidates(credits)
    current_salaries = _current_salary_candidates(salary_candidates, today)
    best_salary_signal = current_salaries[0] if current_salaries else None

    profile_last_salary = float(getattr(profile, "last_salary", 0) or 0)
    reported_value = float(getattr(user, "monthly_income", 0) or 0) or profile_last_salary
    variable_income = float(getattr(user, "variable_income", 0) or 0)
    observed_salary = round(sum(item["monthly_amount"] for item in current_salaries), 2)
    reported_mode = _reported_income_mode(reported_value, user.monthly_income_basis)
    reported_monthly_equivalent = {
        "annual_ctc": float((Decimal(str(reported_value)) / 12).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "monthly": round(reported_value, 2),
    }.get(reported_mode, 0.0)
    income_conflict = _income_conflict(observed_salary, reported_monthly_equivalent)
    # A confirmed income is never silently replaced by what the credits suggest.
    salary_monthly = 0.0 if income_conflict else observed_salary
    monthly_cash_income = round(salary_monthly or reported_monthly_equivalent, 2)

    annualized_compensation = round(monthly_cash_income * 12, 2)
    if reported_mode == "annual_ctc":
        annualized_compensation = round(reported_value, 2)

    current_employer = resume_employer or str(best_salary_signal.get("employer", "") if best_salary_signal else "").strip()
    employer_source = "resume" if resume_employer else ("salary_credit" if best_salary_signal else "not_evidenced")
    salary_source = "salary_credits" if salary_monthly else {
        "annual_ctc": "reported_annual_ctc", "monthly": "reported_monthly_income", "unconfirmed": "reported_income_unconfirmed",
    }.get(reported_mode, "not_evidenced")
    source_summary = _build_source_summary(
        employer=current_employer,
        employer_source=employer_source,
        salary_source=salary_source,
        salary_signal=best_salary_signal,
        reported_mode=reported_mode,
        income_conflict=income_conflict,
        stale_salary_signal=None if current_salaries or not salary_candidates else salary_candidates[0],
    )

    return {
        "current_employer": current_employer,
        "current_employer_source": employer_source,
        "monthly_cash_income": monthly_cash_income,
        "annualized_compensation": annualized_compensation,
        "variable_income": round(variable_income, 2),
        "reported_income": {
            "value": round(reported_value, 2),
            "mode": reported_mode,
            "monthly_equivalent": reported_monthly_equivalent,
        },
        "salary_signal_count": len(current_salaries),
        "salary_credit_signal": best_salary_signal,
        "income_conflict": income_conflict,
        "source_summary": source_summary,
    }


def _build_salary_credit_candidates(credits: list[Expense]) -> list[dict]:
    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "employer": "",
            "amounts": [],
            "months": set(),
            "days": [],
            "keyword_hits": 0,
            "items": [],
        }
    )

    for item in credits:
        amount = float(item.amount or 0)
        if amount < 10000 or is_never_pay(item):
            continue
        raw_text = " ".join(
            str(value or "")
            for value in [
                item.company_name,
                item.counterparty,
                item.merchant,
                item.description,
                item.raw_description,
            ]
            if value
        ).upper()
        if not raw_text:
            continue
        has_salary_keyword = any(keyword in raw_text for keyword in SALARY_KEYWORDS)
        has_non_salary_marker = any(keyword in raw_text for keyword in NON_SALARY_CREDIT_KEYWORDS)
        if has_non_salary_marker and not has_salary_keyword:
            continue
        employer = _extract_employer_label(item, raw_text)
        if not employer:
            continue

        key = _normalize_employer_key(employer)
        bucket = buckets[key]
        bucket["employer"] = employer
        bucket["amounts"].append(amount)
        bucket["months"].add((item.transaction_date.year, item.transaction_date.month))
        bucket["days"].append(item.transaction_date.day)
        if has_salary_keyword:
            bucket["keyword_hits"] += 1
        bucket["items"].append(
            {
                "id": item.id,
                "amount": round(amount, 2),
                "transaction_date": item.transaction_date.isoformat(),
                "merchant": item.merchant or item.company_name or item.counterparty or "",
            }
        )

    candidates: list[dict] = []
    for bucket in buckets.values():
        amounts = bucket["amounts"]
        if not amounts:
            continue
        monthly_amount = float(median(amounts))
        months_count = len(bucket["months"])
        variability = ((max(amounts) - min(amounts)) / max(monthly_amount, 1)) if len(amounts) > 1 else 0.0
        day_span = (max(bucket["days"]) - min(bucket["days"])) if len(bucket["days"]) > 1 else 0
        score = 0
        if bucket["keyword_hits"]:
            score += 3
        if months_count >= 2:
            score += 2
        if months_count >= 3:
            score += 1
        if variability <= 0.2:
            score += 2
        elif variability <= 0.35:
            score += 1
        if day_span <= 6:
            score += 1
        if monthly_amount >= 25000:
            score += 1

        # One credit proves nothing unless its own text says it is salary.
        if score < 4 or not (bucket["keyword_hits"] or months_count > 1):
            continue

        confidence = min(0.95, 0.35 + (0.08 * bucket["keyword_hits"]) + (0.1 * min(months_count, 4)) + (0.12 if variability <= 0.2 else 0.04))
        candidates.append(
            {
                "employer": bucket["employer"],
                "monthly_amount": round(monthly_amount, 2),
                "months_observed": months_count,
                "months": sorted(f"{year}-{month:02d}" for year, month in bucket["months"]),
                "last_credit": max(item["transaction_date"] for item in bucket["items"]),
                "described_as_salary": bool(bucket["keyword_hits"]),
                "transactions_observed": len(amounts),
                "confidence": round(confidence, 3),
                "supporting_transactions": bucket["items"][:6],
            }
        )

    candidates.sort(
        key=lambda item: (
            float(item["confidence"]),
            int(item["months_observed"]),
            float(item["monthly_amount"]),
        ),
        reverse=True,
    )
    return candidates


def _current_salary_candidates(candidates: list[dict], today: date) -> list[dict]:
    cutoff = (today - SALARY_EVIDENCE_MAX_AGE).isoformat()
    recent = [item for item in candidates if item["last_credit"] >= cutoff]
    if not recent:
        return []
    newest = max(date.fromisoformat(item["last_credit"]) for item in recent)
    active = [item for item in recent if newest - date.fromisoformat(item["last_credit"]) <= ACTIVE_PAYER_GAP]
    # A lone credit may be a bonus or stipend, so it waits until any recurring pay has stopped.
    pool = [item for item in active if item["months_observed"] > 1] or active
    payers = [item for item in pool if item["described_as_salary"]] or pool
    primary = max(payers, key=lambda item: item["monthly_amount"])
    return [primary, *(
        item for item in active
        if item is not primary and item["described_as_salary"]
        and len(set(item["months"]) & set(primary["months"])) >= CONCURRENT_JOB_MONTHS
    )]


def _income_conflict(observed_salary: float, reported_monthly: float) -> dict | None:
    if not observed_salary or not reported_monthly:
        return None
    low, high = INCOME_AGREEMENT_RATIO
    if low <= reported_monthly / observed_salary <= high:
        return None
    return {
        "salary_monthly": observed_salary,
        "reported_monthly": reported_monthly,
        "message": (
            f"Recent salary credits of about \u20b9{observed_salary:,.0f} a month differ from your confirmed income of "
            f"\u20b9{reported_monthly:,.0f} a month. ALFRED keeps using your confirmed income; update it in Settings if it has changed."
        ),
    }


def _extract_employer_label(item: Expense, raw_text: str) -> str:
    for value in (item.company_name, item.counterparty, item.merchant):
        label = _clean_employer_label(value)
        if label:
            return label

    field_match = re.search(
        r"\b(?:SALARY|PAYROLL|EMPLOYER|CREDIT)\b[\s:/-]+([A-Z][A-Z0-9&.,'() -]{2,80})",
        raw_text,
    )
    if field_match:
        label = _clean_employer_label(field_match.group(1))
        if label:
            return label

    return ""


def _clean_employer_label(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "").replace("/", " ").replace("-", " ").strip())
    if not text:
        return ""
    upper = text.upper()
    if upper in {"SELF", "TRANSFER"}:
        return ""
    if len(upper.split()) == 1 and upper in EMPLOYER_NOISE_TOKENS:
        return text.title()

    parts = []
    for token in re.sub(r"[^A-Z0-9& ]", " ", upper).split():
        if len(token) <= 1:
            continue
        if token in EMPLOYER_NOISE_TOKENS and parts:
            continue
        parts.append(token)
        if len(parts) >= 4:
            break
    return " ".join(parts).title()[:120]


def _normalize_employer_key(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", str(value or "").upper())).strip()


def _reported_income_mode(reported_value: float, basis: str) -> str:
    """The owner states the period; an amount's size never decides it."""
    if reported_value <= 0:
        return "absent"
    if basis == IncomeBasis.UNCONFIRMED:
        return "unconfirmed"
    # The period also covers a career-profile income used when no income is entered in Settings.
    return "annual_ctc" if basis == IncomeBasis.ANNUAL else "monthly"


def _build_source_summary(
    *,
    employer: str,
    employer_source: str,
    salary_source: str,
    salary_signal: dict | None,
    reported_mode: str,
    income_conflict: dict | None,
    stale_salary_signal: dict | None,
) -> str:
    parts = []
    if income_conflict:
        parts.append(income_conflict["message"])
    if stale_salary_signal:
        parts.append(f"Salary credits last seen on {stale_salary_signal['last_credit']} are too old to set your current income.")
    if employer:
        parts.append(
            f"Current employer is inferred as {employer} from {employer_source.replace('_', ' ')}."
        )
    if salary_signal and not income_conflict:
        parts.append(
            f"Recurring credit history suggests monthly salary cash-in of INR {salary_signal['monthly_amount']:,.0f} across {salary_signal['months_observed']} month(s)."
        )
    elif income_conflict:
        pass  # Its message above already says which income is in use.
    elif salary_source == "reported_annual_ctc":
        parts.append("Monthly cash income falls back to the reported annual CTC because no recurring salary credit pattern is evidenced yet.")
    elif salary_source == "reported_monthly_income":
        parts.append("Monthly cash income falls back to the reported income field because no recurring salary credit pattern is evidenced yet.")
    if reported_mode == "unconfirmed":
        parts.append("The entered income is not used until you confirm in Settings whether it is per month or per year.")
    if reported_mode == "annual_ctc":
        parts.append("The reported income input is being treated as annual CTC, not monthly take-home.")
    return " ".join(parts[:3]).strip()
