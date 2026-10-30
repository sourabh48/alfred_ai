import math

from rest_framework import serializers
from .models import RelationshipProfile

class RelationshipProfileSerializer(serializers.ModelSerializer):
    partner_financial_score = serializers.FloatField(required=False, min_value=0, max_value=100)
    partner_savings_habits = serializers.IntegerField(required=False, min_value=1, max_value=5)
    compatibility_score = serializers.FloatField(required=False, min_value=0, max_value=100)

    class Meta:
        model = RelationshipProfile
        fields = "__all__"
        read_only_fields = ["user", "created_at", "updated_at"]

    def _finite(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Enter a finite number.")
        return value

    def validate_partner_financial_score(self, value):
        return self._finite(value)

    def validate_compatibility_score(self, value):
        return self._finite(value)
