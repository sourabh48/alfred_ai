from django.conf import settings
from django.db import models


class DocumentParserLearningMemory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="document_parser_memories")
    scope = models.CharField(max_length=40)
    file_extension = models.CharField(max_length=16)
    detected_type = models.CharField(max_length=60, blank=True)
    template_signature = models.CharField(max_length=255, blank=True)
    field_signature = models.CharField(max_length=255, blank=True)
    successful_count = models.PositiveIntegerField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    correction_count = models.PositiveIntegerField(default=0)
    retry_success_count = models.PositiveIntegerField(default=0)
    retry_failure_count = models.PositiveIntegerField(default=0)
    average_confidence = models.FloatField(default=0)
    observed_fields = models.JSONField(default=list, blank=True)
    observed_keywords = models.JSONField(default=list, blank=True)
    accepted_field_hints = models.JSONField(default=list, blank=True)
    last_resolution = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "scope", "file_extension", "detected_type", "template_signature", "field_signature"],
                name="ml_engine_document_parser_learning_unique_key",
            )
        ]
        indexes = [
            models.Index(fields=["user", "scope", "file_extension"]),
            models.Index(fields=["user", "scope", "detected_type"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.scope}:{self.file_extension}:{self.detected_type or 'other'}"
