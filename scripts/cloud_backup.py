"""SYNC-11: copy an encrypted ALFRED backup archive to the owner's Cloudflare R2 bucket and back.

Only `recovery.zip` from scripts/release_recovery.py is uploaded: every file chunk and the
manifest inside it are already Fernet-encrypted, and entry names carry no file names. The
key never leaves the PC. Uploads need a portable key the owner confirms has an independent
recovery copy (a Windows-profile-bound key would die with the PC, making the copy useless).
Every upload is read back from R2 and hash-checked before it counts as an off-device copy.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import release_recovery as recovery

GateError = recovery.release.GateError
PREFIX = "alfred-backup-v1/"
PART = 8 * 1024 * 1024  # R2 multipart parts must be equal-sized (min 5 MiB) except the last
MAX_ARCHIVE = 9 * 1024 ** 3  # stays inside R2's 10 GB free storage
MAX_PARTS = 10000


def seconds():
    return time.monotonic() + 20  # public_http caps every request at 20 s


def bucket():
    from django.conf import settings
    from apps.ml_engine.services.memory_r2 import R2Bucket, configured_profile
    if not settings.ALFRED_CLOUD_BACKUP_AUTHORIZED:
        raise GateError("cloud_backup_not_authorized")
    profile = configured_profile()
    if not profile:
        raise GateError("r2_profile_missing_or_invalid")
    return R2Bucket(profile)


def tag(root, name):
    return root.tag.split("}")[0] + "}" + name if root.tag.startswith("{") else name


def xml(response):
    if b"<!" in response.content:
        raise GateError("unsafe_cloud_xml")
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError:
        raise GateError("invalid_cloud_xml") from None
    if root.tag.endswith("Error"):
        raise GateError("cloud_request_failed")
    return root


def listing(client):
    """Archives in the bucket as {sha256: (bytes, uploaded_utc)}."""
    # shortcut: one page of 1000 archives; add continuation tokens if anyone keeps more.
    root = xml(client._send("GET", query={"list-type": "2", "prefix": PREFIX, "max-keys": "1000"},
                            deadline=seconds(), maximum=1024 * 1024))
    result = {}
    for row in root.findall(tag(root, "Contents")):
        match = re.fullmatch(re.escape(PREFIX) + r"([a-f0-9]{64})\.zip", row.findtext(tag(root, "Key")) or "")
        size = row.findtext(tag(root, "Size")) or ""
        if match and size.isdigit():
            result[match.group(1)] = (int(size), row.findtext(tag(root, "LastModified")) or "")
    return result


def chunks(client, digest, size):
    for start in range(0, size, PART):
        end = min(start + PART, size) - 1
        content = client._send("GET", PREFIX + digest + ".zip", headers={"range": f"bytes={start}-{end}"},
                               deadline=seconds(), maximum=PART, statuses=(206,)).content
        if len(content) != end - start + 1:
            raise GateError("cloud_range_incomplete")
        yield content


def remote_sha256(client, digest, size):
    hasher = hashlib.sha256()
    for content in chunks(client, digest, size):
        hasher.update(content)
    return hasher.hexdigest()


def opens_with(archive, key_file):
    """The confirmed recovery key must be portable and must decrypt this archive's manifest."""
    import zipfile
    cipher, kind = recovery.cipher_from_file(key_file)
    if kind != "PORTABLE_FORMAT_UNVERIFIED":
        raise GateError("portable_key_required")
    with zipfile.ZipFile(archive) as zipped:
        if zipped.getinfo("manifest.fernet").file_size > 16 * 1024 * 1024:
            raise GateError("encrypted_manifest_budget")
        try:
            return json.loads(cipher.decrypt(zipped.read("manifest.fernet")))
        except Exception:
            raise GateError("key_does_not_open_backup") from None


def upload(backup, key_file, *, recovery_copy_confirmed, client=None):
    if not recovery_copy_confirmed:
        raise GateError("key_recovery_copy_unconfirmed")
    backup = recovery.no_links(backup)
    public = json.loads((backup / "backup.json").read_text(encoding="utf-8"))
    archive = backup / "recovery.zip"
    size = archive.stat().st_size
    digest = recovery.release.sha256(archive)
    if not public.get("complete") or size != public.get("archive_bytes") or digest != public.get("archive_sha256"):
        raise GateError("backup_archive_hash_failed")
    if size > MAX_ARCHIVE or size > PART * MAX_PARTS:
        raise GateError("archive_exceeds_free_storage")
    opens_with(archive, key_file)
    client = client or bucket()
    name = PREFIX + digest + ".zip"
    already = listing(client).get(digest)
    if not already:
        upload_id = xml(client._send("POST", name, query={"uploads": ""}, headers={"content-type": "application/octet-stream"},
                                     deadline=seconds(), maximum=64 * 1024)).findtext("{*}UploadId") or ""
        if not re.fullmatch(r"[A-Za-z0-9._~+/=-]{1,1024}", upload_id):
            raise GateError("invalid_cloud_upload_id")
        try:
            parts = []
            with archive.open("rb") as stream:
                while content := stream.read(PART):
                    number = len(parts) + 1
                    etag = client._send("PUT", name, query={"partNumber": str(number), "uploadId": upload_id}, data=content,
                                        deadline=seconds(), maximum=64 * 1024).headers.get("ETag", "")
                    if not re.fullmatch(r'"[A-Za-z0-9-]{1,128}"', etag):
                        raise GateError("missing_cloud_part_tag")
                    parts.append(f"<Part><PartNumber>{number}</PartNumber><ETag>{etag}</ETag></Part>")
            body = ("<CompleteMultipartUpload>" + "".join(parts) + "</CompleteMultipartUpload>").encode()
            xml(client._send("POST", name, query={"uploadId": upload_id}, data=body, headers={"content-type": "application/xml"},
                             deadline=seconds(), maximum=64 * 1024))
        except BaseException:
            try:  # leave no half-uploaded parts billed in the bucket; the local backup is untouched
                client._send("DELETE", name, query={"uploadId": upload_id}, deadline=seconds(), maximum=64 * 1024, statuses=(204,))
            except Exception:
                pass
            raise
    if listing(client).get(digest, (None,))[0] != size or remote_sha256(client, digest, size) != digest:
        raise GateError("off_device_copy_verification_failed")
    return {"OFF_DEVICE_COPY_VERIFIED": "PASS", "archive_sha256": digest, "archive_bytes": size,
            "already_present": bool(already), "key_kind": "PORTABLE_FORMAT_UNVERIFIED", "provider": "cloudflare_r2"}


def download(digest, key_file, destination, *, client=None):
    """Fetch one archive into a new private folder that scripts/release_recovery.py can restore."""
    if not re.fullmatch(r"[a-f0-9]{64}", digest or ""):
        raise GateError("invalid_archive_reference")
    client = client or bucket()
    size = listing(client).get(digest, (None,))[0]
    if size is None:
        raise GateError("cloud_archive_missing")
    if size > MAX_ARCHIVE:
        raise GateError("cloud_archive_too_large")
    destination = recovery.private_root(destination)
    archive = destination / "recovery.zip"
    hasher = hashlib.sha256()
    with archive.open("xb") as stream:
        for content in chunks(client, digest, size):
            hasher.update(content)
            stream.write(content)
    if hasher.hexdigest() != digest:
        raise GateError("cloud_archive_hash_failed")
    metadata = opens_with(archive, key_file)
    public = {key: metadata[key] for key in ("schema", "release_id", "candidate_sha", "production_baseline_sha",
                                             "file_count", "total_bytes", "key_kind", "runtime_reference")}
    public.update(archive="recovery.zip", archive_bytes=size, archive_sha256=digest, complete=True)
    recovery.write_json(destination / "backup.json", public)
    return {"CLOUD_DOWNLOAD_VERIFIED": "PASS", "backup_directory": str(destination), "archive_sha256": digest}


def create(runtime, destination, key_file):
    """A fresh encrypted local backup of a stopped runtime, independently restored before upload."""
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30).stdout.strip()
    release_id = "cloud-backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return recovery.create(runtime, destination, key_file, release_id, head, head)


def new_key(path):
    """A portable backup key. Keep a copy somewhere other than this PC before the first upload."""
    from cryptography.fernet import Fernet
    path = recovery.no_links(path)
    if path.is_relative_to(ROOT):
        raise GateError("key_must_stay_outside_repository")
    with path.open("xb") as stream:
        stream.write(Fernet.generate_key())
    return {"key_file": str(path), "key_kind": "PORTABLE_FORMAT_UNVERIFIED"}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, help="the ALFRED data folder whose config/local.env holds the R2 settings")
    commands = parser.add_subparsers(dest="command", required=True)
    key = commands.add_parser("new-key", help="write a new portable backup key to a new file")
    key.add_argument("--key-file", type=Path, required=True)
    send = commands.add_parser("upload", help="upload an encrypted backup; with --runtime, make it first")
    send.add_argument("--backup-dir", type=Path, required=True)
    send.add_argument("--key-file", type=Path, required=True)
    send.add_argument("--create", action="store_true", help="first back up the stopped --data-dir into a new --backup-dir")
    send.add_argument("--recovery-copy-confirmed", action="store_true",
                      help="you keep a copy of the key file somewhere other than this PC")
    commands.add_parser("list", help="list archives in the bucket")
    fetch = commands.add_parser("download", help="download an archive into a new folder")
    fetch.add_argument("--archive", required=True)
    fetch.add_argument("--key-file", type=Path, required=True)
    fetch.add_argument("--to", type=Path, required=True)
    args = parser.parse_args()
    for name in ("data_dir", "key_file", "backup_dir", "to"):  # configure() changes the working directory
        if getattr(args, name, None):
            setattr(args, name, args.__dict__[name].absolute())
    try:
        if args.command != "new-key":
            if not args.data_dir:
                raise GateError("data_dir_required")
            from alfred_native import configure
            configure(recovery.no_links(args.data_dir))  # the app's own settings, including its config/local.env
        if args.command == "new-key":
            result = new_key(args.key_file)
        elif args.command == "upload":
            if args.create:
                if not args.recovery_copy_confirmed:
                    raise GateError("key_recovery_copy_unconfirmed")
                create(args.data_dir, args.backup_dir, args.key_file)
            result = upload(args.backup_dir, args.key_file, recovery_copy_confirmed=args.recovery_copy_confirmed)
        elif args.command == "list":
            result = {digest: {"bytes": size, "uploaded": when} for digest, (size, when) in sorted(listing(bucket()).items())}
        else:
            result = download(args.archive, args.key_file, args.to)
    except Exception as exc:
        from apps.ml_engine.services.memory_sync import SyncUnavailable
        known = isinstance(exc, (GateError, SyncUnavailable))
        print(json.dumps({"status": "FAIL", "code": str(exc) if known else "cloud_backup_failed", "exception_type": type(exc).__name__}))
        raise SystemExit(1)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
