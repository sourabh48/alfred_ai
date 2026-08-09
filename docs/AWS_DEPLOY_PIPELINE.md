# AWS Pull Deployment Pipeline

This pipeline lets developers push code to GitHub, then GitHub Actions connects to the EC2 host and runs an EC2-side deploy script. The EC2 host pulls the requested commit from GitHub, rebuilds the Docker services, runs Django checks, and verifies `/health/`.

It does not store AWS access keys in GitHub. It uses SSH to reach the server.

## Files

- `.github/workflows/aws-deploy.yml` - GitHub Actions workflow.
- `scripts/deploy_aws_pull.sh` - EC2-side pull/build/restart script.
- `docker-compose.aws.yml` - production EC2 web/worker/beat compose file using external PostgreSQL and Redis from `.env`.
- `config/aws.env.example` - production env template.

## EC2 One-Time Setup

1. Create an EC2 Linux host.
2. Install Git, Docker, Docker Compose plugin, and curl.
3. Create the deployment directory:

```bash
sudo mkdir -p /opt/alfred
sudo chown "$USER":"$USER" /opt/alfred
```

4. Generate a GitHub deploy key on EC2:

```bash
ssh-keygen -t ed25519 -C "alfred-ec2-github-pull" -f ~/.ssh/alfred_github_deploy_key
cat ~/.ssh/alfred_github_deploy_key.pub
```

5. Add that public key in GitHub as a read-only Deploy Key for this repository.
6. Add this to `~/.ssh/config` on EC2:

```sshconfig
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/alfred_github_deploy_key
  IdentitiesOnly yes
```

7. Test the GitHub pull path from EC2:

```bash
ssh -T git@github.com
```

8. Create the production env file outside the repo. For strict Free Tier, fill it from `config/aws-free-tier.env.example`, which uses Docker PostgreSQL and Redis on the EC2 host:

```bash
sudo mkdir -p /etc/alfred
sudo nano /etc/alfred/alfred.env
sudo chown "$USER":"$USER" /etc/alfred/alfred.env
chmod 600 /etc/alfred/alfred.env
```

Use `config/aws-free-tier.env.example` as the strict Free Tier template. Set the GitHub secret `AWS_ENV_FILE` to `/etc/alfred/alfred.env`.

## GitHub Secrets

Add these in GitHub repository settings under Actions secrets:

| Secret | Required | Example |
| --- | --- | --- |
| `AWS_EC2_HOST` | yes | `ec2-11-22-33-44.compute-1.amazonaws.com` |
| `AWS_EC2_USER` | yes | `ubuntu` or `ec2-user` |
| `AWS_EC2_SSH_KEY` | yes | private SSH key that can log into EC2 |
| `AWS_EC2_PORT` | no | `22` |
| `AWS_DEPLOY_DIR` | no | `/opt/alfred` |
| `AWS_COMPOSE_FILE` | no | `docker-compose.aws-free-tier.yml` for strict Free Tier, or `docker-compose.aws.yml` for external PostgreSQL/Redis |
| `AWS_ENV_FILE` | recommended | `/etc/alfred/alfred.env` |
| `AWS_HEALTH_URL` | no | `http://127.0.0.1:8000/health/` |

The EC2 SSH key is only for GitHub Actions to reach EC2. The GitHub deploy key generated on EC2 is what lets EC2 pull from GitHub.

## How Deployment Runs

1. Developer pushes to `main` or `master`, or starts `AWS Pull Deploy` manually from GitHub Actions.
2. GitHub Actions SSHes into EC2.
3. EC2 runs `scripts/deploy_aws_pull.sh`.
4. The script clones the repo on first deploy, or fetches the requested branch on later deploys.
5. The script checks out the exact commit from the GitHub workflow.
6. Docker Compose rebuilds and starts `web`, `worker`, and `beat`.
7. The script runs:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

8. The script waits until `/health/` responds successfully.

## Important Safety Rules

- Do not put production secrets in the repository.
- Keep `/etc/alfred/alfred.env` on the EC2 host or in a managed secret store.
- Set `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true` in production so extraction-only raw documents are deleted after parsing.
- Keep the EC2 checkout clean; the deploy script fails if there are uncommitted server-side changes.
- Use GitHub PR checks before merging to the deploy branch.
- Keep Project Details Deployment Readiness separate from successful deploys. A deploy only proves the app restarted; readiness still needs PostgreSQL, Redis, Celery runtime, browser CI, security, and cache traffic proof.
- For strict Free Tier, do not create RDS, ElastiCache, Application Load Balancer, NAT Gateway, Route 53, ECR, or S3 unless the AWS Billing and Free Tier console confirms zero-cost coverage or you explicitly accept the cost.

## Manual First Deploy

After secrets and EC2 setup are done, open GitHub Actions, choose `AWS Pull Deploy`, and run it for the deployment branch. Watch the log for:

- clone or fetch success
- Docker build success
- web/worker/beat containers running
- Django check success
- migration dry-run success
- `/health/` success

Then run the production readiness probe on EC2 after browser CI and cache traffic proof exist:

```bash
cd /opt/alfred
docker compose -f docker-compose.aws-free-tier.yml --env-file /etc/alfred/alfred.env exec -T web python scripts/run_production_readiness_probe.py --require-ready
```

If the probe fails, Project Details should continue to show the remaining production blockers.
