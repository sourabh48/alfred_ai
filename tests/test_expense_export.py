import csv
from datetime import date
from decimal import Decimal
from io import BytesIO, StringIO
import zipfile

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


class FinancialExportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="financial-export-owner")
        self.other = get_user_model().objects.create_user(username="financial-export-other")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def export(self):
        response = self.client.get("/api/expenses/export/financial/")
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(BytesIO(response.content)) as bundle:
            files = {name: bundle.read(name).decode("utf-8") for name in bundle.namelist()}
        return response, files, {name: list(csv.DictReader(StringIO(text))) for name, text in files.items()}

    def test_bundle_holds_each_register_with_exact_values_masked_numbers_and_owner_isolation(self):
        from apps.budgets.models import Budget
        from apps.investments.models import Investment
        from apps.loans.models import Loan

        BankAccount.objects.create(user=self.user, bank_name="Owner Bank", account_number="1234-5678-9012", current_balance="0.10")
        Expense.objects.create(user=self.user, amount="12.34", closing_balance=None, transaction_date=date(2026, 9, 1))
        Loan.objects.create(user=self.user, lender="=HYPERLINK(1)", loan_account_number="LN998877", principal="250000.50",
                            emi="1234.56", interest_rate=8.5, tenure_months=60, remaining_balance="0.00", start_date=date(2026, 1, 1))
        Investment.objects.create(user=self.user, asset_name="Owner Fund", account_number="INV00004321",
                                  invested_amount="1000.01", current_value="0.00")
        Budget.objects.create(user=self.user, month="2026-09", base_budget="5000.00", inflation_adjusted="5100.25", spent="0")
        BankAccount.objects.create(user=self.other, bank_name="FOREIGN-BANK", account_number="5555")
        Loan.objects.create(user=self.other, lender="FOREIGN-LENDER", principal="1", emi="1", interest_rate=1, tenure_months=1, start_date=date(2026, 1, 1))
        response, files, tables = self.export()

        self.assertEqual(set(files), {"bank-accounts.csv", "expenses.csv", "loans.csv", "investments.csv", "budgets.csv"})
        self.assertEqual(tables["bank-accounts.csv"][0]["account_number"], "****9012")
        self.assertEqual(tables["bank-accounts.csv"][0]["current_balance"], "0.10")
        self.assertEqual(tables["expenses.csv"][0]["closing_balance"], "")
        loan = tables["loans.csv"][0]
        self.assertEqual((loan["loan_account_number"], loan["principal"], loan["remaining_balance"]), ("****8877", "250000.50", "0.00"))
        self.assertEqual(loan["lender"], "'=HYPERLINK(1)")
        investment = tables["investments.csv"][0]
        self.assertEqual((investment["account_number"], investment["invested_amount"], investment["current_value"]),
                         ("****4321", "1000.01", "0.00"))
        self.assertEqual(tables["budgets.csv"][0]["inflation_adjusted"], "5100.25")
        content = "".join(files.values())
        for private in ("1234-5678-9012", "LN998877", "INV00004321", "FOREIGN-BANK", "FOREIGN-LENDER", "currency"):
            self.assertNotIn(private, content)
        self.assertTrue(all(len(rows) == 1 for rows in tables.values()))
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn('filename="alfred-financial-data.zip"', response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_empty_account_gets_headers_and_export_requires_sign_in(self):
        _, files, tables = self.export()
        self.assertTrue(files["loans.csv"].startswith("id,loan_type,"))
        self.assertTrue(all(rows == [] for rows in tables.values()))
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get("/api/expenses/export/financial/").status_code, (401, 403))
        self.client.force_login(self.user)
        self.assertContains(self.client.get("/expenses/"), 'href="/api/expenses/export/financial/"')
