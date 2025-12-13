from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from .models import RelationshipProfile
from .serializers import RelationshipProfileSerializer

class RelationshipListCreateView(ListCreateAPIView):
    serializer_class = RelationshipProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RelationshipDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = RelationshipProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipProfile.objects.filter(user=self.request.user)
