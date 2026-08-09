import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings

from alfred_ai.services.production_readiness import (
    PRODUCTION_DEPLOYMENT_PROOF_SOURCE,
    PRODUCTION_READINESS_PROBE_COMMAND,
    REQUIRED_PRODUCTION_ENV_VARS,
    write_production_deployment_proof,
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
        "environment_variables": {
            "ready": True,
            "required": list(REQUIRED_PRODUCTION_ENV_VARS),
            "missing": [],
            "incorrect": [],
            "present_count": len(REQUIRED_PRODUCTION_ENV_VARS),
            "total_count": len(REQUIRED_PRODUCTION_ENV_VARS),
        },
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
            "result_backend": "rediss://redis.example.com:6379/0",
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
            "csrf_trusted_origins_configured": True,
            "cors_restricted": True,
        },
        "browser_ci": {
            "ci_chrome_no_skip": True,
            "browser": "Chrome",
            "run_context": "ci",
            "require_browser": True,
            "run_browser_tests_env": "true",
            "runner_return_code": 0,
            "tests_run_count": 3,
            "skipped_count": 0,
            "github_actions_enabled": True,
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
        aws = (REPO_ROOT / "docs" / "AWS_DEPLOYMENT.md").read_text(encoding="utf-8")

        self.assertIn("Production hardening | 90%", readme)
        self.assertIn("all 21 registered materialized namespaces", readme)
        self.assertIn("python scripts/exercise_materialized_cache_traffic.py", readme)
        self.assertIn("AWS Deployment Guide", readme)
        self.assertIn("docker-compose.aws-local.yml", readme)
        self.assertIn("Data Privacy And Storage", readme)
        self.assertIn("ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true", readme)
        self.assertIn("ALFRED is not production-ready", production)
        self.assertIn("AWS Deployment Guide", production)
        self.assertIn("Celery worker and beat", production)
        self.assertIn("local-memory cache is only for development", production)
        self.assertIn("sustained production-like cache telemetry", production)
        self.assertIn("Required Environment Variables", production)
        self.assertIn("ALFRED_PRODUCTION_DEPLOYMENT_PROOF", production)
        self.assertIn("ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION", production)
        self.assertIn("source: production_deployment_probe", production)
        self.assertIn("python scripts/run_production_readiness_probe.py --require-ready", production)
        self.assertIn("Production Blocker Checklist", production)
        self.assertIn("Production database config", production)
        self.assertIn("Shared cache config", production)
        self.assertIn("Celery worker and beat proof", production)
        self.assertIn("Amazon EC2", aws)
        self.assertIn("Amazon RDS for PostgreSQL", aws)
        self.assertIn("db.t3.micro", aws)
        self.assertIn("db.t4g.micro", aws)
        self.assertIn("ElastiCache", aws)
        self.assertIn("Self-managed Redis on EC2 first", aws)
        self.assertIn("Blocker-To-Proof Checklist", aws)
        self.assertIn("Do not raise Deployment Readiness to 100%", aws)

    def test_aws_env_and_docker_contracts_cover_web_postgres_redis_and_celery(self):
        dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
        compose = (REPO_ROOT / "docker-compose.aws-local.yml").read_text(encoding="utf-8")
        aws_env = (REPO_ROOT / "config" / "aws.env.example").read_text(encoding="utf-8")
        compose_env = (REPO_ROOT / "config" / "docker-compose.env.example").read_text(encoding="utf-8")
        requirements = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8")

        self.assertIn("gunicorn", dockerfile)
        self.assertIn("postgresql-client", dockerfile)
        self.assertIn("redis-tools", dockerfile)
        self.assertIn("gunicorn==", requirements)
        self.assertIn("psycopg[binary]==", requirements)

        for service in ("postgres:", "redis:", "web:", "worker:", "beat:"):
            with self.subTest(service=service):
                self.assertIn(service, compose)

        self.assertIn("python manage.py migrate", compose)
        self.assertIn("python manage.py collectstatic --noinput", compose)
        self.assertIn("celery -A alfred_ai worker", compose)
        self.assertIn("celery -A alfred_ai beat", compose)
        self.assertIn("django.core.cache.backends.redis.RedisCache", aws_env)
        self.assertIn("DB_ENGINE=django.db.backends.postgresql", aws_env)
        self.assertIn("ALFRED_LOCAL_RUNTIME=false", aws_env)
        self.assertIn("DEBUG=false", aws_env)
        self.assertIn("SECURE_SSL_REDIRECT=true", aws_env)
        self.assertIn("SESSION_COOKIE_SECURE=true", aws_env)
        self.assertIn("CSRF_COOKIE_SECURE=true", aws_env)
        self.assertIn("ALFRED_PRODUCTION_DEPLOYMENT_PROOF", aws_env)
        self.assertIn("ALFRED_MATERIALIZED_CACHE_TRAFFIC_PROOF", aws_env)
        self.assertIn("ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true", aws_env)
        self.assertIn("SECURE_SSL_REDIRECT=false", compose_env)
        self.assertIn("ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true", compose_env)
        self.assertIn("This is intentionally not accepted as production proof", compose_env)

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
        self.assertEqual(snapshot["blocker_count"], len(snapshot["blockers"]))
        self.assertEqual(snapshot["blocker_percent"], 100)
        self.assertEqual(snapshot["ready_checks"], [])
        self.assertEqual(len(snapshot["blocked_checks"]), snapshot["blocker_count"])
        self.assertEqual(snapshot["manual_task_count"], snapshot["blocker_count"])
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
        self.assertTrue(validation["sections"]["environment_variables"]["ready"])
        self.assertTrue(validation["sections"]["database"]["ready"])
        self.assertTrue(validation["sections"]["cache"]["ready"])
        self.assertTrue(validation["sections"]["celery"]["ready"])
        self.assertTrue(validation["sections"]["security"]["ready"])
        self.assertTrue(validation["sections"]["browser_ci"]["ready"])
        self.assertTrue(validation["sections"]["cache_traffic"]["ready"])

    def test_production_deployment_proof_rejects_placeholder_payload_without_env_and_ci_details(self):
        payload = _accepted_deployment_proof_payload()
        payload.pop("environment_variables")
        payload["browser_ci"] = {"ci_chrome_no_skip": True}

        validation = validate_production_deployment_proof(
            payload,
            proof_path="artifacts/ops/production_readiness_summary.json",
        )

        self.assertFalse(validation["accepted"])
        self.assertIn(
            "environment variable proof must show required production variables present with production values",
            validation["blockers"],
        )
        self.assertIn(
            "browser CI proof must show GitHub Actions Chrome required-browser execution with zero skipped Selenium tests",
            validation["blockers"],
        )

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
    def test_production_readiness_probe_writes_rejected_local_artifact(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(os.environ, {}, clear=True), patch(
            "alfred_ai.services.production_readiness._database_runtime_probe",
            return_value={
                "engine": "django.db.backends.sqlite3",
                "connection_usable": True,
                "migrations_current": True,
            },
        ):
            proof_path = Path(tmpdir) / "production-readiness.json"
            result = write_production_deployment_proof(
                proof_path=proof_path,
                ping_celery=False,
                browser_summary_path=Path(tmpdir) / "missing-browser.json",
                cache_traffic_proof_path=Path(tmpdir) / "missing-cache.json",
            )
            self.assertTrue(proof_path.exists())

        validation = result["validation"]
        self.assertFalse(validation["accepted"])
        self.assertEqual(validation["state"], "failed")
        self.assertIn("environment is not production", validation["blockers"])
        self.assertIn(
            "environment variable proof must show required production variables present with production values",
            validation["blockers"],
        )
        self.assertFalse(validation["sections"]["environment_variables"]["ready"])
        self.assertFalse(validation["sections"]["cache"]["ready"])
        self.assertFalse(validation["sections"]["celery"]["ready"])

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
                    "ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION": "true",
                },
                clear=True,
            ):
                snapshot = production_readiness_snapshot(
                    cache_health={"production_mature": False, "telemetry_source": "production_probe"},
                    browser_coverage={"proof_summary": {"ci_gate_recorded": True}},
                )

        self.assertTrue(snapshot["ready"])
        self.assertEqual(snapshot["progress"], 100)
        self.assertEqual(snapshot["blocker_percent"], 0)
        self.assertEqual(snapshot["blocker_count"], 0)
        self.assertEqual(snapshot["blockers"], [])
        self.assertEqual(snapshot["probe_command"], PRODUCTION_READINESS_PROBE_COMMAND)


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
        self.assertEqual(readiness["blocker_count"], len(readiness["blockers"]))
        self.assertEqual(len(readiness["ready_checks"]), readiness["ready_check_count"])
        self.assertEqual(len(readiness["blocked_checks"]), readiness["blocker_count"])
        self.assertEqual(readiness["manual_task_count"], readiness["blocker_count"])
        self.assertGreater(readiness["blocker_percent"], 0)
        self.assertIn("Deployment proof gated", readiness["maturity_status"])
        self.assertIn("Production database config", readiness["blockers"])
        self.assertIn("Shared cache config", readiness["blockers"])
        self.assertIn("Production cache traffic proof", readiness["blockers"])
        self.assertEqual(readiness["probe_command"], PRODUCTION_READINESS_PROBE_COMMAND)

        deployment_card = next(item for item in payload["summary_cards"] if item["label"] == "Deployment Readiness")
        self.assertEqual(deployment_card["value"], f"{readiness['progress']}%")
        blocker_card = next(item for item in payload["summary_cards"] if item["label"] == "Production Blockers")
        self.assertEqual(blocker_card["value"], f"{readiness['blocker_percent']}%")
        self.assertIn("excluded from Scope Completion", blocker_card["copy"])
        scope_card = next(item for item in payload["summary_cards"] if item["label"] == "Scope Completion")
        self.assertIn("deployment readiness is excluded", scope_card["copy"])
        self.assertTrue(payload["scope_completion"]["production_readiness_excluded"])
        self.assertEqual(payload["scope_completion"]["production_blocker_percent"], readiness["blocker_percent"])
        self.assertEqual(
            payload["scope_completion"]["remaining_product_gate_count"],
            len(payload["scope_completion"]["remaining_product_gates"]),
        )
        for value in (
            readiness["progress"],
            readiness["blocker_percent"],
            payload["scope_completion"]["progress"],
        ):
            with self.subTest(progress=value):
                self.assertIsInstance(value, int)
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 100)
        production_metric = next(item for item in payload["operational_metrics"] if item["label"] == "Production Readiness")
        self.assertEqual(production_metric["value"], f"{readiness['progress']}%")
        production_blocker_metric = next(item for item in payload["operational_metrics"] if item["label"] == "Production Blockers")
        self.assertEqual(production_blocker_metric["value"], f"{readiness['blocker_percent']}%")
        self.assertTrue(
            any(
                "Production deployment is still gated" in risk
                for risk in payload["risks"]
            )
        )
