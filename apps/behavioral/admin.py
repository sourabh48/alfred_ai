from django.contrib import admin
from .models import BehavioralSignal

@admin.register(BehavioralSignal)
class BehavioralSignalAdmin(admin.ModelAdmin):
    list_display = ("user", "stress_score", "sleep_hours", "work_hours", "timestamp")
    date_hierarchy = "timestamp"
