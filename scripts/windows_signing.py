"""Sign and verify ALFRED's Windows release binaries with Authenticode.

The key stays in hardware: a certificate store entry backed by a token, HSM or
the CA's cloud key provider, or a remote digest-signing library. This module
never accepts a PFX, password, PIN or token, and it stores no secrets. It uses
only the standard library because Inno Setup runs it as its sign tool with -I.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
OWNED = ("ALFRED.exe", "ALFRED Launcher.exe")
UNINSTALLER = "unins000.exe"
SETUP = "ALFRED-Setup.exe"
OWNED_SCRIPTS = ("verify_windows_acceptance.ps1", "verify_smart_app_control.ps1")
CODE_SIGNING_EKU = "1.3.6.1.5.5.7.3.3"
CONFIG_KEYS = {"schema", "provider", "publisher_subject", "timestamp_url", "signtool",
               "certificate_sha1", "machine_store", "dlib", "dmdf"}
SIGNABLE_SCRIPTS = {".ps1", ".psm1", ".psd1"}
PE_SUFFIXES = {".exe", ".dll", ".pyd", ".ocx", ".cpl", ".scr", ".sys", ".drv", ".efi", ".mui"}
# No Authenticode signature can be attached to these, so they are only recorded.
UNSIGNABLE = {".cmd", ".bat"}
# This pipeline has no accepted handling for these executable formats.
UNSUPPORTED = {".msi", ".msp", ".msix", ".appx", ".cab", ".cat", ".hta", ".jar", ".vbs", ".vbe",
               ".wsf", ".wsh", ".jse", ".com", ".pif", ".reg", ".application", ".gadget"}
SMART_APP_CONTROL_STATUS = "NOT_OBSERVED: run scripts/verify_smart_app_control.ps1 on a clean PC"


class SigningError(RuntimeError):
    pass


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def normalized_subject(subject):
    return re.sub(r"\s*,\s*", ", ", str(subject or "").strip())


def load_config(path):
    if path is None:
        raise SigningError("Release signing requires --signing-config; there is no unsigned fallback.")
    path = Path(path).resolve()
    if path.is_relative_to(ROOT):
        raise SigningError("Keep the signing configuration outside the repository.")
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SigningError("Signing configuration is missing or is not valid JSON.") from None
    if type(config) is not dict or config.get("schema") != 1:
        raise SigningError("Signing configuration must be a schema 1 JSON object.")
    if unknown := sorted(set(config) - CONFIG_KEYS):
        raise SigningError(f"Signing configuration has unsupported keys: {unknown}. "
                           "It must never hold a PFX, password, PIN or token.")
    subject = config.get("publisher_subject")
    if type(subject) is not str or "CN=" not in subject:
        raise SigningError("publisher_subject must be the exact certificate subject.")
    url = urlsplit(str(config.get("timestamp_url", "")))
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password or url.query:
        raise SigningError("timestamp_url must be the CA's documented RFC 3161 service, without credentials.")
    signtool = Path(str(config.get("signtool", "")))
    if not signtool.is_absolute() or signtool.name.lower() != "signtool.exe" or not signtool.is_file():
        raise SigningError("signtool must be the absolute path of an installed signtool.exe.")
    pin = config.get("certificate_sha1")
    if pin is not None and not re.fullmatch(r"[0-9A-Fa-f]{40}", str(pin)):
        raise SigningError("certificate_sha1 must be a 40-character thumbprint.")
    if config.get("provider") == "certificate_store":
        if pin is None:
            raise SigningError("A certificate_store provider needs certificate_sha1.")
        if config.get("dlib") or config.get("dmdf"):
            raise SigningError("A certificate_store provider cannot also set dlib or dmdf.")
    elif config.get("provider") == "remote_dlib":
        for key in ("dlib", "dmdf"):
            value = Path(str(config.get(key, "")))
            if not value.is_absolute() or not value.is_file():
                raise SigningError(f"{key} must be the absolute path of an existing file.")
    else:
        raise SigningError("provider must be certificate_store or remote_dlib.")
    return config


def _hidden():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def _powershell(script, payload):
    """Run a fixed script with JSON files, never interpolating paths into its source."""
    executable = Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    with tempfile.TemporaryDirectory(prefix="alfred-signing-") as work:
        source, target = Path(work) / "in.json", Path(work) / "out.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(
            [str(executable), "-NoProfile", "-NonInteractive", "-Command", script],
            env={**os.environ, "ALFRED_SIGNING_IN": str(source), "ALFRED_SIGNING_OUT": str(target)},
            capture_output=True, text=True, errors="replace", timeout=900, **_hidden())
        if result.returncode or not target.is_file():
            raise SigningError(f"PowerShell signature inspection failed with exit code {result.returncode}.")
        return json.loads(target.read_text(encoding="utf-8-sig"))


_CERT_FIELDS = r"""
function CertDate($d) { if ($d) { $d.ToUniversalTime().ToString('o') } }
function Ekus($c) { if ($c) { @($c.EnhancedKeyUsageList | ForEach-Object { [string]$_.ObjectId }) } else { @() } }
"""
_INSPECT = _CERT_FIELDS + r"""
$ErrorActionPreference = 'Stop'
$paths = Get-Content -LiteralPath $env:ALFRED_SIGNING_IN -Raw -Encoding UTF8 | ConvertFrom-Json
$rows = @(foreach ($path in $paths) {
  $s = Get-AuthenticodeSignature -LiteralPath $path
  $c = $s.SignerCertificate; $t = $s.TimeStamperCertificate
  [pscustomobject]@{ path=[string]$path; status=[string]$s.Status; type=[string]$s.SignatureType
    subject=$(if ($c) { $c.Subject }); issuer=$(if ($c) { $c.Issuer }); thumbprint=$(if ($c) { $c.Thumbprint })
    not_after=$(CertDate $(if ($c) { $c.NotAfter })); ekus=@(Ekus $c)
    timestamp_subject=$(if ($t) { $t.Subject }) }
})
ConvertTo-Json -Compress -Depth 4 -InputObject $rows | Set-Content -LiteralPath $env:ALFRED_SIGNING_OUT -Encoding UTF8
"""
_CERTIFICATE = _CERT_FIELDS + r"""
$ErrorActionPreference = 'Stop'
$request = Get-Content -LiteralPath $env:ALFRED_SIGNING_IN -Raw -Encoding UTF8 | ConvertFrom-Json
$location = if ($request.machine_store) { 'LocalMachine' } else { 'CurrentUser' }
$c = Get-Item -LiteralPath ("Cert:\$location\My\" + $request.thumbprint)
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
$chain.ChainPolicy.RevocationMode = 'Online'
$chainOk = $chain.Build($c)
$root = $chain.ChainElements[$chain.ChainElements.Count - 1].Certificate
[pscustomobject]@{ subject=$c.Subject; issuer=$c.Issuer; thumbprint=$c.Thumbprint
  not_before=(CertDate $c.NotBefore); not_after=(CertDate $c.NotAfter); ekus=@(Ekus $c)
  has_private_key=[bool]$c.HasPrivateKey; signature_algorithm=$c.SignatureAlgorithm.FriendlyName
  chain_ok=[bool]$chainOk; chain_status=@($chain.ChainStatus | ForEach-Object { [string]$_.Status })
  root_in_microsoft_store=(Test-Path -LiteralPath ('Cert:\LocalMachine\AuthRoot\' + $root.Thumbprint))
} | ConvertTo-Json -Compress -Depth 4 | Set-Content -LiteralPath $env:ALFRED_SIGNING_OUT -Encoding UTF8
"""


def inspect_signatures(paths):
    paths = [str(path) for path in paths]
    if not paths:
        return {}
    rows = _powershell(_INSPECT, paths)
    rows = rows if type(rows) is list else [rows]
    return {row["path"]: row for row in rows}


def inspect_certificate(config):
    try:
        return _powershell(_CERTIFICATE, {"thumbprint": config["certificate_sha1"].upper(),
                                          "machine_store": bool(config.get("machine_store"))})
    except SigningError:
        raise SigningError("The configured certificate was not found in the Windows certificate store.") from None


def certificate_problems(record, config, now=None):
    """Checks a store certificate before any file is changed."""
    now = now or datetime.now(timezone.utc)
    problems = []
    if str(record.get("thumbprint", "")).upper() != config["certificate_sha1"].upper():
        problems.append("thumbprint differs from the configured certificate")
    if normalized_subject(record.get("subject")) != normalized_subject(config["publisher_subject"]):
        problems.append("subject differs from the configured publisher")
    if normalized_subject(record.get("subject")) == normalized_subject(record.get("issuer")):
        problems.append("certificate is self-signed")
    if CODE_SIGNING_EKU not in (record.get("ekus") or ()):
        problems.append("certificate has no code-signing purpose")
    if not record.get("has_private_key"):
        problems.append("private key is not accessible")
    if "sha1" in str(record.get("signature_algorithm", "")).lower():
        problems.append("certificate uses a SHA-1 signature")
    try:
        if not (datetime.fromisoformat(record["not_before"]) <= now <= datetime.fromisoformat(record["not_after"])):
            problems.append("certificate is outside its validity period")
    except (KeyError, TypeError, ValueError):
        problems.append("certificate validity period is unreadable")
    if not record.get("chain_ok"):
        problems.append(f"certificate chain failed: {record.get('chain_status')}")
    # shortcut: AuthRoot holds Microsoft-distributed roots but an administrator can add to it; the clean-PC run is the real proof.
    if not record.get("root_in_microsoft_store"):
        problems.append("chain root is not a Microsoft-distributed root")
    return problems


def prepare_release(config_path, authorization, source_commit):
    """Everything that must be true before the release bundle is changed."""
    if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        raise SigningError("Production signing is refused in CI; it needs the owner's separate signing PC.")
    if authorization != source_commit:
        raise SigningError("Production signing needs --authorize-production-signing with the exact source commit.")
    config = load_config(config_path)
    tool = inspect_signatures([config["signtool"]])[config["signtool"]]
    if tool["status"] != "Valid" or "Microsoft" not in str(tool.get("subject")):
        raise SigningError("signtool.exe is not validly signed by Microsoft.")
    if config["provider"] == "certificate_store":
        if problems := certificate_problems(inspect_certificate(config), config):
            raise SigningError("Certificate refused: " + "; ".join(problems))
    return config


def sign_command(config, path):
    command = [config["signtool"], "sign", "/fd", "SHA256", "/tr", config["timestamp_url"], "/td", "SHA256", "/d", "ALFRED"]
    if config["provider"] == "certificate_store":
        command += ["/sha1", config["certificate_sha1"].upper(), "/s", "My"]
        if config.get("machine_store"):
            command.append("/sm")
    else:
        command += ["/dlib", config["dlib"], "/dmdf", config["dmdf"]]
    return command + [str(path)]


def _run_signtool(command):
    try:
        return subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=300, **_hidden())
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SigningError(f"signtool could not finish ({type(error).__name__}).") from None


def sign_file(config, path, attempts=3):
    for attempt in range(attempts):
        result = _run_signtool(sign_command(config, path))
        if result.returncode == 0:
            return
        if attempt + 1 < attempts:  # Timestamp services fail transiently; a retry re-signs the whole file.
            time.sleep(2 * (attempt + 1))
    # Only signtool's own error lines are shown; its other output is not needed in logs.
    reason = " ".join(line.strip() for line in (result.stdout + result.stderr).splitlines()
                      if line.startswith("SignTool Error:"))[:500]
    raise SigningError(f"Signing {Path(path).name} failed with exit code {result.returncode}. {reason}".strip())


def signature_problems(record, identity):
    problems = []
    if record.get("status") != "Valid":
        problems.append(f"signature status is {record.get('status')}")
    if record.get("type") != "Authenticode":
        problems.append("signature is not embedded Authenticode")
    if normalized_subject(record.get("subject")) != normalized_subject(identity["publisher_subject"]):
        problems.append("publisher does not match")
    pin = identity.get("certificate_sha1")
    if pin and str(record.get("thumbprint", "")).upper() != pin.upper():
        problems.append("certificate thumbprint does not match")
    if not record.get("timestamp_subject"):
        problems.append("signature has no timestamp")
    if CODE_SIGNING_EKU not in (record.get("ekus") or ()):
        problems.append("certificate has no code-signing purpose")
    return problems


def signtool_verification(signtool, path):
    """signtool verify /pa /v with its output parsed; returns (problems, timestamp)."""
    result = _run_signtool([signtool, "verify", "/pa", "/v", "/tw", str(path)])
    output = result.stdout + result.stderr
    problems = []
    if result.returncode:
        problems.append(f"signtool verify exit code {result.returncode}")
    if not re.search(r"Hash of file \(sha256\)", output, re.IGNORECASE):
        problems.append("file digest is not SHA-256")
    timestamp = re.search(r"The signature is timestamped:\s*(.+)", output)
    if not timestamp:
        problems.append("signtool found no timestamp")
    if "SignTool Warning" in output:
        problems.append("signtool reported a warning")
    return problems, timestamp.group(1).strip() if timestamp else None


def _is_pe(path):
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            return False
        stream.seek(int.from_bytes(header[60:64], "little"))
        return stream.read(4) == b"PE\0\0"


def scan_tree(root):
    """Classify every code-format file by content, not by a trusted extension."""
    rows = []
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if _is_pe(path) or suffix in SIGNABLE_SCRIPTS:
            kind = "signable"
        elif suffix in PE_SUFFIXES:
            kind = "invalid"
        elif suffix in UNSIGNABLE:
            kind = "unsignable"
        elif suffix in UNSUPPORTED:
            kind = "unsupported"
        else:
            continue
        rows.append({"path": path.relative_to(root).as_posix(), "kind": kind})
    return rows


def _is_unsigned(record):
    return record["status"] == "NotSigned" or (record["status"] == "Valid" and record["type"] != "Authenticode")


def _ours(record, identity):
    return not signature_problems(record, identity)


def plan_bundle(bundle, identity=None):
    """Read-only role for each file. Only a reviewed role may ever change a file."""
    bundle = Path(bundle)
    files = scan_tree(bundle)
    signable = [row for row in files if row["kind"] == "signable"]
    status = inspect_signatures([bundle / row["path"] for row in signable])
    plan, blockers = [], []
    for name in OWNED:
        if not (bundle / name).is_file():
            blockers.append(f"{name}: required ALFRED executable is missing")
    for row in files:
        name = row["path"]
        if row["kind"] == "unsignable":
            plan.append({"path": name, "role": "recorded_unsignable", "action": "record"})
            continue
        if row["kind"] != "signable":
            blockers.append(f"{name}: {row['kind']} executable format")
            continue
        record = status[str(bundle / name)]
        owned = name in OWNED
        unsigned, valid = _is_unsigned(record), record["status"] == "Valid" and record["type"] == "Authenticode"
        already = bool(identity) and _ours(record, identity)
        if owned and (unsigned or already):
            plan.append({"path": name, "role": "alfred_owned", "action": "keep" if already else "sign"})
        elif owned:
            blockers.append(f"{name}: unexpected signature ({record['status']}, {record.get('subject')})")
        elif already:
            plan.append({"path": name, "role": "third_party_signed_as_distributor", "action": "keep"})
        elif valid:
            plan.append({"path": name, "role": "vendor_preserved", "action": "keep", "publisher": record.get("subject")})
        elif unsigned:
            plan.append({"path": name, "role": "third_party_signed_as_distributor", "action": "needs_approval"})
        else:  # A corrupt or untrusted vendor signature is never hidden by re-signing.
            blockers.append(f"{name}: invalid vendor signature ({record['status']})")
    return plan, blockers


def _blocked(prefix, blockers):
    shown = "; ".join(blockers[:20])
    more = f"; and {len(blockers) - 20} more" if len(blockers) > 20 else ""
    return SigningError(f"{prefix}: {shown}{more}")


def sign_bundle(bundle, config, approve_unsigned_third_party=False):
    """Sign before Inno embeds the files. Nothing changes unless the whole plan is acceptable."""
    bundle = Path(bundle)
    plan, blockers = plan_bundle(bundle, config)
    if not approve_unsigned_third_party:
        blockers += [f"{row['path']}: unsigned third-party binary needs --approve-unsigned-third-party"
                     for row in plan if row["action"] == "needs_approval"]
    if blockers:
        raise _blocked("Bundle signing refused", blockers)
    for row in plan:
        if row["role"] == "recorded_unsignable":
            continue
        row["original_sha256"] = digest(bundle / row["path"])
        if row["action"] in ("sign", "needs_approval"):
            sign_file(config, bundle / row["path"])
    return plan


def verify_entries(root, entries, identity, signtool=None):
    """Return manifest rows for files whose hash and signature currently verify."""
    root = Path(root)
    present = [row for row in entries if (root / row["path"]).is_file()]
    failures = [f"{row['path']}: missing" for row in entries if row not in present]
    status = inspect_signatures([root / row["path"] for row in present if row["role"] != "recorded_unsignable"])
    rows = []
    for row in present:
        path = root / row["path"]
        sha256 = digest(path)
        result = dict(path=row["path"], role=row["role"], sha256=sha256, bytes=path.stat().st_size)
        if "original_sha256" in row:
            result["original_sha256"] = row["original_sha256"]
        if row["role"] == "recorded_unsignable":
            if row.get("sha256", sha256) != sha256:
                failures.append(f"{row['path']}: changed after signing")
            rows.append({**result, "signing_status": "cannot_carry_authenticode", "verification": "recorded"})
            continue
        problems = []
        if row.get("sha256", sha256) != sha256:
            problems.append("changed after signing")
        record = status[str(path)]
        timestamp = row.get("timestamp")
        if row["role"] == "vendor_preserved":
            if record["status"] != "Valid" or record["type"] != "Authenticode":
                problems.append(f"vendor signature status is {record['status']}")
            if row.get("original_sha256", sha256) != sha256:
                problems.append("vendor binary was modified")
        else:
            problems += signature_problems(record, identity)
            if signtool:
                tool_problems, timestamp = signtool_verification(signtool, path)
                problems += tool_problems
        if problems:
            failures.append(f"{row['path']}: " + ", ".join(problems))
            continue
        rows.append({**result, "signing_status": "signed", "publisher": record.get("subject"),
                     "certificate_thumbprint": record.get("thumbprint"), "timestamp": timestamp,
                     "timestamp_signer": record.get("timestamp_subject"),
                     "verification": "signtool+authenticode" if signtool and row["role"] != "vendor_preserved" else "authenticode"})
    if failures:
        raise _blocked("Signature verification failed", failures)
    return rows


def _reject_unlisted(root, entries, extras=()):
    listed = {row["path"] for row in entries} | set(extras)
    unlisted = [row["path"] for row in scan_tree(root) if row["path"] not in listed]
    if unlisted:
        raise _blocked("Unexpected executable content", unlisted)


def write_signing_manifest(bundle, output, plan, config, source, inno_log):
    """Verify the finished release and write its secret-free record. Raises instead of writing on failure."""
    bundle, output = Path(bundle), Path(output)
    _reject_unlisted(bundle, plan)
    try:
        calls = [json.loads(line) for line in inno_log.read_text(encoding="utf-8").splitlines()]
    except (OSError, ValueError):
        raise SigningError("Inno Setup's signing record is missing; its signed outputs are unproven.") from None
    # Inno signs at least the uninstaller and then the finished Setup.
    if len(calls) < 2:
        raise SigningError("Inno Setup did not request signing for both its uninstaller and Setup.")
    signtool = config["signtool"]
    bundle_rows = verify_entries(bundle, plan, config, signtool)
    output_plan = [{"path": SETUP, "role": "installer"}]
    output_plan += [{"path": name, "role": "acceptance_script"} for name in OWNED_SCRIPTS]
    output_rows = verify_entries(output, output_plan, config, signtool)
    archive = output / "ALFRED-Windows-x64.zip"
    manifest = {
        "schema": 1, "signing_mode": "release", "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source["source_commit"], "source_tree": source["source_tree"],
        "publisher_subject": config["publisher_subject"], "certificate_sha1": config.get("certificate_sha1"),
        "provider": config["provider"], "timestamp_url": config["timestamp_url"],
        "file_digest": "SHA256", "timestamp_digest": "SHA256", "signtool_sha256": digest(signtool),
        "inno_sign_calls": calls, "bundle": bundle_rows, "output": output_rows,
        "not_authenticode": [{"path": archive.name, "sha256": digest(archive), "bytes": archive.stat().st_size,
                              "reason": "ZIP cannot carry Authenticode; its PE contents are signed"}],
        "uninstaller": "Signed by Inno Setup at compile time; run verify-installed after an install.",
        "smart_app_control": SMART_APP_CONTROL_STATUS,
    }
    path = output / "signing-manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def inno_sign_tool(config_path, log_path):
    """The ISCC /S definition. $f is Inno's quoted file; $q and $$ are its documented escapes."""
    quoted = lambda value: "$q" + str(value).replace("$", "$$") + "$q"
    return (f"/Salfredsign={quoted(sys.executable)} -I {quoted(Path(__file__).resolve())} inno-sign "
            f"--config {quoted(Path(config_path).resolve())} --log {quoted(Path(log_path).resolve())} $f")


def inno_sign(config_path, log_path, path):
    """Inno's callback: sign one file and prove the result before Inno keeps it."""
    config = load_config(config_path)
    sign_file(config, path)
    record = inspect_signatures([path])[str(path)]
    problems = signature_problems(record, config)
    tool_problems, _ = signtool_verification(config["signtool"], path)
    if problems + tool_problems:
        raise SigningError(f"{Path(path).name}: " + ", ".join(problems + tool_problems))
    with Path(log_path).open("a", encoding="utf-8") as log:
        log.write(json.dumps({"file": Path(path).name, "sha256": digest(path),
                              "at": datetime.now(timezone.utc).isoformat()}) + "\n")


def _identity(manifest):
    return {"publisher_subject": manifest["publisher_subject"], "certificate_sha1": manifest.get("certificate_sha1")}


def _manifest(path):
    try:
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SigningError("Signing manifest is missing or invalid.") from None
    if manifest.get("signing_mode") != "release":
        raise SigningError("Only a release signing manifest can be verified.")
    return manifest


def verify_release(manifest_path, bundle=None, output=None, signtool=None):
    manifest = _manifest(manifest_path)
    identity = _identity(manifest)
    output = Path(output) if output else Path(manifest_path).resolve().parent
    verify_entries(output, manifest["output"], identity, signtool)
    for row in manifest["not_authenticode"]:
        if digest(output / row["path"]) != row["sha256"]:
            raise SigningError(f"{row['path']}: changed after signing")
    if bundle:
        _reject_unlisted(bundle, manifest["bundle"])
        verify_entries(bundle, manifest["bundle"], identity, signtool)
    return {"verified": True, "bundle_checked": bool(bundle)}


def verify_installed(manifest_path, install_dir, signtool=None):
    """After install: the same bytes and signatures, plus the generated uninstaller."""
    manifest = _manifest(manifest_path)
    identity = _identity(manifest)
    install_dir = Path(install_dir)
    # unins000.exe is generated at install time; the .cmd is the one extra the script installs.
    _reject_unlisted(install_dir, manifest["bundle"], (UNINSTALLER, "Uninstall ALFRED.cmd"))
    rows = verify_entries(install_dir, manifest["bundle"], identity, signtool)
    rows += verify_entries(install_dir, [{"path": UNINSTALLER, "role": "uninstaller"}], identity, signtool)
    return {"verified": True, "files": len(rows)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("inventory", help="read-only signing plan for a frozen bundle")
    inventory.add_argument("--bundle", type=Path, required=True)
    sign = commands.add_parser("inno-sign", help="Inno Setup sign tool callback")
    sign.add_argument("--config", type=Path, required=True)
    sign.add_argument("--log", type=Path, required=True)
    sign.add_argument("file", type=Path)
    release = commands.add_parser("verify-release", help="re-verify a release against its manifest")
    release.add_argument("--manifest", type=Path, required=True)
    release.add_argument("--bundle", type=Path)
    release.add_argument("--signtool", type=Path)
    installed = commands.add_parser("verify-installed", help="verify an installed copy and its uninstaller")
    installed.add_argument("--manifest", type=Path, required=True)
    installed.add_argument("--install-dir", type=Path, required=True)
    installed.add_argument("--signtool", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "inventory":
            plan, blockers = plan_bundle(args.bundle)
            summary = {}
            for row in plan:
                summary[row["role"]] = summary.get(row["role"], 0) + 1
            print(json.dumps({"roles": summary, "blockers": blockers,
                              "unsigned_third_party": [row["path"] for row in plan if row["action"] == "needs_approval"]}, indent=2))
        elif args.command == "inno-sign":
            inno_sign(args.config, args.log, args.file)
        elif args.command == "verify-release":
            print(json.dumps(verify_release(args.manifest, args.bundle, signtool=args.signtool)))
        else:
            print(json.dumps(verify_installed(args.manifest, args.install_dir, args.signtool)))
    except SigningError as error:
        print(f"SIGNING REFUSED: {error}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
