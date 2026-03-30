from django.contrib import admin
from .models import GeneratedReport, SystemTicket

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("user", "file_path", "created_at")


@admin.register(SystemTicket)
class SystemTicketAdmin(admin.ModelAdmin):
    list_display = ("module", "title", "user", "status", "created_at")
    list_filter = ("module", "status")
    search_fields = ("title", "summary", "user__username")
