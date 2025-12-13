from django.contrib import admin
from .models import Expense

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "user", "amount", "category", "payment_mode", "timestamp",
        "is_emotional", "model_confidence"
    )
    list_filter = ("category", "payment_mode", "is_emotional")
    search_fields = ("description",)
    date_hierarchy = "timestamp"
