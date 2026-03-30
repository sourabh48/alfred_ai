from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def relationship_alignment(request):
    """Get relationship compatibility alignment score."""
    try:
        profile = RelationshipProfile.objects.filter(user=request.user).first()
        if not profile:
            return Response({
                "alignment_score": 0,
                "compatibility": "Unknown",
                "message": "No relationship profile found. Create one to get insights."
            })

        # Simple compatibility calculation (placeholder for ML model)
        alignment_score = 75  # Default score
        compatibility = "Good"

        return Response({
            "alignment_score": alignment_score,
            "compatibility": compatibility,
            "insights": [
                "Communication patterns are healthy",
                "Financial goals are aligned",
                "Consider discussing long-term plans"
            ]
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)
