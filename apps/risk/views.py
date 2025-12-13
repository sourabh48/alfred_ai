from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import RiskSignal
from .serializers import RiskSignalSerializer

class RiskSignalListCreateView(ListCreateAPIView):
    serializer_class = RiskSignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RiskSignal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
