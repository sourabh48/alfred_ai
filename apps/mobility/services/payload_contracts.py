from __future__ import annotations

from copy import deepcopy


def merge_nested_payload(existing: dict | None, incoming: dict | None) -> dict:
    merged = deepcopy(existing or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_nested_payload(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def resolve_vehicle_identity(profile, *, bike_name: str = "", vehicle_number: str = "", existing_name: str = "", existing_number: str = "") -> dict:
    return {
        "bike_name": bike_name or existing_name or getattr(profile, "display_name", ""),
        "vehicle_number": vehicle_number or existing_number or getattr(profile, "vehicle_number", ""),
    }


def build_document_payload(parsed, relevance: dict, *, existing: dict | None = None) -> dict:
    return merge_nested_payload(
        existing,
        {
            **(parsed.fields or {}),
            "detected_document_type": parsed.document_type,
            "service_payload": deepcopy(parsed.service_payload or {}),
            **deepcopy(getattr(parsed, "review_payload", {}) or {}),
            "relevance_score": relevance.get("score", 0),
            "relevance_reasons": list(relevance.get("reasons") or []),
        },
    )


def _summarize_extraction_review(extraction_review: dict | None) -> dict:
    source = dict(extraction_review or {})
    pages = []
    for page in source.get("ocr_pages") or []:
        pages.append(
            {
                "page": page.get("page"),
                "preview": page.get("preview", ""),
                "line_count": page.get("line_count", 0),
                "region_count": len(page.get("regions") or []),
                "variant": page.get("variant", ""),
                "rotation": page.get("rotation", 0),
            }
        )
    return {
        key: value
        for key, value in {
            "best_method": source.get("best_method", ""),
            "recovery_steps": deepcopy(source.get("recovery_steps") or []),
            "attempts": deepcopy(source.get("attempts") or []),
            "attempted_variants": deepcopy(source.get("attempted_variants") or []),
            "ocr_pages": pages,
        }.items()
        if value not in ("", None, [], {})
    }


def _build_service_review_trace(parsed, document_payload: dict | None = None, document=None) -> dict:
    payload = dict(document_payload or {})
    extraction_review = payload.get("extraction_review") or getattr(parsed, "review_payload", {}).get("extraction_review") or {}
    accepted_corrections = dict(payload.get("accepted_corrections") or {})
    background_retry = dict(payload.get("background_retry") or {})
    trace = {
        "document_parser_status": getattr(parsed, "parser_status", "") or getattr(document, "parser_status", ""),
        "document_parse_confidence": round(float(getattr(parsed, "confidence", 0) or getattr(document, "parse_confidence", 0) or 0), 4),
        "document_parser_notes": getattr(parsed, "parser_notes", "") or getattr(document, "parser_notes", "") or "",
        "review_queue_resolution": payload.get("review_queue_resolution", ""),
        "review_queue_resolved": bool(payload.get("review_queue_resolved")),
        "accepted_corrections": accepted_corrections,
        "corrected_fields": sorted(key for key, value in accepted_corrections.items() if value not in ("", None, [], {})),
        "background_retry": background_retry,
        "extraction_method": payload.get("extraction_method") or getattr(parsed, "review_payload", {}).get("extraction_method") or "",
        "extraction_review": _summarize_extraction_review(extraction_review),
    }
    return {
        key: value
        for key, value in trace.items()
        if value not in ("", None, [], {})
    }


def build_service_record_payload(parsed, service_payload: dict | None, *, existing: dict | None = None, document_payload: dict | None = None, document=None) -> dict:
    return merge_nested_payload(
        existing,
        {
            "document_parse": deepcopy(parsed.fields or {}),
            "service_payload": deepcopy(service_payload or {}),
            "review_trace": _build_service_review_trace(parsed, document_payload=document_payload, document=document),
        },
    )
