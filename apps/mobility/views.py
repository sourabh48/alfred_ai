from datetime import timedelta
from datetime import date as date_cls

from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord, TravelPlan, TripLog, TripPhoto
from .serializers import (
    BikeConditionSnapshotSerializer,
    BikeDocumentSerializer,
    BikeIssueReportSerializer,
    BikeProfileSerializer,
    BikeServiceRecordSerializer,
    TravelPlanSerializer,
    TripLogSerializer,
    TripPhotoSerializer,
)
from .services import bike_document_ai, bike_service_intelligence, build_profile_payload, list_catalog_models, travel_advisor


def _apply_profile_payload(profile, payload):
    for field, value in payload.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    profile.save()
    return profile


def _resolve_bike_profile(user, profile_id):
    if not profile_id:
        return None
    return BikeProfile.objects.filter(user=user, pk=profile_id).first()


def _parse_optional_date(value):
    if not value:
        return None
    if isinstance(value, date_cls):
        return value
    try:
        return date_cls.fromisoformat(str(value))
    except ValueError:
        return None


class BikeModelCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"results": list_catalog_models()})


class BikeProfileListCreateView(ListCreateAPIView):
    serializer_class = BikeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        profile = serializer.save(user=self.request.user)
        payload = build_profile_payload(profile.display_name or profile.model_name, profile.vehicle_number, profile.variant, profile.make)
        payload["vehicle_type"] = profile.vehicle_type or payload.get("vehicle_type", "motorcycle")
        payload["is_primary"] = profile.is_primary or not BikeProfile.objects.filter(user=self.request.user).exclude(pk=profile.pk).exists()
        if payload["is_primary"]:
            BikeProfile.objects.filter(user=self.request.user).exclude(pk=profile.pk).update(is_primary=False)
        _apply_profile_payload(profile, payload)


class BikeProfileDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeProfile.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        profile = serializer.save()
        payload = build_profile_payload(profile.display_name or profile.model_name, profile.vehicle_number, profile.variant, profile.make)
        payload["vehicle_type"] = profile.vehicle_type or payload.get("vehicle_type", "motorcycle")
        payload["is_primary"] = profile.is_primary
        if payload["is_primary"]:
            BikeProfile.objects.filter(user=self.request.user).exclude(pk=profile.pk).update(is_primary=False)
        _apply_profile_payload(profile, payload)


class BikeServiceRecordListCreateView(ListCreateAPIView):
    serializer_class = BikeServiceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeServiceRecord.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        serializer.save(
            user=self.request.user,
            bike_name=serializer.validated_data.get("bike_name") or (bike_profile.display_name if bike_profile else ""),
            vehicle_number=serializer.validated_data.get("vehicle_number") or (bike_profile.vehicle_number if bike_profile else ""),
        )


class BikeServiceRecordDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeServiceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeServiceRecord.objects.filter(user=self.request.user).select_related("bike_profile")


class BikeIssueReportListCreateView(ListCreateAPIView):
    serializer_class = BikeIssueReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeIssueReport.objects.filter(user=self.request.user).select_related("bike_profile", "bike_service", "travel_plan")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        bike_service = serializer.validated_data.get("bike_service")
        issue = serializer.save(
            user=self.request.user,
            bike_profile=bike_profile or getattr(bike_service, "bike_profile", None),
        )
        bike_service_intelligence.hydrate_issue(issue)


class BikeIssueReportDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeIssueReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeIssueReport.objects.filter(user=self.request.user).select_related("bike_profile", "bike_service", "travel_plan")

    def perform_update(self, serializer):
        issue = serializer.save()
        bike_service_intelligence.hydrate_issue(issue)


class BikeDocumentListCreateView(ListCreateAPIView):
    serializer_class = BikeDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return BikeDocument.objects.filter(user=self.request.user).select_related("bike_profile").order_by("expiry_date", "-id")

    def perform_create(self, serializer):
        document = serializer.save(user=self.request.user)
        bike_service_intelligence.hydrate_document(document)


class BikeDocumentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return BikeDocument.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_update(self, serializer):
        document = serializer.save()
        bike_service_intelligence.hydrate_document(document)


class BikeDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        bike_profile = _resolve_bike_profile(request.user, request.data.get("bike_profile_id") or request.data.get("vehicle_profile_id"))
        if bike_profile is None:
            return Response({"detail": "Select a vehicle profile before uploading a document."}, status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES.get("document_file")
        if upload is None:
            return Response({"detail": "Upload a document file."}, status=status.HTTP_400_BAD_REQUEST)

        parsed = bike_document_ai.parse(upload, upload.name)
        upload.seek(0)
        document_type = request.data.get("document_type_override") or parsed.document_type
        relevance = bike_document_ai.verify_relevance(bike_profile, parsed, document_type)
        if not relevance["accepted"]:
            return Response(
                {
                    "detail": "The uploaded file does not look related to the selected vehicle profile.",
                    "reasons": relevance["reasons"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        amount = parsed.fields.get("amount") or 0
        document = BikeDocument.objects.create(
            user=request.user,
            bike_profile=bike_profile,
            bike_name=bike_profile.display_name,
            vehicle_number=parsed.fields.get("vehicle_number") or bike_profile.vehicle_number,
            document_type=document_type,
            issuer=parsed.fields.get("issuer", ""),
            document_number=parsed.fields.get("document_number", ""),
            issue_date=_parse_optional_date(parsed.fields.get("issue_date")),
            expiry_date=_parse_optional_date(parsed.fields.get("expiry_date")),
            premium_amount=amount if isinstance(amount, (int, float)) else 0,
            document_file=upload,
            document_title=parsed.title,
            parser_status=parsed.parser_status,
            parse_confidence=parsed.confidence,
            parser_notes=" ".join(filter(None, [parsed.parser_notes, *relevance["reasons"]])).strip(),
            source_text=parsed.source_text,
            extracted_payload={
                **parsed.fields,
                "detected_document_type": parsed.document_type,
                "service_payload": parsed.service_payload,
                "relevance_score": relevance["score"],
                "relevance_reasons": relevance["reasons"],
            },
            notes=request.data.get("notes", ""),
        )
        bike_service_intelligence.hydrate_document(document)
        return Response(BikeDocumentSerializer(document, context={"request": request}).data, status=status.HTTP_201_CREATED)


class BikeConditionSnapshotListCreateView(ListCreateAPIView):
    serializer_class = BikeConditionSnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeConditionSnapshot.objects.filter(user=self.request.user).select_related("bike_profile").order_by("-captured_at", "-id")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        snapshot = serializer.save(
            user=self.request.user,
            bike_name=serializer.validated_data.get("bike_name") or (bike_profile.display_name if bike_profile else ""),
            vehicle_number=serializer.validated_data.get("vehicle_number") or (bike_profile.vehicle_number if bike_profile else ""),
        )
        bike_service_intelligence.hydrate_condition(snapshot, self.request.user)


class BikeConditionSnapshotDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeConditionSnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeConditionSnapshot.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_update(self, serializer):
        snapshot = serializer.save()
        bike_service_intelligence.hydrate_condition(snapshot, self.request.user)


class BikeServiceImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        bike_profile = _resolve_bike_profile(request.user, request.data.get("bike_profile_id") or request.data.get("vehicle_profile_id"))
        if bike_profile is None:
            return Response({"detail": "Select a vehicle profile before importing a service bill."}, status=status.HTTP_400_BAD_REQUEST)

        upload = request.FILES.get("service_file")
        if upload is None:
            return Response({"detail": "Upload a service bill or work note."}, status=status.HTTP_400_BAD_REQUEST)

        parsed = bike_document_ai.parse(upload, upload.name)
        relevance = bike_document_ai.verify_relevance(bike_profile, parsed, "invoice")
        if not relevance["accepted"]:
            return Response(
                {
                    "detail": "The uploaded bill or work note does not look related to the selected vehicle profile.",
                    "reasons": relevance["reasons"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        service_payload = parsed.service_payload
        if not service_payload:
            return Response(
                {"detail": "The file was read, but Alfred could not confidently extract service details. Try a clearer bill or add the log manually."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload.seek(0)
        document = BikeDocument.objects.create(
            user=request.user,
            bike_profile=bike_profile,
            bike_name=bike_profile.display_name,
            vehicle_number=parsed.fields.get("vehicle_number") or bike_profile.vehicle_number,
            document_type="invoice",
            issuer=parsed.fields.get("issuer", ""),
            document_number=parsed.fields.get("document_number", ""),
            issue_date=_parse_optional_date(service_payload.get("service_date")),
            premium_amount=service_payload.get("cost") or 0,
            document_file=upload,
            document_title=parsed.title,
            parser_status=parsed.parser_status,
            parse_confidence=parsed.confidence,
            parser_notes=" ".join(filter(None, [parsed.parser_notes, *relevance["reasons"]])).strip(),
            source_text=parsed.source_text,
            extracted_payload={
                **parsed.fields,
                "detected_document_type": parsed.document_type,
                "service_payload": service_payload,
                "relevance_score": relevance["score"],
                "relevance_reasons": relevance["reasons"],
            },
            notes=request.data.get("notes", ""),
        )
        bike_service_intelligence.hydrate_document(document)

        service_record = BikeServiceRecord.objects.create(
            user=request.user,
            bike_profile=bike_profile,
            bike_name=bike_profile.display_name,
            vehicle_number=parsed.fields.get("vehicle_number") or bike_profile.vehicle_number,
            service_date=_parse_optional_date(service_payload.get("service_date")) or timezone.localdate(),
            odometer_km=service_payload.get("odometer_km") or 0,
            service_type=service_payload.get("service_type", "routine"),
            cost=service_payload.get("cost") or 0,
            service_center=service_payload.get("service_center", ""),
            next_service_date=_parse_optional_date(service_payload.get("next_service_date")),
            next_service_km=service_payload.get("next_service_km") or None,
            notes=request.data.get("notes", ""),
            source_mode="bill_import" if parsed.document_type == "invoice" else "work_note",
            source_document_name=upload.name,
            extracted_work_summary=service_payload.get("extracted_work_summary", ""),
            parsed_payload={"document_parse": parsed.fields, "service_payload": service_payload},
        )
        return Response(
            {
                "document": BikeDocumentSerializer(document, context={"request": request}).data,
                "service_record": BikeServiceRecordSerializer(service_record, context={"request": request}).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TravelPlanListCreateView(ListCreateAPIView):
    serializer_class = TravelPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TravelPlan.objects.filter(user=self.request.user).annotate(
            log_count=Count("logs", distinct=True),
            photo_count=Count("photos", distinct=True),
        ).select_related("vehicle_profile")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TravelPlanDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TravelPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TravelPlan.objects.filter(user=self.request.user).annotate(
            log_count=Count("logs", distinct=True),
            photo_count=Count("photos", distinct=True),
        ).select_related("vehicle_profile")


class TripLogListCreateView(ListCreateAPIView):
    serializer_class = TripLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TripLog.objects.filter(user=self.request.user).select_related("travel_plan", "travel_plan__vehicle_profile")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TripLogDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TripLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TripLog.objects.filter(user=self.request.user).select_related("travel_plan", "travel_plan__vehicle_profile")


class TripPhotoListCreateView(ListCreateAPIView):
    serializer_class = TripPhotoSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return TripPhoto.objects.filter(user=self.request.user).select_related("travel_plan", "travel_plan__vehicle_profile", "trip_log")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TripPhotoDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = TripPhotoSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return TripPhoto.objects.filter(user=self.request.user).select_related("travel_plan", "travel_plan__vehicle_profile", "trip_log")


class TravelAdvisorPreviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        destination = (request.data.get("destination") or "").strip()
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        budget = float(request.data.get("budget") or 0)
        transport_mode = request.data.get("transport_mode") or "ride"
        vehicle_profile = _resolve_bike_profile(request.user, request.data.get("vehicle_profile_id"))

        if not destination or not start_date or not end_date:
            return Response({"detail": "Destination, start date, and end date are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            parsed_start = date_cls.fromisoformat(start_date)
            parsed_end = date_cls.fromisoformat(end_date)
        except ValueError:
            return Response({"detail": "Use valid ISO dates for start and end date."}, status=status.HTTP_400_BAD_REQUEST)

        if parsed_end < parsed_start:
            return Response({"detail": "Trip end date cannot be earlier than the start date."}, status=status.HTTP_400_BAD_REQUEST)

        advice = travel_advisor.build_advice(request.user, destination, parsed_start, parsed_end, budget, transport_mode, vehicle_profile=vehicle_profile)
        return Response(advice)


class MobilityDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        bike_profiles = list(BikeProfile.objects.filter(user=request.user))
        travel_plans = list(
            TravelPlan.objects.filter(user=request.user)
            .annotate(log_count=Count("logs", distinct=True), photo_count=Count("photos", distinct=True))
            .select_related("vehicle_profile")
            .order_by("start_date", "-id")
        )
        trip_logs = list(TripLog.objects.filter(user=request.user).select_related("travel_plan", "travel_plan__vehicle_profile").order_by("-log_date", "-id"))
        trip_photos = list(
            TripPhoto.objects.filter(user=request.user)
            .select_related("travel_plan", "travel_plan__vehicle_profile", "trip_log")
            .order_by("-taken_at", "-id")
        )
        condition_snapshot = BikeConditionSnapshot.objects.filter(user=request.user).select_related("bike_profile").order_by("-captured_at", "-id").first()
        documents = list(BikeDocument.objects.filter(user=request.user).select_related("bike_profile").order_by("expiry_date", "-id"))
        current_documents = bike_service_intelligence.current_documents(documents)
        expiring_documents = [item for item in current_documents if item.verification_status in {"expiring_soon", "expired"}]

        active_trip_status = {"planned", "booked", "on_trip"}
        today = timezone.localdate()
        upcoming_plans = [plan for plan in travel_plans if plan.status in active_trip_status and plan.end_date >= today]
        completed_plans = [plan for plan in travel_plans if plan.status == "completed"]
        total_trip_budget = sum(plan.budget or 0 for plan in travel_plans)
        total_trip_spend = sum(log.spend_amount or 0 for log in trip_logs)
        total_trip_distance = sum(log.distance_km or 0 for log in trip_logs)

        heatmap_points = []
        for log in trip_logs:
            if log.latitude is None or log.longitude is None:
                continue
            heatmap_points.append(
                {
                    "type": "log",
                    "title": log.title,
                    "location_name": log.location_name,
                    "latitude": log.latitude,
                    "longitude": log.longitude,
                    "date": log.log_date.isoformat(),
                    "intensity": max(log.distance_km or 0, log.spend_amount or 0, 1),
                }
            )
        for photo in trip_photos:
            if photo.latitude is None or photo.longitude is None:
                continue
            heatmap_points.append(
                {
                    "type": "photo",
                    "title": photo.caption or photo.travel_plan.title,
                    "location_name": photo.location_name,
                    "latitude": photo.latitude,
                    "longitude": photo.longitude,
                    "date": (photo.taken_at.isoformat() if photo.taken_at else ""),
                    "intensity": 1,
                    "photo_url": request.build_absolute_uri(photo.image.url) if photo.image else "",
                }
            )

        return Response(
            {
                "summary": {
                    "upcoming_trips": len(upcoming_plans),
                    "completed_trips": len(completed_plans),
                    "trip_logs": len(trip_logs),
                    "photo_count": len(trip_photos),
                    "total_trip_budget": round(total_trip_budget, 2),
                    "total_trip_spend": round(total_trip_spend, 2),
                    "total_trip_distance_km": round(total_trip_distance, 1),
                    "mapped_points": len(heatmap_points),
                    "expiring_documents": len(expiring_documents),
                    "condition_score": condition_snapshot.overall_score if condition_snapshot else 0,
                    "condition_status": condition_snapshot.get_overall_status_display() if condition_snapshot else "No data",
                },
                "condition_snapshot": BikeConditionSnapshotSerializer(condition_snapshot, context={"request": request}).data if condition_snapshot else None,
                "bike_profiles": BikeProfileSerializer(bike_profiles, many=True, context={"request": request}).data,
                "travel_plans": TravelPlanSerializer(travel_plans, many=True, context={"request": request}).data,
                "trip_logs": TripLogSerializer(trip_logs[:12], many=True, context={"request": request}).data,
                "trip_photos": TripPhotoSerializer(trip_photos[:12], many=True, context={"request": request}).data,
                "heatmap_points": heatmap_points,
            }
        )


class BikeServiceDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        intelligence = bike_service_intelligence.build_dashboard(request.user)
        bike_profiles = BikeProfile.objects.filter(user=request.user)
        service_records = BikeServiceRecord.objects.filter(user=request.user).select_related("bike_profile").order_by("-service_date", "-id")[:18]
        issue_reports = BikeIssueReport.objects.filter(user=request.user).select_related("bike_profile", "bike_service", "travel_plan").order_by("-reported_at", "-id")[:12]
        travel_plans = TravelPlan.objects.filter(user=request.user).select_related("vehicle_profile").order_by("start_date", "-id")[:20]
        documents = BikeDocument.objects.filter(user=request.user).select_related("bike_profile").order_by("expiry_date", "-id")[:15]
        conditions = BikeConditionSnapshot.objects.filter(user=request.user).select_related("bike_profile").order_by("-captured_at", "-id")[:12]

        return Response(
            {
                **intelligence,
                "bike_profiles": BikeProfileSerializer(bike_profiles, many=True, context={"request": request}).data,
                "bike_catalog": list_catalog_models(),
                "bike_services": BikeServiceRecordSerializer(service_records, many=True, context={"request": request}).data,
                "bike_issues": BikeIssueReportSerializer(issue_reports, many=True, context={"request": request}).data,
                "bike_documents": BikeDocumentSerializer(documents, many=True, context={"request": request}).data,
                "bike_conditions": BikeConditionSnapshotSerializer(conditions, many=True, context={"request": request}).data,
                "travel_plans": TravelPlanSerializer(travel_plans, many=True, context={"request": request}).data,
            }
        )
