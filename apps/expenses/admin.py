from django.contrib import admin

from .models import BankAccount, Expense, StatementUpload


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "bank_name",
        "nickname",
        "masked_account_number",
        "account_type",
        "current_balance",
        "is_primary",
        "is_active",
        "last_synced_at",
    )
    list_filter = ("account_type", "is_primary", "is_active", "bank_name")
    search_fields = ("bank_name", "nickname", "account_holder", "account_number")


@admin.register(StatementUpload)
class StatementUploadAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "bank_name",
        "file_name",
        "source",
        "account_number",
        "statement_start",
        "statement_end",
        "imported_count",
        "uploaded_at",
    )
    list_filter = ("source", "uploaded_at")
    search_fields = ("file_name", "account_holder", "account_number")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "transaction_date",
        "bank_account",
        "merchant",
        "company_name",
        "classification",
        "category",
        "direction",
        "amount",
        "is_emotional",
        "payment_mode",
        "source",
    )
    list_filter = ("classification", "category", "payment_mode", "direction", "source", "is_emotional")
    search_fields = ("merchant", "counterparty", "company_name", "description", "raw_description", "external_reference")
    date_hierarchy = "transaction_date"
