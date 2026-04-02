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


class UserDataResetView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        deleted = clear_user_fed_data(request.user)
        serializer = UserSerializer(request.user)
        return Response(
            {
                "detail": "Your Alfred data, uploaded documents, and cached dashboard payloads have been cleared. Your account stays active, and you can start fresh with new data.",
                "deleted": deleted,
                "profile": serializer.data,
            }
        )
