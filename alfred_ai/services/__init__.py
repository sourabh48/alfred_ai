"""Shared service helpers used across ALFRED apps."""

from .document_extraction import ExtractedDocumentText, extract_document_text
from .pdf_recovery import rebuild_orphaned_pdf


def apply_parser_learning(*args, **kwargs):
    from .parser_learning import apply_parser_learning as _apply_parser_learning

    return _apply_parser_learning(*args, **kwargs)


def record_parser_learning(*args, **kwargs):
    from .parser_learning import record_parser_learning as _record_parser_learning

    return _record_parser_learning(*args, **kwargs)


def record_parser_correction(*args, **kwargs):
    from .parser_learning import record_parser_correction as _record_parser_correction

    return _record_parser_correction(*args, **kwargs)


__all__ = [
    "ExtractedDocumentText",
    "apply_parser_learning",
    "extract_document_text",
    "record_parser_correction",
    "record_parser_learning",
    "rebuild_orphaned_pdf",
]
