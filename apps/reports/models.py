from django.db import models
from django.conf import settings


class GeneratedReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_path = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


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
