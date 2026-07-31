from __future__ import annotations

from collections import defaultdict
from statistics import median
import re

from apps.expenses.models import Expense


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


def build_employment_income_signals(*, user, latest_resume=None, profile=None) -> dict:
    resume_payload = (latest_resume.extracted_payload or {}) if latest_resume and latest_resume.parser_status == "parsed" else {}
    resume_employer = str(
        resume_payload.get("current_company")
        or resume_payload.get("company")
        or ""
    ).strip()
    credits = list(
        Expense.objects.filter(user=user, direction="credit")
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
    best_salary_signal = salary_candidates[0] if salary_candidates else None

    profile_last_salary = float(getattr(profile, "last_salary", 0) or 0)
    reported_value = float(getattr(user, "monthly_income", 0) or profile_last_salary or 0)
    variable_income = float(getattr(user, "variable_income", 0) or 0)
    salary_monthly = float(best_salary_signal.get("monthly_amount", 0) or 0) if best_salary_signal else 0.0
    reported_mode = _infer_reported_income_mode(reported_value, salary_monthly)
    reported_monthly_equivalent = round(reported_value / 12, 2) if reported_mode == "annual_ctc" else round(reported_value, 2)
    monthly_cash_income = round(salary_monthly or reported_monthly_equivalent or profile_last_salary, 2)

    annualized_compensation = round(monthly_cash_income * 12, 2)
    if reported_mode == "annual_ctc" and reported_value > 0:
        if not salary_monthly:
            annualized_compensation = round(reported_value, 2)
        else:
            salary_annual = salary_monthly * 12
            ratio = reported_value / max(salary_annual, 1)
            if 0.55 <= ratio <= 1.8:
                annualized_compensation = round(max(reported_value, salary_annual), 2)

    current_employer = resume_employer or str(best_salary_signal.get("employer", "") if best_salary_signal else "").strip()
    employer_source = "resume" if resume_employer else ("salary_credit" if best_salary_signal else "not_evidenced")
    salary_source = "salary_credits" if salary_monthly else ("reported_annual_ctc" if reported_mode == "annual_ctc" else ("reported_monthly_income" if reported_value else "not_evidenced"))
    source_summary = _build_source_summary(
        employer=current_employer,
        employer_source=employer_source,
        salary_source=salary_source,
        salary_signal=best_salary_signal,
        reported_mode=reported_mode,
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
        "salary_signal_count": len(salary_candidates),
        "salary_credit_signal": best_salary_signal,
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
        if amount < 10000:
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

        if score < 4:
            continue

        confidence = min(0.95, 0.35 + (0.08 * bucket["keyword_hits"]) + (0.1 * min(months_count, 4)) + (0.12 if variability <= 0.2 else 0.04))
        candidates.append(
            {
                "employer": bucket["employer"],
                "monthly_amount": round(monthly_amount, 2),
                "months_observed": months_count,
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


def _infer_reported_income_mode(reported_value: float, salary_monthly: float) -> str:
    if reported_value <= 0:
        return "absent"
    if salary_monthly > 0:
        monthly_gap = abs(reported_value - salary_monthly) / max(salary_monthly, 1)
        annual_gap = abs((reported_value / 12) - salary_monthly) / max(salary_monthly, 1)
        if reported_value >= 300000 and annual_gap < monthly_gap:
            return "annual_ctc"
        return "monthly"
    return "annual_ctc" if reported_value >= 300000 else "monthly"


def _build_source_summary(*, employer: str, employer_source: str, salary_source: str, salary_signal: dict | None, reported_mode: str) -> str:
    parts = []
    if employer:
        parts.append(
            f"Current employer is inferred as {employer} from {employer_source.replace('_', ' ')}."
        )
    if salary_signal:
        parts.append(
            f"Recurring credit history suggests monthly salary cash-in of INR {salary_signal['monthly_amount']:,.0f} across {salary_signal['months_observed']} month(s)."
        )
    elif salary_source == "reported_annual_ctc":
        parts.append("Monthly cash income falls back to the reported annual CTC because no recurring salary credit pattern is evidenced yet.")
    elif salary_source == "reported_monthly_income":
        parts.append("Monthly cash income falls back to the reported income field because no recurring salary credit pattern is evidenced yet.")
    if reported_mode == "annual_ctc":
        parts.append("The reported income input is being treated as annual CTC, not monthly take-home.")
    return " ".join(parts[:3]).strip()
