"""Pinned local release gates; promotion is dry-run unless explicitly authorized. Never pushes."""
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from alfred_native import write_json

STATUSES = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "WAIVED_BY_USER"}
TECHNICAL = ("source", "dependencies", "migrations", "privacy", "configuration",
             "backend", "browser", "native", "ollama", "financial", "rollback")
OPERATIONAL = ("operators", "local_backup", "off_device_copy", "portable_key",
               "device_loss_restore", "packaged", "real_account", "separate_pc",
               "installer", "remote_git", "remote_ci", "branch_protection")
WAIVABLE = set(OPERATIONAL) - {"operators", "local_backup", "remote_git"}
PROTECTED = ("artifacts/audit/CODEX_CONTINUATION_STATE.md",
             "artifacts/audit/M14_CONTROLLED_PROMOTION_PLAN.md", "skills-lock.json",
             "docs/M14_LIVE_DEPLOYMENT_20261011.md",
             "docs/POST_MIGRATION_UI_ACCEPTANCE_20261007.md",
             "docs/WINDOWS_RESTORATION_VERIFIED_20261006.md",
             "docs/M15_LIVE_DEPLOYMENT_20261015.md")


class GateError(RuntimeError):
    """Only fixed, non-sensitive error codes cross the reporting boundary."""


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(repo, *args):
    result = subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, timeout=60,
                            env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"))
    if result.returncode:
        raise GateError("git_operation_failed")
    return result.stdout.decode("utf-8", errors="strict").rstrip("\r\n")


def exact_commit(repo, value):
    if not re.fullmatch(r"[a-f0-9]{40}", value or ""):
        raise GateError("full_commit_sha_required")
    if git(repo, "rev-parse", "--verify", value + "^{commit}") != value:
        raise GateError("commit_identity_mismatch")
    return value


def ancestor(repo, older, newer):
    result = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
                            capture_output=True, timeout=60)
    if result.returncode not in (0, 1):
        raise GateError("ancestry_check_failed")
    return result.returncode == 0


def remote_check(repo, manifest, remote="origin", branch="master"):
    if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", value) for value in (remote, branch)):
        raise GateError("invalid_remote_reference")
    rows = git(repo, "ls-remote", "--heads", remote, "refs/heads/" + branch).splitlines()
    if len(rows) != 1:
        raise GateError("remote_branch_missing")
    head = rows[0].split()[0]
    if not re.fullmatch(r"[a-f0-9]{40}", head):
        raise GateError("remote_head_invalid")
    try:
        exact_commit(repo, head)
    except GateError:
        compatible = False
    else:
        compatible = ancestor(repo, head, manifest["candidate_sha"])
    gate(manifest, "remote_git", "PASS" if compatible else "FAIL",
         "remote_fast_forward_verified" if compatible else "remote_diverged", head=head, push_performed=False)


def gate(manifest, name, status, code, **evidence):
    if name not in TECHNICAL + OPERATIONAL or status not in STATUSES:
        raise GateError("invalid_gate_result")
    manifest["gates"][name] = {"status": status, "code": code, "evidence": evidence}


def new_manifest(release_id, candidate, baseline):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", release_id):
        raise GateError("invalid_release_id")
    for value in (candidate, baseline):
        if not re.fullmatch(r"[a-f0-9]{40}", value or ""):
            raise GateError("full_commit_sha_required")
    return {"schema": 1, "release_id": release_id, "candidate_sha": candidate,
            "production_baseline_sha": baseline, "created_utc": now(),
            "gates": {name: {"status": "NOT_RUN", "code": "evidence_missing", "evidence": {}}
                      for name in TECHNICAL + OPERATIONAL}, "waivers": [],
            "approval": {"status": "NOT_RUN"}, "deployment": {"stage": "PREFLIGHT"}}


def valid_waiver(manifest, name):
    for waiver in manifest.get("waivers", []):
        if (waiver.get("release_id") == manifest["release_id"]
                and waiver.get("candidate_sha") == manifest["candidate_sha"]
                and waiver.get("gate") == name and waiver.get("scope") == "this_release_only"
                and all(isinstance(waiver.get(key), str) and waiver[key].strip()
                        for key in ("reason", "authorized_by", "authorization_evidence"))):
            return True
    return False


def decision(manifest, names):
    blocked = []
    failed = []
    waived = []
    for name in names:
        status = manifest["gates"].get(name, {}).get("status", "NOT_RUN")
        if status == "FAIL":
            failed.append(name)
        elif status == "WAIVED_BY_USER" and name in WAIVABLE and valid_waiver(manifest, name):
            waived.append(name)
        elif status != "PASS":
            blocked.append(name)
    return {"status": "FAIL" if failed else "BLOCKED" if blocked else "PASS",
            "failed": failed, "blocked": blocked, "waived": waived}


def report(manifest, output):
    output = Path(output)
    if (output / "release.json").is_file():
        existing = json.loads((output / "release.json").read_text(encoding="utf-8"))
        if any(existing.get(key) != manifest.get(key) for key in
               ("release_id", "candidate_sha", "production_baseline_sha")):
            raise GateError("release_identity_is_immutable")
    output.mkdir(parents=True, exist_ok=True)
    manifest["technical"] = decision(manifest, TECHNICAL)
    manifest["promotion"] = decision(manifest, TECHNICAL + OPERATIONAL)
    if manifest.get("deployment", {}).get("status") == "FAIL":
        manifest["promotion"]["status"] = "FAIL"
        manifest["promotion"]["failed"].append("deployment")
    manifest["promotion"]["authorized"] = manifest.get("approval", {}).get("status") == "PASS"
    manifest["promotion"]["ready"] = (manifest["promotion"]["status"] == "PASS"
                                        and manifest["promotion"]["authorized"])
    write_json(output / "release.json", manifest)
    lines = ["# ALFRED release gate", "", f"Release: `{manifest['release_id']}`",
             f"Candidate: `{manifest['candidate_sha']}`",
             f"Production baseline: `{manifest['production_baseline_sha']}`", "",
             f"Technical validation: **{manifest['technical']['status']}**",
             f"Promotion gates: **{manifest['promotion']['status']}**",
             f"Deployment authorization: **{manifest['approval']['status']}**", "",
             "| Gate | Status | Safe diagnostic code |", "| --- | --- | --- |"]
    for name in TECHNICAL + OPERATIONAL:
        result = manifest["gates"][name]
        lines.append(f"| {name} | {result['status']} | {result['code']} |")
    lines += ["", "Waivers are release-specific exceptions, never PASS or recovery proof.",
              "No deployment or GitHub push is performed by validation/report commands."]
    state = manifest.get("deployment", {})
    lines += ["", f"Deployment: {state.get('stage', 'PREFLIGHT')} / {state.get('status', 'NOT_RUN')}",
              f"Rollback: {state.get('rollback', 'NOT_RUN')}",
              f"Command: {manifest.get('command_result', {}).get('status', 'NOT_RUN')}",
              f"M21 disposable rehearsal: {manifest.get('rehearsal', {}).get('status', 'NOT_RUN')}",
              "", "Recovery checks remain separate: local restore, copied archive, portable key, device-loss restore.",
              "Real-account, separate-PC and installer evidence is never inferred from synthetic tests."]
    for run in manifest.get("targeted_runs", []):
        lines.append(f"Targeted validation: {run['status']}; tests={run['tests']}; skips={run['skips']}; log={run['log']}")
    (output / "release.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return manifest


def source_checks(repo, manifest, expected_dependencies=None, expected_migrations=None, target_repo=None):
    repo = Path(repo).resolve()
    candidate = exact_commit(repo, manifest["candidate_sha"])
    baseline = exact_commit(repo, manifest["production_baseline_sha"])
    if git(repo, "rev-parse", "HEAD") != candidate:
        raise GateError("candidate_is_not_checkout_head")
    if git(repo, "status", "--porcelain", "--untracked-files=all"):
        raise GateError("candidate_worktree_dirty")
    if not ancestor(repo, baseline, candidate):
        raise GateError("baseline_diverged")
    paths = git(repo, "diff", "--name-only", baseline, candidate).splitlines()
    policy = manifest.setdefault("change_policy", {"dependencies": [], "migrations": []})
    if expected_dependencies is not None:
        policy["dependencies"] = list(expected_dependencies)
    if expected_migrations is not None:
        policy["migrations"] = list(expected_migrations)
    expected_dependencies, expected_migrations = policy["dependencies"], policy["migrations"]
    dependencies = [p for p in paths if re.search(r"(^|/)(requirements[^/]*\.txt|constraints/|"
                                                 r"pyproject\.toml|.*lock(?:\.json)?$)", p)]
    migrations = [p for p in paths if "/migrations/" in p and p.endswith(".py")]
    gate(manifest, "dependencies", "PASS" if set(dependencies) == set(expected_dependencies) else "FAIL",
         "dependency_changes_match" if set(dependencies) == set(expected_dependencies) else "unexpected_dependencies",
         paths=dependencies)
    gate(manifest, "migrations", "PASS" if set(migrations) == set(expected_migrations) else "FAIL",
         "migration_changes_match" if set(migrations) == set(expected_migrations) else "unexpected_migrations",
         paths=migrations, automatic_application=False)
    gate(manifest, "source", "PASS", "exact_clean_fast_forward", changed_paths=paths,
         branch=git(repo, "branch", "--show-current"), tags=git(repo, "tag", "--points-at", candidate).splitlines(),
         new_commits=int(git(repo, "rev-list", "--count", baseline + ".." + candidate)))
    if target_repo:
        target = Path(target_repo).resolve()
        gate(manifest, "operators", "NOT_RUN", "target_preflight_pending")
        if target == repo or git(target, "rev-parse", "HEAD") != baseline:
            raise GateError("target_baseline_changed")
        # NUL delimiters preserve spaces/renames; unknown or overlapping edits block.
        dirty = git(target, "status", "--porcelain=v1", "-z", "--untracked-files=all")
        entries = [entry[3:] for entry in dirty.split("\0") if entry]
        if any(p not in PROTECTED or p in paths for p in entries):
            gate(manifest, "operators", "FAIL", "unprotected_or_overlapping_operator_changes")
            raise GateError("unprotected_or_overlapping_operator_changes")
        tracked = set(git(target, "ls-tree", "-r", "--name-only", "-z", baseline).split("\0"))
        for path in paths:
            local = target / path
            if not local.resolve().is_relative_to(target):
                gate(manifest, "operators", "FAIL", "candidate_path_escapes_target")
                raise GateError("candidate_path_escapes_target")
            if path not in tracked and (local.exists() or local.is_symlink()):
                gate(manifest, "operators", "FAIL", "candidate_collides_with_operator_file",
                     path_reference=hashlib.sha256(path.encode()).hexdigest()[:16])
                raise GateError("candidate_collides_with_operator_file")
        hashes = {p: sha256(target / p) for p in PROTECTED if (target / p).is_file()}
        gate(manifest, "operators", "PASS", "operator_files_recorded", sha256=hashes)
    return manifest


def load(path):
    manifest = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if manifest.get("schema") != 1:
        raise GateError("unsupported_manifest_schema")
    new_manifest(manifest["release_id"], manifest["candidate_sha"], manifest["production_baseline_sha"])
    if set(manifest["gates"]) != set(TECHNICAL + OPERATIONAL):
        raise GateError("incomplete_gate_manifest")
    return manifest


def record_evidence(manifest, path):
    """Human/device observations are explicit attestations, never inferred from tests."""
    record = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    name, status = record.get("gate"), record.get("status")
    if (name not in WAIVABLE or status not in STATUSES
            or any(record.get(key) != manifest[key] for key in ("release_id", "candidate_sha"))
            or not all(isinstance(record.get(key), str) and record[key].strip()
                       for key in ("authorized_by", "authorization_evidence", "reason"))):
        raise GateError("invalid_scoped_operational_evidence")
    observed = datetime.fromisoformat(record["observed_utc"])
    if observed.tzinfo is None or observed > datetime.now(timezone.utc):
        raise GateError("invalid_evidence_timestamp")
    reference = sha256(path)
    if status == "WAIVED_BY_USER":
        if record.get("decision") != "YES" or record.get("scope") != "this_release_only":
            raise GateError("explicit_release_waiver_required")
        manifest["waivers"] = [item for item in manifest["waivers"] if item.get("gate") != name]
        manifest["waivers"].append({key: record[key] for key in (
            "release_id", "candidate_sha", "gate", "scope", "reason", "authorized_by", "authorization_evidence")})
    if status == "PASS":
        if not record.get("evidence_files"):
            raise GateError("attestation_requires_verifiable_evidence_files")
        files = [sha256(Path(path).parent / filename) for filename in record["evidence_files"]]
        if name == "device_loss_restore" and not all(record.get(key) is True for key in
                ("decryption_verified", "sqlite_integrity_verified", "inventory_reconciled", "original_profile_not_required")):
            raise GateError("hashes_alone_are_not_device_loss_recovery")
    else:
        files = []
    manifest.setdefault("evidence_history", []).append({"gate": name, "previous": manifest["gates"][name],
        "record_sha256": reference, "observed_utc": observed.isoformat()})
    gate(manifest, name, status, "explicit_operator_attestation", record_sha256=reference,
         evidence_sha256=files, observed_utc=observed.isoformat(), scope="operator_attested_not_automatically_verified")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("preflight", "validate", "backup", "recovery", "promote", "record",
                                           "approval-request", "rehearse", "complete", "status", "report"))
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--release-id")
    parser.add_argument("--candidate")
    parser.add_argument("--baseline")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-repo", type=Path)
    parser.add_argument("--expected-dependency", action="append", default=[])
    parser.add_argument("--expected-migration", action="append", default=[])
    parser.add_argument("--profile", choices=("targeted", "backend", "browser", "native", "packaged", "full"), default="targeted")
    parser.add_argument("--test-label", action="append", default=[])
    parser.add_argument("--with-ollama", action="store_true")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--backup-directory", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--restore-directory", type=Path)
    parser.add_argument("--check-remote", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Requires new exact-release deployment authorization")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--environment", choices=("rehearsal", "production"), default="rehearsal")
    parser.add_argument("--port", type=int, default=8150)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--rehearsal-directory", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--package-manifest", type=Path)
    args = parser.parse_args(argv)
    manifest = None
    try:
        if args.command == "preflight":
            manifest = new_manifest(args.release_id or "", args.candidate, args.baseline)
            source_checks(args.repo, manifest, args.expected_dependency, args.expected_migration, args.target_repo)
            from scripts.release_validation import privacy
            privacy(args.repo, manifest)
            if args.check_remote:
                remote_check(args.repo, manifest)
        else:
            manifest = load(args.output / "release.json")
        if args.command == "record":
            if not args.evidence:
                raise GateError("explicit_evidence_file_required")
            record_evidence(manifest, args.evidence)
        if args.command == "approval-request":
            from scripts.release_promotion import binding
            if not args.target_repo or not args.runtime:
                raise GateError("explicit_target_and_runtime_required")
            source_checks(args.repo, manifest, target_repo=args.target_repo)
            request = {"decision": "PENDING", "binding": binding(manifest, args.target_repo, args.runtime, args.environment),
                       "authorized_by": "", "authorization_evidence": "", "expires_utc": "",
                       "actions": ["stop_writers", "backup", "promote", "restart", "rollback_source", "restart_previous"]}
            destination = args.output / "approval-request.json"
            if destination.exists():
                raise GateError("approval_request_already_exists")
            write_json(destination, request)
        if args.command == "rehearse":
            from scripts.release_acceptance import rehearse
            if not args.rehearsal_directory:
                raise GateError("new_disposable_rehearsal_directory_required")
            rehearse(args.repo, manifest, args.output, args.rehearsal_directory, args.port)
        if args.command == "complete":
            state = manifest["deployment"]
            if (state.get("environment") != "production" or state.get("stage") != "ACCEPTANCE"
                    or not args.target_repo or not args.runtime
                    or str(args.target_repo.resolve()) != state.get("target_repo")
                    or str(args.runtime.resolve()) != state.get("runtime")
                    or git(args.target_repo, "rev-parse", "HEAD") != manifest["candidate_sha"]
                    or decision(manifest, TECHNICAL + OPERATIONAL)["status"] != "PASS"):
                raise GateError("deployment_acceptance_incomplete")
            state.update(stage="COMPLETE", status="PASS", code="all_release_and_human_acceptance_recorded")
        if args.command == "validate":
            from scripts.release_validation import validate
            validate(args.repo, manifest, args.output, args.profile, args.test_label, args.with_ollama,
                     args.bundle, args.package_manifest)
        if args.command in ("backup", "recovery"):
            from scripts import release_recovery
            source_checks(args.repo, manifest)
            if not args.backup_directory or not args.key_file:
                raise GateError("backup_and_existing_key_paths_required")
            if args.command == "backup":
                if not args.runtime:
                    raise GateError("explicit_runtime_required")
                receipt = release_recovery.create(args.runtime, args.backup_directory, args.key_file,
                    manifest["release_id"], manifest["candidate_sha"], manifest["production_baseline_sha"], args.target_repo)
            else:
                if not args.restore_directory:
                    raise GateError("explicit_new_restore_directory_required")
                receipt = release_recovery.restore(args.backup_directory, args.key_file, args.restore_directory)
            if any(receipt.get(key) != manifest[key] for key in ("release_id", "candidate_sha", "production_baseline_sha")):
                raise GateError("recovery_receipt_release_mismatch")
            gate(manifest, "local_backup", "PASS", "independent_local_restore_verified", **receipt)
            gate(manifest, "financial", "PASS", "authenticated_restore_typed_rows_schema_and_fk_match",
                 archive_sha256=receipt["archive_sha256"])
            manifest["backup"] = {"directory": str(args.backup_directory.resolve()), "archive_sha256": receipt["archive_sha256"],
                                  "runtime_reference": receipt["runtime_reference"]}
        if args.command == "promote":
            from scripts.release_promotion import promote
            if not args.target_repo or not args.runtime:
                raise GateError("explicit_target_and_runtime_required")
            promote(args.repo, manifest, args.output, args.target_repo, args.runtime, args.key_file,
                    args.authorization, args.execute, args.environment, args.port)
        scope = ("source", "dependencies", "migrations", "privacy")
        if args.command == "preflight" and args.target_repo:
            scope += ("operators",)
        if args.command == "preflight" and args.check_remote:
            scope += ("remote_git",)
        if args.command == "validate":
            scope += ("configuration",)
            if args.profile in ("backend", "browser", "native", "packaged"):
                scope += (args.profile,)
            elif args.profile == "full":
                scope = TECHNICAL
        if args.command in ("backup", "recovery"):
            scope += ("local_backup", "financial")
        if args.command == "rehearse":
            scope = TECHNICAL
        if args.command in ("record", "approval-request"):
            scope = ()  # Recording a scoped observation does not certify the release.
        command_decision = decision(manifest, scope if args.command in
            ("preflight", "validate", "backup", "recovery", "record", "approval-request", "rehearse") else TECHNICAL + OPERATIONAL)
        if args.command == "validate" and args.profile == "targeted" and manifest.get("last_validation", {}).get("status") == "FAIL":
            command_decision["status"] = "FAIL"
        if args.command == "promote":
            from scripts.release_promotion import REHEARSAL_REQUIRED, BEFORE_PRODUCTION
            command_decision = decision(manifest, REHEARSAL_REQUIRED if args.environment == "rehearsal" else BEFORE_PRODUCTION)
            if args.execute and manifest["deployment"].get("stage") != "COMPLETE":
                command_decision["status"] = "BLOCKED"
            command_decision["dry_run"] = not args.execute
        manifest["command_result"] = {"command": args.command, **command_decision}
        report(manifest, args.output)
        print(json.dumps({key: manifest[key] for key in ("release_id", "candidate_sha", "command_result", "technical", "promotion")}))
        return 1 if command_decision["status"] == "FAIL" else 2 if command_decision["status"] == "BLOCKED" else 0
    except Exception as exc:
        code = str(exc) if isinstance(exc, GateError) else "release_check_failed"
        if manifest is not None:
            manifest["command_result"] = {"command": args.command, "status": "FAIL", "code": code,
                                          "exception_type": type(exc).__name__}
            if args.command in ("preflight", "validate"):
                gate(manifest, "source", "FAIL", code, exception_type=type(exc).__name__)
            elif args.command in ("backup", "recovery"):
                gate(manifest, "local_backup", "FAIL", code, exception_type=type(exc).__name__)
            elif args.command == "promote":
                manifest["deployment"].update(status="FAIL", code=code)
            try:
                report(manifest, args.output)
            except GateError:
                pass  # Never replace a differently pinned release's existing evidence.
        print(json.dumps({"status": "FAIL", "code": code, "exception_type": type(exc).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
