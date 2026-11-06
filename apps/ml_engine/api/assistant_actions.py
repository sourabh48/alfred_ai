from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services.assistant_actions import ActionError, confirm, propose


class AssistantActionProposeAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            return Response({"proposal": propose(request.user, request.data.get("text"), timezone.localdate())})
        except ActionError as error:
            return Response({"proposal": None, "detail": str(error)})


class AssistantActionConfirmAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.data.get("confirmed") is not True:
            return Response({"detail": "Confirm the action first."}, status=400)
        try:
            return Response(confirm(request.user, request.data.get("action"), request.data.get("fields")), status=201)
        except ActionError as error:
            return Response({"detail": str(error)}, status=400)
