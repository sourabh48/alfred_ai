from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import BehavioralSignal
from .serializers import BehavioralSignalSerializer

class BehavioralSignalListCreateView(ListCreateAPIView):
    serializer_class = BehavioralSignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BehavioralSignal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
