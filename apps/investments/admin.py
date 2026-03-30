from django.contrib import admin
from .models import Investment

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "asset_name",
        "asset_type",
        "institution",
        "invested_amount",
        "current_value",
        "monthly_sip",
        "annual_return_rate",
    )
    list_filter = ("asset_type",)
    search_fields = ("asset_name", "institution", "account_number", "notes")
