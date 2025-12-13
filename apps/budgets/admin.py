from django.contrib import admin
from .models import Budget

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("user", "month", "base_budget", "inflation_adjusted", "spent")
    list_filter = ("month",)
