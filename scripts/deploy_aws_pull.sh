#!/usr/bin/env bash
set -euo pipefail

log() {
  printf '[alfred-deploy] %s\n' "$*"
}

fail() {
  printf '[alfred-deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required on the EC2 host"
}

configure_git_safe_directory() {
  if [ -d "$DEPLOY_DIR/.git" ] && ! git config --global --get-all safe.directory | grep -Fx -- "$DEPLOY_DIR" >/dev/null 2>&1; then
    git config --global --add safe.directory "$DEPLOY_DIR"
  fi
}

DEPLOY_DIR="${ALFRED_DEPLOY_DIR:-/opt/alfred}"
REPO_URL="${ALFRED_REPO_URL:-}"
BRANCH="${ALFRED_BRANCH:-master}"
COMMIT_SHA="${ALFRED_COMMIT_SHA:-}"
COMPOSE_FILE="${ALFRED_COMPOSE_FILE:-docker-compose.aws.yml}"
ENV_FILE="${ALFRED_ENV_FILE:-/etc/alfred/alfred.env}"
HEALTH_URL="${ALFRED_HEALTH_URL:-http://127.0.0.1:8000/health/}"
RUN_READINESS_PROBE="${ALFRED_RUN_READINESS_PROBE:-false}"
REQUIRE_READINESS="${ALFRED_REQUIRE_READINESS:-false}"

export HOME="${HOME:-/root}"

require_command git
require_command docker
require_command curl
configure_git_safe_directory

if ! docker compose version >/dev/null 2>&1; then
  fail "docker compose plugin is required on the EC2 host"
fi

if [ -z "$REPO_URL" ] && [ ! -d "$DEPLOY_DIR/.git" ]; then
  fail "ALFRED_REPO_URL is required for the first clone"
fi

if [ ! -d "$DEPLOY_DIR/.git" ]; then
  if [ -d "$DEPLOY_DIR" ] && [ "$(find "$DEPLOY_DIR" -mindepth 1 -maxdepth 1 2>/dev/null | head -n 1)" ]; then
    fail "$DEPLOY_DIR exists but is not a git checkout"
  fi
  log "cloning $REPO_URL into $DEPLOY_DIR"
  mkdir -p "$(dirname "$DEPLOY_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$DEPLOY_DIR"
fi

cd "$DEPLOY_DIR"

if ! git diff --quiet || ! git diff --cached --quiet; then
  fail "$DEPLOY_DIR has uncommitted changes; commit or clean them before deploying"
fi

log "fetching origin/$BRANCH"
git fetch origin "$BRANCH" --tags

if [ -n "$COMMIT_SHA" ]; then
  log "checking out requested commit $COMMIT_SHA"
  git checkout --detach "$COMMIT_SHA"
else
  log "fast-forwarding $BRANCH"
  git checkout "$BRANCH"
  git pull --ff-only origin "$BRANCH"
fi

[ -f "$COMPOSE_FILE" ] || fail "$COMPOSE_FILE not found in $DEPLOY_DIR"
[ -f "$ENV_FILE" ] || fail "$ENV_FILE not found; create it from config/aws.env.example with real secrets"
export ALFRED_RUNTIME_ENV_FILE="$ENV_FILE"

COMPOSE=(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE")

log "building containers"
"${COMPOSE[@]}" build --pull

log "starting web, worker, and beat"
"${COMPOSE[@]}" up -d --remove-orphans

log "running Django deployment checks inside the web container"
"${COMPOSE[@]}" exec -T web python manage.py check
"${COMPOSE[@]}" exec -T web python manage.py makemigrations --check --dry-run

log "checking health endpoint at $HEALTH_URL"
for attempt in $(seq 1 30); do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    log "health endpoint is healthy"
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    "${COMPOSE[@]}" ps
    fail "health endpoint did not become healthy"
  fi
  sleep 2
done

if [ "$RUN_READINESS_PROBE" = "true" ]; then
  log "running production readiness probe"
  if [ "$REQUIRE_READINESS" = "true" ]; then
    "${COMPOSE[@]}" exec -T web python scripts/run_production_readiness_probe.py --require-ready
  else
    "${COMPOSE[@]}" exec -T web python scripts/run_production_readiness_probe.py || true
  fi
fi

log "deployment status"
"${COMPOSE[@]}" ps
log "deployed ${COMMIT_SHA:-origin/$BRANCH}"
