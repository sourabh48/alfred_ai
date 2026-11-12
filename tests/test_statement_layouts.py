"""Statement layouts beyond one bank's dd/mm/yy format; synthetic statements only."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import fitz
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings

from apps.expenses.models import Expense
from apps.expenses.services.statement_import import parse_bank_statement
from tests.test_fund_look_through import xlsx

LEARNING = 'apps.expenses.services.statement_import.apply_parser_learning'


def pdf(lines):
    with fitz.open() as document:
        page = document.new_page(width=900, height=800)
        page.insert_text((30, 40), 'SYNTHETIC BANK Account No: 000111222333', fontname='cour', fontsize=9)
        for index, line in enumerate(lines):
            page.insert_text((30, 80 + index * 24), line, fontname='cour', fontsize=9)
        return document.tobytes()


def rows(parsed):
    return [(item.transaction_date, item.amount, item.direction, item.closing_balance) for item in parsed.transactions]


class StatementTextLayoutTests(SimpleTestCase):
    def parse(self, raw, name='statement.pdf'):
        upload = SimpleUploadedFile(name, raw)
        with patch(LEARNING, return_value=(0.9, [])):
            return parse_bank_statement(upload)

    def test_dash_dates_dr_cr_markers_split_columns_and_overdrawn_balances(self):
        parsed = self.parse(pdf([
            '01-03-2026 NEFT CR SALARY SYNTHETIC 01-03-2026 10,000.00 10,000.00',
            '05-03-2026 UPI-SYNTHETIC GROCER 05-03-2026 1,200.50 8,799.50',
            '06/03/2026 ATM WDL SYNTHETIC 500.00 Dr 8,299.50 Cr',
            '07-03-26 SYNTHETIC REFUND - 99.00 8,398.50',
            '08-03-2026 CHEQUE SYNTHETIC 9,000.00 0.00 -601.50',
            '09-03-2026 CHARGES SYNTHETIC 10.00 Dr 611.50 Dr',
        ]))
        self.assertEqual(rows(parsed), [
            (date(2026, 3, 1), Decimal('10000.00'), 'credit', Decimal('10000.00')),
            (date(2026, 3, 5), Decimal('1200.50'), 'debit', Decimal('8799.50')),
            (date(2026, 3, 6), Decimal('500.00'), 'debit', Decimal('8299.50')),
            (date(2026, 3, 7), Decimal('99.00'), 'credit', Decimal('8398.50')),
            (date(2026, 3, 8), Decimal('9000.00'), 'debit', Decimal('-601.50')),
            (date(2026, 3, 9), Decimal('10.00'), 'debit', Decimal('-611.50')),
        ])
        self.assertTrue(all(isinstance(item.amount, Decimal) for item in parsed.transactions))
        self.assertEqual(parsed.unparsed_rows, [])

    def test_rows_that_cannot_be_read_are_listed_not_dropped(self):
        parsed = self.parse(pdf([
            '01-03-2026 SYNTHETIC OK 01-03-2026 100.00 100.00',
            '02-03-2026 SYNTHETIC BOTH COLUMNS 10.00 5.00 105.00',
            '31-02-2026 SYNTHETIC IMPOSSIBLE DATE 1.00 104.00',
            '03-03-2026 SYNTHETIC NO AMOUNTS AT ALL',
        ]))
        self.assertEqual(len(parsed.transactions), 1)
        self.assertEqual([row['reason'] for row in parsed.unparsed_rows], [
            'Both withdrawal and deposit columns have amounts',
            "'31-02-2026' is not a valid date",
            'No amount and closing balance could be found',
        ])
        self.assertIn('IMPOSSIBLE DATE', parsed.unparsed_rows[1]['text'])
        self.assertIn('could not be read', parsed.parser_notes)


class StatementTableTests(SimpleTestCase):
    def parse(self, raw, name):
        with patch(LEARNING, return_value=(0.9, [])):
            return parse_bank_statement(SimpleUploadedFile(name, raw))

    def test_csv_with_separate_debit_and_credit_columns(self):
        raw = (
            'Synthetic Bank Ltd\nAccount No: 000111222333\n\n'
            'Txn Date,Narration,Ref No,Debit,Credit,Balance\n'
            ',Opening Balance,,,,"5,000.00"\n'
            '01-04-2026,UPI-SYNTHETIC CAFE,REF0001,250.00,,"4,750.00"\n'
            '02/04/2026,NEFT SYNTHETIC EMPLOYER,REF0002,,"30,000.00","34,750.00"\n'
            '03-04-2026,SYNTHETIC BOTH,REF0003,1.00,2.00,"34,751.00"\n'
            'not a date,SYNTHETIC BAD DATE,REF0004,5.00,,"34,746.00"\n'
        ).encode()
        parsed = self.parse(raw, 'synthetic.csv')
        self.assertEqual(rows(parsed), [
            (date(2026, 4, 1), Decimal('250.00'), 'debit', Decimal('4750.00')),
            (date(2026, 4, 2), Decimal('30000.00'), 'credit', Decimal('34750.00')),
        ])
        self.assertEqual(parsed.account_number, '000111222333')
        self.assertEqual([row['reason'] for row in parsed.unparsed_rows][0], 'Both withdrawal and deposit columns have amounts')
        self.assertIn('SYNTHETIC BAD DATE', parsed.unparsed_rows[1]['text'])
        self.assertEqual(parsed.parser_status, 'parsed')

    def test_xlsx_with_amount_and_dr_cr_columns_serial_dates_and_overdraft(self):
        sheet = [
            ['Synthetic Bank statement'],
            ['Date', 'Description', 'Amount (INR)', 'Dr/Cr', 'Balance'],
            [46113, 'SYNTHETIC RENT', '12,000.00', 'DR', '-2,000.00'],
            ['02-04-2026', 'SYNTHETIC INTEREST', 15.5, 'CR', '(1,984.50)'],
        ]
        parsed = self.parse(xlsx(sheet, shared=()), 'synthetic.xlsx')
        self.assertEqual(rows(parsed), [
            (date(2026, 4, 1), Decimal('12000.00'), 'debit', Decimal('-2000.00')),
            (date(2026, 4, 2), Decimal('15.5'), 'credit', Decimal('-1984.50')),
        ])

    def test_broken_spreadsheet_is_refused(self):
        from alfred_ai.services.upload_limits import UploadFormatError
        with self.assertRaises(UploadFormatError):
            self.parse(b'not a zip', 'broken.xlsx')


class StatementTableUploadTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-statement-layout-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root / 'media', ALFRED_ABUSE_THROTTLE_DIR=str(root / 'limits')))
        self.user = get_user_model().objects.create_user(username='synthetic-statement-layout-owner')
        self.client.force_login(self.user)

    def test_csv_upload_is_staged_for_review_with_unreadable_rows_shown(self):
        raw = ('Account No: 000111222333\nDate,Narration,Withdrawal,Deposit,Balance\n'
               '01-04-2026,UPI-SYNTHETIC CAFE,250.00,,"4,750.00"\n'
               '02-04-2026,SYNTHETIC BOTH,1.00,2.00,"4,751.00"\n').encode()
        response = self.client.post('/api/expenses/import-statement/', {'statement': SimpleUploadedFile('synthetic.csv', raw)})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(Expense.objects.exists())
        upload = response.json()['upload']['id']
        preview = self.client.get(f'/api/expenses/uploads/{upload}/preview/').json()
        self.assertEqual(preview['row_count'], 1)
        self.assertEqual(preview['rows'][0]['amount'], '250.00')
        self.assertEqual(preview['unparsed_rows'][0]['reason'], 'Both withdrawal and deposit columns have amounts')
        page = self.client.get(f'/expenses/uploads/{upload}/review/').content.decode()
        self.assertIn('statementUnparsedRows', page)
        self.assertIn('SYNTHETIC BOTH', page)

    def test_other_file_types_are_still_refused(self):
        response = self.client.post('/api/expenses/import-statement/', {'statement': SimpleUploadedFile('statement.txt', b'x')})
        self.assertEqual(response.status_code, 400)
