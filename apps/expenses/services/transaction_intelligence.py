from __future__ import annotations

from datetime import timedelta
import hashlib
import re
from statistics import mean

from django.db.models import Avg
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.expenses.models import BankAccount, Expense
from apps.expenses.services.statement_import import classify_transaction_text
from apps.ml_engine.core.alfred_inference import alfred_engine


DISCRETIONARY_CATEGORIES = {"food", "shopping", "travel", "subscription", "entertainment"}
EMOTIONAL_KEYWORDS = (
    "SALE",
    "LIMITED OFFER",
    "FLASH",
    "SWIGGY",
    "ZOMATO",
    "AMAZON",
    "MYNTRA",
    "FLIPKART",
    "LUXURY",
    "PREMIUM",
)
KNOWN_COMPANIES = {
    "AMAZON": "Amazon",
    "FLIPKART": "Flipkart",
    "MYNTRA": "Myntra",
    "SWIGGY": "Swiggy",
    "ZOMATO": "Zomato",
    "GROWW": "Groww",
    "ZERODHA": "Zerodha",
    "CRED": "CRED",
    "HDFC": "HDFC Bank",
    "ICICI": "ICICI Bank",
    "SBI": "State Bank of India",
    "INDIAN OIL": "Indian Oil",
    "JIO": "Jio",
    "NETFLIX": "Netflix",
    "SPOTIFY": "Spotify",
    "NOBROKER": "NoBroker",
    "BAJAJ": "Bajaj Finance",
    "POONAWALLA": "Poonawalla Fincorp",
    "ONECARD": "OneCard",
}


def hydrate_expense_data(*, user, payload: dict, initial_data: dict | None = None, instance: Expense | None = None) -> dict:
    data = dict(payload)
    provided_fields = set((initial_data or {}).keys())

    direction = data.get("direction") or getattr(instance, "direction", "debit")
    amount = float(data.get("amount", getattr(instance, "amount", 0)) or 0)
    transaction_date = data.get("transaction_date") or getattr(instance, "transaction_date", timezone.localdate())
    source_text = (
        data.get("raw_description")
        or data.get("description")
        or getattr(instance, "raw_description", "")
        or getattr(instance, "description", "")
        or data.get("merchant")
        or getattr(instance, "merchant", "")
    )

    inferred = classify_transaction_text(source_text, direction) if source_text else {}

    for field in ("classification", "category", "payment_mode", "merchant", "external_reference"):
        if _should_fill(field, data, provided_fields):
            data[field] = inferred.get(field, data.get(field))

    if _should_fill("raw_description", data, provided_fields):
        data["raw_description"] = inferred.get("raw_description", source_text)
    if _should_fill("description", data, provided_fields):
        data["description"] = inferred.get("description", source_text[:140] if source_text else "")

    counterparty = data.get("counterparty") or inferred.get("counterparty") or data.get("merchant") or ""
    company_name = data.get("company_name") or inferred.get("company_name") or _infer_company_name(counterparty, source_text)
    emotional = _detect_emotional_spend(
        user=user,
        amount=amount,
        category=data.get("category", getattr(instance, "category", "other")) or "other",
        direction=direction,
        merchant=data.get("merchant", getattr(instance, "merchant", "")) or "",
        description=data.get("raw_description") or source_text,
        transaction_date=transaction_date,
        instance=instance,
    )

    data["counterparty"] = counterparty
    data["company_name"] = company_name
    data["transaction_fingerprint"] = build_transaction_fingerprint(
        bank_account=data.get("bank_account", getattr(instance, "bank_account", None)),
        transaction_date=transaction_date,
        amount=amount,
        direction=direction,
        external_reference=data.get("external_reference", getattr(instance, "external_reference", "")),
        raw_description=data.get("raw_description") or source_text,
        closing_balance=data.get("closing_balance", getattr(instance, "closing_balance", None)),
    )
    data["is_emotional"] = emotional["is_emotional"]
    data["model_confidence"] = emotional["confidence"]
    data["ai_summary"] = _build_ai_summary(
        amount=amount,
        direction=direction,
        counterparty=counterparty,
        company_name=company_name,
        category=data.get("category", getattr(instance, "category", "other")),
        payment_mode=data.get("payment_mode", getattr(instance, "payment_mode", "BANK")),
        emotional=emotional["is_emotional"],
        emotion_reason=emotional["reason"],
    )
    return data


def enrich_imported_expense(
    *,
    user,
    amount: float,
    classification: str,
    category: str,
    payment_mode: str,
    merchant: str,
    description: str,
    raw_description: str,
    direction: str,
    transaction_date,
    external_reference: str,
    counterparty: str = "",
    company_name: str = "",
) -> dict:
    emotional = _detect_emotional_spend(
        user=user,
        amount=amount,
        category=category,
        direction=direction,
        merchant=merchant,
        description=raw_description or description,
        transaction_date=transaction_date,
    )
    effective_counterparty = counterparty or merchant or "Unspecified"
    effective_company = company_name or _infer_company_name(merchant, raw_description or description)
    fingerprint = build_transaction_fingerprint(
        bank_account=None,
        transaction_date=transaction_date,
        amount=amount,
        direction=direction,
        external_reference=external_reference,
        raw_description=raw_description or description,
        closing_balance=None,
    )
    return {
        "classification": classification,
        "category": category,
        "payment_mode": payment_mode,
        "merchant": merchant,
        "description": description,
        "raw_description": raw_description,
        "direction": direction,
        "external_reference": external_reference,
        "counterparty": effective_counterparty,
        "company_name": effective_company,
        "transaction_fingerprint": fingerprint,
        "is_emotional": emotional["is_emotional"],
        "model_confidence": emotional["confidence"],
        "ai_summary": _build_ai_summary(
            amount=amount,
            direction=direction,
            counterparty=effective_counterparty,
            company_name=effective_company,
            category=category,
            payment_mode=payment_mode,
            emotional=emotional["is_emotional"],
            emotion_reason=emotional["reason"],
        ),
    }


def resolve_bank_account(
    *,
    user,
    bank_name: str = "",
    account_holder: str = "",
    account_number: str = "",
    account_type: str = "savings",
    current_balance: float | None = None,
) -> BankAccount | None:
    normalized_number = _normalize_account_number(account_number)
    if not normalized_number:
        return None

    account, created = BankAccount.objects.get_or_create(
        user=user,
        account_number=normalized_number,
        defaults={
            "bank_name": bank_name,
            "account_holder": account_holder,
            "account_type": account_type or "savings",
            "current_balance": current_balance,
            "last_synced_at": timezone.now(),
        },
    )

    changed_fields: list[str] = []
    if bank_name and account.bank_name != bank_name:
        account.bank_name = bank_name
        changed_fields.append("bank_name")
    if account_holder and account.account_holder != account_holder:
        account.account_holder = account_holder
        changed_fields.append("account_holder")
    if account_type and account.account_type != account_type:
        account.account_type = account_type
        changed_fields.append("account_type")
    if current_balance is not None and account.current_balance != current_balance:
        account.current_balance = current_balance
        changed_fields.append("current_balance")
    if created or account.last_synced_at is None:
        account.last_synced_at = timezone.now()
        changed_fields.append("last_synced_at")
    elif current_balance is not None:
        account.last_synced_at = timezone.now()
        changed_fields.append("last_synced_at")

    if changed_fields:
        account.save(update_fields=sorted(set(changed_fields)))

    return account


def build_transaction_fingerprint(
    *,
    bank_account: BankAccount | None,
    transaction_date,
    amount: float,
    direction: str,
    external_reference: str = "",
    raw_description: str = "",
    closing_balance: float | None = None,
) -> str:
    account_key = _normalize_account_number(getattr(bank_account, "account_number", "")) if bank_account else ""
    reference = _normalize_reference(external_reference)
    description = _normalize_description(raw_description)
    closing = f"{float(closing_balance):.2f}" if closing_balance not in {None, ""} else ""
    payload = "|".join(
        [
            account_key,
            str(transaction_date or ""),
            f"{float(amount or 0):.2f}",
            str(direction or ""),
            reference,
            description[:90],
            closing,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sync_account_balance(bank_account: BankAccount | None, closing_balance: float | None) -> None:
    if bank_account is None or closing_balance is None:
        return
    bank_account.current_balance = closing_balance
    bank_account.last_synced_at = timezone.now()
    bank_account.save(update_fields=["current_balance", "last_synced_at"])


def _detect_emotional_spend(*, user, amount: float, category: str, direction: str, merchant: str, description: str, transaction_date, instance: Expense | None = None) -> dict:
    if direction == "credit" or amount <= 0:
        return {"is_emotional": False, "confidence": 0.05, "reason": "Cash-in transactions are not treated as emotional spend."}

    payload = {"amount": amount, "category": category, "description": description or merchant}
    try:
        base = alfred_engine.predict_emotional_spend(payload)
        base_confidence = float(base.get("confidence", 0) or 0)
        base_emotional = bool(base.get("is_emotional"))
    except Exception:
        base_confidence = 0.0
        base_emotional = False

    history_qs = Expense.objects.filter(user=user, direction="debit")
    if instance is not None and instance.pk:
        history_qs = history_qs.exclude(pk=instance.pk)

    category_avg = history_qs.filter(category=category).aggregate(avg=Avg("amount"))["avg"] or 0.0
    overall_avg = history_qs.aggregate(avg=Avg("amount"))["avg"] or 0.0
    recent_emotional_count = history_qs.filter(
        transaction_date__gte=timezone.localdate() - timedelta(days=7),
        is_emotional=True,
    ).count()
    stress_score = _recent_stress_score(user)

    score = 0.0
    reasons: list[str] = []

    if category in DISCRETIONARY_CATEGORIES:
        score += 0.25
        reasons.append("category is discretionary")

    comparison_base = category_avg or overall_avg
    if comparison_base and amount >= comparison_base * 1.35:
        score += 0.25
        reasons.append("ticket size is above your normal pattern")

    text = f"{merchant} {description}".upper()
    if any(keyword in text for keyword in EMOTIONAL_KEYWORDS):
        score += 0.15
        reasons.append("merchant pattern resembles impulse-oriented spending")

    if stress_score >= 6.5:
        score += 0.2
        reasons.append("recent behavioral stress is elevated")

    if recent_emotional_count >= 2:
        score += 0.1
        reasons.append("similar emotional spends appeared recently")

    if transaction_date and getattr(transaction_date, "weekday", lambda: 0)() >= 4 and category in DISCRETIONARY_CATEGORIES:
        score += 0.05
        reasons.append("timing matches weekend discretionary behavior")

    confidence = _clamp((base_confidence * 0.45) + (score * 0.75), 0.05, 0.99)
    is_emotional = base_emotional or score >= 0.45
    reason = "; ".join(reasons[:3]) if reasons else "behavior pattern stays within your normal range"

    return {
        "is_emotional": is_emotional,
        "confidence": round(confidence, 3),
        "reason": reason,
    }


def _recent_stress_score(user) -> float:
    try:
        signals = list(
            BehavioralSignal.objects.filter(user=user).order_by("-timestamp").values_list("stress_score", flat=True)[:7]
        )
    except Exception:
        return 0.0

    if not signals:
        return 0.0
    return mean(float(value or 0) for value in signals)


def _build_ai_summary(*, amount: float, direction: str, counterparty: str, company_name: str, category: str, payment_mode: str, emotional: bool, emotion_reason: str) -> str:
    actor = company_name or counterparty or "an unknown counterparty"
    verb = "Received" if direction == "credit" else "Paid"
    category_label = dict(Expense.CATEGORY_CHOICES).get(category, str(category).replace("_", " ").title())
    summary = f"{verb} INR {amount:,.0f} {'from' if direction == 'credit' else 'to'} {actor} via {payment_mode}."
    summary += f" ALFRED classified it as {category_label.lower()}."
    if emotional and direction == "debit":
        summary += f" Emotional-spend signal is elevated because {emotion_reason}."
    return summary[:255]


def _infer_company_name(counterparty: str, raw_text: str) -> str:
    text = f"{counterparty} {raw_text}".upper()
    for keyword, company in KNOWN_COMPANIES.items():
        if keyword in text:
            return company
    cleaned = " ".join(part for part in str(counterparty).replace("/", " ").replace("-", " ").split() if len(part) > 1)
    return cleaned[:255]


def _normalize_account_number(value: str) -> str:
    return "".join(char for char in str(value or "") if char.isalnum())


def _normalize_reference(value: str) -> str:
    return "".join(char for char in str(value or "").upper() if char.isalnum())


def _normalize_description(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", str(value or "").upper())).strip()


def _should_fill(field: str, data: dict, provided_fields: set[str]) -> bool:
    value = data.get(field)
    return field not in provided_fields or value in {None, ""}


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))
