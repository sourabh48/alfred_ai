"""Time/memory-bound local extraction using the existing frozen-worker entrypoint."""
from dataclasses import asdict
from dataclasses import is_dataclass
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import zipfile

from django.conf import settings
from alfred_private_storage import private_directory

from .ocr_process import hidden_process_options, ocr_command
from .upload_limits import DEFAULTS, UploadFormatError, UploadLimitExceeded, UploadProtectionUnavailable, check_document_resources, check_text_budget, limit, upload_deadline
from .api_errors import safe_error_details
from .upload_limits import begin_upload_writes


WORKER_SOURCE = """import json, sys
from pathlib import Path
from django.conf import settings
job = json.loads((Path(sys.argv[1]) / 'job.json').read_text(encoding='utf-8'))
settings.configure(**job['limits'], ALFRED_BOUNDED_PARSER_WORKER=True)
from alfred_ai.services.bounded_parser import run_worker
run_worker(sys.argv[1])
"""


def run_bounded_parser(kind, raw_bytes, filename, **options):
    timeout = min(limit("ALFRED_UPLOAD_PARSER_SECONDS"), (upload_deadline.get() or float("inf")) - time.monotonic())
    if timeout <= 0:
        raise UploadLimitExceeded()
    with tempfile.TemporaryDirectory(prefix="alfred-parser-", dir=settings.FILE_UPLOAD_TEMP_DIR) as directory:
        root = private_directory(Path(directory))
        source = BytesIO(raw_bytes) if isinstance(raw_bytes, bytes) else raw_bytes
        position = source.tell()
        total = 0
        try:
            source.seek(0)
            with (root / "input").open("wb") as output:
                while chunk := source.read(min(65536, limit("ALFRED_UPLOAD_FILE_BYTES") - total + 1)):
                    total += len(chunk)
                    if total > limit("ALFRED_UPLOAD_FILE_BYTES"):
                        raise UploadLimitExceeded()
                    output.write(chunk)
        finally:
            source.seek(position)
        job = {"kind": kind, "filename": filename, "options": options,
               "limits": {name: limit(name) for name in DEFAULTS}}
        (root / "job.json").write_text(json.dumps(job), encoding="utf-8")
        try:
            completed = subprocess.run(ocr_command("bounded", WORKER_SOURCE, directory, 1),
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       timeout=timeout, **hidden_process_options())
        except subprocess.TimeoutExpired:
            raise UploadLimitExceeded() from None
        output = root / "output.json"
        if not output.exists():
            # Includes hard memory-limit termination; never ingest partial extraction.
            safe_error_details(RuntimeError(), "Parser exited without a result.", logger_name=__name__)
            raise UploadLimitExceeded()
        if output.stat().st_size > limit("ALFRED_UPLOAD_PARSER_OUTPUT_BYTES"):
            raise UploadLimitExceeded()
        result = json.loads(output.read_text(encoding="utf-8"))
        if result.get("error") == "limit":
            raise UploadLimitExceeded()
        if result.get("error") == "format":
            raise UploadFormatError()
        if result.get("error") == "protection":
            safe_error_details(OSError(), UploadProtectionUnavailable.default_detail, logger_name=__name__)
            raise UploadProtectionUnavailable()
        if completed.returncode or result.get("error"):
            raise RuntimeError("Local document extraction failed.")
        if kind != "credit_metadata":
            begin_upload_writes()
        return result["result"]


def _limit_worker_memory(maximum):
    if os.name != "nt":
        # ponytail: per-process POSIX limit; add tree termination before a POSIX release.
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (maximum, maximum))
        return None
    # Windows Job Objects impose a real commit-memory limit, unlike working-set hints.
    import ctypes
    from ctypes import wintypes

    class BasicLimits(ctypes.Structure):
        _fields_ = [("ProcessTime", ctypes.c_longlong), ("JobTime", ctypes.c_longlong),
                    ("Flags", wintypes.DWORD), ("MinWorkingSet", ctypes.c_size_t),
                    ("MaxWorkingSet", ctypes.c_size_t), ("ActiveProcesses", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t), ("Priority", wintypes.DWORD), ("Scheduling", wintypes.DWORD)]

    class ExtendedLimits(ctypes.Structure):
        _fields_ = [("Basic", BasicLimits), ("IOCounters", ctypes.c_ulonglong * 6),
                    ("ProcessMemory", ctypes.c_size_t), ("JobMemory", ctypes.c_size_t),
                    ("PeakProcessMemory", ctypes.c_size_t), ("PeakJobMemory", ctypes.c_size_t)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    job = kernel.CreateJobObjectW(None, None)
    limits = ExtendedLimits()
    # Child OCR workers inherit the job; closing it on worker death kills children.
    limits.Basic.Flags = 0x100 | 0x200 | 0x2000
    limits.ProcessMemory = maximum
    limits.JobMemory = maximum
    if not job or not kernel.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job, kernel.GetCurrentProcess()):
        raise OSError("Parser memory protection unavailable.")
    return job  # Retain the handle for the worker lifetime.


def run_worker(directory):
    root = Path(directory)
    job = json.loads((root / "job.json").read_text(encoding="utf-8"))
    # No local.env, application initialization, credentials or database access.
    if not settings.configured:
        settings.configure(**job["limits"], ALFRED_BOUNDED_PARSER_WORKER=True)
    tempfile.tempdir = str(root)
    try:
        memory_job = _limit_worker_memory(job["limits"]["ALFRED_UPLOAD_PARSER_MEMORY_BYTES"])
        raw_bytes = (root / "input").read_bytes()
        check_document_resources(raw_bytes, job["filename"])
        if job["kind"] == "statement":
            from apps.expenses.services.statement_import import _extract_statement_text
            result = _extract_statement_text(raw_bytes, **job["options"], enable_isolated_ocr=True)
        elif job["kind"] == "document":
            from .document_extraction import extract_document_text
            result = extract_document_text(raw_bytes, job["filename"], **job["options"])
        elif job["kind"] == "credit_metadata":
            from io import BytesIO
            from pypdf import PdfReader
            try:
                metadata = PdfReader(BytesIO(raw_bytes)).metadata or {}
            except Exception:
                metadata = {}
            result = {"title": str(metadata.get("/Title") or "").strip(),
                      "author": str(metadata.get("/Author") or "").strip()}
        else:
            raise ValueError("Unsupported local parser.")
        if is_dataclass(result):
            check_text_budget(result.text)
        payload = json.dumps({"result": asdict(result) if is_dataclass(result) else result}, ensure_ascii=True)
        if len(payload.encode("utf-8")) > job["limits"]["ALFRED_UPLOAD_PARSER_OUTPUT_BYTES"]:
            raise UploadLimitExceeded()
    except (UploadLimitExceeded, MemoryError):
        payload = '{"error":"limit"}'
    except (zipfile.BadZipFile, zipfile.LargeZipFile):
        payload = '{"error":"format"}'
    except OSError:
        payload = '{"error":"protection"}'
    except Exception:
        payload = '{"error":"parser"}'
    (root / "output.json").write_text(payload, encoding="utf-8")
