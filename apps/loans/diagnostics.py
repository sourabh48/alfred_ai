"""Allowlisted public loan diagnostics; historical free text is never trusted."""
import re
from math import isfinite


LOAN_PROCESSING_ERROR = "The loan document could not be processed. Please retry or review it manually."
LOAN_ERROR_CODE = "loan_document_processing_failed"
IMPORT_MESSAGES = {
    "pending": "Loan document is waiting to be processed.",
    "parsed": "Loan records were created or updated from the uploaded document.",
    "needs_review": "Loan document was saved, but its extracted details need review.",
    "failed": "Loan document was saved for review because it could not be processed.",
}
VERIFICATION_MESSAGES = {
    "pending": "Closure document is waiting for verification.",
    "verified": "Closure document was verified against the selected loan.",
    "rejected": "Closure document could not be verified against the selected loan.",
}
RECONCILIATION_MESSAGES = {
    "unmatched": "No loan-linked payment matched the closure document yet.",
    "partial_match": "Matched payments are below the document payable amount.",
    "full_match": "Closure payment was reconciled with the selected loan.",
    "mismatch": "Candidate payments do not match the document payable amount.",
}


def import_message(parser_status):
    return IMPORT_MESSAGES.get(parser_status, IMPORT_MESSAGES["needs_review"])


def verification_message(verification_status):
    return VERIFICATION_MESSAGES.get(verification_status, VERIFICATION_MESSAGES["pending"])


def reconciliation_message(reconciliation_status):
    return RECONCILIATION_MESSAGES.get(reconciliation_status, RECONCILIATION_MESSAGES["unmatched"])


def public_error(payload, *, cleanup=False):
    source = payload if isinstance(payload, dict) else {}
    result = {}
    if source.get("error") or source.get("error_code"):
        result = {"error": "Source upload cleanup failed. Please retry." if cleanup else LOAN_PROCESSING_ERROR,
                  "error_code": "source_upload_cleanup_failed" if cleanup else LOAN_ERROR_CODE}
    reference = source.get("error_id")
    if isinstance(reference, str) and re.fullmatch(r"[a-f0-9]{32}", reference):
        result["error_id"] = reference
    return result


def public_retention(payload):
    source = payload if isinstance(payload, dict) else {}
    result = {key: source[key] for key in ("enabled", "deleted") if type(source.get(key)) is bool}
    for key, choices in {
        "policy": {"delete_after_extraction", "retain_in_local_runtime"},
        "field": {"uploaded_file"},
        "reason": {"loan_document_extraction_complete", "loan_document_parser_failure_cleanup",
                   "loan_closure_document_extraction_complete", "loan_document_retry_extraction_complete",
                   "loan_closure_retry_extraction_complete"},
    }.items():
        if isinstance(source.get(key), str) and source[key] in choices:
            result[key] = source[key]
    result.update(public_error(source, cleanup=True))
    return result


def public_retry(payload):
    source = payload if isinstance(payload, dict) else {}
    result = {}
    for key, choices in {
        "state": {"queued", "running", "resolved", "needs_review", "failed", "unavailable"},
        "reason": {"manual_review_retry", "source_file_unavailable"},
        "resolution": {"loan_rows_updated", "still_needs_review", "closure_document_verified",
                       "raw_file_deleted", "source_file_missing"},
    }.items():
        if isinstance(source.get(key), str) and source[key] in choices:
            result[key] = source[key]
    if result.get("state") == "unavailable":
        result["reason"] = "Upload the source again to retry extraction. Saved fields remain available for review."
    if type(source.get("retry_count")) is int and source["retry_count"] >= 0:
        result["retry_count"] = source["retry_count"]
    return result


def public_payload(payload):
    source = payload if isinstance(payload, dict) else {}
    result = public_error(source)
    for key, choices in {
        "document_type": {"other", "loan_book", "loan_statement", "sanction_letter", "repayment_schedule",
                          "foreclosure_statement", "closure_letter", "noc"},
        "parser_status": set(IMPORT_MESSAGES),
    }.items():
        if isinstance(source.get(key), str) and source[key] in choices:
            result[key] = source[key]
    if type(source.get("confidence")) in (int, float) and isfinite(source["confidence"]) and 0 <= source["confidence"] <= 1:
        result["confidence"] = source["confidence"]
    if "raw_file_retention" in source:
        result["raw_file_retention"] = public_retention(source["raw_file_retention"])
    if "background_retry" in source:
        result["background_retry"] = public_retry(source["background_retry"])
    return result


def public_allocation(payload):
    """Keep settlement accounting, excluding arbitrary notes and nested diagnostics."""
    source = payload if isinstance(payload, dict) else {}
    money_fields = {"expected_total", "payment_total", "payment_gap", "raw_document_total", "confidence",
                    "principal_paid", "interest_paid", "charges_paid", "penalties_paid", "tax_paid",
                    "amount", "remaining_balance_after_payment", "expense_id"}
    result = {key: value for key, value in source.items()
              if key in money_fields and type(value) in (int, float) and isfinite(value)}
    for key, choices in {
        "allocation_status": {"pending_unmatched", "finalized", "provisional_partial", "mismatch_unallocated"},
        "allocation_method": {"unallocated", "document_components", "proportional_to_matched_payment"},
        "document_normalization": {"exact", "principal_only_fallback", "scaled_to_payable_total"},
    }.items():
        if isinstance(source.get(key), str) and source[key] in choices:
            result[key] = source[key]
    for key in ("document_components", "allocated_components"):
        if isinstance(source.get(key), dict):
            result[key] = public_allocation(source[key])
    if isinstance(source.get("expense_allocations"), list):
        result["expense_allocations"] = [public_allocation(item) for item in source["expense_allocations"]
                                         if isinstance(item, dict)]
    payment_date = source.get("payment_date")
    if isinstance(payment_date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", payment_date):
        result["payment_date"] = payment_date
    return result
