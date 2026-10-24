from rest_framework import serializers
from datetime import datetime
from .models import Budget
from .money import BudgetMoneySerializerField

class BudgetSerializer(serializers.ModelSerializer):
    base_budget = BudgetMoneySerializerField()
    inflation_adjusted = BudgetMoneySerializerField()
    spent = BudgetMoneySerializerField(required=False)

    class Meta:
        model = Budget
        fields = "__all__"
        read_only_fields = ["user"]

    def validate_month(self, value):
        for pattern in ("%b %Y", "%B %Y", "%Y-%m"):
            try:
                return datetime.strptime(value.strip(), pattern).strftime("%b %Y")
            except ValueError:
                continue
        raise serializers.ValidationError("Enter a month and year, for example Sep 2026 or 2026-09.")
