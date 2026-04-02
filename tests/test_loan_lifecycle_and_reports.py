import json
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import build_financial_intelligence
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanPaymentHistory
from apps.loans.serializers import LoanSerializer
from apps.loans.services.loan_closure_parser import loan_closure_parser
from apps.loans.services.loan_foreclosure_service import loan_foreclosure_service
from apps.reports.models import SystemTicket


class LoanLifecycleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="loan_user", password="Pass12345!")
        self.user.monthly_income = 100000
        self.user.save(update_fields=["monthly_income"])
        self.client = Client()
        self.client.force_login(self.user)

    def _create_foreclosure_snapshot(
        self,
        *,
        loan: Loan,
        principal: float = 100000.0,
        interest: float = 2000.0,
        charges: float = 1000.0,
        penalties: float = 500.0,
        tax: float = 500.0,
    ) -> LoanForeclosureSnapshot:
        total_amount = principal + interest + charges + penalties + tax
        document = LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=SimpleUploadedFile("closure.txt", b"closure", content_type="text/plain"),
            file_name="closure.txt",
            extracted_text="Axis Bank foreclosure statement",
            extracted_payload={
                "document_type": "foreclosure_statement",
                "lender_name": loan.lender,
                "loan_account_number": loan.loan_account_number,
                "outstanding_principal": principal,
                "accrued_interest": interest,
                "foreclosure_charges": charges,
                "overdue_charges": penalties,
                "taxes_gst": tax,
                "total_amount_payable": total_amount,
            },
            parser_status="parsed",
            parse_confidence=0.91,
            verification_status="verified",
            closure_amount=total_amount,
            closure_date=timezone.localdate(),
        )
        snapshot = LoanForeclosureSnapshot.objects.create(
            loan=loan,
            closure_document=document,
            document_type="foreclosure_statement",
            lender_name=loan.lender,
            borrower_name=self.user.username,
            loan_account_number=loan.loan_account_number,
            statement_date=timezone.localdate(),
            effective_closure_date=timezone.localdate(),
            due_by_date=timezone.localdate(),
            outstanding_principal=principal,
            accrued_interest=interest,
            foreclosure_charges=charges,
            taxes_gst=tax,
            overdue_charges=penalties,
            total_amount_payable=total_amount,
            classification_confidence=0.91,
            linkage_confidence=0.96,
            linkage_notes="Exact deterministic match",
        )
        loan_foreclosure_service._mark_foreclosure_pending(loan, snapshot)
        return snapshot

    def test_consolidate_loans_creates_new_loan_and_closes_sources(self):
        loan_one = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Lender One",
            principal=100000,
            interest_rate=12,
            emi=5200,
            tenure_months=24,
            remaining_balance=82000,
            start_date=timezone.localdate(),
        )
        loan_two = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Lender Two",
            principal=80000,
            interest_rate=13,
            emi=4300,
            tenure_months=24,
            remaining_balance=64000,
            start_date=timezone.localdate(),
        )

        response = self.client.post(
            "/api/loans/consolidate/",
            data=json.dumps({
                "loan_ids": [loan_one.id, loan_two.id],
                "loan_type": "personal",
                "lender": "Unified Finance",
                "loan_account_number": "CONS12345",
                "principal": 146000,
                "interest_rate": 10.5,
                "emi": 6900,
                "tenure_months": 36,
                "start_date": timezone.localdate().isoformat(),
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        loan_one.refresh_from_db()
        loan_two.refresh_from_db()
        consolidated = Loan.objects.get(loan_account_number="CONS12345")
        self.assertFalse(loan_one.is_active)
        self.assertFalse(loan_two.is_active)
        self.assertEqual(loan_one.status, "prepaid")
        self.assertEqual(loan_one.consolidated_into_id, consolidated.id)
        self.assertTrue(consolidated.is_active)

    def test_foreclosure_parser_extracts_structured_fields(self):
        parsed = loan_closure_parser.parse_document(
            BytesIO(
                b"""
                Axis Bank Foreclosure Statement
                Borrower Name: Soura Sarkar
                Loan Account Number: AXIS123456
                Statement Date: 30/03/2026
                Closure Date: 31/03/2026
                Due By: 05/04/2026
                Outstanding Principal: INR 125000
                Accrued Interest: INR 2200
                Foreclosure Charges: INR 900
                GST: INR 162
                Overdue Charges: INR 0
                Total Amount Payable: INR 128262
                """
            ),
            "foreclosure.txt",
            user=self.user,
        )

        self.assertEqual(parsed["parser_status"], "parsed")
        self.assertEqual(parsed["payload"]["document_type"], "foreclosure_statement")
        self.assertEqual(parsed["payload"]["lender_name"], "Axis Bank")
        self.assertEqual(parsed["payload"]["borrower_name"], "Soura Sarkar")
        self.assertEqual(parsed["payload"]["loan_account_number"], "AXIS123456")
        self.assertEqual(parsed["payload"]["statement_date"], "2026-03-30")
        self.assertEqual(parsed["payload"]["effective_closure_date"], "2026-03-31")
        self.assertEqual(parsed["payload"]["due_by_date"], "2026-04-05")
        self.assertEqual(parsed["payload"]["outstanding_principal"], 125000.0)
        self.assertEqual(parsed["payload"]["accrued_interest"], 2200.0)
        self.assertEqual(parsed["payload"]["foreclosure_charges"], 900.0)
        self.assertEqual(parsed["payload"]["taxes_gst"], 162.0)
        self.assertEqual(parsed["payload"]["total_amount_payable"], 128262.0)

    def test_pending_foreclosure_keeps_liability_until_statement_reconciliation_confirms_payment(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXIS123456",
            principal=100000,
            interest_rate=12,
            emi=5200,
            tenure_months=24,
            remaining_balance=14000,
            start_date=timezone.localdate(),
        )

        response = self.client.post(f"/api/loans/{loan.id}/payoff/", data={})
        self.assertEqual(response.status_code, 400)

        foreclosure_doc = SimpleUploadedFile(
            "closure.txt",
            b"Axis Bank loan closure letter. Loan account number AXIS123456. Foreclosure amount 14000. Closure date 30/03/2026. No due certificate.",
            content_type="text/plain",
        )
        response = self.client.post(
            f"/api/loans/{loan.id}/payoff/",
            data={"file": foreclosure_doc, "final_payment_amount": "14000"},
        )
        self.assertEqual(response.status_code, 202)
        payload = response.json()
        loan.refresh_from_db()
        snapshot = LoanForeclosureSnapshot.objects.get(loan=loan)

        self.assertFalse(loan.is_active)
        self.assertEqual(loan.status, "foreclosure_pending")
        self.assertEqual(loan.remaining_balance, 14000.0)
        self.assertIsNone(loan.closed_on)
        self.assertEqual(payload["reconciliation"]["status"], "unmatched")
        self.assertEqual(snapshot.document_type, "noc")
        self.assertEqual(snapshot.loan_account_number, "AXIS123456")
        self.assertEqual(snapshot.total_amount_payable, 14000.0)
        self.assertEqual(snapshot.reconciliation_status, "unmatched")

        before_summary = build_financial_intelligence(self.user)
        self.assertEqual(before_summary["loan_portfolio"]["foreclosure_pending_count"], 1)
        self.assertEqual(before_summary["loan_portfolio"]["pending_foreclosure_excluded_balance"], 14000.0)
        self.assertEqual(before_summary["loan_portfolio"]["reconciled_foreclosures"], 0)
        self.assertEqual(before_summary["loan_portfolio"]["manual_total_outstanding"], 14000.0)
        self.assertEqual(before_summary["balance_sheet"]["pending_foreclosure_excluded_balance"], 14000.0)
        self.assertEqual(before_summary["balance_sheet"]["total_liabilities"], 14000.0)
        self.assertEqual(before_summary["loan_portfolio"]["active_loans"], 0)

        closure_expense = Expense.objects.create(
            user=self.user,
            amount=14000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank foreclosure payment AXIS123456",
            raw_description="AXIS BANK FORECLOSURE AXIS123456",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-CLOSE-001",
        )
        resolved = loan_foreclosure_service.reconcile_pending_foreclosures(user=self.user, expenses=[closure_expense])

        self.assertEqual(len(resolved), 1)
        loan.refresh_from_db()
        snapshot.refresh_from_db()

        self.assertFalse(loan.is_active)
        self.assertEqual(loan.status, "foreclosed")
        self.assertEqual(loan.closure_reason, "foreclosed")
        self.assertEqual(loan.remaining_balance, 0)
        self.assertEqual(snapshot.reconciliation_status, "full_match")
        self.assertEqual(snapshot.matched_payment_total, 14000.0)
        self.assertEqual(snapshot.matched_closure_transaction_ids, [closure_expense.id])

        after_summary = build_financial_intelligence(self.user)
        self.assertEqual(after_summary["loan_portfolio"]["foreclosure_pending_count"], 0)
        self.assertEqual(after_summary["loan_portfolio"]["pending_foreclosure_excluded_balance"], 0.0)
        self.assertEqual(after_summary["loan_portfolio"]["reconciled_foreclosures"], 1)
        self.assertEqual(after_summary["balance_sheet"]["pending_foreclosure_excluded_balance"], 0.0)
        self.assertEqual(after_summary["balance_sheet"]["total_liabilities"], 0.0)
        self.assertEqual(after_summary["loan_portfolio"]["active_loans"], 0)

    def test_foreclosure_reconciliation_allocates_exact_component_split(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISSETTLE001",
            principal=150000,
            interest_rate=12,
            emi=5200,
            tenure_months=36,
            remaining_balance=100000,
            start_date=timezone.localdate(),
        )
        snapshot = self._create_foreclosure_snapshot(loan=loan)
        closure_expense = Expense.objects.create(
            user=self.user,
            amount=104000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank foreclosure payment AXISSETTLE001",
            raw_description="AXIS BANK FORECLOSURE AXISSETTLE001",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-SETTLE-001",
        )

        resolved = loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[closure_expense])

        self.assertTrue(resolved)
        loan.refresh_from_db()
        snapshot.refresh_from_db()
        payment = LoanPaymentHistory.objects.get(loan=loan, expense_reference=closure_expense)
        self.assertEqual(loan.status, "foreclosed")
        self.assertEqual(snapshot.reconciliation_status, "full_match")
        self.assertEqual(payment.principal_paid, 100000.0)
        self.assertEqual(payment.interest_paid, 2000.0)
        self.assertEqual(payment.charges_paid, 1000.0)
        self.assertEqual(payment.penalties_paid, 500.0)
        self.assertEqual(payment.tax_paid, 500.0)
        self.assertEqual(payment.principal_component, 100000.0)
        self.assertEqual(payment.interest_component, 2000.0)
        self.assertEqual(snapshot.audit_payload["settlement_allocation"]["allocation_status"], "finalized")
        self.assertEqual(
            snapshot.audit_payload["settlement_allocation"]["allocated_components"],
            {
                "principal_paid": 100000.0,
                "interest_paid": 2000.0,
                "charges_paid": 1000.0,
                "penalties_paid": 500.0,
                "tax_paid": 500.0,
            },
        )
        serialized = LoanSerializer(loan).data
        self.assertEqual(
            serialized["latest_foreclosure_snapshot"]["settlement_allocation"]["allocated_components"]["interest_paid"],
            2000.0,
        )

    def test_foreclosure_reconciliation_stores_proportional_partial_allocation_without_closing_loan(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISPARTIAL001",
            principal=150000,
            interest_rate=12,
            emi=5200,
            tenure_months=36,
            remaining_balance=100000,
            start_date=timezone.localdate(),
        )
        snapshot = self._create_foreclosure_snapshot(loan=loan)
        partial_expense = Expense.objects.create(
            user=self.user,
            amount=52000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank foreclosure payment AXISPARTIAL001",
            raw_description="AXIS BANK FORECLOSURE AXISPARTIAL001",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-PARTIAL-001",
        )

        resolved = loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[partial_expense])

        self.assertFalse(resolved)
        loan.refresh_from_db()
        snapshot.refresh_from_db()
        allocation = snapshot.audit_payload["settlement_allocation"]
        self.assertEqual(loan.status, "foreclosure_pending")
        self.assertEqual(snapshot.reconciliation_status, "partial_match")
        self.assertEqual(allocation["allocation_status"], "provisional_partial")
        self.assertEqual(
            allocation["allocated_components"],
            {
                "principal_paid": 50000.0,
                "interest_paid": 1000.0,
                "charges_paid": 500.0,
                "penalties_paid": 250.0,
                "tax_paid": 250.0,
            },
        )
        self.assertEqual(len(allocation["expense_allocations"]), 1)
        self.assertEqual(allocation["expense_allocations"][0]["remaining_balance_after_payment"], 50000.0)
        self.assertFalse(LoanPaymentHistory.objects.filter(loan=loan).exists())

    def test_foreclosure_reconciliation_supports_split_payments_across_multiple_transactions(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISSPLIT001",
            principal=150000,
            interest_rate=12,
            emi=5200,
            tenure_months=36,
            remaining_balance=100000,
            start_date=timezone.localdate(),
        )
        snapshot = self._create_foreclosure_snapshot(loan=loan)
        first_split = Expense.objects.create(
            user=self.user,
            amount=60000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank closure transfer AXISSPLIT001 tranche 1",
            raw_description="AXIS BANK FORECLOSURE AXISSPLIT001 PART 1",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-SPLIT-001A",
        )
        second_split = Expense.objects.create(
            user=self.user,
            amount=44000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank closure transfer AXISSPLIT001 tranche 2",
            raw_description="AXIS BANK FORECLOSURE AXISSPLIT001 PART 2",
            transaction_date=timezone.localdate() + timedelta(days=2),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-SPLIT-001B",
        )

        resolved = loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[first_split, second_split])

        self.assertTrue(resolved)
        snapshot.refresh_from_db()
        loan.refresh_from_db()
        self.assertEqual(loan.status, "foreclosed")
        self.assertEqual(snapshot.reconciliation_status, "full_match")
        self.assertEqual(snapshot.matched_payment_total, 104000.0)
        self.assertEqual(snapshot.matched_closure_transaction_ids, [first_split.id, second_split.id])
        payments = list(LoanPaymentHistory.objects.filter(loan=loan).order_by("payment_date", "id"))
        self.assertEqual(len(payments), 2)
        self.assertEqual(round(sum(payment.amount for payment in payments), 2), 104000.0)
        self.assertEqual(round(sum(payment.principal_paid for payment in payments), 2), 100000.0)
        self.assertEqual(round(sum(payment.interest_paid for payment in payments), 2), 2000.0)
        self.assertEqual(round(sum(payment.charges_paid for payment in payments), 2), 1000.0)
        self.assertEqual(round(sum(payment.penalties_paid for payment in payments), 2), 500.0)
        self.assertEqual(round(sum(payment.tax_paid for payment in payments), 2), 500.0)

    def test_foreclosure_reconciliation_keeps_mismatch_unallocated(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISMISMATCH001",
            principal=150000,
            interest_rate=12,
            emi=5200,
            tenure_months=36,
            remaining_balance=100000,
            start_date=timezone.localdate(),
        )
        snapshot = self._create_foreclosure_snapshot(loan=loan)
        mismatch_expense = Expense.objects.create(
            user=self.user,
            amount=130000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank foreclosure payment AXISMISMATCH001",
            raw_description="AXIS BANK FORECLOSURE AXISMISMATCH001",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-MISMATCH-001",
        )

        resolved = loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[mismatch_expense])

        self.assertFalse(resolved)
        loan.refresh_from_db()
        snapshot.refresh_from_db()
        self.assertEqual(loan.status, "foreclosure_pending")
        self.assertEqual(snapshot.reconciliation_status, "mismatch")
        self.assertEqual(snapshot.audit_payload["settlement_allocation"]["allocation_status"], "mismatch_unallocated")
        self.assertEqual(
            snapshot.audit_payload["settlement_allocation"]["allocated_components"],
            {
                "principal_paid": 0.0,
                "interest_paid": 0.0,
                "charges_paid": 0.0,
                "penalties_paid": 0.0,
                "tax_paid": 0.0,
            },
        )
        self.assertFalse(LoanPaymentHistory.objects.filter(loan=loan).exists())

    def test_financial_summary_recomputes_foreclosure_component_totals_after_reconciliation(self):
        loan = Loan.objects.create(
            user=self.user,
            loan_type="personal",
            lender="Axis Bank",
            loan_account_number="AXISSUMMARY001",
            principal=150000,
            interest_rate=12,
            emi=5200,
            tenure_months=36,
            remaining_balance=100000,
            start_date=timezone.localdate(),
        )
        snapshot = self._create_foreclosure_snapshot(loan=loan)
        closure_expense = Expense.objects.create(
            user=self.user,
            amount=104000,
            classification="loan",
            category="loan",
            merchant="Axis Bank",
            description="Axis Bank foreclosure payment AXISSUMMARY001",
            raw_description="AXIS BANK FORECLOSURE AXISSUMMARY001",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="bank_statement",
            external_reference="TXN-SUMMARY-001",
        )

        self.assertTrue(loan_foreclosure_service.reconcile_snapshot(snapshot, expenses=[closure_expense]))

        summary = build_financial_intelligence(self.user)
        self.assertEqual(summary["balance_sheet"]["total_liabilities"], 0.0)
        self.assertEqual(summary["loan_portfolio"]["active_loans"], 0)
        self.assertEqual(summary["loan_portfolio"]["manual_total_outstanding"], 0.0)
        self.assertEqual(
            summary["loan_portfolio"]["payment_component_totals"],
            {
                "principal_paid": 100000.0,
                "interest_paid": 2000.0,
                "charges_paid": 1000.0,
                "penalties_paid": 500.0,
                "tax_paid": 500.0,
            },
        )
        self.assertEqual(summary["loan_portfolio"]["detected_repayments"][0]["interest_paid"], 2000.0)
        self.assertEqual(
            summary["loan_portfolio"]["foreclosure_watchlist"][0]["settlement_allocation"]["allocated_components"]["charges_paid"],
            1000.0,
        )


class SystemTicketTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="ticket_user", password="Pass12345!")
        self.superuser = user_model.objects.create_superuser(username="ticket_admin", password="Pass12345!", email="admin@example.com")
        self.user_client = Client()
        self.user_client.force_login(self.user)
        self.admin_client = Client()
        self.admin_client.force_login(self.superuser)

    def test_high_severity_ticket_is_escalated_to_superuser_developers(self):
        create_response = self.user_client.post(
            "/api/reports/tickets/",
            data=json.dumps({"module": "loans", "title": "Loan parser mismatch", "summary": "Loan payment was matched to the wrong lender after statement import."}),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(SystemTicket.objects.count(), 1)
        ticket = SystemTicket.objects.get()
        self.assertEqual(ticket.severity, "high")
        self.assertEqual(ticket.handled_by, "developer")
        self.assertEqual(ticket.status, "open")

        user_queue = self.user_client.get("/api/reports/tickets/")
        self.assertEqual(user_queue.status_code, 200)
        self.assertEqual(len(user_queue.json()), 1)
        self.assertEqual(user_queue.json()[0]["handled_by"], "developer")

        admin_queue = self.admin_client.get("/api/reports/tickets/")
        self.assertEqual(admin_queue.status_code, 200)
        self.assertEqual(len(admin_queue.json()), 1)

    def test_medium_severity_ticket_is_auto_handled_by_alfred(self):
        create_response = self.user_client.post(
            "/api/reports/tickets/",
            data=json.dumps({"module": "reports", "title": "Chart spacing issue", "summary": "The chart card spacing looks slightly off after refresh."}),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        payload = create_response.json()
        self.assertEqual(payload["handled_by"], "alfred")
        self.assertEqual(payload["severity"], "medium")
        self.assertIn("internal_clock", payload)

        ticket = SystemTicket.objects.latest("id")
        self.assertEqual(ticket.status, "resolved")
        self.assertEqual(ticket.handled_by, "alfred")
        self.assertIsNotNone(ticket.resolved_at)
        self.assertIn("internal_clock", ticket.context_payload)

    def test_superuser_can_resolve_escalated_ticket(self):
        create_response = self.user_client.post(
            "/api/reports/tickets/",
            data=json.dumps({"module": "expenses", "title": "Duplicate transaction risk", "summary": "Duplicate transaction detected in the wrong account after import."}),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        ticket = SystemTicket.objects.get()
        self.assertEqual(ticket.handled_by, "developer")

        resolve_response = self.admin_client.patch(
            f"/api/reports/tickets/{ticket.id}/",
            data=json.dumps({"status": "resolved", "admin_note": "Fixed in import dedupe patch.", "resolution_summary": "Developer validated and resolved the high-severity import issue."}),
            content_type="application/json",
        )
        self.assertEqual(resolve_response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, "resolved")
        self.assertEqual(ticket.admin_note, "Fixed in import dedupe patch.")
        self.assertIsNotNone(ticket.resolved_at)
