from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer
from .services import clear_user_fed_data

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserDataResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            deleted = clear_user_fed_data(request.user)
        except Exception as exc:
            from alfred_ai.services.api_errors import safe_error_response
            return safe_error_response(exc, 'Account reset could not finish. Please try again.', logger_name=__name__, status_code=503)
        serializer = UserSerializer(request.user)
        return Response(
            {
                "detail": "Your Alfred data, uploaded documents, and cached dashboard payloads have been cleared. Your account stays active, and you can start fresh with new data.",
                "deleted": deleted,
                "profile": serializer.data,
            }
        )
