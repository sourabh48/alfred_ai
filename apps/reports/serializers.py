from rest_framework import serializers
from .models import GeneratedReport, SystemTicket

class GeneratedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedReport
        fields = "__all__"
        read_only_fields = ["user"]


class SystemTicketSerializer(serializers.ModelSerializer):
    module_label = serializers.CharField(source="get_module_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    handled_by_label = serializers.CharField(source="get_handled_by_display", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SystemTicket
        fields = (
            "id",
            "user",
            "username",
            "module",
            "module_label",
            "title",
            "summary",
            "context_payload",
            "status",
            "status_label",
            "severity",
            "severity_label",
            "handled_by",
            "handled_by_label",
            "resolution_summary",
            "resolved_at",
            "admin_note",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "created_at",
            "updated_at",
        )
