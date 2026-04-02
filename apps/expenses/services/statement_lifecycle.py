from __future__ import annotations

from dataclasses import dataclass
import logging

from django.db import transaction
from django.db.utils import OperationalError
from django.utils import timezone

from alfred_ai.services import record_parser_learning
from apps.loans.services import loan_foreclosure_service, loan_intelligence_service
from apps.reports.models import SystemTicket
from apps.reports.services import operational_logging_service, reporting_service

from ..models import Expense, StatementUpload
from .statement_import import StatementParseResult, parse_bank_statement, summarize_transactions
from .transaction_intelligence import (
    build_user_merchant_profiles,
    build_reference_signature,
    build_transaction_fingerprint,
    enrich_imported_expense,
    remember_transaction_profile,
    resolve_bank_account,
    sync_account_balance,
)


STATEMENT_ACCOUNT_TYPE_MAP = {
    "bank_statement": "savings",
    "credit_card_statement": "credit",
    "loan_statement": "other",
    "investment_statement": "investment",
    "other_statement": "other",
}

STATEMENT_RETRY_MEDIUM_THRESHOLD = 3
STATEMENT_RETRY_HIGH_THRESHOLD = 6

logger = logging.getLogger(__name__)


@dataclass
class StatementLifecycleResult:
    upload: StatementUpload
    bank_account: object | None
    imported_transactions: list
    created_expenses: list[Expense]
    skipped_count: int
    loan_detection: dict
    new_import_count: int
    total_imported_count: int

    @property
    def summary(self) -> dict:
        return summarize_transactions(self.imported_transactions)


def apply_parsed_statement_upload(*, user, parsed: StatementParseResult, statement_kind: str, statement_file=None, existing_upload: StatementUpload | None = None) -> StatementLifecycleResult:
    latest_closing = parsed.transactions[-1].closing_balance if parsed.transactions else None
    bank_account = resolve_bank_account(
        user=user,
        bank_name=parsed.bank_name,
        account_holder=parsed.account_holder,
        account_number=parsed.account_number,
        account_type=STATEMENT_ACCOUNT_TYPE_MAP.get(statement_kind, "other"),
        current_balance=latest_closing,
    )

    with transaction.atomic():
        upload = _save_upload_metadata(
            user=user,
            statement_file=statement_file,
            parsed=parsed,
            statement_kind=statement_kind,
            bank_account=bank_account,
            existing_upload=existing_upload,
        )
        imported_transactions, skipped_count = _import_statement_transactions(
            user=user,
            upload=upload,
            bank_account=bank_account,
            parsed=parsed,
        )
        sync_account_balance(bank_account, latest_closing)
        upload.imported_count = Expense.objects.filter(statement_upload=upload).count()
        upload.save(update_fields=["imported_count"])
        _cleanup_redundant_statement_uploads(upload)
    created_expenses = list(Expense.objects.filter(statement_upload=upload).order_by("transaction_date", "id"))
    loan_detection = {
        "detected_loans": 0,
        "updated_loans": 0,
        "new_payments": 0,
        "review_payments": 0,
    }
    foreclosure_resolutions: list = []

    if created_expenses:
        try:
            loan_detection = loan_intelligence_service.detect_loan_payments(user, expenses=created_expenses)
        except OperationalError:
            logger.warning("Loan detection skipped after statement import because the database was locked.", exc_info=True)
        try:
            foreclosure_resolutions = loan_foreclosure_service.reconcile_pending_foreclosures(user=user, expenses=created_expenses)
        except OperationalError:
            logger.warning("Foreclosure reconciliation skipped after statement import because the database was locked.", exc_info=True)

    if foreclosure_resolutions:
        operational_logging_service.log(
            user=user,
            module="loans",
            category="document",
            scope="loan_closure_document",
            event_type="foreclosure_reconciled_from_statement",
            severity="info",
            document_id=foreclosure_resolutions[0].closure_document_id,
            file_name=foreclosure_resolutions[0].closure_document.file_name,
            message=f"{len(foreclosure_resolutions)} pending foreclosure document(s) were reconciled after statement import.",
            payload={
                "resolved_snapshot_ids": [item.id for item in foreclosure_resolutions],
                "loan_ids": [item.loan_id for item in foreclosure_resolutions],
            },
        )
    if not created_expenses or upload.parser_status != "parsed":
        operational_logging_service.log(
            user=user,
            module="expenses",
            category="document",
            scope="statement_document",
            event_type="metadata_only_import" if not created_expenses else "review_import",
            severity="warning" if not created_expenses else "info",
            document_id=upload.id,
            file_name=upload.file_name,
            message=(
                "Statement upload saved without imported transactions. Metadata was retained for review."
                if not created_expenses
                else "Statement upload completed with parser review flags still attached."
            ),
            payload={
                "parser_status": upload.parser_status,
                "parse_confidence": upload.parse_confidence,
                "bank_name": upload.bank_name,
                "account_number": upload.account_number,
                "parser_notes": parsed.parser_notes,
                "imported_count": len(created_expenses),
            },
        )

    return StatementLifecycleResult(
        upload=upload,
        bank_account=bank_account,
        imported_transactions=imported_transactions,
        created_expenses=created_expenses,
        skipped_count=skipped_count,
        loan_detection=loan_detection,
        new_import_count=len(imported_transactions),
        total_imported_count=len(created_expenses),
    )


def queue_statement_retry(upload: StatementUpload, *, reason: str = "") -> StatementUpload:
    payload = dict(upload.extracted_payload or {})
    retry_state = dict(payload.get("background_retry") or {})
    ocr_progress = dict(payload.get("ocr_progress") or {})
    retry_state.update(
        {
            "state": "queued",
            "queued_at": timezone.now().isoformat(),
            "retry_count": int(retry_state.get("retry_count") or 0),
            "reason": reason or retry_state.get("reason", ""),
            "processed_pages": int(ocr_progress.get("processed_pages") or 0),
            "total_pages": int(ocr_progress.get("total_pages") or 0),
        }
    )
    payload["background_retry"] = retry_state
    upload.extracted_payload = payload
    upload.save(update_fields=["extracted_payload"])
    return upload


def retry_statement_upload(upload: StatementUpload, *, ocr_page_limit: int = 8) -> StatementLifecycleResult | None:
    if not upload.original_file:
        return None

    payload = dict(upload.extracted_payload or {})
    retry_state = dict(payload.get("background_retry") or {})
    retry_state["state"] = "running"
    retry_state["last_attempt_at"] = timezone.now().isoformat()
    retry_state["retry_count"] = int(retry_state.get("retry_count") or 0) + 1
    payload["background_retry"] = retry_state
    upload.extracted_payload = payload
    upload.save(update_fields=["extracted_payload"])

    upload.original_file.open("rb")
    try:
        parsed = parse_bank_statement(
            upload.original_file,
            user=upload.user,
            ocr_page_limit=ocr_page_limit,
            preview_page_limit=min(2, ocr_page_limit),
            enable_isolated_ocr=True,
        )
    finally:
        upload.original_file.close()

    _apply_saved_corrections(parsed, upload.extracted_payload or {})
    result = apply_parsed_statement_upload(
        user=upload.user,
        parsed=parsed,
        statement_kind=(upload.source or parsed.statement_kind or "bank_statement"),
        existing_upload=upload,
    )

    refreshed_payload = dict(result.upload.extracted_payload or {})
    refreshed_retry_state = dict(refreshed_payload.get("background_retry") or {})
    refreshed_retry_state["retry_count"] = retry_state["retry_count"]
    refreshed_retry_state["last_attempt_at"] = retry_state["last_attempt_at"]
    refreshed_retry_state["ocr_page_limit"] = ocr_page_limit
    if parsed.preview_only:
        refreshed_retry_state["state"] = "queued"
        refreshed_retry_state["resolution"] = "partial_ocr_import" if result.new_import_count else "metadata_improved"
        refreshed_retry_state["processed_pages"] = int(parsed.processed_page_count or 0)
        refreshed_retry_state["total_pages"] = int(parsed.total_page_count or 0)
    elif result.new_import_count or result.upload.parser_status == "parsed":
        refreshed_retry_state["state"] = "resolved"
        refreshed_retry_state["resolution"] = "transactions_imported" if result.new_import_count else "metadata_improved"
    elif retry_state["retry_count"] >= 6:
        refreshed_retry_state["state"] = "exhausted"
    else:
        refreshed_retry_state["state"] = "queued"
    refreshed_payload["background_retry"] = refreshed_retry_state
    result.upload.extracted_payload = refreshed_payload
    result.upload.save(update_fields=["extracted_payload"])
    record_parser_learning(
        user=upload.user,
        scope="statement_document",
        filename=result.upload.file_name,
        detected_type=result.upload.source or parsed.statement_kind or "bank_statement",
        text=parsed.source_text,
        field_names=[key for key, value in refreshed_payload.items() if value not in ("", None, 0, [], {})],
        parser_status=result.upload.parser_status,
        confidence=result.upload.parse_confidence,
        from_retry=True,
        accepted_fields=list((refreshed_payload.get("accepted_corrections") or {}).keys()),
        resolution=refreshed_retry_state.get("resolution", ""),
    )
    if not result.new_import_count and int(result.upload.imported_count or 0) == 0:
        _create_statement_retry_ticket_if_needed(
            upload=result.upload,
            retry_state=refreshed_retry_state,
            ocr_page_limit=ocr_page_limit,
        )
    return result


def delete_statement_upload(upload: StatementUpload) -> None:
    bank_account = upload.bank_account
    with transaction.atomic():
        Expense.objects.filter(statement_upload=upload).delete()
        upload.delete()

    if bank_account is None:
        return

    latest_expense = (
        Expense.objects.filter(bank_account=bank_account, closing_balance__isnull=False)
        .order_by("-transaction_date", "-id")
        .first()
    )
    if latest_expense is not None:
        sync_account_balance(bank_account, latest_expense.closing_balance)
        return

    if not bank_account.expenses.exists():
        bank_account.current_balance = None
        bank_account.last_synced_at = timezone.now()
        bank_account.save(update_fields=["current_balance", "last_synced_at"])


def _statement_retry_severity(retry_count: int) -> str:
    if retry_count >= STATEMENT_RETRY_HIGH_THRESHOLD:
        return "high"
    if retry_count >= STATEMENT_RETRY_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _create_statement_retry_ticket_if_needed(*, upload: StatementUpload, retry_state: dict, ocr_page_limit: int) -> None:
    retry_count = int(retry_state.get("retry_count") or 0)
    title = f"statement_document retry {retry_count} still needs review"
    if SystemTicket.objects.filter(user=upload.user, module="expenses", title=title).exists():
        return

    severity = _statement_retry_severity(retry_count)
    ticket = reporting_service.create_system_ticket(
        user=upload.user,
        module="expenses",
        title=title,
        summary=(
            f"Statement retry {retry_count} still did not populate structured transactions for {upload.file_name}. "
            f"Parser status is {upload.parser_status} at {round(float(upload.parse_confidence or 0) * 100)}% confidence."
        ),
        context_payload={
            "severity": severity,
            "requires_developer": severity == "high",
            "retry_sub_ticket": True,
            "retry_count": retry_count,
            "document_scope": "statement_document",
            "document_id": upload.id,
            "file_name": upload.file_name,
            "parser_status": upload.parser_status,
            "parse_confidence": round(float(upload.parse_confidence or 0), 4),
            "ocr_page_limit": ocr_page_limit,
            "background_retry": retry_state,
            "bank_name": upload.bank_name,
            "account_number": upload.account_number,
            "imported_count": int(upload.imported_count or 0),
            "unresolved_reason": "no_transactions_imported_after_retry",
        },
    )
    operational_logging_service.log(
        user=upload.user,
        module="expenses",
        category="document",
        scope="statement_document",
        event_type="retry_ticket_created",
        severity="error" if severity == "high" else "warning",
        document_id=upload.id,
        file_name=upload.file_name,
        message=f"Created retry ticket {ticket.id} after statement retry {retry_count} stayed unresolved.",
        payload={
            "ticket_id": ticket.id,
            "ticket_status": ticket.status,
            "ticket_severity": ticket.severity,
            "handled_by": ticket.handled_by,
            "retry_count": retry_count,
            "ocr_page_limit": ocr_page_limit,
        },
    )


def _save_upload_metadata(*, user, statement_file, parsed: StatementParseResult, statement_kind: str, bank_account, existing_upload: StatementUpload | None) -> StatementUpload:
    payload = _statement_payload(parsed, statement_kind, existing_upload.extracted_payload if existing_upload else None)
    if existing_upload is not None:
        upload = existing_upload
        upload.bank_account = bank_account
        upload.source = statement_kind
        upload.bank_name = parsed.bank_name
        upload.account_holder = parsed.account_holder
        upload.account_number = parsed.account_number
        upload.institution_name = parsed.bank_name
        upload.statement_start = parsed.statement_start
        upload.statement_end = parsed.statement_end
        upload.parser_status = parsed.parser_status
        upload.parse_confidence = parsed.confidence
        upload.extracted_payload = payload
        upload.save(
            update_fields=[
                "bank_account",
                "source",
                "bank_name",
                "account_holder",
                "account_number",
                "institution_name",
                "statement_start",
                "statement_end",
                "parser_status",
                "parse_confidence",
                "extracted_payload",
            ]
        )
        return upload

    return StatementUpload.objects.create(
        user=user,
        bank_account=bank_account,
        source=statement_kind,
        original_file=statement_file,
        file_name=getattr(statement_file, "name", "statement.pdf"),
        bank_name=parsed.bank_name,
        account_holder=parsed.account_holder,
        account_number=parsed.account_number,
        institution_name=parsed.bank_name,
        statement_start=parsed.statement_start,
        statement_end=parsed.statement_end,
        parser_status=parsed.parser_status,
        parse_confidence=parsed.confidence,
        extracted_payload=payload,
    )


def _statement_payload(parsed: StatementParseResult, statement_kind: str, existing_payload=None) -> dict:
    payload = dict(existing_payload or {})
    payload.update(
        {
            "statement_kind": statement_kind,
            "loan_hints": parsed.loan_hints,
            "parser_notes": parsed.parser_notes,
            "raw_text_excerpt": _compact_statement_excerpt(parsed),
            "preview_only": bool(parsed.preview_only),
            "preview_transaction_count": int(parsed.preview_transaction_count or 0),
            "ocr_progress": {
                "processed_pages": int(parsed.processed_page_count or 0),
                "total_pages": int(parsed.total_page_count or 0),
                "is_partial": bool(parsed.preview_only),
            },
        }
    )
    return payload


def _compact_statement_excerpt(parsed: StatementParseResult) -> str:
    source_text = str(parsed.source_text or "").strip()
    if not source_text:
        return ""

    preserve_transaction_rows = bool(parsed.transactions or parsed.preview_transaction_count)
    line_limit = 22 if preserve_transaction_rows else 12
    char_limit = 1200 if preserve_transaction_rows else 640
    interesting_tokens = (
        "STATEMENT FROM",
        "STATEMENT OF ACCOUNT",
        "ACCOUNT NO",
        "ACCOUNT NUMBER",
        "ACCOUNT HOLDER",
        "CUST ID",
        "VALUE DT",
        "CLOSING BALANCE",
        "DATE NARRATION",
        "HDFC",
        "ICICI",
        "AXIS",
        "SBI",
    )

    compact_lines: list[str] = []
    seen: set[str] = set()
    for raw_line in source_text.splitlines():
        line = " ".join(str(raw_line or "").split())
        if len(line) < 3:
            continue
        if line in seen:
            continue
        if not preserve_transaction_rows and not any(token in line.upper() for token in interesting_tokens):
            continue
        seen.add(line)
        compact_lines.append(line[:220])
        if len(compact_lines) >= line_limit:
            break

    excerpt = "\n".join(compact_lines).strip()
    return excerpt[:char_limit]


def _cleanup_redundant_statement_uploads(upload: StatementUpload) -> None:
    duplicate_candidates = StatementUpload.objects.filter(
        user=upload.user,
        source=upload.source,
        bank_name=upload.bank_name,
        account_number=upload.account_number,
        statement_start=upload.statement_start,
        statement_end=upload.statement_end,
        imported_count=0,
        parser_status__in=["failed", "needs_review"],
    ).exclude(pk=upload.pk)

    current_quality = (1000 if int(upload.imported_count or 0) else 0) + float(upload.parse_confidence or 0)
    for duplicate in duplicate_candidates:
        duplicate_quality = (1000 if int(duplicate.imported_count or 0) else 0) + float(duplicate.parse_confidence or 0)
        if current_quality < duplicate_quality:
            continue
        if duplicate.original_file:
            duplicate.original_file.delete(save=False)
        duplicate.delete()


def _import_statement_transactions(*, user, upload: StatementUpload, bank_account, parsed: StatementParseResult) -> tuple[list, int]:
    if not parsed.transactions:
        return [], 0

    to_create: list[Expense] = []
    imported_transactions = []
    skipped_count = 0
    transaction_dates = {item.transaction_date for item in parsed.transactions}
    existing_expenses = Expense.objects.filter(
        user=user,
        bank_account=bank_account,
        source="bank_statement",
        transaction_date__in=transaction_dates,
    ).values(
        "transaction_fingerprint",
        "transaction_date",
        "amount",
        "direction",
        "external_reference",
        "raw_description",
    )
    existing_fingerprints = {item["transaction_fingerprint"] for item in existing_expenses if item["transaction_fingerprint"]}
    existing_reference_signatures = {
        build_reference_signature(
            transaction_date=item["transaction_date"],
            amount=item["amount"],
            direction=item["direction"],
            external_reference=item["external_reference"],
            raw_description=item["raw_description"],
        )
        for item in existing_expenses
        if item["external_reference"]
    }
    merchant_profiles = build_user_merchant_profiles(user=user)

    for item in parsed.transactions:
        fingerprint = build_transaction_fingerprint(
            bank_account=bank_account,
            transaction_date=item.transaction_date,
            amount=item.amount,
            direction=item.direction,
            external_reference=item.external_reference,
            raw_description=item.raw_description,
            closing_balance=item.closing_balance,
        )
        reference_signature = build_reference_signature(
            transaction_date=item.transaction_date,
            amount=item.amount,
            direction=item.direction,
            external_reference=item.external_reference,
            raw_description=item.raw_description,
        )
        if fingerprint in existing_fingerprints or (reference_signature[3] and reference_signature in existing_reference_signatures):
            skipped_count += 1
            continue
        existing_fingerprints.add(fingerprint)
        if reference_signature[3]:
            existing_reference_signatures.add(reference_signature)

        imported_transactions.append(item)
        enriched = enrich_imported_expense(
            user=user,
            amount=item.amount,
            classification=item.classification,
            category=item.category,
            payment_mode=item.payment_mode,
            merchant=item.merchant,
            description=item.description,
            raw_description=item.raw_description,
            direction=item.direction,
            transaction_date=item.transaction_date,
            external_reference=item.external_reference,
            counterparty=item.counterparty,
            company_name=item.company_name,
            merchant_profiles=merchant_profiles,
        )
        remember_transaction_profile(
            merchant_profiles=merchant_profiles,
            details=enriched,
            direction=enriched["direction"],
        )
        to_create.append(
            Expense(
                user=user,
                bank_account=bank_account,
                statement_upload=upload,
                amount=item.amount,
                classification=enriched["classification"],
                category=enriched["category"],
                payment_mode=enriched["payment_mode"],
                merchant=enriched["merchant"],
                description=enriched["description"],
                raw_description=enriched["raw_description"],
                transaction_date=item.transaction_date,
                direction=enriched["direction"],
                source="bank_statement",
                external_reference=enriched["external_reference"],
                transaction_fingerprint=fingerprint,
                closing_balance=item.closing_balance,
                counterparty=enriched["counterparty"],
                company_name=enriched["company_name"],
                ai_summary=enriched["ai_summary"],
                is_emotional=enriched["is_emotional"],
                model_confidence=enriched["model_confidence"],
            )
        )

    Expense.objects.bulk_create(to_create)
    return imported_transactions, skipped_count


def _apply_saved_corrections(parsed: StatementParseResult, extracted_payload: dict) -> None:
    corrections = dict((extracted_payload or {}).get("accepted_corrections") or {})
    parsed.bank_name = corrections.get("bank_name") or parsed.bank_name
    parsed.account_holder = corrections.get("account_holder") or parsed.account_holder
    parsed.account_number = corrections.get("account_number") or parsed.account_number
    parsed.statement_kind = corrections.get("statement_kind") or parsed.statement_kind
    parsed.parser_notes = " ".join(filter(None, [parsed.parser_notes, corrections.get("review_note", "")])).strip()
