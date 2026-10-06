from rest_framework import serializers
from .models import Dependent

class FamilyFinancialSharingSerializer(serializers.Serializer):
    share_financial_summary = serializers.BooleanField(required=True)

    def validate(self, attrs):
        if set(self.initial_data) != {"share_financial_summary"} or not isinstance(self.initial_data["share_financial_summary"], bool):
            raise serializers.ValidationError("Provide only share_financial_summary as a JSON boolean.")
        return attrs


class DependentSerializer(serializers.ModelSerializer):
    age = serializers.IntegerField(min_value=0)
    name = serializers.CharField(max_length=50, allow_blank=False, trim_whitespace=True)
    relation = serializers.CharField(max_length=50, allow_blank=False, trim_whitespace=True)

    class Meta:
        model = Dependent
        fields = "__all__"
        read_only_fields = ["user"]
