from datetime import date
import json
import os
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from alfred_ai.services.materialized_cache import (
    MATERIALIZED_PAYLOAD_REGISTRY,
    MATERIALIZED_TRAFFIC_PROOF_SOURCE,
    invalidate_user_materialized_payloads,
    materialize_payload,
    materialized_cache_health_snapshot,
    validate_materialized_cache_traffic_proof,
)
from scripts.exercise_materialized_cache_traffic import run_materialized_cache_traffic_exercise
from apps.behavioral.models import BehavioralSignal
from apps.budgets.models import Budget
from apps.career.models import CareerProfile
from apps.expenses.models import Expense
from apps.family.models import Dependent
from apps.investments.models import Investment
from apps.loans.models import Loan
from apps.mobility.models import BikeConditionSnapshot, BikeProfile
from apps.risk.models import RiskSignal


class LargeDataMaterializationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.proof_tempdir = tempfile.TemporaryDirectory()
        self.cache_proof_path = Path(self.proof_tempdir.name) / "materialized-cache-proof.json"
        self.cache_proof_env = patch.dict(
            os.environ,
            {"ALFRED_MATERIALIZED_CACHE_TRAFFIC_PROOF": str(self.cache_proof_path)},
            clear=False,
        )
        self.cache_proof_env.start()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="large_data_user",
            password="Pass12345!",
            monthly_income=110000,
            rent_or_emi=28000,
            city="Bengaluru",
        )
        self.client = Client()
        self.client.force_login(self.user)
        self._seed_history()

    def tearDown(self):
        self.cache_proof_env.stop()
        self.proof_tempdir.cleanup()
        cache.clear()

    def test_financial_and_behavioral_dashboards_return_materialized_hits(self):
        endpoints = [
            ("/api/budgets/dashboard/", "budget-dashboard"),
            ("/api/loans/summary/", "loan-summary"),
            ("/api/loans/metrics/", "loan-metrics"),
            ("/api/loans/networth/", "loan-networth"),
            ("/api/behavioral/fingerprint/", "behavioral-fingerprint"),
            ("/api/behavioral/stress/", "behavioral-stress"),
        ]

        for path, namespace in endpoints:
            with self.subTest(path=path):
                self._assert_materialized_hit(path, namespace)

    def test_budget_dashboard_revision_invalidates_when_history_changes(self):
        first = self.client.get("/api/budgets/dashboard/")
        second = self.client.get("/api/budgets/dashboard/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_key = first.json()["_materialized"]["cache_key"]
        self.assertTrue(second.json()["_materialized"]["cached"])

        Expense.objects.create(
            user=self.user,
            amount=1450,
            classification="expense",
            category="fuel",
            payment_mode="UPI",
            merchant="Fuel Station",
            description="Fuel topup",
            raw_description="Fuel topup",
            transaction_date=timezone.localdate(),
            direction="debit",
            source="manual",
        )

        refreshed = self.client.get("/api/budgets/dashboard/")
        self.assertEqual(refreshed.status_code, 200)
        self.assertFalse(refreshed.json()["_materialized"]["cached"])
        self.assertNotEqual(first_key, refreshed.json()["_materialized"]["cache_key"])
        self.assertEqual(refreshed.json()["_materialized"]["invalidation_reason"], "revision_changed")
        self.assertTrue(refreshed.json()["_materialized"]["stale_regenerated"])

    def test_evidence_heavy_dashboards_return_materialized_hits(self):
        with patch(
            "apps.risk.services.risk_intelligence.job_intelligence.market_outlook",
            return_value={
                "risk_score": 24,
                "layoff_news": [],
                "job_market_news": [],
                "macro_context": {
                    "unemployment": {"latest_value": 5.0},
                    "inflation": {"latest_value": 4.8},
                    "market": {"one_month_return_pct": 1.8, "india_vix": 14.0},
                },
                "insights": ["Market pressure is controlled."],
                "evidence": [_evidence("World Bank")],
            },
        ), patch(
            "apps.risk.services.risk_intelligence.bike_service_intelligence.risk_snapshot",
            return_value={
                "summary": {
                    "critical_faults": 0,
                    "expired_documents": 0,
                    "expiring_documents": 0,
                    "latest_condition_score": 88,
                    "document_compliance_score": 100,
                },
                "pending_tasks": [],
            },
        ), patch(
            "apps.risk.services.risk_intelligence.verified_intelligence.google_news_search",
            return_value=_insight("Google News"),
        ), patch(
            "apps.integrations.views.verified_intelligence.market_snapshot",
            return_value=_insight("Yahoo Finance"),
        ), patch(
            "apps.integrations.views.verified_intelligence.world_bank_indicator",
            return_value=_insight("World Bank"),
        ), patch(
            "apps.integrations.views.verified_intelligence.tax_regime_reference",
            return_value=_insight("Income Tax Department"),
        ), patch(
            "apps.integrations.views.verified_intelligence.nps_tax_reference",
            return_value=_insight("PFRDA"),
        ), patch(
            "apps.integrations.views.verified_intelligence.ppf_reference",
            return_value=_insight("India Post"),
        ):
            self._assert_materialized_hit("/api/risk/outlook/", "risk-outlook")
            self._assert_materialized_hit(
                "/api/integrations/recommendations/overview/?investment_amount=5000&time_horizon=short_term",
                "recommendation-overview",
            )
            self._assert_materialized_hit(
                "/api/integrations/tax/overview/?annual_income=1320000&basic_salary=55000",
                "tax-optimizer-overview",
            )

    def test_materialized_metadata_standardizes_hit_miss_ttl_revision_and_latency(self):
        first = materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="metadata-standard",
            ttl_seconds=60,
            builder=lambda: {"value": 1},
        )
        second = materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="metadata-standard",
            ttl_seconds=60,
            builder=lambda: {"value": 2},
        )

        first_meta = first["_materialized"]
        second_meta = second["_materialized"]
        self.assertFalse(first_meta["cached"])
        self.assertEqual(first_meta["cache_status"], "miss")
        self.assertEqual(first_meta["invalidation_reason"], "cold_start")
        self.assertEqual(first_meta["ttl_seconds"], 60)
        self.assertTrue(first_meta["generated_at"])
        self.assertTrue(first_meta["expires_at"])
        self.assertTrue(first_meta["served_at"])
        self.assertTrue(first_meta["revision_key"])
        self.assertEqual(first_meta["revision"], first_meta["revision_key"])
        self.assertGreaterEqual(first_meta["generation_latency_ms"], 0)

        self.assertEqual(second["value"], 1)
        self.assertTrue(second_meta["cached"])
        self.assertEqual(second_meta["cache_status"], "hit")
        self.assertEqual(second_meta["cache_key"], first_meta["cache_key"])
        self.assertEqual(second_meta["generated_at"], first_meta["generated_at"])
        self.assertEqual(second_meta["expires_at"], first_meta["expires_at"])
        self.assertEqual(second_meta["revision_key"], first_meta["revision_key"])
        self.assertGreaterEqual(second_meta["generation_latency_ms"], 0)

        health = materialized_cache_health_snapshot()
        namespace = _namespace_row(health, "budget-dashboard")
        self.assertEqual(namespace["requests"], 2)
        self.assertEqual(namespace["hits"], 1)
        self.assertEqual(namespace["misses"], 1)
        self.assertEqual(namespace["hit_rate_pct"], 50.0)
        self.assertEqual(namespace["observed_ttl_seconds"], 60)
        self.assertEqual(namespace["last_cache_status"], "hit")

    def test_revision_regeneration_and_user_invalidation_are_observable(self):
        first = materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="revision-one",
            ttl_seconds=60,
            builder=lambda: {"value": 1},
        )
        regenerated = materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="revision-two",
            ttl_seconds=60,
            builder=lambda: {"value": 2},
        )

        self.assertFalse(regenerated["_materialized"]["cached"])
        self.assertEqual(regenerated["_materialized"]["invalidation_reason"], "revision_changed")
        self.assertTrue(regenerated["_materialized"]["stale_regenerated"])
        health = materialized_cache_health_snapshot()
        namespace = _namespace_row(health, "budget-dashboard")
        self.assertEqual(namespace["stale_regenerations"], 1)
        self.assertGreaterEqual(namespace["average_generation_latency_ms"], 0)

        invalidate_user_materialized_payloads(self.user.id, reason="test_reset")
        after_invalidation = materialized_cache_health_snapshot()
        namespace = _namespace_row(after_invalidation, "budget-dashboard")
        self.assertEqual(namespace["invalidations"], 1)
        self.assertEqual(namespace["last_invalidation_reason"], "test_reset")
        self.assertTrue(namespace["last_invalidation_at"])
        self.assertEqual(after_invalidation["last_invalidation_reason"], "test_reset")
        self.assertIsNone(cache.get(first["_materialized"]["cache_key"]))
        self.assertIsNone(cache.get(regenerated["_materialized"]["cache_key"]))

    def test_cache_health_snapshot_registers_all_materialized_namespaces(self):
        materialize_payload(
            namespace="budget-dashboard",
            user_id=self.user.id,
            revision="registry-check",
            ttl_seconds=60,
            builder=lambda: {"value": 1},
        )

        health = materialized_cache_health_snapshot()
        registry_namespaces = {item["namespace"] for item in MATERIALIZED_PAYLOAD_REGISTRY}
        snapshot_namespaces = {item["namespace"] for item in health["namespaces"]}

        self.assertEqual(health["registered_namespace_count"], len(registry_namespaces))
        self.assertTrue(registry_namespaces.issubset(snapshot_namespaces))
        self.assertGreaterEqual(health["configured_ttl_coverage_pct"], 100.0)
        self.assertFalse(health["production_mature"])
        self.assertTrue(health["configured_ttl_ready"])
        self.assertTrue(health["observability_ready"])
        self.assertFalse(health["runtime_telemetry_ready"])
        self.assertFalse(health["traffic_sample_ready"])
        self.assertGreater(health["unobserved_namespace_count"], 0)
        self.assertTrue(any("runtime telemetry" in blocker for blocker in health["maturity_blockers"]))
        self.assertIn("materialized namespace(s) have runtime telemetry", health["summary"])

    def test_cache_health_snapshot_keeps_observability_gate_closed_without_runtime_traffic(self):
        health = materialized_cache_health_snapshot()

        self.assertEqual(health["observed_namespace_count"], 0)
        self.assertEqual(health["unobserved_namespace_count"], health["registered_namespace_count"])
        self.assertTrue(health["configured_ttl_ready"])
        self.assertFalse(health["observability_ready"])
        self.assertFalse(health["runtime_telemetry_ready"])
        self.assertFalse(health["traffic_sample_ready"])
        self.assertTrue(any("runtime telemetry" in blocker for blocker in health["maturity_blockers"]))

    def test_cache_traffic_proof_rejects_incomplete_namespace_telemetry(self):
        payload = {
            "summary_version": 1,
            "source": MATERIALIZED_TRAFFIC_PROOF_SOURCE,
            "registered_namespace_count": len(MATERIALIZED_PAYLOAD_REGISTRY),
            "observed_namespace_count": 1,
            "observed_namespaces": ["budget-dashboard"],
            "total_requests": 2,
            "hits": 1,
            "misses": 1,
            "hit_rate_pct": 50,
            "observed_ttl_coverage_pct": 4.8,
            "configured_ttl_coverage_pct": 100,
            "stale_regeneration_count": 0,
            "invalidation_count": 0,
            "last_invalidation_reason": "",
            "average_generation_latency_ms": 0,
            "namespaces": [
                {
                    "namespace": "budget-dashboard",
                    "configured_ttl_seconds": 60,
                    "observed_ttl_seconds": 60,
                    "ttl_observed": True,
                    "requests": 2,
                    "hits": 1,
                    "misses": 1,
                    "last_revision_key": "abc",
                    "last_generated_at": "2026-08-05T00:00:00+00:00",
                    "last_served_at": "2026-08-05T00:00:01+00:00",
                    "average_generation_latency_ms": 0,
                }
            ],
        }

        validation = validate_materialized_cache_traffic_proof(payload, proof_path=str(self.cache_proof_path))

        self.assertFalse(validation["accepted"])
        self.assertIn("observed namespace count does not cover the full registry", validation["blockers"])
        self.assertTrue(any("missing namespace telemetry" in blocker for blocker in validation["blockers"]))
        self.assertIn("stale regeneration telemetry is missing", validation["blockers"])
        self.assertIn("cache invalidation telemetry is missing", validation["blockers"])

    def test_deterministic_cache_traffic_exercise_records_full_namespace_telemetry(self):
        summary = run_materialized_cache_traffic_exercise(
            user=self.user,
            client=self.client,
            proof_path=self.cache_proof_path,
        )

        self.assertTrue(self.cache_proof_path.exists())
        saved = json.loads(self.cache_proof_path.read_text(encoding="utf-8"))
        registry_namespaces = {item["namespace"] for item in MATERIALIZED_PAYLOAD_REGISTRY}
        self.assertEqual(set(saved["observed_namespaces"]), registry_namespaces)
        self.assertTrue(summary["validation"]["accepted"])
        self.assertEqual(summary["validation"]["observed_namespace_count"], len(registry_namespaces))
        self.assertEqual(summary["validation"]["registered_namespace_count"], len(registry_namespaces))

        health = materialized_cache_health_snapshot()
        self.assertTrue(health["traffic_proof_ready"])
        self.assertTrue(health["runtime_telemetry_ready"])
        self.assertTrue(health["traffic_sample_ready"])
        self.assertFalse(health["production_mature"])
        self.assertEqual(health["telemetry_source"], "traffic_proof")
        self.assertEqual(health["observed_namespace_count"], len(registry_namespaces))
        self.assertEqual(health["unobserved_namespace_count"], 0)
        self.assertGreaterEqual(health["total_requests"], len(registry_namespaces) * 2)
        self.assertGreater(health["hit_rate_pct"], 0)
        self.assertEqual(health["observed_ttl_coverage_pct"], 100.0)
        self.assertGreater(health["stale_regeneration_count"], 0)
        self.assertGreater(health["invalidation_count"], 0)
        self.assertEqual(health["last_invalidation_reason"], "staging_cache_traffic_proof")
        for row in health["namespaces"]:
            with self.subTest(namespace=row["namespace"]):
                self.assertGreaterEqual(row["requests"], 2)
                self.assertGreaterEqual(row["hits"], 1)
                self.assertGreaterEqual(row["misses"], 1)
                self.assertTrue(row["ttl_observed"])
                self.assertGreater(row["observed_ttl_seconds"], 0)
                self.assertTrue(row["last_revision_key"])
                self.assertTrue(row["last_generated_at"])
                self.assertTrue(row["last_served_at"])

    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    )
    def test_cache_traffic_exercise_uses_secure_requests_when_ssl_redirect_is_enabled(self):
        summary = run_materialized_cache_traffic_exercise(
            user=self.user,
            client=self.client,
            proof_path=self.cache_proof_path,
        )

        self.assertTrue(summary["validation"]["accepted"])
        for target in summary["endpoint_targets"]:
            with self.subTest(namespace=target["namespace"]):
                self.assertTrue(target["status_codes"])
                self.assertTrue(all(status == 200 for status in target["status_codes"]))

    def test_cache_namespace_registry_matches_materialized_payload_call_sites(self):
        source_namespaces = set()
        for root_name in ("alfred_ai", "apps"):
            for path in (Path(settings.BASE_DIR) / root_name).rglob("*.py"):
                if path.name == "materialized_cache.py":
                    continue
                text = path.read_text(encoding="utf-8")
                if "materialize_payload(" not in text:
                    continue
                source_namespaces.update(re.findall(r"namespace\s*=\s*[\"']([^\"']+)[\"']", text))

        registry_namespaces = {item["namespace"] for item in MATERIALIZED_PAYLOAD_REGISTRY}
        self.assertEqual(registry_namespaces, source_namespaces)

    def _assert_materialized_hit(self, path: str, namespace: str):
        first = self.client.get(path)
        second = self.client.get(path)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        first_meta = first.json()["_materialized"]
        second_meta = second.json()["_materialized"]
        self.assertEqual(first_meta["namespace"], namespace)
        self.assertFalse(first_meta["cached"])
        self.assertEqual(first_meta["cache_status"], "miss")
        self.assertTrue(second_meta["cached"])
        self.assertEqual(second_meta["cache_status"], "hit")
        self.assertEqual(first_meta["cache_key"], second_meta["cache_key"])
        for meta in (first_meta, second_meta):
            self.assertEqual(meta["revision"], meta["revision_key"])
            self.assertTrue(meta["generated_at"])
            self.assertTrue(meta["expires_at"])
            self.assertTrue(meta["served_at"])
            self.assertGreater(meta["ttl_seconds"], 0)
            self.assertIn(meta["invalidation_reason"], {"cold_start", "revision_changed", "expired", "cache_hit"})
            self.assertGreaterEqual(meta["generation_latency_ms"], 0)

    def _seed_history(self):
        Budget.objects.create(
            user=self.user,
            month="July 2026",
            base_budget=76000,
            inflation_adjusted=79000,
            spent=42000,
        )
        Expense.objects.create(
            user=self.user,
            amount=42000,
            classification="expense",
            category="household",
            payment_mode="UPI",
            merchant="Household",
            description="Monthly spend",
            raw_description="Monthly spend",
            transaction_date=date(2026, 7, 20),
            direction="debit",
            source="manual",
        )
        Loan.objects.create(
            user=self.user,
            lender="HDFC",
            loan_type="personal",
            principal=500000,
            interest_rate=11.5,
            emi=12800,
            tenure_months=48,
            remaining_balance=390000,
            start_date=date(2025, 8, 1),
            is_active=True,
            status="active",
        )
        Investment.objects.create(
            user=self.user,
            asset_type="mutual_fund",
            asset_name="Index Fund",
            institution="Groww",
            invested_amount=150000,
            current_value=172000,
            monthly_sip=8000,
            annual_return_rate=11,
            risk_level="Moderate",
        )
        BehavioralSignal.objects.create(user=self.user, stress_score=5, sleep_hours=7, work_hours=9)
        RiskSignal.objects.create(user=self.user, layoff_risk=22, illness_risk=18, relocation_risk=12)
        Dependent.objects.create(user=self.user, name="Parent", age=64, relation="parent")
        CareerProfile.objects.create(
            user=self.user,
            role="Data Analyst",
            experience_years=5,
            skills="Python, SQL, BI",
            last_salary=1400000,
        )
        bike = BikeProfile.objects.create(
            user=self.user,
            display_name="Activa",
            make="Honda",
            model_name="Activa 125",
            vehicle_type="scooter",
            bike_class="scooter",
            vehicle_number="KA03XY1111",
            is_primary=True,
        )
        BikeConditionSnapshot.objects.create(
            user=self.user,
            bike_profile=bike,
            bike_name=bike.display_name,
            vehicle_number=bike.vehicle_number,
            overall_status="good",
            engine_status="good",
            brake_status="good",
            tyre_status="good",
            battery_status="good",
            body_status="good",
            odometer_km=6200,
        )


def _evidence(source_name: str) -> dict:
    return {
        "source_name": source_name,
        "source_url": "https://example.com/proof",
        "status": "fresh",
        "stale_after": "2026-08-31T00:00:00+05:30",
    }


def _insight(source_name: str):
    class DummyInsight:
        def __init__(self):
            self.payload = {"latest_value": 4.8, "one_month_return_pct": 1.8, "india_vix": 14.0}
            self.evidence = _evidence(source_name)

    return DummyInsight()


def _namespace_row(snapshot: dict, namespace: str) -> dict:
    return next(item for item in snapshot["namespaces"] if item["namespace"] == namespace)
