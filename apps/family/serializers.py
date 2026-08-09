from rest_framework import serializers
from .models import Dependent

class DependentSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(min_value=0)
    name = serializers.CharField(max_length=50, allow_blank=False, trim_whitespace=True)
    relation = serializers.CharField(max_length=50, allow_blank=False, trim_whitespace=True)

    class Meta:
        model = Dependent
        fields = "__all__"
        read_only_fields = ["user"]
