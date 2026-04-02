from celery import shared_task

from .models import StatementUpload
from .services.statement_lifecycle import retry_statement_upload


@shared_task
def retry_statement_upload_task(upload_id: int, ocr_page_limit: int = 8):
    upload = StatementUpload.objects.filter(pk=upload_id).first()
    if upload is None:
        return {"status": "missing"}
    result = retry_statement_upload(upload, ocr_page_limit=ocr_page_limit)
    if result is None:
        return {"status": "skipped"}
    return {
        "status": "ok",
        "upload_id": upload_id,
        "imported_count": result.new_import_count,
        "parser_status": result.upload.parser_status,
    }


@shared_task
def retry_low_confidence_statement_uploads(batch_size: int = 3):
    uploads = list(
        StatementUpload.objects.filter(parser_status__in=["failed", "needs_review"], imported_count=0)
        .exclude(original_file="")
        .order_by("uploaded_at", "id")[:batch_size]
    )
    results = []
    for upload in uploads:
        retry_state = ((upload.extracted_payload or {}).get("background_retry") or {})
        current_limit = int(retry_state.get("ocr_page_limit") or 4)
        next_limit = min(max(current_limit * 2, 4), 128)
        outcome = retry_statement_upload(upload, ocr_page_limit=next_limit)
        results.append(
            {
                "upload_id": upload.id,
                "imported_count": 0 if outcome is None else outcome.new_import_count,
                "parser_status": upload.parser_status if outcome is None else outcome.upload.parser_status,
                "ocr_page_limit": next_limit,
            }
        )
    return {"status": "ok", "processed": len(results), "results": results}
