"""
Loan Intelligence Service
Automatically detects loan payments from expense transactions and tracks loan lifecycle.
"""
from __future__ import annotations

from uuid import uuid4
from django.utils import timezone
from typing import Dict, List, Optional

from apps.expenses.models import Expense
from apps.loans.models import Loan, LoanPaymentHistory
from apps.reports.services import reporting_service


class LoanIntelligenceService:
    """ML-powered loan tracking and detection."""

    LOAN_KEYWORDS = [
        "BAJAJ", "POONAWALLA", "HOUSING FINANCE", "HDFC HOME", "ICICI HOME",
        "SBI LOAN", "AXIS LOAN", "EMI", "LOAN", "FINCORP", "FINSERV",
        "BAJAJ HOUSING", "TATA CAPITAL", "FULLERTON", "MUTHOOT", "MANAPPURAM",
    ]

    def detect_loan_payments(self, user, expenses: Optional[List[Expense]] = None) -> Dict[str, any]:
        """
        Scan expense transactions to detect loan payments and auto-create/update loan records.
        """
        if expenses is None:
            loan_expenses = list(
                Expense.objects.filter(
                    user=user,
                    direction="debit",
                    classification="loan"
                ).order_by("transaction_date", "id")
            )
        else:
            loan_expenses = [
                item for item in expenses
                if item.direction == "debit" and item.classification == "loan"
            ]

        detected_loans = []
        updated_loans = []
        new_payments = []
        review_payments = []

        for expense in loan_expenses:
            # Check if payment is already linked
            if hasattr(expense, "linked_loan_payments") and expense.linked_loan_payments.exists():
                continue

            # Try to match to existing loan
            match = self.match_expense_to_loan(user, expense)
            matched_loan = match.get("loan")

            if matched_loan:
                # Update existing loan
                payment = self._create_payment_record(matched_loan, expense, match)
                if payment.match_status == "matched":
                    self._update_loan_from_payment(matched_loan, payment)
                    payment.loan_effect_applied = True
                    payment.save(update_fields=["loan_effect_applied"])
                updated_loans.append(matched_loan)
                new_payments.append(payment)
                if payment.match_status == "review":
                    review_payments.append(payment)
            else:
                # Create new loan from detected pattern
                new_loan = self._create_loan_from_expense(user, expense)
                if new_loan:
                    payment = self._create_payment_record(
                        new_loan,
                        expense,
                        {"confidence": 62.0, "reason": "Recurring EMI-like pattern detected from statement history."},
                    )
                    if payment.match_status == "matched":
                        self._update_loan_from_payment(new_loan, payment)
                        payment.loan_effect_applied = True
                        payment.save(update_fields=["loan_effect_applied"])
                    detected_loans.append(new_loan)
                    new_payments.append(payment)
                    review_payments.append(payment)

        if review_payments:
            reporting_service.create_system_ticket(
                user=user,
                module="loans",
                title="Loan payment matches need review",
                summary=f"{len(review_payments)} detected loan payment(s) were linked with lower confidence and may need parser or matching review.",
                context_payload={
                    "payment_ids": [item.id for item in review_payments],
                    "loans": [item.loan_id for item in review_payments],
                },
            )

        return {
            "detected_loans": len(detected_loans),
            "updated_loans": len(updated_loans),
            "new_payments": len(new_payments),
            "review_payments": len(review_payments),
            "loans": detected_loans,
        }

    def match_expense_to_loan(self, user, expense: Expense) -> Dict[str, any]:
        """Match an expense to the most likely active loan and expose confidence metadata."""
        active_loans = list(Loan.objects.filter(user=user, is_active=True).order_by("-updated_at", "-id"))
        best_loan = None
        best_score = 0.0
        best_reason = "No reliable loan match was found."

        for loan in active_loans:
            score, reason = self._loan_match_score(loan, expense)
            if score > best_score:
                best_loan = loan
                best_score = score
                best_reason = reason

        if best_loan and best_score >= 45:
            return {"loan": best_loan, "confidence": round(best_score, 1), "reason": best_reason}
        return {"loan": None, "confidence": round(best_score, 1), "reason": best_reason}

    def _create_loan_from_expense(self, user, expense: Expense) -> Optional[Loan]:
        """Auto-create loan from detected EMI pattern."""
        # Look for recurring payments (same merchant, similar amounts)
        similar_expenses = Expense.objects.filter(
            user=user,
            direction="debit",
            classification="loan",
            company_name__iexact=expense.company_name or "",
            amount__gte=expense.amount * 0.95,
            amount__lte=expense.amount * 1.05,
        ).order_by("transaction_date")

        if similar_expenses.count() < 2:
            return None

        # Estimate loan parameters
        emi = expense.amount
        first_payment = similar_expenses.first()
        lender = expense.company_name or expense.merchant or "Unknown Lender"

        # Estimate principal (rough approximation)
        estimated_principal = emi * 24  # Assume 2-year tenure initially

        loan = Loan.objects.create(
            user=user,
            loan_type=self._infer_loan_type(lender, expense.description),
            lender=lender[:120],
            loan_account_number=expense.external_reference[:64] if expense.external_reference else "",
            principal=estimated_principal,
            interest_rate=10.0,  # Default estimate
            emi=emi,
            tenure_months=24,  # Default estimate
            remaining_balance=estimated_principal,
            start_date=first_payment.transaction_date,
            is_active=True,
            status="active",
            auto_detected=True,
            last_payment_date=expense.transaction_date,
            total_paid=emi,
        )

        return loan

    def _create_payment_record(self, loan: Loan, expense: Expense, match: Optional[Dict[str, any]] = None) -> LoanPaymentHistory:
        """Create payment history record from expense."""
        # Calculate principal vs interest split
        remaining = loan.remaining_balance or loan.principal
        interest_component = (remaining * loan.interest_rate / 100) / 12
        principal_component = expense.amount - interest_component
        confidence = float((match or {}).get("confidence", 0) or 0)
        reason = (match or {}).get("reason", "")
        match_status = "matched" if confidence >= 70 else "review"

        payment = LoanPaymentHistory.objects.create(
            loan=loan,
            payment_date=expense.transaction_date,
            amount=expense.amount,
            principal_component=max(0, principal_component),
            interest_component=max(0, interest_component),
            principal_paid=max(0, principal_component),
            interest_paid=max(0, interest_component),
            charges_paid=0,
            penalties_paid=0,
            tax_paid=0,
            remaining_balance=max(0, remaining - principal_component),
            is_auto_detected=True,
            detection_confidence=confidence,
            detection_reason=reason[:255],
            matched_reference=(expense.external_reference or "")[:120],
            match_status=match_status,
            expense_reference=expense,
        )

        return payment

    def _update_loan_from_payment(self, loan: Loan, payment: LoanPaymentHistory):
        """Update loan status based on new payment."""
        loan.last_payment_date = payment.payment_date
        loan.total_paid += payment.amount
        loan.remaining_balance = payment.remaining_balance

        # Check if loan is paid off
        if loan.remaining_balance <= 100:  # Allow small rounding differences
            loan.is_active = False
            loan.status = "closed"
            loan.closed_on = payment.payment_date
            loan.remaining_balance = 0

        loan.save(update_fields=[
            "last_payment_date",
            "total_paid",
            "remaining_balance",
            "is_active",
            "status",
            "closed_on",
            "updated_at",
        ])

    def _infer_loan_type(self, lender: str, description: str) -> str:
        """Infer loan type from lender name and description."""
        text = f"{lender} {description}".upper()

        if any(keyword in text for keyword in ["HOME", "HOUSING", "MORTGAGE"]):
            return "home"
        elif any(keyword in text for keyword in ["CAR", "AUTO", "VEHICLE"]):
            return "car"
        elif any(keyword in text for keyword in ["EDUCATION", "STUDENT"]):
            return "education"
        elif any(keyword in text for keyword in ["BUSINESS", "COMMERCIAL"]):
            return "business"
        elif any(keyword in text for keyword in ["PERSONAL", "PL "]):
            return "personal"
        elif any(keyword in text for keyword in ["CREDIT CARD", "CARD"]):
            return "credit_card"

        return "other"

    def consolidate_loans(
        self,
        *,
        user,
        source_loans: List[Loan],
        consolidated_loan_type: str,
        lender: str,
        loan_account_number: str,
        principal: float,
        interest_rate: float,
        emi: float,
        tenure_months: int,
        start_date,
        notes: str = "",
    ) -> Loan:
        consolidation_group = uuid4().hex[:12]
        consolidated_loan = Loan.objects.create(
            user=user,
            loan_type=consolidated_loan_type,
            lender=lender,
            loan_account_number=loan_account_number,
            principal=principal,
            interest_rate=interest_rate,
            emi=emi,
            tenure_months=tenure_months,
            remaining_balance=principal,
            start_date=start_date,
            status="active",
            is_active=True,
            consolidation_group=consolidation_group,
            notes=notes,
        )

        for loan in source_loans:
            loan.is_active = False
            loan.status = "prepaid"
            loan.closed_on = start_date
            loan.closure_reason = "consolidated"
            loan.consolidated_into = consolidated_loan
            loan.consolidation_group = consolidation_group
            loan.save(
                update_fields=[
                    "is_active",
                    "status",
                    "closed_on",
                    "closure_reason",
                    "consolidated_into",
                    "consolidation_group",
                    "updated_at",
                ]
            )

        return consolidated_loan

    def calculate_loan_metrics(self, user) -> Dict[str, any]:
        """Calculate comprehensive loan metrics for user."""
        from apps.expenses.services.financial_intelligence import (
            _loan_counts_toward_recurring_emi,
            _loan_reporting_balance,
            resolve_canonical_financial_baseline,
        )

        baseline = resolve_canonical_financial_baseline(user)
        today = timezone.localdate()
        all_loans = list(Loan.objects.filter(user=user).order_by("-updated_at", "-id"))
        recurring_loans = []
        pending_foreclosure_balance = 0.0

        for loan in all_loans:
            balance = _loan_reporting_balance(loan, today=today)
            if loan.status == "foreclosure_pending" and round(float(balance or 0), 2) > 0:
                pending_foreclosure_balance += float(balance or 0)
            if _loan_counts_toward_recurring_emi(loan, balance):
                recurring_loans.append((loan, balance))

        total_principal = sum(float(loan.principal or 0) for loan, _ in recurring_loans)
        total_remaining = sum(float(balance or 0) for _, balance in recurring_loans)
        total_paid = sum(float(loan.total_paid or 0) for loan, _ in recurring_loans)
        total_monthly_emi = float(baseline.get("recurring_emi_burden", 0) or 0)
        monthly_income = float(baseline.get("monthly_income", 0) or 0)
        dti_ratio = (total_monthly_emi / monthly_income * 100) if monthly_income > 0 else 0.0

        # Get loan breakdown by type
        loan_breakdown = []
        for loan_type, label in Loan.LOAN_TYPE_CHOICES:
            type_loans = [(loan, balance) for loan, balance in recurring_loans if loan.loan_type == loan_type]
            if type_loans:
                loan_breakdown.append({
                    "type": label,
                    "count": len(type_loans),
                    "total_emi": round(sum(float(loan.emi or 0) for loan, _ in type_loans), 2),
                    "remaining_balance": round(sum(float(balance or 0) for _, balance in type_loans), 2),
                })

        return {
            "active_loan_count": len(recurring_loans),
            "total_principal": round(total_principal, 2),
            "total_remaining": round(total_remaining, 2),
            "total_paid": round(total_paid, 2),
            "completion_percentage": round((total_paid / total_principal * 100) if total_principal > 0 else 0, 2),
            "monthly_emi_burden": round(total_monthly_emi, 2),
            "debt_to_income_ratio": round(dti_ratio, 2),
            "monthly_income": round(monthly_income, 2),
            "fixed_obligations": round(float(baseline.get("fixed_obligations", 0) or 0), 2),
            "disposable_cash_flow": round(float(baseline.get("disposable_cash_flow", 0) or 0), 2),
            "savings_capacity": round(float(baseline.get("savings_capacity", 0) or 0), 2),
            "pending_foreclosure_balance": round(pending_foreclosure_balance, 2),
            "financial_baseline": baseline,
            "loan_breakdown": loan_breakdown,
        }

    def _loan_match_score(self, loan: Loan, expense: Expense) -> tuple[float, str]:
        text = " ".join(
            part for part in [
                expense.description,
                expense.raw_description,
                expense.external_reference,
                expense.company_name,
                expense.merchant,
                expense.counterparty,
            ]
            if part
        ).upper()
        reasons = []
        score = 0.0

        normalized_account = "".join(char for char in (loan.loan_account_number or "").upper() if char.isalnum())
        if normalized_account and normalized_account[-6:] and normalized_account[-6:] in text:
            score += 62
            reasons.append("Statement text contains the loan account reference.")

        lender = (loan.lender or "").upper()
        lender_tokens = [token for token in lender.replace("&", " ").split() if len(token) > 2]
        token_hits = [token for token in lender_tokens if token in text]
        if token_hits:
            score += min(45, 15 * len(token_hits))
            reasons.append(f"Lender tokens matched: {', '.join(token_hits[:3])}.")

        amount_delta = abs(float(loan.emi or 0) - float(expense.amount or 0))
        if loan.emi and amount_delta <= max(loan.emi * 0.02, 50):
            score += 30
            reasons.append("Expense amount closely matches the configured EMI.")
        elif loan.emi and amount_delta <= max(loan.emi * 0.05, 150):
            score += 16
            reasons.append("Expense amount is within the EMI tolerance band.")

        if any(keyword in text for keyword in self.LOAN_KEYWORDS):
            score += 10
            reasons.append("Loan-related keywords were detected in the bank statement text.")

        if loan.loan_type == "credit_card" and "CARD" in text:
            score += 6
            reasons.append("Credit-card debt wording was detected.")

        return score, " ".join(reasons) if reasons else "Only weak signals matched this expense to the loan."


# Singleton instance
loan_intelligence_service = LoanIntelligenceService()
