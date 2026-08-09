# Production Readiness

ALFRED is not production-ready until environment-backed checks are green. The application has core Django flows, cache materialization, browser regression wiring, Celery schedules, and supervised-model lifecycle checks, but production maturity still depends on deployment proof.

For the AWS path, see [AWS Deployment Guide](AWS_DEPLOYMENT.md) and [AWS Free Tier Only Deployment](AWS_FREE_TIER_ONLY.md). The strict Free Tier path uses one EC2 host with Dockerized PostgreSQL, Redis, Django, Celery worker, and Celery beat. Managed RDS or ElastiCache are opt-in only after account-specific Free Tier coverage is confirmed.

## Current State

- Large-data hardening is at 90% in Project Details after deterministic staging traffic exercised all 21 materialized cache namespaces.
- Browser/UI regression coverage is implemented, but full UI maturity remains gated on repeated no-skip local Chrome or Edge and CI Chrome summaries.
- Batch jobs are implemented through Celery worker and beat schedules for ML training, statement retry, verified-intelligence refresh, and verified-intelligence cleanup.
- Verified evidence refresh can be exercised manually with `python scripts/refresh_verified_evidence.py --require-healthy`, which writes `artifacts/evidence/verified_evidence_refresh_summary.json` for Project Details.
- Production deployment readiness can be probed with `python scripts/run_production_readiness_probe.py --require-ready`, which writes `artifacts/ops/production_readiness_summary.json` for Project Details.
- Project Details now exposes a Deployment Readiness card and `production_readiness` payload. It remains gated until production database, shared cache, Celery runtime, security settings, browser CI, and production-like cache traffic are all proven.
- Project Details keeps product Scope Completion separate from deployment readiness and shows Production Blockers as their own percentage.

## Required For Production

- Run Django with `DEBUG=false`, a real `DJANGO_SECRET_KEY`, production `ALLOWED_HOSTS`, HTTPS, secure cookies, HSTS, explicit CSRF/CORS origins, and a bounded authenticated-session timeout.
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
| `ALFRED_SESSION_TIMEOUT_SECONDS` | Bounded authenticated idle timeout, recommended `1800` for production |
| `ALFRED_SESSION_WARNING_SECONDS` | User-visible warning window, recommended `300` |
| `SESSION_SAVE_EVERY_REQUEST` | `true`, so active authenticated requests refresh the idle timeout |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | `true` for production browser-close expiry |
| `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION` | `true`, so raw uploaded documents are deleted after parser extraction |
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
- required production environment variables with `ALFRED_LOCAL_RUNTIME=false` and `DEBUG=false`
- database engine, usable connection, and current migrations
- shared cache backend and read/write health
- Redis-backed Celery worker ping, beat schedule health, and required scheduled task count
- `DEBUG=false`, configured hosts, production secret, HTTPS redirect, secure cookies, and HSTS
- CI Chrome browser proof with zero skipped Selenium tests
- production-like shared-cache traffic covering every materialized namespace

Staging cache proof can move Large-data hardening to 90%, but it does not close production readiness by itself.

Run the deployment probe only after the production web process can load settings, migrations are applied, the Redis-backed cache is configured, Celery worker and beat are running, browser-regression CI has produced `browser_regression_summary.ci-chrome.json`, and materialized cache telemetry has been exercised against the shared cache.

## Production Blocker Checklist

| Project Details blocker | What closes it | Command or proof |
| --- | --- | --- |
| Production database config | Runtime env points Django at PostgreSQL, not SQLite | `DB_ENGINE=django.db.backends.postgresql` plus PostgreSQL connection settings |
| Shared cache config | Django cache uses Redis or another shared backend | `CACHE_BACKEND=django.core.cache.backends.redis.RedisCache` and `CACHE_LOCATION` |
| Celery config | Broker/result backend use deployed Redis and required beat entries remain configured | `REDIS_URL` plus `python manage.py check` |
| Production security config | Local runtime disabled, debug disabled, real secret, explicit hosts/origins, HTTPS redirect, secure cookies, and HSTS | `python scripts/run_production_readiness_probe.py --require-ready` |
| Database runtime proof | Deployed app can connect to PostgreSQL and migrations are current | readiness probe database section |
| Shared cache runtime proof | Deployed app can write/read/delete through shared cache | readiness probe cache section |
| Celery worker and beat proof | Worker ping succeeds and beat schedule includes training, retry, refresh, and cleanup | readiness probe Celery section |
| Production cache traffic proof | Shared-cache telemetry covers every registered materialized namespace under deployed traffic | `python scripts/exercise_materialized_cache_traffic.py --allow-live-external` then readiness probe |
| Browser CI proof | GitHub browser-regression job writes CI Chrome summary with zero skipped Selenium tests | `artifacts/browser/browser_regression_summary.ci-chrome.json` |

The local Docker Compose file proves the dependency shape but does not close production security or production runtime proof by itself. The strict Free Tier EC2 compose path can close runtime proof only after it runs on AWS with real PostgreSQL, Redis, Celery, browser CI, security, and cache traffic artifacts.
