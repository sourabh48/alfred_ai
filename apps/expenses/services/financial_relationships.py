from __future__ import annotations

from collections import Counter, defaultdict
import re

from apps.integrations.models import CreditReportUpload
from apps.loans.models import LoanForeclosureSnapshot
from apps.loans.services.payment_history_access import fetch_payment_history_rows


TRANSFER_KEYWORDS = (
    "TRANSFER",
    "SELF",
    "OWN ACCOUNT",
    "IMPS",
    "NEFT",
    "RTGS",
    "UPI",
)
DISBURSEMENT_KEYWORDS = (
    "DISBURSE",
    "DISBURSEMENT",
    "SANCTION",
    "LOAN CREDIT",
)
PART_PAYMENT_KEYWORDS = (
    "PART PAYMENT",
    "PARTPAY",
    "PREPAY",
    "PRE-PAY",
    "TOP UP",
)
ACCOUNT_TYPE_TOKENS = {
    "personal loan": "personal",
    "home loan": "home",
    "housing loan": "home",
    "mortgage": "home",
    "car loan": "car",
    "auto loan": "car",
    "education loan": "education",
    "student loan": "education",
    "business loan": "business",
    "loan against property": "other",
    "credit card": "credit_card",
}
CITY_TO_STATE_COUNTRY = {
    "bengaluru": ("Karnataka", "India"),
    "bangalore": ("Karnataka", "India"),
    "mumbai": ("Maharashtra", "India"),
    "pune": ("Maharashtra", "India"),
    "hyderabad": ("Telangana", "India"),
    "chennai": ("Tamil Nadu", "India"),
    "delhi": ("Delhi", "India"),
    "gurugram": ("Haryana", "India"),
    "gurgaon": ("Haryana", "India"),
    "noida": ("Uttar Pradesh", "India"),
    "kolkata": ("West Bengal", "India"),
    "san francisco": ("California", "United States"),
    "new york": ("New York", "United States"),
    "austin": ("Texas", "United States"),
}
STATE_TO_COUNTRY = {
    "karnataka": "India",
    "maharashtra": "India",
    "telangana": "India",
    "tamil nadu": "India",
    "delhi": "India",
    "haryana": "India",
    "uttar pradesh": "India",
    "west bengal": "India",
    "california": "United States",
    "new york": "United States",
    "texas": "United States",
}
COUNTRY_ALIASES = {
    "india": "India",
    "united states": "United States",
    "usa": "United States",
    "us": "United States",
    "united kingdom": "United Kingdom",
    "uk": "United Kingdom",
    "canada": "Canada",
    "australia": "Australia",
    "remote": "Remote",
    "worldwide": "Remote",
    "global": "Remote",
}


def build_financial_relationships(*, user, expenses, loans) -> tuple[dict, dict[int, list[dict]]]:
    bureau_context = _bureau_account_context(user=user, loans=loans)
    payment_rows = fetch_payment_history_rows(
        user=user,
        require_expense_reference=True,
        include_loan_fields=True,
    )
    snapshots = list(
        LoanForeclosureSnapshot.objects.select_related("loan")
        .filter(loan__user=user)
        .order_by("-updated_at", "-id")
    )
    foreclosure_by_expense_id = {}
    for snapshot in snapshots:
        for transaction_id in snapshot.matched_closure_transaction_ids or []:
            foreclosure_by_expense_id[int(transaction_id)] = snapshot

    events: list[dict] = []
    transaction_index: dict[int, list[dict]] = defaultdict(list)
    transfer_transaction_ids: set[int] = set()
    expenses_by_id = {item.id: item for item in expenses}

    for event in _detect_self_transfers(expenses):
        events.append(event)
        for transaction_id in event["transaction_ids"]:
            transfer_transaction_ids.add(transaction_id)
        _index_event(transaction_index, event)

    for event in _build_loan_payment_events(
        payment_rows=payment_rows,
        expenses_by_id=expenses_by_id,
        foreclosure_by_expense_id=foreclosure_by_expense_id,
        bureau_accounts=bureau_context["matched_accounts_by_loan_id"],
    ):
        events.append(event)
        _index_event(transaction_index, event)

    for event in _detect_loan_disbursements(
        expenses=expenses,
        loans=loans,
        bureau_accounts=bureau_context["matched_accounts_by_loan_id"],
        excluded_transaction_ids=transfer_transaction_ids,
    ):
        events.append(event)
        _index_event(transaction_index, event)

    events.sort(key=lambda item: (item.get("date", ""), item.get("confidence", 0), item.get("amount", 0)), reverse=True)
    relation_counts = Counter(item["relation_type"] for item in events)
    payload = {
        "summary": {
            "tracked_events": len(events),
            "self_transfers": relation_counts.get("self_transfer", 0),
            "loan_disbursements": relation_counts.get("loan_disbursement", 0),
            "loan_repayments": relation_counts.get("loan_repayment", 0),
            "loan_part_payments": relation_counts.get("loan_part_payment", 0),
            "loan_closure_payments": relation_counts.get("loan_closure_payment", 0),
            "bureau_accounts": len(bureau_context["accounts"]),
            "bureau_accounts_linked": sum(1 for item in bureau_context["accounts"] if item.get("matched_loan_id")),
        },
        "bureau_report": bureau_context["report"],
        "bureau_accounts": bureau_context["accounts"],
        "events": events[:16],
    }
    return payload, transaction_index


def _bureau_account_context(*, user, loans) -> dict:
    uploads = CreditReportUpload.objects.filter(user=user).order_by("-created_at", "-id")
    selected_upload = None
    raw_accounts = []
    for upload in uploads[:6]:
        candidate_accounts = list((upload.extracted_payload or {}).get("loan_accounts") or [])
        if candidate_accounts:
            selected_upload = upload
            raw_accounts = candidate_accounts
            break

    accounts = []
    matched_accounts_by_loan_id = {}
    for account in raw_accounts:
        normalized = _normalize_bureau_account(account)
        loan, match_basis, match_confidence = _match_bureau_account_to_loan(normalized, loans)
        normalized.update(
            {
                "matched_loan_id": getattr(loan, "id", None),
                "matched_lender": getattr(loan, "lender", ""),
                "match_basis": match_basis,
                "match_confidence": round(match_confidence, 2),
            }
        )
        if loan and loan.id not in matched_accounts_by_loan_id:
            matched_accounts_by_loan_id[loan.id] = normalized
        accounts.append(normalized)

    report = {
        "source_upload_id": getattr(selected_upload, "id", None),
        "bureau": getattr(selected_upload, "bureau", ""),
        "report_date": selected_upload.report_date.isoformat() if getattr(selected_upload, "report_date", None) else "",
        "file_name": getattr(selected_upload, "file_name", ""),
    }
    return {
        "report": report,
        "accounts": accounts,
        "matched_accounts_by_loan_id": matched_accounts_by_loan_id,
    }


def _normalize_bureau_account(account: dict) -> dict:
    location = _parse_location(account.get("branch_location", "") or account.get("location", ""))
    return {
        "lender_name": str(account.get("lender_name", "") or "").strip(),
        "loan_account_number": str(account.get("loan_account_number", "") or "").strip(),
        "account_last4": _digits_last4(account.get("loan_account_number", "")),
        "account_type": str(account.get("account_type", "") or "").strip(),
        "account_type_category": _loan_category(account.get("account_type", "")),
        "status": str(account.get("status", "") or "").strip() or "unknown",
        "opened_on": str(account.get("opened_on", "") or "").strip(),
        "closed_on": str(account.get("closed_on", "") or "").strip(),
        "sanctioned_amount": round(float(account.get("sanctioned_amount") or 0), 2),
        "current_balance": round(float(account.get("current_balance") or 0), 2),
        "emi_amount": round(float(account.get("emi_amount") or 0), 2),
        "overdue_amount": round(float(account.get("overdue_amount") or 0), 2),
        "payment_status": str(account.get("payment_status", "") or "").strip(),
        "country": location["country"],
        "state": location["state"],
        "city": location["city"],
    }


def _match_bureau_account_to_loan(account: dict, loans) -> tuple[object | None, str, float]:
    best_loan = None
    best_basis = ""
    best_score = 0.0
    account_last4 = account.get("account_last4", "")
    account_lender = _normalize_text(account.get("lender_name", ""))
    account_category = account.get("account_type_category", "")
    account_balance = float(account.get("current_balance") or 0)
    for loan in loans:
        score = 0.0
        reasons = []
        if account_last4 and account_last4 == _digits_last4(loan.loan_account_number):
            score += 0.55
            reasons.append("account_last4")
        if account_lender and account_lender and account_lender in _normalize_text(loan.lender):
            score += 0.3
            reasons.append("lender")
        if account_category and account_category == loan.loan_type:
            score += 0.1
            reasons.append("loan_type")
        if account_balance and loan.remaining_balance and abs(account_balance - float(loan.remaining_balance or 0)) <= max(account_balance, loan.remaining_balance) * 0.35:
            score += 0.08
            reasons.append("balance")
        if score > best_score:
            best_loan = loan
            best_basis = ", ".join(reasons)
            best_score = score
    return (best_loan, best_basis, best_score) if best_score >= 0.35 else (None, "", 0.0)


def _detect_self_transfers(expenses) -> list[dict]:
    debits = [item for item in expenses if item.direction == "debit" and _looks_like_transfer(item)]
    credits = [item for item in expenses if item.direction == "credit" and _looks_like_transfer(item)]
    used_credit_ids: set[int] = set()
    events = []

    for debit in sorted(debits, key=lambda item: (item.transaction_date, item.id), reverse=True):
        best_credit = None
        best_score = 0.0
        best_evidence = []
        for credit in credits:
            if credit.id in used_credit_ids:
                continue
            if abs((debit.transaction_date - credit.transaction_date).days) > 2:
                continue
            if abs(float(debit.amount or 0) - float(credit.amount or 0)) > 1:
                continue
            score = 0.56
            evidence = ["Opposite-direction transactions share the same amount within a two-day window."]
            debit_reference = _normalize_reference(debit.external_reference)
            credit_reference = _normalize_reference(credit.external_reference)
            if debit_reference and debit_reference == credit_reference:
                score += 0.22
                evidence.append("External reference matches on both sides of the transfer.")
            if debit.bank_account_id and credit.bank_account_id and debit.bank_account_id != credit.bank_account_id:
                score += 0.12
                evidence.append("Transactions hit different tracked bank accounts.")
            if _normalize_text(debit.counterparty or debit.merchant) and _normalize_text(debit.counterparty or debit.merchant) == _normalize_text(credit.counterparty or credit.merchant):
                score += 0.08
                evidence.append("Counterparty labeling is consistent across the transfer pair.")
            if score > best_score:
                best_credit = credit
                best_score = score
                best_evidence = evidence
        if best_credit is None or best_score < 0.72:
            continue
        used_credit_ids.add(best_credit.id)
        events.append(
            {
                "relationship_id": f"self-transfer-{debit.id}-{best_credit.id}",
                "relation_type": "self_transfer",
                "title": "Self transfer across tracked accounts",
                "status": "linked",
                "confidence": round(min(best_score, 0.97), 2),
                "review_required": False,
                "amount": round(float(debit.amount or 0), 2),
                "date": max(debit.transaction_date, best_credit.transaction_date).isoformat(),
                "loan_id": None,
                "loan_account_number": "",
                "lender": "",
                "transaction_ids": [debit.id, best_credit.id],
                "transaction_fingerprints": [debit.transaction_fingerprint, best_credit.transaction_fingerprint],
                "external_references": [value for value in [debit.external_reference, best_credit.external_reference] if value],
                "components": {},
                "source_records": ["transactions"],
                "evidence": best_evidence,
            }
        )
    return events


def _build_loan_payment_events(
    *,
    payment_rows,
    expenses_by_id: dict[int, object],
    foreclosure_by_expense_id: dict[int, object],
    bureau_accounts: dict[int, dict],
) -> list[dict]:
    events = []
    for payment in payment_rows:
        expense = expenses_by_id.get(payment.get("expense_reference_id"))
        if expense is None:
            continue
        snapshot = foreclosure_by_expense_id.get(expense.id)
        relation_type = "loan_repayment"
        title = "Loan repayment"
        evidence = ["Transaction is already linked to loan payment history."]
        if snapshot is not None:
            relation_type = "loan_closure_payment"
            title = "Loan closure payment"
            evidence.append("The transaction is linked to a reconciled foreclosure snapshot.")
        elif _is_part_payment(payment=payment, expense=expense):
            relation_type = "loan_part_payment"
            title = "Loan part payment"
            evidence.append("Payment exceeds the normal EMI band or contains part-payment keywords.")
        bureau_account = bureau_accounts.get(payment.get("loan_id"))
        if bureau_account:
            evidence.append("Latest uploaded bureau report carries a matching loan account for this loan.")
        events.append(
            {
                "relationship_id": f"{relation_type}-{payment.get('id')}",
                "relation_type": relation_type,
                "title": title,
                "status": "linked",
                "confidence": round(max(float(payment.get("detection_confidence") or 0) / 100, 0.7), 2),
                "review_required": payment.get("match_status") == "review",
                "amount": round(float(payment.get("amount") or 0), 2),
                "date": payment.get("payment_date").isoformat(),
                "loan_id": payment.get("loan_id"),
                "loan_account_number": payment.get("loan__loan_account_number", ""),
                "lender": payment.get("loan__lender", ""),
                "transaction_ids": [expense.id],
                "transaction_fingerprints": [expense.transaction_fingerprint],
                "external_references": [value for value in [expense.external_reference, payment.get("matched_reference")] if value],
                "components": {
                    "principal_paid": round(float(payment.get("principal_paid") or payment.get("principal_component") or 0), 2),
                    "interest_paid": round(float(payment.get("interest_paid") or payment.get("interest_component") or 0), 2),
                    "charges_paid": round(float(payment.get("charges_paid") or 0), 2),
                    "penalties_paid": round(float(payment.get("penalties_paid") or 0), 2),
                    "tax_paid": round(float(payment.get("tax_paid") or 0), 2),
                    "total_paid": round(float(payment.get("amount") or 0), 2),
                },
                "source_records": [item for item in ["loan_payment_history", "foreclosure_snapshot" if snapshot else "", "credit_report" if bureau_account else ""] if item],
                "evidence": evidence,
            }
        )
    return events


def _detect_loan_disbursements(*, expenses, loans, bureau_accounts: dict[int, dict], excluded_transaction_ids: set[int]) -> list[dict]:
    credit_transactions = [item for item in expenses if item.direction == "credit" and item.id not in excluded_transaction_ids]
    events = []
    used_ids: set[int] = set()
    for expense in sorted(credit_transactions, key=lambda item: (item.transaction_date, item.id), reverse=True):
        if expense.id in used_ids:
            continue
        best_loan = None
        best_score = 0.0
        best_evidence = []
        for loan in loans:
            score = 0.0
            evidence = []
            day_gap = abs((expense.transaction_date - loan.start_date).days)
            if day_gap <= 15:
                score += 0.24
                evidence.append("Transaction date lines up with the tracked loan start window.")
            if loan.principal and float(expense.amount or 0) >= loan.principal * 0.4 and float(expense.amount or 0) <= loan.principal * 1.05:
                score += 0.26
                evidence.append("Credit amount fits the recorded loan principal band.")
            if _expense_mentions_loan(expense, loan):
                score += 0.24
                evidence.append("Transaction text references the lender or loan account.")
            if _looks_like_disbursement(expense):
                score += 0.12
                evidence.append("Transaction text contains loan disbursement keywords.")
            bureau_account = bureau_accounts.get(loan.id)
            if bureau_account:
                opened_on = bureau_account.get("opened_on", "")
                if opened_on and abs((_coerce_date(opened_on) - expense.transaction_date).days) <= 30:
                    score += 0.08
                    evidence.append("Uploaded bureau report shows a matching account opened in the same period.")
                elif bureau_account.get("matched_loan_id") == loan.id:
                    score += 0.05
                    evidence.append("Uploaded bureau report includes the same loan account.")
            if score > best_score:
                best_loan = loan
                best_score = score
                best_evidence = evidence
        if best_loan is None or best_score < 0.65:
            continue
        used_ids.add(expense.id)
        events.append(
            {
                "relationship_id": f"loan-disbursement-{expense.id}",
                "relation_type": "loan_disbursement",
                "title": "Loan disbursement",
                "status": "linked",
                "confidence": round(min(best_score, 0.95), 2),
                "review_required": best_score < 0.78,
                "amount": round(float(expense.amount or 0), 2),
                "date": expense.transaction_date.isoformat(),
                "loan_id": best_loan.id,
                "loan_account_number": best_loan.loan_account_number,
                "lender": best_loan.lender,
                "transaction_ids": [expense.id],
                "transaction_fingerprints": [expense.transaction_fingerprint],
                "external_references": [value for value in [expense.external_reference] if value],
                "components": {"disbursed_amount": round(float(expense.amount or 0), 2)},
                "source_records": [item for item in ["transactions", "credit_report" if bureau_accounts.get(best_loan.id) else ""] if item],
                "evidence": best_evidence,
            }
        )
    return events


def _index_event(transaction_index: dict[int, list[dict]], event: dict) -> None:
    for transaction_id in event.get("transaction_ids", []):
        transaction_index[transaction_id].append(
            {
                "relationship_id": event.get("relationship_id", ""),
                "relation_type": event.get("relation_type", ""),
                "title": event.get("title", ""),
                "confidence": event.get("confidence", 0),
                "loan_id": event.get("loan_id"),
                "lender": event.get("lender", ""),
                "related_transaction_ids": [item for item in event.get("transaction_ids", []) if item != transaction_id],
            }
        )


def _is_part_payment(*, payment, expense) -> bool:
    text = _expense_text(expense)
    if any(keyword in text for keyword in PART_PAYMENT_KEYWORDS):
        return True
    emi = float(payment.get("loan__emi") or 0)
    return bool(emi and float(payment.get("amount") or 0) >= max(emi * 1.2, emi + 750))


def _looks_like_transfer(expense) -> bool:
    text = _expense_text(expense)
    return any(keyword in text for keyword in TRANSFER_KEYWORDS)


def _looks_like_disbursement(expense) -> bool:
    text = _expense_text(expense)
    return any(keyword in text for keyword in DISBURSEMENT_KEYWORDS)


def _expense_mentions_loan(expense, loan) -> bool:
    text = _expense_text(expense)
    lender = _normalize_text(loan.lender)
    account_last4 = _digits_last4(loan.loan_account_number)
    return bool((lender and lender in text) or (account_last4 and account_last4 in text))


def _expense_text(expense) -> str:
    return _normalize_text(
        " ".join(
            str(value)
            for value in [
                expense.merchant,
                expense.description,
                expense.raw_description,
                expense.counterparty,
                expense.company_name,
                expense.external_reference,
            ]
            if value
        )
    )


def _parse_location(value: str) -> dict:
    raw = str(value or "").strip()
    if not raw:
        return {"country": "", "state": "", "city": ""}
    normalized = raw.lower()
    if any(token in normalized for token in ("remote", "worldwide", "global", "anywhere")):
        return {"country": "Remote", "state": "", "city": ""}
    parts = [item.strip() for item in re.split(r"[,/|]", raw) if item.strip()]
    city = ""
    state = ""
    country = ""
    for part in parts:
        lowered = part.lower()
        if lowered in COUNTRY_ALIASES:
            country = COUNTRY_ALIASES[lowered]
            continue
        if lowered in STATE_TO_COUNTRY:
            state = part.title()
            country = country or STATE_TO_COUNTRY[lowered]
            continue
        if lowered in CITY_TO_STATE_COUNTRY:
            city = part.title()
            mapped_state, mapped_country = CITY_TO_STATE_COUNTRY[lowered]
            state = state or mapped_state
            country = country or mapped_country
    if not city:
        for city_name, (mapped_state, mapped_country) in CITY_TO_STATE_COUNTRY.items():
            if city_name in normalized:
                city = city_name.title()
                state = state or mapped_state
                country = country or mapped_country
                break
    return {"country": country, "state": state, "city": city}


def _loan_category(value: str) -> str:
    normalized = str(value or "").lower()
    for token, category in ACCOUNT_TYPE_TOKENS.items():
        if token in normalized:
            return category
    return "other"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9 ]", " ", str(value or "").upper())).strip()


def _normalize_reference(value: str) -> str:
    return "".join(char for char in str(value or "").upper() if char.isalnum())


def _digits_last4(value: str) -> str:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits[-4:] if digits else ""


def _coerce_date(value: str):
    from datetime import date

    for separator in ("-", "/"):
        parts = str(value or "").split(separator)
        if len(parts) == 3:
            try:
                if len(parts[0]) == 4:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except ValueError:
                continue
    return date.min
