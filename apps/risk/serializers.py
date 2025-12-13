from rest_framework import serializers
from .models import RiskSignal

class RiskSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskSignal
        fields = "__all__"
        read_only_fields = ["user"]
