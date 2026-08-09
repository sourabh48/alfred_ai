from __future__ import annotations

import logging
import re
from collections.abc import Mapping, Sequence


ROUTE_VALUE_PATTERN = re.compile(
    r"https?://[^\s\"')<>]+|(?<![A-Za-z0-9])/(?:[A-Za-z0-9._~%!$&'()*+,;=:@-]+/?)+"  # noqa: W605
)


def sanitize_log_record_value(value):
    if isinstance(value, str):
        return ROUTE_VALUE_PATTERN.sub("[redacted-url]", value)
    if isinstance(value, Mapping):
        return {
            key: sanitize_log_record_value(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(sanitize_log_record_value(item) for item in value)
    if isinstance(value, list):
        return [sanitize_log_record_value(item) for item in value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return type(value)(sanitize_log_record_value(item) for item in value)
    return value


class RedactRouteFilter(logging.Filter):
    """Redact URL/path-like values before operational logs are emitted."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = sanitize_log_record_value(record.msg)
        record.args = sanitize_log_record_value(record.args)
        return True
