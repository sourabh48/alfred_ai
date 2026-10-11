from math import isfinite
import re

from django.db import migrations, models


def _amount(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return round(result, 2) if isfinite(result) and result >= 0 else None


def _identity(account):
    number = re.sub(r"[^A-Z0-9]", "", str(account.get("loan_account_number") or "").upper())
    lender = " ".join(re.sub(r"[^A-Z0-9]", " ", str(account.get("lender_name") or "").upper()).split())
    return (number, lender) if number and lender else None


def _supports_retained_terms(loan, raw_account, sync_account):
    balance = _amount(raw_account.get("current_balance"))
    # Before this migration the parser encoded an absent balance as zero.
    # Positive retained raw values prove presence; zero needs the new explicit
    # provenance. A successful identity match alone never confirms amounts.
    if balance is None or not (
        raw_account.get("balance_reported") is True
        if "balance_reported" in raw_account else balance > 0
    ):
        return False
    if balance != _amount(sync_account.get("current_balance")) or balance != _amount(loan.remaining_balance):
        return False
    emi = _amount(raw_account.get("emi_amount", 0))
    principal = _amount(raw_account.get("sanctioned_amount")) or balance
    return (
        principal > 0 and principal == _amount(loan.principal)
        and emi is not None and emi == _amount(loan.emi)
        and _amount(loan.interest_rate) == 0
    )


def backfill_verification(apps, schema_editor):
    Loan = apps.get_model("loans", "Loan")
    Report = apps.get_model("integrations", "CreditReportUpload")
    alias = schema_editor.connection.alias
    # No amounts, lifecycle state, payment rows, or source documents are changed.
    # A matched payment alone never establishes the guessed loan terms.
    Loan.objects.using(alias).filter(auto_detected=True, verification_source="user", verified_at=None).update(
        verification_status="needs_review", verification_source="legacy_inference",
    )
    reports = Report.objects.using(alias).filter(
        parser_status__in=["parsed", "needs_review"], parse_confidence__gte=.65,
    ).order_by("updated_at", "pk")
    for report in reports.iterator():
        payload = report.extracted_payload
        sync = payload.get("loan_sync", {}) if isinstance(payload, dict) else {}
        accounts = sync.get("accounts", []) if isinstance(sync, dict) else []
        raw_accounts = payload.get("loan_accounts", []) if isinstance(payload, dict) else []
        if not isinstance(accounts, list) or not isinstance(raw_accounts, list):
            continue
        for account in accounts:
            if not isinstance(account, dict):
                continue
            if account.get("verification_status") not in {"verified", "no_change"}:
                continue
            if account.get("action") not in {"created", "updated", "verified"}:
                continue
            confidence = account.get("match_confidence")
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not .65 <= confidence <= 1:
                continue
            loan_id = account.get("matched_loan_id")
            if not isinstance(loan_id, int) or isinstance(loan_id, bool):
                continue
            loan = Loan.objects.using(alias).filter(
                pk=loan_id, user_id=report.user_id, auto_detected=True,
                verification_source__in=["legacy_inference", "bureau"],
            ).first()
            identity = _identity(account)
            if loan is None or identity is None or identity != _identity({
                "loan_account_number": loan.loan_account_number, "lender_name": loan.lender,
            }):
                continue
            raw_matches = [raw for raw in raw_accounts if isinstance(raw, dict) and _identity(raw) == identity]
            if len(raw_matches) != 1 or not _supports_retained_terms(loan, raw_matches[0], account):
                continue
            Loan.objects.using(alias).filter(pk=loan.pk).update(
                verification_status="confirmed", verification_source="bureau", verified_at=report.updated_at,
            )


class Migration(migrations.Migration):
    dependencies = [
        ("loans", "0012_loanpaymenthistory_review_state"),
        ("integrations", "0004_creditreportupload"),
    ]

    operations = [
        migrations.AddField(
            model_name="loan", name="verification_status",
            field=models.CharField(max_length=20, default="confirmed", choices=[
                ("estimated", "Estimated - needs review"), ("needs_review", "Needs review"),
                ("confirmed", "Confirmed"),
            ]),
        ),
        migrations.AddField(
            model_name="loan", name="verification_source",
            field=models.CharField(max_length=30, default="user", choices=[
                ("user", "User recorded"), ("emi_pattern", "Recurring payment estimate"),
                ("legacy_inference", "Legacy inferred record"), ("bureau", "Bureau report"),
            ]),
        ),
        migrations.AddField(
            model_name="loan", name="verified_at", field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.RunPython(backfill_verification, migrations.RunPython.noop),
    ]
