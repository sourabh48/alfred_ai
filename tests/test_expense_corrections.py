from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.expenses.serializers import ExpenseSerializer


class ExpenseCorrectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="correction-owner")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.account = BankAccount.objects.create(user=self.user, account_number="CORRECTION1", current_balance="80.00")
        self.upload = StatementUpload.objects.create(user=self.user, bank_account=self.account, file_name="synthetic.pdf")
        self.context = {"request": SimpleNamespace(user=self.user)}
        predictor = patch("apps.expenses.services.transaction_intelligence.alfred_engine.predict_emotional_spend", return_value={"confidence": .1, "is_emotional": False})
        predictor.start()
        self.addCleanup(predictor.stop)
        serializer = ExpenseSerializer(data={
            "amount": "2.675", "closing_balance": "10.005", "bank_account": self.account.pk,
            "source": "bank_statement", "transaction_date": "2026-09-01",
            "classification": "expense", "category": "health", "payment_mode": "BANK",
            "merchant": "Owner corrected merchant", "description": "Owner corrected description",
            "raw_description": "UPI SAMPLE MERCHANT", "external_reference": "OWNER-REF",
            "counterparty": "Owner counterparty", "company_name": "Owner company",
        }, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.row = serializer.save(user=self.user, statement_upload=self.upload)

    def test_partial_correction_preserves_omitted_owner_values_and_identity(self):
        fields = ("classification", "category", "payment_mode", "merchant", "description", "raw_description",
                  "external_reference", "counterparty", "company_name", "transaction_fingerprint", "transaction_identity")
        before = {field: deepcopy(getattr(self.row, field)) for field in fields}
        response = self.client.patch(f"/api/expenses/{self.row.pk}/", {"amount": "2.68"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.row.refresh_from_db()
        self.assertEqual({field: getattr(self.row, field) for field in fields}, before)
        self.assertEqual(self.row.amount, Decimal("2.68"))

    def test_editable_description_does_not_replace_import_text_or_fingerprint(self):
        before = self.row.transaction_fingerprint
        response = self.client.patch(f"/api/expenses/{self.row.pk}/", {"description": "New owner note", "merchant": "New owner merchant"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.row.refresh_from_db()
        self.assertEqual(self.row.description, "New owner note")
        self.assertEqual(self.row.merchant, "New owner merchant")
        self.assertEqual(self.row.raw_description, "UPI SAMPLE MERCHANT")
        self.assertEqual(self.row.transaction_fingerprint, before)

    def test_correction_can_explicitly_clear_optional_owner_labels(self):
        response = self.client.patch(f"/api/expenses/{self.row.pk}/", {"merchant": "", "counterparty": "", "company_name": ""}, format="json")
        self.assertEqual(response.status_code, 200)
        self.row.refresh_from_db()
        self.assertEqual((self.row.merchant, self.row.counterparty, self.row.company_name), ("", "", ""))
