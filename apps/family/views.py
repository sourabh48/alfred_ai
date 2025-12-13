from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from .models import Dependent
from .serializers import DependentSerializer

class DependentListCreateView(ListCreateAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class DependentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = DependentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dependent.objects.filter(user=self.request.user)
