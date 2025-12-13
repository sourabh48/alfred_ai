from django.contrib import admin
from .models import RiskSignal

@admin.register(RiskSignal)
class RiskSignalAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "layoff_risk",
        "illness_risk",
        "relocation_risk",
        "timestamp",
    )
