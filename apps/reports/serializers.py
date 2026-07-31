from rest_framework import serializers
from .models import ChatGPTImport, GeneratedReport, SystemTicket

class GeneratedReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedReport
        fields = "__all__"
        read_only_fields = ["user"]


class ChatGPTImportSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=180)
    source_label = serializers.CharField(required=False, allow_blank=True, max_length=120)
    import_type_label = serializers.CharField(source="get_import_type_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    raw_text = serializers.CharField(write_only=True, trim_whitespace=False)
    preview = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    detected_modules = serializers.SerializerMethodField()

    class Meta:
        model = ChatGPTImport
        fields = (
            "id",
            "user",
            "username",
            "title",
            "import_type",
            "import_type_label",
            "source_label",
            "raw_text",
            "preview",
            "summary",
            "detected_modules",
            "parsed_payload",
            "content_hash",
            "status",
            "status_label",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "parsed_payload",
            "content_hash",
            "status",
            "created_at",
            "updated_at",
        )

    def get_preview(self, obj):
        return (obj.parsed_payload or {}).get("preview", "")

    def get_summary(self, obj):
        return (obj.parsed_payload or {}).get("summary", "")

    def get_detected_modules(self, obj):
        return (obj.parsed_payload or {}).get("detected_modules", [])

    def validate_raw_text(self, value):
        if not str(value or "").strip():
            raise serializers.ValidationError("Paste a ChatGPT dashboard, transcript, or exported conversation JSON first.")
        return value


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
