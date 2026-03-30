from django.db import models
from django.conf import settings


class CareerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=100)
    experience_years = models.FloatField()
    skills = models.TextField()
    last_salary = models.FloatField(default=0)

    def __str__(self):
        return self.role


class CareerResume(models.Model):
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_resumes")
    uploaded_file = models.FileField(upload_to="career_resumes/%Y/%m/")
    file_name = models.CharField(max_length=255)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    extracted_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    weaknesses = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.file_name}"


class CareerResumeLearningMemory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_resume_learning_memories")
    file_extension = models.CharField(max_length=16)
    role_hint = models.CharField(max_length=100, blank=True)
    skill_signature = models.CharField(max_length=240, blank=True)
    successful_count = models.PositiveIntegerField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    average_confidence = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_seen_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "file_extension", "role_hint", "skill_signature"],
                name="career_resume_learning_memory_unique_key",
            )
        ]
        indexes = [
            models.Index(fields=["user", "file_extension"]),
            models.Index(fields=["user", "role_hint"]),
        ]

    def __str__(self):
        return f"{self.user.username} | {self.file_extension} | {self.role_hint or 'unknown'}"


class CareerJobAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="career_job_analyses")
    source_name = models.CharField(max_length=120, blank=True)
    job_url = models.URLField()
    apply_url = models.URLField(blank=True)
    company = models.CharField(max_length=180, blank=True)
    job_title = models.CharField(max_length=180, blank=True)
    location = models.CharField(max_length=180, blank=True)
    fit_score = models.FloatField(default=0)
    market_risk_score = models.FloatField(default=0)
    strengths = models.TextField(blank=True)
    gaps = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    evidence = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "company", "created_at"]),
        ]

    def __str__(self):
        return self.job_title or self.job_url
