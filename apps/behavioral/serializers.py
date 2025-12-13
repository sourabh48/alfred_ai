from rest_framework import serializers
from .models import BehavioralSignal

class BehavioralSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehavioralSignal
        fields = "__all__"
        read_only_fields = ["user"]
