# AWS Free Tier Only Deployment

Last reviewed: 2026-08-09

This is ALFRED's strict AWS Free Tier path. It avoids managed services that can become paid unexpectedly and runs the full app on one EC2 host.

## Rule

Do not create RDS, ElastiCache, Application Load Balancer, NAT Gateway, Route 53 hosted zones, ECR, S3 buckets, or paid monitoring until the AWS Billing and Free Tier console confirms they are covered for this account.

The default free-tier-only deployment is:

| Need | Service |
| --- | --- |
| Web server | One Free Tier eligible EC2 Linux instance |
| Django app | Docker container on EC2 |
| PostgreSQL | Docker `postgres:16-alpine` service on EC2 |
| Redis cache and broker | Docker `redis:7-alpine` service on EC2 |
| Celery worker | Docker container on EC2 |
| Celery beat | Docker container on EC2 |
| Static files | WhiteNoise/static volume on EC2 |
| Uploaded raw extraction documents | Deleted after extraction |
| TLS | Free Caddy/Nginx plus Let's Encrypt, only if you already have a domain |

## Files

- `docker-compose.aws-free-tier.yml`
- `config/aws-free-tier.env.example`
- `scripts/deploy_aws_pull.sh`
- `.github/workflows/aws-deploy.yml`

Set the GitHub Actions secret `AWS_COMPOSE_FILE` to:

```text
docker-compose.aws-free-tier.yml
```

Set `AWS_ENV_FILE` to:

```text
/etc/alfred/alfred.env
```

## What This Can Prove

This path can prove ALFRED is using PostgreSQL, Redis, Celery worker, and Celery beat in a real cloud runtime. It is not high availability. The database and Redis live on one EC2 volume, so backup discipline matters.

Project Details must not mark full deployment readiness unless the deployed environment records:

- non-sqlite PostgreSQL runtime proof
- Redis cache read/write proof
- Redis-backed Celery worker ping
- Celery beat schedule proof
- HTTPS/security proof
- browser CI Chrome proof
- materialized cache traffic proof

## Cost Guardrails

- Use one EC2 instance only.
- Keep EBS storage within the free allocation shown in your AWS Billing console.
- Do not allocate Elastic IP addresses unless you accept the IPv4 charge.
- Do not create NAT Gateway or Application Load Balancer.
- Do not use ElastiCache unless the Billing console confirms free coverage.
- Do not use RDS unless the Billing console confirms free coverage.
- Do not use S3 for uploaded documents in this path.
- Keep AWS Budgets and billing alerts enabled before deployment.

## Manual Steps

1. In AWS Billing, confirm the account is on a Free plan or has active Free Tier credits.
2. Create a budget alert before provisioning resources.
3. Enable MFA for the root user.
4. Create a non-root admin identity for daily AWS work.
5. Create one Free Tier eligible EC2 Linux instance in `ap-south-1`.
6. Keep storage small enough for the free EBS allocation.
7. Allow SSH only from your IP.
8. Allow HTTP/HTTPS only if exposing the app publicly.
9. Install Git, Docker, Docker Compose plugin, and curl on EC2.
10. Create `/etc/alfred/alfred.env` from `config/aws-free-tier.env.example`.
11. Set `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true`.
12. Configure GitHub Actions secrets from `docs/AWS_DEPLOY_PIPELINE.md`.
13. Run the `AWS Pull Deploy` workflow.
14. Run cache traffic and production readiness proof commands on EC2.

## Production Limits

This is the cheapest AWS proof path, not the strongest production architecture. Remaining limits:

- one EC2 failure can take down web, PostgreSQL, Redis, worker, and beat
- backups are your responsibility
- scaling is limited by one small instance
- HTTPS needs a real domain for normal browser trust
- public IPv4 can still incur charges depending on current AWS pricing and account plan
