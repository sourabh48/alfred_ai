from rest_framework import serializers
from .models import CareerJobAnalysis, CareerProfile, CareerResume

class CareerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerProfile
        fields = "__all__"
        read_only_fields = ["user"]


class CareerResumeSerializer(serializers.ModelSerializer):
    parser_status_label = serializers.CharField(source="get_parser_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CareerResume
        fields = (
            "id",
            "user",
            "uploaded_file",
            "file_url",
            "file_name",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "extracted_payload",
            "summary",
            "strengths",
            "weaknesses",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "file_url",
            "file_name",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "extracted_payload",
            "summary",
            "strengths",
            "weaknesses",
            "created_at",
            "updated_at",
        )

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.uploaded_file:
            return ""
        if request is not None:
            return request.build_absolute_uri(obj.uploaded_file.url)
        return obj.uploaded_file.url


class CareerJobAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = CareerJobAnalysis
        fields = (
            "id",
            "user",
            "source_name",
            "job_url",
            "apply_url",
            "company",
            "job_title",
            "location",
            "fit_score",
            "market_risk_score",
            "strengths",
            "gaps",
            "summary",
            "extracted_payload",
            "evidence",
            "created_at",
        )
        read_only_fields = (
            "user",
            "source_name",
            "apply_url",
            "company",
            "job_title",
            "location",
            "fit_score",
            "market_risk_score",
            "strengths",
            "gaps",
            "summary",
            "extracted_payload",
            "evidence",
            "created_at",
        )
