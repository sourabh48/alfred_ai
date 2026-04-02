from io import BytesIO

from django.test import SimpleTestCase
from pypdf import PdfReader

from alfred_ai.services.pdf_recovery import rebuild_orphaned_pdf


BROKEN_MINIMAL_PDF = b"""%PDF-1.7
3 0 obj
<< /Length 42 >>
stream
BT /F1 12 Tf 72 720 Td (Hello) Tj ET
endstream
endobj
4 0 obj
<< /Font << /F1 5 0 R >> >>
endobj
5 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
6 0 obj
<< /Contents [ 3 0 R ] /MediaBox [ 0 0 612 792 ] /Parent 2 0 R /Resources 4 0 R /Type /Page >>
endobj
"""


class PdfRecoveryTests(SimpleTestCase):
    def test_rebuild_orphaned_pdf_restores_catalog_and_pages(self):
        recovered = rebuild_orphaned_pdf(BROKEN_MINIMAL_PDF)

        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.page_count, 1)
        self.assertIn(b"startxref", recovered.repaired_bytes)
        self.assertIn(b"/Type /Catalog", recovered.repaired_bytes)

        reader = PdfReader(BytesIO(recovered.repaired_bytes))
        self.assertEqual(len(reader.pages), 1)
