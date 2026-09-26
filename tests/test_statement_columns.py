"""Check real PDF columns against independently specified transaction meanings."""
from datetime import date
from io import BytesIO
from unittest.mock import patch

import fitz
from django.test import SimpleTestCase

from apps.expenses.services.statement_import import parse_bank_statement


class StatementColumnTests(SimpleTestCase):
    def parse_rows(self, rows):
        header = (f"{'Date':<12}{'Narration':<35}{'Chq./Ref.No.':<18}{'Value Dt':<12}"
                  f"{'Withdrawal Amt.':<20}{'Deposit Amt.':<20}Closing Balance")
        with fitz.open() as document:
            page = document.new_page(width=1100, height=800)
            page.insert_text((30, 40), 'HDFC BANK Statement From: 01/03/2026 To: 30/04/2026', fontname='cour', fontsize=9)
            page.insert_text((30, 70), header, fontname='cour', fontsize=9)
            for index, (posted, description, valued, debit, credit, balance) in enumerate(rows):
                line = (f"{posted:<12}{description:<35}{'123456789012':<18}{valued:<12}"
                        f"{debit:>16}    {credit:>16}    {balance:>16}")
                page.insert_text((30, 100 + index * 30), line, fontname='cour', fontsize=9)
            raw = document.tobytes()
        with patch('apps.expenses.services.statement_import.apply_parser_learning', return_value=(0.9, [])):
            return parse_bank_statement(BytesIO(raw)).transactions

    def test_first_deposit_is_credit_without_an_opening_balance(self):
        rows = self.parse_rows([
            ('31/03/26', 'UPI-RECEIVED', '31/03/26', '', '250.00', '1,250.00'),
            ('31/03/26', 'UPI-SHOP', '31/03/26', '40.00', '', '1,210.00'),
        ])
        self.assertEqual([(row.amount, row.direction) for row in rows], [(250.0, 'credit'), (40.0, 'debit')])

    def test_transaction_date_controls_month_even_when_value_date_differs(self):
        rows = self.parse_rows([('01/04/26', 'INTEREST PAID', '31/03/26', '', '12.00', '1,222.00')])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].transaction_date, date(2026, 4, 1))
        self.assertEqual(rows[0].direction, 'credit')

    def test_withdrawal_column_overrides_misleading_credit_words(self):
        rows = self.parse_rows([('02/04/26', 'UPI-REFUND-SHOP', '02/04/26', '90.00', '', '1,132.00')])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].direction, 'debit')

    def test_columns_work_for_reverse_chronological_balances(self):
        rows = self.parse_rows([
            ('03/04/26', 'UPI-SHOP', '03/04/26', '20.00', '', '980.00'),
            ('02/04/26', 'UPI-SHOP', '02/04/26', '30.00', '', '1,000.00'),
        ])
        self.assertEqual([row.direction for row in rows], ['debit', 'debit'])
