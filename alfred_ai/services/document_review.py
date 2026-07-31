from __future__ import annotations

from datetime import date
import json
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from alfred_ai.services import record_parser_correction, record_parser_learning
from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume
from apps.career.services import job_intelligence, resume_intelligence
from apps.expenses.models import StatementUpload
from apps.expenses.services.statement_lifecycle import delete_statement_upload, queue_statement_retry, retry_statement_upload
from apps.integrations.models import CreditReportUpload, CreditScore
from apps.integrations.services.credit_report_parser import credit_report_parser
from apps.integrations.views import _persist_uploaded_credit_score
from apps.investments.models import Investment, InvestmentImportDocument
from apps.investments.services import portfolio_intelligence_service
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument
from apps.loans.services.loan_pdf_parser import loan_pdf_parser
from apps.loans.services import loan_foreclosure_service
from apps.loans.services.loan_closure_parser import loan_closure_parser
from apps.mobility.models import BikeDocument, BikeServiceRecord
from apps.mobility.services import bike_document_ai, bike_service_intelligence, build_document_payload, build_service_record_payload, merge_nested_payload
from apps.reports.models import SystemTicket
from apps.reports.services import operational_logging_service, reporting_service


REVIEW_CONFIDENCE_THRESHOLD = 0.72
RETRY_TICKET_MEDIUM_THRESHOLD = 3
RETRY_TICKET_HIGH_THRESHOLD = 6
PARSER_STATUS_RANK = {
    "failed": 0,
    "pending": 0,
    "needs_review": 1,
    "parsed": 2,
}

SCOPE_MODULE_MAP = {
    "statement_document": "expenses",
    "loan_document": "loans",
    "loan_closure_document": "loans",
    "investment_document": "investments",
    "vehicle_document": "mobility",
    "resume_document": "career",
    "recruiter_document": "career",
    "credit_report": "general",
}

REVIEW_FIELD_SCHEMAS = {
    "statement_document": [
        {"name": "bank_name", "label": "Institution", "type": "text"},
        {"name": "account_holder", "label": "Account Holder", "type": "text"},
        {"name": "account_number", "label": "Account Number", "type": "text"},
        {"name": "statement_start", "label": "Statement Start", "type": "date"},
        {"name": "statement_end", "label": "Statement End", "type": "date"},
        {"name": "statement_kind", "label": "Statement Type", "type": "text"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "loan_document": [
        {"name": "document_type", "label": "Document Type", "type": "text"},
        {"name": "lender", "label": "Lender", "type": "text"},
        {"name": "loan_type", "label": "Loan Type", "type": "text"},
        {"name": "loan_account_number", "label": "Loan Account Number", "type": "text"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "loan_closure_document": [
        {"name": "loan_account_number", "label": "Loan Account Number", "type": "text"},
        {"name": "closure_amount", "label": "Closure Amount", "type": "number"},
        {"name": "closure_date", "label": "Closure Date", "type": "date"},
        {"name": "matched_keyword", "label": "Matched Keyword", "type": "text"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "investment_document": [
        {"name": "broker_name", "label": "Broker / Institution", "type": "text"},
        {"name": "asset_name", "label": "Primary Asset Name", "type": "text"},
        {"name": "asset_type", "label": "Primary Asset Type", "type": "text"},
        {"name": "account_number", "label": "Account / Folio", "type": "text"},
        {"name": "invested_amount", "label": "Invested Amount", "type": "number"},
        {"name": "current_value", "label": "Current Value", "type": "number"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "vehicle_document": [
        {"name": "document_type", "label": "Document Type", "type": "text"},
        {"name": "issuer", "label": "Issuer", "type": "text"},
        {"name": "document_number", "label": "Document Number", "type": "text"},
        {"name": "vehicle_number", "label": "Vehicle Number", "type": "text"},
        {"name": "issue_date", "label": "Issue Date", "type": "date"},
        {"name": "expiry_date", "label": "Expiry Date", "type": "date"},
        {"name": "service_date", "label": "Service Date", "type": "date"},
        {"name": "service_center", "label": "Service Center", "type": "text"},
        {"name": "service_type", "label": "Service Type", "type": "text"},
        {"name": "odometer_km", "label": "Odometer", "type": "number"},
        {"name": "cost", "label": "Service Cost", "type": "number"},
        {"name": "next_service_date", "label": "Next Service Date", "type": "date"},
        {"name": "next_service_km", "label": "Next Service Km", "type": "number"},
        {"name": "extracted_work_summary", "label": "Work Summary", "type": "text"},
        {"name": "parts_items", "label": "Parts Items JSON", "type": "json"},
        {"name": "labour_items", "label": "Labour Items JSON", "type": "json"},
        {"name": "customer_voice_items", "label": "Customer Voice JSON", "type": "json"},
        {"name": "systems_impacted", "label": "Impacted Systems JSON", "type": "json"},
        {"name": "total_customer_amount", "label": "Total Customer Amount", "type": "number"},
        {"name": "parts_customer_amount", "label": "Parts Customer Amount", "type": "number"},
        {"name": "labour_customer_amount", "label": "Labour Customer Amount", "type": "number"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "resume_document": [
        {"name": "role", "label": "Role", "type": "text"},
        {"name": "experience_years", "label": "Experience Years", "type": "number"},
        {"name": "skills", "label": "Skills", "type": "text"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "recruiter_document": [
        {"name": "job_title", "label": "Role Title", "type": "text"},
        {"name": "company", "label": "Company", "type": "text"},
        {"name": "location", "label": "Location", "type": "text"},
        {"name": "experience_years", "label": "Experience Years", "type": "number"},
        {"name": "salary_min", "label": "Salary Min", "type": "number"},
        {"name": "salary_max", "label": "Salary Max", "type": "number"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
    "credit_report": [
        {"name": "bureau", "label": "Bureau", "type": "text"},
        {"name": "applicant_name", "label": "Applicant Name", "type": "text"},
        {"name": "report_number", "label": "Report Number", "type": "text"},
        {"name": "report_date", "label": "Report Date", "type": "date"},
        {"name": "review_note", "label": "Review Note", "type": "text"},
    ],
}

REVIEW_GENERIC_FIELD_ALIASES = {
    "statement_document": {
        "date": ["statement_start", "statement_end"],
        "document_date": ["statement_start", "statement_end"],
    },
    "loan_document": {
        "account_number": ["loan_account_number"],
    },
    "loan_closure_document": {
        "account_number": ["loan_account_number"],
        "amount": ["closure_amount"],
        "date": ["closure_date"],
        "document_date": ["closure_date"],
    },
    "investment_document": {
        "amount": ["invested_amount", "current_value"],
    },
    "vehicle_document": {
        "amount": ["cost", "total_customer_amount"],
        "date": ["issue_date", "service_date", "expiry_date", "next_service_date"],
        "document_date": ["issue_date", "service_date", "expiry_date", "next_service_date"],
        "invoice_number": ["document_number"],
        "policy_number": ["document_number"],
        "registration_number": ["vehicle_number"],
    },
    "recruiter_document": {
        "amount": ["salary_min", "salary_max"],
    },
    "credit_report": {
        "date": ["report_date"],
        "document_date": ["report_date"],
    },
}


def _log_document_event(
    *,
    user,
    module: str,
    scope: str,
    event_type: str,
    severity: str,
    message: str,
    document_id: int,
    file_name: str,
    payload: dict | None = None,
):
    operational_logging_service.log(
        user=user,
        module=module,
        category="document",
        scope=scope,
        event_type=event_type,
        severity=severity,
        document_id=document_id,
        file_name=file_name,
        message=message,
        payload=payload,
    )


def _retry_payload(payload: dict | None, *, state: str, reason: str = "", resolution: str = "", retry_count: int | None = None) -> dict:
    normalized = dict(payload or {})
    background = dict(normalized.get("background_retry") or {})
    background["state"] = state
    background["last_attempt_at"] = timezone.now().isoformat()
    background["retry_count"] = int(retry_count if retry_count is not None else (background.get("retry_count") or 0))
    if reason:
        background["reason"] = reason
    if resolution:
        background["resolution"] = resolution
    normalized["background_retry"] = background
    return normalized


def _mark_review_queue_resolved(payload: dict | None, *, resolution: str = "accepted_correction") -> dict:
    normalized = dict(payload or {})
    normalized["review_queue_resolved"] = True
    normalized["review_queue_resolved_at"] = timezone.now().isoformat()
    normalized["review_queue_resolution"] = resolution
    return normalized


def _begin_retry_payload(payload: dict | None, *, reason: str = "manual_review_retry") -> tuple[dict, dict]:
    normalized = dict(payload or {})
    background = dict(normalized.get("background_retry") or {})
    background["state"] = "running"
    background["reason"] = reason
    background["last_attempt_at"] = timezone.now().isoformat()
    background["retry_count"] = int(background.get("retry_count") or 0) + 1
    normalized["background_retry"] = background
    return normalized, background


def _retry_ticket_severity(retry_count: int) -> str:
    if retry_count >= RETRY_TICKET_HIGH_THRESHOLD:
        return "high"
    if retry_count >= RETRY_TICKET_MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _create_retry_ticket_if_needed(
    *,
    user,
    scope: str,
    document_id: int,
    file_name: str,
    retry_count: int,
    parser_status: str,
    parse_confidence: float,
    summary: str,
    unresolved_reason: str,
    payload: dict | None = None,
):
    if parser_status == "parsed":
        return None

    module = SCOPE_MODULE_MAP.get(scope, "general")
    title = f"{scope} retry {retry_count} still needs review"
    if SystemTicket.objects.filter(user=user, module=module, title=title).exists():
        return None

    severity = _retry_ticket_severity(int(retry_count or 0))
    ticket = reporting_service.create_system_ticket(
        user=user,
        module=module,
        title=title,
        summary=summary,
        context_payload={
            "severity": severity,
            "requires_developer": severity == "high",
            "retry_sub_ticket": True,
            "retry_count": int(retry_count or 0),
            "document_scope": scope,
            "document_id": document_id,
            "file_name": file_name,
            "parser_status": parser_status,
            "parse_confidence": round(float(parse_confidence or 0), 4),
            "unresolved_reason": unresolved_reason,
            **dict(payload or {}),
        },
    )
    _log_document_event(
        user=user,
        module=module,
        scope=scope,
        event_type="retry_ticket_created",
        severity="error" if severity == "high" else "warning",
        message=f"Created retry ticket {ticket.id} after retry {retry_count} stayed unresolved.",
        document_id=document_id,
        file_name=file_name,
        payload={
            "ticket_id": ticket.id,
            "ticket_status": ticket.status,
            "ticket_severity": ticket.severity,
            "handled_by": ticket.handled_by,
            "retry_count": int(retry_count or 0),
            "unresolved_reason": unresolved_reason,
            **dict(payload or {}),
        },
    )
    return ticket


def _best_status(current: str, candidate: str) -> str:
    return candidate if PARSER_STATUS_RANK.get(candidate, 0) >= PARSER_STATUS_RANK.get(current, 0) else current


def _prefer_value(new_value, old_value):
    return new_value if new_value not in (None, "", [], {}) else old_value


def _merge_non_empty_payload(existing: dict | None, incoming: dict | None) -> dict:
    merged = dict(existing or {})
    for key, value in (incoming or {}).items():
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged


def _apply_resume_profile(user, parsed) -> None:
    profile, _ = CareerProfile.objects.get_or_create(
        user=user,
        defaults={
            "role": "Profile pending",
            "experience_years": 0,
            "skills": "",
            "last_salary": getattr(user, "monthly_income", 0) or 0,
        },
    )
    resume_intelligence.apply_to_profile(profile, parsed)


def build_review_queue(user, *, limit: int = 24) -> list[dict]:
    items = [
        *[_serialize_statement(item) for item in StatementUpload.objects.filter(_review_filter(user)).order_by("-uploaded_at", "-id")[:8]],
        *[_serialize_loan(item) for item in LoanImportDocument.objects.filter(_review_filter(user)).order_by("-created_at", "-id")[:5]],
        *[
            _serialize_loan_closure(item)
            for item in LoanClosureDocument.objects.filter(_review_filter(user, user_lookup="loan__user"))
            .select_related("loan")
            .order_by("-updated_at", "-id")[:4]
        ],
        *[_serialize_investment(item) for item in InvestmentImportDocument.objects.filter(_review_filter(user)).prefetch_related("linked_investments").order_by("-updated_at", "-id")[:4]],
        *[_serialize_vehicle(item) for item in BikeDocument.objects.filter(_review_filter(user)).order_by("-updated_at", "-id")[:5]],
        *[_serialize_resume(item) for item in CareerResume.objects.filter(_review_filter(user)).order_by("-updated_at", "-id")[:3]],
        *[
            _serialize_recruiter(item)
            for item in CareerJobAnalysis.objects.filter(_review_filter(user), extracted_payload__source_kind__in=["recruiter_message", "jd_attachment"])
            .order_by("-updated_at", "-id")[:3]
        ],
        *[_serialize_credit(item) for item in CreditReportUpload.objects.filter(_review_filter(user)).order_by("-updated_at", "-id")[:3]],
    ]
    items.sort(key=lambda item: (item["priority_rank"], item["created_at"]), reverse=True)
    return items[:limit]


def apply_correction(user, *, scope: str, document_id: int, corrections: dict) -> dict:
    normalized = {key: value for key, value in (corrections or {}).items() if value not in (None, "", [])}
    if scope == "statement_document":
        item = _apply_statement_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="expenses",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for a statement document.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "loan_document":
        item = _apply_loan_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="loans",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for a loan document.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "loan_closure_document":
        item = _apply_loan_closure_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="loans",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for a loan closure document.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "investment_document":
        item = _apply_investment_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="investments",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for an investment import document.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "vehicle_document":
        item = _apply_vehicle_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="mobility",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for a vehicle document.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "resume_document":
        item = _apply_resume_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="career",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for a resume document.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "recruiter_document":
        item = _apply_recruiter_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="career",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for recruiter or JD intake.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    if scope == "credit_report":
        item = _apply_credit_correction(user, document_id, normalized)
        _log_document_event(
            user=user,
            module="integrations",
            scope=scope,
            event_type="accepted_correction",
            severity="info",
            message="Accepted a user correction for a credit report.",
            document_id=document_id,
            file_name=item["file_name"],
            payload={"fields": sorted(normalized.keys())},
        )
        return item
    raise ValueError("Unsupported review scope.")


def delete_document(user, *, scope: str, document_id: int) -> None:
    if scope == "statement_document":
        upload = StatementUpload.objects.get(user=user, pk=document_id)
        file_name = upload.file_name
        delete_statement_upload(upload)
        _log_document_event(
            user=user,
            module="expenses",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a statement upload and its linked imported expenses.",
            document_id=document_id,
            file_name=file_name,
        )
        return

    if scope == "loan_document":
        document = LoanImportDocument.objects.get(user=user, pk=document_id)
        file_name = document.file_name
        linked_loans = list(document.linked_loans.all())
        document.delete()
        for loan in linked_loans:
            if loan.source_documents.exists() or loan.payment_history.exists() or loan.closure_documents.exists():
                continue
            loan.delete()
        _log_document_event(
            user=user,
            module="loans",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a loan document and cleaned up orphan loan rows where safe.",
            document_id=document_id,
            file_name=file_name,
            payload={"linked_loans": len(linked_loans)},
        )
        return

    if scope == "loan_closure_document":
        document = LoanClosureDocument.objects.select_related("loan").get(loan__user=user, pk=document_id)
        file_name = document.file_name
        loan = document.loan
        document.delete()
        _log_document_event(
            user=user,
            module="loans",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a loan closure document from the review history.",
            document_id=document_id,
            file_name=file_name,
            payload={"loan_id": loan.id},
        )
        return

    if scope == "investment_document":
        document = InvestmentImportDocument.objects.prefetch_related("linked_investments").get(user=user, pk=document_id)
        file_name = document.file_name
        linked_investments = list(document.linked_investments.all())
        document.delete()
        for investment in linked_investments:
            if investment.source_documents.exists():
                continue
            investment.delete()
        _log_document_event(
            user=user,
            module="investments",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted an investment import document and cleaned up orphan imported holdings where safe.",
            document_id=document_id,
            file_name=file_name,
            payload={"linked_investments": len(linked_investments)},
        )
        return

    if scope == "vehicle_document":
        document = BikeDocument.objects.get(user=user, pk=document_id)
        file_name = document.document_title or document.document_file.name.split("/")[-1]
        deleted_services = BikeServiceRecord.objects.filter(source_document=document).count()
        BikeServiceRecord.objects.filter(source_document=document).delete()
        document.delete()
        _log_document_event(
            user=user,
            module="mobility",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a vehicle document and removed linked imported service history where tracked.",
            document_id=document_id,
            file_name=file_name,
            payload={"deleted_service_records": deleted_services},
        )
        return

    if scope == "resume_document":
        resume = CareerResume.objects.get(user=user, pk=document_id)
        file_name = resume.file_name
        resume.delete()
        _log_document_event(
            user=user,
            module="career",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a resume document from the career intake history.",
            document_id=document_id,
            file_name=file_name,
        )
        return

    if scope == "recruiter_document":
        analysis = CareerJobAnalysis.objects.get(user=user, pk=document_id)
        file_name = analysis.source_document_name or analysis.job_title or analysis.source_name or "recruiter intake"
        analysis.delete()
        _log_document_event(
            user=user,
            module="career",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a recruiter or JD intake item from the review history.",
            document_id=document_id,
            file_name=file_name,
        )
        return

    if scope == "credit_report":
        upload = CreditReportUpload.objects.get(user=user, pk=document_id)
        file_name = upload.file_name
        score = upload.parsed_credit_score
        upload.delete()
        if score:
            score.factors.all().delete()
            score.delete()
        _log_document_event(
            user=user,
            module="integrations",
            scope=scope,
            event_type="delete_document",
            severity="info",
            message="Deleted a credit report upload and its linked parsed score where present.",
            document_id=document_id,
            file_name=file_name,
            payload={"deleted_score": bool(score)},
        )
        return

    raise ValueError("Unsupported delete scope.")


def retry_review_item(user, *, scope: str, document_id: int) -> dict:
    if scope == "statement_document":
        return _retry_statement_document(user, document_id)
    if scope == "loan_document":
        return _retry_loan_document(user, document_id)
    if scope == "loan_closure_document":
        return _retry_loan_closure_document(user, document_id)
    if scope == "investment_document":
        return _retry_investment_document(user, document_id)
    if scope == "vehicle_document":
        return _retry_vehicle_document(user, document_id)
    if scope == "resume_document":
        return _retry_resume_document(user, document_id)
    if scope == "recruiter_document":
        return _retry_recruiter_document(user, document_id)
    if scope == "credit_report":
        return _retry_credit_report(user, document_id)
    raise ValueError("Unsupported retry scope.")


def _retry_statement_document(user, document_id: int) -> dict:
    upload = StatementUpload.objects.get(user=user, pk=document_id)
    queue_statement_retry(upload, reason="manual_review_retry")
    result = retry_statement_upload(upload, ocr_page_limit=12)
    serialized = _serialize_statement(result.upload if result is not None else upload)
    retry_state = dict((serialized.get("background_retry") or {}))
    severity = "info" if serialized["parser_status"] == "parsed" or (result and result.new_import_count) else "warning"
    _log_document_event(
        user=user,
        module="expenses",
        scope="statement_document",
        event_type="retry_document",
        severity=severity,
        message=(
            "Retried a statement document and populated imported transactions."
            if result and result.new_import_count
            else "Retried a statement document. Metadata was preserved for further review."
        ),
        document_id=document_id,
        file_name=serialized["file_name"],
        payload={
            "parser_status": serialized["parser_status"],
            "parse_confidence": serialized["parse_confidence"],
            "imported_count": serialized["fields"].get("imported_count", 0),
        },
    )
    unresolved = not (result and result.new_import_count) and serialized["fields"].get("imported_count", 0) == 0
    if unresolved:
        _create_retry_ticket_if_needed(
            user=user,
            scope="statement_document",
            document_id=document_id,
            file_name=serialized["file_name"],
            retry_count=int(retry_state.get("retry_count") or 1),
            parser_status=serialized["parser_status"],
            parse_confidence=float(serialized["parse_confidence"] or 0),
            summary=(
                f"Statement retry {int(retry_state.get('retry_count') or 1)} still did not populate structured transactions. "
                f"Current parser status is {serialized['parser_status']} at {round(float(serialized['parse_confidence'] or 0) * 100)}% confidence."
            ),
            unresolved_reason="no_transactions_imported_after_retry",
            payload={
                "imported_count": serialized["fields"].get("imported_count", 0),
                "background_retry": retry_state,
            },
        )
    return serialized


def _retry_loan_document(user, document_id: int) -> dict:
    document = LoanImportDocument.objects.prefetch_related("linked_loans").get(user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(document.extracted_payload)
    document.extracted_payload = payload
    document.save(update_fields=["extracted_payload"])

    document.uploaded_file.open("rb")
    try:
        parsed = loan_pdf_parser.parse_document(document.uploaded_file, user=user, filename=document.file_name)
    finally:
        document.uploaded_file.close()

    created_loans = _upsert_retry_loans(user, parsed.get("loans") or [])
    existing_payload = dict(document.extracted_payload or {})
    updated_payload = _merge_non_empty_payload(
        existing_payload,
        {
            "document_type": parsed.get("document_type") or "",
            "confidence": float(parsed.get("confidence") or 0),
            "loans": parsed.get("loans") or [],
            "extracted_text_excerpt": (parsed.get("extracted_text") or "")[:1500],
        },
    )
    retry_resolution = "loan_rows_updated" if created_loans else "still_needs_review"
    updated_payload = _retry_payload(
        updated_payload,
        state="resolved" if created_loans else "needs_review",
        reason="manual_review_retry",
        resolution=retry_resolution,
        retry_count=retry_state["retry_count"],
    )
    existing_status = document.parser_status
    new_status = "parsed" if created_loans else ("needs_review" if parsed.get("extracted_text") or parsed.get("document_type") not in {"", "other"} else "failed")
    document.document_type = _prefer_value(parsed.get("document_type"), document.document_type)
    document.parse_confidence = max(float(document.parse_confidence or 0), float(parsed.get("confidence") or 0))
    document.parser_status = _best_status(existing_status, new_status)
    document.extracted_text = _prefer_value(parsed.get("extracted_text"), document.extracted_text)
    document.extracted_payload = updated_payload
    if created_loans:
        previous_loans = list(document.linked_loans.all())
        document.summary = f"{len(created_loans)} loan record(s) are now linked to this document after retry."
        document.save(update_fields=["document_type", "parse_confidence", "parser_status", "extracted_text", "extracted_payload", "summary"])
        document.linked_loans.set(created_loans)
        _delete_orphan_loans(previous_loans, created_loans)
    else:
        document.summary = document.summary or "Retry completed, but Alfred still needs review to map structured loan rows."
        document.save(update_fields=["document_type", "parse_confidence", "parser_status", "extracted_text", "extracted_payload", "summary"])
    record_parser_learning(
        user=user,
        scope="loan_document",
        filename=document.file_name,
        detected_type=document.document_type or "other",
        text=document.extracted_text or "",
        field_names=sorted({key for loan in (parsed.get("loans") or []) for key, value in loan.items() if value not in ("", None, 0)}),
        parser_status=document.parser_status,
        confidence=document.parse_confidence,
        from_retry=True,
        accepted_fields=list((document.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=retry_resolution,
    )
    serialized = _serialize_loan(document)
    _log_document_event(
        user=user,
        module="loans",
        scope="loan_document",
        event_type="retry_document",
        severity="info" if created_loans else "warning",
        message=(
            "Retried a loan document and refreshed the linked loan records."
            if created_loans
            else "Retried a loan document, but Alfred still could not populate structured loan rows."
        ),
        document_id=document_id,
        file_name=document.file_name,
        payload={
            "parser_status": document.parser_status,
            "parse_confidence": document.parse_confidence,
            "linked_loans": len(created_loans),
        },
    )
    if not created_loans:
        _create_retry_ticket_if_needed(
            user=user,
            scope="loan_document",
            document_id=document_id,
            file_name=document.file_name,
            retry_count=int(retry_state["retry_count"]),
            parser_status=document.parser_status,
            parse_confidence=float(document.parse_confidence or 0),
            summary=(
                f"Loan document retry {retry_state['retry_count']} still could not populate structured loan rows. "
                f"Detected type is {document.document_type or 'unknown'}."
            ),
            unresolved_reason="no_structured_loan_rows",
            payload={
                "document_type": document.document_type or "",
                "linked_loans": len(created_loans),
            },
        )
    return serialized


def _retry_loan_closure_document(user, document_id: int) -> dict:
    document = LoanClosureDocument.objects.select_related("loan").get(loan__user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(document.extracted_payload)
    document.extracted_payload = payload
    document.save(update_fields=["extracted_payload"])

    document.uploaded_file.open("rb")
    try:
        parsed = loan_closure_parser.parse_document(document.uploaded_file, document.file_name, user=user)
    finally:
        document.uploaded_file.close()

    merged_payload = _merge_non_empty_payload(document.extracted_payload, {**(parsed.get("payload") or {}), "parser_notes": parsed.get("parser_notes", "")})
    verified, notes = loan_closure_parser.verify_document(document.loan, {"payload": merged_payload, "extracted_text": parsed.get("extracted_text") or document.extracted_text})
    retry_resolution = "closure_document_verified" if verified else "still_needs_review"
    merged_payload = _retry_payload(
        merged_payload,
        state="resolved" if verified else "needs_review",
        reason="manual_review_retry",
        resolution=retry_resolution,
        retry_count=retry_state["retry_count"],
    )
    document.extracted_text = _prefer_value(parsed.get("extracted_text"), document.extracted_text)
    document.extracted_payload = merged_payload
    document.parse_confidence = max(float(document.parse_confidence or 0), float(parsed.get("confidence") or 0))
    document.parser_status = _best_status(document.parser_status, parsed.get("parser_status") or "needs_review")
    document.verification_status = "verified" if verified else "rejected"
    document.verification_notes = notes
    document.closure_amount = float(merged_payload.get("closure_amount") or document.closure_amount or 0)
    document.closure_date = _parse_date(merged_payload.get("closure_date")) or document.closure_date
    document.save(
        update_fields=[
            "extracted_text",
            "extracted_payload",
            "parse_confidence",
            "parser_status",
            "verification_status",
            "verification_notes",
            "closure_amount",
            "closure_date",
            "updated_at",
        ]
    )
    snapshot = loan_foreclosure_service.sync_snapshot_from_document(document)
    if verified:
        loan_foreclosure_service.reconcile_snapshot(snapshot)
    record_parser_learning(
        user=user,
        scope="loan_closure_document",
        filename=document.file_name,
        detected_type="loan_closure_document",
        text=document.extracted_text or "",
        field_names=[key for key, value in (merged_payload or {}).items() if value not in ("", None, 0)],
        parser_status=document.parser_status,
        confidence=document.parse_confidence,
        from_retry=True,
        accepted_fields=list((document.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=retry_resolution,
    )
    serialized = _serialize_loan_closure(document)
    _log_document_event(
        user=user,
        module="loans",
        scope="loan_closure_document",
        event_type="retry_document",
        severity="info" if verified else "warning",
        message=(
            "Retried a loan closure document and verified the closure linkage."
            if verified
            else "Retried a loan closure document, but it still needs review before Alfred can trust the foreclosure match."
        ),
        document_id=document_id,
        file_name=document.file_name,
        payload={
            "parser_status": document.parser_status,
            "parse_confidence": document.parse_confidence,
            "verification_status": document.verification_status,
        },
    )
    if not verified:
        _create_retry_ticket_if_needed(
            user=user,
            scope="loan_closure_document",
            document_id=document_id,
            file_name=document.file_name,
            retry_count=int(retry_state["retry_count"]),
            parser_status=document.parser_status,
            parse_confidence=float(document.parse_confidence or 0),
            summary=(
                f"Loan closure document retry {retry_state['retry_count']} still could not verify the foreclosure/no-due match for loan {document.loan_id}."
            ),
            unresolved_reason="loan_closure_still_needs_review",
            payload={"loan_id": document.loan_id, "verification_status": document.verification_status},
        )
    return serialized


def _retry_investment_document(user, document_id: int) -> dict:
    document = InvestmentImportDocument.objects.prefetch_related("linked_investments").get(user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(document.extracted_payload)
    document.extracted_payload = payload
    document.save(update_fields=["extracted_payload"])

    document.uploaded_file.open("rb")
    try:
        parsed = portfolio_intelligence_service.parse_portfolio_document(document.uploaded_file, user=user, filename=document.file_name)
    finally:
        document.uploaded_file.close()

    created_investments = _upsert_retry_investments(user, parsed.get("investments") or [])
    updated_payload = _merge_non_empty_payload(document.extracted_payload, parsed.get("payload") or {})
    retry_resolution = "investment_rows_updated" if created_investments else "still_needs_review"
    updated_payload = _retry_payload(
        updated_payload,
        state="resolved" if created_investments else "needs_review",
        reason="manual_review_retry",
        resolution=retry_resolution,
        retry_count=retry_state["retry_count"],
    )
    previous_investments = list(document.linked_investments.all())
    document.broker_name = _prefer_value(parsed.get("broker"), document.broker_name)
    document.parse_confidence = max(float(document.parse_confidence or 0), float(parsed.get("confidence") or 0))
    document.parser_status = _best_status(document.parser_status, parsed.get("parser_status") or "needs_review")
    document.extracted_text = _prefer_value(parsed.get("extracted_text"), document.extracted_text)
    document.extracted_payload = updated_payload
    document.summary = (
        f"{len(created_investments)} investment record(s) are now linked to this document after retry."
        if created_investments
        else (document.summary or "Retry completed, but Alfred still needs review to map structured investment rows.")
    )
    document.save(update_fields=["broker_name", "parse_confidence", "parser_status", "extracted_text", "extracted_payload", "summary", "updated_at"])
    if created_investments:
        document.linked_investments.set(created_investments)
        _delete_orphan_investments(previous_investments, created_investments)
    record_parser_learning(
        user=user,
        scope="investment_document",
        filename=document.file_name,
        detected_type=(document.broker_name or "portfolio_statement").lower().replace(" ", "_"),
        text=document.extracted_text or "",
        field_names=sorted({key for item in (parsed.get("payload", {}).get("investments") or []) for key, value in item.items() if value not in ("", None, 0)}),
        parser_status=document.parser_status,
        confidence=document.parse_confidence,
        from_retry=True,
        accepted_fields=list((document.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=retry_resolution,
    )
    serialized = _serialize_investment(document)
    _log_document_event(
        user=user,
        module="investments",
        scope="investment_document",
        event_type="retry_document",
        severity="info" if created_investments else "warning",
        message=(
            "Retried an investment document and refreshed the linked holdings."
            if created_investments
            else "Retried an investment document, but Alfred still could not populate structured holdings."
        ),
        document_id=document_id,
        file_name=document.file_name,
        payload={
            "parser_status": document.parser_status,
            "parse_confidence": document.parse_confidence,
            "linked_investments": len(created_investments),
        },
    )
    if not created_investments:
        _create_retry_ticket_if_needed(
            user=user,
            scope="investment_document",
            document_id=document_id,
            file_name=document.file_name,
            retry_count=int(retry_state["retry_count"]),
            parser_status=document.parser_status,
            parse_confidence=float(document.parse_confidence or 0),
            summary=(
                f"Investment document retry {retry_state['retry_count']} still could not populate structured holdings. Broker is {document.broker_name or 'unknown'}."
            ),
            unresolved_reason="no_structured_investment_rows",
            payload={"broker_name": document.broker_name or "", "linked_investments": len(created_investments)},
        )
    return serialized


def _retry_vehicle_document(user, document_id: int) -> dict:
    document = BikeDocument.objects.select_related("bike_profile").get(user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(document.extracted_payload)
    document.extracted_payload = payload
    document.save(update_fields=["extracted_payload"])

    document.document_file.open("rb")
    try:
        parsed = bike_document_ai.parse(document.document_file, document.document_file.name.split("/")[-1], user=user)
    finally:
        document.document_file.close()

    relevance = bike_document_ai.verify_relevance(document.bike_profile, parsed, document.document_type)
    updated_payload = _merge_non_empty_payload(document.extracted_payload, build_document_payload(parsed, relevance))
    updated_payload = _retry_payload(
        updated_payload,
        state="resolved" if parsed.parser_status == "parsed" else "needs_review",
        reason="manual_review_retry",
        resolution="document_reparsed" if parsed.parser_status == "parsed" else "still_needs_review",
        retry_count=retry_state["retry_count"],
    )
    document.document_title = _prefer_value(parsed.title, document.document_title)
    document.issuer = _prefer_value(parsed.fields.get("issuer"), document.issuer)
    document.document_number = _prefer_value(parsed.fields.get("document_number"), document.document_number)
    document.vehicle_number = _prefer_value(parsed.fields.get("vehicle_number"), document.vehicle_number)
    document.issue_date = _parse_date(parsed.fields.get("issue_date")) or document.issue_date
    document.expiry_date = _parse_date(parsed.fields.get("expiry_date")) or document.expiry_date
    amount = parsed.fields.get("amount")
    document.premium_amount = amount if isinstance(amount, (int, float)) and amount else document.premium_amount
    document.parse_confidence = max(float(document.parse_confidence or 0), float(parsed.confidence or 0))
    document.parser_status = _best_status(document.parser_status, parsed.parser_status)
    document.parser_notes = " ".join(filter(None, [parsed.parser_notes, *relevance["reasons"]])).strip() or document.parser_notes
    document.source_text = _prefer_value(parsed.source_text, document.source_text)
    document.extracted_payload = updated_payload
    document.save(
        update_fields=[
            "document_title",
            "issuer",
            "document_number",
            "vehicle_number",
            "issue_date",
            "expiry_date",
            "premium_amount",
            "parse_confidence",
            "parser_status",
            "parser_notes",
            "source_text",
            "extracted_payload",
            "updated_at",
        ]
    )
    bike_service_intelligence.hydrate_document(document)
    _refresh_imported_service_records(document, parsed)
    record_parser_learning(
        user=user,
        scope="vehicle_document",
        filename=document.document_title or document.document_file.name.split("/")[-1],
        detected_type=document.document_type,
        text=document.source_text,
        field_names=[*list((document.extracted_payload or {}).keys()), *list((parsed.service_payload or {}).keys())],
        parser_status=document.parser_status,
        confidence=document.parse_confidence,
        from_retry=True,
        accepted_fields=list((document.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=(document.extracted_payload or {}).get("background_retry", {}).get("resolution", ""),
    )
    serialized = _serialize_vehicle(document)
    _log_document_event(
        user=user,
        module="mobility",
        scope="vehicle_document",
        event_type="retry_document",
        severity="info" if document.parser_status == "parsed" else "warning",
        message=(
            "Retried a vehicle document and refreshed the extracted vehicle fields."
            if document.parser_status == "parsed"
            else "Retried a vehicle document, but it still needs review before Alfred can trust the extracted fields."
        ),
        document_id=document_id,
        file_name=serialized["file_name"],
        payload={
            "parser_status": document.parser_status,
            "parse_confidence": document.parse_confidence,
            "relevance": relevance,
        },
    )
    if document.parser_status != "parsed":
        _create_retry_ticket_if_needed(
            user=user,
            scope="vehicle_document",
            document_id=document_id,
            file_name=serialized["file_name"],
            retry_count=int(retry_state["retry_count"]),
            parser_status=document.parser_status,
            parse_confidence=float(document.parse_confidence or 0),
            summary=(
                f"Vehicle document retry {retry_state['retry_count']} still needs review. "
                f"Relevance score was {round(float(relevance.get('score') or 0) * 100)}%."
            ),
            unresolved_reason="vehicle_document_still_needs_review",
            payload={
                "document_type": document.document_type,
                "relevance_score": relevance.get("score"),
                "relevance_reasons": relevance.get("reasons", []),
            },
        )
    return serialized


def _retry_resume_document(user, document_id: int) -> dict:
    resume = CareerResume.objects.get(user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(resume.extracted_payload)
    resume.extracted_payload = payload
    resume.save(update_fields=["extracted_payload"])

    resume.uploaded_file.open("rb")
    try:
        parsed = resume_intelligence.parse(resume.uploaded_file, resume.file_name, user=user)
    finally:
        resume.uploaded_file.close()

    merged_payload = _merge_non_empty_payload(resume.extracted_payload, parsed.payload)
    merged_payload = _retry_payload(
        merged_payload,
        state="resolved" if parsed.parser_status == "parsed" else "needs_review",
        reason="manual_review_retry",
        resolution="resume_reparsed" if parsed.parser_status == "parsed" else "still_needs_review",
        retry_count=retry_state["retry_count"],
    )
    resume.parse_confidence = max(float(resume.parse_confidence or 0), float(parsed.confidence or 0))
    resume.parser_status = _best_status(resume.parser_status, parsed.parser_status)
    resume.extracted_text = _prefer_value(parsed.extracted_text, resume.extracted_text)
    resume.extracted_payload = merged_payload
    resume.summary = parsed.summary if parsed.summary else resume.summary
    resume.strengths = "\n".join(parsed.strengths) if parsed.strengths else resume.strengths
    resume.weaknesses = "\n".join(parsed.weaknesses) if parsed.weaknesses else resume.weaknesses
    resume.save(
        update_fields=[
            "parse_confidence",
            "parser_status",
            "extracted_text",
            "extracted_payload",
            "summary",
            "strengths",
            "weaknesses",
            "updated_at",
        ]
    )
    resume_intelligence.record_parse_outcome(user, resume.file_name, parsed)
    record_parser_learning(
        user=user,
        scope="resume_document",
        filename=resume.file_name,
        detected_type="resume",
        text=resume.extracted_text,
        field_names=[key for key, value in merged_payload.items() if value not in ("", None, 0, [], {})],
        parser_status=resume.parser_status,
        confidence=resume.parse_confidence,
        from_retry=True,
        accepted_fields=list((resume.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=(resume.extracted_payload or {}).get("background_retry", {}).get("resolution", ""),
    )
    _apply_resume_profile(user, parsed)
    serialized = _serialize_resume(resume)
    _log_document_event(
        user=user,
        module="career",
        scope="resume_document",
        event_type="retry_document",
        severity="info" if resume.parser_status == "parsed" else "warning",
        message=(
            "Retried a resume document and refreshed extracted resume intelligence."
            if resume.parser_status == "parsed"
            else "Retried a resume document, but it still needs review before Alfred can fully use it."
        ),
        document_id=document_id,
        file_name=resume.file_name,
        payload={
            "parser_status": resume.parser_status,
            "parse_confidence": resume.parse_confidence,
            "role": merged_payload.get("role", ""),
            "skills": merged_payload.get("skills", []),
        },
    )
    if resume.parser_status != "parsed":
        _create_retry_ticket_if_needed(
            user=user,
            scope="resume_document",
            document_id=document_id,
            file_name=resume.file_name,
            retry_count=int(retry_state["retry_count"]),
            parser_status=resume.parser_status,
            parse_confidence=float(resume.parse_confidence or 0),
            summary=(
                f"Resume retry {retry_state['retry_count']} still needs review. "
                "Role or skill extraction is not reliable enough yet."
            ),
            unresolved_reason="resume_fields_still_incomplete",
            payload={
                "role": merged_payload.get("role", ""),
                "skill_count": len(merged_payload.get("skills", []) or []),
            },
        )
    return serialized


def _retry_recruiter_document(user, document_id: int) -> dict:
    analysis = CareerJobAnalysis.objects.get(user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(analysis.extracted_payload)
    analysis.extracted_payload = payload
    analysis.save(update_fields=["extracted_payload", "updated_at"])

    combined_text = payload.get("intake_combined_text") or analysis.extracted_text or payload.get("intake_message_text") or ""
    message_text = payload.get("intake_message_text") or combined_text
    snapshot = job_intelligence.parse_recruiter_message(message_text or combined_text)
    parser_status, parse_confidence = _recruiter_parser_state(
        snapshot,
        attachment_present=bool(payload.get("attachment_file_name")),
    )
    resume_payload = _resume_payload_for_job_analysis(user)
    _apply_recruiter_analysis_update(analysis, snapshot, resume_payload=resume_payload)
    analysis.parse_confidence = max(float(analysis.parse_confidence or 0), parse_confidence)
    analysis.parser_status = _best_status(analysis.parser_status, parser_status)
    updated_payload = dict(analysis.extracted_payload or {})
    updated_payload["intake_combined_text"] = snapshot.description or combined_text
    updated_payload["intake_confidence"] = parse_confidence
    retry_resolution = "recruiter_document_reparsed" if analysis.parser_status == "parsed" else "still_needs_review"
    updated_payload = _retry_payload(
        updated_payload,
        state="resolved" if analysis.parser_status == "parsed" else "needs_review",
        reason="manual_review_retry",
        resolution=retry_resolution,
        retry_count=retry_state["retry_count"],
    )
    analysis.extracted_payload = updated_payload
    analysis.save(
        update_fields=[
            "source_name",
            "job_url",
            "apply_url",
            "company",
            "job_title",
            "location",
            "parser_status",
            "parse_confidence",
            "extracted_text",
            "fit_score",
            "strengths",
            "gaps",
            "summary",
            "extracted_payload",
            "updated_at",
        ]
    )
    record_parser_learning(
        user=user,
        scope="recruiter_document",
        filename=analysis.source_document_name or "recruiter_message.txt",
        detected_type=(analysis.extracted_payload or {}).get("source_kind") or "recruiter_message",
        text=analysis.extracted_text or "",
        field_names=[
            *[key for key, value in ((analysis.extracted_payload or {}).get("job_snapshot") or {}).items() if value not in ("", None, 0, [])],
            *list(((analysis.extracted_payload or {}).get("job_snapshot") or {}).get("required_skills", [])[:8]),
        ],
        parser_status=analysis.parser_status,
        confidence=analysis.parse_confidence,
        from_retry=True,
        accepted_fields=list((analysis.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=retry_resolution,
    )
    serialized = _serialize_recruiter(analysis)
    _log_document_event(
        user=user,
        module="career",
        scope="recruiter_document",
        event_type="retry_document",
        severity="info" if analysis.parser_status == "parsed" else "warning",
        message=(
            "Retried recruiter or JD intake and refreshed the extracted role details."
            if analysis.parser_status == "parsed"
            else "Retried recruiter or JD intake, but Alfred still needs review before trusting the extracted fields."
        ),
        document_id=document_id,
        file_name=serialized["file_name"],
        payload={
            "parser_status": analysis.parser_status,
            "parse_confidence": analysis.parse_confidence,
            "job_title": analysis.job_title,
            "company": analysis.company,
        },
    )
    if analysis.parser_status != "parsed":
        _create_retry_ticket_if_needed(
            user=user,
            scope="recruiter_document",
            document_id=document_id,
            file_name=serialized["file_name"],
            retry_count=int(retry_state["retry_count"]),
            parser_status=analysis.parser_status,
            parse_confidence=float(analysis.parse_confidence or 0),
            summary=(
                f"Recruiter intake retry {retry_state['retry_count']} still needs review. "
                f"Role title is {analysis.job_title or 'unknown'} and company is {analysis.company or 'unknown'}."
            ),
            unresolved_reason="recruiter_document_still_needs_review",
            payload={
                "job_title": analysis.job_title,
                "company": analysis.company,
                "source_kind": (analysis.extracted_payload or {}).get("source_kind", "recruiter_message"),
            },
        )
    return serialized


def _retry_credit_report(user, document_id: int) -> dict:
    upload = CreditReportUpload.objects.select_related("parsed_credit_score").get(user=user, pk=document_id)
    payload, retry_state = _begin_retry_payload(upload.extracted_payload)
    upload.extracted_payload = payload
    upload.save(update_fields=["extracted_payload"])

    upload.uploaded_file.open("rb")
    try:
        parsed = credit_report_parser.parse(upload.uploaded_file, filename=upload.file_name, user=user)
    finally:
        upload.uploaded_file.close()

    merged_payload = _merge_non_empty_payload(
        upload.extracted_payload,
        {**parsed.payload, "bureau": parsed.bureau or parsed.payload.get("bureau", "")},
    )
    merged_payload = _retry_payload(
        merged_payload,
        state="resolved" if parsed.parser_status == "parsed" else "needs_review",
        reason="manual_review_retry",
        resolution="credit_report_reparsed" if parsed.parser_status == "parsed" else "still_needs_review",
        retry_count=retry_state["retry_count"],
    )
    upload.bureau = _prefer_value(parsed.bureau, upload.bureau)
    upload.parse_confidence = max(float(upload.parse_confidence or 0), float(parsed.confidence or 0))
    upload.parser_status = _best_status(upload.parser_status, parsed.parser_status)
    upload.extracted_text = _prefer_value(parsed.extracted_text, upload.extracted_text)
    upload.extracted_payload = merged_payload
    upload.summary = parsed.summary or upload.summary
    upload.parser_notes = " ".join(filter(None, [upload.parser_notes, parsed.parser_notes])).strip()
    upload.applicant_name = _prefer_value(parsed.payload.get("applicant_name"), upload.applicant_name)
    upload.report_number = _prefer_value(parsed.payload.get("report_number"), upload.report_number)
    upload.report_date = _parse_date(parsed.payload.get("report_date")) or upload.report_date
    upload.save(
        update_fields=[
            "bureau",
            "parse_confidence",
            "parser_status",
            "extracted_text",
            "extracted_payload",
            "summary",
            "parser_notes",
            "applicant_name",
            "report_number",
            "report_date",
            "updated_at",
        ]
    )
    if parsed.payload.get("score"):
        _persist_uploaded_credit_score(user, upload, parsed, upload.bureau)
    record_parser_learning(
        user=user,
        scope="credit_report",
        filename=upload.file_name,
        detected_type=upload.bureau or parsed.bureau or "credit_report",
        text=upload.extracted_text,
        field_names=[key for key, value in (upload.extracted_payload or {}).items() if value not in ("", None, 0)],
        parser_status=upload.parser_status,
        confidence=upload.parse_confidence,
        from_retry=True,
        accepted_fields=list((upload.extracted_payload or {}).get("accepted_corrections", {}).keys()),
        resolution=(upload.extracted_payload or {}).get("background_retry", {}).get("resolution", ""),
    )
    serialized = _serialize_credit(upload)
    _log_document_event(
        user=user,
        module="integrations",
        scope="credit_report",
        event_type="retry_document",
        severity="info" if upload.parser_status == "parsed" else "warning",
        message=(
            "Retried a credit report and refreshed the extracted bureau summary."
            if upload.parser_status == "parsed"
            else "Retried a credit report, but it still needs review before Alfred can trust the extracted score details."
        ),
        document_id=document_id,
        file_name=upload.file_name,
        payload={
            "parser_status": upload.parser_status,
            "parse_confidence": upload.parse_confidence,
            "bureau": upload.bureau,
            "score": parsed.payload.get("score") or 0,
        },
    )
    if upload.parser_status != "parsed":
        _create_retry_ticket_if_needed(
            user=user,
            scope="credit_report",
            document_id=document_id,
            file_name=upload.file_name,
            retry_count=int(retry_state["retry_count"]),
            parser_status=upload.parser_status,
            parse_confidence=float(upload.parse_confidence or 0),
            summary=(
                f"Credit report retry {retry_state['retry_count']} still needs review. "
                f"Bureau detection is {upload.bureau or 'unknown'} and score extraction is incomplete."
            ),
            unresolved_reason="credit_report_still_needs_review",
            payload={
                "bureau": upload.bureau or "",
                "score": parsed.payload.get("score") or 0,
            },
        )
    return serialized


def _upsert_retry_loans(user, loans_data: list[dict]) -> list[Loan]:
    created_loans: list[Loan] = []
    if not loans_data:
        return created_loans
    with transaction.atomic():
        for loan_data in loans_data:
            loan_account_number = (loan_data.get("loan_account_number") or "").strip()
            lender = (loan_data.get("lender") or "").strip()
            principal = loan_data.get("principal", 0)

            existing = None
            if loan_account_number:
                existing = Loan.objects.filter(user=user, loan_account_number=loan_account_number).first()
            elif lender and principal:
                existing = Loan.objects.filter(user=user, lender__iexact=lender, principal=principal).first()

            if existing:
                for key, value in loan_data.items():
                    if value not in ("", None, 0):
                        setattr(existing, key, value)
                existing.save()
                created_loans.append(existing)
            else:
                created_loans.append(Loan.objects.create(user=user, **loan_data))
    return created_loans


def _delete_orphan_loans(previous_loans: list[Loan], current_loans: list[Loan]) -> None:
    current_ids = {loan.id for loan in current_loans}
    for loan in previous_loans:
        if loan.id in current_ids:
            continue
        loan.refresh_from_db()
        if loan.source_documents.exists() or loan.payment_history.exists() or loan.closure_documents.exists():
            continue
        loan.delete()


def _upsert_retry_investments(user, investments_data: list[dict]) -> list[Investment]:
    linked: list[Investment] = []
    if not investments_data:
        return linked
    with transaction.atomic():
        for item in investments_data:
            asset_name = (item.get("asset_name") or "").strip()
            institution = (item.get("institution") or "").strip()
            if not asset_name:
                continue
            investment, _ = Investment.objects.update_or_create(
                user=user,
                asset_name=asset_name,
                institution=institution,
                defaults={
                    "asset_type": item.get("asset_type", "equity"),
                    "account_number": item.get("account_number", ""),
                    "invested_amount": float(item.get("invested_amount") or 0),
                    "monthly_sip": float(item.get("monthly_sip") or 0),
                    "current_value": float(item.get("current_value") or 0),
                    "annual_return_rate": float(item.get("annual_return_rate") or 0),
                    "risk_level": item.get("risk_level", ""),
                    "notes": item.get("notes", ""),
                },
            )
            linked.append(investment)
    return linked


def _delete_orphan_investments(previous_investments: list[Investment], current_investments: list[Investment]) -> None:
    current_ids = {investment.id for investment in current_investments}
    for investment in previous_investments:
        if investment.id in current_ids:
            continue
        investment.refresh_from_db()
        if investment.source_documents.exists():
            continue
        investment.delete()


def _refresh_imported_service_records(document: BikeDocument, parsed) -> None:
    service_payload = parsed.service_payload or {}
    records = list(document.imported_service_records.all())
    if not service_payload and not records:
        return

    issue_date = _parse_date(service_payload.get("service_date")) or timezone.localdate()
    for record in records:
        update_fields = ["parsed_payload"]
        if service_payload:
            record.service_date = issue_date
            record.odometer_km = int(service_payload.get("odometer_km") or record.odometer_km or 0)
            record.service_type = service_payload.get("service_type") or record.service_type
            record.cost = float(service_payload.get("cost") or record.cost or 0)
            record.service_center = service_payload.get("service_center") or record.service_center
            record.next_service_date = _parse_date(service_payload.get("next_service_date")) or record.next_service_date
            record.next_service_km = service_payload.get("next_service_km") or record.next_service_km
            record.extracted_work_summary = service_payload.get("extracted_work_summary") or record.extracted_work_summary
            update_fields.extend(
                [
                    "service_date",
                    "odometer_km",
                    "service_type",
                    "cost",
                    "service_center",
                    "next_service_date",
                    "next_service_km",
                    "extracted_work_summary",
                ]
            )
        record.parsed_payload = build_service_record_payload(
            parsed,
            service_payload,
            existing=record.parsed_payload,
            document=document,
            document_payload=document.extracted_payload,
        )
        record.save(update_fields=update_fields)


def _parse_jsonish_correction(value):
    if value in ("", None):
        return None
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        if candidate.startswith("{") or candidate.startswith("["):
            try:
                return json.loads(candidate)
            except Exception:
                return None
    return None


def _apply_vehicle_service_payload_corrections(service_payload: dict, corrections: dict) -> dict:
    updated = dict(service_payload or {})
    corrected_keys = {key for key, value in (corrections or {}).items() if value not in ("", None, [], {})}
    structured_fields = (
        "parts_items",
        "labour_items",
        "customer_voice_items",
        "replaced_parts",
        "service_operations",
        "systems_impacted",
        "parts_codes",
        "labour_codes",
    )
    scalar_fields = (
        "customer_voice_summary",
        "advisor_name",
        "advisor_contact",
        "service_advisor_name",
        "service_advisor_contact",
        "customer_name",
        "service_consultant",
        "invoice_kind",
        "service_center_contact",
        "service_center_mobile",
        "service_center_email",
        "service_center_website",
        "service_center_address",
        "job_card_number",
    )
    numeric_fields = (
        "line_item_count",
        "parts_item_count",
        "labour_item_count",
        "parts_total_amount",
        "parts_customer_amount",
        "labour_total_amount",
        "labour_customer_amount",
        "parts_tax_total",
        "part_tax_total",
        "labour_tax_total",
        "parts_taxable_amount",
        "part_taxable_total",
        "labour_taxable_amount",
        "labour_taxable_total",
        "total_tax_amount",
        "total_amount",
        "total_customer_amount",
    )

    for field in structured_fields:
        parsed_value = _parse_jsonish_correction(corrections.get(field))
        if parsed_value is not None:
            updated[field] = parsed_value

    for field in scalar_fields:
        if corrections.get(field):
            updated[field] = str(corrections.get(field)).strip()

    if corrections.get("advisor_name") and not updated.get("service_advisor_name"):
        updated["service_advisor_name"] = str(corrections.get("advisor_name")).strip()
    if corrections.get("advisor_contact") and not updated.get("service_advisor_contact"):
        updated["service_advisor_contact"] = str(corrections.get("advisor_contact")).strip()
    if corrections.get("service_advisor_name") and not updated.get("advisor_name"):
        updated["advisor_name"] = str(corrections.get("service_advisor_name")).strip()
    if corrections.get("service_advisor_contact") and not updated.get("advisor_contact"):
        updated["advisor_contact"] = str(corrections.get("service_advisor_contact")).strip()

    for field in numeric_fields:
        if corrections.get(field) in ("", None):
            continue
        try:
            raw_value = float(corrections.get(field) or 0)
        except (TypeError, ValueError):
            continue
        updated[field] = int(raw_value) if raw_value.is_integer() else raw_value

    if "parts_items" in updated and not updated.get("parts_item_count"):
        updated["parts_item_count"] = len(updated.get("parts_items") or [])
    if "labour_items" in updated and not updated.get("labour_item_count"):
        updated["labour_item_count"] = len(updated.get("labour_items") or [])
    if (
        (updated.get("parts_items") or updated.get("labour_items"))
        and not updated.get("line_item_count")
    ):
        updated["line_item_count"] = len(updated.get("parts_items") or []) + len(updated.get("labour_items") or [])

    invoice_enrichment = bike_document_ai._derive_invoice_enrichment(  # pylint: disable=protected-access
        updated.get("parts_items") or [],
        updated.get("labour_items") or [],
        updated.get("customer_voice_items") or [],
    )
    for key, value in invoice_enrichment.items():
        if key in corrected_keys and updated.get(key) not in ("", None, [], {}):
            continue
        if value not in ("", None, [], {}):
            updated[key] = value
    if updated.get("parts_total_amount") in ("", None, 0) and updated.get("parts_customer_amount") not in ("", None, 0):
        updated["parts_total_amount"] = updated.get("parts_customer_amount")
    if updated.get("labour_total_amount") in ("", None, 0) and updated.get("labour_customer_amount") not in ("", None, 0):
        updated["labour_total_amount"] = updated.get("labour_customer_amount")
    if updated.get("total_customer_amount") in ("", None, 0):
        combined_customer_amount = float(updated.get("parts_customer_amount") or 0) + float(updated.get("labour_customer_amount") or 0)
        if combined_customer_amount:
            updated["total_customer_amount"] = round(combined_customer_amount, 2)
    if updated.get("total_amount") in ("", None, 0):
        combined_total_amount = float(updated.get("parts_total_amount") or 0) + float(updated.get("labour_total_amount") or 0)
        if combined_total_amount:
            updated["total_amount"] = round(combined_total_amount, 2)
    if updated.get("cost") in ("", None, 0) and updated.get("total_customer_amount") not in ("", None, 0):
        updated["cost"] = updated.get("total_customer_amount")
    if updated.get("total_customer_amount") in ("", None, 0) and updated.get("cost") not in ("", None, 0):
        updated["total_customer_amount"] = updated.get("cost")
    return updated


def _review_filter(user, *, user_lookup: str = "user"):
    return Q(**{user_lookup: user}) & (
        (Q(parser_status__in=["needs_review", "failed"]) | Q(parse_confidence__lt=REVIEW_CONFIDENCE_THRESHOLD))
        & (Q(extracted_payload__review_queue_resolved=False) | Q(extracted_payload__review_queue_resolved__isnull=True))
    )


def _serialize_statement(upload: StatementUpload) -> dict:
    payload = upload.extracted_payload or {}
    ocr_progress = payload.get("ocr_progress") or {}
    is_partial = bool(payload.get("preview_only") or ocr_progress.get("is_partial"))
    if is_partial:
        processed_pages = int(ocr_progress.get("processed_pages") or 0)
        total_pages = int(ocr_progress.get("total_pages") or processed_pages)
        summary = (
            f"Partial OCR import: {upload.imported_count} row(s) from {processed_pages}/{total_pages or processed_pages} page(s)"
            if upload.imported_count
            else f"OCR preview retained from {processed_pages}/{total_pages or processed_pages} page(s)"
        )
    else:
        summary = f"{upload.imported_count} imported transaction(s)" if upload.imported_count else "Metadata retained for review"
    return {
        "scope": "statement_document",
        "id": upload.id,
        "file_name": upload.file_name,
        "parser_status": upload.parser_status,
        "parse_confidence": upload.parse_confidence,
        "summary": summary,
        "notes": payload.get("parser_notes", ""),
        "fields": {
            "bank_name": upload.bank_name,
            "account_holder": upload.account_holder,
            "account_number": upload.account_number,
            "statement_start": upload.statement_start.isoformat() if upload.statement_start else "",
            "statement_end": upload.statement_end.isoformat() if upload.statement_end else "",
            "statement_kind": payload.get("statement_kind", upload.source),
            "imported_count": upload.imported_count,
            "preview_transaction_count": payload.get("preview_transaction_count", 0),
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=payload.get("raw_text_excerpt", ""), scope="statement_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["statement_document"],
        "created_at": upload.uploaded_at.isoformat(),
        "priority_rank": _priority_rank(upload.parser_status, upload.parse_confidence),
    }


def _serialize_loan(document: LoanImportDocument) -> dict:
    payload = document.extracted_payload or {}
    first_loan = (payload.get("loans") or [{}])[0] if payload.get("loans") else {}
    return {
        "scope": "loan_document",
        "id": document.id,
        "file_name": document.file_name,
        "parser_status": document.parser_status,
        "parse_confidence": document.parse_confidence,
        "summary": document.summary,
        "notes": (payload.get("parser_notes") or payload.get("error") or ""),
        "fields": {
            "document_type": document.document_type,
            "lender": first_loan.get("lender", ""),
            "loan_type": first_loan.get("loan_type", ""),
            "loan_account_number": first_loan.get("loan_account_number", ""),
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=document.extracted_text, scope="loan_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["loan_document"],
        "created_at": document.created_at.isoformat(),
        "priority_rank": _priority_rank(document.parser_status, document.parse_confidence),
    }


def _serialize_loan_closure(document: LoanClosureDocument) -> dict:
    payload = document.extracted_payload or {}
    snapshot = getattr(document, "foreclosure_snapshot", None)
    return {
        "scope": "loan_closure_document",
        "id": document.id,
        "file_name": document.file_name,
        "parser_status": document.parser_status,
        "parse_confidence": document.parse_confidence,
        "summary": (
            f"Verified closure for {document.loan.lender or document.loan.get_loan_type_display()}"
            if document.verification_status == "verified"
            else "Closure document retained for review"
        ),
        "notes": (payload.get("parser_notes") or document.verification_notes or ""),
        "fields": {
            "document_type": (snapshot.get_document_type_display() if snapshot else "") or payload.get("document_type", ""),
            "lender_name": (snapshot.lender_name if snapshot else "") or payload.get("lender_name", ""),
            "borrower_name": (snapshot.borrower_name if snapshot else "") or payload.get("borrower_name", ""),
            "loan_account_number": payload.get("loan_account_number") or document.loan.loan_account_number,
            "closure_amount": document.closure_amount or payload.get("closure_amount") or 0,
            "closure_date": document.closure_date.isoformat() if document.closure_date else payload.get("closure_date") or "",
            "matched_keyword": payload.get("matched_keyword", ""),
            "reconciliation_status": snapshot.get_reconciliation_status_display() if snapshot else "",
            "matched_payment_total": snapshot.matched_payment_total if snapshot else 0,
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=document.extracted_text, scope="loan_closure_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["loan_closure_document"],
        "created_at": (document.updated_at or document.created_at).isoformat(),
        "priority_rank": _priority_rank(document.parser_status, document.parse_confidence),
    }


def _serialize_investment(document: InvestmentImportDocument) -> dict:
    payload = document.extracted_payload or {}
    payload_items = payload.get("investments") or []
    linked_items = list(document.linked_investments.all())
    first_linked = linked_items[0] if linked_items else None
    first_payload = payload_items[0] if payload_items else {}
    return {
        "scope": "investment_document",
        "id": document.id,
        "file_name": document.file_name,
        "parser_status": document.parser_status,
        "parse_confidence": document.parse_confidence,
        "summary": document.summary or "Investment document retained for review",
        "notes": (payload.get("parser_notes") or payload.get("raw_notes", [""])[0] or ""),
        "fields": {
            "broker_name": document.broker_name or payload.get("broker_name", ""),
            "asset_name": (first_linked.asset_name if first_linked else "") or first_payload.get("asset_name", ""),
            "asset_type": (first_linked.asset_type if first_linked else "") or first_payload.get("asset_type", ""),
            "account_number": (
                (first_linked.account_number if first_linked else "")
                or first_payload.get("account_number", "")
                or payload.get("account_number", "")
            ),
            "invested_amount": (first_linked.invested_amount if first_linked else 0) or first_payload.get("invested_amount", 0),
            "current_value": (first_linked.current_value if first_linked else 0) or first_payload.get("current_value", 0),
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=document.extracted_text, scope="investment_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["investment_document"],
        "created_at": document.updated_at.isoformat(),
        "priority_rank": _priority_rank(document.parser_status, document.parse_confidence),
    }


def _serialize_vehicle(document: BikeDocument) -> dict:
    payload = document.extracted_payload or {}
    service_payload = payload.get("service_payload") or {}
    return {
        "scope": "vehicle_document",
        "id": document.id,
        "file_name": document.document_title or document.document_file.name.split("/")[-1],
        "parser_status": document.parser_status,
        "parse_confidence": document.parse_confidence,
        "summary": document.get_document_type_display(),
        "notes": document.parser_notes,
        "fields": {
            "document_type": document.document_type,
            "issuer": document.issuer,
            "document_number": document.document_number,
            "vehicle_number": document.vehicle_number,
            "issue_date": document.issue_date.isoformat() if document.issue_date else "",
            "expiry_date": document.expiry_date.isoformat() if document.expiry_date else "",
            "service_date": service_payload.get("service_date", ""),
            "service_center": service_payload.get("service_center", ""),
            "service_type": service_payload.get("service_type", ""),
            "odometer_km": service_payload.get("odometer_km", ""),
            "cost": service_payload.get("cost", ""),
            "next_service_date": service_payload.get("next_service_date", ""),
            "next_service_km": service_payload.get("next_service_km", ""),
            "extracted_work_summary": service_payload.get("extracted_work_summary", ""),
            "parts_items": service_payload.get("parts_items", []),
            "labour_items": service_payload.get("labour_items", []),
            "customer_voice_items": service_payload.get("customer_voice_items", []),
            "systems_impacted": service_payload.get("systems_impacted", []),
            "total_customer_amount": service_payload.get("total_customer_amount", service_payload.get("cost", "")),
            "parts_customer_amount": service_payload.get("parts_customer_amount", ""),
            "labour_customer_amount": service_payload.get("labour_customer_amount", ""),
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=document.source_text, scope="vehicle_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["vehicle_document"],
        "created_at": document.updated_at.isoformat(),
        "priority_rank": _priority_rank(document.parser_status, document.parse_confidence),
    }


def _serialize_resume(resume: CareerResume) -> dict:
    payload = resume.extracted_payload or {}
    return {
        "scope": "resume_document",
        "id": resume.id,
        "file_name": resume.file_name,
        "parser_status": resume.parser_status,
        "parse_confidence": resume.parse_confidence,
        "summary": resume.summary,
        "notes": "",
        "fields": {
            "role": payload.get("role", ""),
            "experience_years": payload.get("experience_years", ""),
            "skills": ", ".join(payload.get("skills", []) or []),
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=resume.extracted_text, scope="resume_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["resume_document"],
        "created_at": resume.updated_at.isoformat(),
        "priority_rank": _priority_rank(resume.parser_status, resume.parse_confidence),
    }


def _serialize_recruiter(analysis: CareerJobAnalysis) -> dict:
    payload = analysis.extracted_payload or {}
    job_snapshot = payload.get("job_snapshot") or {}
    return {
        "scope": "recruiter_document",
        "id": analysis.id,
        "file_name": analysis.source_document_name or analysis.job_title or analysis.source_name or "Recruiter intake",
        "parser_status": analysis.parser_status,
        "parse_confidence": analysis.parse_confidence,
        "summary": analysis.summary or "Recruiter or JD intake retained for review",
        "notes": payload.get("review_note", ""),
        "fields": {
            "job_title": analysis.job_title or job_snapshot.get("title", ""),
            "company": analysis.company or job_snapshot.get("company", ""),
            "location": analysis.location or job_snapshot.get("location", ""),
            "experience_years": job_snapshot.get("experience_years", ""),
            "salary_min": job_snapshot.get("salary_min", ""),
            "salary_max": job_snapshot.get("salary_max", ""),
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=analysis.extracted_text, scope="recruiter_document"),
        "review_fields": REVIEW_FIELD_SCHEMAS["recruiter_document"],
        "created_at": (analysis.updated_at or analysis.created_at).isoformat(),
        "priority_rank": _priority_rank(analysis.parser_status, analysis.parse_confidence),
    }


def _serialize_credit(upload: CreditReportUpload) -> dict:
    payload = upload.extracted_payload or {}
    return {
        "scope": "credit_report",
        "id": upload.id,
        "file_name": upload.file_name,
        "parser_status": upload.parser_status,
        "parse_confidence": upload.parse_confidence,
        "summary": upload.summary,
        "notes": upload.parser_notes,
        "fields": {
            "bureau": upload.bureau,
            "applicant_name": upload.applicant_name,
            "report_number": upload.report_number,
            "report_date": upload.report_date.isoformat() if upload.report_date else "",
        },
        "background_retry": payload.get("background_retry", {}),
        "accepted_corrections": _accepted_corrections_payload(payload),
        "review_artifacts": _review_artifacts_payload(payload, fallback_excerpt=upload.extracted_text, scope="credit_report"),
        "review_fields": REVIEW_FIELD_SCHEMAS["credit_report"],
        "created_at": upload.updated_at.isoformat(),
        "priority_rank": _priority_rank(upload.parser_status, upload.parse_confidence),
    }


def _accepted_corrections_payload(payload: dict | None) -> dict:
    corrections = dict((payload or {}).get("accepted_corrections") or {})
    return {
        key: value
        for key, value in corrections.items()
        if value not in ("", None, [], {})
    }


def _review_field_label(field_name: str) -> str:
    normalized = str(field_name or "").strip()
    for fields in REVIEW_FIELD_SCHEMAS.values():
        for field in fields:
            if field.get("name") == normalized:
                return str(field.get("label") or normalized)
    return normalized.replace("_", " ").title()


def _review_schema_names(scope: str) -> set[str]:
    return {str(field.get("name") or "") for field in REVIEW_FIELD_SCHEMAS.get(scope, []) if field.get("name")}


def _review_schema_label(scope: str, field_name: str) -> str:
    for field in REVIEW_FIELD_SCHEMAS.get(scope, []):
        if field.get("name") == field_name:
            return str(field.get("label") or field_name)
    return _review_field_label(field_name)


def _review_candidate_value(value) -> str:
    if value in ("", None, [], {}):
        return ""
    if isinstance(value, (list, dict)):
        try:
            return json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)[:500]
        except TypeError:
            return str(value)[:500]
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()[:500]


def _normalize_review_candidate(item: dict) -> dict:
    if not isinstance(item, dict):
        return {}
    value = _review_candidate_value(item.get("value"))
    if not value:
        return {}
    try:
        confidence = round(max(0.0, min(1.0, float(item.get("confidence") or 0))), 2)
    except (TypeError, ValueError):
        confidence = 0.0
    page = item.get("page")
    bbox = []
    for point in list(item.get("bbox") or [])[:4]:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        try:
            bbox.append([round(float(point[0]), 1), round(float(point[1]), 1)])
        except (TypeError, ValueError):
            continue
    normalized = {
        "field_type": str(item.get("field_type") or item.get("field_name") or "candidate")[:80],
        "field_name": str(item.get("field_name") or "")[:80],
        "label": str(item.get("label") or _review_field_label(item.get("field_name", "")) or "Candidate")[:80],
        "value": value,
        "confidence": confidence,
        "source": str(item.get("source") or "")[:80],
        "context": str(item.get("context") or "")[:220],
    }
    if page not in ("", None):
        try:
            normalized["page"] = int(page)
        except (TypeError, ValueError):
            pass
    if bbox:
        normalized["bbox"] = bbox
    if item.get("accepted"):
        normalized["accepted"] = True
    return {
        key: value
        for key, value in normalized.items()
        if value not in ("", None, [], {})
    }


def _accepted_correction_candidates(payload: dict | None) -> list[dict]:
    candidates = []
    for field_name, value in _accepted_corrections_payload(payload).items():
        candidates.append(
            {
                "field_type": "accepted_correction",
                "field_name": field_name,
                "label": _review_field_label(field_name),
                "value": value,
                "confidence": 1.0,
                "source": "accepted_correction",
                "context": "Accepted reviewer value retained for parser learning and retry comparison.",
                "accepted": True,
            }
        )
    return candidates


def _scope_aware_review_field_candidates(scope: str, candidates: list[dict]) -> list[dict]:
    schema_names = _review_schema_names(scope)
    alias_map = REVIEW_GENERIC_FIELD_ALIASES.get(scope, {})
    if not schema_names or not alias_map:
        return candidates

    expanded = list(candidates)
    for candidate in candidates:
        if candidate.get("accepted"):
            continue
        alias_keys = {
            str(candidate.get("field_type") or "").strip(),
            str(candidate.get("field_name") or "").strip(),
        }
        target_fields = []
        for key in alias_keys:
            for field_name in alias_map.get(key, []):
                if field_name in schema_names and field_name not in target_fields:
                    target_fields.append(field_name)
        if not target_fields:
            continue
        existing_name = str(candidate.get("field_name") or "")
        if existing_name in schema_names and len(target_fields) == 1 and target_fields[0] == existing_name:
            continue
        for field_name in target_fields:
            alias = dict(candidate)
            alias["field_name"] = field_name
            alias["label"] = _review_schema_label(scope, field_name)
            alias["source"] = f"{candidate.get('source') or 'candidate'}_schema_alias"[:80]
            alias["confidence"] = max(0.0, min(1.0, round(float(candidate.get("confidence") or 0) - 0.01, 2)))
            alias["context"] = str(candidate.get("context") or "Mapped from generic OCR evidence for this review schema.")[:220]
            expanded.append(alias)
    return expanded


def _merge_review_field_candidates(source: dict, extraction_review: dict, *, scope: str = "") -> list[dict]:
    merged = [
        *list(source.get("field_candidates") or []),
        *list(extraction_review.get("field_candidates") or []),
        *_accepted_correction_candidates(source),
    ]
    normalized = []
    seen = set()
    for item in merged:
        candidate = _normalize_review_candidate(item)
        if not candidate:
            continue
        key = (
            candidate.get("field_name") or candidate.get("field_type"),
            candidate.get("value"),
            candidate.get("source"),
        )
        if key in seen:
            continue
        seen.add(key)
        normalized.append(candidate)
    normalized = _scope_aware_review_field_candidates(scope, normalized)
    normalized_deduped = []
    seen = set()
    for candidate in normalized:
        key = (
            candidate.get("field_name") or candidate.get("field_type"),
            candidate.get("value"),
            candidate.get("source"),
        )
        if key in seen:
            continue
        seen.add(key)
        normalized_deduped.append(candidate)
    schema_names = _review_schema_names(scope)
    normalized = normalized_deduped
    normalized.sort(
        key=lambda item: (
            not bool(item.get("accepted")),
            bool(schema_names) and str(item.get("field_name") or "") not in schema_names,
            item.get("field_type") == "low_confidence_text",
            -float(item.get("confidence") or 0),
            item.get("field_name") or item.get("field_type") or "",
        )
    )
    return normalized[:24]


def _annotate_review_ocr_pages(ocr_pages: list[dict], field_candidates: list[dict]) -> list[dict]:
    accepted_candidates = [
        candidate
        for candidate in field_candidates
        if candidate.get("accepted") and candidate.get("field_name") and candidate.get("value")
    ]
    annotated_pages = []
    for page in list(ocr_pages or [])[:6]:
        page_copy = dict(page or {})
        page_number = page_copy.get("page")
        page_fields = sorted(
            {
                candidate.get("field_name")
                for candidate in field_candidates
                if candidate.get("page") == page_number and candidate.get("field_name")
            }
        )
        annotated_regions = []
        for region in list(page_copy.get("regions") or [])[:10]:
            region_copy = dict(region or {})
            region_text = str(region_copy.get("text") or "").lower()
            field_matches = []
            for candidate in accepted_candidates:
                candidate_value = str(candidate.get("value") or "").lower()
                if candidate_value and candidate_value in region_text:
                    field_matches.append(candidate.get("field_name"))
            if field_matches:
                region_copy["field_matches"] = sorted(set(field_matches))
            try:
                region_confidence = float(region_copy.get("confidence") or 0)
            except (TypeError, ValueError):
                region_confidence = 0
            if 0 < region_confidence < 0.55:
                region_copy["needs_correction"] = True
            annotated_regions.append(region_copy)
        page_copy["regions"] = annotated_regions
        if page_fields:
            page_copy["candidate_fields"] = page_fields
        annotated_pages.append(page_copy)
    return annotated_pages


def _review_overlay_summary(
    *,
    ocr_pages: list[dict],
    field_candidates: list[dict],
    corrected_fields: list[str],
    retry_outcome: dict,
    invoice_summary: dict,
) -> dict:
    region_count = sum(len(page.get("regions") or []) for page in ocr_pages)
    low_confidence_regions = 0
    for page in ocr_pages:
        for region in page.get("regions") or []:
            try:
                confidence = float(region.get("confidence") or 0)
            except (TypeError, ValueError):
                confidence = 0
            if 0 < confidence < 0.55:
                low_confidence_regions += 1
    summary = {
        "page_count": len(ocr_pages),
        "region_count": region_count,
        "low_confidence_regions": low_confidence_regions,
        "field_candidate_count": len(field_candidates),
        "accepted_correction_count": len(corrected_fields),
        "retry_count": retry_outcome.get("retry_count"),
        "retry_resolution": retry_outcome.get("resolution"),
        "invoice_edge_rows": invoice_summary.get("recovered_edge_rows"),
    }
    return {
        key: value
        for key, value in summary.items()
        if value not in ("", None, [], {})
    }


def _review_artifacts_payload(payload: dict | None, *, fallback_excerpt: str = "", scope: str = "") -> dict:
    source = dict(payload or {})
    extraction_review = dict(source.get("extraction_review") or {})
    excerpt = str(source.get("raw_text_excerpt") or extraction_review.get("raw_text_excerpt") or fallback_excerpt or "").strip()
    extraction_notes = source.get("extraction_notes") or source.get("raw_notes") or []
    if isinstance(extraction_notes, str):
        extraction_notes = [extraction_notes]
    field_candidates = _merge_review_field_candidates(source, extraction_review, scope=scope)
    ocr_pages = _annotate_review_ocr_pages(list(extraction_review.get("ocr_pages") or []), field_candidates)
    retry_outcome = {
        key: value
        for key, value in dict(source.get("background_retry") or {}).items()
        if value not in ("", None, [], {})
    }
    corrected_fields = sorted(
        key
        for key, value in dict(source.get("accepted_corrections") or {}).items()
        if value not in ("", None, [], {})
    )
    invoice_summary = {
        key: value
        for key, value in {
            "line_item_count": (source.get("service_payload") or {}).get("line_item_count"),
            "parts_item_count": (source.get("service_payload") or {}).get("parts_item_count"),
            "labour_item_count": (source.get("service_payload") or {}).get("labour_item_count"),
            "systems_impacted": (source.get("service_payload") or {}).get("systems_impacted"),
            "recovered_edge_rows": (source.get("invoice_review") or {}).get("recovered_edge_rows"),
            "compact_ocr_rows": (source.get("invoice_review") or {}).get("compact_ocr_rows"),
        }.items()
        if value not in ("", None, [], {})
    }
    artifacts = {
        "extraction_method": source.get("extraction_method") or extraction_review.get("best_method") or "",
        "extraction_notes": list(extraction_notes)[:6],
        "raw_text_excerpt": excerpt[:600],
        "ocr_pages": ocr_pages,
        "field_candidates": field_candidates,
        "recovery_steps": list(extraction_review.get("recovery_steps") or [])[:8],
        "attempts": list(extraction_review.get("attempts") or [])[:8],
        "attempted_variants": list(extraction_review.get("attempted_variants") or [])[:8],
        "retry_outcome": retry_outcome,
        "review_resolution": source.get("review_queue_resolution", ""),
        "corrected_fields": corrected_fields,
        "invoice_summary": invoice_summary,
        "overlay_summary": _review_overlay_summary(
            ocr_pages=ocr_pages,
            field_candidates=field_candidates,
            corrected_fields=corrected_fields,
            retry_outcome=retry_outcome,
            invoice_summary=invoice_summary,
        ),
    }
    return {
        key: value
        for key, value in artifacts.items()
        if value not in ("", None, [], {})
    }


def _vehicle_document_parse_fields(document: BikeDocument, payload: dict | None, service_payload: dict | None = None) -> dict:
    source = dict(payload or {})
    service_data = dict(service_payload or source.get("service_payload") or {})
    return {
        key: value
        for key, value in {
            "detected_document_type": source.get("detected_document_type") or document.document_type,
            "document_type": document.document_type,
            "document_number": document.document_number or source.get("document_number", ""),
            "issuer": document.issuer or source.get("issuer", ""),
            "vehicle_number": document.vehicle_number or source.get("vehicle_number", ""),
            "issue_date": document.issue_date.isoformat() if document.issue_date else source.get("issue_date", ""),
            "expiry_date": document.expiry_date.isoformat() if document.expiry_date else source.get("expiry_date", ""),
            "job_card_number": service_data.get("job_card_number", ""),
            "invoice_kind": service_data.get("invoice_kind", ""),
            "customer_name": service_data.get("customer_name", ""),
            "service_consultant": service_data.get("service_consultant", ""),
            "service_advisor_name": service_data.get("service_advisor_name") or service_data.get("advisor_name", ""),
            "service_advisor_contact": service_data.get("service_advisor_contact") or service_data.get("advisor_contact", ""),
            "service_center_name": service_data.get("service_center", "") or source.get("service_center_name", ""),
            "total_customer_amount": service_data.get("total_customer_amount") or service_data.get("cost") or document.premium_amount or 0,
        }.items()
        if value not in ("", None, [], {})
    }


def _apply_statement_correction(user, document_id: int, corrections: dict) -> dict:
    upload = StatementUpload.objects.get(user=user, pk=document_id)
    payload = dict(upload.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    upload.bank_name = corrections.get("bank_name", upload.bank_name)
    upload.account_holder = corrections.get("account_holder", upload.account_holder)
    upload.account_number = corrections.get("account_number", upload.account_number)
    upload.source = corrections.get("statement_kind", upload.source)
    upload.institution_name = corrections.get("bank_name", upload.institution_name)
    upload.statement_start = _parse_date(corrections.get("statement_start")) or upload.statement_start
    upload.statement_end = _parse_date(corrections.get("statement_end")) or upload.statement_end
    upload.parse_confidence = max(upload.parse_confidence, 0.74 if len(accepted) >= 4 else 0.62)
    upload.parser_status = "parsed" if upload.imported_count else "needs_review"
    payload["parser_notes"] = " ".join(filter(None, [payload.get("parser_notes", ""), corrections.get("review_note", "Accepted user correction.")])).strip()
    payload = _mark_review_queue_resolved(payload)
    upload.extracted_payload = payload
    upload.save(
        update_fields=[
            "bank_name",
            "account_holder",
            "account_number",
            "source",
            "institution_name",
            "statement_start",
            "statement_end",
            "parse_confidence",
            "parser_status",
            "extracted_payload",
        ]
    )
    record_parser_correction(
        user=user,
        scope="statement_document",
        filename=upload.file_name,
        detected_type=upload.source,
        text=str((upload.extracted_payload or {}).get("raw_text_excerpt") or ""),
        field_names=[key for key, value in accepted.items() if value],
        confidence=upload.parse_confidence,
    )
    queue_statement_retry(upload, reason="accepted_user_correction")
    ocr_progress = dict((upload.extracted_payload or {}).get("ocr_progress") or {})
    processed_pages = int(ocr_progress.get("processed_pages") or 0)
    total_pages = int(ocr_progress.get("total_pages") or 0)
    retry_limit = min(max(processed_pages * 6, 24), total_pages or 64, 64)
    retry_statement_upload(upload, ocr_page_limit=retry_limit)
    upload.refresh_from_db()
    return _serialize_statement(upload)


def _apply_loan_correction(user, document_id: int, corrections: dict) -> dict:
    document = LoanImportDocument.objects.get(user=user, pk=document_id)
    payload = dict(document.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload)
    document.document_type = corrections.get("document_type", document.document_type)
    document.parse_confidence = max(document.parse_confidence, 0.7 if len(accepted) >= 3 else 0.58)
    document.parser_status = "parsed" if document.linked_loans.exists() else "needs_review"
    document.extracted_payload = payload
    document.summary = document.summary or "User correction accepted for this loan document."
    document.save(update_fields=["document_type", "parse_confidence", "parser_status", "extracted_payload", "summary"])
    record_parser_correction(
        user=user,
        scope="loan_document",
        filename=document.file_name,
        detected_type=document.document_type or "loan_document",
        text=document.extracted_text,
        field_names=[key for key, value in accepted.items() if value],
        confidence=document.parse_confidence,
    )
    return _serialize_loan(document)


def _apply_loan_closure_correction(user, document_id: int, corrections: dict) -> dict:
    document = LoanClosureDocument.objects.select_related("loan").get(loan__user=user, pk=document_id)
    payload = dict(document.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload, resolution="accepted_correction_reviewed")
    if corrections.get("loan_account_number"):
        payload["loan_account_number"] = str(corrections["loan_account_number"]).strip()
    if corrections.get("matched_keyword"):
        payload["matched_keyword"] = str(corrections["matched_keyword"]).strip()
    closure_amount = _parse_float(corrections.get("closure_amount"))
    if closure_amount is not None:
        payload["closure_amount"] = closure_amount
        document.closure_amount = closure_amount
    closure_date = _parse_date(corrections.get("closure_date"))
    if closure_date:
        payload["closure_date"] = closure_date.isoformat()
        document.closure_date = closure_date
    payload["parser_notes"] = " ".join(
        filter(None, [payload.get("parser_notes", ""), corrections.get("review_note", "Accepted user correction.")])
    ).strip()
    verified, notes = loan_closure_parser.verify_document(
        document.loan,
        {
            "payload": payload,
            "extracted_text": document.extracted_text or "",
        },
    )
    document.extracted_payload = payload
    document.parse_confidence = max(document.parse_confidence, 0.78 if len(accepted) >= 3 else 0.64)
    document.parser_status = "parsed" if payload.get("matched_keyword") else "needs_review"
    document.verification_status = "verified" if verified else "rejected"
    document.verification_notes = notes
    document.save(
        update_fields=[
            "extracted_payload",
            "parse_confidence",
            "parser_status",
            "verification_status",
            "verification_notes",
            "closure_amount",
            "closure_date",
            "updated_at",
        ]
    )
    snapshot = loan_foreclosure_service.sync_snapshot_from_document(document)
    if verified:
        loan_foreclosure_service.reconcile_snapshot(snapshot)
    record_parser_correction(
        user=user,
        scope="loan_closure_document",
        filename=document.file_name,
        detected_type="loan_closure_document",
        text=document.extracted_text,
        field_names=[key for key, value in accepted.items() if value not in ("", None, [])],
        confidence=document.parse_confidence,
        resolution="accepted_correction_verified" if verified else "accepted_correction_reviewed",
    )
    return _serialize_loan_closure(document)


def _apply_investment_correction(user, document_id: int, corrections: dict) -> dict:
    document = InvestmentImportDocument.objects.prefetch_related("linked_investments").get(user=user, pk=document_id)
    payload = dict(document.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload)

    primary_item = dict(((payload.get("investments") or [{}])[0]) if payload.get("investments") else {})
    if corrections.get("asset_name"):
        primary_item["asset_name"] = str(corrections["asset_name"]).strip()
    if corrections.get("asset_type"):
        primary_item["asset_type"] = str(corrections["asset_type"]).strip()
    if corrections.get("account_number"):
        primary_item["account_number"] = str(corrections["account_number"]).strip()
    invested_amount = _parse_float(corrections.get("invested_amount"))
    if invested_amount is not None:
        primary_item["invested_amount"] = invested_amount
    current_value = _parse_float(corrections.get("current_value"))
    if current_value is not None:
        primary_item["current_value"] = current_value
    if corrections.get("broker_name"):
        document.broker_name = str(corrections["broker_name"]).strip()
        payload["broker_name"] = document.broker_name
    if document.broker_name and not primary_item.get("institution"):
        primary_item["institution"] = document.broker_name
    if primary_item:
        remaining_items = list(payload.get("investments") or [])[1:]
        payload["investments"] = [primary_item, *remaining_items]

    previous_investments = list(document.linked_investments.all())
    linked = _upsert_retry_investments(user, [primary_item] if primary_item.get("asset_name") else [])
    document.extracted_payload = payload
    document.parse_confidence = max(document.parse_confidence, 0.8 if linked else 0.63)
    document.parser_status = "parsed" if linked else "needs_review"
    document.summary = (
        f"{len(linked)} investment record(s) are now linked to this document after user correction."
        if linked
        else (document.summary or "User correction accepted, but Alfred still needs more portfolio detail.")
    )
    document.save(
        update_fields=[
            "broker_name",
            "extracted_payload",
            "parse_confidence",
            "parser_status",
            "summary",
            "updated_at",
        ]
    )
    if linked:
        document.linked_investments.set(linked)
        _delete_orphan_investments(previous_investments, linked)
    record_parser_correction(
        user=user,
        scope="investment_document",
        filename=document.file_name,
        detected_type=(document.broker_name or "portfolio_statement").lower().replace(" ", "_"),
        text=document.extracted_text,
        field_names=[key for key, value in accepted.items() if value not in ("", None, [])],
        confidence=document.parse_confidence,
        resolution="accepted_correction_linked_holdings" if linked else "accepted_correction_reviewed",
    )
    return _serialize_investment(document)


def _apply_vehicle_correction(user, document_id: int, corrections: dict) -> dict:
    document = BikeDocument.objects.get(user=user, pk=document_id)
    payload = dict(document.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload)
    service_payload = dict(payload.get("service_payload") or {})
    document.document_type = corrections.get("document_type", document.document_type)
    document.issuer = corrections.get("issuer", document.issuer)
    document.document_number = corrections.get("document_number", document.document_number)
    document.vehicle_number = corrections.get("vehicle_number", document.vehicle_number)
    document.issue_date = _parse_date(corrections.get("issue_date")) or document.issue_date
    document.expiry_date = _parse_date(corrections.get("expiry_date")) or document.expiry_date
    if corrections.get("service_date"):
        service_payload["service_date"] = corrections.get("service_date")
    if corrections.get("service_center"):
        service_payload["service_center"] = corrections.get("service_center")
    if corrections.get("service_type"):
        service_payload["service_type"] = corrections.get("service_type")
    if corrections.get("odometer_km") not in ("", None):
        service_payload["odometer_km"] = int(float(corrections.get("odometer_km") or 0))
    if corrections.get("cost") not in ("", None):
        service_payload["cost"] = float(corrections.get("cost") or 0)
    if corrections.get("next_service_date"):
        service_payload["next_service_date"] = corrections.get("next_service_date")
    if corrections.get("next_service_km") not in ("", None):
        service_payload["next_service_km"] = int(float(corrections.get("next_service_km") or 0))
    if corrections.get("extracted_work_summary"):
        service_payload["extracted_work_summary"] = corrections.get("extracted_work_summary")
    service_payload = _apply_vehicle_service_payload_corrections(service_payload, corrections)
    if service_payload:
        payload["service_payload"] = service_payload
    has_service_data = any(
        service_payload.get(key) not in ("", None, [], {})
        for key in (
            "service_date",
            "service_center",
            "service_type",
            "odometer_km",
            "cost",
            "extracted_work_summary",
            "parts_items",
            "labour_items",
            "line_item_count",
        )
    )
    if service_payload.get("cost") not in ("", None, 0):
        document.premium_amount = float(service_payload.get("cost") or 0)
    document.parse_confidence = max(document.parse_confidence, 0.78 if len(accepted) >= 3 or has_service_data else 0.62)
    document.parser_status = "parsed" if document.document_number or has_service_data else "needs_review"
    document.parser_notes = " ".join(filter(None, [document.parser_notes, corrections.get("review_note", "")])).strip()
    document.extracted_payload = payload
    document.save(
        update_fields=[
            "document_type",
            "issuer",
            "document_number",
            "vehicle_number",
            "issue_date",
            "expiry_date",
            "premium_amount",
            "parse_confidence",
            "parser_status",
            "parser_notes",
            "extracted_payload",
        ]
    )
    bike_service_intelligence.hydrate_document(document)
    _refresh_imported_service_records(
        document,
        SimpleNamespace(
            fields=_vehicle_document_parse_fields(document, payload, service_payload),
            service_payload=service_payload,
            parser_status=document.parser_status,
            confidence=document.parse_confidence,
            parser_notes=document.parser_notes,
        ),
    )
    record_parser_correction(
        user=user,
        scope="vehicle_document",
        filename=document.document_title or document.document_file.name.split("/")[-1],
        detected_type=document.document_type,
        text=document.source_text,
        field_names=[key for key, value in accepted.items() if value],
        confidence=document.parse_confidence,
    )
    return _serialize_vehicle(document)


def _apply_resume_correction(user, document_id: int, corrections: dict) -> dict:
    resume = CareerResume.objects.get(user=user, pk=document_id)
    payload = dict(resume.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload)
    if corrections.get("role"):
        payload["role"] = corrections["role"]
    if corrections.get("experience_years") not in (None, ""):
        payload["experience_years"] = float(corrections["experience_years"])
    if corrections.get("skills"):
        payload["skills"] = [item.strip() for item in str(corrections["skills"]).split(",") if item.strip()]
    resume.extracted_payload = payload
    resume.summary = resume.summary or "User review accepted for this resume."
    resume.parse_confidence = max(resume.parse_confidence, 0.75 if payload.get("skills") else 0.6)
    resume.parser_status = "parsed" if payload.get("role") or payload.get("skills") else "needs_review"
    resume.save(update_fields=["extracted_payload", "summary", "parse_confidence", "parser_status", "updated_at"])
    record_parser_correction(
        user=user,
        scope="resume_document",
        filename=resume.file_name,
        detected_type="resume",
        text=resume.extracted_text,
        field_names=[key for key, value in accepted.items() if value],
        confidence=resume.parse_confidence,
    )
    return _serialize_resume(resume)


def _resume_payload_for_job_analysis(user) -> dict:
    latest_resume = CareerResume.objects.filter(user=user).order_by("-updated_at", "-id").first()
    if latest_resume:
        return latest_resume.extracted_payload or {}
    profile = CareerProfile.objects.filter(user=user).first()
    if profile is None:
        return {"role": "", "experience_years": 0, "skills": []}
    return {
        "role": profile.role,
        "experience_years": profile.experience_years,
        "skills": [item.strip() for item in (profile.skills or "").split(",") if item.strip()],
    }


def _job_snapshot_like(payload: dict):
    snapshot = payload.get("job_snapshot") or {}
    return type(
        "JobSnapshotLike",
        (),
        {
            "source_name": payload.get("source_name") or "Recruiter Mail Intake",
            "job_url": payload.get("job_url") or "",
            "apply_url": snapshot.get("apply_url") or payload.get("apply_url") or payload.get("job_url") or "",
            "company": snapshot.get("company", ""),
            "title": snapshot.get("title", ""),
            "location": snapshot.get("location", ""),
            "description": payload.get("intake_combined_text") or "",
            "required_skills": snapshot.get("required_skills") or [],
            "experience_years": float(snapshot.get("experience_years") or 0),
            "employment_type": snapshot.get("employment_type", ""),
            "salary_min": float(snapshot.get("salary_min") or 0),
            "salary_max": float(snapshot.get("salary_max") or 0),
            "salary_currency": snapshot.get("salary_currency", ""),
            "salary_period": snapshot.get("salary_period", ""),
            "source_kind": snapshot.get("source_kind") or payload.get("source_kind") or "recruiter_message",
        },
    )()


def _recruiter_parser_state(snapshot, *, attachment_present: bool = False) -> tuple[str, float]:
    confidence = 0.18
    if snapshot.title:
        confidence += 0.18
    if snapshot.company:
        confidence += 0.12
    if snapshot.location:
        confidence += 0.08
    if snapshot.required_skills:
        confidence += 0.16
    if snapshot.experience_years:
        confidence += 0.08
    if snapshot.salary_min or snapshot.salary_max:
        confidence += 0.1
    if snapshot.apply_url and str(snapshot.apply_url).startswith("http"):
        confidence += 0.08
    if attachment_present:
        confidence += 0.06
    confidence = round(min(confidence, 0.96), 2)
    status = "parsed" if confidence >= 0.62 else ("needs_review" if snapshot.description or snapshot.title or snapshot.company else "failed")
    return status, confidence


def _apply_recruiter_analysis_update(analysis: CareerJobAnalysis, snapshot, *, resume_payload: dict, keep_evidence: bool = True) -> None:
    fit = job_intelligence.compare_resume_to_job(resume_payload, snapshot)
    compensation = job_intelligence.compensation_benchmark(
        role=snapshot.title or resume_payload.get("role") or "analyst",
        location=snapshot.location or "",
        openings=[],
        job_snapshot=snapshot,
        openings_evidence=None,
        current_income_annual=0.0,
    )
    payload = dict(analysis.extracted_payload or {})
    payload["source_kind"] = snapshot.source_kind
    payload["job_url"] = snapshot.job_url
    payload["apply_url"] = snapshot.apply_url
    payload["job_snapshot"] = {
        "title": snapshot.title,
        "company": snapshot.company,
        "location": snapshot.location,
        "required_skills": snapshot.required_skills,
        "experience_years": snapshot.experience_years,
        "salary_min": snapshot.salary_min,
        "salary_max": snapshot.salary_max,
        "salary_currency": snapshot.salary_currency,
        "salary_period": snapshot.salary_period,
        "employment_type": snapshot.employment_type,
        "source_kind": snapshot.source_kind,
        "apply_url": snapshot.apply_url,
    }
    payload["fit"] = fit
    payload["compensation_benchmark"] = compensation
    payload["resume_payload"] = resume_payload
    analysis.source_name = snapshot.source_name or analysis.source_name or "Recruiter Mail Intake"
    analysis.job_url = snapshot.job_url or analysis.job_url
    analysis.apply_url = snapshot.apply_url or analysis.apply_url
    analysis.company = snapshot.company[:180]
    analysis.job_title = snapshot.title[:180]
    analysis.location = snapshot.location[:180]
    analysis.fit_score = fit["fit_score"]
    analysis.strengths = "\n".join(fit["strengths"])
    analysis.gaps = "\n".join(fit["gaps"])
    analysis.summary = f"Recruiter intake fit score {fit['fit_score']}/100 for {snapshot.title or 'this role'} at {snapshot.company or analysis.source_name}."
    analysis.extracted_payload = payload
    analysis.extracted_text = snapshot.description or analysis.extracted_text
    if not keep_evidence:
        analysis.evidence = []


def _apply_recruiter_correction(user, document_id: int, corrections: dict) -> dict:
    analysis = CareerJobAnalysis.objects.get(user=user, pk=document_id)
    payload = dict(analysis.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload)
    payload["review_note"] = " ".join(filter(None, [payload.get("review_note", ""), corrections.get("review_note", "")])).strip()
    snapshot_payload = dict(payload.get("job_snapshot") or {})
    if corrections.get("job_title"):
        snapshot_payload["title"] = str(corrections["job_title"]).strip()
    if corrections.get("company"):
        snapshot_payload["company"] = str(corrections["company"]).strip()
    if corrections.get("location"):
        snapshot_payload["location"] = str(corrections["location"]).strip()
    experience_years = _parse_float(corrections.get("experience_years"))
    if experience_years is not None:
        snapshot_payload["experience_years"] = experience_years
    salary_min = _parse_float(corrections.get("salary_min"))
    if salary_min is not None:
        snapshot_payload["salary_min"] = salary_min
    salary_max = _parse_float(corrections.get("salary_max"))
    if salary_max is not None:
        snapshot_payload["salary_max"] = salary_max
    payload["job_snapshot"] = snapshot_payload

    snapshot = _job_snapshot_like(
        {
            **payload,
            "source_name": analysis.source_name,
            "job_url": analysis.job_url,
            "apply_url": analysis.apply_url,
            "intake_combined_text": analysis.extracted_text or payload.get("intake_combined_text", ""),
        }
    )
    resume_payload = _resume_payload_for_job_analysis(user)
    _apply_recruiter_analysis_update(analysis, snapshot, resume_payload=resume_payload)
    analysis.parse_confidence = max(float(analysis.parse_confidence or 0), 0.8 if len(accepted) >= 3 else 0.64)
    analysis.parser_status = "parsed" if analysis.job_title or analysis.company else "needs_review"
    analysis.save(
        update_fields=[
            "source_name",
            "job_url",
            "apply_url",
            "company",
            "job_title",
            "location",
            "parser_status",
            "parse_confidence",
            "extracted_text",
            "fit_score",
            "strengths",
            "gaps",
            "summary",
            "extracted_payload",
            "updated_at",
        ]
    )
    record_parser_correction(
        user=user,
        scope="recruiter_document",
        filename=analysis.source_document_name or "recruiter_message.txt",
        detected_type=(analysis.extracted_payload or {}).get("source_kind") or "recruiter_message",
        text=analysis.extracted_text,
        field_names=[key for key, value in accepted.items() if value not in ("", None, [])],
        confidence=analysis.parse_confidence,
        resolution="accepted_correction_recruiter_document",
    )
    return _serialize_recruiter(analysis)


def _apply_credit_correction(user, document_id: int, corrections: dict) -> dict:
    upload = CreditReportUpload.objects.get(user=user, pk=document_id)
    payload = dict(upload.extracted_payload or {})
    accepted = dict(payload.get("accepted_corrections") or {})
    accepted.update(corrections)
    payload["accepted_corrections"] = accepted
    payload = _mark_review_queue_resolved(payload)
    upload.bureau = corrections.get("bureau", upload.bureau)
    upload.applicant_name = corrections.get("applicant_name", upload.applicant_name)
    upload.report_number = corrections.get("report_number", upload.report_number)
    upload.report_date = _parse_date(corrections.get("report_date")) or upload.report_date
    upload.parse_confidence = max(upload.parse_confidence, 0.76 if len(accepted) >= 3 else 0.61)
    upload.parser_status = "parsed" if upload.report_number or upload.parsed_credit_score_id else "needs_review"
    upload.parser_notes = " ".join(filter(None, [upload.parser_notes, corrections.get("review_note", "")])).strip()
    upload.extracted_payload = payload
    upload.save(
        update_fields=[
            "bureau",
            "applicant_name",
            "report_number",
            "report_date",
            "parse_confidence",
            "parser_status",
            "parser_notes",
            "extracted_payload",
            "updated_at",
        ]
    )
    if upload.parsed_credit_score_id:
        CreditScore.objects.filter(pk=upload.parsed_credit_score_id).update(bureau=upload.bureau or "CIBIL")
    record_parser_correction(
        user=user,
        scope="credit_report",
        filename=upload.file_name,
        detected_type=upload.bureau or "credit_report",
        text=upload.extracted_text,
        field_names=[key for key, value in accepted.items() if value],
        confidence=upload.parse_confidence,
    )
    return _serialize_credit(upload)


def _priority_rank(parser_status: str, parse_confidence: float) -> int:
    if parser_status == "failed":
        return 4
    if parser_status == "needs_review" and parse_confidence < 0.3:
        return 3
    if parser_status == "needs_review":
        return 2
    return 1


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
