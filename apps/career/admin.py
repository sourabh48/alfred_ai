from django.contrib import admin
from .models import CareerJobAnalysis, CareerProfile, CareerResume, CareerResumeLearningMemory

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
    list_display = ("user", "job_title", "company", "fit_score", "market_risk_score", "created_at")
    search_fields = ("job_title", "company", "job_url")


@admin.register(CareerResumeLearningMemory)
class CareerResumeLearningMemoryAdmin(admin.ModelAdmin):
    list_display = ("user", "file_extension", "role_hint", "successful_count", "review_count", "failed_count", "average_confidence", "last_seen_at")
    search_fields = ("user__username", "file_extension", "role_hint", "skill_signature")
