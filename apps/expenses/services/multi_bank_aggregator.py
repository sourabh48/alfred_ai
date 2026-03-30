"""
Multi-Bank Account Aggregation Service
Manages multiple bank accounts and provides consolidated financial view.
"""
from __future__ import annotations

from typing import Dict, List
from django.db.models import Sum, Count, Q, Max
from django.utils import timezone
from datetime import timedelta

from apps.expenses.models import BankAccount, Expense


class MultiBankAggregatorService:
    """
    Service to manage multiple bank accounts and provide unified financial insights.
    """

    def get_consolidated_view(self, user) -> Dict[str, any]:
        """
        Get consolidated view of all user's bank accounts.
        """
        accounts = BankAccount.objects.filter(user=user, is_active=True)

        if not accounts.exists():
            return {
                "total_accounts": 0,
                "total_balance": 0,
                "accounts": [],
                "message": "No active bank accounts found. Add your accounts to get started.",
            }

        account_details = []
        total_balance = 0

        for account in accounts:
            # Get transaction count for this account
            txn_count = Expense.objects.filter(
                user=user,
                bank_account=account
            ).count()

            # Get last transaction date
            last_txn = Expense.objects.filter(
                user=user,
                bank_account=account
            ).aggregate(last=Max("transaction_date"))["last"]

            # Get monthly spending from this account
            month_start = timezone.now().date().replace(day=1)
            monthly_spending = Expense.objects.filter(
                user=user,
                bank_account=account,
                transaction_date__gte=month_start,
                direction="debit"
            ).aggregate(total=Sum("amount"))["total"] or 0

            balance = account.current_balance or 0
            total_balance += balance

            account_details.append({
                "id": account.id,
                "display_name": account.display_name,
                "bank_name": account.bank_name,
                "account_type": account.get_account_type_display(),
                "masked_account": account.masked_account_number,
                "balance": round(balance, 2),
                "is_primary": account.is_primary,
                "transaction_count": txn_count,
                "last_transaction": last_txn.isoformat() if last_txn else None,
                "monthly_spending": round(monthly_spending, 2),
                "last_synced": account.last_synced_at.isoformat() if account.last_synced_at else None,
            })

        # Sort by primary first, then by balance
        account_details.sort(key=lambda x: (-x["is_primary"], -x["balance"]))

        return {
            "total_accounts": accounts.count(),
            "total_balance": round(total_balance, 2),
            "accounts": account_details,
            "primary_account": next((a for a in account_details if a["is_primary"]), None),
        }

    def get_account_analytics(self, user, account_id: int) -> Dict[str, any]:
        """
        Get detailed analytics for a specific bank account.
        """
        try:
            account = BankAccount.objects.get(id=account_id, user=user)
        except BankAccount.DoesNotExist:
            return {"error": "Account not found"}

        # Last 30 days analysis
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        expenses = Expense.objects.filter(
            user=user,
            bank_account=account,
            transaction_date__gte=thirty_days_ago
        )

        total_debits = expenses.filter(direction="debit").aggregate(
            total=Sum("amount")
        )["total"] or 0

        total_credits = expenses.filter(direction="credit").aggregate(
            total=Sum("amount")
        )["total"] or 0

        # Category breakdown
        category_breakdown = []
        for category, label in Expense.CATEGORY_CHOICES:
            if category in ["income", "transfer"]:
                continue

            cat_total = expenses.filter(
                category=category,
                direction="debit"
            ).aggregate(total=Sum("amount"))["total"] or 0

            if cat_total > 0:
                category_breakdown.append({
                    "category": label,
                    "amount": round(cat_total, 2),
                    "percentage": round((cat_total / total_debits * 100) if total_debits > 0 else 0, 2),
                })

        # Sort by amount
        category_breakdown.sort(key=lambda x: -x["amount"])

        # Monthly trend (last 6 months)
        monthly_trend = []
        for i in range(6):
            month_start = timezone.now().date() - timedelta(days=30 * (i + 1))
            month_end = timezone.now().date() - timedelta(days=30 * i)

            month_debits = Expense.objects.filter(
                user=user,
                bank_account=account,
                direction="debit",
                transaction_date__gte=month_start,
                transaction_date__lt=month_end
            ).aggregate(total=Sum("amount"))["total"] or 0

            month_credits = Expense.objects.filter(
                user=user,
                bank_account=account,
                direction="credit",
                transaction_date__gte=month_start,
                transaction_date__lt=month_end
            ).aggregate(total=Sum("amount"))["total"] or 0

            monthly_trend.append({
                "month": month_start.strftime("%b %Y"),
                "debits": round(month_debits, 2),
                "credits": round(month_credits, 2),
                "net": round(month_credits - month_debits, 2),
            })

        monthly_trend.reverse()

        return {
            "account": {
                "id": account.id,
                "display_name": account.display_name,
                "bank_name": account.bank_name,
                "account_type": account.get_account_type_display(),
                "balance": account.current_balance or 0,
            },
            "last_30_days": {
                "total_debits": round(total_debits, 2),
                "total_credits": round(total_credits, 2),
                "net_flow": round(total_credits - total_debits, 2),
                "transaction_count": expenses.count(),
            },
            "category_breakdown": category_breakdown,
            "monthly_trend": monthly_trend,
        }

    def detect_duplicate_transactions(self, user) -> List[Dict]:
        """
        Detect potential duplicate transactions across multiple accounts.
        Useful when transactions are imported from different sources.
        """
        # Find transactions with same amount, date, and similar description
        thirty_days_ago = timezone.now().date() - timedelta(days=30)

        expenses = Expense.objects.filter(
            user=user,
            transaction_date__gte=thirty_days_ago
        ).values(
            "amount",
            "transaction_date",
            "merchant",
            "direction"
        ).annotate(
            count=Count("id")
        ).filter(count__gt=1)

        duplicates = []
        for exp_group in expenses:
            if exp_group["count"] > 1:
                # Get actual expense records
                similar_expenses = Expense.objects.filter(
                    user=user,
                    amount=exp_group["amount"],
                    transaction_date=exp_group["transaction_date"],
                    merchant=exp_group["merchant"],
                    direction=exp_group["direction"]
                )

                # Check if they're from different accounts
                distinct_accounts = similar_expenses.values("bank_account").distinct().count()

                if distinct_accounts > 1:
                    duplicates.append({
                        "amount": exp_group["amount"],
                        "date": exp_group["transaction_date"].isoformat(),
                        "merchant": exp_group["merchant"],
                        "count": exp_group["count"],
                        "expense_ids": list(similar_expenses.values_list("id", flat=True)),
                    })

        return duplicates

    def set_primary_account(self, user, account_id: int) -> Dict[str, any]:
        """Set an account as primary."""
        try:
            # Remove primary flag from all accounts
            BankAccount.objects.filter(user=user).update(is_primary=False)

            # Set new primary
            account = BankAccount.objects.get(id=account_id, user=user)
            account.is_primary = True
            account.save(update_fields=["is_primary"])

            return {
                "success": True,
                "message": f"{account.display_name} is now your primary account.",
            }
        except BankAccount.DoesNotExist:
            return {
                "success": False,
                "message": "Account not found.",
            }

    def suggest_account_for_transaction(self, user, amount: float, category: str) -> Dict[str, any]:
        """
        Suggest which account to use for a transaction based on:
        - Account balance
        - Account type
        - Historical usage patterns
        """
        accounts = BankAccount.objects.filter(user=user, is_active=True)

        if not accounts.exists():
            return {"suggested_account": None}

        # Score each account
        account_scores = []

        for account in accounts:
            score = 0

            # Primary account gets bonus
            if account.is_primary:
                score += 30

            # Balance check
            balance = account.current_balance or 0
            if balance >= amount * 1.5:
                score += 40
            elif balance >= amount:
                score += 20

            # Account type appropriateness
            if category in ["rent", "loan", "bills"] and account.account_type == "salary":
                score += 20
            elif category in ["shopping", "food"] and account.account_type in ["savings", "current"]:
                score += 10

            # Historical usage pattern
            past_usage = Expense.objects.filter(
                user=user,
                bank_account=account,
                category=category
            ).count()
            score += min(past_usage * 2, 20)

            account_scores.append({
                "account": account,
                "score": score,
            })

        # Sort by score
        account_scores.sort(key=lambda x: -x["score"])

        best_account = account_scores[0]["account"] if account_scores else None

        return {
            "suggested_account": {
                "id": best_account.id,
                "display_name": best_account.display_name,
                "balance": best_account.current_balance or 0,
                "confidence": min(account_scores[0]["score"], 100) if account_scores else 0,
            } if best_account else None,
        }


# Singleton instance
multi_bank_aggregator = MultiBankAggregatorService()
