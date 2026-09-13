# Local Hosting

ALFRED is treated as a local or LAN-hosted application. The operating path is local hosting.

## Recommended Local Stack

Use Docker Compose when you want ALFRED to keep running with background jobs:

- Django web app
- PostgreSQL database
- Redis cache and Celery broker
- Celery worker
- Celery beat scheduler
- persistent Docker volumes for database, Redis, uploaded media, static files, and artifacts

This keeps the "main brain" and cron-style jobs on the local host.

## First Run

Prerequisite: install Docker Desktop and make sure `docker compose version` works in PowerShell.

From the repository root:

```powershell
Copy-Item config\local.env.example config\local.env
```

Edit `config\local.env` before using real data:

- set `DJANGO_SECRET_KEY` to a long random value
- if another device will connect over LAN, add the host machine IP to `ALLOWED_HOSTS`
- if another device will connect over LAN, add `http://<host-ip>:8000` to `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS`
- keep `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=true` if raw uploaded PDFs/images should be deleted after parsing

Start the local stack:

```powershell
docker compose -f docker-compose.local.yml up --build -d
```

Create your admin user:

```powershell
docker compose -f docker-compose.local.yml exec web python manage.py createsuperuser
```

Open:

```text
http://localhost:8000/
```

For LAN access, open:

```text
http://<host-machine-ip>:8000/
```

## Day-To-Day Commands

Start:

```powershell
docker compose -f docker-compose.local.yml up -d
```

Stop without deleting data:

```powershell
docker compose -f docker-compose.local.yml down
```

View services:

```powershell
docker compose -f docker-compose.local.yml ps
```

View logs:

```powershell
docker compose -f docker-compose.local.yml logs -f web worker beat
```

Run migrations after pulling new code:

```powershell
docker compose -f docker-compose.local.yml exec web python manage.py migrate
```

Run checks:

```powershell
docker compose -f docker-compose.local.yml exec web python manage.py check
docker compose -f docker-compose.local.yml exec web python manage.py makemigrations --check --dry-run
```

Run the local dependency proof:

```powershell
docker compose -f docker-compose.local.yml exec web python scripts/run_production_readiness_probe.py
```

Do not use `--require-ready` for normal LAN hosting unless you intentionally configured public-production HTTPS settings. The strict probe expects public-production controls such as HTTPS redirect, secure cookies, and HSTS.

## Persistence

Local data is stored in Docker volumes:

- `alfred_local_postgres`
- `alfred_local_redis`
- `alfred_local_media`
- `alfred_local_artifacts`
- `alfred_local_staticfiles`

Do not run `docker compose -f docker-compose.local.yml down -v` unless you intentionally want to delete local ALFRED data.

## Backups

Create a PostgreSQL backup:

```powershell
docker compose -f docker-compose.local.yml exec -T postgres pg_dump -U alfred -d alfred > alfred-backup.sql
```

Restore into an empty local database:

```powershell
Get-Content .\alfred-backup.sql | docker compose -f docker-compose.local.yml exec -T postgres psql -U alfred -d alfred
```

Also back up the Docker media and artifacts volumes if you keep user media or proof artifacts.

## Security Notes

Local hosting is still sensitive because ALFRED stores financial metadata.

- Use a strong Windows login password.
- Do not expose port `8000` to the public internet.
- Use Windows Firewall to allow only trusted private-network devices if LAN access is needed.
- Keep `config/local.env` out of Git.
- Keep raw document deletion enabled if you do not need retained PDFs/images after extraction.
- Linked family users should have their own ALFRED accounts instead of sharing a password.

## Optional Native Development Mode

For quick single-machine development without Docker:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

This mode uses local settings and may use SQLite/local-memory cache depending on your `.env`. It is convenient, but Docker Compose is the better local-hosting path because it runs PostgreSQL, Redis, worker, and beat together.
