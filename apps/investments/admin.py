from django.contrib import admin
from .models import Investment

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("user", "asset_type", "monthly_sip", "current_value")
    list_filter = ("asset_type",)
