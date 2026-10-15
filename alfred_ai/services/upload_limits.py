"""Shared streamed upload limits; no filenames or contents in diagnostics."""
from contextvars import ContextVar
from contextlib import ExitStack
from io import BytesIO
from functools import wraps
from pathlib import Path
import os
import shutil
import tempfile
import time
import zipfile

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent
from django.core.files.uploadhandler import FileUploadHandler, TemporaryFileUploadHandler
from django.core.files.uploadedfile import UploadedFile, TemporaryUploadedFile
from django.core.files import temp as django_tempfile
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.db import transaction
from rest_framework.exceptions import APIException

from .api_errors import safe_error_details
from alfred_ai.upload_config import UPLOAD_LIMIT_DEFAULTS as DEFAULTS
from alfred_private_storage import protect, private_directory, PrivateStorageUnavailable


upload_deadline = ContextVar("upload_deadline", default=None)
upload_transaction = ContextVar("upload_transaction", default=None)


def begin_upload_writes():
    scope = upload_transaction.get()
    if scope is not None and not scope["active"]:
        scope["stack"].enter_context(transaction.atomic())
        scope["active"] = True


def parser_budget(function):
    @wraps(function)
    def bounded(*args, **kwargs):
        token = upload_deadline.set(upload_deadline.get() or time.monotonic() + limit("ALFRED_UPLOAD_PARSER_SECONDS"))
        try:
            return function(*args, **kwargs)
        finally:
            upload_deadline.reset(token)
    return bounded


def limit(name):
    value = getattr(settings, name, DEFAULTS[name])
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ImproperlyConfigured("Upload limits must be positive integers.")
    return value


def validate_limits():
    for name in DEFAULTS:
        limit(name)
    if limit("ALFRED_UPLOAD_FILE_BYTES") > limit("ALFRED_UPLOAD_REQUEST_BYTES"):
        raise ImproperlyConfigured("The upload file limit must not exceed the request limit.")
    for name in ("DATA_UPLOAD_MAX_NUMBER_FILES", "DATA_UPLOAD_MAX_NUMBER_FIELDS", "DATA_UPLOAD_MAX_MEMORY_SIZE"):
        value = getattr(settings, name)
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ImproperlyConfigured("Multipart limits must be positive integers.")


class UploadLimitExceeded(APIException):
    status_code = 413
    default_detail = "Upload exceeds the configured size or processing limits. Use a smaller document."
    default_code = "upload_limit"


class UploadStorageUnavailable(APIException):
    status_code = 503
    default_detail = "Upload temporary storage is unavailable. Please retry later."


class UploadProtectionUnavailable(APIException):
    status_code = 503
    default_detail = "Document processing protection is unavailable. Please retry later."


class UploadFormatError(APIException):
    status_code = 400
    default_detail = "Document format is invalid or unsupported. Check the file and try again."


class CountingStream:
    """Count the actual framed stream, including boundaries and form fields."""
    def __init__(self, stream, maximum):
        self.stream, self.maximum, self.count = stream, maximum, 0

    def _read(self, method, size):
        remaining = self.maximum - self.count + 1
        size = remaining if size is None or size < 0 else min(size, remaining)
        data = method(size)
        self.count += len(data)
        if self.count > self.maximum:
            raise UploadLimitExceeded()
        return data

    def read(self, size=-1):
        return self._read(self.stream.read, size)

    def readline(self, size=-1):
        return self._read(self.stream.readline, size)


class BoundedUploadHandler(FileUploadHandler):
    """Check decoded file chunks before Django writes them to temporary storage."""
    def new_file(self, *args, **kwargs):
        try:
            free = shutil.disk_usage(settings.FILE_UPLOAD_TEMP_DIR or tempfile.gettempdir()).free
        except OSError:
            raise UploadStorageUnavailable() from None
        if free < limit("ALFRED_UPLOAD_MIN_FREE_BYTES") + limit("ALFRED_UPLOAD_REQUEST_BYTES"):
            raise UploadStorageUnavailable()
        super().new_file(*args, **kwargs)
        self.received = 0

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > limit("ALFRED_UPLOAD_FILE_BYTES"):
            raise UploadLimitExceeded()
        return raw_data

    def file_complete(self, file_size):
        return None


class PrivateTemporaryUploadedFile(TemporaryUploadedFile):
    def __init__(self, name, content_type, size, charset, content_type_extra):
        self._private_directory = tempfile.TemporaryDirectory(prefix='alfred-upload-', dir=settings.FILE_UPLOAD_TEMP_DIR)
        stream = None
        try:
            root = private_directory(Path(self._private_directory.name))
            stream = django_tempfile.NamedTemporaryFile(suffix='.upload' + os.path.splitext(name)[1], dir=root)
            UploadedFile.__init__(self, stream, name, content_type, size, charset, content_type_extra)
        except BaseException:
            if stream is not None:
                stream.close()
            self._private_directory.cleanup()
            raise

    def close(self):
        try:
            super().close()
        finally:
            self._private_directory.cleanup()


class PrivateTemporaryUploadHandler(TemporaryFileUploadHandler):
    def new_file(self, *args, **kwargs):
        FileUploadHandler.new_file(self, *args, **kwargs)
        try:
            self.file = PrivateTemporaryUploadedFile(self.file_name, self.content_type, 0,
                                                    self.charset, self.content_type_extra)
            protect(Path(self.file.temporary_file_path()))
        except (OSError, ValueError, PrivateStorageUnavailable) as exc:
            safe_error_details(exc, UploadStorageUnavailable.default_detail, logger_name=__name__)
            if hasattr(self, 'file'):
                self.file.close()
            raise UploadStorageUnavailable() from None


def read_upload_bytes(upload):
    """Installed document libraries need bytes; keep that allocation bounded."""
    position = upload.tell() if hasattr(upload, "tell") else None
    try:
        if hasattr(upload, "seek"):
            upload.seek(0)
        chunks, total = [], 0
        while chunk := upload.read(min(65536, limit("ALFRED_UPLOAD_FILE_BYTES") - total + 1)):
            total += len(chunk)
            if total > limit("ALFRED_UPLOAD_FILE_BYTES"):
                raise UploadLimitExceeded()
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        if position is not None:
            upload.seek(position)


def document_source(upload):
    # HTTP/retry extraction passes a stream to the worker, avoiding a parent RAM copy.
    return upload if upload_deadline.get() is not None else read_upload_bytes(upload)


def check_text_budget(text):
    if len(text.encode("utf-8")) > limit("ALFRED_UPLOAD_TEXT_BYTES") or text.count("\n") + 1 > limit("ALFRED_UPLOAD_TEXT_ROWS"):
        raise UploadLimitExceeded()


def check_document_resources(raw_bytes, filename):
    """Preflight supported containers inside the time-bounded parser process."""
    if len(raw_bytes) > limit("ALFRED_UPLOAD_FILE_BYTES"):
        raise UploadLimitExceeded()
    extension = os.path.splitext(filename.lower())[1]
    if extension in {".docx", ".odt"}:
        with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
            members = archive.infolist()
            if len(members) > limit("ALFRED_UPLOAD_ARCHIVE_MEMBERS"):
                raise UploadLimitExceeded()
            total = 0
            for member in members:
                if member.file_size > limit("ALFRED_UPLOAD_EXPANDED_BYTES") - total:
                    raise UploadLimitExceeded()
                # Count actual decompression, including unused members; never extract paths.
                with archive.open(member) as source:
                    while chunk := source.read(min(65536, limit("ALFRED_UPLOAD_EXPANDED_BYTES") - total + 1)):
                        total += len(chunk)
                        if total > limit("ALFRED_UPLOAD_EXPANDED_BYTES"):
                            raise UploadLimitExceeded()
    elif raw_bytes.startswith(b"%PDF"):
        import fitz
        try:
            document = fitz.open(stream=raw_bytes, filetype="pdf")
        except (fitz.FileDataError, RuntimeError):
            # Existing damaged-PDF recovery remains available in the bounded worker.
            return
        with document:
            if (document.page_count > limit("ALFRED_UPLOAD_PDF_PAGES")
                    or document.xref_length() > limit("ALFRED_UPLOAD_PDF_OBJECTS")):
                raise UploadLimitExceeded()
            # Avoid enormous raster allocations before OCR renders pages at 2x.
            for page in document:
                if page.rect.width * page.rect.height * 4 > limit("ALFRED_UPLOAD_IMAGE_PIXELS"):
                    raise UploadLimitExceeded()
            expanded = 0
            for xref in range(1, document.xref_length()):
                if document.xref_is_stream(xref):
                    expanded += len(document.xref_stream(xref))
                    if expanded > limit("ALFRED_UPLOAD_EXPANDED_BYTES"):
                        raise UploadLimitExceeded()
    elif extension in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"} or raw_bytes.startswith((b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"II*\0", b"MM\0*")):
        from PIL import Image
        with Image.open(BytesIO(raw_bytes)) as image:
            if image.width * image.height > limit("ALFRED_UPLOAD_IMAGE_PIXELS"):
                raise UploadLimitExceeded()
    elif extension in {".txt", ".md", ".csv", ".log", ".rtf", ".html", ".htm", ".xml"}:
        if len(raw_bytes) > limit("ALFRED_UPLOAD_TEXT_BYTES") or raw_bytes.count(b"\n") + 1 > limit("ALFRED_UPLOAD_TEXT_ROWS"):
            raise UploadLimitExceeded()


class UploadProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in {"POST", "PUT", "PATCH"} or request.content_type != "multipart/form-data":
            return self.get_response(request)
        request._bounded_upload = True
        token = None
        write_token = None
        writes = {"stack": ExitStack(), "active": False}
        success = False
        try:
            validate_limits()
            maximum = limit("ALFRED_UPLOAD_REQUEST_BYTES")
            try:
                declared = int(request.META.get("CONTENT_LENGTH") or 0)
            except (TypeError, ValueError):
                declared = 0
            if declared > maximum:
                raise UploadLimitExceeded()
            request._stream = CountingStream(request._stream, maximum)
            meta = {**request.META, "CONTENT_LENGTH": str(max(declared, 1))}
            # Parse before CSRF can access POST. CSRF/auth still gate the view.
            request._post, request._files = MultiPartParser(meta, request, request.upload_handlers, request.encoding).parse()
            token = upload_deadline.set(time.monotonic() + limit("ALFRED_UPLOAD_PARSER_SECONDS"))
            write_token = upload_transaction.set(writes)
            response = self.get_response(request)
            success = response.status_code < 400
            return response
        except (UploadLimitExceeded, RequestDataTooBig, TooManyFieldsSent, TooManyFilesSent):
            return JsonResponse({"detail": UploadLimitExceeded.default_detail}, status=413)
        except (UploadStorageUnavailable, UploadProtectionUnavailable, UploadFormatError) as exc:
            return JsonResponse({"detail": exc.default_detail}, status=exc.status_code)
        except MultiPartParserError:
            return JsonResponse({"detail": "Upload form is malformed."}, status=400)
        except ImproperlyConfigured as exc:
            return JsonResponse(safe_error_details(exc, "Upload protection is unavailable. Please retry later.", logger_name=__name__), status=503)
        except OSError as exc:
            return JsonResponse(safe_error_details(exc, UploadStorageUnavailable.default_detail, logger_name=__name__), status=503)
        finally:
            # Open the write transaction only after heavy extraction succeeds.
            # SQLite IMMEDIATE must not reserve its writer during up to 90s of OCR.
            commit_error = None
            try:
                if writes["active"] and not success:
                    transaction.set_rollback(True)
                writes["stack"].close()
            except Exception as exc:
                commit_error = safe_error_details(exc, "Document processing failed. Please retry.", logger_name=__name__)
            finally:
                if write_token is not None:
                    upload_transaction.reset(write_token)
                if token is not None:
                    upload_deadline.reset(token)
            # Django closes completed files; include the active incomplete handler too.
            files_to_close = [handler.file for handler in request.upload_handlers if getattr(handler, "file", None) is not None]
            if hasattr(request, "_files"):
                for _, files in request._files.lists():
                    files_to_close.extend(files)
            for file in files_to_close:
                try:
                    file.close()
                except OSError as exc:
                    safe_error_details(exc, "Temporary upload cleanup failed.", logger_name=__name__)
            if commit_error is not None:
                return JsonResponse(commit_error, status=500)

    def process_exception(self, request, exception):
        if getattr(request, "_bounded_upload", False):
            if isinstance(exception, (UploadLimitExceeded, UploadStorageUnavailable, UploadProtectionUnavailable, UploadFormatError)):
                return JsonResponse({"detail": exception.default_detail}, status=exception.status_code)
            if isinstance(exception, OSError):
                return JsonResponse(safe_error_details(exception, UploadStorageUnavailable.default_detail, logger_name=__name__), status=503)
            return JsonResponse(safe_error_details(exception, "Document processing failed. Please retry.", logger_name=__name__), status=500)
