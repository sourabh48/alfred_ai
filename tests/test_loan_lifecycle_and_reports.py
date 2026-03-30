import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone

from apps.loans.models import Loan
from apps.reports.models import SystemTicket


class LoanLifecycleTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="loan_user", password="Pass12345!")
        self.client = Client()
        self.client.force_login(self.user)

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

    def test_foreclosure_requires_matching_document(self):
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
        self.assertEqual(response.status_code, 200)
        loan.refresh_from_db()
        self.assertFalse(loan.is_active)
        self.assertEqual(loan.status, "prepaid")
        self.assertEqual(loan.closure_reason, "foreclosed")


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
