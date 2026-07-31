from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.behavioral.models import BehavioralSignal
from apps.expenses.models import Expense
from apps.ml_engine.models import DocumentParserLearningMemory
from apps.mobility.models import BikeProfile, BikeServiceRecord
from apps.relationship.models import RelationshipProfile


SEED_PREFIX = "alfred_training_seed"


class Command(BaseCommand):
    help = "Create traceable local bootstrap samples required by supervised ALFRED training gates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--allow-non-debug",
            action="store_true",
            help="Allow creating bootstrap samples when DEBUG is false.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_non_debug"]:
            raise CommandError("Refusing to create bootstrap training samples outside DEBUG without --allow-non-debug.")

        before = _counts()
        with transaction.atomic():
            seed_users = _ensure_income_users()
            _ensure_expense_samples(seed_users[0])
            _ensure_behavioral_samples(seed_users[0])
            _ensure_parser_memory(seed_users[0])
            _ensure_relationship_profiles(seed_users)
            _ensure_service_records(seed_users[0])
        after = _counts()

        self.stdout.write(self.style.SUCCESS("ALFRED supervised training sample bootstrap complete."))
        for key in sorted(after):
            self.stdout.write(f"{key}: {before[key]} -> {after[key]}")


def _counts() -> dict:
    user_model = get_user_model()
    return {
        "income_users": user_model.objects.filter(monthly_income__gt=0).count(),
        "expense_rows": Expense.objects.count(),
        "behavioral_snapshots": BehavioralSignal.objects.count(),
        "parser_memory_rows": DocumentParserLearningMemory.objects.count(),
        "scored_relationship_profiles": RelationshipProfile.objects.filter(compatibility_score__gt=0).count(),
        "paid_service_records": BikeServiceRecord.objects.filter(cost__gt=0).count(),
    }


def _ensure_income_users() -> list:
    user_model = get_user_model()
    profiles = [
        ("bengaluru", 52000, 6000, 14000),
        ("mumbai", 68000, 8500, 22000),
        ("pune", 76000, 9000, 19000),
        ("hyderabad", 88000, 12000, 21000),
        ("chennai", 94000, 14000, 24000),
        ("delhi", 112000, 18000, 33000),
        ("gurgaon", 136000, 22000, 41000),
        ("kolkata", 59000, 5000, 15000),
    ]
    users = []
    for index, (city, monthly_income, variable_income, rent_or_emi) in enumerate(profiles, start=1):
        username = f"{SEED_PREFIX}_{index:02d}"
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.invalid",
                "monthly_income": monthly_income,
                "variable_income": variable_income,
                "rent_or_emi": rent_or_emi,
                "city": city.title(),
                "country": "India",
                "ml_training_consent_granted": True,
                "ml_training_consent_given_at": timezone.now(),
            },
        )
        changed = False
        for field, value in {
            "monthly_income": monthly_income,
            "variable_income": variable_income,
            "rent_or_emi": rent_or_emi,
            "city": city.title(),
            "country": "India",
            "ml_training_consent_granted": True,
        }.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed = True
        if user.ml_training_consent_given_at is None:
            user.ml_training_consent_given_at = timezone.now()
            changed = True
        if created:
            user.set_unusable_password()
            changed = True
        if changed:
            user.save()
        users.append(user)
    return users


def _ensure_expense_samples(user) -> None:
    categories = ["food", "fuel", "groceries", "utilities", "travel", "health", "subscription"]
    base_date = date(2026, 1, 1)
    index = 0
    while Expense.objects.count() < 28:
        transaction_date = base_date + timedelta(days=index)
        reference = f"{SEED_PREFIX}-expense-{index:02d}"
        if not Expense.objects.filter(external_reference=reference).exists():
            category = categories[index % len(categories)]
            Expense.objects.create(
                user=user,
                amount=220 + (index * 37) + (80 if category in {"travel", "health"} else 0),
                classification="expense",
                category=category,
                payment_mode="UPI" if index % 3 else "Card",
                merchant=f"Training Merchant {index % 6}",
                description=f"ALFRED supervised training expense sample {index + 1}",
                raw_description=f"ALFRED TRAINING SAMPLE {index + 1}",
                transaction_date=transaction_date,
                direction="debit",
                source="manual",
                external_reference=reference,
                transaction_fingerprint=reference,
                is_emotional=index % 9 == 0,
                model_confidence=0.78,
            )
        index += 1
        if index > 40:
            break


def _ensure_behavioral_samples(user) -> None:
    rows = [
        (3.2, 7.4, 8.0),
        (4.1, 6.9, 8.5),
        (5.6, 6.2, 9.0),
        (7.2, 5.4, 11.2),
        (8.1, 4.8, 12.0),
        (6.8, 5.9, 10.8),
        (3.8, 7.1, 7.5),
        (5.1, 6.5, 9.5),
        (7.8, 5.0, 11.6),
        (4.7, 6.8, 8.8),
        (8.4, 4.6, 12.4),
        (6.2, 6.0, 10.2),
    ]
    _create_behavioral_rows_until_ready(user, rows)


def _create_behavioral_rows_until_ready(user, rows) -> None:
    index = 0
    while BehavioralSignal.objects.count() < 12 or _behavioral_class_count() < 2:
        stress_score, sleep_hours, work_hours = rows[index % len(rows)]
        BehavioralSignal.objects.create(
            user=user,
            stress_score=stress_score,
            sleep_hours=sleep_hours,
            work_hours=work_hours,
        )
        index += 1
        if index > len(rows) + 4:
            break


def _behavioral_class_count() -> int:
    labels = set(
        1 if float(item.work_hours or 0) > 10 else 0
        for item in BehavioralSignal.objects.only("work_hours")
    )
    return len(labels)


def _ensure_parser_memory(user) -> None:
    index = 0
    while DocumentParserLearningMemory.objects.count() < 12 or _parser_memory_class_count() < 2:
        success = index % 2 == 0
        DocumentParserLearningMemory.objects.get_or_create(
            user=user,
            scope="statement_document" if success else "vehicle_document",
            file_extension=".pdf",
            detected_type="statement" if success else "invoice",
            template_signature=f"{SEED_PREFIX}-parser-template-{index:02d}",
            field_signature=f"{SEED_PREFIX}-parser-fields-{index:02d}",
            defaults={
                "successful_count": 4 if success else 0,
                "review_count": 1 if success else 4,
                "failed_count": 0 if success else 3,
                "correction_count": 1 if success else 0,
                "retry_success_count": 1 if success else 0,
                "retry_failure_count": 0 if success else 2,
                "average_confidence": 0.82 if success else 0.34,
                "observed_fields": ["amount", "date", "merchant"] if success else ["document_number", "tax"],
                "observed_keywords": ["ACCOUNT", "UPI", "BALANCE"] if success else ["INVOICE", "GST", "LABOUR"],
                "accepted_field_hints": ["amount", "date"] if success else ["document_number"],
                "last_resolution": "accepted_correction" if success else "manual_review_required",
            },
        )
        index += 1
        if index > 24:
            break


def _parser_memory_class_count() -> int:
    labels = set()
    for item in DocumentParserLearningMemory.objects.only(
        "successful_count",
        "review_count",
        "failed_count",
        "correction_count",
        "retry_success_count",
        "retry_failure_count",
    ):
        success_weight = item.successful_count + item.retry_success_count + item.correction_count
        failure_weight = item.failed_count + item.retry_failure_count + item.review_count
        labels.add(1 if success_weight >= max(failure_weight, 1) else 0)
    return len(labels)


def _ensure_relationship_profiles(users) -> None:
    scores = [
        (54, 2, 52),
        (61, 3, 59),
        (67, 4, 68),
        (72, 4, 74),
        (78, 5, 82),
        (46, 2, 48),
        (83, 5, 88),
        (58, 3, 63),
    ]
    for index, (financial_score, savings_habits, compatibility_score) in enumerate(scores):
        if RelationshipProfile.objects.filter(compatibility_score__gt=0).count() >= 8:
            break
        user = users[index % len(users)]
        partner_name = f"Training Partner {index + 1}"
        profile = RelationshipProfile.objects.filter(user=user, partner_name=partner_name).first()
        if profile is None:
            RelationshipProfile.objects.create(
                user=user,
                partner_name=partner_name,
                partner_financial_score=financial_score,
                partner_savings_habits=savings_habits,
                compatibility_score=compatibility_score,
            )
        elif profile.compatibility_score <= 0:
            profile.partner_financial_score = financial_score
            profile.partner_savings_habits = savings_habits
            profile.compatibility_score = compatibility_score
            profile.save(update_fields=["partner_financial_score", "partner_savings_habits", "compatibility_score", "updated_at"])


def _ensure_service_records(user) -> None:
    profile = _seed_vehicle_profile(user)
    base_date = date(2026, 1, 8)
    service_types = ["routine", "oil_chain", "repair", "routine", "tyres", "routine", "repair", "oil_chain", "routine", "accessory"]
    index = 0
    while BikeServiceRecord.objects.filter(cost__gt=0).count() < 10:
        service_date = base_date + timedelta(days=index * 21)
        service_type = service_types[index % len(service_types)]
        if not BikeServiceRecord.objects.filter(
            user=user,
            vehicle_number=profile.vehicle_number,
            service_date=service_date,
            service_type=service_type,
        ).exists():
            line_item_count = 2 + (index % 4)
            parts_count = 1 + (index % 3)
            labour_count = max(1, line_item_count - parts_count)
            BikeServiceRecord.objects.create(
                user=user,
                bike_profile=profile,
                bike_name=profile.display_name,
                vehicle_number=profile.vehicle_number,
                service_date=service_date,
                odometer_km=1800 + (index * 850),
                service_type=service_type,
                cost=950 + (index * 185) + (420 if service_type in {"repair", "tyres"} else 0),
                service_center="ALFRED Training Service Center",
                notes="ALFRED supervised training bootstrap sample.",
                parsed_payload={
                    "service_payload": {
                        "line_item_count": line_item_count,
                        "parts_item_count": parts_count,
                        "labour_item_count": labour_count,
                        "parts_items": [{"description": f"Part {part + 1}"} for part in range(parts_count)],
                        "labour_items": [{"description": f"Labour {part + 1}"} for part in range(labour_count)],
                    }
                },
            )
        index += 1
        if index > 24:
            break


def _seed_vehicle_profile(user) -> BikeProfile:
    profile = BikeProfile.objects.filter(user=user, vehicle_number="ALFRED-TRAIN-001").first()
    if profile is None:
        return BikeProfile.objects.create(
            user=user,
            vehicle_type="motorcycle",
            display_name="ALFRED Training Hunter 350",
            make="Royal Enfield",
            model_name="Hunter 350",
            vehicle_number="ALFRED-TRAIN-001",
            bike_class="retro",
            engine_cc=349,
            expected_mileage_kmpl=36,
            service_interval_km=5000,
            service_interval_days=180,
            fuel_type="petrol",
            usage_pattern="personal",
            catalog_key="royal-enfield-hunter-350",
            official_source_name="Royal Enfield Maintenance Tips",
            official_source_url="https://www.royalenfield.com/uk/en/after-sales/digital-quickstart/goan-classic-350/maintenancetips/",
            verification_status="official",
            is_primary=True,
            ai_notes="ALFRED supervised training bootstrap vehicle profile.",
        )
    return profile
