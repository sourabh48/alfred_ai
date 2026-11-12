from rest_framework import serializers
from datetime import datetime
from django.utils import timezone

from alfred_ai.services.currency import CURRENCY_CHOICES
from apps.expenses.money import money_float

from .models import Budget, SavingsGoal
from .money import BudgetMoneySerializerField, goal_progress


class SavingsGoalSerializer(serializers.ModelSerializer):
    target_amount = BudgetMoneySerializerField()
    saved_amount = BudgetMoneySerializerField(required=False)
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal
        fields = ("id", "name", "target_amount", "saved_amount", "target_date", "currency", "created_at", "updated_at", "progress")
        read_only_fields = ("created_at", "updated_at")

    def validate_name(self, value):
        value = " ".join(value.split())
        if not value:
            raise serializers.ValidationError("Name the goal.")
        return value

    def validate_currency(self, value):
        return value or None  # FIN-15: blank means not recorded, never a guessed INR

    def validate_target_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a target above zero.")
        return value

    def get_progress(self, goal):
        result = goal_progress(goal.target_amount, goal.saved_amount, goal.target_date, timezone.localdate())
        return {**result, "remaining": money_float(result["remaining"]), "percent": float(result["percent"]),
                "monthly_needed": money_float(result["monthly_needed"]) if result["monthly_needed"] is not None else None}


class BudgetSerializer(serializers.ModelSerializer):
    base_budget = BudgetMoneySerializerField()
    inflation_adjusted = BudgetMoneySerializerField()
    # Bug 6: spent comes from transactions when read; the stored column is legacy and no longer written.
    spent = serializers.SerializerMethodField()
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Budget
        fields = "__all__"
        read_only_fields = ["user"]

    def validate_currency(self, value):
        return value or None  # FIN-15: blank means not recorded, never a guessed INR

    def get_spent(self, budget):
        from .services.budget_intelligence import budget_spent
        value = budget_spent(budget)
        return money_float(value) if value is not None else None

    def validate_month(self, value):
        for pattern in ("%b %Y", "%B %Y", "%Y-%m"):
            try:
                return datetime.strptime(value.strip(), pattern).strftime("%b %Y")
            except ValueError:
                continue
        raise serializers.ValidationError("Enter a month and year, for example Sep 2026 or 2026-09.")
