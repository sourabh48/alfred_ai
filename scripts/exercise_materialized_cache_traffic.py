from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import ExitStack, nullcontext
from datetime import date, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("ALFRED_LOCAL_RUNTIME", "true")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alfred_ai.settings")


MATERIALIZED_ENDPOINT_TARGETS = (
    {"namespace": "budget-dashboard", "path": "/api/budgets/dashboard/"},
    {"namespace": "loan-summary", "path": "/api/loans/summary/"},
    {"namespace": "loan-metrics", "path": "/api/loans/metrics/"},
    {"namespace": "loan-networth", "path": "/api/loans/networth/"},
    {"namespace": "financial-intelligence", "path": "/api/expenses/dashboard/"},
    {"namespace": "behavioral-fingerprint", "path": "/api/behavioral/fingerprint/"},
    {"namespace": "behavioral-stress", "path": "/api/behavioral/stress/"},
    {"namespace": "career-dashboard", "path": "/api/career/dashboard/"},
    {"namespace": "family-growth", "path": "/api/family/growth/"},
    {
        "namespace": "recommendation-overview",
        "path": "/api/integrations/recommendations/overview/?investment_amount=5000&time_horizon=short_term",
    },
    {
        "namespace": "tax-optimizer-overview",
        "path": "/api/integrations/tax/overview/?annual_income=1320000&basic_salary=55000",
    },
    {"namespace": "investments-summary", "path": "/api/investments/summary/"},
    {"namespace": "investments-allocation", "path": "/api/investments/allocation/"},
    {"namespace": "investments-growth", "path": "/api/investments/growth/"},
    {"namespace": "mobility-dashboard", "path": "/api/mobility/dashboard/"},
    {"namespace": "bike-service-dashboard-view", "path": "/api/mobility/bike-service-dashboard/"},
    {"namespace": "relationship-alignment", "path": "/api/relationship/alignment/"},
    {"namespace": "risk-outlook", "path": "/api/risk/outlook/"},
)

INTERNAL_TARGET_NAMESPACES = (
    "financial-baseline",
    "bike-service-dashboard",
    "bike-service-risk-snapshot",
)


def ensure_django_ready() -> None:
    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()


def run_materialized_cache_traffic_exercise(
    *,
    user=None,
    client=None,
    username: str = "cache_traffic_probe",
    proof_path: str | Path | None = None,
    repetitions: int = 2,
    clear_cache: bool = True,
    offline_fixtures: bool = True,
) -> dict:
    ensure_django_ready()

    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core.cache import cache
    from django.test import Client
    from django.test.utils import override_settings
    from django.utils import timezone

    from alfred_ai.services.materialized_cache import (
        MATERIALIZED_PAYLOAD_REGISTRY,
        MATERIALIZED_TRAFFIC_PROOF_DEFAULT_PATH,
        MATERIALIZED_TRAFFIC_PROOF_SOURCE,
        invalidate_user_materialized_payloads,
        materialize_payload,
        materialized_cache_health_snapshot,
        validate_materialized_cache_traffic_proof,
    )
    from apps.expenses.services.financial_intelligence import build_canonical_financial_baseline
    from apps.mobility.services import bike_service_intelligence

    if clear_cache:
        cache.clear()

    if user is None:
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": f"{username}@example.com",
                "monthly_income": 110000,
                "rent_or_emi": 28000,
                "city": "Bengaluru",
            },
        )
        if created:
            user.set_password("CacheProbe123!")
        user.monthly_income = 110000
        user.rent_or_emi = 28000
        user.city = "Bengaluru"
        user.save()

    ensure_cache_probe_data(user)

    client = client or Client()
    client.force_login(user)
    allowed_hosts = sorted({*getattr(settings, "ALLOWED_HOSTS", []), "testserver", "localhost", "127.0.0.1"})
    endpoint_results: list[dict] = []
    internal_results: list[dict] = []

    with override_settings(ALLOWED_HOSTS=allowed_hosts), _offline_fixture_patches() if offline_fixtures else nullcontext():
        for target in MATERIALIZED_ENDPOINT_TARGETS:
            statuses = []
            for _ in range(max(int(repetitions), 2)):
                response = client.get(target["path"])
                statuses.append(response.status_code)
                if response.status_code >= 400:
                    raise RuntimeError(
                        f"{target['namespace']} traffic request failed at {target['path']} "
                        f"with HTTP {response.status_code}: {response.content[:400]!r}"
                    )
            endpoint_results.append({**target, "status_codes": statuses})

        internal_callers = {
            "financial-baseline": lambda: build_canonical_financial_baseline(user),
            "bike-service-dashboard": lambda: bike_service_intelligence.build_dashboard(user),
            "bike-service-risk-snapshot": lambda: bike_service_intelligence.risk_snapshot(user),
        }
        for namespace in INTERNAL_TARGET_NAMESPACES:
            metadata = []
            for _ in range(max(int(repetitions), 2)):
                payload = internal_callers[namespace]()
                metadata.append(dict(payload.get("_materialized") or {}))
            internal_results.append(
                {
                    "namespace": namespace,
                    "path": next(item["path"] for item in MATERIALIZED_PAYLOAD_REGISTRY if item["namespace"] == namespace),
                    "cache_statuses": [item.get("cache_status") for item in metadata],
                }
            )

        materialize_payload(
            namespace="budget-dashboard",
            user_id=user.id,
            revision="staging-cache-traffic-proof-revision-one",
            ttl_seconds=60,
            builder=lambda: {"proof_marker": "one"},
        )
        materialize_payload(
            namespace="budget-dashboard",
            user_id=user.id,
            revision="staging-cache-traffic-proof-revision-two",
            ttl_seconds=60,
            builder=lambda: {"proof_marker": "two"},
        )
        invalidate_user_materialized_payloads(user.id, reason="staging_cache_traffic_proof")

    health = materialized_cache_health_snapshot(include_traffic_proof=False)
    observed_namespaces = sorted(
        item["namespace"]
        for item in health["namespaces"]
        if int(item.get("requests") or 0) > 0
    )
    summary = {
        "summary_version": 1,
        "source": MATERIALIZED_TRAFFIC_PROOF_SOURCE,
        "generated_at_utc": timezone.now().isoformat(),
        "user_id": user.id,
        "username": user.username,
        "request_repetitions": max(int(repetitions), 2),
        "endpoint_targets": endpoint_results,
        "internal_targets": internal_results,
        "observed_namespaces": observed_namespaces,
        **health,
    }
    validation = validate_materialized_cache_traffic_proof(summary, proof_path=str(proof_path or ""))
    summary["validation"] = validation

    resolved_proof_path = _resolve_proof_path(proof_path or MATERIALIZED_TRAFFIC_PROOF_DEFAULT_PATH)
    resolved_proof_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_proof_path.write_text(json.dumps(summary, indent=2, sort_keys=True, default=_json_default), encoding="utf-8")
    summary["proof_path"] = str(resolved_proof_path)

    if not validation["accepted"]:
        raise RuntimeError(f"Materialized cache traffic proof was not accepted: {validation['blockers']}")
    return summary


def ensure_cache_probe_data(user) -> None:
    from django.utils import timezone

    from apps.behavioral.models import BehavioralSignal
    from apps.budgets.models import Budget
    from apps.career.models import CareerJobAnalysis, CareerProfile
    from apps.expenses.models import BankAccount, Expense, StatementUpload
    from apps.family.models import Dependent
    from apps.investments.models import Investment
    from apps.loans.models import Loan, LoanPaymentHistory
    from apps.mobility.models import (
        BikeConditionSnapshot,
        BikeDocument,
        BikeIssueReport,
        BikeProfile,
        BikeServiceRecord,
        FuelRefillLog,
        TravelPlan,
        TripLog,
    )
    from apps.relationship.models import RelationshipProfile
    from apps.risk.models import RiskSignal

    today = timezone.localdate()
    account, _ = BankAccount.objects.get_or_create(
        user=user,
        account_number="CACHEPROOF0001",
        defaults={
            "bank_name": "Cache Proof Bank",
            "nickname": "Cache Proof Salary",
            "account_type": "salary",
            "current_balance": 185000,
            "is_primary": True,
            "last_synced_at": timezone.now(),
        },
    )
    statement, _ = StatementUpload.objects.get_or_create(
        user=user,
        file_name="cache-proof-statement.pdf",
        defaults={
            "bank_account": account,
            "bank_name": "Cache Proof Bank",
            "account_number": account.account_number,
            "statement_start": today.replace(day=1),
            "statement_end": today,
            "parser_status": "parsed",
            "parse_confidence": 0.92,
            "imported_count": 4,
            "extracted_payload": {"layout": "cache-proof-realistic"},
        },
    )
    Budget.objects.get_or_create(
        user=user,
        month=today.strftime("%B %Y"),
        defaults={"base_budget": 76000, "inflation_adjusted": 79000, "spent": 42000},
    )
    _ensure_expense(
        user=user,
        bank_account=account,
        statement_upload=statement,
        amount=110000,
        classification="other",
        category="income",
        merchant="Cache Proof Payroll",
        direction="credit",
        transaction_date=today.replace(day=1),
        external_reference="cache-proof-income",
    )
    _ensure_expense(
        user=user,
        bank_account=account,
        statement_upload=statement,
        amount=28000,
        classification="expense",
        category="rent",
        merchant="Cache Proof Rent",
        direction="debit",
        transaction_date=today.replace(day=min(today.day, 3)),
        external_reference="cache-proof-rent",
    )
    _ensure_expense(
        user=user,
        bank_account=account,
        statement_upload=statement,
        amount=12800,
        classification="loan",
        category="loan",
        merchant="HDFC Loan",
        direction="debit",
        transaction_date=today.replace(day=min(today.day, 5)),
        external_reference="cache-proof-loan",
    )
    _ensure_expense(
        user=user,
        bank_account=account,
        statement_upload=statement,
        amount=4200,
        classification="expense",
        category="fuel",
        merchant="Cache Proof Fuel",
        direction="debit",
        transaction_date=today - timedelta(days=2),
        external_reference="cache-proof-fuel",
    )
    _ensure_expense(
        user=user,
        bank_account=account,
        statement_upload=statement,
        amount=6900,
        classification="expense",
        category="groceries",
        merchant="Cache Proof Groceries",
        direction="debit",
        transaction_date=today - timedelta(days=1),
        external_reference="cache-proof-groceries",
    )

    loan, _ = Loan.objects.get_or_create(
        user=user,
        loan_account_number="CACHE-LOAN-001",
        defaults={
            "lender": "HDFC",
            "loan_type": "personal",
            "principal": 500000,
            "interest_rate": 11.5,
            "emi": 12800,
            "tenure_months": 48,
            "remaining_balance": 390000,
            "start_date": date(2025, 8, 1),
            "is_active": True,
            "status": "active",
        },
    )
    LoanPaymentHistory.objects.get_or_create(
        loan=loan,
        payment_date=today.replace(day=min(today.day, 5)),
        amount=12800,
        defaults={
            "principal_component": 9100,
            "interest_component": 3700,
            "principal_paid": 9100,
            "interest_paid": 3700,
            "remaining_balance": 390000,
            "match_status": "matched",
        },
    )

    Investment.objects.get_or_create(
        user=user,
        asset_name="Cache Proof Index Fund",
        institution="Groww",
        defaults={
            "asset_type": "mutual_fund",
            "invested_amount": 150000,
            "current_value": 172000,
            "monthly_sip": 8000,
            "annual_return_rate": 11,
            "risk_level": "Moderate",
        },
    )
    Investment.objects.get_or_create(
        user=user,
        asset_name="Cache Proof Debt Fund",
        institution="Zerodha",
        defaults={
            "asset_type": "bond",
            "invested_amount": 80000,
            "current_value": 84000,
            "monthly_sip": 3000,
            "annual_return_rate": 7,
            "risk_level": "Low",
        },
    )

    CareerProfile.objects.update_or_create(
        user=user,
        defaults={
            "role": "Data Analyst",
            "experience_years": 5,
            "skills": "Python, SQL, BI",
            "last_salary": 1400000,
        },
    )
    CareerJobAnalysis.objects.get_or_create(
        user=user,
        job_url="https://example.com/cache-proof-data-analyst",
        defaults={
            "source_name": "Cache Proof Job Page",
            "apply_url": "https://example.com/cache-proof-data-analyst/apply",
            "company": "Cache Proof Analytics",
            "job_title": "Senior Data Analyst",
            "location": "Bengaluru, Karnataka, India",
            "parser_status": "parsed",
            "parse_confidence": 0.91,
            "fit_score": 78,
            "market_risk_score": 22,
            "extracted_payload": {
                "job_snapshot": {
                    "title": "Senior Data Analyst",
                    "company": "Cache Proof Analytics",
                    "location": "Bengaluru, Karnataka, India",
                    "required_skills": ["Python", "SQL", "Power BI"],
                    "experience_years": 5,
                    "salary_min": 1800000,
                    "salary_max": 2400000,
                    "salary_currency": "INR",
                    "salary_period": "annual",
                    "source_kind": "job_page",
                }
            },
        },
    )

    Dependent.objects.get_or_create(user=user, name="Parent", defaults={"age": 64, "relation": "parent"})
    RelationshipProfile.objects.get_or_create(
        user=user,
        partner_name="Cache Partner",
        defaults={"partner_financial_score": 72, "partner_savings_habits": 4, "compatibility_score": 78},
    )
    if not BehavioralSignal.objects.filter(user=user).exists():
        for index in range(3):
            BehavioralSignal.objects.create(
                user=user,
                stress_score=5 + index,
                sleep_hours=7 - (index * 0.2),
                work_hours=9 + index,
            )
    if not RiskSignal.objects.filter(user=user).exists():
        RiskSignal.objects.create(user=user, layoff_risk=22, illness_risk=18, relocation_risk=12)

    bike, _ = BikeProfile.objects.get_or_create(
        user=user,
        vehicle_number="KA03XY1111",
        defaults={
            "display_name": "Activa Cache Proof",
            "make": "Honda",
            "model_name": "Activa 125",
            "vehicle_type": "scooter",
            "bike_class": "scooter",
            "estimated_market_value": 74000,
            "usage_pattern": "essential",
            "is_primary": True,
            "verification_status": "official",
            "official_source_name": "Honda India",
            "official_source_url": "https://www.honda2wheelersindia.com/",
        },
    )
    BikeServiceRecord.objects.get_or_create(
        user=user,
        bike_profile=bike,
        bike_name=bike.display_name,
        vehicle_number=bike.vehicle_number,
        service_date=today - timedelta(days=35),
        odometer_km=6200,
        defaults={"service_type": "routine", "cost": 1450, "service_center": "Cache Proof Honda"},
    )
    FuelRefillLog.objects.get_or_create(
        user=user,
        bike_profile=bike,
        bike_name=bike.display_name,
        vehicle_number=bike.vehicle_number,
        refill_date=today - timedelta(days=5),
        defaults={"odometer_km": 6600, "fuel_liters": 5.4, "total_cost": 610, "station_name": "Cache Proof Fuel"},
    )
    BikeConditionSnapshot.objects.get_or_create(
        user=user,
        bike_profile=bike,
        bike_name=bike.display_name,
        vehicle_number=bike.vehicle_number,
        odometer_km=6700,
        defaults={
            "overall_status": "good",
            "overall_score": 86,
            "engine_status": "good",
            "brake_status": "watch",
            "tyre_status": "good",
            "battery_status": "good",
            "body_status": "good",
        },
    )
    BikeIssueReport.objects.get_or_create(
        user=user,
        bike_profile=bike,
        title="Cache Proof Brake Bite",
        defaults={
            "system": "brakes",
            "severity": "medium",
            "status": "resolved",
            "symptom": "Brake bite changed",
            "actual_cost": 950,
        },
    )
    BikeDocument.objects.get_or_create(
        user=user,
        bike_profile=bike,
        bike_name=bike.display_name,
        vehicle_number=bike.vehicle_number,
        document_type="invoice",
        document_number="CACHE-INVOICE-001",
        defaults={
            "issuer": "Cache Proof Honda",
            "issue_date": today - timedelta(days=35),
            "verification_status": "valid",
            "parser_status": "parsed",
            "parse_confidence": 0.91,
            "extracted_payload": {"service_payload": {"cost": 1450, "odometer_km": 6200}},
        },
    )
    travel_plan, _ = TravelPlan.objects.get_or_create(
        user=user,
        title="Cache Proof Mysuru Ride",
        defaults={
            "vehicle_profile": bike,
            "destination": "Mysuru",
            "start_date": today + timedelta(days=10),
            "end_date": today + timedelta(days=12),
            "budget": 9000,
            "transport_mode": "ride",
            "status": "planned",
        },
    )
    TripLog.objects.get_or_create(
        user=user,
        travel_plan=travel_plan,
        title="Cache Proof Shakedown",
        log_date=today - timedelta(days=1),
        defaults={
            "location_name": "Bengaluru",
            "distance_km": 38,
            "spend_amount": 480,
            "mood": "steady",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )


def _ensure_expense(**kwargs) -> None:
    from apps.expenses.models import Expense

    reference = kwargs.pop("external_reference")
    defaults = dict(kwargs)
    defaults["external_reference"] = reference
    defaults.setdefault("payment_mode", "UPI")
    defaults.setdefault("description", defaults.get("merchant", "Cache proof transaction"))
    defaults.setdefault("raw_description", defaults.get("description", "Cache proof transaction"))
    defaults.setdefault("source", "bank_statement")
    defaults.setdefault("model_confidence", 0.86)
    Expense.objects.get_or_create(
        user=defaults["user"],
        external_reference=reference,
        defaults=defaults,
    )


def _offline_fixture_patches():
    ensure_django_ready()

    from apps.integrations.services.verified_intelligence import freshness_snapshot
    from unittest.mock import patch

    stack = ExitStack()
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.market_snapshot",
            side_effect=lambda: _insight(
                "Yahoo Finance",
                {
                    "one_month_return_pct": 1.8,
                    "india_vix": 14.0,
                    "realized_volatility_pct": 12.4,
                },
            ),
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.world_bank_indicator",
            side_effect=lambda indicator, label: _insight("World Bank", {"indicator": indicator, "latest_value": 4.8}),
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.tax_regime_reference",
            side_effect=lambda: _insight("Income Tax Department", {"regimes": ["old", "new"]}),
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.nps_tax_reference",
            side_effect=lambda: _insight("NPS Trust", {"section": "80CCD"}),
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.ppf_reference",
            side_effect=lambda: _insight("India Post", {"section": "80C"}),
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.google_news_search",
            side_effect=lambda query: _insight(
                "Google News RSS",
                {
                    "items": [
                        {
                            "title": f"Cache proof news for {query}",
                            "link": "https://example.com/cache-proof-news",
                            "published": "2026-08-01",
                            "source": "Example",
                        }
                    ]
                },
            ),
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.macro_context",
            side_effect=_macro_context,
        )
    )
    stack.enter_context(
        patch(
            "apps.integrations.services.verified_intelligence.verified_intelligence.household_planning_context",
            side_effect=_household_planning_context,
        )
    )

    from apps.career.services import job_intelligence
    from apps.investments.views import portfolio_intelligence_service

    stack.enter_context(patch.object(job_intelligence, "market_outlook", side_effect=_career_market_outlook))
    stack.enter_context(patch.object(job_intelligence, "suggest_openings", side_effect=_career_openings))
    stack.enter_context(
        patch.object(
            portfolio_intelligence_service,
            "build_short_horizon_watchlist",
            side_effect=lambda user: {
                "available": False,
                "summary": "Cache proof skipped AMFI network fetch while preserving the watchlist payload contract.",
                "algorithm": {"source": "offline-fixture"},
                "items": [],
                "evidence": [_evidence("AMFI")],
                "freshness": freshness_snapshot([_evidence("AMFI")]),
                "generated_at": _now_iso(),
            },
        )
    )
    return stack


def _insight(source_name: str, payload: dict | None = None):
    from apps.integrations.services.verified_intelligence import InsightResult

    return InsightResult(payload=payload or {"latest_value": 4.8}, evidence=_evidence(source_name), cached=False)


def _evidence(source_name: str) -> dict:
    from django.utils import timezone

    now = timezone.now()
    slug = "".join(char.lower() if char.isalnum() else "-" for char in source_name).strip("-") or "source"
    return {
        "title": f"{source_name} cache proof",
        "source_name": source_name,
        "source_url": f"https://example.com/{slug}/cache-proof",
        "summary": f"Deterministic {source_name} fixture for materialized cache traffic proof.",
        "status": "fresh",
        "fetched_at": now.isoformat(),
        "verified_at": now.isoformat(),
        "stale_after": (now + timedelta(days=30)).isoformat(),
        "query": "cache proof",
        "scheduled_refresh": "refresh_due_records",
        "circuit_breaker": False,
        "stale_fallback": True,
    }


def _macro_payload() -> dict:
    return {
        "unemployment": {"latest_value": 5.0},
        "inflation": {"latest_value": 4.8},
        "market": {"one_month_return_pct": 1.8, "india_vix": 14.0, "realized_volatility_pct": 12.4},
    }


def _macro_context() -> dict:
    from apps.integrations.services.verified_intelligence import freshness_snapshot

    evidence = [_evidence("World Bank"), _evidence("Yahoo Finance")]
    return {
        "payload": _macro_payload(),
        "evidence": evidence,
        "freshness": freshness_snapshot(evidence),
        "notes": ["Deterministic macro fixture for cache proof traffic."],
    }


def _household_planning_context() -> dict:
    from apps.integrations.services.verified_intelligence import freshness_snapshot

    evidence = [_evidence("World Bank"), _evidence("Yahoo Finance")]
    return {
        "payload": {"inflation": _macro_payload()["inflation"], "market": _macro_payload()["market"]},
        "evidence": evidence,
        "freshness": freshness_snapshot(evidence),
        "notes": ["Deterministic household planning fixture for cache proof traffic."],
    }


def _career_market_outlook(role: str, company: str = "", macro: dict | None = None) -> dict:
    macro_payload = dict((macro or {}).get("payload") or macro or _macro_payload())
    return {
        "risk_score": 24,
        "layoff_news": [],
        "job_market_news": [
            {
                "title": f"{role or 'Analyst'} hiring remains active",
                "link": "https://example.com/cache-proof-hiring",
                "published": "2026-08-01",
                "source": "Example",
            }
        ],
        "macro_context": macro_payload,
        "insights": ["Deterministic market pressure is controlled for cache proof traffic."],
        "evidence": [_evidence("World Bank"), _evidence("Google News RSS")],
    }


def _career_openings(role: str, skills: list[str], *, country: str = "", state: str = "") -> dict:
    from apps.integrations.services.verified_intelligence import freshness_snapshot

    evidence = [_evidence("Remotive Jobs API"), _evidence("Arbeitnow Job Board API")]
    openings = [
        {
            "title": f"Senior {role or 'Data Analyst'}",
            "company": "Cache Proof Analytics",
            "location": "Bengaluru, Karnataka, India",
            "country": "India",
            "state": "Karnataka",
            "city": "Bengaluru",
            "url": "https://example.com/cache-proof-data-analyst",
            "apply_url": "https://example.com/cache-proof-data-analyst/apply",
            "salary": "INR 18-24 LPA",
            "aggregator_name": "Remotive Jobs API",
            "relevance_score": 88,
            "skills": skills[:3],
        },
        {
            "title": f"{role or 'Data Analyst'}",
            "company": "Cache Proof BI",
            "location": "Remote, India",
            "country": "India",
            "state": "",
            "city": "",
            "is_remote": True,
            "url": "https://example.com/cache-proof-bi",
            "salary": "INR 15-21 LPA",
            "aggregator_name": "Arbeitnow Job Board API",
            "relevance_score": 81,
            "skills": skills[:2],
        },
    ]
    return {
        "openings": openings,
        "evidence": evidence,
        "source_evidence": evidence,
        "source_coverage": {
            "configured_feed_count": 2,
            "salary_bearing_opening_count": 2,
            "freshness": freshness_snapshot(evidence),
        },
        "filters": {"countries": ["India"], "states": ["Karnataka"]},
        "active_filters": {"country": country, "state": state},
        "total_candidates": len(openings),
        "filtered_candidates": len(openings),
    }


def _resolve_proof_path(path_value: str | Path) -> Path:
    ensure_django_ready()
    from django.conf import settings

    path = Path(path_value)
    if path.is_absolute():
        return path
    return Path(settings.BASE_DIR) / path


def _now_iso() -> str:
    from django.utils import timezone

    return timezone.now().isoformat()


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise every materialized dashboard/API cache namespace.")
    parser.add_argument("--username", default="cache_traffic_probe")
    parser.add_argument("--proof-path", default=None)
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--no-clear-cache", action="store_true")
    parser.add_argument("--allow-live-external", action="store_true")
    args = parser.parse_args()

    summary = run_materialized_cache_traffic_exercise(
        username=args.username,
        proof_path=args.proof_path,
        repetitions=args.repetitions,
        clear_cache=not args.no_clear_cache,
        offline_fixtures=not args.allow_live_external,
    )
    validation = summary["validation"]
    print(
        "materialized cache traffic proof accepted: "
        f"{validation['observed_namespace_count']}/{validation['registered_namespace_count']} namespace(s), "
        f"{validation['total_requests']} request(s), {validation['hit_rate_pct']}% hit rate"
    )
    print(f"summary: {summary['proof_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
