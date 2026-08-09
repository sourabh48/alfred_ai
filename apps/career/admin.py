from django.contrib import admin
from .models import CareerJobAnalysis, CareerProfile, CareerResume, CareerResumeLearningMemory
from .services.job_intelligence import job_intelligence

@admin.register(CareerProfile)
class CareerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "experience_years", "last_salary")
    search_fields = ("role", "skills")


@admin.register(CareerResume)
class CareerResumeAdmin(admin.ModelAdmin):
    list_display = ("user", "file_name", "parser_status", "parse_confidence", "created_at")
    search_fields = ("file_name", "summary")
    list_filter = ("parser_status",)


@admin.register(CareerJobAnalysis)
class CareerJobAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "job_title",
        "company",
        "fit_score",
        "market_risk_score",
        "opportunity_outcome_status",
        "opportunity_outcome_contract",
        "created_at",
    )
    search_fields = ("job_title", "company", "job_url")
    list_filter = ("parser_status",)
    readonly_fields = ("opportunity_outcome_summary",)

    def _opportunity_outcome(self, obj):
        payload = obj.extracted_payload if isinstance(obj.extracted_payload, dict) else {}
        outcome = payload.get("opportunity_outcome")
        return outcome if isinstance(outcome, dict) else {}

    @admin.display(description="Outcome")
    def opportunity_outcome_status(self, obj):
        return self._opportunity_outcome(obj).get("outcome", "")

    @admin.display(description="Outcome contract")
    def opportunity_outcome_contract(self, obj):
        status = job_intelligence.opportunity_outcome_contract_status(self._opportunity_outcome(obj))
        if status["valid"]:
            return "valid"
        return "missing: " + ", ".join(status["missing"])

    @admin.display(description="Opportunity outcome proof")
    def opportunity_outcome_summary(self, obj):
        outcome = self._opportunity_outcome(obj)
        if not outcome:
            return "No opportunity outcome recorded. Use Project Details Career Outcome Entry to record accepted or rejected salary-bearing decisions."
        status = job_intelligence.opportunity_outcome_contract_status(outcome)
        salary = " - ".join(
            str(value)
            for value in [outcome.get("salary_min_annual"), outcome.get("salary_max_annual")]
            if value
        )
        return (
            f"contract={'valid' if status['valid'] else 'missing ' + ', '.join(status['missing'])}; "
            f"decision={outcome.get('outcome', '')}; "
            f"salary_annual={salary or 'missing'}; "
            f"source_url={outcome.get('source_url', '') or 'missing'}; "
            f"location={outcome.get('location', '') or outcome.get('city', '') or outcome.get('state', '') or outcome.get('country', '') or 'missing'}"
        )


@admin.register(CareerResumeLearningMemory)
class CareerResumeLearningMemoryAdmin(admin.ModelAdmin):
    list_display = ("user", "file_extension", "role_hint", "successful_count", "review_count", "failed_count", "average_confidence", "last_seen_at")
    search_fields = ("user__username", "file_extension", "role_hint", "skill_signature")
