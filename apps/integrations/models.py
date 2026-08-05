"""
Models for Integration module - Credit Scores, Email Connections, etc.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.db import models
from django.conf import settings
from django.utils import timezone


TOKEN_PREFIX = "enc::"


def _email_token_cipher() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_token(value: str | None) -> str | None:
    if not value:
        return value
    if value.startswith(TOKEN_PREFIX):
        return value
    encrypted = _email_token_cipher().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{TOKEN_PREFIX}{encrypted}"


def _decrypt_token(value: str | None) -> str:
    if not value:
        return ""
    if not value.startswith(TOKEN_PREFIX):
        return value
    try:
        encrypted = value[len(TOKEN_PREFIX):].encode("utf-8")
        return _email_token_cipher().decrypt(encrypted).decode("utf-8")
    except InvalidToken:
        return ""


class CreditScore(models.Model):
    """Store credit scores from various bureaus."""

    BUREAU_CHOICES = [
        ('CIBIL', 'TransUnion CIBIL'),
        ('EXPERIAN', 'Experian'),
        ('EQUIFAX', 'Equifax'),
        ('CRIF', 'CRIF High Mark'),
    ]
    SCORE_KIND_CHOICES = [
        ("estimated", "Estimated From Alfred Data"),
        ("official", "Official Bureau Pull"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='credit_scores')
    bureau = models.CharField(max_length=20, choices=BUREAU_CHOICES)
    score_kind = models.CharField(max_length=20, choices=SCORE_KIND_CHOICES, default="estimated")
    score = models.IntegerField()
    score_range_min = models.IntegerField(default=300)
    score_range_max = models.IntegerField(default=900)

    # Rating
    rating = models.CharField(max_length=20)  # Excellent, Good, Fair, Poor

    # Report details
    total_accounts = models.IntegerField(default=0)
    active_accounts = models.IntegerField(default=0)
    closed_accounts = models.IntegerField(default=0)
    delinquent_accounts = models.IntegerField(default=0)
    total_credit_limit = models.FloatField(default=0)
    credit_utilization = models.FloatField(default=0)  # Percentage

    # Timestamps
    fetched_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateTimeField()  # Score valid for 30 days

    # Metadata
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['user', 'bureau', '-fetched_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.bureau} - {self.score}"

    @property
    def is_valid(self):
        """Check if score is still valid (within 30 days)."""
        return timezone.now() < self.valid_until

    @property
    def days_until_refresh(self):
        """Days until score can be refreshed."""
        if not self.is_valid:
            return 0
        delta = self.valid_until - timezone.now()
        return delta.days


class CreditScoreFactor(models.Model):
    """Breakdown of factors affecting credit score."""

    credit_score = models.ForeignKey(CreditScore, on_delete=models.CASCADE, related_name='factors')

    factor_name = models.CharField(max_length=50)  # payment_history, credit_utilization, etc.
    weight = models.IntegerField()  # Percentage weight (e.g., 35 for payment history)
    score = models.FloatField()  # Score out of 100 for this factor
    status = models.CharField(max_length=20)  # Good, Fair, Poor

    class Meta:
        ordering = ['-weight']

    def __str__(self):
        return f"{self.factor_name} - {self.score}/100"


class CreditReportUpload(models.Model):
    """Store uploaded bureau report documents and their parsed results."""

    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="credit_report_uploads")
    uploaded_file = models.FileField(upload_to="credit_reports/%Y/%m/")
    file_name = models.CharField(max_length=255)
    bureau = models.CharField(max_length=20, choices=CreditScore.BUREAU_CHOICES, blank=True)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    extracted_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    parser_notes = models.TextField(blank=True)
    applicant_name = models.CharField(max_length=180, blank=True)
    report_number = models.CharField(max_length=120, blank=True)
    report_date = models.DateField(null=True, blank=True)
    parsed_credit_score = models.OneToOneField(
        "CreditScore",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_upload",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "bureau", "created_at"]),
            models.Index(fields=["user", "parser_status", "created_at"]),
        ]

    def __str__(self):
        bureau = self.bureau or "Unknown bureau"
        return f"{self.user.username} | {bureau} | {self.file_name}"


class EmailConnection(models.Model):
    """Store email connection details for automatic imports."""

    PROVIDER_CHOICES = [
        ('GMAIL', 'Gmail'),
        ('OUTLOOK', 'Outlook / Microsoft 365'),
        ('IMAP', 'Generic IMAP'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_connections')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    email_address = models.EmailField()

    # Connection status
    is_connected = models.BooleanField(default=False)
    last_synced = models.DateTimeField(null=True, blank=True)

    # Settings
    auto_import_enabled = models.BooleanField(default=True)
    sync_frequency_days = models.IntegerField(default=7)  # Sync every N days

    # OAuth tokens are encrypted at rest before save.
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'email_address']

    def __str__(self):
        return f"{self.user.username} - {self.email_address} ({self.provider})"

    def save(self, *args, **kwargs):
        self.access_token = _encrypt_token(self.access_token)
        self.refresh_token = _encrypt_token(self.refresh_token)
        super().save(*args, **kwargs)

    def get_access_token(self) -> str:
        return _decrypt_token(self.access_token)

    def get_refresh_token(self) -> str:
        return _decrypt_token(self.refresh_token)

    def set_access_token(self, value: str | None) -> None:
        self.access_token = _encrypt_token(value)

    def set_refresh_token(self, value: str | None) -> None:
        self.refresh_token = _encrypt_token(value)

    def clear_tokens(self) -> None:
        self.access_token = ""
        self.refresh_token = ""
        self.token_expires_at = None


class VerifiedExternalInsight(models.Model):
    """Cached, source-backed external intelligence with freshness tracking."""

    STATUS_CHOICES = [
        ("fresh", "Fresh"),
        ("stale", "Stale"),
        ("failed", "Failed"),
        ("rejected", "Rejected"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="verified_external_insights",
        null=True,
        blank=True,
    )
    scope = models.CharField(max_length=40)
    cache_key = models.CharField(max_length=160)
    title = models.CharField(max_length=180)
    source_name = models.CharField(max_length=180)
    source_url = models.URLField()
    query = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    checksum = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="fresh")
    fetched_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(default=timezone.now)
    stale_after = models.DateTimeField()
    last_refresh_attempt_at = models.DateTimeField(null=True, blank=True)
    last_refresh_success_at = models.DateTimeField(null=True, blank=True)
    last_refresh_status = models.CharField(max_length=32, blank=True)
    last_refresh_error = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-verified_at", "-id"]
        indexes = [
            models.Index(fields=["scope", "cache_key", "status"]),
            models.Index(fields=["user", "scope", "cache_key"]),
            models.Index(fields=["stale_after", "status"]),
            models.Index(fields=["last_refresh_attempt_at", "last_refresh_status"], name="integration_last_re_8c70a1_idx"),
        ]

    def __str__(self):
        return f"{self.scope}:{self.cache_key} [{self.source_name}]"

    @property
    def is_fresh(self):
        return self.status == "fresh" and timezone.now() <= self.stale_after
