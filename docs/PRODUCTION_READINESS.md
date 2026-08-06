# Production Readiness

ALFRED is not production-ready until environment-backed checks are green. The application has core Django flows, cache materialization, browser regression wiring, Celery schedules, and supervised-model lifecycle checks, but production maturity still depends on deployment proof.

## Current State

- Large-data hardening is at 90% in Project Details after deterministic staging traffic exercised all 21 materialized cache namespaces.
- Browser/UI regression coverage is implemented, but full UI maturity remains gated on repeated no-skip local Chrome or Edge and CI Chrome summaries.
- Batch jobs are implemented through Celery worker and beat schedules for ML training, statement retry, verified-intelligence refresh, and verified-intelligence cleanup.
- Project Details now exposes a Deployment Readiness card and `production_readiness` payload. It remains gated until production database, shared cache, Celery runtime, security settings, browser CI, and production-like cache traffic are all proven.

## Required For Production

- Run Django with `DEBUG=false`, a real `DJANGO_SECRET_KEY`, production `ALLOWED_HOSTS`, HTTPS, secure cookies, HSTS, and explicit CSRF/CORS origins.
- Use a production database such as PostgreSQL, run migrations, and configure backup and restore checks.
- Use Redis or another shared cache backend for Django cache state and materialized dashboard telemetry; local-memory cache is only for development.
- Run separate Celery worker and Celery beat processes with Redis broker/result backend.
- Store media and generated artifacts in durable storage with access controls.
- Keep browser-regression CI green with `ALFRED_RUN_BROWSER_TESTS=true`, zero skipped Selenium tests, and uploaded browser artifacts.
- Record sustained production-like cache telemetry for all materialized namespaces under realistic concurrency and payload volume.

## Required Environment Variables

| Variable | Production expectation |
| --- | --- |
| `ALFRED_LOCAL_RUNTIME` | `false` |
| `DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | Set to a strong secret, not the local fallback |
| `ALLOWED_HOSTS` | Explicit production hostnames |
| `CSRF_TRUSTED_ORIGINS` | Explicit HTTPS origins |
| `CORS_ALLOWED_ORIGINS` | Explicit origins when cross-origin browser access is required |
| `DB_ENGINE` | Production backend such as `django.db.backends.postgresql` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Production database connection settings |
| `CACHE_BACKEND` | Shared backend such as `django.core.cache.backends.redis.RedisCache` |
| `CACHE_LOCATION` | Shared cache location, usually Redis |
| `REDIS_URL` | Redis broker/result backend for Celery |
| `ALFRED_PRODUCTION_DEPLOYMENT_PROOF` | Optional path to the recorded production deployment proof JSON |
| `ALFRED_MATERIALIZED_CACHE_TRAFFIC_PROOF` | Optional path to a cache traffic proof artifact |

The local defaults are intentionally convenient for development and tests. They are not production proof.

## Batch Job Processes

Start these alongside the Django web process:

```bash
celery -A alfred_ai worker -l info
celery -A alfred_ai beat -l info
```

The current beat schedule includes:

- `apps.ml_engine.continual.tasks.run_global_training_cycle` every 24 hours.
- `apps.expenses.tasks.retry_low_confidence_statement_uploads` every 20 minutes.
- `apps.integrations.tasks.refresh_verified_external_intelligence` every 6 hours.
- `apps.integrations.tasks.cleanup_verified_external_intelligence` every 24 hours.

## Deployment Proof Contract

Project Details reads `artifacts/ops/production_readiness_summary.json` by default, or the path in `ALFRED_PRODUCTION_DEPLOYMENT_PROOF`. The proof must be generated from the deployed environment and include:

- `source: production_deployment_probe`
- `environment: production`
- database engine, usable connection, and current migrations
- shared cache backend and read/write health
- Redis-backed Celery worker ping, beat schedule health, and required scheduled task count
- `DEBUG=false`, configured hosts, production secret, HTTPS redirect, secure cookies, and HSTS
- CI Chrome browser proof with zero skipped Selenium tests
- production-like shared-cache traffic covering every materialized namespace

Staging cache proof can move Large-data hardening to 90%, but it does not close production readiness by itself.
