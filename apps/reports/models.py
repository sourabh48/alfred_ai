from django.db import models
from django.conf import settings


class GeneratedReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class ChatGPTImport(models.Model):
    IMPORT_TYPE_CHOICES = [
        ("chat_transcript", "Chat Transcript"),
        ("dashboard_export", "Dashboard Export"),
        ("mixed_context", "Mixed Context"),
    ]

    STATUS_CHOICES = [
        ("review_ready", "Review Ready"),
        ("mapped", "Mapped"),
        ("archived", "Archived"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chatgpt_imports")
    title = models.CharField(max_length=180)
    import_type = models.CharField(max_length=30, choices=IMPORT_TYPE_CHOICES, default="chat_transcript")
    source_label = models.CharField(max_length=120, default="ChatGPT", blank=True)
    raw_text = models.TextField()
    parsed_payload = models.JSONField(default=dict, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="review_ready")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "status", "created_at"]),
            models.Index(fields=["user", "content_hash"]),
            models.Index(fields=["import_type", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.source_label or 'ChatGPT'} | {self.title}"


class SystemTicket(models.Model):
    MODULE_CHOICES = [
        ("expenses", "Expenses"),
        ("loans", "Loans"),
        ("career", "Career"),
        ("mobility", "Mobility"),
        ("risk", "Risk"),
        ("behavioral", "Behavioral"),
        ("reports", "Reports"),
        ("general", "General"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("triaged", "Triaged"),
        ("resolved", "Resolved"),
    ]

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    HANDLER_CHOICES = [
        ("alfred", "ALFRED"),
        ("developer", "Developer"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="system_tickets")
    module = models.CharField(max_length=30, choices=MODULE_CHOICES, default="general")
    title = models.CharField(max_length=180)
    summary = models.TextField()
    context_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    handled_by = models.CharField(max_length=20, choices=HANDLER_CHOICES, default="developer")
    resolution_summary = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["module", "status", "created_at"]),
            models.Index(fields=["severity", "handled_by", "status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.module} | {self.title}"


class OperationalLog(models.Model):
    CATEGORY_CHOICES = [
        ("document", "Document Processing"),
        ("visualization", "Visualization"),
        ("api", "API"),
        ("background", "Background Job"),
    ]

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="operational_logs")
    module = models.CharField(max_length=30, default="general")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="document")
    scope = models.CharField(max_length=50, blank=True)
    event_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="info")
    document_id = models.PositiveIntegerField(null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "module", "created_at"]),
            models.Index(fields=["user", "scope", "created_at"]),
            models.Index(fields=["user", "severity", "created_at"]),
            models.Index(fields=["category", "created_at"]),
        ]

    def __str__(self):
        return f"{self.module} | {self.event_type} | {self.severity}"
