from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from .models import GeneratedReport, SystemTicket
from .serializers import GeneratedReportSerializer, SystemTicketSerializer
from .services import reporting_service

class ReportListView(ListAPIView):
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GeneratedReport.objects.filter(user=self.request.user).order_by("-created_at")


class SystemTicketListCreateView(ListCreateAPIView):
    serializer_class = SystemTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = SystemTicket.objects.all().order_by("-created_at", "-id")
        if self.request.user.is_superuser:
            return queryset
        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = reporting_service.create_system_ticket(
            user=request.user,
            module=serializer.validated_data["module"],
            title=serializer.validated_data["title"],
            summary=serializer.validated_data["summary"],
            context_payload=serializer.validated_data.get("context_payload") or {},
        )
        detail = (
            "ALFRED auto-handled the issue and recorded the resolution."
            if ticket.handled_by == "alfred"
            else "High-severity issue escalated to the developer queue."
        )
        return Response(
            {
                "detail": detail,
                "ticket_id": ticket.id,
                "status": ticket.status,
                "severity": ticket.severity,
                "handled_by": ticket.handled_by,
                "resolution_summary": ticket.resolution_summary,
                "internal_clock": ticket.context_payload.get("internal_clock", {}),
            },
            status=status.HTTP_201_CREATED,
        )


class SystemTicketDetailView(RetrieveUpdateAPIView):
    serializer_class = SystemTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not self.request.user.is_superuser:
            return SystemTicket.objects.none()
        return SystemTicket.objects.all()

    def perform_update(self, serializer):
        ticket = serializer.save()
        if ticket.status == "resolved" and ticket.resolved_at is None:
            ticket.resolved_at = timezone.now()
            ticket.save(update_fields=["resolved_at"])
