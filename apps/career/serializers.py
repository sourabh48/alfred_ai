from rest_framework import serializers
from .models import CareerProfile

class CareerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerProfile
        fields = "__all__"
        read_only_fields = ["user"]
