from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from django.conf import settings
from django.utils import timezone

from .api_errors import safe_error_details


RAW_FILE_RETENTION_KEY = "raw_file_retention"

# Every stored private upload: (model, file field, owner lookup).
PRIVATE_FILE_FIELDS = (
    ("expenses.StatementUpload", "original_file", "user_id"),
    ("investments.InvestmentImportDocument", "uploaded_file", "user_id"),
    ("career.CareerResume", "uploaded_file", "user_id"),
    ("mobility.TripPhoto", "image", "user_id"),
    ("mobility.TripVideo", "video", "user_id"),
    ("mobility.BikeDocument", "document_file", "user_id"),
    ("loans.LoanImportDocument", "uploaded_file", "user_id"),
    ("loans.LoanClosureDocument", "uploaded_file", "loan__user_id"),
)


def stored_file_names(owner_id=None) -> set[str]:
    from django.apps import apps

    names = set()
    for model, field, owner in PRIVATE_FILE_FIELDS:
        rows = apps.get_model(model).objects.exclude(**{field: ""})
        if owner_id is not None:
            rows = rows.filter(**{owner: owner_id})
        names.update(rows.values_list(field, flat=True))
    return names


def remove_unreferenced_files(candidates) -> list[str]:
    """Remove stored files that no remaining record references (after a user delete)."""
    from django.core.files.storage import default_storage

    referenced = stored_file_names()
    removed = []
    for name in sorted(set(candidates) - referenced):
        try:
            default_storage.delete(name)
            removed.append(name)
        except OSError:
            pass  # the record is gone; a locked file stays until the next reset
    return removed


def raw_upload_cleanup_enabled() -> bool:
    return bool(getattr(settings, "ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION", False))


def purge_uploaded_file_after_extraction(
    instance,
    field_name: str,
    *,
    reason: str,
    payload_field: str = "extracted_payload",
    update_timestamp: bool = True,
    metadata_filter=None,
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
        return metadata_filter(metadata) if metadata_filter else metadata

    update_fields: set[str] = set()
    if storage_name:
        try:
            field_file.delete(save=False)
            setattr(instance, field_name, "")
            metadata["deleted"] = True
            metadata["deleted_at"] = now
            update_fields.add(field_name)
        except Exception as exc:
            metadata.update(safe_error_details(exc, "Source upload cleanup failed. Please retry.",
                                               logger_name=__name__, field="error"))
    else:
        metadata["deleted"] = True
        metadata["deleted_at"] = now

    if metadata_filter:
        metadata = metadata_filter(metadata)

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
