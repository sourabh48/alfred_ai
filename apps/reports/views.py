from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from .models import GeneratedReport
from .serializers import GeneratedReportSerializer

class ReportListView(ListAPIView):
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedReport.objects.filter(user=self.request.user)
