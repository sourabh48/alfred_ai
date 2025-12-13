from rest_framework import serializers
from .models import GeneratedReport

class GeneratedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedReport
        fields = "__all__"
        read_only_fields = ["user"]
