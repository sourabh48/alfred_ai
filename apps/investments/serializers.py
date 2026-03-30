from rest_framework import serializers
from .models import Investment


class InvestmentSerializer(serializers.ModelSerializer):
    gain_loss = serializers.FloatField(read_only=True)

    class Meta:
        model = Investment
        fields = (
            "id",
            "user",
            "asset_type",
            "asset_name",
            "institution",
            "account_number",
            "invested_amount",
            "monthly_sip",
            "current_value",
            "annual_return_rate",
            "risk_level",
            "notes",
            "gain_loss",
            "created_at",
            "updated_at",
        )
        read_only_fields = ["user", "gain_loss", "created_at", "updated_at"]

    def validate(self, attrs):
        invested_amount = attrs.get("invested_amount", getattr(self.instance, "invested_amount", 0))
        current_value = attrs.get("current_value", getattr(self.instance, "current_value", 0))
        monthly_sip = attrs.get("monthly_sip", getattr(self.instance, "monthly_sip", 0))
        if invested_amount < 0 or current_value < 0 or monthly_sip < 0:
            raise serializers.ValidationError("Investment amounts cannot be negative.")
        return attrs
