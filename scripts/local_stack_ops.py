"""Safe local Compose verification, quiesced backups, and isolated restore checks.

No command restores over the live database or prints the resolved environment.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {"web", "worker", "beat", "postgres", "redis"}
WRITERS = ("beat", "worker", "web")
ARCHIVE_ROOTS = {"media", "ml_models", "artifacts"}
COUNT_SQL = r"""SELECT format('SELECT %L, count(*) FROM %I.%I;',
table_schema || '.' || table_name, table_schema, table_name)
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
ORDER BY table_name
\gexec
"""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class OperationError(RuntimeError):
    pass


class Compose:
    def __init__(self, env_file=ROOT / "config/local.env"):
        self.env_file = Path(env_file).resolve()
        self.env = dict(os.environ, ALFRED_LOCAL_ENV_FILE=str(self.env_file))
        self.prefix = ["docker", "compose", "--env-file", str(self.env_file),
                       "-f", str(ROOT / "docker-compose.local.yml")]

    def run(self, *args, input_data=None, output_file=None, timeout=180):
        # Binary pipes preserve custom-format pg_dump and tar archives on Windows.
        result = subprocess.run(self.prefix + list(args), cwd=ROOT, env=self.env,
                                input=input_data, stdout=output_file or subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=False)
        if result.returncode:
            # Docker stderr may contain resolved configuration; do not persist it.
            raise OperationError(f"Compose {args[0]} failed (exit {result.returncode}); inspect service logs locally")
        return (result.stdout or b"").decode("utf-8", errors="replace")

    def preflight(self):
        if not shutil.which("docker"):
            raise OperationError("Docker CLI is unavailable; install/start Docker Desktop before runtime validation")
        if not self.env_file.is_file():
            raise OperationError("Local environment file is missing; create it from config/local.env.example")
        self.run("version")
        self.run("config", "--quiet")
        self.run("ps", timeout=30)  # daemon connection, without exposing config

    def status(self):
        raw = self.run("ps", "--all", "--format", "json").strip()
        if not raw:
            return {}
        rows = json.loads(raw) if raw.startswith("[") else [json.loads(line) for line in raw.splitlines()]
        return {row["Service"]: {key: row.get(key, "") for key in ("State", "Health")}
                for row in rows if row.get("Service") in SERVICES}

    def sql(self, sql, database=None):
        if database is not None:
            validate_restore_name(database)
        target = database or '"$POSTGRES_DB"'
        command = f'exec psql -X -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d {target}'
        return self.run("exec", "-T", "postgres", "sh", "-c", command, input_data=sql.encode())


def validate_restore_name(name):
    if not re.fullmatch(r"alfred_restore_check_[a-f0-9]{32}", name):
        raise ValueError("Restore checks only accept generated isolated database names")


def row_counts(compose, database=None):
    return {name: int(count) for name, count in
            (line.rsplit("|", 1) for line in compose.sql(COUNT_SQL, database).splitlines() if line)}


def inspect_archive(path, destination=None):
    files = {}
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
        seen = set()
        for member in members:
            parts = PurePosixPath(member.name).parts
            if (not parts or parts[0] not in ARCHIVE_ROOTS or ".." in parts
                    or PurePosixPath(member.name).is_absolute() or "\\" in member.name or ":" in member.name
                    or not (member.isfile() or member.isdir())):
                raise OperationError("Archive contains an unsafe path or non-regular entry")
            normalized = os.path.normcase("/".join(parts))
            if normalized in seen:
                raise OperationError("Archive contains duplicate paths")
            seen.add(normalized)
            if member.isfile():
                with archive.extractfile(member) as stream:
                    files[member.name] = {"size": member.size,
                                          "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}
        if destination is not None:
            archive.extractall(destination, members=members, filter="data")
            for name, metadata in files.items():
                if digest(Path(destination) / name) != metadata["sha256"]:
                    raise OperationError("Extracted file integrity check failed")
    return files


def read_manifest(folder):
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("complete") is not True
            or manifest.get("kind") != "local_compose_backup" or manifest.get("version") != 1):
        raise OperationError("Backup is incomplete or unsupported")
    checksums = manifest.get("sha256")
    counts = manifest.get("row_counts")
    files = manifest.get("files")

    def valid_digest(value):
        return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value) is not None

    if (not isinstance(checksums, dict)
            or not all(valid_digest(checksums.get(name)) for name in ("database.dump", "files.tar.gz"))
            or not isinstance(counts, dict)
            or not all(isinstance(name, str) and type(count) is int and count >= 0 for name, count in counts.items())
            or not isinstance(files, dict)
            or not all(isinstance(name, str) and isinstance(metadata, dict)
                       and type(metadata.get("size")) is int and metadata["size"] >= 0
                       and valid_digest(metadata.get("sha256")) for name, metadata in files.items())):
        raise OperationError("Backup manifest is missing valid checksums, row counts, or file metadata")
    return manifest


def backup(compose, output_root):
    compose.preflight()
    status = compose.status()
    if status.get("postgres", {}).get("State") != "running":
        raise OperationError("PostgreSQL must be running before backup")
    running_writers = [name for name in WRITERS if status.get(name, {}).get("State") == "running"]
    destination = Path(output_root).resolve() / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    destination.mkdir(parents=True, exist_ok=False)
    summary = {"version": 1, "kind": "local_compose_backup", "generated_at_utc": utc_now(),
               "complete": False, "writers_paused": running_writers,
               "writers_resumed": not running_writers,
               "excluded": ["runtime secrets", "Redis queues/cache", "rebuildable static files"]}
    try:
        if running_writers:
            # Allow workers to finish in-flight jobs before copying related files.
            compose.run("stop", "--timeout", "120", *running_writers, timeout=180)
        summary["row_counts"] = row_counts(compose)
        with (destination / "database.dump").open("xb") as stream:
            compose.run("exec", "-T", "postgres", "sh", "-c",
                        'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom',
                        output_file=stream, timeout=1800)
        with (destination / "files.tar.gz").open("xb") as stream:
            compose.run("run", "--rm", "--no-deps", "-T", "--entrypoint", "tar", "web",
                        "-czf", "-", "-C", "/app", "media", "ml_models", "artifacts",
                        output_file=stream, timeout=1800)
        summary["files"] = inspect_archive(destination / "files.tar.gz")
        summary["sha256"] = {name: digest(destination / name) for name in ("database.dump", "files.tar.gz")}
        summary["complete"] = True
    finally:
        try:
            if running_writers:
                compose.run("start", *reversed(running_writers))
            summary["writers_resumed"] = True
        finally:
            write_json(destination / "manifest.json", summary)
    return {"complete": True, "backup_directory": str(destination)}


def restore_check(compose, backup_directory):
    folder = Path(backup_directory).resolve()
    manifest = read_manifest(folder)
    for name in ("database.dump", "files.tar.gz"):
        if digest(folder / name) != manifest["sha256"][name]:
            raise OperationError(f"Backup checksum mismatch: {name}")
    # Reject unsafe or inconsistent file archives before creating any database.
    with tempfile.TemporaryDirectory(prefix="alfred-restore-files-") as destination:
        files = inspect_archive(folder / "files.tar.gz", destination)
    if files != manifest["files"]:
        raise OperationError("Restored file manifest differs from the backup")
    compose.preflight()
    database = "alfred_restore_check_" + uuid.uuid4().hex
    validate_restore_name(database)
    summary = {"kind": "isolated_restore_check", "generated_at_utc": utc_now(), "accepted": False,
               "database": database, "live_database_modified": False, "cleanup_complete": False}
    created = False
    checks_passed = False
    try:
        compose.run("exec", "-T", "postgres", "sh", "-c",
                    'exec createdb -U "$POSTGRES_USER" --template=template0 ' + database)
        created = True
        # Stream the binary dump through stdin; never use a PowerShell text pipe.
        with (folder / "database.dump").open("rb") as stream:
            result = subprocess.run(compose.prefix + ["exec", "-T", "postgres", "sh", "-c",
                                    'exec pg_restore -U "$POSTGRES_USER" --exit-on-error --no-owner -d ' + database],
                                    cwd=ROOT, env=compose.env, stdin=stream, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE, timeout=1800, check=False)
        if result.returncode:
            raise OperationError("Isolated pg_restore failed; live database was not a restore target")
        summary["row_counts"] = row_counts(compose, database)
        if summary["row_counts"] != manifest["row_counts"]:
            raise OperationError("Restored table row counts differ from the backup")
        summary["restored_file_count"] = len(files)
        checks_passed = True
    finally:
        try:
            if created:
                # Name is generated locally and validated again before the sole DROP operation.
                validate_restore_name(database)
                compose.run("exec", "-T", "postgres", "sh", "-c", 'exec dropdb -U "$POSTGRES_USER" ' + database)
            summary["cleanup_complete"] = True
            summary["accepted"] = checks_passed
        finally:
            write_json(folder / "restore_check.json", summary)
    return summary


def verify(compose, proof_path):
    summary = {"kind": "local_stack_verification", "generated_at_utc": utc_now(),
               "accepted": False, "checks": {}, "blockers": [],
               "remaining": ["host restart/persistence drill", "second-device LAN request",
                             "isolated backup restore check", "sustained scheduled job outcomes"]}
    try:
        compose.preflight()
        summary["services"] = compose.status()
        summary["checks"]["services_healthy"] = all(
            summary["services"].get(name, {}).get("State") == "running"
            and summary["services"].get(name, {}).get("Health") == "healthy" for name in SERVICES)
        checks = {
            "migrations_current": ["exec", "-T", "web", "python", "manage.py", "migrate", "--check"],
            "django_checks": ["exec", "-T", "web", "python", "manage.py", "check"],
            "http_liveness": ["exec", "-T", "web", "curl", "-fsS", "-o", "/dev/null", "http://127.0.0.1:8000/health/live/"],
            "redis_ping": ["exec", "-T", "redis", "redis-cli", "ping"],
            "worker_ping": ["exec", "-T", "worker", "celery", "-A", "alfred_ai", "inspect", "ping", "--timeout=5"],
        }
        for name, command in checks.items():
            try:
                compose.run(*command)
                summary["checks"][name] = True
            except (OperationError, subprocess.TimeoutExpired, OSError):
                summary["checks"][name] = False
        summary["accepted"] = all(summary["checks"].values())
        summary["blockers"] = [name for name, passed in summary["checks"].items() if not passed]
    except (OperationError, subprocess.TimeoutExpired, OSError) as exc:
        summary["blockers"].append(str(exc) if isinstance(exc, OperationError) else type(exc).__name__)
    write_json(proof_path, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / "config/local.env")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("verify")
    check.add_argument("--proof-path", type=Path, default=ROOT / "artifacts/ops/local_stack_verification.json")
    save = commands.add_parser("backup")
    save.add_argument("--output-root", type=Path, default=ROOT / "artifacts/backups")
    restore = commands.add_parser("restore-check")
    restore.add_argument("backup_directory", type=Path)
    args = parser.parse_args()
    compose = Compose(args.env_file)
    try:
        if args.command == "verify":
            result = verify(compose, args.proof_path)
        elif args.command == "backup":
            result = backup(compose, args.output_root)
        else:
            result = restore_check(compose, args.backup_directory)
        print(json.dumps(result, indent=2))
        return 0 if result.get("accepted", result.get("complete", False)) else 1
    except (OperationError, OSError, ValueError, tarfile.TarError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"complete": False, "error": str(exc) if isinstance(exc, OperationError) else type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
