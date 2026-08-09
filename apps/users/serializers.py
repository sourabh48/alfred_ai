from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    monthly_income = serializers.FloatField(min_value=0, required=False)
    variable_income = serializers.FloatField(min_value=0, required=False)
    rent_or_emi = serializers.FloatField(min_value=0, required=False)
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
            "variable_income",
            "rent_or_emi",
            "city",
            "country",
            "created_at",
        ]
        read_only_fields = ["id", "username", "created_at"]
