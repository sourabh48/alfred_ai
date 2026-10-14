"""One explicit native runtime, authenticated encrypted backup, disposable local restore.

Reads an existing key; never creates/exports/rotates one or opens a passphrase UI.
Only newly created private scratch directories are removed after verified success.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, closing, contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from cryptography.fernet import Fernet
from alfred_native import InstanceLock, parent_is_running, write_json
from apps.ml_engine.services.memory_key import private_directory, protect_key
from scripts import release_gate as release
from scripts.verify_private_recovery import verify

CHUNK = 1024 * 1024
GROUPS = ("config", "media", "ml_models", "artifacts/native/jobs.sqlite3", "artifacts/private-memory-v2")


def no_links(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise release.GateError("linked_recovery_path")
    return path


def private_root(path):
    path = no_links(path)
    if path.exists():
        raise release.GateError("recovery_destination_must_be_new")
    if os.name == "nt":
        private_directory(path, deadline=time.monotonic() + 15)
    else:
        path.mkdir(parents=True, mode=0o700)
    return path


def cipher_from_file(path):
    blob = no_links(path).read_bytes()
    profile_bound = blob.startswith(b"M15DPAPI1\0")
    key = protect_key(blob[10:], decrypt=True) if profile_bound else blob.strip()
    return Fernet(key), "WINDOWS_PROFILE_BOUND" if profile_bound else "PORTABLE_FORMAT_UNVERIFIED"


def database_snapshot(path):
    """Typed row fingerprints preserve money/identity/ownership without publishing values."""
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise release.GateError("sqlite_integrity_failed")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise release.GateError("sqlite_foreign_key_failed")
        tables = db.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        result = {}
        for table, schema in tables:
            hashes = []
            for row in db.execute('SELECT * FROM "' + table.replace('"', '""') + '"'):
                values = [(type(value).__name__, value.hex() if isinstance(value, bytes) else repr(value)) for value in row]
                hashes.append(hashlib.sha256(json.dumps(values).encode()).digest())
                if len(hashes) > 1000000:
                    raise release.GateError("sqlite_row_scan_budget")
            result[table] = {"count": len(hashes), "sha256": hashlib.sha256(b"".join(sorted(hashes))).hexdigest(),
                             "schema_sha256": hashlib.sha256(schema.encode()).hexdigest()}
        return result


def sqlite_copy(source, target, seconds=60):
    deadline = time.monotonic() + seconds
    def progress(*_):
        if time.monotonic() > deadline:
            raise release.GateError("sqlite_backup_timeout")
    with closing(sqlite3.connect(Path(source).resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as original:
        with closing(sqlite3.connect(target)) as copy:
            original.backup(copy, pages=256, progress=progress, sleep=0.05)


@contextmanager
def writer_barriers(runtime, databases):
    """House native locks plus SQLite write reservations prevent cross-file drift."""
    state_path = runtime / "artifacts/native/runtime.json"
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8-sig"))
        if any(parent_is_running(state.get(key, 0)) for key in ("pid", "worker_pid") if isinstance(state.get(key), int)):
            raise release.GateError("native_writer_running")
    with ExitStack() as stack:
        stack.enter_context(InstanceLock(runtime))
        stack.enter_context(InstanceLock(runtime, "worker.lock"))
        for path in databases:
            connection = stack.enter_context(closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True, timeout=0.2)))
            try:
                connection.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError:
                raise release.GateError("sqlite_writer_busy") from None
        yield


def selected_files(runtime):
    files = {"db.sqlite3": no_links(runtime / "db.sqlite3")}
    if not files["db.sqlite3"].is_file():
        raise release.GateError("runtime_database_missing")
    coverage = {}
    for name in GROUPS:
        path = no_links(runtime / name)
        coverage[name] = path.exists()
        candidates = sorted(path.rglob("*")) if path.is_dir() else [path] if path.is_file() else []
        for item in candidates:
            no_links(item)
            if item.is_file() and not item.name.endswith(("-wal", "-shm", "-journal", ".lock", ".tmp")):
                files[item.relative_to(runtime).as_posix()] = item
    if not all(coverage[name] for name in ("config", "media", "artifacts/native/jobs.sqlite3")):
        raise release.GateError("required_recovery_coverage_missing")
    return files, coverage


def create(runtime, destination, key_file, release_id, candidate, baseline, source_repo=None):
    release.new_manifest(release_id, candidate, baseline)
    runtime, destination, key_file = map(no_links, (runtime, destination, key_file))
    if (destination == runtime or destination.is_relative_to(runtime) or runtime.is_relative_to(destination)
            or key_file.is_relative_to(destination) or destination.is_relative_to(ROOT)):
        raise release.GateError("unsafe_backup_destination")
    cipher, key_kind = cipher_from_file(key_file)
    files, coverage = selected_files(runtime)
    databases = [path for path in files.values() if path.suffix.lower() in (".sqlite3", ".sqlite", ".db")]
    destination = private_root(destination)
    scratch = Path(tempfile.mkdtemp(prefix="capture-", dir=destination))
    records, snapshots = [], {}
    metadata = {"schema": 1, "release_id": release_id, "candidate_sha": candidate,
                "production_baseline_sha": baseline, "complete": False, "files": records,
                "coverage": coverage, "database_snapshots": snapshots, "key_kind": key_kind}
    with writer_barriers(runtime, databases):
        for name, source in files.items():
            target = scratch / name
            target.parent.mkdir(parents=True, exist_ok=True)
            is_database = source in databases
            if is_database:
                sqlite_copy(source, target)
                snapshots[name] = database_snapshot(target)
            else:
                before = release.sha256(source)
                shutil.copyfile(source, target)
                if release.sha256(target) != before or release.sha256(source) != before:
                    raise release.GateError("recovery_source_changed")
            records.append({"backup_path": name, "bytes": target.stat().st_size,
                            "sha256": release.sha256(target), "sqlite_snapshot": is_database})
        if source_repo:
            source_repo = no_links(source_repo)
            if release.git(source_repo, "rev-parse", "HEAD") != baseline:
                raise release.GateError("backup_source_baseline_changed")
            for name in release.PROTECTED:
                if (source_repo / name).is_file():
                    before = release.sha256(source_repo / name)
                    target = scratch / "operator-files" / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(no_links(source_repo / name), target)
                    if release.sha256(source_repo / name) != before or release.sha256(target) != before:
                        raise release.GateError("operator_file_changed_during_backup")
                    records.append({"backup_path": target.relative_to(scratch).as_posix(), "bytes": target.stat().st_size,
                                    "sha256": release.sha256(target), "sqlite_snapshot": False})
            bundle = scratch / "source.bundle"
            process = subprocess.run(["git", "-C", str(source_repo), "bundle", "create", str(bundle), "HEAD"],
                                     capture_output=True, timeout=120)
            if process.returncode:
                raise release.GateError("source_recovery_bundle_failed")
            heads = release.git(source_repo, "bundle", "list-heads", str(bundle)).splitlines()
            if heads != [baseline + " HEAD"] or release.git(source_repo, "rev-parse", "HEAD") != baseline:
                raise release.GateError("source_recovery_bundle_identity_failed")
            records.append({"backup_path": "source.bundle", "bytes": bundle.stat().st_size,
                            "sha256": release.sha256(bundle), "sqlite_snapshot": False})
        metadata.update(complete=True, file_count=len(records), total_bytes=sum(r["bytes"] for r in records))
        write_json(scratch / "manifest.json", metadata)
        verify(scratch, scratch_root=destination)
        archive = destination / "recovery.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_STORED) as zipped:
            for index, record in enumerate(records):
                chunks = []
                with (scratch / record["backup_path"]).open("rb") as stream:
                    while content := stream.read(CHUNK):
                        entry = f"payload/{index:06d}/{len(chunks):06d}.fernet"
                        token = cipher.encrypt(content)
                        zipped.writestr(entry, token)
                        chunks.append({"entry": entry, "sha256": hashlib.sha256(token).hexdigest(), "bytes": len(content)})
                record["chunks"] = chunks
            zipped.writestr("manifest.fernet", cipher.encrypt(json.dumps(metadata, sort_keys=True).encode()))
    public = {key: metadata[key] for key in ("schema", "release_id", "candidate_sha", "production_baseline_sha", "file_count", "total_bytes", "key_kind")}
    public.update(archive="recovery.zip", archive_bytes=archive.stat().st_size, archive_sha256=release.sha256(archive), complete=True)
    write_json(destination / "backup.json", public)
    # Independent process: decrypt and restore with the supplied existing key, not capture's in-memory cipher.
    restored = destination / "independent-local-restore"
    process = subprocess.run([sys.executable, str(Path(__file__)), "--backup", str(destination),
                              "--key-file", str(key_file), "--restore", str(restored)], capture_output=True, timeout=300)
    if process.returncode:
        raise release.GateError("independent_local_restore_failed")
    receipt = json.loads(process.stdout)
    if receipt.get("LOCAL_BACKUP_VERIFIED") != "PASS":
        raise release.GateError("independent_local_restore_incomplete")
    if not scratch.resolve().is_relative_to(destination.resolve()) or not scratch.name.startswith("capture-"):
        raise release.GateError("scratch_cleanup_boundary_failed")
    # Only this operation's temporary capture, after independent recovery; never any retained backup.
    shutil.rmtree(scratch)
    write_json(destination / "local-restore.json", receipt)
    return receipt


def restore(backup, key_file, destination):
    backup, key_file, destination = map(no_links, (backup, key_file, destination))
    if destination == backup or destination in backup.parents or destination == ROOT or ROOT in destination.parents:
        raise release.GateError("unsafe_restore_destination")
    public = json.loads((backup / "backup.json").read_text(encoding="utf-8"))
    archive = backup / "recovery.zip"
    if (not public.get("complete") or archive.stat().st_size != public["archive_bytes"]
            or release.sha256(archive) != public["archive_sha256"]):
        raise release.GateError("backup_archive_hash_failed")
    cipher, key_kind = cipher_from_file(key_file)
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist()
        if len(names) != len(set(names)) or len(names) > 100000:
            raise release.GateError("backup_duplicate_or_excessive_volumes")
        if zipped.getinfo("manifest.fernet").file_size > 16 * 1024 * 1024:
            raise release.GateError("encrypted_manifest_budget")
        metadata = json.loads(cipher.decrypt(zipped.read("manifest.fernet")))
        for key in ("schema", "release_id", "candidate_sha", "production_baseline_sha", "file_count", "total_bytes"):
            if metadata.get(key) != public.get(key):
                raise release.GateError("authenticated_manifest_identity_failed")
        records = metadata["files"]
        if len(records) != metadata["file_count"] or sum(r["bytes"] for r in records) != metadata["total_bytes"]:
            raise release.GateError("authenticated_manifest_inventory_failed")
        expected_entries = {"manifest.fernet"}
        destinations = set()
        for record in records:
            relative = PurePosixPath(record["backup_path"])
            if (relative.is_absolute() or ".." in relative.parts or "\\" in str(relative) or ":" in str(relative)
                    or not relative.parts or str(relative).casefold() in destinations):
                raise release.GateError("unsafe_restore_manifest_path")
            destinations.add(str(relative).casefold())
            for chunk in record["chunks"]:
                entry = chunk["entry"]
                if entry in expected_entries or not re.fullmatch(r"payload/\d{6}/\d{6}\.fernet", entry):
                    raise release.GateError("unsafe_chunk_manifest")
                expected_entries.add(entry)
        if set(names) != expected_entries:
            raise release.GateError("missing_or_unexpected_archive_volume")
        destination = private_root(destination)
        for record in records:
            target = destination / record["backup_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                for chunk in record["chunks"]:
                    if zipped.getinfo(chunk["entry"]).file_size > CHUNK * 2:
                        raise release.GateError("encrypted_chunk_budget")
                    token = zipped.read(chunk["entry"])
                    if hashlib.sha256(token).hexdigest() != chunk["sha256"]:
                        raise release.GateError("encrypted_chunk_hash_failed")
                    content = cipher.decrypt(token)
                    if len(content) != chunk["bytes"] or len(content) > CHUNK:
                        raise release.GateError("decrypted_chunk_size_failed")
                    stream.write(content)
        write_json(destination / "manifest.json", metadata)
        verify(destination, scratch_root=destination)
        for name, expected in metadata["database_snapshots"].items():
            if database_snapshot(destination / name) != expected:
                raise release.GateError("financial_restore_reconciliation_failed")
    return {"release_id": metadata["release_id"], "candidate_sha": metadata["candidate_sha"],
            "production_baseline_sha": metadata["production_baseline_sha"],
            "LOCAL_BACKUP_VERIFIED": "PASS", "OFF_DEVICE_COPY_VERIFIED": "NOT_RUN",
            "PORTABLE_KEY_VERIFIED": "NOT_RUN", "INDEPENDENT_DEVICE_LOSS_RESTORE_VERIFIED": "NOT_RUN",
            "file_count": metadata["file_count"], "database_count": len(metadata["database_snapshots"]),
            "sqlite_integrity": "PASS", "foreign_keys": "PASS", "financial_reconciliation": "PASS",
            "archive_sha256": public["archive_sha256"], "key_kind": key_kind,
            "restore_scope": "fresh_process_same_device_only"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--restore", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(restore(args.backup, args.key_file, args.restore)))
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "code": str(exc) if isinstance(exc, release.GateError) else "recovery_failed",
                          "exception_type": type(exc).__name__}))
        raise SystemExit(1)
