from rest_framework import serializers
from apps.users.money import ProfileMoneySerializerField
from apps.expenses.money import NumericMoneySerializerField
from .models import CareerJobAnalysis, CareerProfile, CareerResume
from .services import application_tracker


class CareerOpportunitySerializer(serializers.ModelSerializer):
    outcome = serializers.SerializerMethodField()
    salary_evidence = serializers.SerializerMethodField()
    interview_prep = serializers.SerializerMethodField()
    application = serializers.SerializerMethodField()
    match_freshness = serializers.SerializerMethodField()
    triage = serializers.SerializerMethodField()
    interview_notes = serializers.SerializerMethodField()

    class Meta:
        model = CareerJobAnalysis
        fields = ('id','company','job_title','location','job_url','updated_at','outcome','salary_evidence','interview_prep',
                  'application','match_freshness','triage','interview_notes')

    def get_interview_notes(self, obj):
        from .services import interview_notes
        notes = interview_notes.clean(obj.extracted_payload.get('interview_notes') if isinstance(obj.extracted_payload, dict) else None)
        if (notes['stories'] or notes['sessions']) and 'current_cv_text' not in self.context:
            request = self.context.get('request')
            resume = CareerResume.objects.filter(user=request.user).order_by('-created_at', '-id').only('extracted_text').first() if request else None
            self.context['current_cv_text'] = resume.extracted_text if resume else ''
        for story in notes['stories']:
            story['unverified_figures'] = interview_notes.unverified_figures(story, self.context['current_cv_text'])
        for session in notes['sessions']:
            if session['source'] == 'practice':
                for turn in session['turns']:
                    turn['checks'] = interview_notes.answer_checks(turn, session['round_type'], self.context['current_cv_text'])
        return notes

    def get_application(self, obj):
        from django.utils import timezone
        payload = obj.extracted_payload if isinstance(obj.extracted_payload, dict) else {}
        application = payload.get('application')
        return {**application_tracker._clean(application),
                'follow_up': application_tracker.follow_up_status(application, today=timezone.localdate())}

    def get_triage(self, obj):
        triage = obj.extracted_payload.get('triage') if isinstance(obj.extracted_payload, dict) else None
        return triage if isinstance(triage, dict) else None

    def get_match_freshness(self, obj):
        # The list shares one context, so the owner's current resume is read once per page.
        if 'current_resume_evidence' not in self.context:
            request = self.context.get('request')
            self.context['current_resume_evidence'] = application_tracker.current_resume_evidence(request.user) if request else None
        return application_tracker.match_freshness(obj.extracted_payload, self.context['current_resume_evidence'])

    def get_interview_prep(self, obj):
        from .services.job_intelligence import job_intelligence
        return job_intelligence.interview_prep(obj)

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

    def validate_salary_currency(self, value):
        return value or None  # FIN-15: blank means not recorded, never a guessed INR


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
    fit_score = serializers.FloatField(source="available_fit_score", read_only=True, allow_null=True)
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
