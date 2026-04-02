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
            "relevance_score": relevance.get("score", 0),
            "relevance_reasons": list(relevance.get("reasons") or []),
        },
    )


def build_service_record_payload(parsed, service_payload: dict | None, *, existing: dict | None = None) -> dict:
    return merge_nested_payload(
        existing,
        {
            "document_parse": deepcopy(parsed.fields or {}),
            "service_payload": deepcopy(service_payload or {}),
        },
    )
