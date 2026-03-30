from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord, TravelPlan, TripLog, TripPhoto


class BikeProfileSerializer(serializers.ModelSerializer):
    verification_status_label = serializers.CharField(source="get_verification_status_display", read_only=True)
    vehicle_type_label = serializers.CharField(source="get_vehicle_type_display", read_only=True)
    usage_pattern_label = serializers.CharField(source="get_usage_pattern_display", read_only=True)

    class Meta:
        model = BikeProfile
        fields = (
            "id",
            "user",
            "vehicle_type",
            "vehicle_type_label",
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
            "usage_pattern_label",
            "estimated_market_value",
            "monthly_income_support",
            "catalog_key",
            "official_source_name",
            "official_source_url",
            "verification_status",
            "verification_status_label",
            "is_primary",
            "ai_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "vehicle_type_label",
            "usage_pattern_label",
            "catalog_key",
            "official_source_name",
            "official_source_url",
            "verification_status",
            "verification_status_label",
            "ai_notes",
            "created_at",
            "updated_at",
        )


class BikeServiceRecordSerializer(serializers.ModelSerializer):
    service_type_label = serializers.CharField(source="get_service_type_display", read_only=True)
    source_mode_label = serializers.CharField(source="get_source_mode_display", read_only=True)
    bike_profile_name = serializers.CharField(source="bike_profile.display_name", read_only=True)
    bike_profile = serializers.PrimaryKeyRelatedField(queryset=BikeProfile.objects.all(), allow_null=True, required=False)

    class Meta:
        model = BikeServiceRecord
        fields = (
            "id",
            "user",
            "bike_profile",
            "bike_profile_name",
            "bike_name",
            "vehicle_number",
            "service_date",
            "odometer_km",
            "service_type",
            "service_type_label",
            "cost",
            "service_center",
            "next_service_date",
            "next_service_km",
            "notes",
            "source_mode",
            "source_mode_label",
            "source_document_name",
            "extracted_work_summary",
            "parsed_payload",
            "created_at",
        )
        read_only_fields = ("user", "created_at")

    def validate(self, attrs):
        request = self.context.get("request")
        service_date = attrs.get("service_date", getattr(self.instance, "service_date", None))
        next_service_date = attrs.get("next_service_date", getattr(self.instance, "next_service_date", None))
        odometer_km = attrs.get("odometer_km", getattr(self.instance, "odometer_km", 0))
        next_service_km = attrs.get("next_service_km", getattr(self.instance, "next_service_km", None))
        bike_profile = attrs.get("bike_profile", getattr(self.instance, "bike_profile", None))

        if service_date and next_service_date and next_service_date < service_date:
            raise serializers.ValidationError({"next_service_date": "Next service date cannot be earlier than the service date."})
        if next_service_km is not None and odometer_km is not None and next_service_km < odometer_km:
            raise serializers.ValidationError({"next_service_km": "Next service km must be greater than or equal to the current odometer."})
        if request is not None and bike_profile and bike_profile.user_id != request.user.id:
            raise serializers.ValidationError({"bike_profile": "You can only use your own saved vehicle profiles."})

        return attrs


class TravelPlanSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    transport_mode_label = serializers.CharField(source="get_transport_mode_display", read_only=True)
    duration_days = serializers.IntegerField(read_only=True)
    log_count = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()
    vehicle_profile_name = serializers.CharField(source="vehicle_profile.display_name", read_only=True)
    vehicle_profile = serializers.PrimaryKeyRelatedField(queryset=BikeProfile.objects.all(), allow_null=True, required=False)

    class Meta:
        model = TravelPlan
        fields = (
            "id",
            "user",
            "vehicle_profile",
            "vehicle_profile_name",
            "title",
            "destination",
            "start_date",
            "end_date",
            "budget",
            "transport_mode",
            "transport_mode_label",
            "status",
            "status_label",
            "stay_details",
            "notes",
            "duration_days",
            "log_count",
            "photo_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("user", "duration_days", "log_count", "photo_count", "created_at", "updated_at")

    def validate(self, attrs):
        request = self.context.get("request")
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        vehicle_profile = attrs.get("vehicle_profile", getattr(self.instance, "vehicle_profile", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError("Trip end date cannot be earlier than the start date.")
        if request is not None and vehicle_profile and vehicle_profile.user_id != request.user.id:
            raise serializers.ValidationError({"vehicle_profile": "You can only link your own vehicle profile."})
        return attrs

    def get_log_count(self, obj):
        return getattr(obj, "log_count", obj.logs.count())

    def get_photo_count(self, obj):
        return getattr(obj, "photo_count", obj.photos.count())


class TripLogSerializer(serializers.ModelSerializer):
    travel_plan_title = serializers.CharField(source="travel_plan.title", read_only=True)

    class Meta:
        model = TripLog
        fields = (
            "id",
            "user",
            "travel_plan",
            "travel_plan_title",
            "log_date",
            "title",
            "location_name",
            "notes",
            "latitude",
            "longitude",
            "distance_km",
            "spend_amount",
            "mood",
            "created_at",
        )
        read_only_fields = ("user", "travel_plan_title", "created_at")

    def validate(self, attrs):
        request = self.context.get("request")
        travel_plan = attrs.get("travel_plan", getattr(self.instance, "travel_plan", None))
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))

        if request is not None and travel_plan and travel_plan.user_id != request.user.id:
            raise serializers.ValidationError({"travel_plan": "You can only log trips for your own travel plans."})
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError("Provide both latitude and longitude together.")

        return attrs


class TripPhotoSerializer(serializers.ModelSerializer):
    travel_plan_title = serializers.CharField(source="travel_plan.title", read_only=True)
    trip_log_title = serializers.CharField(source="trip_log.title", read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = TripPhoto
        fields = (
            "id",
            "user",
            "travel_plan",
            "travel_plan_title",
            "trip_log",
            "trip_log_title",
            "image",
            "photo_url",
            "caption",
            "location_name",
            "latitude",
            "longitude",
            "taken_at",
            "created_at",
        )
        read_only_fields = ("user", "travel_plan_title", "trip_log_title", "photo_url", "created_at")

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if not obj.image:
            return ""
        if request is not None:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def validate(self, attrs):
        request = self.context.get("request")
        travel_plan = attrs.get("travel_plan", getattr(self.instance, "travel_plan", None))
        trip_log = attrs.get("trip_log", getattr(self.instance, "trip_log", None))
        latitude = attrs.get("latitude", getattr(self.instance, "latitude", None))
        longitude = attrs.get("longitude", getattr(self.instance, "longitude", None))

        if request is not None and travel_plan and travel_plan.user_id != request.user.id:
            raise serializers.ValidationError({"travel_plan": "You can only upload photos to your own travel plans."})
        if request is not None and trip_log and trip_log.user_id != request.user.id:
            raise serializers.ValidationError({"trip_log": "You can only attach photos to your own trip logs."})
        if trip_log and travel_plan and trip_log.travel_plan_id != travel_plan.id:
            raise serializers.ValidationError({"trip_log": "Selected trip log does not belong to the chosen travel plan."})
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError("Provide both latitude and longitude together.")

        return attrs


class BikeIssueReportSerializer(serializers.ModelSerializer):
    system_label = serializers.CharField(source="get_system_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    bike_service_title = serializers.CharField(source="bike_service.bike_name", read_only=True)
    bike_profile_name = serializers.CharField(source="bike_profile.display_name", read_only=True)
    travel_plan_title = serializers.CharField(source="travel_plan.title", read_only=True)
    bike_profile = serializers.PrimaryKeyRelatedField(queryset=BikeProfile.objects.all(), allow_null=True, required=False)
    bike_service = serializers.PrimaryKeyRelatedField(queryset=BikeServiceRecord.objects.all(), allow_null=True, required=False)
    travel_plan = serializers.PrimaryKeyRelatedField(queryset=TravelPlan.objects.all(), allow_null=True, required=False)
    odometer_km = serializers.IntegerField(allow_null=True, required=False)
    next_action_at = serializers.DateTimeField(allow_null=True, required=False)
    actual_cost = serializers.FloatField(allow_null=True, required=False)

    class Meta:
        model = BikeIssueReport
        fields = (
            "id",
            "user",
            "bike_profile",
            "bike_profile_name",
            "bike_service",
            "bike_service_title",
            "travel_plan",
            "travel_plan_title",
            "reported_at",
            "next_action_at",
            "title",
            "system",
            "system_label",
            "severity",
            "severity_label",
            "status",
            "status_label",
            "odometer_km",
            "symptom",
            "observation",
            "probable_cause",
            "suggested_action",
            "service_center_note",
            "projected_cost",
            "actual_cost",
            "tags",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "bike_service_title",
            "travel_plan_title",
            "system_label",
            "severity_label",
            "status_label",
            "probable_cause",
            "suggested_action",
            "service_center_note",
            "projected_cost",
            "tags",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        bike_service = attrs.get("bike_service", getattr(self.instance, "bike_service", None))
        bike_profile = attrs.get("bike_profile", getattr(self.instance, "bike_profile", None))
        travel_plan = attrs.get("travel_plan", getattr(self.instance, "travel_plan", None))
        reported_at = attrs.get("reported_at", getattr(self.instance, "reported_at", None))
        next_action_at = attrs.get("next_action_at", getattr(self.instance, "next_action_at", None))

        if request is not None and bike_profile and bike_profile.user_id != request.user.id:
            raise serializers.ValidationError({"bike_profile": "You can only attach issues to your own vehicle profiles."})
        if request is not None and bike_service and bike_service.user_id != request.user.id:
            raise serializers.ValidationError({"bike_service": "You can only attach issues to your own bike service records."})
        if request is not None and travel_plan and travel_plan.user_id != request.user.id:
            raise serializers.ValidationError({"travel_plan": "You can only link issues to your own travel plans."})
        if reported_at and next_action_at and next_action_at < reported_at:
            raise serializers.ValidationError({"next_action_at": "Next action cannot be earlier than the reported time."})

        return attrs

    def to_internal_value(self, data):
        normalized = data.copy()
        for field in ("bike_service", "travel_plan", "odometer_km", "next_action_at", "actual_cost"):
            if normalized.get(field) == "":
                normalized[field] = None
        return super().to_internal_value(normalized)


class BikeDocumentSerializer(serializers.ModelSerializer):
    document_type_label = serializers.CharField(source="get_document_type_display", read_only=True)
    verification_status_label = serializers.CharField(source="get_verification_status_display", read_only=True)
    parser_status_label = serializers.CharField(source="get_parser_status_display", read_only=True)
    document_url = serializers.SerializerMethodField()
    bike_profile_name = serializers.CharField(source="bike_profile.display_name", read_only=True)
    bike_profile = serializers.PrimaryKeyRelatedField(queryset=BikeProfile.objects.all(), allow_null=True, required=False)

    class Meta:
        model = BikeDocument
        fields = (
            "id",
            "user",
            "bike_profile",
            "bike_profile_name",
            "bike_name",
            "vehicle_number",
            "document_type",
            "document_type_label",
            "issuer",
            "document_number",
            "issue_date",
            "expiry_date",
            "premium_amount",
            "verification_status",
            "verification_status_label",
            "verification_notes",
            "document_file",
            "document_url",
            "document_title",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "parser_notes",
            "extracted_payload",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user",
            "document_type_label",
            "verification_status",
            "verification_status_label",
            "verification_notes",
            "document_url",
            "document_title",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "parser_notes",
            "extracted_payload",
            "created_at",
            "updated_at",
        )

    def get_document_url(self, obj):
        request = self.context.get("request")
        if not obj.document_file:
            return ""
        if request is not None:
            return request.build_absolute_uri(obj.document_file.url)
        return obj.document_file.url

    def validate(self, attrs):
        request = self.context.get("request")
        issue_date = attrs.get("issue_date", getattr(self.instance, "issue_date", None))
        expiry_date = attrs.get("expiry_date", getattr(self.instance, "expiry_date", None))
        bike_profile = attrs.get("bike_profile", getattr(self.instance, "bike_profile", None))
        if issue_date and expiry_date and expiry_date < issue_date:
            raise serializers.ValidationError({"expiry_date": "Expiry date cannot be earlier than issue date."})
        if self.instance is None and not attrs.get("document_file"):
            raise serializers.ValidationError({"document_file": "Upload a document file so Alfred can parse it."})
        if request is not None and bike_profile and bike_profile.user_id != request.user.id:
            raise serializers.ValidationError({"bike_profile": "You can only attach documents to your own vehicle profiles."})
        return attrs

    def to_internal_value(self, data):
        normalized = data.copy()
        for field in ("issue_date", "expiry_date", "document_number", "issuer", "vehicle_number", "notes"):
            if normalized.get(field) == "":
                normalized[field] = None if field in {"issue_date", "expiry_date"} else ""
        if normalized.get("premium_amount") == "":
            normalized["premium_amount"] = 0
        return super().to_internal_value(normalized)


class BikeConditionSnapshotSerializer(serializers.ModelSerializer):
    overall_status_label = serializers.CharField(source="get_overall_status_display", read_only=True)
    engine_status_label = serializers.CharField(source="get_engine_status_display", read_only=True)
    brake_status_label = serializers.CharField(source="get_brake_status_display", read_only=True)
    tyre_status_label = serializers.CharField(source="get_tyre_status_display", read_only=True)
    battery_status_label = serializers.CharField(source="get_battery_status_display", read_only=True)
    body_status_label = serializers.CharField(source="get_body_status_display", read_only=True)
    bike_profile_name = serializers.CharField(source="bike_profile.display_name", read_only=True)
    bike_profile = serializers.PrimaryKeyRelatedField(queryset=BikeProfile.objects.all(), allow_null=True, required=False)

    class Meta:
        model = BikeConditionSnapshot
        fields = (
            "id",
            "user",
            "bike_profile",
            "bike_profile_name",
            "bike_name",
            "vehicle_number",
            "captured_at",
            "odometer_km",
            "overall_status",
            "overall_status_label",
            "overall_score",
            "engine_status",
            "engine_status_label",
            "brake_status",
            "brake_status_label",
            "tyre_status",
            "tyre_status_label",
            "battery_status",
            "battery_status_label",
            "body_status",
            "body_status_label",
            "observed_symptoms",
            "ai_assessment",
            "notes",
            "created_at",
        )
        read_only_fields = (
            "user",
            "overall_status_label",
            "engine_status_label",
            "brake_status_label",
            "tyre_status_label",
            "battery_status_label",
            "body_status_label",
            "overall_score",
            "ai_assessment",
            "created_at",
        )

    def validate(self, attrs):
        request = self.context.get("request")
        captured_at = attrs.get("captured_at", getattr(self.instance, "captured_at", None))
        bike_profile = attrs.get("bike_profile", getattr(self.instance, "bike_profile", None))
        if captured_at and captured_at > (timezone.now() + timedelta(minutes=5)):
            raise serializers.ValidationError({"captured_at": "Condition snapshot time cannot be more than 5 minutes in the future."})
        if request is not None and bike_profile and bike_profile.user_id != request.user.id:
            raise serializers.ValidationError({"bike_profile": "You can only attach condition logs to your own vehicle profiles."})
        return attrs

    def to_internal_value(self, data):
        normalized = data.copy()
        for field in ("captured_at", "odometer_km"):
            if normalized.get(field) == "":
                normalized[field] = None
        return super().to_internal_value(normalized)
