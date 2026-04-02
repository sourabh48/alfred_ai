from rest_framework import serializers
from .models import RelationshipProfile

class RelationshipProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationshipProfile
        fields = "__all__"
        read_only_fields = ["user", "created_at", "updated_at"]
