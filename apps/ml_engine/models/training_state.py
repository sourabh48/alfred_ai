from django.db import models
from django.utils import timezone


class AdaptiveModelState(models.Model):
    STATUS_CHOICES = [
        ("idle", "Idle"),
        ("training", "Training"),
        ("ready", "Ready"),
        ("skipped", "Skipped"),
        ("failed", "Failed"),
    ]

    model_key = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idle")
    last_trigger = models.CharField(max_length=32, blank=True)
    sample_count = models.PositiveIntegerField(default=0)
    quality_score = models.FloatField(default=0)
    confidence_estimate = models.FloatField(default=0)
    artifact_path = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    freshness_hours = models.PositiveIntegerField(default=24)
    last_started_at = models.DateTimeField(null=True, blank=True)
    last_finished_at = models.DateTimeField(null=True, blank=True)
    next_refresh_due_at = models.DateTimeField(null=True, blank=True)
    success_count = models.PositiveIntegerField(default=0)
    failure_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_name", "model_key"]

    def __str__(self):
        return f"{self.display_name} [{self.status}]"

    @property
    def is_fresh(self) -> bool:
        if self.status != "ready":
            return False
        if self.next_refresh_due_at is None:
            return False
        return timezone.now() < self.next_refresh_due_at

    @property
    def inference_ready(self) -> bool:
        from apps.ml_engine.training.quality import resolve_artifact_path, validation_blockers

        return bool(
            self.is_fresh
            and self.artifact_path
            and resolve_artifact_path(self.artifact_path).is_file()
            and not validation_blockers(self.model_key, self.sample_count, self.quality_score, self.confidence_estimate)
        )


class AdaptiveTrainingRun(models.Model):
    STATUS_CHOICES = AdaptiveModelState.STATUS_CHOICES

    model_key = models.CharField(max_length=64)
    display_name = models.CharField(max_length=120)
    trigger = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="idle")
    sample_count = models.PositiveIntegerField(default=0)
    quality_score = models.FloatField(default=0)
    confidence_estimate = models.FloatField(default=0)
    duration_ms = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["model_key", "started_at"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self):
        return f"{self.display_name} | {self.trigger or 'manual'} | {self.status}"
