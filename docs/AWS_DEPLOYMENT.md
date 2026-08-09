# AWS Deployment Guide

Last reviewed: 2026-08-09

This guide prepares ALFRED for an AWS hybrid/cloud deployment without marking it production-ready before proof exists. Use it with `docs/PRODUCTION_READINESS.md` and Project Details.

## Free Tier Reality

AWS is usable for ALFRED, but do not treat it as permanently free for a Django app with PostgreSQL, Redis, and always-running Celery jobs.

Current AWS source pages:

- AWS Free Tier: https://aws.amazon.com/free/
- Amazon RDS Free Tier: https://aws.amazon.com/rds/free/
- Amazon ElastiCache pricing and Free Tier notes: https://aws.amazon.com/elasticache/pricing/

As of the review date, AWS says new Free Tier customers receive credits for a limited period, and RDS Free Plan coverage includes `db.t3.micro` and `db.t4g.micro` for PostgreSQL. ElastiCache differs by signup date: legacy accounts may have a `cache.t3.micro` allowance, while newer accounts use Free/Paid plan credits. Confirm your account's Billing and Free Tier page before leaving anything running 24x7.

## Recommended Low-Cost AWS Shape

For the first shared ALFRED deployment, use the smallest architecture that can prove the real production contracts:

| ALFRED need | AWS service | Free-tier cautious choice |
| --- | --- | --- |
| Django web process | Amazon EC2 | One small Linux instance, Docker-based |
| PostgreSQL | Amazon RDS for PostgreSQL | Single-AZ `db.t3.micro` or `db.t4g.micro` where your account/region marks it eligible |
| Redis cache, broker, result backend | Self-managed Redis on EC2 first; ElastiCache later | Use the EC2 Redis container for strict cost control; move to ElastiCache only after checking credits/cost |
| Celery worker | Same EC2 instance | Separate Docker service/process |
| Celery beat | Same EC2 instance | Separate Docker service/process |
| Static files | WhiteNoise from Django container | Run `collectstatic`; no S3 needed for static files at first |
| Media and proof artifacts | EC2 volume first; S3 later | Add S3 when users upload important documents or you need durable artifact retention |
| TLS | Caddy or Nginx on EC2 | Avoid paid load balancer while testing |
| Cost control | AWS Budgets and billing alerts | Create budget alerts before launch |

This shape is not the final high-availability architecture. It is the lowest-complexity path that still uses PostgreSQL, Redis, Celery worker, and Celery beat.

## Environment Template

Use `config/aws.env.example` as the production env template. Replace every placeholder and provide it to the EC2 container runtime, systemd environment file, ECS task definition, or another secret manager.

Minimum required variables:

- `ALFRED_LOCAL_RUNTIME=false`
- `DEBUG=false`
- `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_ENGINE=django.db.backends.postgresql`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
- `CACHE_BACKEND=django.core.cache.backends.redis.RedisCache`
- `CACHE_LOCATION`
- `REDIS_URL`
- `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true`

Keep `.env` files out of Git. Commit only the example templates.

For the raw-document retention policy and developer access boundary, see [Data Privacy And Storage](DATA_PRIVACY_AND_STORAGE.md).

## Local Production-Style Validation

Use Docker Compose to prove ALFRED can boot with PostgreSQL, Redis, web, worker, and beat before touching AWS:

```bash
docker compose -f docker-compose.aws-local.yml up --build
```

Create the first admin user:

```bash
docker compose -f docker-compose.aws-local.yml exec web python manage.py createsuperuser
```

Run local diagnostics:

```bash
docker compose -f docker-compose.aws-local.yml exec web python manage.py check
docker compose -f docker-compose.aws-local.yml exec web python manage.py makemigrations --check --dry-run
docker compose -f docker-compose.aws-local.yml exec web python scripts/exercise_materialized_cache_traffic.py --repetitions 3
```

The compose file intentionally disables HTTPS-only settings for `http://localhost:8000`, so it is not accepted as production security proof.

## AWS Manual Deployment Steps

1. Create an AWS budget alert before provisioning services.
2. Create an EC2 Linux instance and install Docker plus Docker Compose.
3. Create an RDS PostgreSQL instance, using a free-tier eligible micro class only if AWS marks it eligible in your account and region.
4. Decide Redis mode:
   - lowest cost: run Redis on the same EC2 instance as a Docker service
   - managed later: use ElastiCache Redis OSS or Valkey after checking whether it consumes credits or becomes paid
5. Clone the repo on EC2 and create a real `.env` from `config/aws.env.example`.
6. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the real domain.
7. Run migrations and collect static files.
8. Start web, worker, and beat as separate long-running services.
9. Configure TLS through Caddy/Nginx or another HTTPS layer.
10. Run browser-regression CI from GitHub Actions and keep `artifacts/browser/browser_regression_summary.ci-chrome.json`.
11. Exercise materialized cache traffic against the deployed/shared Redis cache.
12. Run `python scripts/run_production_readiness_probe.py --require-ready` in the deployed environment.
13. Open Project Details and confirm Deployment Readiness and Production Blockers reflect the recorded proof.

## Blocker-To-Proof Checklist

| Production blocker | Required AWS setup | Proof command or artifact |
| --- | --- | --- |
| Production database config | RDS PostgreSQL env vars set in runtime | `python manage.py check` plus Project Details readiness snapshot |
| Shared cache config | Redis-backed `CACHE_BACKEND` and `CACHE_LOCATION` | `python manage.py check` plus readiness probe cache section |
| Celery config | `REDIS_URL` points to deployed Redis and beat schedule remains present | `python manage.py check` plus readiness probe Celery section |
| Production security config | `DEBUG=false`, HTTPS, secure cookies, HSTS, real hosts and CSRF origins | readiness probe security section |
| Database runtime proof | migrations applied against RDS and connection usable | `python scripts/run_production_readiness_probe.py --require-ready` |
| Shared cache runtime proof | Redis read/write probe succeeds | `python scripts/run_production_readiness_probe.py --require-ready` |
| Celery worker and beat proof | worker responds to ping and beat schedule is loaded | `python scripts/run_production_readiness_probe.py --require-ready` |
| Production cache traffic proof | all materialized namespaces exercised through shared Redis under deployed traffic | `python scripts/exercise_materialized_cache_traffic.py --allow-live-external` then readiness probe |
| Browser CI proof | GitHub browser-regression workflow records zero skipped Selenium tests | `artifacts/browser/browser_regression_summary.ci-chrome.json` |

## Notes For Hybrid Browser App

The user-facing app remains browser-based. The cloud runs the main Django brain, PostgreSQL, Redis, Celery worker, and Celery beat. A future desktop launcher should only open the hosted app URL or a local browser shell; it should not own the canonical intelligence store.

Do not raise Deployment Readiness to 100% from local SQLite, local-memory cache, placeholder proof files, or compose-only localhost runs.

## Git Pull Deployment Pipeline

Use [AWS Pull Deployment Pipeline](AWS_DEPLOY_PIPELINE.md) when you want developers to push code to GitHub and have EC2 pull the requested commit. The pipeline uses:

- `.github/workflows/aws-deploy.yml`
- `scripts/deploy_aws_pull.sh`
- `docker-compose.aws.yml`
- GitHub Actions SSH secrets
- a read-only GitHub deploy key stored on EC2

This closes the code-delivery path only. It does not close production readiness until the runtime proof contract is accepted.
