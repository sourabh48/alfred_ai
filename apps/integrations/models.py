"""
Models for Integration module - Email Connections and verified external insights.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.db import models
from django.conf import settings
from django.utils import timezone


TOKEN_PREFIX = "enc::"


def _email_token_cipher(*, include_fallbacks=True) -> MultiFernet:
    keys = [settings.SECRET_KEY]
    if include_fallbacks:
        keys.extend(getattr(settings, "SECRET_KEY_FALLBACKS", []))
    return MultiFernet([
        Fernet(base64.urlsafe_b64encode(hashlib.sha256(key.encode("utf-8")).digest()))
        for key in keys
    ])


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
