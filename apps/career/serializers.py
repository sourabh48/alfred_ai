from rest_framework import serializers
from apps.users.money import ProfileMoneySerializerField
from apps.expenses.money import NumericMoneySerializerField
from .models import CareerJobAnalysis, CareerProfile, CareerResume


class CareerOpportunitySerializer(serializers.ModelSerializer):
    outcome = serializers.SerializerMethodField()
    salary_evidence = serializers.SerializerMethodField()

    class Meta:
        model = CareerJobAnalysis
        fields = ('id','company','job_title','location','job_url','updated_at','outcome','salary_evidence')

    def get_outcome(self, obj):
        payload = obj.extracted_payload if isinstance(obj.extracted_payload, dict) else {}
        outcome = payload.get('opportunity_outcome')
        fields = ('outcome','salary_min','salary_max','salary_currency','salary_period','decided_at',
                  'source_url','location','notes','rejection_reason','verification')
        return {key:outcome[key] for key in fields if key in outcome} if isinstance(outcome,dict) else {}

    def get_salary_evidence(self, obj):
        payload = obj.extracted_payload if isinstance(obj.extracted_payload, dict) else {}
        snapshot = payload.get('job_snapshot')
        fields = ('salary_min','salary_max','salary_currency','salary_period')
        return {key:snapshot[key] for key in fields if key in snapshot} if isinstance(snapshot,dict) else {}


class CareerProfileSerializer(serializers.ModelSerializer):
    last_salary = NumericMoneySerializerField(required=False)

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
    parser_status_label = serializers.CharField(source="get_parser_status_display", read_only=True)

    class Meta:
        model = CareerJobAnalysis
        fields = (
            "id",
            "user",
            "source_name",
            "source_document_name",
            "job_url",
            "apply_url",
            "company",
            "job_title",
            "location",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "extracted_text",
            "fit_score",
            "market_risk_score",
            "strengths",
            "gaps",
            "summary",
            "extracted_payload",
            "evidence",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "source_name",
            "source_document_name",
            "apply_url",
            "company",
            "job_title",
            "location",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "extracted_text",
            "fit_score",
            "market_risk_score",
            "strengths",
            "gaps",
            "summary",
            "extracted_payload",
            "evidence",
            "created_at",
            "updated_at",
        )


class CareerProjectionScenarioSerializer(serializers.Serializer):
    monthly_income = ProfileMoneySerializerField(required=False)
    variable_income = ProfileMoneySerializerField(required=False)
    rent_or_emi = ProfileMoneySerializerField(required=False)
    city = serializers.CharField(required=False, allow_blank=True, max_length=100)
    experience_years = serializers.FloatField(required=False, min_value=0)
    skills = serializers.ListField(
        child=serializers.CharField(allow_blank=False, trim_whitespace=True, max_length=80),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one scenario input to simulate.")
        return attrs
