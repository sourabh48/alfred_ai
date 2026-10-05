"""Payment/closure currency stays exact internally and numeric at API boundaries."""
from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from alfred_ai.services.document_review import apply_correction
from apps.expenses.models import Expense
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanPaymentHistory
from apps.loans.services.loan_foreclosure_service import loan_foreclosure_service
from apps.loans.services.loan_intelligence import loan_intelligence_service
from apps.loans.services.payment_review import _sync_loan_from_applied_matches, reject_subscription_false_positive_match
from apps.ml_engine.services.tax_optimizer import tax_optimizer


class LoanRelatedMoneyRuntimeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.user = get_user_model().objects.create_user(username="related-money-owner")
        self.other = get_user_model().objects.create_user(username="related-money-other")
        self.client.force_login(self.user)

    def loan(self, **changes):
        values = dict(
            user=self.user, lender="Example Housing Finance", loan_account_number="HOME123456",
            loan_type="home", principal="1000.10", remaining_balance="500.10", emi="100.20",
            interest_rate=0, tenure_months=24, start_date=timezone.localdate() - timedelta(days=60),
            verification_status="confirmed", total_paid="0.00",
        )
        values.update(changes)
        loan = Loan.objects.create(**values)
        loan.refresh_from_db()
        return loan

    def expense(self, loan, **changes):
        values = dict(
            user=loan.user, amount=.1, direction="debit", classification="loan", category="loan",
            merchant=loan.lender, company_name=loan.lender,
            description=f"{loan.lender} EMI {loan.loan_account_number}",
            external_reference=loan.loan_account_number, transaction_date=timezone.localdate(),
        )
        values.update(changes)
        return Expense.objects.create(**values)

    def payment(self, loan, **changes):
        values = dict(
            loan=loan, payment_date=timezone.localdate(), amount="0.10", principal_paid="0.10",
            remaining_balance=None, match_status="review",
        )
        values.update(changes)
        return LoanPaymentHistory.objects.create(**values)

    def document(self, loan, **changes):
        values = dict(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure.pdf", b"raw source proof", content_type="application/pdf"),
            file_name="closure.pdf", closure_amount="2.675",
            extracted_payload={"raw_source_amount": "2.675", "loan_account_number": loan.loan_account_number},
        )
        values.update(changes)
        return LoanClosureDocument.objects.create(**values)

    def review(self, payment, decision):
        return self.client.post(
            f"/api/loans/payment-history/{payment.pk}/review/",
            {"decision": decision}, content_type="application/json",
        )

    def test_detection_rounds_history_but_retains_original_expense_evidence(self):
        loan = self.loan(emi="0.01")
        expense = self.expense(loan, amount=.005)
        result = loan_intelligence_service.detect_loan_payments(self.user, [expense])
        self.assertEqual(result["new_payments"], 1)
        payment = LoanPaymentHistory.objects.get(expense_reference=expense)
        self.assertTrue(payment.loan_effect_applied)
        self.assertEqual(payment.amount, Decimal("0.01"))
        self.assertEqual(payment.principal_paid, Decimal("0.01"))
        self.assertEqual(payment.remaining_balance, Decimal("500.09"))
        self.assertEqual(payment.interest_paid, Decimal("0.00"))
        loan.refresh_from_db()
        expense.refresh_from_db()
        self.assertEqual(loan.total_paid, Decimal("0.01"))
        self.assertEqual(expense.amount, .005)

    def test_unconfirmed_detection_keeps_nullable_balance_and_no_loan_effect(self):
        loan = self.loan(emi="0.01", verification_status="estimated")
        expense = self.expense(loan, amount=.005)
        loan_intelligence_service.detect_loan_payments(self.user, [expense])
        payment = LoanPaymentHistory.objects.get(expense_reference=expense)
        self.assertEqual(payment.amount, Decimal("0.01"))
        self.assertIsNone(payment.remaining_balance)
        self.assertEqual(payment.principal_paid, Decimal("0.00"))
        self.assertEqual(payment.interest_paid, Decimal("0.00"))
        self.assertEqual(payment.match_status, "review")
        self.assertFalse(payment.loan_effect_applied)
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("500.10"))
        self.assertEqual(loan.total_paid, Decimal("0.00"))

    def test_review_accepts_legacy_component_fallback_and_refreshes_cached_totals(self):
        loan = self.loan(total_paid="0.10")
        self.payment(loan, payment_date=timezone.localdate() - timedelta(days=1),
                     match_status="matched", loan_effect_applied=True, remaining_balance="500.10")
        payment = self.payment(loan, amount="0.30", principal_paid=0, principal_component="0.20",
                               interest_component="0.10")
        self.assertEqual(self.client.get("/api/loans/summary/").status_code, 200)
        self.assertTrue(self.client.get("/api/loans/summary/").json()["_materialized"]["cached"])
        response = self.review(payment, "accept")
        self.assertEqual(response.status_code, 200, response.content)
        row = response.json()["payment"]
        self.assertEqual(row["amount"], .3)
        self.assertIsInstance(row["amount"], float)
        self.assertEqual(row["principal_component"], .2)
        self.assertIsNone(row["remaining_balance"])
        self.assertEqual(row["loan"]["remaining_balance"], 499.9)
        self.assertEqual(row["loan"]["total_paid"], .4)
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("499.90"))
        self.assertEqual(loan.total_paid, Decimal("0.40"))
        refreshed = self.client.get("/api/loans/summary/")
        self.assertFalse(refreshed.json()["_materialized"]["cached"])
        self.assertEqual(self.review(payment, "accept").status_code, 400)
        self.assertEqual(Loan.objects.get(pk=loan.pk).total_paid, Decimal("0.40"))

    def test_rejecting_applied_legacy_components_restores_exact_saved_balance(self):
        loan = self.loan(remaining_balance="499.90", total_paid="0.40")
        self.payment(loan, payment_date=timezone.localdate() - timedelta(days=1),
                     match_status="matched", loan_effect_applied=True, remaining_balance="500.10")
        payment = self.payment(loan, amount="0.30", principal_paid=0, principal_component="0.20",
                               interest_component="0.10", loan_effect_applied=True)
        response = self.review(payment, "reject")
        self.assertEqual(response.status_code, 200, response.content)
        loan.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("500.10"))
        self.assertEqual(loan.total_paid, Decimal("0.10"))
        self.assertFalse(payment.loan_effect_applied)
        self.assertEqual(payment.match_status, "rejected")

    def test_history_sync_does_not_invent_zero_for_unknown_register_balance(self):
        loan = self.loan(remaining_balance=None)
        self.payment(loan, remaining_balance=None, match_status="matched", loan_effect_applied=True)
        self.assertTrue(_sync_loan_from_applied_matches(loan))
        loan.refresh_from_db()
        self.assertIsNone(loan.remaining_balance)
        self.assertTrue(loan.is_active)
        self.assertEqual(loan.status, "active")
        self.assertEqual(loan.total_paid, Decimal("0.10"))

    def test_payment_review_cannot_read_or_mutate_another_owners_money(self):
        loan = self.loan(user=self.other)
        payment = self.payment(loan)
        self.assertEqual(self.review(payment, "accept").status_code, 404)
        loan.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(loan.total_paid, Decimal("0.00"))
        self.assertEqual(payment.match_status, "review")

    def test_closure_snapshot_and_watchlist_json_remain_numeric(self):
        loan = self.loan()
        document = self.document(loan)
        snapshot = LoanForeclosureSnapshot.objects.create(
            loan=loan, closure_document=document, outstanding_principal="2.675",
            accrued_interest="0.005", foreclosure_charges="0.015", taxes_gst="0.025",
            overdue_charges="0.035", total_amount_payable="2.78", matched_payment_total="2.675",
            classification_confidence=.8, linkage_confidence=.9, reconciliation_confidence=.7,
            audit_payload={"settlement_allocation": {"payment_total": 2.68}},
        )
        foreign = self.loan(user=self.other)
        self.document(foreign, closure_amount="999.99")
        payload = self.client.get("/api/loans/summary/").json()
        self.assertEqual(len(payload["recent_closures"]), 1)
        closure = payload["recent_closures"][0]
        self.assertEqual(closure["closure_amount"], 2.68)
        self.assertIsInstance(closure["closure_amount"], float)
        expected = dict(outstanding_principal=2.68, accrued_interest=.01, foreclosure_charges=.02,
                        taxes_gst=.03, overdue_charges=.04, total_amount_payable=2.78, matched_payment_total=2.68)
        for field, value in expected.items():
            with self.subTest(field=field):
                self.assertEqual(closure["foreclosure_snapshot"][field], value)
                self.assertIsInstance(closure["foreclosure_snapshot"][field], float)
        watch = payload["summary"]["foreclosure_watchlist"][0]
        self.assertEqual(watch["amount_payable"], 2.78)
        self.assertIsInstance(watch["matched_payment_total"], float)
        self.assertEqual(watch["settlement_allocation"]["payment_total"], 2.68)
        self.assertEqual(closure["extracted_payload"]["raw_source_amount"], "2.675")
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.outstanding_principal, Decimal("2.68"))

    def test_canonical_component_and_home_cost_totals_use_owned_matched_history(self):
        loan = self.loan()
        entries = (
            dict(amount=.10, principal_paid="0.01", interest_paid="0.02", charges_paid="0.03", penalties_paid="0.01", tax_paid="0.03"),
            dict(amount=.20, principal_paid=0, principal_component="0.10", interest_component="0.04", charges_paid="0.02", penalties_paid="0.01", tax_paid="0.03"),
            dict(amount=.30, principal_paid="0.10", interest_paid="0.05", charges_paid="0.05", penalties_paid="0.05", tax_paid="0.05"),
        )
        for entry in entries:
            expense = self.expense(loan, amount=entry["amount"])
            self.payment(loan, expense_reference=expense, match_status="matched", **entry)
        for status in ("review", "rejected"):
            expense = self.expense(loan, amount=99)
            self.payment(loan, expense_reference=expense, amount=99, principal_paid=99, match_status=status)
        foreign = self.loan(user=self.other)
        self.payment(foreign, expense_reference=self.expense(foreign, amount=99), amount=99,
                     principal_paid=99, match_status="matched")
        summary = self.client.get("/api/loans/summary/").json()["summary"]
        self.assertEqual(summary["payment_component_totals"], {
            "principal_paid": .21, "interest_paid": .11, "charges_paid": .10,
            "penalties_paid": .07, "tax_paid": .11,
        })
        home = summary["home_ownership_positions"][0]
        self.assertEqual(home["principal_paid_recorded"], .21)
        self.assertEqual(home["interest_and_cost_paid_recorded"], .39)
        self.assertIsInstance(home["ownership_progress_pct"], float)
        self.assertEqual(summary["home_ownership_summary"]["interest_and_cost_paid_recorded_total"], .39)

    def test_canonical_history_totals_can_exceed_individual_field_bounds(self):
        for account in ("LARGE-1", "LARGE-2"):
            loan = self.loan(principal="999999999999.99", remaining_balance="0.00", status="closed",
                             is_active=False, loan_account_number=account)
            expense = self.expense(loan, amount=999999999999.99)
            self.payment(loan, amount="999999999999.99", principal_paid="999999999999.99",
                         match_status="matched", expense_reference=expense)
        summary = self.client.get("/api/loans/summary/").json()["summary"]
        self.assertEqual(summary["payment_component_totals"]["principal_paid"], 1999999999999.98)
        self.assertEqual(summary["home_ownership_summary"]["principal_paid_recorded_total"], 1999999999999.98)

    def test_document_correction_keeps_raw_text_and_numeric_normalized_amount(self):
        document = self.document(self.loan())
        with patch("alfred_ai.services.document_review.loan_closure_parser.verify_document", return_value=(False, "Review")):
            response = self.client.post("/api/documents/review-queue/resolve/", {
                "scope": "loan_closure_document", "id": document.pk,
                "corrections": {"closure_amount": "2.675"},
            }, content_type="application/json")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["item"]["fields"]["closure_amount"], 2.68)
            self.assertIsInstance(response.json()["item"]["fields"]["closure_amount"], float)
            document.refresh_from_db()
            self.assertEqual(document.closure_amount, Decimal("2.68"))
            self.assertEqual(document.extracted_payload["accepted_corrections"]["closure_amount"], "2.675")
            self.assertEqual(document.extracted_payload["raw_source_amount"], "2.675")
            zero = self.client.post("/api/documents/review-queue/resolve/", {
                "scope": "loan_closure_document", "id": document.pk,
                "corrections": {"closure_amount": "0"},
            }, content_type="application/json")
        self.assertEqual(zero.status_code, 200, zero.content)
        self.assertEqual(zero.json()["item"]["fields"]["closure_amount"], 0.0)
        document.refresh_from_db()
        self.assertEqual(document.closure_amount, Decimal("0.00"))

    def test_invalid_or_foreign_document_correction_preserves_saved_evidence(self):
        document = self.document(self.loan())
        before = dict(document.extracted_payload)
        for invalid in ("NaN", "Infinity", True, "bad money", "1000000000000"):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError):
                    apply_correction(self.user, scope="loan_closure_document", document_id=document.pk,
                                     corrections={"closure_amount": invalid})
                document.refresh_from_db()
                self.assertEqual(document.closure_amount, Decimal("2.68"))
                self.assertEqual(document.extracted_payload, before)
        with self.assertRaises(LoanClosureDocument.DoesNotExist):
            apply_correction(self.other, scope="loan_closure_document", document_id=document.pk,
                             corrections={"closure_amount": "0"})

    def test_retry_keeps_accepted_zero_and_numeric_review_fields(self):
        document = self.document(self.loan(), extracted_payload={
            "accepted_corrections": {"closure_amount": "0"}, "raw_source_amount": "2.675",
        })
        with patch("alfred_ai.services.document_review.loan_closure_parser.parse_document", return_value={
            "payload": {"closure_amount": "99.995"}, "extracted_text": "Raw retry evidence",
            "confidence": .9, "parser_status": "parsed",
        }), patch("alfred_ai.services.document_review.loan_closure_parser.verify_document", return_value=(False, "Review")):
            response = self.client.post("/api/documents/review-queue/retry/", {
                "scope": "loan_closure_document", "id": document.pk,
            }, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["item"]["fields"]["closure_amount"], 0.0)
        self.assertIsInstance(response.json()["item"]["fields"]["closure_amount"], float)
        document.refresh_from_db()
        self.assertEqual(document.closure_amount, Decimal("0.00"))
        self.assertEqual(document.extracted_payload["accepted_corrections"]["closure_amount"], "0")

    def test_invalid_currency_correction_returns_400_without_mutating_loan_evidence(self):
        loan = self.loan()
        document = self.document(loan)
        self.payment(loan, match_status="matched", loan_effect_applied=True)
        snapshot = LoanForeclosureSnapshot.objects.create(
            loan=loan, closure_document=document, total_amount_payable="2.68",
            audit_payload={"settlement_allocation": {"payment_total": 2.68}},
        )
        before_loan = Loan.objects.filter(pk=loan.pk).values().get()
        before_document = LoanClosureDocument.objects.filter(pk=document.pk).values().get()
        before_snapshot = LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get()
        before_history = list(LoanPaymentHistory.objects.filter(loan=loan).values())
        for invalid in ("NaN", "Infinity", "1000000000000", True, False):
            with self.subTest(value=invalid):
                response = self.client.post("/api/documents/review-queue/resolve/", {
                    "scope": "loan_closure_document", "id": document.pk,
                    "corrections": {"closure_amount": invalid},
                }, content_type="application/json")
                self.assertEqual(response.status_code, 400, response.content)
                self.assertEqual(Loan.objects.filter(pk=loan.pk).values().get(), before_loan)
                self.assertEqual(LoanClosureDocument.objects.filter(pk=document.pk).values().get(), before_document)
                self.assertEqual(LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get(), before_snapshot)
                self.assertEqual(list(LoanPaymentHistory.objects.filter(loan=loan).values()), before_history)

    def test_closure_correction_rolls_back_document_if_snapshot_sync_rejects_it(self):
        loan = self.loan()
        document = self.document(loan)
        self.payment(loan, match_status="matched", loan_effect_applied=True)
        snapshot = LoanForeclosureSnapshot.objects.create(
            loan=loan, closure_document=document, total_amount_payable="2.68",
            audit_payload={"settlement_allocation": {"payment_total": 2.68}},
        )
        before_loan = Loan.objects.filter(pk=loan.pk).values().get()
        before_document = LoanClosureDocument.objects.filter(pk=document.pk).values().get()
        before_snapshot = LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get()
        before_history = list(LoanPaymentHistory.objects.filter(loan=loan).values())
        with patch("alfred_ai.services.document_review.loan_closure_parser.verify_document", return_value=(False, "Review")), patch(
            "alfred_ai.services.document_review.loan_foreclosure_service.sync_snapshot_from_document",
            side_effect=ValueError("Snapshot rejected the corrected money value"),
        ) as sync:
            response = self.client.post("/api/documents/review-queue/resolve/", {
                "scope": "loan_closure_document", "id": document.pk,
                "corrections": {"closure_amount": "3.005"},
            }, content_type="application/json")
        sync.assert_called_once()
        self.assertEqual(sync.call_args.args[0].closure_amount, Decimal("3.01"))
        self.assertEqual(response.status_code, 400, response.content)
        self.assertEqual(Loan.objects.filter(pk=loan.pk).values().get(), before_loan)
        self.assertEqual(LoanClosureDocument.objects.filter(pk=document.pk).values().get(), before_document)
        self.assertEqual(LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get(), before_snapshot)
        self.assertEqual(list(LoanPaymentHistory.objects.filter(loan=loan).values()), before_history)

    def test_payoff_preserves_explicit_zero_and_rejects_nonfinite_before_posting(self):
        loan = self.loan()
        document = self.document(loan, verification_status="verified")
        snapshot = LoanForeclosureSnapshot.objects.create(loan=loan, closure_document=document)
        result = SimpleNamespace(loan=loan, closure_document=document, snapshot=snapshot,
                                 confirmed=False, message="Retained for matching")
        with patch("apps.loans.views.loan_closure_parser.parse_document", return_value={"payload": {}}), patch(
            "apps.loans.views.loan_foreclosure_service.process_document", return_value=result,
        ) as process:
            response = self.client.post(f"/api/loans/{loan.pk}/payoff/", {
                "final_payment_amount": "0",
                "file": SimpleUploadedFile("request.pdf", b"request proof", content_type="application/pdf"),
            })
            self.assertEqual(response.status_code, 202, response.content)
            self.assertEqual(process.call_args.kwargs["requested_closure_amount"], Decimal("0.00"))
            self.assertIsInstance(response.json()["reconciliation"]["matched_payment_total"], float)
            process.reset_mock()
            invalid = self.client.post(f"/api/loans/{loan.pk}/payoff/", {
                "final_payment_amount": "NaN",
                "file": SimpleUploadedFile("invalid.pdf", b"request proof", content_type="application/pdf"),
            })
            self.assertEqual(invalid.status_code, 400, invalid.content)
            process.assert_not_called()
        self.assertEqual(LoanClosureDocument.objects.filter(loan=loan).count(), 1)
        self.assertEqual(Loan.objects.get(pk=loan.pk).remaining_balance, Decimal("500.10"))

    def test_review_preserves_finalized_settlement_and_unrelated_history_stays_evidence_only(self):
        for applied in (False, True):
            for decision in ("accept", "reject"):
                with self.subTest(applied=applied, decision=decision):
                    loan = self.loan(
                        loan_account_number=f"SETTLED-{applied}-{decision}",
                        total_paid="500.20" if applied else "0.10",
                        status="foreclosure_pending", is_active=False,
                    )
                    self.payment(loan, amount="0.10", match_status="matched", loan_effect_applied=True,
                                 remaining_balance="500.10", payment_date=timezone.localdate() - timedelta(days=2))
                    expense = self.expense(
                        loan, amount=500.10, category="subscription", merchant="Google Play Housing Finance",
                        description=f"FORECLOSURE {loan.lender} {loan.loan_account_number}",
                    )
                    settled = self.payment(
                        loan, expense_reference=expense, amount="500.10", principal_paid=0,
                        principal_component="450.10", interest_component="50.00", remaining_balance="999.90",
                        loan_effect_applied=applied, is_auto_detected=True,
                    )
                    original_settled = LoanPaymentHistory.objects.filter(pk=settled.pk).values().get()
                    document = self.document(
                        loan, closure_amount="500.10", parser_status="parsed", verification_status="verified",
                        extracted_payload={"total_amount_payable": 500.10},
                    )
                    snapshot = LoanForeclosureSnapshot.objects.create(
                        loan=loan, closure_document=document, total_amount_payable="500.10",
                        outstanding_principal="450.10", accrued_interest="50.00", lender_name=loan.lender,
                        loan_account_number=loan.loan_account_number, effective_closure_date=timezone.localdate(),
                    )
                    self.assertTrue(loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[expense]))
                    finalized_loan = Loan.objects.filter(pk=loan.pk).values().get()
                    finalized_snapshot = LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get()
                    self.assertEqual(finalized_loan["status"], "foreclosed")
                    self.assertEqual(finalized_loan["remaining_balance"], Decimal("0.00"))
                    self.assertEqual(finalized_loan["total_paid"], Decimal("500.20"))
                    self.assertEqual(LoanPaymentHistory.objects.filter(pk=settled.pk).values().get(), original_settled)
                    response = self.review(settled, decision)
                    self.assertEqual(response.status_code, 400, response.content)
                    with self.assertRaisesRegex(ValueError, "finalized foreclosure settlement"):
                        reject_subscription_false_positive_match(user=self.user, payment_id=settled.pk)
                    self.assertEqual(LoanPaymentHistory.objects.filter(pk=settled.pk).values().get(), original_settled)
                    self.assertEqual(Loan.objects.filter(pk=loan.pk).values().get(), finalized_loan)
                    self.assertEqual(LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get(), finalized_snapshot)

                    unrelated = self.payment(
                        loan, amount="0.30", principal_paid="0.20", interest_paid="0.10",
                        payment_date=timezone.localdate() - timedelta(days=3), loan_effect_applied=applied,
                    )
                    response = self.review(unrelated, decision)
                    self.assertEqual(response.status_code, 200, response.content)
                    unrelated.refresh_from_db()
                    self.assertEqual(unrelated.match_status, "matched" if decision == "accept" else "rejected")
                    self.assertFalse(unrelated.loan_effect_applied)
                    self.assertEqual(unrelated.amount, Decimal("0.30"))
                    self.assertEqual(unrelated.principal_paid, Decimal("0.20"))
                    self.assertEqual(unrelated.interest_paid, Decimal("0.10"))
                    self.assertEqual(Loan.objects.filter(pk=loan.pk).values().get(), finalized_loan)
                    self.assertEqual(LoanForeclosureSnapshot.objects.filter(pk=snapshot.pk).values().get(), finalized_snapshot)

    def test_foreclosed_status_and_unfinalized_snapshot_do_not_block_payment_review(self):
        loan = self.loan(status="foreclosed", is_active=False)
        payment = self.payment(loan, amount="0.30", principal_paid="0.20", remaining_balance="499.90")
        document = self.document(loan)
        LoanForeclosureSnapshot.objects.create(
            loan=loan, closure_document=document, reconciliation_status="full_match",
            audit_payload={"settlement_posting": {"preserved_existing_payment_history": [
                {"payment_history_id": payment.pk},
            ]}},
        )
        response = self.review(payment, "accept")
        self.assertEqual(response.status_code, 200, response.content)
        payment.refresh_from_db()
        self.assertTrue(payment.loan_effect_applied)
        loan.refresh_from_db()
        self.assertEqual(loan.remaining_balance, Decimal("499.90"))
        self.assertEqual(loan.total_paid, Decimal("0.30"))

    def test_tax_history_sums_cents_with_legacy_fallback_and_owned_year_filter(self):
        loan = self.loan()
        day = timezone.localdate()
        self.payment(loan, principal_paid="0.10", interest_paid="0.10", match_status="matched")
        self.payment(loan, principal_paid=0, principal_component="0.20", interest_component="0.20",
                     match_status="matched")
        self.payment(loan, principal_paid="999", interest_paid="999", match_status="rejected")
        foreign = self.loan(user=self.other)
        self.payment(foreign, principal_paid="999", interest_paid="999", match_status="matched")
        self.payment(loan, principal_paid="999", interest_paid="999", match_status="matched",
                     payment_date=day - timedelta(days=730))
        deductions = tax_optimizer._calculate_current_deductions(self.user)
        self.assertEqual(deductions["80C"], .3)
        self.assertEqual(deductions["24B"], .3)
        self.assertIsInstance(deductions["80C"], float)
