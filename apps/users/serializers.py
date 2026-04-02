from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
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
        read_only_fields = fields
