from django.contrib import admin
from .models import RelationshipProfile

@admin.register(RelationshipProfile)
class RelationshipProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "partner_name",
        "partner_financial_score",
        "partner_savings_habits",
        "compatibility_score",
    )
