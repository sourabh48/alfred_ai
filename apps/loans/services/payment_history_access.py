from __future__ import annotations

from django.db import connection

from apps.loans.models import LoanPaymentHistory


DIRECT_VALUE_FIELD_COLUMNS = {
    "id": "id",
    "loan_id": "loan_id",
    "expense_reference_id": "expense_reference_id",
    "payment_date": "payment_date",
    "amount": "amount",
    "principal_component": "principal_component",
    "interest_component": "interest_component",
    "principal_paid": "principal_paid",
    "interest_paid": "interest_paid",
    "charges_paid": "charges_paid",
    "penalties_paid": "penalties_paid",
    "tax_paid": "tax_paid",
    "remaining_balance": "remaining_balance",
    "match_status": "match_status",
    "is_auto_detected": "is_auto_detected",
    "detection_confidence": "detection_confidence",
    "detection_reason": "detection_reason",
    "matched_reference": "matched_reference",
}
RELATED_VALUE_FIELDS = ("loan__lender", "loan__loan_account_number", "loan__emi")


def loan_payment_history_columns() -> set[str]:
    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, LoanPaymentHistory._meta.db_table)
    except Exception:
        return {column for column in DIRECT_VALUE_FIELD_COLUMNS.values() if column not in {"principal_paid", "interest_paid", "charges_paid", "penalties_paid", "tax_paid"}}
    return {column.name for column in description}


def fetch_payment_history_rows(
    *,
    user,
    expense_reference_ids=None,
    require_expense_reference: bool = False,
    include_loan_fields: bool = False,
) -> list[dict]:
    direct_columns = loan_payment_history_columns()
    value_fields = [
        field_name
        for field_name, column_name in DIRECT_VALUE_FIELD_COLUMNS.items()
        if column_name in direct_columns
    ]
    if include_loan_fields:
        value_fields.extend(RELATED_VALUE_FIELDS)

    queryset = LoanPaymentHistory.objects.filter(loan__user=user)
    if require_expense_reference:
        queryset = queryset.filter(expense_reference__isnull=False)
    if expense_reference_ids is not None:
        expense_reference_ids = [value for value in expense_reference_ids if value]
        if not expense_reference_ids:
            return []
        queryset = queryset.filter(expense_reference_id__in=expense_reference_ids)

    return list(queryset.values(*value_fields).order_by("-payment_date", "-id"))
