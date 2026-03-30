from rest_framework import serializers
from .models import BehavioralSignal

class BehavioralSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehavioralSignal
        fields = "__all__"
        read_only_fields = ["user", "timestamp"]

    def validate_stress_score(self, value):
        if not 0 <= value <= 10:
            raise serializers.ValidationError("Stress score must be between 0 and 10.")
        return value

    def validate_sleep_hours(self, value):
        if not 0 <= value <= 24:
            raise serializers.ValidationError("Sleep hours must be between 0 and 24.")
        return value

    def validate_work_hours(self, value):
        if not 0 <= value <= 24:
            raise serializers.ValidationError("Work hours must be between 0 and 24.")
        return value
