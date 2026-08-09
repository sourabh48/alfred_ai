from django.contrib import admin
from .models import Dependent, FamilyAccountLink

@admin.register(Dependent)
class DependentAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "age", "relation")
    list_filter = ("relation",)


@admin.register(FamilyAccountLink)
class FamilyAccountLinkAdmin(admin.ModelAdmin):
    list_display = ("created_by", "linked_user", "status", "invite_code_hint", "expires_at", "accepted_at", "revoked_at")
    list_filter = ("status", "share_profile_summary", "share_dependents")
    search_fields = ("created_by__username", "linked_user__username", "invite_code_hint")
    readonly_fields = ("invite_code_hash", "invite_code_hint", "created_at", "updated_at", "accepted_at", "revoked_at")
