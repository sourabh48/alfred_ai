"""Account-scoped, atomic invitation limits for the local/LAN runtime."""
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from diskcache import Cache
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle

from alfred_ai.services.api_errors import safe_error_response


class InvitationProtectionUnavailable(APIException):
    status_code = 503
    default_detail = "Invitation protection is temporarily unavailable. Please try again."


def reserve_invitation_attempt(user_id, scope, limit, window_seconds):
    """Return a retry delay, or atomically reserve one rolling-window attempt."""
    if limit < 1 or window_seconds < 1:
        raise ValueError("Invitation limits must be positive")
    directory = settings.ALFRED_FAMILY_INVITE_THROTTLE_DIR
    if not directory or not Path(directory).is_absolute():
        raise ValueError("Invitation protection requires an absolute persistent directory")
    # Dedicated, non-evicting store: ordinary cache clearing cannot reset quotas.
    with Cache(directory, timeout=5,
               eviction_policy="none", cull_limit=0) as store, store.transact():
        now = timezone.now().timestamp()
        store.expire()
        key = (scope, user_id)
        history = [stamp for stamp in store.get(key, []) if stamp > now - window_seconds]
        if len(history) >= limit:
            return min(history) + window_seconds - now
        store.set(key, history + [now], expire=window_seconds)
    return 0


class FamilyInvitationThrottle(BaseThrottle):
    def allow_request(self, request, view):
        if request.method != "POST" or not request.user.is_authenticated:
            return True
        try:
            self.retry_after = reserve_invitation_attempt(
                request.user.pk, self.scope,
                getattr(settings, f"ALFRED_FAMILY_INVITE_{self.operation}_LIMIT"),
                getattr(settings, f"ALFRED_FAMILY_INVITE_{self.operation}_WINDOW_SECONDS"),
            )
        except Exception as exc:
            response = safe_error_response(exc, InvitationProtectionUnavailable.default_detail,
                logger_name=__name__, status_code=503)
            raise InvitationProtectionUnavailable(response.data) from None
        return self.retry_after == 0

    def wait(self):
        return self.retry_after


class FamilyInvitationCreateThrottle(FamilyInvitationThrottle):
    scope = "family_invite_create"
    operation = "CREATE"


class FamilyInvitationAcceptThrottle(FamilyInvitationThrottle):
    scope = "family_invite_accept"
    operation = "ACCEPT"
