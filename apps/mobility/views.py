from datetime import timedelta
from datetime import date as date_cls

from django.db.models import Count, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.pagination import OptionalPageNumberPagination
from alfred_ai.services import record_parser_learning
from alfred_ai.services.materialized_cache import materialize_payload
from apps.reports.services import operational_logging_service
from .models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord, FuelRefillLog, TravelPlan, TripLog, TripPhoto
from .serializers import (
    BikeConditionSnapshotSerializer,
    BikeDocumentSerializer,
    BikeIssueReportSerializer,
    BikeProfileSerializer,
    BikeServiceRecordSerializer,
    FuelRefillLogSerializer,
    TravelPlanSerializer,
    TripLogSerializer,
    TripPhotoSerializer,
)
from .services import bike_document_ai, bike_service_intelligence, build_profile_payload, catalog_coverage_summary, list_catalog_manufacturers, list_catalog_models, travel_advisor
from .services import build_document_payload, build_service_record_payload, merge_nested_payload, resolve_vehicle_identity


PROFILE_MANUAL_OVERRIDE_FIELDS = {
    "vehicle_type",
    "display_name",
    "make",
    "model_name",
    "variant",
    "vehicle_number",
    "bike_class",
    "engine_cc",
    "fuel_tank_capacity_l",
    "expected_mileage_kmpl",
    "service_interval_km",
    "service_interval_days",
    "optimal_cruising_speed_kmph",
    "tyre_front_spec",
    "tyre_rear_spec",
    "fuel_type",
    "usage_pattern",
    "estimated_market_value",
    "monthly_income_support",
}


def _apply_profile_payload(profile, payload):
    for field, value in payload.items():
        if hasattr(profile, field):
            setattr(profile, field, value)
    profile.save()
    return profile


def _profile_manual_overrides(serializer):
    validated_data = getattr(serializer, "validated_data", {}) or {}
    return {
        field: validated_data[field]
        for field in PROFILE_MANUAL_OVERRIDE_FIELDS
        if field in validated_data
    }


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
        vehicle_type = str(request.query_params.get("vehicle_type", "") or "").strip().lower()
        make = (
            request.query_params.get("make")
            or request.query_params.get("brand")
            or request.query_params.get("manufacturer")
            or ""
        )
        return Response(
            {
                "results": list_catalog_models(vehicle_type=vehicle_type, make=make),
                "manufacturers": list_catalog_manufacturers(vehicle_type=vehicle_type),
                "selected_make": str(make or "").strip(),
                "coverage": catalog_coverage_summary(),
            }
        )


class BikeProfileListCreateView(ListCreateAPIView):
    serializer_class = BikeProfileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return BikeProfile.objects.filter(user=self.request.user).order_by("-is_primary", "display_name", "-id")

    def perform_create(self, serializer):
        profile = serializer.save(user=self.request.user)
        manual_overrides = _profile_manual_overrides(serializer)
        payload = build_profile_payload(profile.display_name or profile.model_name, profile.vehicle_number, profile.variant, profile.make)
        payload["vehicle_type"] = profile.vehicle_type or payload.get("vehicle_type", "motorcycle")
        payload.update(manual_overrides)
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
        manual_overrides = _profile_manual_overrides(serializer)
        payload = build_profile_payload(profile.display_name or profile.model_name, profile.vehicle_number, profile.variant, profile.make)
        payload["vehicle_type"] = profile.vehicle_type or payload.get("vehicle_type", "motorcycle")
        payload.update(manual_overrides)
        payload["is_primary"] = profile.is_primary
        if payload["is_primary"]:
            BikeProfile.objects.filter(user=self.request.user).exclude(pk=profile.pk).update(is_primary=False)
        _apply_profile_payload(profile, payload)


class BikeServiceRecordListCreateView(ListCreateAPIView):
    serializer_class = BikeServiceRecordSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return BikeServiceRecord.objects.filter(user=self.request.user).select_related("bike_profile").order_by("-service_date", "-id")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        )
        serializer.save(
            user=self.request.user,
            **identity,
        )


class BikeServiceRecordDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeServiceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeServiceRecord.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_update(self, serializer):
        instance = serializer.instance
        bike_profile = serializer.validated_data.get("bike_profile", instance.bike_profile)
        save_kwargs = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
            existing_name=instance.bike_name,
            existing_number=instance.vehicle_number,
        )
        if "parsed_payload" in serializer.validated_data:
            save_kwargs["parsed_payload"] = merge_nested_payload(instance.parsed_payload, serializer.validated_data.get("parsed_payload"))
        serializer.save(**save_kwargs)


class FuelRefillLogListCreateView(ListCreateAPIView):
    serializer_class = FuelRefillLogSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return FuelRefillLog.objects.filter(user=self.request.user).select_related("bike_profile").order_by("-refill_date", "-id")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        )
        serializer.save(
            user=self.request.user,
            **identity,
        )


class FuelRefillLogDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = FuelRefillLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FuelRefillLog.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_update(self, serializer):
        instance = serializer.instance
        bike_profile = serializer.validated_data.get("bike_profile", instance.bike_profile)
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
            existing_name=instance.bike_name,
            existing_number=instance.vehicle_number,
        )
        serializer.save(**identity)


class BikeIssueReportListCreateView(ListCreateAPIView):
    serializer_class = BikeIssueReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return BikeIssueReport.objects.filter(user=self.request.user).select_related("bike_profile", "bike_service", "travel_plan").order_by("-reported_at", "-id")

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
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return BikeDocument.objects.filter(user=self.request.user).select_related("bike_profile").order_by("expiry_date", "-id")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        )
        document = serializer.save(user=self.request.user, **identity)
        bike_service_intelligence.hydrate_document(document)


class BikeDocumentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeDocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return BikeDocument.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_update(self, serializer):
        instance = serializer.instance
        bike_profile = serializer.validated_data.get("bike_profile", instance.bike_profile)
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
            existing_name=instance.bike_name,
            existing_number=instance.vehicle_number,
        )
        document = serializer.save(**identity)
        bike_service_intelligence.hydrate_document(document)

    def perform_destroy(self, instance):
        BikeServiceRecord.objects.filter(source_document=instance).delete()
        instance.delete()


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

        parsed = bike_document_ai.parse(upload, upload.name, user=request.user)
        upload.seek(0)
        document_type = request.data.get("document_type_override") or parsed.document_type
        relevance = bike_document_ai.verify_relevance(bike_profile, parsed, document_type)
        if not relevance["accepted"]:
            operational_logging_service.log(
                user=request.user,
                module="mobility",
                category="document",
                scope="vehicle_document",
                event_type="vehicle_document_rejected",
                severity="warning",
                file_name=upload.name,
                message="Vehicle document upload was rejected because it did not match the selected vehicle profile closely enough.",
                payload={"reasons": relevance["reasons"], "document_type": document_type},
            )
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
            extracted_payload=build_document_payload(parsed, relevance),
            notes=request.data.get("notes", ""),
        )
        bike_service_intelligence.hydrate_document(document)
        record_parser_learning(
            user=request.user,
            scope="vehicle_document",
            filename=upload.name,
            detected_type=document_type,
            text=parsed.source_text,
            field_names=list((document.extracted_payload or {}).keys()),
            parser_status=parsed.parser_status,
            confidence=parsed.confidence,
        )
        if document.parser_status != "parsed":
            operational_logging_service.log(
                user=request.user,
                module="mobility",
                category="document",
                scope="vehicle_document",
                event_type="vehicle_document_needs_review",
                severity="warning",
                document_id=document.id,
                file_name=upload.name,
                message="Vehicle document upload was saved, but Alfred still needs review before trusting the extracted fields.",
                payload={
                    "parse_confidence": document.parse_confidence,
                    "parser_notes": document.parser_notes,
                    "document_type": document.document_type,
                },
            )
        return Response(BikeDocumentSerializer(document, context={"request": request}).data, status=status.HTTP_201_CREATED)


class BikeConditionSnapshotListCreateView(ListCreateAPIView):
    serializer_class = BikeConditionSnapshotSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return BikeConditionSnapshot.objects.filter(user=self.request.user).select_related("bike_profile").order_by("-captured_at", "-id")

    def perform_create(self, serializer):
        bike_profile = serializer.validated_data.get("bike_profile")
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
        )
        snapshot = serializer.save(
            user=self.request.user,
            **identity,
        )
        bike_service_intelligence.hydrate_condition(snapshot, self.request.user)


class BikeConditionSnapshotDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BikeConditionSnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BikeConditionSnapshot.objects.filter(user=self.request.user).select_related("bike_profile")

    def perform_update(self, serializer):
        instance = serializer.instance
        bike_profile = serializer.validated_data.get("bike_profile", instance.bike_profile)
        identity = resolve_vehicle_identity(
            bike_profile,
            bike_name=serializer.validated_data.get("bike_name", ""),
            vehicle_number=serializer.validated_data.get("vehicle_number", ""),
            existing_name=instance.bike_name,
            existing_number=instance.vehicle_number,
        )
        snapshot = serializer.save(**identity)
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

        parsed = bike_document_ai.parse(upload, upload.name, user=request.user)
        relevance = bike_document_ai.verify_relevance(bike_profile, parsed, "invoice")
        if not relevance["accepted"]:
            operational_logging_service.log(
                user=request.user,
                module="mobility",
                category="document",
                scope="vehicle_document",
                event_type="service_document_rejected",
                severity="warning",
                file_name=upload.name,
                message="Service bill upload was rejected because it did not match the selected vehicle profile closely enough.",
                payload={"reasons": relevance["reasons"]},
            )
            return Response(
                {
                    "detail": "The uploaded bill or work note does not look related to the selected vehicle profile.",
                    "reasons": relevance["reasons"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        service_payload = parsed.service_payload
        if not service_payload:
            operational_logging_service.log(
                user=request.user,
                module="mobility",
                category="document",
                scope="vehicle_document",
                event_type="service_document_needs_review",
                severity="warning",
                file_name=upload.name,
                message="Service bill upload was read, but Alfred could not populate a structured service log from it yet.",
                payload={"parser_notes": parsed.parser_notes, "parse_confidence": parsed.confidence},
            )
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
            extracted_payload=build_document_payload(parsed, relevance),
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
            source_document=document,
            source_document_name=upload.name,
            extracted_work_summary=service_payload.get("extracted_work_summary", ""),
            parsed_payload=build_service_record_payload(
                parsed,
                service_payload,
                document=document,
                document_payload=document.extracted_payload,
            ),
        )
        record_parser_learning(
            user=request.user,
            scope="vehicle_document",
            filename=upload.name,
            detected_type="invoice",
            text=parsed.source_text,
            field_names=[*list((document.extracted_payload or {}).keys()), *list((service_record.parsed_payload or {}).keys())],
            parser_status=parsed.parser_status,
            confidence=parsed.confidence,
        )
        if document.parser_status != "parsed":
            operational_logging_service.log(
                user=request.user,
                module="mobility",
                category="document",
                scope="vehicle_document",
                event_type="service_document_review_import",
                severity="warning",
                document_id=document.id,
                file_name=upload.name,
                message="Service bill was imported, but parser confidence stayed below the trusted threshold.",
                payload={"parse_confidence": document.parse_confidence, "parser_notes": document.parser_notes},
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
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return TravelPlan.objects.filter(user=self.request.user).annotate(
            log_count=Count("logs", distinct=True),
            photo_count=Count("photos", distinct=True),
        ).select_related("vehicle_profile").order_by("start_date", "-id")

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
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return TripLog.objects.filter(user=self.request.user).select_related("travel_plan", "travel_plan__vehicle_profile").order_by("-log_date", "-id")

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
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return TripPhoto.objects.filter(user=self.request.user).select_related("travel_plan", "travel_plan__vehicle_profile", "trip_log").order_by("-taken_at", "-id")

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
        revision = self._revision(request.user)
        payload = materialize_payload(
            namespace="mobility-dashboard",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=45,
            builder=lambda: self._build_payload(request),
        )
        return Response(payload)

    def _revision(self, user) -> str:
        profile_meta = BikeProfile.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        plan_meta = TravelPlan.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        log_meta = TripLog.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("log_date"))
        photo_meta = TripPhoto.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_taken=Max("taken_at"))
        document_meta = BikeDocument.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        condition_meta = BikeConditionSnapshot.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_captured=Max("captured_at"))
        return "|".join(
            str(value or "")
            for value in [
                profile_meta["count"], profile_meta["max_id"], profile_meta["max_updated"],
                plan_meta["count"], plan_meta["max_id"], plan_meta["max_updated"],
                log_meta["count"], log_meta["max_id"], log_meta["max_date"],
                photo_meta["count"], photo_meta["max_id"], photo_meta["max_taken"],
                document_meta["count"], document_meta["max_id"], document_meta["max_updated"],
                condition_meta["count"], condition_meta["max_id"], condition_meta["max_captured"],
            ]
        )

    def _build_payload(self, request):
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

        return {
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


class BikeServiceDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile_meta = BikeProfile.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        service_meta = BikeServiceRecord.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("service_date"))
        refill_meta = FuelRefillLog.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("refill_date"))
        issue_meta = BikeIssueReport.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_reported=Max("reported_at"))
        plan_meta = TravelPlan.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        document_meta = BikeDocument.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        condition_meta = BikeConditionSnapshot.objects.filter(user=request.user).aggregate(count=Count("id"), max_id=Max("id"), max_captured=Max("captured_at"))
        revision = "|".join(
            str(value or "")
            for value in [
                profile_meta["count"], profile_meta["max_id"], profile_meta["max_updated"],
                service_meta["count"], service_meta["max_id"], service_meta["max_date"],
                refill_meta["count"], refill_meta["max_id"], refill_meta["max_date"],
                issue_meta["count"], issue_meta["max_id"], issue_meta["max_reported"],
                plan_meta["count"], plan_meta["max_id"], plan_meta["max_updated"],
                document_meta["count"], document_meta["max_id"], document_meta["max_updated"],
                condition_meta["count"], condition_meta["max_id"], condition_meta["max_captured"],
            ]
        )
        payload = materialize_payload(
            namespace="bike-service-dashboard-view",
            user_id=request.user.id,
            revision=revision,
            ttl_seconds=45,
            builder=lambda: self._build_payload(request),
        )
        return Response(payload)

    def _build_payload(self, request):
        intelligence = bike_service_intelligence.build_dashboard(request.user)
        bike_profiles = BikeProfile.objects.filter(user=request.user)
        service_records = BikeServiceRecord.objects.filter(user=request.user).select_related("bike_profile").order_by("-service_date", "-id")[:18]
        refill_logs = FuelRefillLog.objects.filter(user=request.user).select_related("bike_profile").order_by("-refill_date", "-id")[:18]
        issue_reports = BikeIssueReport.objects.filter(user=request.user).select_related("bike_profile", "bike_service", "travel_plan").order_by("-reported_at", "-id")[:12]
        travel_plans = TravelPlan.objects.filter(user=request.user).select_related("vehicle_profile").order_by("start_date", "-id")[:20]
        documents = BikeDocument.objects.filter(user=request.user).select_related("bike_profile").order_by("expiry_date", "-id")[:15]
        conditions = BikeConditionSnapshot.objects.filter(user=request.user).select_related("bike_profile").order_by("-captured_at", "-id")[:12]
        return {
            **intelligence,
            "bike_profiles": BikeProfileSerializer(bike_profiles, many=True, context={"request": request}).data,
            "bike_catalog": [],
            "bike_catalog_manufacturers": list_catalog_manufacturers(),
            "bike_catalog_summary": catalog_coverage_summary(),
            "bike_services": BikeServiceRecordSerializer(service_records, many=True, context={"request": request}).data,
            "bike_refills": FuelRefillLogSerializer(refill_logs, many=True, context={"request": request}).data,
            "bike_issues": BikeIssueReportSerializer(issue_reports, many=True, context={"request": request}).data,
            "bike_documents": BikeDocumentSerializer(documents, many=True, context={"request": request}).data,
            "bike_conditions": BikeConditionSnapshotSerializer(conditions, many=True, context={"request": request}).data,
            "travel_plans": TravelPlanSerializer(travel_plans, many=True, context={"request": request}).data,
        }
