import math

from rest_framework import serializers
from .models import RiskSignal

class RiskSignalSerializer(serializers.ModelSerializer):
    layoff_risk = serializers.FloatField(required=False, min_value=0, max_value=100)
    illness_risk = serializers.FloatField(required=False, min_value=0, max_value=100)
    relocation_risk = serializers.FloatField(required=False, min_value=0, max_value=100)

    class Meta:
        model = RiskSignal
        fields = "__all__"
        read_only_fields = ["user"]

    def _finite(self, value):
        if not math.isfinite(value):
            raise serializers.ValidationError("Enter a finite number.")
        return value

    def validate_layoff_risk(self, value):
        return self._finite(value)

    def validate_illness_risk(self, value):
        return self._finite(value)

    def validate_relocation_risk(self, value):
        return self._finite(value)
