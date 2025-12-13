from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .models import CareerProfile
from .serializers import CareerProfileSerializer

class CareerProfileView(RetrieveUpdateAPIView):
    serializer_class = CareerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return CareerProfile.objects.get(user=self.request.user)
