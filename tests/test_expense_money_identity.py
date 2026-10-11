"""Frozen import identity contracts established before the M13D schema change."""
from datetime import date
from decimal import Decimal
import hashlib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.expenses.services.statement_import import ParsedTransaction, StatementParseResult
from apps.expenses.services.statement_lifecycle import _import_statement_transactions
from apps.expenses.services.transaction_intelligence import build_transaction_fingerprint, build_reference_signature
from apps.expenses.services.cashflow_treatment import rounded_cashflow_bucket, summarize_cashflow


def parsed_fixture(*, amount=2.675, closing=10.005, direction="debit", category="shopping", description="UPI SAMPLE MERCHANT", reference="REF-001", account="TEST0001"):
    item = ParsedTransaction(
        transaction_date=date(2026, 9, 1), amount=amount, closing_balance=closing,
        direction=direction, classification="other" if category == "transfer" else "expense",
        category=category, payment_mode="UPI", merchant="Sample Merchant",
        description=description, raw_description=description, external_reference=reference,
        counterparty="Sample Merchant", company_name="Sample Merchant",
    )
    return StatementParseResult(
        bank_name="Test Bank", account_holder="Synthetic Owner", account_number=account,
        statement_start=date(2026, 9, 1), statement_end=date(2026, 9, 30), transactions=[item],
        statement_kind="bank_statement", parser_status="parsed", confidence=.91,
        source_text="Synthetic statement evidence", loan_hints={},
    )


class LegacyFingerprintContractTests(SimpleTestCase):
    def test_frozen_float_formatted_half_cent_hash(self):
        account = BankAccount(account_number="TEST0001")
        actual = build_transaction_fingerprint(bank_account=account, transaction_date=date(2026, 9, 1), amount=2.675, direction="debit", external_reference="REF-001", raw_description="UPI SAMPLE MERCHANT", closing_balance=10.005)
        # Literal legacy payload: binary-float formatting, not currency HALF_UP.
        expected = hashlib.sha256(b"TEST0001|2026-09-01|2.67|debit|REF001|UPI SAMPLE MERCHANT|10.01").hexdigest()
        self.assertEqual(actual, expected)

    def test_equivalent_amount_representations_keep_legacy_identity(self):
        for values in ((1, 1.0, "1.00", Decimal("1.00")), (2.675, "2.675", Decimal("2.675"))):
            fingerprints = {build_transaction_fingerprint(bank_account=None, transaction_date=date(2026, 9, 1), amount=value, direction="debit") for value in values}
            signatures = {build_reference_signature(transaction_date=date(2026, 9, 1), amount=value, direction="debit", external_reference="Ref-001") for value in values}
            self.assertEqual(len(fingerprints), 1)
            self.assertEqual(len(signatures), 1)

    def test_null_and_zero_balance_are_distinct_identities(self):
        args = dict(bank_account=None, transaction_date=date(2026, 9, 1), amount=1, direction="debit")
        self.assertNotEqual(build_transaction_fingerprint(**args, closing_balance=None), build_transaction_fingerprint(**args, closing_balance=0))


class StatementIdentityRegressionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="identity-owner")
        self.other = get_user_model().objects.create_user(username="identity-other")
        self.account = BankAccount.objects.create(user=self.user, account_number="TEST0001")
        self.upload = StatementUpload.objects.create(user=self.user, bank_account=self.account, file_name="fixture.pdf", extracted_payload={"raw": "synthetic evidence"})
        self.predict = patch("apps.expenses.services.transaction_intelligence.alfred_engine.predict_emotional_spend", return_value={"confidence": .1, "is_emotional": False})
        self.predict.start()
        self.addCleanup(self.predict.stop)

    def import_rows(self, parsed, *, account=None, upload=None, user=None):
        return _import_statement_transactions(user=user or self.user, upload=upload or self.upload, bank_account=account or self.account, parsed=parsed)

    def test_exact_reimport_keeps_ids_fingerprints_ownership_and_metadata(self):
        parsed = parsed_fixture()
        created, skipped = self.import_rows(parsed)
        self.assertEqual((len(created), skipped), (1, 0))
        before = list(Expense.objects.values("id", "user_id", "bank_account_id", "statement_upload_id", "transaction_date", "transaction_fingerprint", "external_reference", "raw_description", "timestamp"))
        self.assertEqual(tuple(map(len, (self.import_rows(parsed)[0],))), (0,))
        self.assertEqual(Expense.objects.count(), 1)
        self.assertEqual(before, list(Expense.objects.values(*before[0].keys())))
        self.upload.refresh_from_db()
        self.assertEqual(self.upload.extracted_payload, {"raw": "synthetic evidence"})

    def test_reference_deduplication_survives_changed_closing_balance_at_half_cent(self):
        self.import_rows(parsed_fixture())
        created, skipped = self.import_rows(parsed_fixture(closing=15.005))
        self.assertEqual((len(created), skipped, Expense.objects.count()), (0, 1, 1))

    def test_reference_reuse_with_new_description_is_a_distinct_transaction(self):
        self.import_rows(parsed_fixture())
        created, skipped = self.import_rows(parsed_fixture(description="UPI OTHER MERCHANT"))
        self.assertEqual((len(created), skipped, Expense.objects.count()), (1, 0, 2))

    def test_two_transfer_legs_are_preserved_and_excluded_from_spend(self):
        second = BankAccount.objects.create(user=self.user, account_number="TEST0002")
        other_upload = StatementUpload.objects.create(user=self.user, bank_account=second, file_name="second.pdf")
        debit = parsed_fixture(amount=50, closing=950, category="transfer")
        credit = parsed_fixture(amount=50, closing=50, direction="credit", category="transfer", account="TEST0002")
        for _ in range(2):
            self.import_rows(debit)
            self.import_rows(credit, account=second, upload=other_upload)
        rows = list(Expense.objects.filter(user=self.user))
        self.assertEqual(len(rows), 2)
        totals = rounded_cashflow_bucket(summarize_cashflow(rows))
        self.assertEqual((totals["expense_total"], totals["outflow_total"], totals["income_total"]), (0, 0, 0))
        self.assertEqual((totals["transfer_out_total"], totals["transfer_in_total"]), (50, 50))

    def test_deduplication_is_scoped_by_owner_and_account(self):
        self.import_rows(parsed_fixture())
        second = BankAccount.objects.create(user=self.other, account_number="TEST0001")
        other_upload = StatementUpload.objects.create(user=self.other, bank_account=second, file_name="other.pdf")
        self.import_rows(parsed_fixture(), account=second, upload=other_upload, user=self.other)
        self.assertEqual(Expense.objects.count(), 2)
        self.assertEqual(Expense.objects.filter(user=self.other, bank_account=second).count(), 1)
