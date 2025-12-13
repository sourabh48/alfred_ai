from django.contrib import admin
from .models import GeneratedReport

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("user", "file_path", "created_at")
