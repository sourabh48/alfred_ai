from io import BytesIO
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.mobility.services.bike_document_ai import BikeDocumentAI


SAMPLE_INVOICE_TEXT = """
Customer Name
Sourabh Sarkar
Service Consultant
Israel S
Address
C405, Sanjeevini Sruti, Soukya Road,
Kachrakanahalli village,Whitefield, ,HOSAKOTE
Model Code
VSKM60HE
Registration Number
Ka01kc6667
Job Card Number
RJC011402IJ11758
Model Name
HUNTER 350 DAPPER GREEN
Job Card Date
10-08-2025 12:20
Odometer Reading
26,021
Invoice Date
Recipient GSTIN
Service Centre
Jagadamba Automobiles
Engine Number
J3A5FCR1223168
Supplier GSTIN
29ATMPJ3615M1Z7
Chassis Number
ME3J3D5FCR1005699
Customer Voice
Paid service
1050
1
engine oil & filter change
750
2
chain lube
170
3
.consumables
120
4
.back rear brake pad replacement
370
5
.clutch cable check and inform to customer
7077927159
Surya
Service Pre-Invoice
Code
Description
Qty
Price
Discount
Amount
CGST/SGST
(%)
CGST
SGST
IGST
(%)
IGST
Customer
Amount
Amount
3600027
LIQUID GUN SEMI
SYNTHETIC-15W50- 210
LTS
1.70
330.51
\u20b9 0.00
9.00
50.57
\u20b9 50.57
0.00
\u20b9 0.00
\u20b9 663.01
\u20b9 663.01
3600008/A
CHAIN LUBE & CLEANER
KIT- 500ML.
85.00
1.69
\u20b9 0.00
9.00
12.93
\u20b9 12.93
0.00
\u20b9 0.00
\u20b9 169.51
\u20b9 169.51
1570120/B
FILTER COMP-ENGINE OIL
1.00
80.51
\u20b9 0.00
9.00
7.25
\u20b9 7.25
0.00
\u20b9 0.00
\u20b9 95.00
\u20b9 95.01
KAB00246/
A
BRAKE PAD KIT
1.00
226.56
\u20b9 0.00
14.00
31.72
\u20b9 31.72
0.00
\u20b9 0.00
\u20b9 290.00
\u20b9 290.00
Total
\u20b9 1217.52
\u20b9 1217.53
Labour Description
Code
Description
Hrs
Price
Discount
Amount
CGST/SGST
(%)
CGST
SGST
IGST
(%)
IGST
Customer
Amount
Amount
GELA017
CONSUMABLE CHARGES
FOR SERVICE
1.00
\u20b9 100.00
\u20b9 0.00
9.00
\u20b9 9.00
\u20b9 9.00
0.00
\u20b9 0.00
\u20b9 118.00
\u20b9 118.00
WBRB007
R&R REAR BRAKE SHOES
/ PADS (INCLUS OF
WHEEL REMOVAL FOR
DRUM BRAKE)
0.12
\u20b9 500.00
\u20b9 0.00
9.00
\u20b9 5.40
\u20b9 5.40
0.00
\u20b9 0.00
\u20b9 70.80
\u20b9 70.80
DSC7-36M-
30K
SCHEDULED PAID 36
MONTHS OR 30K
KILOMETERS SERVICE
1.00
\u20b9 870.00
\u20b9 0.00
9.00
\u20b9 78.30
\u20b9 78.30
0.00
\u20b9 0.00
\u20b9 1,026.60
\u20b9 1,026.60
Total
\u20b9 1215.40
\u20b9 1215.40
Total Amount
\u20b9 2432.93
Address
:
#11, Eioz Industrial area, SY. no.88, Sadarmangala Village, K.R.Puram Hubli, Bangalore 560066
,
,
BENGALURU
,
,
KARNATAKA
Contact Number:
8879945595
Mobile:
9606468371
Email:
servicewhitefield.jagadamba@gmail.com
Website: www.royalenfield.com
Jagadamba Automobiles
Total Customer Amount
\u20b9 2432.92
""".strip()


class BikeDocumentParserTests(SimpleTestCase):
    @patch.object(BikeDocumentAI, "_extract_text", return_value=SAMPLE_INVOICE_TEXT)
    def test_invoice_parser_extracts_structured_invoice_data(self, _extract_text):
        parser = BikeDocumentAI()
        upload = BytesIO(b"fake-pdf")
        upload.name = "JcPreInvoice.pdf"

        parsed = parser.parse(upload, upload.name)

        self.assertEqual(parsed.document_type, "invoice")
        self.assertEqual(parsed.fields["document_number"], "RJC011402IJ11758")
        self.assertEqual(parsed.fields["issuer"], "Jagadamba Automobiles")
        self.assertEqual(parsed.fields["customer_name"], "Sourabh Sarkar")
        self.assertEqual(parsed.fields["service_consultant"], "Israel S")
        self.assertEqual(parsed.fields["vehicle_number"], "Ka01kc6667")
        self.assertEqual(parsed.fields["odometer_km"], 26021)
        self.assertAlmostEqual(parsed.fields["total_customer_amount"], 2432.92)
        self.assertAlmostEqual(parsed.fields["parts_total_amount"], 1217.53)
        self.assertAlmostEqual(parsed.fields["labour_total_amount"], 1215.4)
        self.assertAlmostEqual(parsed.fields["total_tax_amount"], 390.34)
        self.assertAlmostEqual(parsed.fields["total_taxable_amount"], 2042.59)
        self.assertEqual(parsed.fields["service_center_contact"], "8879945595")
        self.assertEqual(parsed.fields["service_center_email"], "servicewhitefield.jagadamba@gmail.com")
        self.assertEqual(parsed.fields["service_advisor_name"], "Surya")
        self.assertEqual(parsed.fields["service_advisor_contact"], "7077927159")
        self.assertEqual(parsed.fields["parts_item_count"], 4)
        self.assertEqual(parsed.fields["labour_item_count"], 3)
        self.assertEqual(parsed.fields["line_item_count"], 7)
        self.assertIn("engine", parsed.fields["systems_impacted"])
        self.assertIn("brakes", parsed.fields["systems_impacted"])
        self.assertEqual(len(parsed.fields["parts_items"]), 4)
        self.assertEqual(len(parsed.fields["labour_items"]), 3)

        self.assertEqual(parsed.service_payload["service_type"], "routine")
        self.assertEqual(parsed.service_payload["job_card_number"], "RJC011402IJ11758")
        self.assertAlmostEqual(parsed.service_payload["cost"], 2432.92)
        self.assertEqual(parsed.service_payload["odometer_km"], 26021)
        self.assertEqual(parsed.service_payload["service_advisor_name"], "Surya")
        self.assertEqual(parsed.service_payload["line_item_count"], 7)
        self.assertIn("BRAKE PAD KIT", parsed.service_payload["replaced_parts"])
        self.assertIn("brake pad replacement", parsed.service_payload["extracted_work_summary"].lower())
        self.assertIn("line item", parsed.parser_notes.lower())

    @patch.object(BikeDocumentAI, "_extract_text", return_value="""
Service Pre-Invoice
Job Card Number
EDGE-INV-1001
Registration Number
KA01KC6667
Service Centre
Jagadamba Automobiles
Invoice Date
28-03-2026
Odometer Reading
26500
Parts Description
Code
Description
Qty
Customer Amount
BPK001
BRAKE PAD KIT
1.00
820.00
Total 820.00 820.00
Labour Description
Code
Description
Hrs
Customer Amount
LAB001
PERIODIC SERVICE LABOUR
1.00
640.00
Total 640.00 640.00
Total Customer Amount
1460.00
""".strip())
    def test_invoice_parser_recovers_inline_totals_and_short_ocr_rows(self, _extract_text):
        parser = BikeDocumentAI()
        upload = BytesIO(b"fake-pdf")
        upload.name = "edge-invoice.pdf"

        parsed = parser.parse(upload, upload.name)

        self.assertEqual(parsed.document_type, "invoice")
        self.assertEqual(parsed.fields["document_number"], "EDGE-INV-1001")
        self.assertEqual(parsed.fields["service_center_name"], "Jagadamba Automobiles")
        self.assertEqual(parsed.fields["parts_total_amount"], 820.0)
        self.assertEqual(parsed.fields["labour_total_amount"], 640.0)
        self.assertEqual(parsed.fields["total_customer_amount"], 1460.0)
        self.assertEqual(parsed.fields["parts_item_count"], 1)
        self.assertEqual(parsed.fields["labour_item_count"], 1)
        self.assertEqual(parsed.fields["line_item_count"], 2)
        self.assertEqual(parsed.service_payload["line_item_count"], 2)
        self.assertEqual(parsed.service_payload["parts_items"][0]["parse_mode"], "edge_recovered")
        self.assertEqual(parsed.service_payload["labour_items"][0]["parse_mode"], "edge_recovered")
        self.assertEqual(parsed.review_payload["invoice_review"]["recovered_edge_rows"], 2)
        self.assertIn("Recovered 2 invoice line item", parsed.parser_notes)

    @patch.object(BikeDocumentAI, "_extract_text", return_value="""
Service Invoice
Job Card No: EDGE-INV-2002
Registration No: KA01KC6667
Service Center: Jagadamba Automobiles
Invoice Date: 31-03-2026
Odometer: 26500 km
Parts Description
Code Description Qty Customer Amount
BPK001 BRAKE PAD KIT 1 820.00
EOL15W50 ENGINE OIL 1.70 Rs 663.01
Total 1483.01 1483.01
Labour Description
Code Description Hrs Customer Amount
LAB001 PERIODIC SERVICE LABOUR 1 640.00
Total 640.00 640.00
Total Customer Amount: Rs 2123.01
""".strip())
    def test_invoice_parser_recovers_compact_ocr_rows_and_inline_labels(self, _extract_text):
        parser = BikeDocumentAI()
        upload = BytesIO(b"fake-pdf")
        upload.name = "compact-edge-invoice.pdf"

        parsed = parser.parse(upload, upload.name)

        self.assertEqual(parsed.document_type, "invoice")
        self.assertEqual(parsed.fields["document_number"], "EDGE-INV-2002")
        self.assertEqual(parsed.fields["service_center_name"], "Jagadamba Automobiles")
        self.assertEqual(parsed.fields["vehicle_number"], "KA01KC6667")
        self.assertEqual(parsed.fields["invoice_date"], "2026-03-31")
        self.assertEqual(parsed.fields["odometer_km"], 26500)
        self.assertEqual(parsed.fields["parts_item_count"], 2)
        self.assertEqual(parsed.fields["labour_item_count"], 1)
        self.assertEqual(parsed.fields["line_item_count"], 3)
        self.assertAlmostEqual(parsed.fields["parts_customer_amount"], 1483.01)
        self.assertAlmostEqual(parsed.fields["labour_customer_amount"], 640.0)
        self.assertAlmostEqual(parsed.fields["total_customer_amount"], 2123.01)
        self.assertEqual(parsed.service_payload["parts_items"][0]["parse_mode"], "compact_ocr_row")
        self.assertEqual(parsed.service_payload["parts_items"][1]["parse_mode"], "compact_ocr_row")
        self.assertEqual(parsed.service_payload["labour_items"][0]["parse_mode"], "compact_ocr_row")
        self.assertEqual(parsed.review_payload["invoice_review"]["recovered_edge_rows"], 3)
        self.assertEqual(parsed.review_payload["invoice_review"]["compact_ocr_rows"], 3)
        self.assertIn("Recovered 3 invoice line item", parsed.parser_notes)

    @patch.object(BikeDocumentAI, "_extract_text", return_value="""
Service Invoice
Job Card No EDGE INV 3003
Registration No KA 01 KC 6667
Service Center Jagadamba Automobiles
Invoice Date 04 Apr 2026
Odometer Reading 27,140 KM
Parts Description
Code Description Qty Customer Amount
BPK001 BRAKE PAD KIT Qty 1 Customer Amount Rs 820.00
EOL15W50 ENGINE OIL 15W50 Qty 1.70 Amount Rs 663.01
Total Rs 1483.01
Labour Description
Code Description Hrs Customer Amount
LAB001 PERIODIC SERVICE LABOUR Hrs 1 Amount Rs 640.00
Total Rs 640.00
Total Customer Amount Rs 2123.01
""".strip())
    def test_invoice_parser_recovers_label_collapsed_ocr_rows(self, _extract_text):
        parser = BikeDocumentAI()
        upload = BytesIO(b"fake-pdf")
        upload.name = "label-collapsed-invoice.pdf"

        parsed = parser.parse(upload, upload.name)

        self.assertEqual(parsed.document_type, "invoice")
        self.assertEqual(parsed.fields["document_number"], "EDGE INV 3003")
        self.assertEqual(parsed.fields["service_center_name"], "Jagadamba Automobiles")
        self.assertEqual(parsed.fields["invoice_date"], "2026-04-04")
        self.assertEqual(parsed.fields["odometer_km"], 27140)
        self.assertEqual(parsed.fields["parts_item_count"], 2)
        self.assertEqual(parsed.fields["labour_item_count"], 1)
        self.assertEqual(parsed.fields["line_item_count"], 3)
        self.assertAlmostEqual(parsed.fields["parts_customer_amount"], 1483.01)
        self.assertAlmostEqual(parsed.fields["labour_customer_amount"], 640.0)
        self.assertAlmostEqual(parsed.fields["total_customer_amount"], 2123.01)
        self.assertEqual(parsed.service_payload["parts_items"][0]["description"], "BRAKE PAD KIT")
        self.assertEqual(parsed.service_payload["parts_items"][1]["description"], "ENGINE OIL 15W50")
        self.assertEqual(parsed.service_payload["labour_items"][0]["description"], "PERIODIC SERVICE LABOUR")
        self.assertTrue(
            all(
                item["parse_mode"] == "compact_ocr_row"
                for item in [*parsed.service_payload["parts_items"], *parsed.service_payload["labour_items"]]
            )
        )
        self.assertEqual(parsed.review_payload["invoice_review"]["compact_ocr_rows"], 3)

    def test_invoice_amount_parser_ignores_empty_ocr_amount_tokens(self):
        parser = BikeDocumentAI()

        self.assertEqual(parser._parse_amount_token(","), 0.0)
        self.assertEqual(parser._parse_amount_token("₹ ,"), 0.0)
        self.assertFalse(parser._looks_numeric_token(","))
