from rest_framework import serializers
from alfred_ai.services.currency import CURRENCY_CHOICES

from .models import IncomeBasis, User
from .money import ProfileMoneySerializerField

class UserSerializer(serializers.ModelSerializer):
    monthly_income = ProfileMoneySerializerField(required=False)
    monthly_income_basis = serializers.ChoiceField(choices=IncomeBasis.choices, required=False)
    variable_income = ProfileMoneySerializerField(required=False)
    rent_or_emi = ProfileMoneySerializerField(required=False)
    income_currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    variable_income_currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    rent_currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    city = serializers.CharField(required=False, allow_blank=True, max_length=100)
    country = serializers.CharField(required=False, allow_blank=True, max_length=100)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "monthly_income",
            "monthly_income_basis",
            "variable_income",
            "rent_or_emi",
            "income_currency",
            "variable_income_currency",
            "rent_currency",
            "city",
            "country",
            "created_at",
        ]
        read_only_fields = ["id", "username", "created_at"]

    def validate(self, attrs):
        for name in ("income_currency", "variable_income_currency", "rent_currency"):
            if name in attrs:
                attrs[name] = attrs[name] or None  # blank means not recorded, never a guessed INR
        return attrs

    def validate_monthly_income_basis(self, value):
        if value == IncomeBasis.UNCONFIRMED:
            raise serializers.ValidationError("Choose per month or per year.")
        return value
