from django.conf import settings
from django.db import models
from django.utils import timezone


class BikeProfile(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ("motorcycle", "Motorcycle"),
        ("scooter", "Scooter"),
        ("car", "Car"),
        ("other", "Other"),
    ]
    BIKE_CLASS_CHOICES = [
        ("commuter", "Commuter"),
        ("roadster", "Roadster"),
        ("retro", "Retro"),
        ("adventure", "Adventure"),
        ("sport", "Sport"),
        ("cruiser", "Cruiser"),
        ("scooter", "Scooter"),
        ("touring", "Touring"),
        ("hatchback", "Hatchback"),
        ("sedan", "Sedan"),
        ("suv", "SUV"),
        ("mpv", "MPV"),
        ("custom", "Custom"),
    ]

    VERIFICATION_CHOICES = [
        ("official", "Official Catalog Match"),
        ("matched", "AI Matched"),
        ("custom", "Custom / Unverified"),
    ]
    USAGE_PATTERN_CHOICES = [
        ("personal", "Personal / Lifestyle"),
        ("essential", "Essential Mobility"),
        ("mixed", "Mixed Personal + Utility"),
        ("commercial", "Commercial / Income Generating"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bike_profiles")
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default="motorcycle")
    display_name = models.CharField(max_length=180)
    make = models.CharField(max_length=80, blank=True)
    model_name = models.CharField(max_length=120)
    variant = models.CharField(max_length=120, blank=True)
    vehicle_number = models.CharField(max_length=40, blank=True)
    bike_class = models.CharField(max_length=20, choices=BIKE_CLASS_CHOICES, default="roadster")
    engine_cc = models.FloatField(null=True, blank=True)
    fuel_tank_capacity_l = models.FloatField(null=True, blank=True)
    expected_mileage_kmpl = models.FloatField(null=True, blank=True)
    service_interval_km = models.PositiveIntegerField(null=True, blank=True)
    service_interval_days = models.PositiveIntegerField(null=True, blank=True)
    optimal_cruising_speed_kmph = models.PositiveIntegerField(null=True, blank=True)
    tyre_front_spec = models.CharField(max_length=40, blank=True)
    tyre_rear_spec = models.CharField(max_length=40, blank=True)
    fuel_type = models.CharField(max_length=20, blank=True, default="petrol")
    usage_pattern = models.CharField(max_length=20, choices=USAGE_PATTERN_CHOICES, default="personal")
    estimated_market_value = models.FloatField(default=0)
    monthly_income_support = models.FloatField(default=0)
    catalog_key = models.CharField(max_length=80, blank=True)
    official_source_name = models.CharField(max_length=120, blank=True)
    official_source_url = models.URLField(blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_CHOICES, default="custom")
    is_primary = models.BooleanField(default=False)
    ai_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "display_name", "-updated_at"]
        indexes = [
            models.Index(fields=["user", "vehicle_type", "is_primary"]),
            models.Index(fields=["user", "display_name"]),
            models.Index(fields=["user", "vehicle_number"]),
        ]

    def __str__(self):
        return self.display_name


class BikeServiceRecord(models.Model):
    SERVICE_TYPE_CHOICES = [
        ("routine", "Routine Service"),
        ("repair", "Repair"),
        ("oil_chain", "Oil / Chain"),
        ("tyres", "Tyres / Wheels"),
        ("accessory", "Accessory / Upgrade"),
        ("custom", "Custom Work"),
    ]
    SOURCE_MODE_CHOICES = [
        ("manual", "Manual"),
        ("bill_import", "Imported From Bill"),
        ("work_note", "Imported From Work Note"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bike_services")
    bike_profile = models.ForeignKey("BikeProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="service_records")
    bike_name = models.CharField(max_length=120)
    vehicle_number = models.CharField(max_length=40, blank=True)
    service_date = models.DateField()
    odometer_km = models.PositiveIntegerField(default=0)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPE_CHOICES, default="routine")
    cost = models.FloatField(default=0)
    service_center = models.CharField(max_length=160, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    next_service_km = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    source_mode = models.CharField(max_length=20, choices=SOURCE_MODE_CHOICES, default="manual")
    source_document_name = models.CharField(max_length=220, blank=True)
    extracted_work_summary = models.TextField(blank=True)
    parsed_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-service_date", "-id"]
        indexes = [
            models.Index(fields=["user", "bike_profile", "service_date"]),
            models.Index(fields=["user", "vehicle_number", "service_date"]),
        ]

    def __str__(self):
        return f"{self.bike_name} service on {self.service_date}"


class TravelPlan(models.Model):
    TRANSPORT_MODE_CHOICES = [
        ("ride", "Bike Ride"),
        ("roadtrip", "Road Trip"),
        ("train", "Train"),
        ("flight", "Flight"),
        ("mixed", "Mixed Mode"),
    ]

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("booked", "Booked"),
        ("on_trip", "On Trip"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="travel_plans")
    vehicle_profile = models.ForeignKey("BikeProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="travel_plans")
    title = models.CharField(max_length=160)
    destination = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.FloatField(default=0)
    transport_mode = models.CharField(max_length=20, choices=TRANSPORT_MODE_CHOICES, default="ride")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="planned")
    stay_details = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "-id"]
        indexes = [
            models.Index(fields=["user", "status", "start_date"]),
            models.Index(fields=["user", "vehicle_profile", "start_date"]),
        ]

    def __str__(self):
        return f"{self.title} to {self.destination}"

    @property
    def duration_days(self) -> int:
        return max((self.end_date - self.start_date).days + 1, 1)


class TripLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trip_logs")
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE, related_name="logs")
    log_date = models.DateField()
    title = models.CharField(max_length=160)
    location_name = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    distance_km = models.FloatField(default=0)
    spend_amount = models.FloatField(default=0)
    mood = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-log_date", "-id"]
        indexes = [
            models.Index(fields=["user", "travel_plan", "log_date"]),
        ]

    def __str__(self):
        return f"{self.title} on {self.log_date}"


class TripPhoto(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="trip_photos")
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.CASCADE, related_name="photos")
    trip_log = models.ForeignKey(TripLog, on_delete=models.SET_NULL, null=True, blank=True, related_name="photos")
    image = models.FileField(upload_to="trip_photos/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)
    location_name = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-taken_at", "-id"]
        indexes = [
            models.Index(fields=["user", "travel_plan", "taken_at"]),
        ]

    def __str__(self):
        return self.caption or f"Photo for {self.travel_plan.title}"


class BikeIssueReport(models.Model):
    SYSTEM_CHOICES = [
        ("general", "General"),
        ("engine", "Engine"),
        ("brakes", "Brakes"),
        ("chain", "Chain / Drive"),
        ("electrical", "Electrical"),
        ("tyres", "Tyres / Wheels"),
        ("suspension", "Suspension"),
        ("clutch", "Clutch / Gearbox"),
        ("body", "Body / Accessories"),
    ]

    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("monitor", "Monitor"),
        ("in_service", "In Service"),
        ("resolved", "Resolved"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bike_issue_reports")
    bike_profile = models.ForeignKey("BikeProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="issue_reports")
    bike_service = models.ForeignKey(BikeServiceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="issue_reports")
    travel_plan = models.ForeignKey(TravelPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="bike_issue_reports")
    reported_at = models.DateTimeField(default=timezone.now)
    next_action_at = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=160)
    system = models.CharField(max_length=20, choices=SYSTEM_CHOICES, default="general")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    symptom = models.TextField()
    observation = models.TextField(blank=True)
    probable_cause = models.CharField(max_length=220, blank=True)
    suggested_action = models.TextField(blank=True)
    service_center_note = models.TextField(blank=True)
    projected_cost = models.FloatField(default=0)
    actual_cost = models.FloatField(null=True, blank=True)
    tags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reported_at", "-id"]
        indexes = [
            models.Index(fields=["user", "bike_profile", "status", "reported_at"]),
            models.Index(fields=["user", "severity", "status", "reported_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"


class BikeDocument(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ("insurance", "Insurance"),
        ("puc", "PUC"),
        ("registration", "Registration / RC"),
        ("license", "License"),
        ("roadside", "Roadside Assistance"),
        ("invoice", "Service Invoice"),
        ("other", "Other"),
    ]

    VERIFICATION_STATUS_CHOICES = [
        ("valid", "Valid"),
        ("expiring_soon", "Expiring Soon"),
        ("expired", "Expired"),
        ("incomplete", "Incomplete"),
    ]
    PARSER_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("parsed", "Parsed"),
        ("needs_review", "Needs Review"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bike_documents")
    bike_profile = models.ForeignKey("BikeProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    bike_name = models.CharField(max_length=120)
    vehicle_number = models.CharField(max_length=40, blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default="other")
    issuer = models.CharField(max_length=160, blank=True)
    document_number = models.CharField(max_length=120, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    premium_amount = models.FloatField(default=0)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default="incomplete")
    verification_notes = models.TextField(blank=True)
    document_file = models.FileField(upload_to="bike_documents/%Y/%m/", blank=True)
    document_title = models.CharField(max_length=220, blank=True)
    parser_status = models.CharField(max_length=20, choices=PARSER_STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0)
    parser_notes = models.TextField(blank=True)
    source_text = models.TextField(blank=True)
    extracted_payload = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expiry_date", "-id"]
        indexes = [
            models.Index(fields=["user", "bike_profile", "document_type", "expiry_date"]),
            models.Index(fields=["user", "vehicle_number", "document_type"]),
        ]

    def __str__(self):
        return f"{self.bike_name} {self.get_document_type_display()}"


class BikeConditionSnapshot(models.Model):
    CONDITION_CHOICES = [
        ("good", "Good"),
        ("watch", "Watch"),
        ("service", "Service Soon"),
        ("urgent", "Urgent"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bike_condition_snapshots")
    bike_profile = models.ForeignKey("BikeProfile", on_delete=models.SET_NULL, null=True, blank=True, related_name="condition_snapshots")
    bike_name = models.CharField(max_length=120)
    vehicle_number = models.CharField(max_length=40, blank=True)
    captured_at = models.DateTimeField(default=timezone.now)
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    overall_status = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    overall_score = models.PositiveIntegerField(default=80)
    engine_status = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    brake_status = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    tyre_status = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    battery_status = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    body_status = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    observed_symptoms = models.TextField(blank=True)
    ai_assessment = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-captured_at", "-id"]
        indexes = [
            models.Index(fields=["user", "bike_profile", "captured_at"]),
            models.Index(fields=["user", "vehicle_number", "captured_at"]),
        ]

    def __str__(self):
        return f"{self.bike_name} condition {self.overall_score}"
