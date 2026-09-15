from apps.expenses.models import Expense
import pandas as pd

def load_user_expense_history(user_id=None):
    """Load debit spending, retaining event dates and stable row ordering."""
    qs = Expense.objects.filter(classification="expense", direction="debit", amount__gt=0).exclude(
        category__in=["transfer", "income", "investment", "credit_card", "loan"]
    )
    if user_id:
        qs = qs.filter(user_id=user_id)

    df = pd.DataFrame.from_records(
        qs.values("id", "user_id", "amount", "category", "transaction_date", "timestamp", "is_emotional")
    )
    return df
