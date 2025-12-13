from apps.expenses.models import Expense
import pandas as pd

def load_user_expense_history(user_id=None):
    """Load expenses for all users or single user."""
    qs = Expense.objects.all()
    if user_id:
        qs = qs.filter(user_id=user_id)

    df = pd.DataFrame.from_records(
        qs.values("user_id", "amount", "category", "timestamp", "is_emotional")
    )
    return df
