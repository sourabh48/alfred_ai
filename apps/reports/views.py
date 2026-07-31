from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from alfred_ai.pagination import OptionalPageNumberPagination
from .models import ChatGPTImport, GeneratedReport, SystemTicket
from .serializers import ChatGPTImportSerializer, GeneratedReportSerializer, SystemTicketSerializer
from .services import chatgpt_import_service, reporting_service

class ReportListView(ListAPIView):
    serializer_class = GeneratedReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return GeneratedReport.objects.filter(user=self.request.user).order_by("-created_at")


class ChatGPTImportListCreateView(ListCreateAPIView):
    serializer_class = ChatGPTImportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return ChatGPTImport.objects.filter(user=self.request.user).order_by("-created_at", "-id")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payload = chatgpt_import_service.build_payload(
                raw_text=serializer.validated_data["raw_text"],
                title=serializer.validated_data.get("title") or "",
                import_type=serializer.validated_data.get("import_type") or "chat_transcript",
            )
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_400_BAD_REQUEST)

        import_record = ChatGPTImport.objects.create(
            user=request.user,
            title=payload["title"],
            import_type=payload["import_type"],
            source_label=(serializer.validated_data.get("source_label") or "ChatGPT")[:120],
            raw_text=serializer.validated_data["raw_text"].strip(),
            parsed_payload=payload["parsed_payload"],
            content_hash=payload["content_hash"],
        )
        return Response(self.get_serializer(import_record).data, status=status.HTTP_201_CREATED)


class SystemTicketListCreateView(ListCreateAPIView):
    serializer_class = SystemTicketSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

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
