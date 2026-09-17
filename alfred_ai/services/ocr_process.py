"""Run the existing isolated OCR routines from Python or the frozen launcher."""
import os
import subprocess
import sys


def ocr_command(kind, source, path, pages):
    if getattr(sys, "frozen", False):
        return [sys.executable, "--ocr-worker", kind, path, str(max(pages, 1))]
    return [sys.executable, "-c", source, path, str(max(pages, 1))]


def hidden_process_options():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def run_frozen_worker(arguments):
    kind, path, pages = arguments
    if kind == "document":
        from alfred_ai.services.document_extraction import ISOLATED_PDF_OCR_WORKER as source
    elif kind == "statement":
        from apps.expenses.services.statement_import import ISOLATED_OCR_WORKER as source
    else:
        raise ValueError("Unknown OCR worker")
    sys.argv = ["-c", path, pages]
    exec(compile(source, "<isolated-ocr>", "exec"), {"__name__": "__main__"})
    return 0
