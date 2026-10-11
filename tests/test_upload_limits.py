"""Synthetic HTTP and streamed-byte regressions for shared upload protection."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import time
import zipfile
import subprocess
import sys
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.client import encode_multipart
from django.http import JsonResponse

from apps.career.models import CareerResume
from apps.expenses.models import BankAccount, Expense, StatementUpload


@override_settings(ALFRED_UPLOAD_FILE_BYTES=1024, ALFRED_UPLOAD_REQUEST_BYTES=4096)
class UploadHTTPTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="upload_limits", password="Synthetic123!")
        self.client.force_login(self.user)
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-upload-tests-"))
        self.directory = Path(directory)
        self.enterContext(override_settings(MEDIA_ROOT=directory, FILE_UPLOAD_TEMP_DIR=directory))

    def upload(self, size, **extra):
        return self.client.post("/api/career/resumes/upload/", {
            "resume": SimpleUploadedFile("resume.txt", b"A" * size), **extra})

    def test_below_and_exact_file_boundary_are_accepted_and_temp_files_closed(self):
        for size in (1023, 1024):
            with self.subTest(size=size):
                self.assertEqual(self.upload(size).status_code, 201)
                self.assertFalse(list(self.directory.glob("*.upload*")))
        self.assertEqual(CareerResume.objects.count(), 2)

    def test_oversized_actual_file_is_rejected_before_parser_or_record_write(self):
        with patch("apps.career.views.resume_intelligence.parse") as parser:
            response = self.upload(1025)
        self.assertEqual(response.status_code, 413)
        parser.assert_not_called()
        self.assertEqual(CareerResume.objects.count(), 0)
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertNotIn(str(self.directory), response.content.decode())

    def test_file_count_and_fields_are_bounded(self):
        with override_settings(DATA_UPLOAD_MAX_NUMBER_FILES=1):
            response = self.upload(10, other=SimpleUploadedFile("other.txt", b"B"))
        self.assertEqual(response.status_code, 413)
        with override_settings(DATA_UPLOAD_MAX_NUMBER_FIELDS=1):
            response = self.upload(10, first="x", second="y")
        self.assertEqual(response.status_code, 413)
        self.assertEqual(CareerResume.objects.count(), 0)
        self.assertFalse(list(self.directory.glob("*.upload*")))

    def test_combined_body_and_form_data_limits_reject_without_writes(self):
        with override_settings(ALFRED_UPLOAD_REQUEST_BYTES=1500):
            response = self.upload(900, other=SimpleUploadedFile("other.txt", b"B" * 900))
        self.assertEqual(response.status_code, 413)
        with override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=64):
            response = self.upload(10, description="X" * 65)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(CareerResume.objects.count(), 0)

    def test_every_supported_upload_endpoint_rejects_before_services(self):
        endpoints = (
            ("/api/expenses/import-statement/", "statement"),
            ("/api/loans/import-pdf/", "file"),
            ("/api/loans/1/payoff/", "file"),
            ("/api/investments/import-pdf/", "file"),
            ("/api/career/resumes/upload/", "resume"),
            ("/api/career/recruiter-match/", "attachment"),
            ("/api/integrations/credit-score/upload-report/", "report"),
            ("/api/mobility/bike-documents/upload/", "document_file"),
            ("/api/mobility/bike-services/import/", "service_file"),
        )
        for url, field in endpoints:
            with self.subTest(url=url):
                response = self.client.post(url, {field: SimpleUploadedFile("synthetic.pdf", b"X" * 1025)})
                self.assertEqual(response.status_code, 413)
        self.assertEqual((Expense.objects.count(), BankAccount.objects.count(), StatementUpload.objects.count()), (0, 0, 0))

    def test_authentication_and_csrf_remain_required(self):
        anonymous = Client()
        response = anonymous.post("/api/career/resumes/upload/", {"resume": SimpleUploadedFile("resume.txt", b"Valid")})
        self.assertEqual(response.status_code, 403)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post("/api/career/resumes/upload/", {"resume": SimpleUploadedFile("resume.txt", b"Valid")})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(CareerResume.objects.count(), 0)

    def test_invalid_statement_format_keeps_ordinary_validation(self):
        for filename in ("statement.csv", "statement.xlsx"):
            response = self.client.post("/api/expenses/import-statement/", {"statement": SimpleUploadedFile(filename, b"date,amount\n")})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(StatementUpload.objects.count(), 0)

    def test_parser_failure_cleans_temp_files_and_has_safe_response(self):
        with patch("apps.career.views.resume_intelligence.parse", side_effect=RuntimeError("PRIVATE amount token C:\\secret")), self.assertLogs("alfred_ai.services.upload_limits", level="ERROR") as logs:
            response = self.client.post("/api/career/resumes/upload/", {"resume": SimpleUploadedFile("resume.txt", b"Valid")})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("PRIVATE", response.content.decode())
        self.assertEqual(CareerResume.objects.count(), 0)
        self.assertNotIn("PRIVATE", " ".join(logs.output))
        self.assertIn("error_id", logs.records[0].__dict__)
        self.assertFalse(list(self.directory.glob("*.upload*")))

    def test_low_disk_space_rejects_before_creating_temp_files(self):
        with patch("alfred_ai.services.upload_limits.shutil.disk_usage", return_value=SimpleNamespace(free=0)):
            response = self.upload(10)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertEqual(CareerResume.objects.count(), 0)
        self.assertFalse(list(self.directory.glob("*.upload*")))

    def test_wsgi_missing_or_understated_content_length_is_not_imported(self):
        body = encode_multipart("boundary", {"resume": SimpleUploadedFile("resume.txt", b"Valid")})
        for length in ("", "1", "invalid"):
            response = self.client.generic("POST", "/api/career/resumes/upload/", body,
                content_type="multipart/form-data; boundary=boundary", CONTENT_LENGTH=length)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(CareerResume.objects.count(), 0)

    def test_unavailable_temporary_directory_has_safe_503_response(self):
        with patch("alfred_ai.services.upload_limits.shutil.disk_usage", side_effect=OSError("PRIVATE temporary path")):
            response = self.upload(10)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("PRIVATE", response.content.decode())
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_configuration_fails_closed_and_logs_only_class_and_reference(self):
        for invalid in (0, -1, None, "1024", True):
            with self.subTest(value=invalid), override_settings(ALFRED_UPLOAD_FILE_BYTES=invalid), self.assertLogs("alfred_ai.services.upload_limits", level="ERROR") as logs:
                response = self.upload(10)
                self.assertEqual(response.status_code, 503)
                self.assertIn("error_id", response.json())
                self.assertNotIn(str(self.directory), " ".join(logs.output))
        self.assertEqual(CareerResume.objects.count(), 0)

    def test_heavy_extraction_does_not_hold_an_extra_database_write_transaction(self):
        from django.db import connection
        from apps.career.services import resume_intelligence
        baseline = len(connection.atomic_blocks)
        original = resume_intelligence.parse
        def checked_parse(*args, **kwargs):
            self.assertEqual(len(connection.atomic_blocks), baseline)
            return original(*args, **kwargs)
        with patch("apps.career.views.resume_intelligence.parse", side_effect=checked_parse):
            self.assertEqual(self.upload(20).status_code, 201)
        self.assertEqual(len(connection.atomic_blocks), baseline)

    def test_failure_after_extraction_rolls_back_new_model_writes(self):
        original = CareerResume.objects.create
        def fail_after_write(**fields):
            original(**fields)
            raise RuntimeError("PRIVATE post-write failure")
        with patch("apps.career.views.CareerResume.objects.create", side_effect=fail_after_write):
            response = self.upload(20)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("PRIVATE", response.content.decode())
        self.assertEqual(CareerResume.objects.count(), 0)
        self.assertFalse(list(self.directory.glob("*.upload*")))

    def test_resource_failure_is_not_saved_as_a_loan_review_upload(self):
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        from apps.loans.models import LoanImportDocument, Loan
        with patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=UploadLimitExceeded()):
            response = self.client.post("/api/loans/import-pdf/", {"file": SimpleUploadedFile("loan.pdf", b"%PDF")})
        self.assertEqual(response.status_code, 413)
        self.assertEqual((Loan.objects.count(), LoanImportDocument.objects.count()), (0, 0))
        self.assertFalse(list(self.directory.glob("*.upload*")))

    def test_failed_recruiter_attachment_rolls_back_profile_creation(self):
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        from apps.career.models import CareerProfile
        with patch("apps.career.views.job_intelligence.parse_recruiter_message", side_effect=UploadLimitExceeded()):
            response = self.client.post("/api/career/recruiter-match/", {"attachment": SimpleUploadedFile("job.txt", b"Job")})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(CareerProfile.objects.count(), 0)


class UploadStreamAndResourceTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-parser-tests-"))
        self.directory = Path(directory)
        self.enterContext(override_settings(FILE_UPLOAD_TEMP_DIR=directory))

    def test_stream_counts_actual_chunks_and_stops_at_limit_plus_one(self):
        from alfred_ai.services.upload_limits import CountingStream, UploadLimitExceeded
        source = BytesIO(b"X" * 100000)
        stream = CountingStream(source, 64)
        self.assertEqual(len(stream.read(16)), 16)
        with self.assertRaises(UploadLimitExceeded):
            stream.read()
        self.assertEqual(source.tell(), 65)
        self.assertEqual(CountingStream(BytesIO(b"X" * 64), 64).read(), b"X" * 64)

    def test_unknown_and_understated_length_cannot_bypass_real_multipart_accounting(self):
        from alfred_ai.services.upload_limits import UploadProtectionMiddleware
        class ShortReads(BytesIO):
            def read(self, size=-1):
                return super().read(min(size, 7))
        body = encode_multipart("boundary", {"file": SimpleUploadedFile("test.txt", b"X" * 65)})
        for length in (None, "", "1", "invalid", str(len(body))):
            with self.subTest(length=length), override_settings(ALFRED_UPLOAD_FILE_BYTES=64, ALFRED_UPLOAD_REQUEST_BYTES=1024):
                request = RequestFactory().post("/upload/", body, content_type="multipart/form-data; boundary=boundary")
                request.META["CONTENT_LENGTH"] = length
                # Simulates an already framed chunked/ASGI stream; don't bypass WSGI framing.
                request._stream = ShortReads(body)
                with patch("apps.career.views.resume_intelligence.parse") as parser:
                    response = UploadProtectionMiddleware(lambda _: JsonResponse({"unexpected": True}))(request)
                self.assertEqual(response.status_code, 413)
                parser.assert_not_called()
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_combined_stream_bytes_include_form_fields_and_multipart_overhead(self):
        from alfred_ai.services.upload_limits import UploadProtectionMiddleware
        body = encode_multipart("boundary", {"file": SimpleUploadedFile("one.txt", b"A" * 60),
                                              "other": SimpleUploadedFile("two.txt", b"B" * 60), "note": "X" * 50})
        with override_settings(ALFRED_UPLOAD_FILE_BYTES=64, ALFRED_UPLOAD_REQUEST_BYTES=len(body) - 1):
            request = RequestFactory().post("/upload/", body, content_type="multipart/form-data; boundary=boundary")
            request.META.pop("CONTENT_LENGTH")
            request._stream = BytesIO(body)
            response = UploadProtectionMiddleware(lambda _: JsonResponse({}))(request)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_bounded_file_reader_handles_short_reads_and_ignores_size_metadata(self):
        from alfred_ai.services.upload_limits import read_upload_bytes, UploadLimitExceeded
        class ShortReads(BytesIO):
            size = 1
            def read(self, size=-1):
                return super().read(min(size, 3))
        with override_settings(ALFRED_UPLOAD_FILE_BYTES=64):
            self.assertEqual(read_upload_bytes(ShortReads(b"X" * 64)), b"X" * 64)
            oversized = ShortReads(b"X" * 65)
            with self.assertRaises(UploadLimitExceeded):
                read_upload_bytes(oversized)
            self.assertEqual(oversized.tell(), 0)

    def test_real_worker_csv_compatibility_and_row_limit(self):
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        with override_settings(ALFRED_UPLOAD_TEXT_ROWS=2):
            result = run_bounded_parser("document", b"date,amount\n2026-01-01,10", "synthetic.csv")
            self.assertEqual(result["method"], "plain_text")
            self.assertIn("10", result["text"])
            with self.assertRaises(UploadLimitExceeded):
                run_bounded_parser("document", b"date,amount\n2026-01-01,10\n2026-01-02,20", "synthetic.csv")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_pdf_pages_and_decompressed_stream_budgets(self):
        import fitz
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        with fitz.open() as pdf:
            pdf.new_page()
            pdf.new_page()
            content = pdf.tobytes()
        with override_settings(ALFRED_UPLOAD_PDF_PAGES=1), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", content, "synthetic.pdf")
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.insert_text((20, 20), "Synthetic statement")
            content = pdf.tobytes(deflate=True)
        with override_settings(ALFRED_UPLOAD_EXPANDED_BYTES=8), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", content, "synthetic.pdf")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_archive_actual_expansion_and_member_limits(self):
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        source = BytesIO()
        with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("word/document.xml", b"<root>" + b"X" * 1000 + b"</root>")
            archive.writestr("unused/data", b"X" * 1000)
        with override_settings(ALFRED_UPLOAD_EXPANDED_BYTES=100), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", source.getvalue(), "synthetic.docx")
        with override_settings(ALFRED_UPLOAD_ARCHIVE_MEMBERS=1), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", source.getvalue(), "synthetic.docx")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_image_pixel_budget_before_ocr(self):
        from PIL import Image
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        content = BytesIO()
        Image.new("RGB", (5, 5)).save(content, format="PNG")
        with override_settings(ALFRED_UPLOAD_IMAGE_PIXELS=24), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", content.getvalue(), "synthetic.png")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_real_parser_timeout_kills_child_and_cleans_job_files(self):
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        started = time.monotonic()
        with override_settings(ALFRED_UPLOAD_PARSER_SECONDS=1), patch("alfred_ai.services.bounded_parser.WORKER_SOURCE", "import time; time.sleep(30)"), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", b"Valid", "synthetic.txt")
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_worker_failure_uses_static_error_and_cleans_files(self):
        from alfred_ai.services.bounded_parser import run_bounded_parser
        source = "import pathlib,sys; pathlib.Path(sys.argv[1], 'output.json').write_text('{\"error\":\"parser\"}')"
        with patch("alfred_ai.services.bounded_parser.WORKER_SOURCE", source), self.assertRaisesRegex(RuntimeError, "^Local document extraction failed\\.$"):
            run_bounded_parser("document", b"Valid", "synthetic.txt")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_worker_input_is_streamed_bounded_and_position_preserved(self):
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        class LimitedReads(BytesIO):
            def read(self, size=-1):
                if size < 0 or size > 65536:
                    raise AssertionError("Unbounded file read")
                return super().read(min(size, 3))
        source = LimitedReads(b"Valid CSV text")
        source.seek(3)
        self.assertEqual(run_bounded_parser("document", source, "synthetic.csv")["text"], "Valid CSV text")
        self.assertEqual(source.tell(), 3)
        with override_settings(ALFRED_UPLOAD_FILE_BYTES=8), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", source, "synthetic.csv")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_extracted_statement_text_is_bounded_before_row_processing(self):
        from alfred_ai.services.upload_limits import UploadLimitExceeded
        from apps.expenses.services.statement_import import parse_bank_statement, StatementTextExtraction
        extraction = StatementTextExtraction(text="header\nrow\nrow", notes=[], preview_only=False)
        with override_settings(ALFRED_UPLOAD_TEXT_ROWS=2), patch("apps.expenses.services.statement_import._extract_statement_text", return_value=extraction), self.assertRaises(UploadLimitExceeded):
            parse_bank_statement(BytesIO(b"%PDF synthetic"))

    def test_windows_worker_memory_limit_is_actually_enforced(self):
        if sys.platform != "win32":
            self.skipTest("Windows Job Object proof")
        source = """from django.conf import settings
settings.configure()
from alfred_ai.services.bounded_parser import _limit_worker_memory
job = _limit_worker_memory(128 * 1024 * 1024)
try:
    allocation = bytearray(256 * 1024 * 1024)
except MemoryError:
    print('bounded')
else:
    raise SystemExit(9)
"""
        completed = subprocess.run([sys.executable, "-c", source], capture_output=True, text=True, timeout=15)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "bounded")

    def test_invalid_archive_format_and_parser_output_budget(self):
        from alfred_ai.services.bounded_parser import run_bounded_parser
        from alfred_ai.services.upload_limits import UploadFormatError, UploadLimitExceeded
        with self.assertRaises(UploadFormatError):
            run_bounded_parser("document", b"not a ZIP archive", "synthetic.docx")
        with override_settings(ALFRED_UPLOAD_PARSER_OUTPUT_BYTES=1), self.assertRaises(UploadLimitExceeded):
            run_bounded_parser("document", b"Valid document", "synthetic.txt")
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_real_native_transport_rejects_chunked_and_content_length_oversize(self):
        import threading
        import http.client
        from alfred_ai.services.native_web import create_native_server
        with override_settings(ALFRED_UPLOAD_FILE_BYTES=64, ALFRED_UPLOAD_REQUEST_BYTES=128):
            server = create_native_server(lambda environ, start: (start("200 OK", [("Content-Type", "text/plain")]), [b"OK"])[1], 0)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        try:
            for chunked in (False, True):
                with self.subTest(chunked=chunked):
                    connection = http.client.HTTPConnection("127.0.0.1", int(server.effective_port), timeout=5)
                    if chunked:
                        connection.request("POST", "/upload", body=iter([b"X" * 64, b"X" * 65]), encode_chunked=True)
                    else:
                        # Waitress rejects an excessive declared length before the body.
                        # Sending that body anyway races its Connection: close on Windows.
                        connection.putrequest("POST", "/upload")
                        connection.putheader("Content-Length", "129")
                        connection.endheaders()
                    response = connection.getresponse()
                    self.assertEqual(response.status, 413)
                    response.read()
                    connection.close()
        finally:
            server.task_dispatcher.shutdown()
            server.close()
            thread.join(timeout=5)
