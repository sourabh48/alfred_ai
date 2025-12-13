from django.contrib import admin
from .models import Loan

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("user", "loan_type", "principal", "interest_rate", "emi", "start_date")
    list_filter = ("loan_type",)
    search_fields = ("loan_type",)
