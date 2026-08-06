import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from alfred_ai.services.production_readiness import (
    PRODUCTION_DEPLOYMENT_PROOF_SOURCE,
    production_readiness_snapshot,
    validate_production_deployment_proof,
)
from alfred_ai.services.materialized_cache import MATERIALIZED_PAYLOAD_REGISTRY


REPO_ROOT = Path(__file__).resolve().parents[1]


def _accepted_deployment_proof_payload() -> dict:
    namespace_count = len(MATERIALIZED_PAYLOAD_REGISTRY)
    return {
        "summary_version": 1,
        "source": PRODUCTION_DEPLOYMENT_PROOF_SOURCE,
        "environment": "production",
        "generated_at_utc": "2026-08-06T00:00:00+00:00",
        "database": {
            "engine": "django.db.backends.postgresql",
            "connection_usable": True,
            "migrations_current": True,
        },
        "cache": {
            "backend": "django.core.cache.backends.redis.RedisCache",
            "shared_backend": True,
            "read_write_ok": True,
        },
        "celery": {
            "broker_url": "rediss://redis.example.com:6379/0",
            "worker_ping_ok": True,
            "beat_schedule_ok": True,
            "scheduled_task_count": 4,
        },
        "security": {
            "debug": False,
            "allowed_hosts_configured": True,
            "secret_key_configured": True,
            "secure_cookies": True,
            "ssl_redirect": True,
            "hsts_seconds": 31536000,
        },
        "browser_ci": {
            "ci_chrome_no_skip": True,
        },
        "cache_traffic": {
            "production_like": True,
            "shared_cache_backend": True,
            "registered_namespace_count": namespace_count,
            "observed_namespace_count": namespace_count,
        },
    }


class ProductionReadinessContractTests(SimpleTestCase):
    def test_readme_and_production_doc_keep_production_maturity_gated(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        production = (REPO_ROOT / "docs" / "PRODUCTION_READINESS.md").read_text(encoding="utf-8")

        self.assertIn("Production hardening | 90%", readme)
        self.assertIn("all 21 registered materialized namespaces", readme)
        self.assertIn("python scripts/exercise_materialized_cache_traffic.py", readme)
        self.assertIn("ALFRED is not production-ready", production)
        self.assertIn("Celery worker and beat", production)
        self.assertIn("local-memory cache is only for development", production)
        self.assertIn("sustained production-like cache telemetry", production)
        self.assertIn("Required Environment Variables", production)
        self.assertIn("ALFRED_PRODUCTION_DEPLOYMENT_PROOF", production)
        self.assertIn("source: production_deployment_probe", production)

    def test_sonarqube_is_not_part_of_current_production_contract(self):
        removed_paths = (
            REPO_ROOT / ".github" / "workflows" / "sonarqube.yml",
            REPO_ROOT / "sonar-project.properties",
        )

        for path in removed_paths:
            with self.subTest(path=path):
                self.assertFalse(path.exists())

        docs = "\n".join(
            [
                (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "PRODUCTION_READINESS.md").read_text(encoding="utf-8"),
                (REPO_ROOT / "docs" / "PROJECT_STATUS.md").read_text(encoding="utf-8"),
            ]
        )
        self.assertNotIn("SonarQube", docs)
        self.assertNotIn("SONAR_TOKEN", docs)

    @override_settings(
        LOCAL_RUNTIME=True,
        DEBUG=True,
        SECRET_KEY="alfred-local-development-key",
        ALLOWED_HOSTS=["localhost", "127.0.0.1"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "test"}},
        CELERY_BROKER_URL="redis://localhost:6379/0",
        CELERY_RESULT_BACKEND="redis://localhost:6379/0",
    )
    def test_production_readiness_snapshot_gates_local_defaults_and_missing_proof(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"ALFRED_PRODUCTION_DEPLOYMENT_PROOF": str(Path(tmpdir) / "missing.json")},
            clear=True,
        ):
            snapshot = production_readiness_snapshot(
                cache_health={"production_mature": False, "telemetry_source": "traffic_proof"},
                browser_coverage={"proof_summary": {"ci_gate_recorded": False}},
            )

        self.assertFalse(snapshot["ready"])
        self.assertLess(snapshot["progress"], 100)
        self.assertEqual(snapshot["maturity_status"], "Deployment proof gated")
        self.assertIn("Production database config", snapshot["blockers"])
        self.assertIn("Shared cache config", snapshot["blockers"])
        self.assertIn("Celery config", snapshot["blockers"])
        self.assertIn("Production security config", snapshot["blockers"])
        self.assertIn("Database runtime proof", snapshot["blockers"])
        self.assertIn("Shared cache runtime proof", snapshot["blockers"])
        self.assertIn("Celery worker and beat proof", snapshot["blockers"])
        self.assertIn("Production cache traffic proof", snapshot["blockers"])
        self.assertIn("Browser CI proof", snapshot["blockers"])
        self.assertIn("DB_ENGINE", snapshot["required_env_vars"])
        self.assertIn("CACHE_BACKEND", snapshot["required_env_vars"])
        self.assertIn("REDIS_URL", snapshot["required_env_vars"])

    def test_production_deployment_proof_contract_accepts_complete_payload(self):
        validation = validate_production_deployment_proof(
            _accepted_deployment_proof_payload(),
            proof_path="artifacts/ops/production_readiness_summary.json",
        )

        self.assertTrue(validation["accepted"])
        self.assertEqual(validation["state"], "accepted")
        self.assertTrue(validation["sections"]["database"]["ready"])
        self.assertTrue(validation["sections"]["cache"]["ready"])
        self.assertTrue(validation["sections"]["celery"]["ready"])
        self.assertTrue(validation["sections"]["security"]["ready"])
        self.assertTrue(validation["sections"]["browser_ci"]["ready"])
        self.assertTrue(validation["sections"]["cache_traffic"]["ready"])

    @override_settings(
        LOCAL_RUNTIME=False,
        DEBUG=False,
        SECRET_KEY="production-secret",
        ALLOWED_HOSTS=["alfred.example.com"],
        CSRF_TRUSTED_ORIGINS=["https://alfred.example.com"],
        CORS_ALLOW_ALL_ORIGINS=False,
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_HSTS_SECONDS=31536000,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "alfred",
                "USER": "alfred",
                "PASSWORD": "secret",
                "HOST": "db.example.com",
                "PORT": "5432",
            }
        },
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.redis.RedisCache",
                "LOCATION": "rediss://redis.example.com:6379/1",
            }
        },
        CELERY_BROKER_URL="rediss://redis.example.com:6379/0",
        CELERY_RESULT_BACKEND="rediss://redis.example.com:6379/0",
    )
    def test_production_readiness_snapshot_can_accept_fully_proven_deployment(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proof_path = Path(tmpdir) / "production-readiness.json"
            proof_path.write_text(json.dumps(_accepted_deployment_proof_payload()), encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "ALFRED_PRODUCTION_DEPLOYMENT_PROOF": str(proof_path),
                    "ALFRED_LOCAL_RUNTIME": "false",
                    "DEBUG": "false",
                    "DJANGO_SECRET_KEY": "production-secret",
                    "ALLOWED_HOSTS": "alfred.example.com",
                    "CSRF_TRUSTED_ORIGINS": "https://alfred.example.com",
                    "DB_ENGINE": "django.db.backends.postgresql",
                    "DB_NAME": "alfred",
                    "DB_USER": "alfred",
                    "DB_PASSWORD": "secret",
                    "DB_HOST": "db.example.com",
                    "CACHE_BACKEND": "django.core.cache.backends.redis.RedisCache",
                    "CACHE_LOCATION": "rediss://redis.example.com:6379/1",
                    "REDIS_URL": "rediss://redis.example.com:6379/0",
                },
                clear=True,
            ):
                snapshot = production_readiness_snapshot(
                    cache_health={"production_mature": False, "telemetry_source": "production_probe"},
                    browser_coverage={"proof_summary": {"ci_gate_recorded": True}},
                )

        self.assertTrue(snapshot["ready"])
        self.assertEqual(snapshot["progress"], 100)
        self.assertEqual(snapshot["blockers"], [])


class ProductionReadinessProjectDetailsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            username="production-readiness-admin",
            password="Pass12345!",
            email="production-readiness@example.com",
        )
        self.client = Client()
        self.client.force_login(self.superuser)

    def test_project_details_surfaces_production_readiness_without_claiming_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            os.environ,
            {"ALFRED_PRODUCTION_DEPLOYMENT_PROOF": str(Path(tmpdir) / "missing.json")},
            clear=False,
        ):
            payload = self.client.get("/api/project-details/").json()

        readiness = payload["production_readiness"]
        self.assertFalse(readiness["ready"])
        self.assertLess(readiness["progress"], 100)
        self.assertIn("Deployment proof gated", readiness["maturity_status"])
        self.assertIn("Production database config", readiness["blockers"])
        self.assertIn("Shared cache config", readiness["blockers"])
        self.assertIn("Production cache traffic proof", readiness["blockers"])

        deployment_card = next(item for item in payload["summary_cards"] if item["label"] == "Deployment Readiness")
        self.assertEqual(deployment_card["value"], f"{readiness['progress']}%")
        production_metric = next(item for item in payload["operational_metrics"] if item["label"] == "Production Readiness")
        self.assertEqual(production_metric["value"], f"{readiness['progress']}%")
        self.assertTrue(
            any(
                "Production deployment is still gated" in risk
                for risk in payload["risks"]
            )
        )
