# AWS Deployment Guide

Last reviewed: 2026-08-09

This guide prepares ALFRED for an AWS hybrid/cloud deployment without marking it production-ready before proof exists. Use it with `docs/PRODUCTION_READINESS.md`, [AWS Free Tier Only Deployment](AWS_FREE_TIER_ONLY.md), and Project Details.

## Free Tier Reality

AWS is usable for ALFRED, but do not treat every AWS managed service as free for a Django app with PostgreSQL, Redis, and always-running Celery jobs.

Current AWS source pages:

- AWS Free Tier: https://aws.amazon.com/free/
- AWS Free Tier database offers: https://aws.amazon.com/free/database/
- Amazon ElastiCache pricing and Free Tier notes: https://aws.amazon.com/elasticache/pricing/
- Amazon EBS pricing and Free Tier notes: https://aws.amazon.com/ebs/pricing/

As of the review date, AWS says new Free Tier customers receive credits for a limited period. RDS and ElastiCache coverage depends on the account plan, signup date, region, and service-specific Free Tier rules. Confirm your account's Billing and Free Tier page before leaving anything running 24x7.

## Recommended Free Tier Only Shape

For the first shared ALFRED deployment, use the strict Free Tier shape first:

| ALFRED need | AWS service | Free-tier-only choice |
| --- | --- | --- |
| Django web process | Amazon EC2 | One small Linux instance, Docker-based |
| PostgreSQL | Docker on EC2 | `postgres:16-alpine` service on the same EC2 instance |
| Redis cache, broker, result backend | Docker on EC2 | `redis:7-alpine` service on the same EC2 instance |
| Celery worker | Same EC2 instance | Separate Docker service/process |
| Celery beat | Same EC2 instance | Separate Docker service/process |
| Static files | WhiteNoise from Django container | Run `collectstatic`; no S3 needed for static files at first |
| Media and proof artifacts | EC2 volume | Keep raw extraction uploads deleted after parsing |
| TLS | Caddy or Nginx on EC2 | Avoid paid load balancer |
| Cost control | AWS Budgets and billing alerts | Create budget alerts before launch |

This shape is not the final high-availability architecture. It is the lowest-cost path that still uses PostgreSQL, Redis, Celery worker, and Celery beat. RDS, ElastiCache, Application Load Balancer, NAT Gateway, Route 53, ECR, and S3 are opt-in only after the AWS Billing console proves they are covered or you accept the cost.

## Environment Template

For strict Free Tier, use `config/aws-free-tier.env.example` with `docker-compose.aws-free-tier.yml`. For external managed PostgreSQL/Redis, use `config/aws.env.example` with `docker-compose.aws.yml`.

Minimum required variables:

- `ALFRED_LOCAL_RUNTIME=false`
- `DEBUG=false`
- `DJANGO_SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `DB_ENGINE=django.db.backends.postgresql`
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`; strict Free Tier uses `DB_HOST=postgres`
- `CACHE_BACKEND=django.core.cache.backends.redis.RedisCache`
- `CACHE_LOCATION`; strict Free Tier uses `redis://redis:6379/1`
- `REDIS_URL`; strict Free Tier uses `redis://redis:6379/0`
- `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true`
- `SECURE_PROXY_SSL_HEADER_ENABLED=true` when Django runs behind Caddy/Nginx TLS termination

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
2. Create one Free Tier eligible EC2 Linux instance and install Docker plus Docker Compose.
3. Do not create RDS or ElastiCache for the Free Tier only path.
4. Clone the repo on EC2 and create `/etc/alfred/alfred.env` from `config/aws-free-tier.env.example`.
5. Set `AWS_COMPOSE_FILE=docker-compose.aws-free-tier.yml` in GitHub Actions secrets.
6. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the real domain or accepted test host.
7. Run migrations and collect static files.
8. Start postgres, redis, web, worker, and beat as separate Docker services.
9. Configure TLS through Caddy/Nginx or another HTTPS layer.
10. Run browser-regression CI from GitHub Actions and keep `artifacts/browser/browser_regression_summary.ci-chrome.json`.
11. Exercise materialized cache traffic against the deployed/shared Redis cache.
12. Run `python scripts/run_production_readiness_probe.py --require-ready` in the deployed environment.
13. Open Project Details and confirm Deployment Readiness and Production Blockers reflect the recorded proof.

## Blocker-To-Proof Checklist

| Production blocker | Required AWS setup | Proof command or artifact |
| --- | --- | --- |
| Production database config | PostgreSQL env vars set in runtime; strict Free Tier may use Docker PostgreSQL on EC2 | `python manage.py check` plus Project Details readiness snapshot |
| Shared cache config | Redis-backed `CACHE_BACKEND` and `CACHE_LOCATION` | `python manage.py check` plus readiness probe cache section |
| Celery config | `REDIS_URL` points to deployed Redis and beat schedule remains present | `python manage.py check` plus readiness probe Celery section |
| Production security config | `DEBUG=false`, HTTPS, secure cookies, HSTS, real hosts and CSRF origins | readiness probe security section |
| Database runtime proof | migrations applied against PostgreSQL and connection usable | `python scripts/run_production_readiness_probe.py --require-ready` |
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
- `docker-compose.aws-free-tier.yml` for strict Free Tier
- `docker-compose.aws.yml` for external managed PostgreSQL/Redis
- GitHub Actions SSH secrets
- a read-only GitHub deploy key stored on EC2

This closes the code-delivery path only. It does not close production readiness until the runtime proof contract is accepted.
