from django.db import models
from django.conf import settings

class Dependent(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    relation = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.name} ({self.relation})"


class FamilyAccountLink(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REVOKED = "revoked"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REVOKED, "Revoked"),
        (STATUS_EXPIRED, "Expired"),
    ]

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_link_invites",
    )
    linked_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="family_link_acceptances",
        null=True,
        blank=True,
    )
    invite_code_hash = models.CharField(max_length=64, unique=True)
    invite_code_hint = models.CharField(max_length=16, blank=True)
    share_profile_summary = models.BooleanField(default=True)
    share_dependents = models.BooleanField(default=True)
    share_financial_summary = models.BooleanField(default=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_by", "status", "expires_at"]),
            models.Index(fields=["linked_user", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        linked = self.linked_user.username if self.linked_user_id else "pending"
        return f"{self.created_by.username} -> {linked} ({self.status})"
