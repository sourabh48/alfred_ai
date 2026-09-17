"""Real extraction of unusual, generated layouts with known text references.

These fixtures exercise parsing mechanics, not real-world model accuracy.
"""
from io import BytesIO
import zipfile

from django.test import SimpleTestCase
import fitz

from alfred_ai.services.document_extraction import extract_document_text


class DocumentLayoutTests(SimpleTestCase):
    def check_reference(self, content, filename):
        result = extract_document_text(content, filename)
        for value in ("INV-90812", "12,345.50", "2026-09-18"):
            self.assertIn(value, result.text, (filename, result.method, result.text[:1000]))
        self.assertTrue(result.review_payload["field_candidates"], filename)

    def test_rotated_pdf_page_preserves_invoice_fields(self):
        with fitz.open() as document:
            page = document.new_page()
            page.insert_text((60, 80), "Invoice Number INV-90812\nTotal INR 12,345.50\nDate 2026-09-18", fontsize=15)
            page.set_rotation(90)
            self.check_reference(document.tobytes(), "rotated-invoice.pdf")

    def test_two_column_pdf_with_repeated_headers(self):
        with fitz.open() as document:
            for _ in range(2):
                page = document.new_page()
                page.insert_text((40, 60), "Invoice Number INV-90812", fontsize=12)
                page.insert_text((340, 60), "Date 2026-09-18", fontsize=12)
                page.insert_text((40, 140), "Description: vehicle service", fontsize=12)
                page.insert_text((340, 140), "Total INR 12,345.50", fontsize=12)
            self.check_reference(document.tobytes(), "two-column-invoice.pdf")

    def test_landscape_pdf_table_with_wrapped_description(self):
        with fitz.open() as document:
            page = document.new_page(width=842, height=595)
            for x in (50, 420, 740):
                page.draw_line((x, 65), (x, 195))
            for y in (65, 110, 150, 195):
                page.draw_line((50, y), (740, y))
            page.insert_text((60, 90), "Invoice Number INV-90812", fontsize=14)
            page.insert_text((430, 90), "Date 2026-09-18", fontsize=14)
            page.insert_text((60, 130), "Scheduled maintenance and\nreplacement service parts", fontsize=12)
            page.insert_text((430, 175), "Total INR 12,345.50", fontsize=14)
            self.check_reference(document.tobytes(), "landscape-invoice.pdf")

    def test_docx_table_and_split_runs_keep_fields(self):
        output = BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("word/document.xml", '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
            <w:p><w:r><w:t>Invoice Number </w:t></w:r><w:r><w:t>INV-90812</w:t></w:r></w:p>
            <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Total INR 12,345.50</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>Date 2026-09-18</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
            </w:body></w:document>''')
        self.check_reference(output.getvalue(), "table-invoice.docx")

    def test_html_nested_table_entities_keep_fields(self):
        self.check_reference(b"<html><table><tr><td>Invoice&nbsp;Number INV-90812</td>"
                             b"<td><b>Total INR 12,345.50</b></td></tr></table><p>Date 2026-09-18</p></html>",
                             "nested-invoice.html")
