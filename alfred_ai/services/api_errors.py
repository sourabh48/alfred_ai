"""Safe public errors with diagnostic references, without exception contents."""
import logging
from uuid import uuid4

from rest_framework import status
from rest_framework.response import Response


def safe_error_response(exc, message, *, logger_name, field="detail", status_code=status.HTTP_400_BAD_REQUEST):
    error_id = uuid4().hex
    exception_type = type(exc).__name__
    logging.getLogger(logger_name).error(
        "API request failed; error_id=%s; exception_type=%s", error_id, exception_type,
        extra={"error_id": error_id, "exception_type": exception_type},
    )
    return Response({field: message, "error_id": error_id}, status=status_code)
