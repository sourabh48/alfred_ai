from __future__ import annotations

import hashlib
import hmac
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Dependent, FamilyAccountLink


CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_PREFIX = "ALF"
CODE_GROUP_LENGTHS = (4, 4)


def normalize_family_link_code(value: str) -> str:
    compact = "".join(char for char in str(value or "").upper() if char in string.ascii_uppercase + string.digits)
    if compact.startswith(CODE_PREFIX):
        compact = compact[len(CODE_PREFIX):]
    groups = []
    cursor = 0
    for length in CODE_GROUP_LENGTHS:
        groups.append(compact[cursor:cursor + length])
        cursor += length
    if any(len(group) != length for group, length in zip(groups, CODE_GROUP_LENGTHS)):
        raise ValidationError("Enter a complete family link code.")
    return "-".join([CODE_PREFIX, *groups])


def hash_family_link_code(value: str) -> str:
    normalized = normalize_family_link_code(value)
    return hmac.new(
        str(settings.SECRET_KEY).encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_family_link_code() -> str:
    groups = [
        "".join(secrets.choice(CODE_ALPHABET) for _ in range(length))
        for length in CODE_GROUP_LENGTHS
    ]
    return "-".join([CODE_PREFIX, *groups])


def create_family_link_invite(user):
    ttl_hours = max(1, int(getattr(settings, "ALFRED_FAMILY_LINK_CODE_TTL_HOURS", 24) or 24))
    expires_at = timezone.now() + timedelta(hours=ttl_hours)
    for _attempt in range(12):
        code = generate_family_link_code()
        digest = hash_family_link_code(code)
        if FamilyAccountLink.objects.filter(invite_code_hash=digest).exists():
            continue
        link = FamilyAccountLink.objects.create(
            created_by=user,
            invite_code_hash=digest,
            invite_code_hint=code[-4:],
            expires_at=expires_at,
        )
        return link, code
    raise RuntimeError("Could not generate a unique family link code.")


def accept_family_link_code(user, code: str) -> FamilyAccountLink:
    digest = hash_family_link_code(code)
    now = timezone.now()
    expired = False
    with transaction.atomic():
        try:
            link = FamilyAccountLink.objects.select_for_update().get(invite_code_hash=digest)
        except FamilyAccountLink.DoesNotExist as exc:
            raise ValidationError("Family link code was not found.") from exc

        if link.created_by_id == user.id:
            raise ValidationError("A family link code must be accepted by a different signed-in user.")
        if link.status != FamilyAccountLink.STATUS_PENDING:
            raise ValidationError("Family link code is no longer pending.")
        if link.expires_at <= now:
            link.status = FamilyAccountLink.STATUS_EXPIRED
            link.save(update_fields=["status", "updated_at"])
            expired = True
        else:
            if _accepted_link_between_users(user.id, link.created_by_id).exists():
                raise ValidationError("These accounts are already linked.")

            link.linked_user = user
            link.status = FamilyAccountLink.STATUS_ACCEPTED
            link.accepted_at = now
            link.save(update_fields=["linked_user", "status", "accepted_at", "updated_at"])

    if expired:
        raise ValidationError("Family link code has expired.")
    return link


def revoke_family_link(user, link_id: int) -> FamilyAccountLink:
    with transaction.atomic():
        try:
            link = FamilyAccountLink.objects.select_for_update().get(
                Q(created_by=user) | Q(linked_user=user),
                id=link_id,
            )
        except FamilyAccountLink.DoesNotExist as exc:
            raise ValidationError("Family link was not found.") from exc

        if link.status in {FamilyAccountLink.STATUS_REVOKED, FamilyAccountLink.STATUS_EXPIRED}:
            return link

        link.status = FamilyAccountLink.STATUS_REVOKED
        link.revoked_at = timezone.now()
        link.save(update_fields=["status", "revoked_at", "updated_at"])
        return link


def expire_pending_family_links() -> int:
    return FamilyAccountLink.objects.filter(
        status=FamilyAccountLink.STATUS_PENDING,
        expires_at__lte=timezone.now(),
    ).update(status=FamilyAccountLink.STATUS_EXPIRED, updated_at=timezone.now())


def family_context_user_ids(user) -> list[int]:
    user_ids = {user.id}
    for link in accepted_family_links_for_user(user).select_related("created_by", "linked_user"):
        other_user_id = link.linked_user_id if link.created_by_id == user.id else link.created_by_id
        if other_user_id and link.share_dependents:
            user_ids.add(other_user_id)
    return sorted(user_ids)


def family_financial_user_ids(user) -> list[int]:
    user_ids = {user.id}
    for link in accepted_family_links_for_user(user).select_related("created_by", "linked_user"):
        other_user_id = link.linked_user_id if link.created_by_id == user.id else link.created_by_id
        if other_user_id and link.share_financial_summary:
            user_ids.add(other_user_id)
    return sorted(user_ids)


def accepted_family_links_for_user(user):
    return FamilyAccountLink.objects.filter(
        Q(created_by=user) | Q(linked_user=user),
        status=FamilyAccountLink.STATUS_ACCEPTED,
    )


def build_family_link_snapshot(user) -> dict:
    expire_pending_family_links()
    links = (
        FamilyAccountLink.objects.filter(Q(created_by=user) | Q(linked_user=user))
        .select_related("created_by", "linked_user")
        .order_by("-updated_at", "-id")
    )
    rows = [_serialize_family_link(user, link) for link in links]
    accepted_rows = [row for row in rows if row["status"] == FamilyAccountLink.STATUS_ACCEPTED]
    linked_user_ids = {row["linked_user_id"] for row in accepted_rows if row.get("linked_user_id")}
    dependent_count = Dependent.objects.filter(user_id__in=family_context_user_ids(user)).count()
    own_dependent_count = Dependent.objects.filter(user=user).count()
    return {
        "links": rows,
        "accepted_link_count": len(accepted_rows),
        "pending_invite_count": sum(1 for row in rows if row["status"] == FamilyAccountLink.STATUS_PENDING),
        "linked_user_count": len(linked_user_ids),
        "own_dependent_count": own_dependent_count,
        "shared_dependent_count": max(0, dependent_count - own_dependent_count),
        "family_context_user_count": len(family_context_user_ids(user)),
        "family_financial_user_count": len(family_financial_user_ids(user)),
    }


def _accepted_link_between_users(user_id: int, other_user_id: int):
    return FamilyAccountLink.objects.filter(
        (
            Q(created_by_id=user_id, linked_user_id=other_user_id)
            | Q(created_by_id=other_user_id, linked_user_id=user_id)
        ),
        status=FamilyAccountLink.STATUS_ACCEPTED,
    )


def _serialize_family_link(user, link: FamilyAccountLink) -> dict:
    is_creator = link.created_by_id == user.id
    other_user = link.linked_user if is_creator else link.created_by
    linked_user = other_user if link.status == FamilyAccountLink.STATUS_ACCEPTED else None
    return {
        "id": link.id,
        "status": link.status,
        "role": "owner" if is_creator else "member",
        "invite_code_hint": link.invite_code_hint,
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "accepted_at": link.accepted_at.isoformat() if link.accepted_at else None,
        "revoked_at": link.revoked_at.isoformat() if link.revoked_at else None,
        "share_profile_summary": link.share_profile_summary,
        "share_dependents": link.share_dependents,
        "share_financial_summary": link.share_financial_summary,
        "linked_user_id": linked_user.id if linked_user else None,
        "linked_profile": _safe_user_summary(linked_user) if linked_user and link.share_profile_summary else None,
    }


def _safe_user_summary(user) -> dict | None:
    if not user:
        return None
    full_name = f"{user.first_name} {user.last_name}".strip()
    return {
        "id": user.id,
        "username": user.username,
        "display_name": full_name or user.username,
        "city": user.city,
        "country": user.country,
        "dependent_count": Dependent.objects.filter(user=user).count(),
    }
