from rest_framework import serializers
from datetime import datetime
from math import isfinite
from .models import Budget

class BudgetSerializer(serializers.ModelSerializer):
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

    def validate(self, attrs):
        for field in ("base_budget", "inflation_adjusted", "spent"):
            if field in attrs and (not isfinite(attrs[field]) or attrs[field] < 0):
                raise serializers.ValidationError({field: "Enter a finite amount of zero or more."})
        return attrs
