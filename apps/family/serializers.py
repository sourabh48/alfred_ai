from rest_framework import serializers
from .models import Dependent

class DependentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dependent
        fields = "__all__"
        read_only_fields = ["user"]
