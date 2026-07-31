from __future__ import annotations

from datetime import date

from django.utils import timezone

from apps.loans.models import Loan


ACCOUNT_TYPE_TO_LOAN_TYPE = {
    "personal loan": "personal",
    "home loan": "home",
    "housing loan": "home",
    "mortgage": "home",
    "car loan": "car",
    "auto loan": "car",
    "vehicle loan": "car",
    "education loan": "education",
    "student loan": "education",
    "business loan": "business",
    "credit card": "credit_card",
}
ACTIVE_STATUS_TOKENS = ("active", "open", "current", "standard", "regular")
CLOSED_STATUS_TOKENS = (
    "closed",
    "settled",
    "written off",
    "written-off",
    "foreclosed",
    "pre-closed",
    "preclosed",
    "paid",
)


def sync_credit_report_loans(*, user, report_upload) -> dict:
    raw_accounts = list((report_upload.extracted_payload or {}).get("loan_accounts") or [])
    if report_upload.parser_status not in {"parsed", "needs_review"} or report_upload.parse_confidence < 0.65 or not raw_accounts:
        return {
            "processed_accounts": 0,
            "matched_loans": 0,
            "updated_loans": 0,
            "closed_loans": 0,
            "created_loans": 0,
            "created_active_loans": 0,
            "created_closed_loans": 0,
            "review_items": 0,
            "skipped_accounts": 0,
            "accounts": [],
            "unmatched_internal_loans": [],
            "summary": "Loan sync skipped because the bureau report did not contain enough verified tradeline detail.",
        }

    loans = list(Loan.objects.filter(user=user).order_by("-start_date", "-id"))
    normalized_accounts = [_normalize_account(item) for item in raw_accounts]
    processed = []
    matched_loan_ids: set[int] = set()
    updated_count = 0
    closed_count = 0
    created_loans: list[Loan] = []
    review_count = 0
    skipped_count = 0

    for account in normalized_accounts:
        matched_loan, match_score, match_basis = _match_account_to_loan(account=account, loans=loans)
        if matched_loan and match_score >= 0.65:
            sync_result = _apply_account_to_existing_loan(
                loan=matched_loan,
                account=account,
                report_upload=report_upload,
            )
            matched_loan_ids.add(matched_loan.id)
            if sync_result["action"] == "review":
                review_count += 1
            else:
                if sync_result["updated"]:
                    updated_count += 1
                if sync_result["closed"]:
                    closed_count += 1
            processed.append(
                {
                    **_serialize_account_for_payload(account),
                    "action": sync_result["action"],
                    "verification_status": sync_result["verification_status"],
                    "matched_loan_id": matched_loan.id,
                    "match_confidence": round(match_score, 2),
                    "match_basis": match_basis,
                    "notes": sync_result["notes"],
                }
            )
            continue

        if _can_create_loan_from_account(account):
            created = _create_loan_from_account(
                user=user,
                account=account,
                report_upload=report_upload,
            )
            loans.append(created)
            created_loans.append(created)
            matched_loan_ids.add(created.id)
            processed.append(
                {
                    **_serialize_account_for_payload(account),
                    "action": "created",
                    "verification_status": "verified",
                    "matched_loan_id": created.id,
                    "match_confidence": 0.88,
                    "match_basis": "created_from_bureau_tradeline",
                    "notes": "Created a new internal loan record from the uploaded bureau tradeline.",
                }
            )
        else:
            skipped_count += 1
            review_count += 1
            processed.append(
                {
                    **_serialize_account_for_payload(account),
                    "action": "review",
                    "verification_status": "needs_review",
                    "matched_loan_id": None,
                    "match_confidence": round(match_score, 2),
                    "match_basis": match_basis,
                    "notes": "Tradeline could not be linked or created safely from the available bureau fields.",
                }
            )

    unmatched_internal_loans = []
    for loan in loans:
        if loan.id in matched_loan_ids:
            continue
        if loan.status in {"foreclosed", "closed", "prepaid"}:
            continue
        unmatched_internal_loans.append(
            {
                "loan_id": loan.id,
                "lender": loan.lender,
                "loan_account_number": loan.loan_account_number,
                "status": loan.status,
                "remaining_balance": round(float(loan.remaining_balance or 0), 2),
                "note": "Internal loan not confirmed in the latest uploaded bureau report.",
            }
        )

    created_active = sum(1 for loan in created_loans if loan.is_active)
    created_closed = sum(1 for loan in created_loans if not loan.is_active)
    matched_count = sum(1 for item in processed if item["action"] in {"updated", "verified", "review"})
    summary = (
        f"Processed {len(normalized_accounts)} bureau tradeline(s): "
        f"{matched_count} matched, {updated_count} updated, {closed_count} closed, "
        f"{len(created_loans)} created, {review_count} review item(s)."
    )
    return {
        "processed_accounts": len(normalized_accounts),
        "matched_loans": matched_count,
        "updated_loans": updated_count,
        "closed_loans": closed_count,
        "created_loans": len(created_loans),
        "created_active_loans": created_active,
        "created_closed_loans": created_closed,
        "review_items": review_count,
        "skipped_accounts": skipped_count,
        "accounts": processed,
        "unmatched_internal_loans": unmatched_internal_loans[:8],
        "summary": summary,
    }


def _normalize_account(account: dict) -> dict:
    status_value = _normalize_status(
        status=str(account.get("status", "") or ""),
        current_balance=float(account.get("current_balance") or 0),
        closed_on=str(account.get("closed_on", "") or ""),
    )
    account_type = str(account.get("account_type", "") or "").strip()
    return {
        "lender_name": str(account.get("lender_name", "") or "").strip(),
        "loan_account_number": str(account.get("loan_account_number", "") or "").strip(),
        "account_last4": _digits_last4(account.get("loan_account_number", "")),
        "account_type": account_type,
        "loan_type": _loan_type_from_account_type(account_type),
        "status": status_value,
        "status_raw": str(account.get("status", "") or "").strip(),
        "opened_on": _coerce_date(str(account.get("opened_on", "") or "").strip()),
        "closed_on": _coerce_date(str(account.get("closed_on", "") or "").strip()),
        "sanctioned_amount": round(float(account.get("sanctioned_amount") or 0), 2),
        "current_balance": round(float(account.get("current_balance") or 0), 2),
        "emi_amount": round(float(account.get("emi_amount") or 0), 2),
        "overdue_amount": round(float(account.get("overdue_amount") or 0), 2),
        "payment_status": str(account.get("payment_status", "") or "").strip(),
    }


def _match_account_to_loan(*, account: dict, loans: list[Loan]) -> tuple[Loan | None, float, str]:
    best_loan = None
    best_score = 0.0
    best_basis = ""
    lender_key = _normalize_text(account.get("lender_name", ""))
    account_last4 = account.get("account_last4", "")
    loan_type = account.get("loan_type", "")
    current_balance = float(account.get("current_balance") or 0)
    opened_on = account.get("opened_on")
    for loan in loans:
        score = 0.0
        reasons = []
        loan_last4 = _digits_last4(loan.loan_account_number)
        if account_last4 and loan_last4 and account_last4 == loan_last4:
            score += 0.58
            reasons.append("account_last4")
        loan_lender = _normalize_text(loan.lender)
        if lender_key and loan_lender and (lender_key in loan_lender or loan_lender in lender_key):
            score += 0.24
            reasons.append("lender")
        if loan_type and loan_type == loan.loan_type:
            score += 0.1
            reasons.append("loan_type")
        if current_balance and loan.remaining_balance is not None and abs(current_balance - float(loan.remaining_balance or 0)) <= max(current_balance, float(loan.remaining_balance or 0), 1) * 0.35:
            score += 0.05
            reasons.append("balance")
        if opened_on and loan.start_date and abs((opened_on - loan.start_date).days) <= 120:
            score += 0.04
            reasons.append("start_date")
        if score > best_score:
            best_loan = loan
            best_score = score
            best_basis = ", ".join(reasons)
    return best_loan, best_score, best_basis


def _apply_account_to_existing_loan(*, loan: Loan, account: dict, report_upload) -> dict:
    if account["status"] == "active" and loan.status in {"closed", "foreclosed", "prepaid"}:
        note = "Bureau tradeline shows the account as active, but the internal loan is already closed. Review before reopening."
        _append_sync_note(loan=loan, report_upload=report_upload, note=note)
        return {
            "action": "review",
            "verification_status": "needs_review",
            "updated": False,
            "closed": False,
            "notes": note,
        }

    changed_fields: list[str] = []
    closed = False

    if account["lender_name"] and account["lender_name"] != loan.lender:
        loan.lender = account["lender_name"]
        changed_fields.append("lender")
    if account["loan_type"] and loan.loan_type == "other" and account["loan_type"] != "other":
        loan.loan_type = account["loan_type"]
        changed_fields.append("loan_type")
    if account["sanctioned_amount"] > 0 and (loan.auto_detected or loan.principal <= 1):
        loan.principal = account["sanctioned_amount"]
        changed_fields.append("principal")
    if account["emi_amount"] > 0 and (loan.auto_detected or float(loan.emi or 0) <= 0):
        loan.emi = account["emi_amount"]
        changed_fields.append("emi")
    if account["opened_on"] and loan.auto_detected and loan.start_date != account["opened_on"]:
        loan.start_date = account["opened_on"]
        changed_fields.append("start_date")

    if account["status"] == "closed":
        if loan.status != "closed":
            loan.status = "closed"
            changed_fields.append("status")
        if loan.is_active:
            loan.is_active = False
            changed_fields.append("is_active")
        if float(loan.remaining_balance or 0) != 0:
            loan.remaining_balance = 0.0
            changed_fields.append("remaining_balance")
        closed_on = account["closed_on"] or report_upload.report_date or timezone.localdate()
        if loan.closed_on != closed_on:
            loan.closed_on = closed_on
            changed_fields.append("closed_on")
        if loan.closure_reason != "bureau_report_verified":
            loan.closure_reason = "bureau_report_verified"
            changed_fields.append("closure_reason")
        closed = True
    else:
        if loan.status == "active" and account["current_balance"] > 0 and float(loan.remaining_balance or 0) != account["current_balance"]:
            loan.remaining_balance = account["current_balance"]
            changed_fields.append("remaining_balance")
        if loan.closed_on is not None and loan.status == "active":
            loan.closed_on = None
            changed_fields.append("closed_on")
        if not loan.is_active and loan.status not in {"closed", "foreclosed", "prepaid"}:
            loan.is_active = True
            changed_fields.append("is_active")

    sync_note = (
        f"Bureau sync from {report_upload.file_name}: "
        f"status {account['status']}, balance INR {account['current_balance']:,.0f}, "
        f"sanctioned INR {account['sanctioned_amount']:,.0f}."
    )
    if _append_sync_note(loan=loan, report_upload=report_upload, note=sync_note):
        changed_fields.append("notes")

    verification_status = "verified" if changed_fields else "no_change"
    if changed_fields:
        loan.save(update_fields=sorted(set(changed_fields + ["updated_at"])))
        return {
            "action": "updated",
            "verification_status": verification_status,
            "updated": True,
            "closed": closed,
            "notes": sync_note,
        }
    return {
        "action": "verified",
        "verification_status": verification_status,
        "updated": False,
        "closed": closed,
        "notes": "Tradeline matched an existing loan and confirmed the current internal state.",
    }


def _create_loan_from_account(*, user, account: dict, report_upload) -> Loan:
    principal = account["sanctioned_amount"] or account["current_balance"] or max(account["emi_amount"] * 12, 1)
    emi = account["emi_amount"] or 0.0
    tenure_months = max(int(round(principal / emi)) if emi > 0 else 12, 1)
    start_date = account["opened_on"] or report_upload.report_date or timezone.localdate()
    closed_on = account["closed_on"] if account["status"] == "closed" else None
    is_active = account["status"] == "active"
    remaining_balance = account["current_balance"] if is_active else 0.0
    note = (
        f"Created from uploaded bureau report {report_upload.file_name}. "
        f"Reported status {account['status']} with balance INR {account['current_balance']:,.0f}."
    )
    return Loan.objects.create(
        user=user,
        loan_type=account["loan_type"],
        lender=account["lender_name"],
        loan_account_number=account["loan_account_number"] or (f"XXXX{account['account_last4']}" if account["account_last4"] else ""),
        principal=principal,
        interest_rate=0.0,
        emi=emi,
        tenure_months=tenure_months,
        remaining_balance=remaining_balance,
        start_date=start_date,
        closed_on=closed_on,
        is_active=is_active,
        status="active" if is_active else "closed",
        closure_reason="bureau_report_verified" if not is_active else "",
        auto_detected=True,
        notes=note,
    )


def _append_sync_note(*, loan: Loan, report_upload, note: str) -> bool:
    prefix = f"[Bureau sync #{report_upload.id}]"
    line = f"{prefix} {note}"
    current_notes = str(loan.notes or "").strip()
    if line in current_notes:
        return False
    loan.notes = f"{current_notes}\n{line}".strip() if current_notes else line
    return True


def _can_create_loan_from_account(account: dict) -> bool:
    has_identity = bool(account["lender_name"] and (account["account_last4"] or account["loan_account_number"]))
    has_financial_signal = bool(account["sanctioned_amount"] > 0 or account["current_balance"] > 0 or account["emi_amount"] > 0)
    return has_identity and has_financial_signal


def _loan_type_from_account_type(value: str) -> str:
    normalized = str(value or "").lower()
    for token, loan_type in ACCOUNT_TYPE_TO_LOAN_TYPE.items():
        if token in normalized:
            return loan_type
    return "other"


def _normalize_status(*, status: str, current_balance: float, closed_on: str) -> str:
    normalized = str(status or "").strip().lower()
    if any(token in normalized for token in CLOSED_STATUS_TOKENS):
        return "closed"
    if any(token in normalized for token in ACTIVE_STATUS_TOKENS):
        return "active"
    if closed_on:
        return "closed"
    if current_balance > 0:
        return "active"
    return "closed"


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").upper().replace("&", " ").replace("-", " ").split())


def _digits_last4(value: str) -> str:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return digits[-4:] if digits else ""


def _coerce_date(value: str) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    for separator in ("-", "/"):
        parts = raw.split(separator)
        if len(parts) != 3:
            continue
        try:
            if len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
            return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except ValueError:
            continue
    return None


def _serialize_account_for_payload(account: dict) -> dict:
    serialized = dict(account)
    for key in ("opened_on", "closed_on"):
        value = serialized.get(key)
        if isinstance(value, date):
            serialized[key] = value.isoformat()
    return serialized
