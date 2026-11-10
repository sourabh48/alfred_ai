from django.db import DatabaseError
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.assistant_actions import ActionConflict, ActionError, cancel, confirm, prepare


def _failure(error):
    if isinstance(error, DatabaseError):
        return Response({"detail": "Confirmation could not be verified. Retry this same review safely or check Budgets."}, status=503)
    return Response({"detail": str(error)}, status=409 if isinstance(error, ActionConflict) else 400)


@method_decorator(never_cache, name="dispatch")
class AssistantActionProposeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - {"text"}:
            return Response({"detail": "Supply only the action request text."}, status=400)
        try:
            return Response({"proposal": prepare(request.user, request.data.get("text"), timezone.localdate())})
        except ActionError as error:
            return Response({"proposal": None, "detail": str(error)})
        except DatabaseError as error:
            return _failure(error)


@method_decorator(never_cache, name="dispatch")
class AssistantActionConfirmAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) - {"proposal_id", "action", "fields", "confirmed", "summary", "expires_at", "revision"}:
            return Response({"detail": "Use the reviewed proposal fields."}, status=400)
        if request.data.get("confirmed") is not True:
            return Response({"detail": "Confirm the action first."}, status=400)
        try:
            result = confirm(request.user, request.data.get("proposal_id"), request.data.get("action"), request.data.get("fields"))
            return Response(result, status=200 if result["already_applied"] else 201)
        except (ActionError, DatabaseError) as error:
            return _failure(error)


@method_decorator(never_cache, name="dispatch")
class AssistantActionCancelAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not isinstance(request.data, dict) or set(request.data) != {"proposal_id"}:
            return Response({"detail": "Choose a proposal to cancel."}, status=400)
        try:
            return Response(cancel(request.user, request.data["proposal_id"]))
        except (ActionError, DatabaseError) as error:
            return _failure(error)
