from django.contrib import admin

from .models import CreditScore, CreditScoreFactor, EmailConnection, VerifiedExternalInsight


admin.site.register(CreditScore)
admin.site.register(CreditScoreFactor)
admin.site.register(VerifiedExternalInsight)


@admin.register(EmailConnection)
class EmailConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "email_address",
        "provider",
        "is_connected",
        "auto_import_enabled",
        "token_storage_status",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at", "token_storage_status")
    exclude = ("access_token", "refresh_token")

    @admin.display(description="Token storage")
    def token_storage_status(self, obj):
        if not obj:
            return "No tokens"
        if obj.access_token or obj.refresh_token:
            return "Encrypted"
        return "No tokens"
