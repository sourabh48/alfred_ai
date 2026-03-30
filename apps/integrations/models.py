"""
Models for Integration module - Credit Scores, Email Connections, etc.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


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

    # OAuth tokens (encrypted in production)
    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'email_address']

    def __str__(self):
        return f"{self.user.username} - {self.email_address} ({self.provider})"


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
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-verified_at", "-id"]
        indexes = [
            models.Index(fields=["scope", "cache_key", "status"]),
            models.Index(fields=["user", "scope", "cache_key"]),
            models.Index(fields=["stale_after", "status"]),
        ]

    def __str__(self):
        return f"{self.scope}:{self.cache_key} [{self.source_name}]"

    @property
    def is_fresh(self):
        return self.status == "fresh" and timezone.now() <= self.stale_after
