from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from django.conf import settings
from django.utils import timezone


RAW_FILE_RETENTION_KEY = "raw_file_retention"


def raw_upload_cleanup_enabled() -> bool:
    return bool(getattr(settings, "ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION", False))


def purge_uploaded_file_after_extraction(
    instance,
    field_name: str,
    *,
    reason: str,
    payload_field: str = "extracted_payload",
    update_timestamp: bool = True,
) -> dict[str, Any]:
    field_file = getattr(instance, field_name, None)
    storage_name = str(getattr(field_file, "name", "") or "")
    file_name = PurePosixPath(storage_name).name if storage_name else ""
    now = timezone.now().isoformat()
    metadata = {
        "policy": "delete_after_extraction" if raw_upload_cleanup_enabled() else "retain_in_local_runtime",
        "enabled": raw_upload_cleanup_enabled(),
        "field": field_name,
        "file_name": file_name,
        "storage_name": storage_name,
        "deleted": False,
        "deleted_at": "",
        "reason": reason,
        "error": "",
    }

    if not raw_upload_cleanup_enabled():
        return metadata

    update_fields: set[str] = set()
    if storage_name:
        try:
            field_file.delete(save=False)
            setattr(instance, field_name, "")
            metadata["deleted"] = True
            metadata["deleted_at"] = now
            update_fields.add(field_name)
        except Exception as exc:  # pragma: no cover - depends on storage backend failure.
            metadata["error"] = f"{type(exc).__name__}: {exc}"
    else:
        metadata["deleted"] = True
        metadata["deleted_at"] = now

    if payload_field and hasattr(instance, payload_field):
        current_payload = getattr(instance, payload_field, None)
        if isinstance(current_payload, dict):
            payload = dict(current_payload)
        else:
            payload = {}
        payload[RAW_FILE_RETENTION_KEY] = metadata
        setattr(instance, payload_field, payload)
        update_fields.add(payload_field)

    if update_timestamp and hasattr(instance, "updated_at"):
        update_fields.add("updated_at")

    if update_fields:
        instance.save(update_fields=sorted(update_fields))

    return metadata
