# Local hosting

For the selected native Windows setup, use [Native Windows](NATIVE_WINDOWS.md):
Waitress, Huey and SQLite start together from a double-click launcher or the
standalone installer. The rest of this document describes the optional Docker
Compose alternative.

ALFRED runs on the local host or a trusted LAN. The Docker Compose stack runs
Django, PostgreSQL, Redis, a Celery worker, and the beat scheduler, with persistent
volumes for application data and files.

## First run

Install/start Docker Desktop and confirm `docker compose version` works in
PowerShell. From the repository root, create the local environment file if it
does not already exist:

```powershell
if (-not (Test-Path config\local.env)) {
    Copy-Item config\local.env.example config\local.env
}
```

Edit `config/local.env` before using real data:

- Replace `DJANGO_SECRET_KEY` and `DB_PASSWORD` with long random values.
- Keep `DB_NAME` and `DB_USER` consistent with the database you create.
- Set `ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION` to match your retention
  choice; `true` deletes raw uploaded PDFs/images after extraction.
- For LAN access, add `ALFRED_BIND_ADDRESS=<host-LAN-IP>`, add that IP to
  `ALLOWED_HOSTS`, and add `http://<host-LAN-IP>:8000` to
  `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS`. Allow inbound traffic only
  from trusted devices on the Windows Firewall private-network profile.

The default binding is `127.0.0.1:8000`, so another device cannot reach it until
the LAN binding is configured. `ALFRED_WEB_PORT` can override the host port; use
that port in the trusted origins and browser URLs too. The optional
`ALFRED_WEB_WORKERS`, `ALFRED_WEB_TIMEOUT`, and `ALFRED_WORKER_CONCURRENCY`
settings control web workers, request timeout, and worker concurrency.

Always pass `--env-file config/local.env`: Compose needs it for database and
port interpolation as well as the environment loaded inside app containers.
Avoid printing `docker compose config` without `--quiet`; the expanded output
can contain secrets.

```powershell
docker compose --env-file config/local.env -f docker-compose.local.yml config --quiet
docker compose --env-file config/local.env -f docker-compose.local.yml up --build -d
docker compose --env-file config/local.env -f docker-compose.local.yml exec web python manage.py createsuperuser
```

Open `http://localhost:8000/` with the default binding, or
`http://<host-LAN-IP>:8000/` with a LAN binding. PostgreSQL's initialization
variables apply only when its volume is first created; editing `DB_PASSWORD`
later does not change the password already stored by PostgreSQL.

## Day-to-day commands

Start or stop services while keeping their volumes:

```powershell
docker compose --env-file config/local.env -f docker-compose.local.yml up -d
docker compose --env-file config/local.env -f docker-compose.local.yml down
```

Inspect services and logs:

```powershell
docker compose --env-file config/local.env -f docker-compose.local.yml ps
docker compose --env-file config/local.env -f docker-compose.local.yml logs -f web worker beat
```

After updating code, rebuild/recreate the services with `up --build -d`. The web
startup applies database migrations and collects static files; worker and beat
wait for web health. Preserve a backup before changes that require migrations.

Run application and migration checks:

```powershell
docker compose --env-file config/local.env -f docker-compose.local.yml exec web python manage.py check
docker compose --env-file config/local.env -f docker-compose.local.yml exec web python manage.py migrate --check
docker compose --env-file config/local.env -f docker-compose.local.yml exec web python manage.py makemigrations --check --dry-run
```

## Repeatable runtime verification

Using the host's Python 3.12+ environment, run:

```powershell
.\.venv\Scripts\python.exe scripts/local_stack_ops.py verify
```

This checks Docker access, Compose configuration, all five service health
statuses, applied migrations, Django checks, HTTP liveness, Redis, and worker
response. It writes `artifacts/ops/local_stack_verification.json` on the host
and exits with status 1 if validation fails. The command does not start or stop
services or apply migrations. A missing Docker CLI, daemon, or environment file
is recorded as a blocker.

An accepted result confirms the checks at that moment. Complete these separate
operational checks before claiming recovery and sustained operation:

1. Run a backup and its isolated restore check as described in
   [Backup and restore](BACKUP_AND_RESTORE.md).
2. In an agreed maintenance window, restart the host, start Docker Desktop if
   needed, and rerun verification. Confirm accounts and retained files persist.
   Docker restart policies take effect once the Docker engine is running.
3. Request the configured URL from a second trusted LAN device if LAN access is
   required.
4. Observe the relevant scheduled job outcomes over their actual schedule;
   worker ping and a running beat process alone do not prove jobs completed.

The optional application dependency probe writes inside the artifacts volume:

```powershell
docker compose --env-file config/local.env -f docker-compose.local.yml exec web python scripts/run_production_readiness_probe.py
```

Do not use `--require-ready` for normal LAN hosting unless you intentionally
configured its HTTPS controls. The strict probe expects HTTPS redirect, secure
cookies, and HSTS.

### Isolated synthetic cache benchmark

To exercise larger dashboard histories without using configured application
data or Redis:

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_local_cache.py
```

The script creates a temporary SQLite database, a private local-memory cache,
and 3,000 synthetic expense rows plus dashboard fixtures. It disables startup
training and network access, runs ten sequential requests per endpoint plus
internal cache checks, then removes temporary storage. The report at
`artifacts/cache/isolated_synthetic_benchmark.json` records behavior for all 21
cache namespaces and endpoint latency. This measures a single synthetic user
through Django's test client; Redis, simultaneous users, actual external data,
and trained-model performance still require separate evidence.

## Persistence and backups

Compose declares these logical volume names:

- `alfred_local_postgres`
- `alfred_local_redis`
- `alfred_local_media`
- `alfred_local_artifacts`
- `alfred_local_staticfiles`
- `alfred_local_models`

Docker prefixes the actual names with the Compose project name (`alfred-local`
by default). Host folders with similar names are separate from these volumes.
Do not use `down -v` unless you intend to delete this data.

Use the paired PostgreSQL and file backup helper, followed by the isolated
restore check in [Backup and restore](BACKUP_AND_RESTORE.md). A database-only
dump omits retained media, trained models, and runtime artifacts.

## Local access and secrets

- Keep `config/local.env` untracked and protect the host's user account.
- Keep port `8000` off the public internet and restrict LAN access to trusted
  devices.
- Give family members separate ALFRED accounts.
- Keep a protected backup on a separate disk, including separately stored
  runtime configuration needed for recovery.

## Optional native development mode

For development without Docker:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

This uses native settings and may use SQLite and local-memory cache depending
on your local configuration. Worker and beat processes need to be run
separately if required. Native data has its own recovery procedure in
[Backup and restore](BACKUP_AND_RESTORE.md).
