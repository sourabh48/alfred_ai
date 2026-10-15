"""M21 sandbox selection and proof boundaries, without starting any service."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from scripts import release_acceptance as acceptance
from scripts import release_gate as release
from tests.test_release_gate import ReleaseRepositoryFixture


class ReleaseAcceptanceTests(ReleaseRepositoryFixture, unittest.TestCase):
    def test_cli_preserves_imported_fixed_gate_error_code(self):
        output=self.root/'cli-report'
        release.report(self.manifest,output)
        script=Path(__file__).resolve().parents[1]/'scripts/release_gate.py'
        result=subprocess.run([sys.executable,'-B',str(script),'rehearse','--repo',str(self.repo),
            '--output',str(output),'--rehearsal-directory',str(self.root/'new-sandbox')],
            capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,1)
        report=json.loads(result.stdout.splitlines()[-1])
        self.assertEqual(report['code'],'complete_technical_validation_before_rehearsal')
        self.assertFalse((self.root/'new-sandbox').exists())

    def test_rehearsal_without_complete_technical_gate_never_creates_target(self):
        target = self.root / "rehearsal"
        with self.assertRaisesRegex(release.GateError, "complete_technical_validation_before_rehearsal"):
            acceptance.rehearse(self.repo, self.manifest, self.root / "report", target)
        self.assertFalse(target.exists())

    def test_native_fixture_requires_current_matching_report_and_runtime(self):
        with self.assertRaisesRegex(release.GateError, "completed_synthetic_native_fixture_required"):
            acceptance.native_fixture(self.repo, self.manifest)
        self.manifest["native_run"] = "a" * 10
        proof = self.repo / "artifacts/ops/native_huey_verification.json"
        proof.parent.mkdir(parents=True)
        proof.write_text(json.dumps({"run": "a" * 10, "passed": True, "data_dir": str(self.root / "another-runtime")}))
        release.gate(self.manifest, "native", "PASS", "synthetic", report_sha256=release.sha256(proof))
        with self.assertRaisesRegex(release.GateError, "native_fixture_runtime_mismatch"):
            acceptance.native_fixture(self.repo, self.manifest)
        proof.write_text("{}")
        with self.assertRaisesRegex(release.GateError, "native_fixture_proof_changed"):
            acceptance.native_fixture(self.repo, self.manifest)


if __name__ == "__main__":
    unittest.main()
