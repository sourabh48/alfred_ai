"""INV-02 with dummy documents: invented holdings statements in common Indian broker and registrar layouts.

Every name, folio and amount is made up. Amounts use Indian lakh grouping, as these statements do. Synthetic only.
"""
from decimal import Decimal
from io import BytesIO

import fitz
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service as service

GROWW = """Groww Invest Tech - Holdings Statement
Demat Account: 1208160012345678
Stock Name  |  ISIN  |  Quantity  |  Buy value  |  Closing value
Synthetic Motors Ltd  |  INE000A01011  |  40  |  1,12,400.00  |  1,30,250.50
Synthetic Power Ltd  |  INE000B01012  |  150  |  42,000.00  |  39,875.25
Total  |    |    |  1,54,400.00  |  1,70,125.75"""

CAMS = """Consolidated Account Statement - CAMS
Folio No  |  Scheme  |  Units  |  Cost Value  |  Market Value
12345678/90  |  Synthetic Flexi Cap Fund - Direct Growth  |  812.345  |  2,50,000.00  |  3,05,412.18
12345678/90  |  Synthetic Liquid Fund - Direct Growth  |  20.100  |  60,000.00  |  61,204.90"""

KITE = """Zerodha Console - Holdings
Client ID: ZX1234
Instrument  |  Qty.  |  Invested  |  Cur. val
SYNTHINFRA  |  25  |  37,500.00  |  41,212.75"""


def pdf(text):
    document = fitz.open()
    document.new_page().insert_text((30, 50), text, fontname="helv", fontsize=8)
    data = document.tobytes(); document.close()
    return BytesIO(data)


class DummyBrokerTests(TestCase):
    def test_three_layouts_with_lakh_grouping_are_read_and_reconciled(self):
        user = get_user_model().objects.create_user("synthetic-broker-owner")
        cases = {
            "groww": (GROWW, [("Synthetic Motors Ltd", "112400.00", "130250.50", "1208160012345678"), ("Synthetic Power Ltd", "42000.00", "39875.25", "1208160012345678")]),
            "cams": (CAMS, [("Synthetic Flexi Cap Fund - Direct Growth", "250000.00", "305412.18", "12345678/90"), ("Synthetic Liquid Fund - Direct Growth", "60000.00", "61204.90", "12345678/90")]),
            "kite": (KITE, [("SYNTHINFRA", "37500.00", "41212.75", "ZX1234")]),
        }
        for name, (text, expected) in cases.items():
            with self.subTest(layout=name):
                rows, review = service._parse_holdings_table(text, broker="Generic")
                self.assertEqual(review["status"], "parsed", review)
                self.assertEqual([(row["asset_name"], str(Decimal(row["invested_amount"])), str(Decimal(row["current_value"])), row["account_number"]) for row in rows], expected)
        parsed = service.parse_portfolio_document(pdf(GROWW), user=user, filename="dummy-groww.pdf")
        self.assertEqual([item["asset_name"] for item in parsed["investments"]], ["Synthetic Motors Ltd", "Synthetic Power Ltd"])

    def test_a_wrong_total_or_mixed_grouping_still_asks_for_review(self):
        rows, review = service._parse_holdings_table(GROWW.replace("1,70,125.75", "1,70,125.70"), broker="Generic")
        self.assertEqual((rows, review["status"]), ([], "needs_review"))
        rows, review = service._parse_holdings_table(KITE.replace("37,500.00", "3,7500.00"), broker="Generic")
        self.assertEqual((rows, review["status"]), ([], "needs_review"))
