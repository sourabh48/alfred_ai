import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.expenses.models import BankAccount, Expense, StatementUpload


class ExpenseExportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="export-owner")
        self.other = get_user_model().objects.create_user(username="export-other")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def export(self, query=""):
        response = self.client.get("/api/expenses/export/" + query)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        content = b"".join(response.streaming_content).decode("utf-8")
        return response, content, list(csv.DictReader(StringIO(content)))

    def test_export_preserves_decimal_null_zero_unicode_and_owner_isolation(self):
        account = BankAccount.objects.create(user=self.user, account_number="PRIVATE-ACCOUNT", current_balance="95.00")
        upload = StatementUpload.objects.create(user=self.user, bank_account=account, file_name="private-document.pdf")
        row = Expense.objects.create(user=self.user, bank_account=account, statement_upload=upload,
            amount="999999999999.99", closing_balance="-0.01", transaction_date=date(2026, 9, 1),
            merchant='Café, "owner"', description="Line one\nLine two", raw_description="PRIVATE-RAW", external_reference="REF-OWN")
        Expense.objects.create(user=self.user, amount="0.01", closing_balance=None, transaction_date=date(2026, 9, 2))
        Expense.objects.create(user=self.user, amount="2.68", closing_balance=0, transaction_date=date(2026, 9, 3))
        foreign = Expense.objects.create(user=self.other, amount="900.00", merchant="FOREIGN-ONLY")
        response, content, rows = self.export(f"?user={self.other.pk}&limit=1")
        self.assertEqual(len(rows), 3)
        self.assertEqual([item["closing_balance"] for item in rows], ["0.00", "", "-0.01"])
        exported = rows[-1]
        self.assertEqual(exported["amount"], "999999999999.99")
        self.assertEqual((exported["merchant"], exported["description"]), (row.merchant, row.description))
        self.assertEqual((exported["bank_account_id"], exported["statement_upload_id"]), (str(account.pk), str(upload.pk)))
        for private in ("PRIVATE-ACCOUNT", "PRIVATE-RAW", "private-document.pdf", "FOREIGN-ONLY"):
            self.assertNotIn(private, content)
        self.assertNotIn(str(foreign.pk), [item["id"] for item in rows])
        self.assertNotIn("user", exported)
        self.assertNotIn("currency", exported)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn('filename="alfred-expenses.csv"', response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        account.refresh_from_db()
        self.assertEqual(account.current_balance, Decimal("95.00"))

    def test_spreadsheet_formula_prefixes_are_escaped_in_every_text_column(self):
        values = ("=1+1", "+SUM(1,2)", "-1+2", "@SUM(1,2)", " \t=1", "\ttext", "\rtext", "\ntext")
        for value in values:
            Expense.objects.create(user=self.user, amount="1.00", merchant=value, description=value, external_reference=value)
        _, _, rows = self.export()
        for row, value in zip(rows, reversed(values)):
            for column in ("merchant", "description", "external_reference"):
                self.assertEqual(row[column], "'" + value)

    def test_export_is_complete_beyond_list_page_size_and_empty_catalog_has_header(self):
        _, content, rows = self.export()
        self.assertEqual(rows, [])
        self.assertTrue(content.startswith("id,transaction_date,"))
        Expense.objects.bulk_create([Expense(user=self.user, amount="1.00") for _ in range(125)])
        _, _, rows = self.export()
        self.assertEqual(len(rows), 125)
        self.assertEqual(len({row["id"] for row in rows}), 125)

    def test_export_requires_authentication_and_ui_exposes_session_download(self):
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get("/api/expenses/export/").status_code, (401, 403))
        self.client.force_login(self.user)
        self.export()
        response = self.client.get("/expenses/")
        self.assertContains(response, 'id="expenseExportBtn"')
        self.assertContains(response, 'href="/api/expenses/export/"')
