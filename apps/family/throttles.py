"""Account-scoped, atomic invitation limits for the local/LAN runtime."""
from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle

from alfred_ai.services.api_errors import safe_error_response
from alfred_ai.services.throttling import reserve_attempts


class InvitationProtectionUnavailable(APIException):
    status_code = 503
    default_detail = "Invitation protection is temporarily unavailable. Please try again."


def reserve_invitation_attempt(user_id, scope, limit, window_seconds):
    """Return a retry delay, or atomically reserve one rolling-window attempt."""
    return reserve_attempts(settings.ALFRED_FAMILY_INVITE_THROTTLE_DIR,
        [((scope, user_id), limit, window_seconds)])


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
