from django.db.models import Count, Max
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from alfred_ai.services.materialized_cache import materialize_payload
from .models import RelationshipProfile
from .serializers import RelationshipProfileSerializer
from .services.relationship_intelligence import build_relationship_alignment

class RelationshipListCreateView(ListCreateAPIView):
    serializer_class = RelationshipProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipProfile.objects.filter(user=self.request.user).order_by("-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RelationshipDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = RelationshipProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return RelationshipProfile.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relationship_alignment(request):
    """Get relationship compatibility alignment score."""
    revision_state = RelationshipProfile.objects.filter(user=request.user).aggregate(
        profile_count=Count("id"),
        latest_update=Max("updated_at"),
    )
    revision = f"profiles:{revision_state['profile_count']}:{revision_state['latest_update'].isoformat() if revision_state['latest_update'] else '0'}"
    payload = materialize_payload(
        namespace="relationship-alignment",
        user_id=request.user.id,
        revision=revision,
        ttl_seconds=30,
        builder=lambda: build_relationship_alignment(request.user).payload,
    )
    return Response(payload)
