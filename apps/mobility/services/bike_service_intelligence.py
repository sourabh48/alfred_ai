from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import re
from statistics import mean

from django.db.models import Count, Max, Q
from django.utils import timezone

from alfred_ai.services.materialized_cache import materialize_payload
from apps.ml_engine.inference_adapters.service_cost_predictor import service_cost_predictor, service_type_score, vehicle_type_score
from apps.mobility.models import BikeConditionSnapshot, BikeDocument, BikeIssueReport, BikeProfile, BikeServiceRecord, FuelRefillLog, TripLog
from .bike_catalog import build_maintenance_guidance


SERVICE_RULES = [
    {
        "system": "chain",
        "keywords": ["chain", "sprocket", "slack", "jerk", "clunk", "dry chain", "drivetrain"],
        "probable_cause": "Chain slack is out of spec, lubrication is low, or sprocket wear has started.",
        "suggested_action": "Clean and lubricate the chain, check slack, and inspect sprocket teeth for hooking.",
        "service_center_note": "Please inspect chain slack, chain lubrication state, and sprocket wear. Confirm whether a clean-and-lube is enough or a chain/sprocket set is needed.",
        "cost_range": (250, 4200),
        "tags": ["drive-train", "chain-check"],
    },
    {
        "system": "brakes",
        "keywords": ["brake", "squeal", "grinding", "long braking", "soft lever", "pad", "disc"],
        "probable_cause": "Brake pads may be worn, glazed, contaminated, or the caliper/fluid system may need inspection.",
        "suggested_action": "Inspect front and rear pads, disc condition, caliper movement, and brake fluid level before riding hard again.",
        "service_center_note": "Please inspect pad thickness, rotor condition, brake fluid, and caliper movement. Confirm whether the issue is pad wear, contamination, or caliper drag.",
        "cost_range": (700, 2400),
        "tags": ["brake-safety", "pad-check"],
    },
    {
        "system": "electrical",
        "keywords": ["hard start", "battery", "starting", "self start", "dim light", "electrical", "starter"],
        "probable_cause": "Battery health, charging output, spark plug condition, or starter circuit performance may be weak.",
        "suggested_action": "Test battery voltage, charging output, starter response, and inspect the spark plug before replacing parts blindly.",
        "service_center_note": "Please run a battery and charging-system test, check starter draw, and inspect the spark plug and terminals.",
        "cost_range": (300, 4500),
        "tags": ["battery-check", "starting-issue"],
    },
    {
        "system": "engine",
        "keywords": ["overheat", "heating", "engine knock", "misfire", "rough idle", "oil leak", "smoke"],
        "probable_cause": "Engine oil quality, cooling flow, tuning, or sealing may need inspection.",
        "suggested_action": "Check engine oil age and level, inspect for leaks, and ask for a full engine health check if heating or misfire persists.",
        "service_center_note": "Please inspect engine oil condition, cooling path, leak points, spark plug, and throttle-body/carb tune if idle is unstable.",
        "cost_range": (1200, 6500),
        "tags": ["engine-health", "oil-check"],
    },
    {
        "system": "tyres",
        "keywords": ["tyre", "tire", "puncture", "wobble", "uneven wear", "vibration", "alignment"],
        "probable_cause": "Tyre pressure, wheel balance, alignment, or tyre wear pattern may be causing instability.",
        "suggested_action": "Check pressure, inspect tyre wear, and ask for balancing or replacement if wobble continues.",
        "service_center_note": "Please inspect tyre pressure, tread wear, wheel balance, and spoke/alloy condition. Confirm if replacement is needed.",
        "cost_range": (150, 5000),
        "tags": ["tyre-check", "stability"],
    },
    {
        "system": "clutch",
        "keywords": ["clutch", "gear", "gearbox", "shift", "slip", "stuck gear"],
        "probable_cause": "Clutch cable free play, clutch wear, or gearbox adjustment may be off.",
        "suggested_action": "Check clutch free play and gear-shift feel first, then escalate to clutch-pack inspection if slipping continues.",
        "service_center_note": "Please inspect clutch free play, cable condition, clutch wear, and gear-shift linkage response.",
        "cost_range": (250, 4200),
        "tags": ["clutch-check", "gear-shift"],
    },
]

PART_RULES = [
    {
        "key": "engine_oil",
        "label": "Engine Oil",
        "system": "engine",
        "keywords": ["engine oil", "oil change", "oil filter", "synthetic oil", "10w", "15w", "lubricant"],
        "condition_field": "engine_status",
        "service_window_days": 180,
        "service_window_km": 4000,
        "impact_area": "Lubrication, heat control, and long-term engine wear",
        "performance_effect": "Late oil service can increase heat, roughness, and long-term engine wear.",
        "recommended_action": "Keep oil and filter changes close to the model interval, especially before long highway or summer runs.",
    },
    {
        "key": "air_filter",
        "label": "Air Filter",
        "system": "engine",
        "keywords": ["air filter", "air cleaner", "filter clean", "intake filter"],
        "condition_field": "engine_status",
        "service_window_days": 240,
        "service_window_km": 6000,
        "impact_area": "Airflow, throttle response, and mileage stability",
        "performance_effect": "A dirty air filter can reduce throttle response and hurt mileage under load.",
        "recommended_action": "Inspect and clean or replace the air filter if rides are dusty, mileage drops, or throttle response feels flat.",
    },
    {
        "key": "brake_pads",
        "label": "Brake Pads And Fluid",
        "system": "brakes",
        "keywords": ["brake pad", "pads", "brake fluid", "caliper service", "disc pad", "brake shoe"],
        "condition_field": "brake_status",
        "service_window_days": 180,
        "service_window_km": 5000,
        "impact_area": "Stopping distance, braking feel, and safety margin",
        "performance_effect": "Brake wear directly affects stopping confidence, heat handling, and emergency braking safety.",
        "recommended_action": "Inspect pad thickness, disc condition, and brake fluid freshness before trusting long descents or high-speed riding.",
    },
    {
        "key": "chain_drive",
        "label": "Chain And Drive",
        "system": "chain",
        "keywords": ["chain", "sprocket", "chain clean", "chain lube", "chain set", "chain slack"],
        "condition_field": "",
        "service_window_days": 120,
        "service_window_km": 2500,
        "impact_area": "Power delivery, drivetrain smoothness, and wear rate",
        "performance_effect": "Dry or worn chain components can increase noise, jerkiness, and premature sprocket wear.",
        "recommended_action": "Keep chain clean, lubricated, and in spec before long rides or rain-heavy usage.",
    },
    {
        "key": "tyres",
        "label": "Tyres And Wheels",
        "system": "tyres",
        "keywords": ["tyre", "tire", "wheel balance", "alignment", "puncture", "tubeless", "wheel"],
        "condition_field": "tyre_status",
        "service_window_days": 365,
        "service_window_km": 12000,
        "impact_area": "Grip, stability, braking, and puncture resilience",
        "performance_effect": "Tyre wear or poor wheel condition affects grip, wet braking, and steering stability.",
        "recommended_action": "Track tyre wear and balancing closely before highway or loaded rides.",
    },
    {
        "key": "battery",
        "label": "Battery And Charging",
        "system": "electrical",
        "keywords": ["battery", "charging", "self start", "starter", "terminal", "voltage"],
        "condition_field": "battery_status",
        "service_window_days": 365,
        "service_window_km": 12000,
        "impact_area": "Starting reliability, lights, and electrical stability",
        "performance_effect": "Weak battery or charging health causes hard starts, dim lighting, and intermittent electrical behavior.",
        "recommended_action": "Check battery voltage and charging output if starts feel weaker or lights dip noticeably.",
    },
    {
        "key": "spark_plug",
        "label": "Spark Plug And Tune",
        "system": "electrical",
        "keywords": ["spark plug", "plug change", "ignition", "misfire", "rough idle", "tune"],
        "condition_field": "engine_status",
        "service_window_days": 240,
        "service_window_km": 8000,
        "impact_area": "Combustion quality, idle smoothness, and cold-start behavior",
        "performance_effect": "Poor ignition tune can reduce mileage and make idle or morning starts inconsistent.",
        "recommended_action": "Inspect spark plug condition and tune state when starts, idle, or pickup begin to degrade.",
    },
]

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
CONDITION_SCORES = {"good": 92, "watch": 74, "service": 56, "urgent": 34}
CONDITION_ORDER = {"good": 1, "watch": 2, "service": 3, "urgent": 4}
REQUIRED_DOCUMENT_TYPES = ("registration", "insurance", "puc")
DOCUMENT_TYPE_LABELS = {
    "registration": "Registration / RC",
    "insurance": "Insurance",
    "puc": "PUC",
}
VEHICLE_NUMBER_PATTERNS = (
    re.compile(r"^[A-Z]{2}\d{1,2}[A-Z]{1,3}\d{4}$"),
    re.compile(r"^\d{2}BH\d{4}[A-Z]{2}$"),
)


class BikeServiceIntelligenceService:
    def build_dashboard(self, user) -> dict:
        return materialize_payload(
            namespace="bike-service-dashboard",
            user_id=user.id,
            revision=self._dashboard_revision(user),
            ttl_seconds=45,
            builder=lambda: self._build_dashboard_uncached(user),
        )

    def _build_dashboard_uncached(self, user) -> dict:
        today = timezone.localdate()
        now = timezone.now()
        bike_profiles = list(BikeProfile.objects.filter(user=user).order_by("-is_primary", "-updated_at"))
        primary_profile = bike_profiles[0] if bike_profiles else None
        service_records = list(
            BikeServiceRecord.objects.filter(user=user)
            .select_related("bike_profile")
            .order_by("-service_date", "-id")
        )
        issues = list(
            BikeIssueReport.objects.filter(user=user)
            .select_related("bike_profile", "bike_service", "travel_plan")
            .order_by("-reported_at", "-id")
        )
        trip_logs = list(
            TripLog.objects.filter(user=user)
            .select_related("travel_plan", "travel_plan__vehicle_profile")
            .order_by("-log_date", "-id")
        )
        refill_logs = list(
            FuelRefillLog.objects.filter(user=user)
            .select_related("bike_profile")
            .order_by("-refill_date", "-id")
        )
        documents = list(BikeDocument.objects.filter(user=user).select_related("bike_profile").order_by("expiry_date", "-id"))
        condition_snapshots = list(BikeConditionSnapshot.objects.filter(user=user).select_related("bike_profile").order_by("-captured_at", "-id"))

        if primary_profile:
            scoped_service_records = [item for item in service_records if item.bike_profile_id == primary_profile.id or not item.bike_profile_id]
            scoped_issues = [
                item for item in issues
                if item.bike_profile_id == primary_profile.id
                or (item.bike_service and item.bike_service.bike_profile_id == primary_profile.id)
                or (not item.bike_profile_id and not getattr(item.bike_service, "bike_profile_id", None))
            ]
            scoped_trip_logs = [
                item for item in trip_logs
                if getattr(item.travel_plan, "vehicle_profile_id", None) in {None, primary_profile.id}
            ]
            scoped_refill_logs = [item for item in refill_logs if item.bike_profile_id == primary_profile.id or not item.bike_profile_id]
            scoped_documents = [item for item in documents if item.bike_profile_id == primary_profile.id or not item.bike_profile_id]
            scoped_condition_snapshots = [item for item in condition_snapshots if item.bike_profile_id == primary_profile.id or not item.bike_profile_id]
        else:
            scoped_service_records = service_records
            scoped_issues = issues
            scoped_trip_logs = trip_logs
            scoped_refill_logs = refill_logs
            scoped_documents = documents
            scoped_condition_snapshots = condition_snapshots

        current_documents = self._current_documents(scoped_documents)

        open_issues = [item for item in scoped_issues if item.status != "resolved"]
        critical_issues = [item for item in open_issues if item.severity in {"high", "critical"}]
        latest_service = scoped_service_records[0] if scoped_service_records else None
        latest_condition = scoped_condition_snapshots[0] if scoped_condition_snapshots else None
        total_service_cost = round(sum(item.cost or 0 for item in scoped_service_records), 2)
        annual_service_cost = round(sum(item.cost or 0 for item in scoped_service_records if (today - item.service_date).days <= 365), 2)
        trip_cost_total = round(sum(item.spend_amount or 0 for item in scoped_trip_logs), 2)
        trip_distance_total = round(sum(item.distance_km or 0 for item in scoped_trip_logs), 1)
        cost_per_km = round(trip_cost_total / trip_distance_total, 2) if trip_distance_total else 0
        projected_next_service_cost = round(self._routine_service_baseline(scoped_service_records, profile=primary_profile) + sum(self._issue_cost(issue, scoped_issues) for issue in open_issues[:3]), 2)
        document_summary = self._document_summary(current_documents, today)
        modification_summary = self._detect_modifications(scoped_service_records, scoped_issues)
        expected_mileage = primary_profile.expected_mileage_kmpl if primary_profile and primary_profile.expected_mileage_kmpl else 0
        estimated_range = round(expected_mileage * (primary_profile.fuel_tank_capacity_l or 0), 1) if primary_profile else 0
        valid_refill_logs = [item for item in scoped_refill_logs if self._refill_actual_mileage(item) is not None]
        latest_actual_mileage = self._refill_actual_mileage(valid_refill_logs[0]) if valid_refill_logs else 0
        average_actual_mileage = round(mean(self._refill_actual_mileage(item) for item in valid_refill_logs), 2) if valid_refill_logs else 0
        mileage_gap = round(average_actual_mileage - expected_mileage, 2) if average_actual_mileage and expected_mileage else 0
        service_history_summary = self._build_service_history_summary(scoped_service_records, scoped_documents, scoped_condition_snapshots, scoped_refill_logs)
        part_insights = self._build_part_insights(scoped_service_records, scoped_issues, latest_condition, latest_service, today)

        pending_tasks = self._build_pending_tasks(latest_service, open_issues, current_documents, latest_condition, today, now)
        observations = self._build_observations(
            scoped_service_records,
            scoped_issues,
            trip_cost_total,
            cost_per_km,
            document_summary,
            latest_condition,
            scoped_refill_logs,
            expected_mileage,
            average_actual_mileage,
        )
        service_center_brief = self._build_service_center_brief(open_issues, latest_service, latest_condition)
        bike_profile = self._build_bike_profile(primary_profile, latest_service, current_documents, latest_condition, modification_summary, estimated_range)
        document_compliance = self._build_document_compliance(current_documents, today)

        return {
            "summary": {
                "managed_vehicle_count": len(bike_profiles),
                "service_count": len(scoped_service_records),
                "total_service_cost": total_service_cost,
                "annual_service_cost": annual_service_cost,
                "trip_cost_total": trip_cost_total,
                "trip_distance_total": trip_distance_total,
                "trip_cost_per_km": cost_per_km,
                "open_faults": len(open_issues),
                "critical_faults": len(critical_issues),
                "projected_next_service_cost": projected_next_service_cost,
                "next_service_date": latest_service.next_service_date.isoformat() if latest_service and latest_service.next_service_date else "",
                "next_service_km": latest_service.next_service_km if latest_service else None,
                "valid_documents": document_summary["valid_count"],
                "expiring_documents": document_summary["expiring_soon_count"],
                "expired_documents": document_summary["expired_count"],
                "insurance_expiry": document_summary["insurance_expiry"],
                "puc_expiry": document_summary["puc_expiry"],
                "missing_required_documents": document_summary["missing_required_count"],
                "document_compliance_score": document_summary["compliance_score"],
                "expected_mileage_kmpl": expected_mileage,
                "latest_actual_mileage_kmpl": latest_actual_mileage,
                "average_actual_mileage_kmpl": average_actual_mileage,
                "mileage_gap_kmpl": mileage_gap,
                "estimated_range_km": estimated_range,
                "refill_count": len(scoped_refill_logs),
                "fuel_cost_total": round(sum(item.total_cost or 0 for item in scoped_refill_logs), 2),
                "latest_condition_score": latest_condition.overall_score if latest_condition else 0,
                "latest_condition_status": latest_condition.get_overall_status_display() if latest_condition else "No data",
            },
            "bike_profile": bike_profile,
            "fleet_summary": self._build_fleet_summary(bike_profiles, service_records, documents),
            "pending_tasks": pending_tasks,
            "observations": observations,
            "suggestions": self._build_suggestions(open_issues, latest_service),
            "service_center_brief": service_center_brief,
            "charts": self._build_charts(
                scoped_service_records,
                scoped_trip_logs,
                scoped_issues,
                scoped_condition_snapshots,
                scoped_refill_logs,
                expected_mileage,
                getattr(primary_profile, "official_source_name", ""),
                getattr(primary_profile, "official_source_url", ""),
            ),
            "document_summary": document_summary,
            "document_compliance": document_compliance,
            "service_history_summary": service_history_summary,
            "part_insights": part_insights,
        }

    def risk_snapshot(self, user) -> dict:
        return materialize_payload(
            namespace="bike-service-risk-snapshot",
            user_id=user.id,
            revision=self._dashboard_revision(user),
            ttl_seconds=30,
            builder=lambda: self._risk_snapshot_uncached(user),
        )

    def _risk_snapshot_uncached(self, user) -> dict:
        today = timezone.localdate()
        now = timezone.now()
        bike_profiles = list(
            BikeProfile.objects.filter(user=user)
            .only("id", "is_primary", "updated_at")
            .order_by("-is_primary", "-updated_at")[:12]
        )
        primary_profile = bike_profiles[0] if bike_profiles else None

        service_filter = Q(user=user)
        issue_filter = Q(user=user)
        trip_filter = Q(user=user)
        document_queryset = BikeDocument.objects.filter(user=user)
        condition_queryset = BikeConditionSnapshot.objects.filter(user=user)

        if primary_profile:
            service_filter &= Q(bike_profile_id=primary_profile.id) | Q(bike_profile__isnull=True)
            issue_filter &= (
                Q(bike_profile_id=primary_profile.id)
                | Q(bike_service__bike_profile_id=primary_profile.id)
                | (Q(bike_profile__isnull=True) & Q(bike_service__bike_profile__isnull=True))
            )
            trip_filter &= Q(travel_plan__vehicle_profile_id=primary_profile.id) | Q(travel_plan__vehicle_profile__isnull=True)
            document_queryset = document_queryset.filter(Q(bike_profile_id=primary_profile.id) | Q(bike_profile__isnull=True))
            condition_queryset = condition_queryset.filter(Q(bike_profile_id=primary_profile.id) | Q(bike_profile__isnull=True))

        latest_service = (
            BikeServiceRecord.objects.filter(service_filter)
            .only("service_date", "next_service_date", "next_service_km", "odometer_km", "bike_name")
            .order_by("-service_date", "-id")
            .first()
        )
        latest_condition = (
            condition_queryset
            .only("captured_at", "overall_status", "overall_score", "ai_assessment")
            .order_by("-captured_at", "-id")
            .first()
        )
        open_issues = list(
            BikeIssueReport.objects.filter(issue_filter)
            .exclude(status="resolved")
            .only("title", "severity", "next_action_at", "suggested_action", "symptom", "reported_at")
            .order_by("-reported_at", "-id")[:5]
        )
        current_documents = self._current_documents(
            list(
                document_queryset
                .only("document_type", "expiry_date", "verification_status", "verification_notes", "document_number", "bike_name", "vehicle_number", "bike_profile_id", "updated_at", "created_at")
                .order_by("expiry_date", "-id")
            )
        )
        document_summary = self._document_summary(current_documents, today)
        pending_tasks = self._build_pending_tasks(latest_service, open_issues, current_documents, latest_condition, today, now)

        critical_faults = sum(1 for item in open_issues if item.severity in {"high", "critical"})
        service_count = BikeServiceRecord.objects.filter(service_filter).count()
        managed_trip_count = TripLog.objects.filter(trip_filter).count()

        return {
            "summary": {
                "managed_vehicle_count": len(bike_profiles),
                "service_count": service_count,
                "managed_trip_count": managed_trip_count,
                "open_faults": len(open_issues),
                "critical_faults": critical_faults,
                "expiring_documents": document_summary["expiring_soon_count"],
                "expired_documents": document_summary["expired_count"],
                "missing_required_documents": document_summary["missing_required_count"],
                "document_compliance_score": document_summary["compliance_score"],
                "latest_condition_score": latest_condition.overall_score if latest_condition else 0,
                "latest_condition_status": latest_condition.get_overall_status_display() if latest_condition else "No data",
            },
            "pending_tasks": pending_tasks,
        }

    def _dashboard_revision(self, user) -> str:
        profile_meta = BikeProfile.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        service_meta = BikeServiceRecord.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("service_date"))
        issue_meta = BikeIssueReport.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_reported=Max("reported_at"))
        trip_meta = TripLog.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("log_date"))
        refill_meta = FuelRefillLog.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_date=Max("refill_date"))
        document_meta = BikeDocument.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
        condition_meta = BikeConditionSnapshot.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_captured=Max("captured_at"))
        return "|".join(
            str(value or "")
            for value in [
                profile_meta["count"], profile_meta["max_id"], profile_meta["max_updated"],
                service_meta["count"], service_meta["max_id"], service_meta["max_date"],
                issue_meta["count"], issue_meta["max_id"], issue_meta["max_reported"],
                trip_meta["count"], trip_meta["max_id"], trip_meta["max_date"],
                refill_meta["count"], refill_meta["max_id"], refill_meta["max_date"],
                document_meta["count"], document_meta["max_id"], document_meta["max_updated"],
                condition_meta["count"], condition_meta["max_id"], condition_meta["max_captured"],
            ]
        )

    def hydrate_issue(self, issue: BikeIssueReport) -> BikeIssueReport:
        rule = self._match_rule(issue.title, issue.symptom, issue.observation, issue.system)
        history = list(BikeIssueReport.objects.filter(user=issue.user, system=issue.system).exclude(pk=issue.pk))

        if rule:
            issue.system = issue.system if issue.system != "general" else rule["system"]
            if not issue.probable_cause:
                issue.probable_cause = rule["probable_cause"]
            if not issue.suggested_action:
                issue.suggested_action = rule["suggested_action"]
            if not issue.service_center_note:
                issue.service_center_note = rule["service_center_note"]
            if not issue.tags:
                issue.tags = ", ".join(rule["tags"])
            if not issue.projected_cost:
                issue.projected_cost = self._blend_cost(rule["cost_range"], history)

        if issue.status != "resolved" and issue.next_action_at is None:
            hours = {"critical": 12, "high": 48, "medium": 168, "low": 336}.get(issue.severity, 168)
            issue.next_action_at = timezone.now() + timedelta(hours=hours)

        issue.save()
        return issue

    def hydrate_document(self, document: BikeDocument) -> BikeDocument:
        today = timezone.localdate()
        notes = []
        required_fields = []

        if document.document_type in REQUIRED_DOCUMENT_TYPES and not document.document_number:
            required_fields.append("document number")
        if document.document_type in REQUIRED_DOCUMENT_TYPES and not document.vehicle_number:
            required_fields.append("vehicle number")
        if document.document_type in {"insurance", "puc"} and not document.expiry_date:
            required_fields.append("expiry date")

        if required_fields:
            document.verification_status = "incomplete"
            notes.append(f"Missing {', '.join(required_fields)} for reliable verification.")
        else:
            if document.expiry_date:
                days_left = (document.expiry_date - today).days
                if days_left < 0:
                    document.verification_status = "expired"
                    notes.append(f"Expired {abs(days_left)} day(s) ago.")
                elif days_left <= 30:
                    document.verification_status = "expiring_soon"
                    notes.append(f"Expires in {days_left} day(s).")
                else:
                    document.verification_status = "valid"
                    notes.append(f"Valid for another {days_left} day(s).")
            else:
                document.verification_status = "valid"
                notes.append("Core document details are captured.")

        if document.vehicle_number and not self._looks_like_indian_vehicle_number(document.vehicle_number):
            notes.append("Vehicle number format looks unusual. Verify it against the RC.")
        if document.document_type == "insurance" and not document.issuer:
            notes.append("Add the insurer name to improve policy tracking.")
        if document.document_type == "insurance" and not document.premium_amount:
            notes.append("Premium amount is not logged yet.")
        if document.document_file:
            notes.append("Source document uploaded.")

        document.verification_notes = " ".join(notes).strip()
        document.save()
        return document

    def hydrate_condition(self, snapshot: BikeConditionSnapshot, user) -> BikeConditionSnapshot:
        states = [
            snapshot.engine_status,
            snapshot.brake_status,
            snapshot.tyre_status,
            snapshot.battery_status,
            snapshot.body_status,
        ]
        status = max(states, key=lambda value: CONDITION_ORDER.get(value, 1))
        scores = [CONDITION_SCORES.get(value, 80) for value in states]
        open_issues = BikeIssueReport.objects.filter(user=user, status__in=["pending", "monitor", "in_service"])
        issue_penalty = min(open_issues.count() * 3, 15)
        snapshot.overall_status = status
        snapshot.overall_score = max(15, round(mean(scores) - issue_penalty))

        concerns = []
        if snapshot.brake_status in {"service", "urgent"}:
            concerns.append("Brake inspection should be prioritized.")
        if snapshot.tyre_status in {"service", "urgent"}:
            concerns.append("Tyre wear or pressure needs attention before long rides.")
        if snapshot.battery_status in {"service", "urgent"}:
            concerns.append("Battery or charging health should be tested.")
        if snapshot.engine_status in {"service", "urgent"}:
            concerns.append("Engine service is recommended based on the current snapshot.")
        if not concerns:
            concerns.append("Current condition snapshot suggests the bike is stable for regular use.")

        snapshot.ai_assessment = " ".join(concerns[:3])
        snapshot.save()
        return snapshot

    def current_documents(self, documents: list[BikeDocument]) -> list[BikeDocument]:
        return self._current_documents(documents)

    def _routine_service_baseline(self, service_records: list[BikeServiceRecord], *, profile=None) -> float:
        routine_costs = [item.cost for item in service_records if item.service_type == "routine" and item.cost]
        heuristic = round(mean(routine_costs[-3:]), 2) if routine_costs else 1800.0
        latest_record = next((item for item in service_records if item.cost), service_records[0] if service_records else None)
        if latest_record is None:
            return heuristic

        active_profile = profile or getattr(latest_record, "bike_profile", None)
        service_payload = ((latest_record.parsed_payload or {}).get("service_payload") or {})
        parts_items = service_payload.get("parts_items") or []
        labour_items = service_payload.get("labour_items") or []
        predicted = service_cost_predictor.predict_cost(
            {
                "vehicle_type_score": vehicle_type_score(getattr(active_profile, "vehicle_type", "")),
                "service_type_score": service_type_score("routine"),
                "odometer_band": round(float(latest_record.odometer_km or 0) / 10000.0, 4),
                "engine_cc_band": round(float(getattr(active_profile, "engine_cc", 0) or 0) / 100.0, 4),
                "expected_mileage_band": round(float(getattr(active_profile, "expected_mileage_kmpl", 0) or 0) / 10.0, 4),
                "line_item_count": int(service_payload.get("line_item_count") or len(parts_items) + len(labour_items) or 0),
                "parts_item_count": int(service_payload.get("parts_item_count") or len(parts_items)),
                "labour_item_count": int(service_payload.get("labour_item_count") or len(labour_items)),
                "recent_average_cost": heuristic if routine_costs else 0.0,
            }
        )
        if predicted is None:
            return heuristic
        if routine_costs:
            return round((heuristic * 0.55) + (predicted * 0.45), 2)
        return round(predicted, 2)

    def _issue_cost(self, issue: BikeIssueReport, issues: list[BikeIssueReport]) -> float:
        if issue.projected_cost:
            return issue.projected_cost
        rule = self._match_rule(issue.title, issue.symptom, issue.observation, issue.system)
        return self._blend_cost(rule["cost_range"], [item for item in issues if item.system == issue.system]) if rule else 800.0

    def _blend_cost(self, cost_range: tuple[int, int], history: list[BikeIssueReport]) -> float:
        historical_costs = [item.actual_cost for item in history if item.actual_cost]
        midpoint = (cost_range[0] + cost_range[1]) / 2
        if historical_costs:
            return round((mean(historical_costs[-3:]) * 0.65) + (midpoint * 0.35), 2)
        return round(midpoint, 2)

    def _match_rule(self, *parts: str) -> dict | None:
        haystack = " ".join(part.lower() for part in parts if part)
        if not haystack:
            return None
        for rule in SERVICE_RULES:
            if any(keyword in haystack for keyword in rule["keywords"]):
                return rule
        return None

    def _build_pending_tasks(self, latest_service, open_issues, documents, latest_condition, today, now) -> list[dict]:
        tasks = []
        if latest_service and latest_service.next_service_date:
            days_left = (latest_service.next_service_date - today).days
            tasks.append(
                {
                    "title": f"{latest_service.bike_name} scheduled service",
                    "priority": "high" if days_left <= 7 else ("medium" if days_left <= 30 else "low"),
                    "due_at": latest_service.next_service_date.isoformat(),
                    "note": f"Next due date is {latest_service.next_service_date.isoformat()} and target km is {latest_service.next_service_km or 'not set'}.",
                }
            )
        if latest_service and latest_service.next_service_km and latest_service.odometer_km:
            km_left = latest_service.next_service_km - latest_service.odometer_km
            tasks.append(
                {
                    "title": "Odometer service checkpoint",
                    "priority": "high" if km_left <= 250 else ("medium" if km_left <= 750 else "low"),
                    "due_at": "",
                    "note": f"{max(km_left, 0)} km remain before the next logged service checkpoint.",
                }
            )
        for issue in open_issues[:5]:
            tasks.append(
                {
                    "title": issue.title,
                    "priority": issue.severity,
                    "due_at": issue.next_action_at.isoformat() if issue.next_action_at else "",
                    "note": issue.suggested_action or issue.symptom,
                }
            )
        for document in documents[:6]:
            if not document.expiry_date:
                if document.verification_status == "incomplete":
                    tasks.append(
                        {
                            "title": f"Complete {document.get_document_type_display()} record",
                            "priority": "medium",
                            "due_at": "",
                            "note": document.verification_notes or "Add missing dates or document number.",
                        }
                    )
                continue
            days_left = (document.expiry_date - today).days
            if days_left <= 45:
                tasks.append(
                    {
                        "title": f"{document.get_document_type_display()} renewal",
                        "priority": "critical" if days_left < 0 else ("high" if days_left <= 7 else "medium"),
                        "due_at": document.expiry_date.isoformat(),
                        "note": document.verification_notes or f"Document for {document.bike_name} needs review.",
                    }
                )
        if latest_condition and latest_condition.overall_status in {"service", "urgent"}:
            tasks.append(
                {
                    "title": "Condition-led preventive inspection",
                    "priority": "high" if latest_condition.overall_status == "service" else "critical",
                    "due_at": latest_condition.captured_at.isoformat(),
                    "note": latest_condition.ai_assessment or "Recent condition snapshot suggests a deeper inspection.",
                }
            )
        tasks.sort(key=lambda item: SEVERITY_ORDER.get(item["priority"], 0), reverse=True)
        return tasks[:6]

    def _build_observations(
        self,
        service_records,
        issues,
        trip_cost_total,
        cost_per_km,
        document_summary,
        latest_condition,
        refill_logs,
        expected_mileage,
        average_actual_mileage,
    ) -> list[str]:
        observations = []
        if service_records:
            observations.append(f"Total logged bike service spend is INR {sum(item.cost or 0 for item in service_records):,.0f}.")
        if trip_cost_total:
            observations.append(f"Trip logs currently capture INR {trip_cost_total:,.0f} of ride spend at roughly INR {cost_per_km:,.2f} per km.")
        if refill_logs:
            observations.append(f"Fuel refill history now covers {len(refill_logs)} refill log(s), so Alfred can compare your real mileage against the expected benchmark.")
        if average_actual_mileage and expected_mileage:
            if average_actual_mileage < (expected_mileage * 0.9):
                observations.append(f"Average actual mileage is about {average_actual_mileage:,.1f} kmpl versus the benchmark {expected_mileage:,.1f} kmpl, which suggests below-optimal efficiency.")
            elif average_actual_mileage > (expected_mileage * 1.05):
                observations.append(f"Average actual mileage is about {average_actual_mileage:,.1f} kmpl, which is outperforming the saved benchmark of {expected_mileage:,.1f} kmpl.")
        recurring_systems = Counter(item.system for item in issues if item.system != "general")
        if recurring_systems:
            system, count = recurring_systems.most_common(1)[0]
            if count >= 2:
                observations.append(f"{system.title()} issues have recurred {count} times, so that system should be inspected more deeply.")
        if issues and any(item.severity == "critical" for item in issues if item.status != "resolved"):
            observations.append("At least one critical issue is still open and should be escalated before a long ride.")
        if document_summary["expired_count"]:
            observations.append(f"{document_summary['expired_count']} bike document(s) are already expired.")
        elif document_summary["expiring_soon_count"]:
            observations.append(f"{document_summary['expiring_soon_count']} bike document(s) will expire soon and should be renewed proactively.")
        if latest_condition:
            observations.append(f"Latest condition snapshot is {latest_condition.get_overall_status_display().lower()} with a score of {latest_condition.overall_score}/100.")
        if not observations:
            observations.append("Log more service jobs or fault reports to let the advisor learn your bike's maintenance pattern.")
        return observations[:5]

    def _build_suggestions(self, open_issues, latest_service) -> list[str]:
        suggestions = []
        if latest_service and latest_service.notes:
            suggestions.append(f"Use the last service note as a baseline: {latest_service.notes[:140]}")
        for issue in open_issues[:3]:
            if issue.suggested_action:
                suggestions.append(issue.suggested_action)
        if not suggestions:
            suggestions.append("Capture a fault report whenever you hear a new sound, feel vibration, or notice braking or starting changes.")
        return suggestions[:4]

    def _build_service_center_brief(self, open_issues, latest_service, latest_condition) -> dict:
        top_issues = sorted(open_issues, key=lambda item: SEVERITY_ORDER.get(item.severity, 0), reverse=True)[:3]
        opening = "Please inspect the bike with focus on the items below and confirm parts, labour, and whether the issue is urgent."
        talking_points = [issue.service_center_note or issue.title for issue in top_issues]
        if latest_service and latest_service.notes:
            talking_points.append(f"Previous service note: {latest_service.notes}")
        if latest_condition and latest_condition.ai_assessment:
            talking_points.append(f"Current condition snapshot: {latest_condition.ai_assessment}")
        if not talking_points:
            talking_points.append("Please perform a preventive inspection covering chain slack, brakes, tyres, battery, and fluid condition.")
        return {
            "opening": opening,
            "talking_points": talking_points[:4],
            "projected_total": round(sum(issue.projected_cost or 0 for issue in top_issues), 2),
        }

    def _build_service_history_summary(self, service_records, documents, condition_snapshots, refill_logs) -> dict:
        imported_bills = sum(1 for item in service_records if item.source_mode in {"bill_import", "work_note"})
        manual_logs = sum(1 for item in service_records if item.source_mode == "manual")
        average_cost = round(mean([item.cost for item in service_records if item.cost]), 2) if any(item.cost for item in service_records) else 0.0
        recurring_centers = [center for center, _ in Counter(item.service_center for item in service_records if item.service_center).most_common(2)]
        return {
            "total_service_logs": len(service_records),
            "imported_service_bills": imported_bills,
            "manual_service_logs": manual_logs,
            "average_service_cost": average_cost,
            "document_count": len(documents),
            "condition_snapshot_count": len(condition_snapshots),
            "fuel_refill_count": len(refill_logs),
            "recurring_centers": recurring_centers,
            "history_note": (
                "Imported service bills, manual logs, and refill history are all retained, so Alfred can build a longer maintenance and mileage history for this vehicle."
                if (service_records or refill_logs)
                else "Start by importing a service bill, adding a manual service log, or storing a fuel refill to build maintenance history."
            ),
        }

    def _build_part_insights(self, service_records, issues, latest_condition, latest_service, today) -> list[dict]:
        current_odometer = (
            latest_condition.odometer_km
            if latest_condition and latest_condition.odometer_km is not None
            else (latest_service.odometer_km if latest_service and latest_service.odometer_km is not None else None)
        )
        open_issues = [item for item in issues if item.status != "resolved"]
        insights = []

        for rule in PART_RULES:
            matched_services = [
                record for record in service_records
                if any(keyword in self._service_record_text(record) for keyword in rule["keywords"])
            ]
            matched_issues = [
                issue for issue in open_issues
                if issue.system == rule["system"] or any(keyword in self._issue_text(issue) for keyword in rule["keywords"])
            ]
            latest_part_service = matched_services[0] if matched_services else None
            condition_value = getattr(latest_condition, rule["condition_field"], "") if latest_condition and rule["condition_field"] else ""
            days_since = (today - latest_part_service.service_date).days if latest_part_service else None
            km_since = (
                max((current_odometer or 0) - (latest_part_service.odometer_km or 0), 0)
                if latest_part_service and current_odometer is not None and latest_part_service.odometer_km is not None
                else None
            )
            due_by_days = bool(days_since is not None and rule["service_window_days"] and days_since >= rule["service_window_days"])
            due_by_km = bool(km_since is not None and rule["service_window_km"] and km_since >= rule["service_window_km"])
            warning_by_days = bool(days_since is not None and rule["service_window_days"] and days_since >= (rule["service_window_days"] * 0.7))
            warning_by_km = bool(km_since is not None and rule["service_window_km"] and km_since >= (rule["service_window_km"] * 0.7))
            severe_issue = any(item.severity in {"high", "critical"} for item in matched_issues)

            if severe_issue or condition_value == "urgent":
                status = "urgent"
            elif matched_issues or condition_value == "service" or due_by_days or due_by_km:
                status = "service"
            elif condition_value == "watch" or warning_by_days or warning_by_km:
                status = "watch"
            else:
                status = "good" if latest_part_service else "watch"

            evidence = []
            if latest_part_service:
                evidence.append(f"Last logged on {latest_part_service.service_date.isoformat()}.")
            else:
                evidence.append("No direct part-level service evidence has been logged yet.")
            if matched_issues:
                evidence.append(f"{len(matched_issues)} open issue signal(s) are tied to this area.")
            if days_since is not None:
                evidence.append(f"{days_since} day(s) since the last logged part-specific service.")
            if km_since is not None:
                evidence.append(f"{km_since} km since the last logged part-specific service.")
            if condition_value:
                evidence.append(f"Latest condition snapshot marks this area as {condition_value}.")

            confidence = 0.28
            if latest_part_service:
                confidence += 0.28
            if matched_issues:
                confidence += min(len(matched_issues) * 0.12, 0.24)
            if condition_value:
                confidence += 0.16

            insights.append(
                {
                    "label": rule["label"],
                    "status": status,
                    "status_label": {"good": "Stable", "watch": "Watch", "service": "Service Soon", "urgent": "Urgent"}[status],
                    "impact_area": rule["impact_area"],
                    "performance_effect": rule["performance_effect"],
                    "recommended_action": rule["recommended_action"],
                    "last_service_date": latest_part_service.service_date.isoformat() if latest_part_service else "",
                    "last_service_cost": round(latest_part_service.cost or 0, 2) if latest_part_service else 0,
                    "service_count": len(matched_services),
                    "issue_count": len(matched_issues),
                    "days_since_service": days_since,
                    "km_since_service": km_since,
                    "confidence": round(min(confidence, 0.96), 2),
                    "evidence": evidence[:3],
                }
            )

        insights.sort(key=lambda item: CONDITION_ORDER.get(item["status"], 0), reverse=True)
        return insights[:6]

    def _refill_actual_mileage(self, refill_log: FuelRefillLog):
        if not refill_log or not refill_log.fuel_liters or not refill_log.trip_meter_km:
            return None
        if refill_log.fuel_liters <= 0 or refill_log.trip_meter_km <= 0:
            return None
        return round(refill_log.trip_meter_km / refill_log.fuel_liters, 2)

    def _build_mileage_trend(self, refill_logs, expected_mileage, source_name, source_url) -> dict:
        eligible_logs = [item for item in reversed(refill_logs[:10]) if self._refill_actual_mileage(item) is not None]
        actual_values = [self._refill_actual_mileage(item) for item in eligible_logs]
        return {
            "labels": [item.refill_date.strftime("%d %b") for item in eligible_logs],
            "actual_values": actual_values,
            "optimal_values": [round(expected_mileage or 0, 2)] * len(actual_values),
            "variance_values": [round(actual - (expected_mileage or 0), 2) for actual in actual_values],
            "evidence_kind": "official_catalog" if source_url else "custom_profile",
            "source_name": source_name,
            "source_url": source_url,
        }

    def _build_charts(self, service_records, trip_logs, issues, condition_snapshots, refill_logs, expected_mileage, source_name, source_url) -> dict:
        service_chart = {
            "labels": [item.service_date.isoformat() for item in reversed(service_records[:8])],
            "values": [round(item.cost or 0, 2) for item in reversed(service_records[:8])],
        }

        monthly = defaultdict(lambda: {"service": 0.0, "trip": 0.0})
        for item in service_records[:12]:
            key = (item.service_date.year, item.service_date.month)
            monthly[key]["service"] += item.cost or 0
        for item in trip_logs[:24]:
            key = (item.log_date.year, item.log_date.month)
            monthly[key]["trip"] += item.spend_amount or 0
        ordered_keys = sorted(monthly.keys())[-6:]
        month_labels = [datetime(year, month, 1).strftime("%b %Y") for year, month in ordered_keys]
        cost_mix = {
            "labels": month_labels,
            "service_values": [round(monthly[key]["service"], 2) for key in ordered_keys],
            "trip_values": [round(monthly[key]["trip"], 2) for key in ordered_keys],
        }

        severity_counts = Counter(item.severity for item in issues if item.status != "resolved")
        issue_chart = {
            "labels": ["Low", "Medium", "High", "Critical"],
            "values": [severity_counts.get("low", 0), severity_counts.get("medium", 0), severity_counts.get("high", 0), severity_counts.get("critical", 0)],
        }
        return {
            "service_cost_trend": service_chart,
            "cost_mix": cost_mix,
            "issue_breakdown": issue_chart,
            "mileage_trend": self._build_mileage_trend(refill_logs, expected_mileage, source_name, source_url),
        }

    def _document_summary(self, documents: list[BikeDocument], today) -> dict:
        documents_by_type = {document.document_type: document for document in documents}
        insurance_expiry = ""
        puc_expiry = ""
        valid_count = 0
        expiring_soon_count = 0
        expired_count = 0

        for document in documents:
            if document.verification_status == "valid":
                valid_count += 1
            elif document.verification_status == "expiring_soon":
                expiring_soon_count += 1
            elif document.verification_status == "expired":
                expired_count += 1

            if document.document_type == "insurance" and document.expiry_date and not insurance_expiry:
                insurance_expiry = document.expiry_date.isoformat()
            if document.document_type == "puc" and document.expiry_date and not puc_expiry:
                puc_expiry = document.expiry_date.isoformat()

        compliance_points = []
        for document_type in REQUIRED_DOCUMENT_TYPES:
            document = documents_by_type.get(document_type)
            if document is None:
                compliance_points.append(0)
                continue
            compliance_points.append(
                {
                    "valid": 100,
                    "expiring_soon": 70,
                    "incomplete": 35,
                    "expired": 0,
                }.get(document.verification_status, 0)
            )

        return {
            "valid_count": valid_count,
            "expiring_soon_count": expiring_soon_count,
            "expired_count": expired_count,
            "insurance_expiry": insurance_expiry,
            "puc_expiry": puc_expiry,
            "missing_required_count": sum(1 for document_type in REQUIRED_DOCUMENT_TYPES if document_type not in documents_by_type),
            "compliance_score": round(sum(compliance_points) / max(len(REQUIRED_DOCUMENT_TYPES), 1)),
        }

    def _build_bike_profile(self, primary_profile, latest_service, current_documents, latest_condition, modification_summary, estimated_range) -> dict:
        documents_by_type = {document.document_type: document for document in current_documents}
        source = primary_profile or latest_service or latest_condition or next(iter(current_documents), None)
        insurance = documents_by_type.get("insurance")
        puc = documents_by_type.get("puc")
        registration = documents_by_type.get("registration")
        maintenance_guidance = build_maintenance_guidance(
            {
                "make": getattr(primary_profile, "make", ""),
                "vehicle_type": getattr(primary_profile, "vehicle_type", ""),
                "bike_class": getattr(primary_profile, "bike_class", ""),
                "service_interval_km": getattr(primary_profile, "service_interval_km", None),
                "service_interval_days": getattr(primary_profile, "service_interval_days", None),
                "official_source_name": getattr(primary_profile, "official_source_name", ""),
                "official_source_url": getattr(primary_profile, "official_source_url", ""),
            }
        )
        return {
            "id": getattr(primary_profile, "id", None),
            "bike_name": getattr(source, "display_name", getattr(source, "bike_name", "")),
            "model_name": getattr(primary_profile, "model_name", ""),
            "variant": getattr(primary_profile, "variant", ""),
            "vehicle_type": getattr(primary_profile, "get_vehicle_type_display", lambda: "")(),
            "vehicle_number": getattr(source, "vehicle_number", ""),
            "make": getattr(primary_profile, "make", ""),
            "bike_class": getattr(primary_profile, "bike_class", ""),
            "fuel_type": getattr(primary_profile, "fuel_type", ""),
            "usage_pattern": getattr(primary_profile, "get_usage_pattern_display", lambda: "")(),
            "estimated_market_value": getattr(primary_profile, "estimated_market_value", 0),
            "monthly_income_support": getattr(primary_profile, "monthly_income_support", 0),
            "engine_cc": getattr(primary_profile, "engine_cc", None),
            "fuel_tank_capacity_l": getattr(primary_profile, "fuel_tank_capacity_l", None),
            "expected_mileage_kmpl": getattr(primary_profile, "expected_mileage_kmpl", None),
            "estimated_range_km": estimated_range,
            "service_interval_km": getattr(primary_profile, "service_interval_km", None),
            "service_interval_days": getattr(primary_profile, "service_interval_days", None),
            "optimal_cruising_speed_kmph": getattr(primary_profile, "optimal_cruising_speed_kmph", None),
            "verification_status": getattr(primary_profile, "get_verification_status_display", lambda: "")(),
            "official_source_name": getattr(primary_profile, "official_source_name", ""),
            "official_source_url": getattr(primary_profile, "official_source_url", ""),
            "last_service_date": latest_service.service_date.isoformat() if latest_service else "",
            "next_service_date": latest_service.next_service_date.isoformat() if latest_service and latest_service.next_service_date else "",
            "insurance_number": insurance.document_number if insurance else "",
            "insurance_expiry": insurance.expiry_date.isoformat() if insurance and insurance.expiry_date else "",
            "insurance_status": insurance.get_verification_status_display() if insurance else "Missing",
            "puc_number": puc.document_number if puc else "",
            "puc_expiry": puc.expiry_date.isoformat() if puc and puc.expiry_date else "",
            "puc_status": puc.get_verification_status_display() if puc else "Missing",
            "registration_number": registration.document_number if registration else "",
            "registration_status": registration.get_verification_status_display() if registration else "Missing",
            "condition_status": latest_condition.get_overall_status_display() if latest_condition else "No data",
            "condition_score": latest_condition.overall_score if latest_condition else 0,
            "condition_assessment": latest_condition.ai_assessment if latest_condition else "",
            "performance_modifications": modification_summary["labels"],
            "modification_impact_note": modification_summary["note"],
            "maintenance_guidance": maintenance_guidance,
        }

    def _build_fleet_summary(self, bike_profiles, service_records, documents) -> list[dict]:
        service_costs = defaultdict(float)
        current_documents = self._current_documents(documents)
        doc_counts = Counter(self._document_vehicle_key(document) for document in current_documents)
        for record in service_records:
            service_costs[self._profile_key(record.bike_profile_id, record.vehicle_number, record.bike_name)] += record.cost or 0

        items = []
        for profile in bike_profiles:
            key = self._profile_key(profile.id, profile.vehicle_number, profile.display_name)
            items.append(
                {
                    "id": profile.id,
                    "display_name": profile.display_name,
                    "vehicle_type": profile.get_vehicle_type_display(),
                    "vehicle_number": profile.vehicle_number,
                    "is_primary": profile.is_primary,
                    "verification_status": profile.get_verification_status_display(),
                    "service_cost_total": round(service_costs.get(key, 0), 2),
                    "current_document_count": doc_counts.get(key, 0),
                }
            )
        return items

    def _detect_modifications(self, service_records, issues) -> dict:
        haystack = " ".join(
            filter(
                None,
                [*(item.notes for item in service_records[:12]), *(item.observation for item in issues[:12]), *(item.symptom for item in issues[:12])],
            )
        ).lower()
        labels = []
        if any(token in haystack for token in ["exhaust", "slip on", "full system"]):
            labels.append("Exhaust")
        if any(token in haystack for token in ["air filter", "performance filter", "bmc", "k&n"]):
            labels.append("Air Filter")
        if any(token in haystack for token in ["ecu", "remap", "tune"]):
            labels.append("ECU / Tune")
        if any(token in haystack for token in ["sprocket", "gear ratio"]):
            labels.append("Sprocket")
        if not labels:
            return {"labels": [], "note": "No performance-oriented modification signals detected in your current service history."}
        return {
            "labels": labels,
            "note": "Modification keywords were detected in service or issue notes. Mileage and wear may deviate from stock expectations.",
        }

    def _build_document_compliance(self, current_documents: list[BikeDocument], today) -> list[dict]:
        documents_by_type = {document.document_type: document for document in current_documents}
        items = []

        for document_type in REQUIRED_DOCUMENT_TYPES:
            document = documents_by_type.get(document_type)
            if document is None:
                items.append(
                    {
                        "document_type": document_type,
                        "label": DOCUMENT_TYPE_LABELS[document_type],
                        "status": "missing",
                        "status_label": "Missing",
                        "expiry_date": "",
                        "document_number": "",
                        "note": f"Add {DOCUMENT_TYPE_LABELS[document_type].lower()} details to track compliance cleanly.",
                        "required": True,
                    }
                )
                continue

            days_left = (document.expiry_date - today).days if document.expiry_date else None
            items.append(
                {
                    "document_type": document.document_type,
                    "label": document.get_document_type_display(),
                    "status": document.verification_status,
                    "status_label": document.get_verification_status_display(),
                    "expiry_date": document.expiry_date.isoformat() if document.expiry_date else "",
                    "document_number": document.document_number,
                    "note": document.verification_notes,
                    "days_left": days_left,
                    "required": True,
                }
            )

        for document in current_documents:
            if document.document_type in REQUIRED_DOCUMENT_TYPES:
                continue
            items.append(
                {
                    "document_type": document.document_type,
                    "label": document.get_document_type_display(),
                    "status": document.verification_status,
                    "status_label": document.get_verification_status_display(),
                    "expiry_date": document.expiry_date.isoformat() if document.expiry_date else "",
                    "document_number": document.document_number,
                    "note": document.verification_notes,
                    "required": False,
                }
            )

        return items

    def _service_record_text(self, record: BikeServiceRecord) -> str:
        return " ".join(
            str(part).lower()
            for part in [
                record.service_type,
                record.notes or "",
                record.extracted_work_summary or "",
                record.source_document_name or "",
                record.parsed_payload or {},
            ]
            if part
        )

    def _issue_text(self, issue: BikeIssueReport) -> str:
        return " ".join(
            str(part).lower()
            for part in [
                issue.title,
                issue.symptom,
                issue.observation,
                issue.tags,
                issue.probable_cause,
                issue.suggested_action,
            ]
            if part
        )

    def _current_documents(self, documents: list[BikeDocument]) -> list[BikeDocument]:
        documents_by_type = {}
        for document in documents:
            key = (self._document_vehicle_key(document), document.document_type)
            current = documents_by_type.get(key)
            if current is None or self._document_sort_key(document) > self._document_sort_key(current):
                documents_by_type[key] = document
        return list(documents_by_type.values())

    def _document_vehicle_key(self, document: BikeDocument) -> str:
        return self._profile_key(document.bike_profile_id, document.vehicle_number, document.bike_name)

    def _profile_key(self, profile_id, vehicle_number, bike_name) -> str:
        normalized_vehicle_number = re.sub(r"[\s-]+", "", vehicle_number or "").upper()
        return f"{profile_id or 'legacy'}::{normalized_vehicle_number or bike_name or 'unknown'}"

    def _document_sort_key(self, document: BikeDocument) -> tuple:
        return (
            1 if document.expiry_date else 0,
            document.expiry_date or document.issue_date or timezone.localdate(),
            getattr(document, "updated_at", None) or getattr(document, "created_at", None) or timezone.now(),
        )

    def _looks_like_indian_vehicle_number(self, value: str) -> bool:
        normalized = re.sub(r"[\s-]+", "", value or "").upper()
        return any(pattern.match(normalized) for pattern in VEHICLE_NUMBER_PATTERNS)


bike_service_intelligence = BikeServiceIntelligenceService()
