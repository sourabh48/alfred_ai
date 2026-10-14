"""Release checks run only against generated synthetic Git repositories."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import datetime, timezone

from scripts import release_gate as release


class ReleaseRepositoryFixture:
    def setUp(self):
        self.temporary = TemporaryDirectory(prefix="alfred-release-synthetic-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "release@example.test")
        self.git("config", "user.name", "Synthetic Release")
        self.commit("baseline.txt", "synthetic baseline")
        self.baseline = self.git("rev-parse", "HEAD")
        self.commit("candidate.txt", "synthetic candidate")
        self.candidate = self.git("rev-parse", "HEAD")
        self.manifest = release.new_manifest("synthetic-1", self.candidate, self.baseline)

    def git(self, *args):
        return release.git(self.repo, *args)

    def commit(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        self.git("add", "--", path)
        self.git("commit", "-qm", "synthetic fixture")


class ReleaseSourceTests(ReleaseRepositoryFixture, unittest.TestCase):
    def target(self, baseline=True):
        target = self.root / "target"
        release.git(self.root, "clone", "--quiet", str(self.repo), str(target))
        if baseline:
            release.git(target, "checkout", "--detach", self.baseline)
        return target

    def test_target_operator_edits_are_hashed_and_preserved(self):
        target = self.target()
        path = target / "docs/M15_LIVE_DEPLOYMENT_20261015.md"
        path.parent.mkdir()
        path.write_text("synthetic operator note")
        release.source_checks(self.repo, self.manifest, target_repo=target)
        self.assertEqual(self.manifest["gates"]["operators"]["status"], "PASS")
        self.assertEqual(path.read_text(), "synthetic operator note")

    def test_unknown_target_edits_are_not_overwritten(self):
        target = self.target()
        (target / "baseline.txt").write_text("synthetic operator edit")
        with self.assertRaisesRegex(release.GateError, "unprotected_or_overlapping_operator_changes"):
            release.source_checks(self.repo, self.manifest, target_repo=target)
        self.assertEqual((target / "baseline.txt").read_text(), "synthetic operator edit")

    def test_changed_target_head_blocks(self):
        with self.assertRaisesRegex(release.GateError, "target_baseline_changed"):
            release.source_checks(self.repo, self.manifest, target_repo=self.target(baseline=False))

    def test_remote_divergence_blocks_without_push(self):
        remote = self.target()
        self.git("remote", "add", "origin", str(remote))
        release.git(remote, "switch", "-c", "remote-diverged")
        (remote / "diverged.txt").write_text("synthetic divergence")
        release.git(remote, "add", "diverged.txt")
        release.git(remote, "-c", "user.name=Synthetic", "-c", "user.email=release@example.test", "commit", "-qm", "synthetic divergence")
        release.remote_check(self.repo, self.manifest, branch="remote-diverged")
        self.assertEqual(self.manifest["gates"]["remote_git"]["status"], "FAIL")
        self.assertFalse(self.manifest["gates"]["remote_git"]["evidence"]["push_performed"])


    def test_exact_clean_candidate_and_changed_file_inventory(self):
        release.source_checks(self.repo, self.manifest)
        source = self.manifest["gates"]["source"]
        self.assertEqual(source["status"], "PASS")
        self.assertEqual(source["evidence"]["changed_paths"], ["candidate.txt"])
        self.assertEqual(source["evidence"]["new_commits"], 1)

    def test_short_sha_or_missing_commit_is_rejected(self):
        for candidate in (self.candidate[:7], "f" * 40, "HEAD", "--all"):
            with self.subTest(candidate=candidate), self.assertRaises(release.GateError):
                release.exact_commit(self.repo, candidate)

    def test_newer_checkout_does_not_substitute_authorized_candidate(self):
        self.commit("newer.txt", "synthetic newer commit")
        with self.assertRaisesRegex(release.GateError, "candidate_is_not_checkout_head"):
            release.source_checks(self.repo, self.manifest)

    def test_dirty_tracked_and_untracked_files_are_rejected(self):
        for path in ("baseline.txt", "untracked.txt"):
            with self.subTest(path=path):
                target = self.repo / path
                target.write_text("synthetic edit")
                with self.assertRaisesRegex(release.GateError, "candidate_worktree_dirty"):
                    release.source_checks(self.repo, self.manifest)
                if path == "untracked.txt":
                    target.unlink()
                else:
                    target.write_text("synthetic baseline")

    def test_diverged_baseline_is_rejected(self):
        self.git("checkout", "-qb", "other", self.baseline)
        self.commit("other.txt", "synthetic divergence")
        self.manifest["production_baseline_sha"] = self.git("rev-parse", "HEAD")
        self.git("checkout", "--detach", self.candidate)
        with self.assertRaisesRegex(release.GateError, "baseline_diverged"):
            release.source_checks(self.repo, self.manifest)

    def test_unexpected_dependency_and_migration_changes_fail(self):
        self.commit("requirements.txt", "synthetic-package==1")
        self.commit("apps/demo/migrations/0001_initial.py", "# synthetic")
        self.manifest["candidate_sha"] = self.git("rev-parse", "HEAD")
        release.source_checks(self.repo, self.manifest)
        self.assertEqual(self.manifest["gates"]["dependencies"]["status"], "FAIL")
        self.assertEqual(self.manifest["gates"]["migrations"]["status"], "FAIL")
        release.source_checks(self.repo, self.manifest, ["requirements.txt"], ["apps/demo/migrations/0001_initial.py"])
        self.assertEqual(self.manifest["gates"]["dependencies"]["status"], "PASS")
        self.assertEqual(self.manifest["gates"]["migrations"]["status"], "PASS")

    def test_report_missing_gates_block_without_fake_pass(self):
        release.source_checks(self.repo, self.manifest)
        result = release.report(self.manifest, self.root / "report")
        self.assertEqual(result["technical"]["status"], "BLOCKED")
        self.assertFalse(result["promotion"]["ready"])
        self.assertIn("local_backup", result["promotion"]["blocked"])
        self.assertEqual(release.load(self.root / "report/release.json")["candidate_sha"], self.candidate)

    def test_existing_release_output_cannot_silently_change_candidate(self):
        output = self.root / "report"
        release.report(self.manifest, output)
        before = (output / "release.json").read_bytes()
        other = release.new_manifest("synthetic-1", self.baseline, self.baseline)
        with self.assertRaisesRegex(release.GateError, "release_identity_is_immutable"):
            release.report(other, output)
        self.assertEqual(before, (output / "release.json").read_bytes())

    def test_report_failure_is_not_hidden_by_other_passes(self):
        for name in release.TECHNICAL + release.OPERATIONAL:
            release.gate(self.manifest, name, "PASS", "synthetic")
        release.gate(self.manifest, "financial", "FAIL", "financial_difference")
        result = release.report(self.manifest, self.root / "report")
        self.assertEqual(result["technical"]["status"], "FAIL")
        self.assertFalse(result["promotion"]["ready"])

    def test_old_release_waiver_cannot_be_inherited(self):
        waiver = {"release_id": "M15", "candidate_sha": self.candidate, "gate": "device_loss_restore",
                  "scope": "this_release_only", "reason": "synthetic", "authorized_by": "synthetic operator",
                  "authorization_evidence": "synthetic explicit YES"}
        self.manifest["waivers"] = [waiver]
        release.gate(self.manifest, "device_loss_restore", "WAIVED_BY_USER", "user_waiver")
        self.assertEqual(release.decision(self.manifest, ["device_loss_restore"])["status"], "BLOCKED")
        waiver["release_id"] = self.manifest["release_id"]
        self.assertEqual(release.decision(self.manifest, ["device_loss_restore"])["waived"], ["device_loss_restore"])
        waiver["candidate_sha"] = "a" * 40
        self.assertEqual(release.decision(self.manifest, ["device_loss_restore"])["status"], "BLOCKED")

    def test_technical_failures_cannot_be_waived(self):
        self.manifest["waivers"] = [{"release_id": "synthetic-1", "candidate_sha": self.candidate,
            "gate": "financial", "scope": "this_release_only", "reason": "synthetic",
            "authorized_by": "synthetic", "authorization_evidence": "synthetic"}]
        release.gate(self.manifest, "financial", "WAIVED_BY_USER", "invalid_waiver")
        self.assertEqual(release.decision(self.manifest, ["financial"])["status"], "BLOCKED")

    def test_green_gates_are_separate_from_deployment_authorization(self):
        for name in release.TECHNICAL + release.OPERATIONAL:
            release.gate(self.manifest, name, "PASS", "synthetic")
        release.report(self.manifest, self.root / "report")
        self.assertEqual(self.manifest["promotion"]["status"], "PASS")
        self.assertFalse(self.manifest["promotion"]["ready"])

    def test_cli_preflight_scope_pass_does_not_claim_release_readiness(self):
        code = release.main(["preflight", "--repo", str(self.repo), "--release-id", "synthetic-1",
                             "--candidate", self.candidate, "--baseline", self.baseline,
                             "--output", str(self.root / "cli")])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads((self.root / "cli/release.json").read_text())["promotion"]["ready"])

    def evidence(self, name="device_loss_restore", status="WAIVED_BY_USER"):
        payload = {"release_id": "synthetic-1", "candidate_sha": self.candidate, "gate": name, "status": status,
                   "authorized_by": "synthetic operator", "authorization_evidence": "synthetic current explicit YES",
                   "reason": "synthetic test only", "observed_utc": datetime.now(timezone.utc).isoformat(),
                   "decision": "YES", "scope": "this_release_only"}
        path = self.root / "evidence.json"
        path.write_text(json.dumps(payload))
        return path, payload

    def test_explicit_waiver_keeps_distinct_status_and_release_scope(self):
        path, payload = self.evidence()
        release.record_evidence(self.manifest, path)
        self.assertEqual(self.manifest["gates"]["device_loss_restore"]["status"], "WAIVED_BY_USER")
        self.assertEqual(release.decision(self.manifest, ["device_loss_restore"])["waived"], ["device_loss_restore"])
        other = release.new_manifest("next-release", self.candidate, self.baseline)
        with self.assertRaisesRegex(release.GateError, "invalid_scoped_operational_evidence"):
            release.record_evidence(other, path)

    def test_financial_privacy_local_backup_and_remote_git_cannot_be_attested_or_waived(self):
        for name in ("financial", "privacy", "local_backup", "operators", "remote_git"):
            path, payload = self.evidence(name)
            with self.subTest(gate=name), self.assertRaisesRegex(release.GateError, "invalid_scoped_operational_evidence"):
                release.record_evidence(self.manifest, path)

    def test_waiver_requires_explicit_yes(self):
        path, payload = self.evidence()
        payload["decision"] = "PENDING"
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(release.GateError, "explicit_release_waiver_required"):
            release.record_evidence(self.manifest, path)

    def test_hashes_cannot_be_attested_as_decryption_or_device_loss_restore(self):
        path, payload = self.evidence(status="PASS")
        proof = self.root / "hashes.json"
        proof.write_text('{"synthetic_hashes_only": true}')
        payload["evidence_files"] = [proof.name]
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(release.GateError, "hashes_alone_are_not_device_loss_recovery"):
            release.record_evidence(self.manifest, path)
        for key in ("decryption_verified", "sqlite_integrity_verified", "inventory_reconciled", "original_profile_not_required"):
            payload[key] = True
        path.write_text(json.dumps(payload))
        release.record_evidence(self.manifest, path)
        evidence = self.manifest["gates"]["device_loss_restore"]["evidence"]
        self.assertEqual(evidence["scope"], "operator_attested_not_automatically_verified")
        self.assertEqual(evidence["evidence_sha256"], [release.sha256(proof)])


if __name__ == "__main__":
    unittest.main()
