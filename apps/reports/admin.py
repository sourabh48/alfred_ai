from django.contrib import admin
from .models import ChatGPTImport, GeneratedReport, SystemTicket

@admin.register(GeneratedReport)
class GeneratedReportAdmin(admin.ModelAdmin):
    list_display = ("user", "file_path", "created_at")


@admin.register(SystemTicket)
class SystemTicketAdmin(admin.ModelAdmin):
    list_display = ("module", "title", "user", "status", "created_at")
    list_filter = ("module", "status")
    search_fields = ("title", "summary", "user__username")


@admin.register(ChatGPTImport)
class ChatGPTImportAdmin(admin.ModelAdmin):
    list_display = ("title", "source_label", "import_type", "status", "user", "created_at")
    list_filter = ("import_type", "status", "source_label")
    search_fields = ("title", "source_label", "raw_text", "user__username")
