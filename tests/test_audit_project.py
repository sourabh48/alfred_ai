"""Diagnostic inventory helpers use only generated public-source fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from scripts import audit_project as audit
from scripts.run_master_audit_checks import isolated_environment


class AuditProjectTests(unittest.TestCase):
    def test_links_resolve_relative_and_root_but_skip_external_and_anchors(self):
        root = Path("F:/synthetic-source").resolve()
        self.assertEqual(audit.link_target(root, "docs/a.md", "../README.md#intro"), root / "README.md")
        self.assertEqual(audit.link_target(root, "docs/a.md", "/scripts/test.py"), root / "scripts/test.py")
        for link in ("#heading", "https://example.com/docs", "F:/private/reference.md", "app://connector"):
            self.assertIsNone(audit.link_target(root, "docs/a.md", link))

    def test_monetary_candidates_exclude_measurements_and_records_have_lines(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "models.py").write_text("class Profile:\n income=models.FloatField()\n interest_rate=models.FloatField()\n amount=models.DecimalField()\n")
            fields = audit.source_inventory(root, ["models.py"])[0]["model_fields"]
            self.assertEqual([row["field"] for row in fields if row["monetary_candidate"]], ["income", "amount"])
            self.assertTrue(all(row["line"] for row in fields))

    def test_historical_records_and_vendor_docs_are_not_current_guides(self):
        self.assertEqual(audit.classification("docs/MASTER_M13D_VERIFICATION_20261006.md"), "HISTORICAL")
        self.assertEqual(audit.classification("docs/MANUAL_ACCEPTANCE.md"), "CURRENT")
        self.assertEqual(audit.classification(".codex/skills/graphify/SKILL.md"), "VENDOR")
        self.assertEqual(audit.classification(".agents/skills/playwright/SKILL.md"), "VENDOR")
        self.assertEqual(audit.classification("docs/ALFRED_COMPLETION_ROADMAP.md"), "CURRENT")

    def test_diagnostic_environment_cannot_inherit_provider_or_database_settings(self):
        from unittest.mock import patch
        with TemporaryDirectory() as directory, patch.dict("os.environ", {
            "DATABASE_URL": "postgres://synthetic.invalid/example", "OPENAI_API_KEY": "synthetic",
            "ALFRED_MEMORY_CLOUD_AUTHORIZED": "true"}):
            env = isolated_environment(directory)
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertEqual(env["ALFRED_MEMORY_CLOUD_AUTHORIZED"], "false")
            self.assertEqual(env["ALFRED_MEMORY_OPENAI_AUTHORIZED"], "false")
            self.assertTrue(env["DATABASE_URL"].startswith("sqlite:///"))
            self.assertEqual(Path(env["ALFRED_DATA_DIR"]), Path(directory).resolve())

    def test_authoritative_tracker_covers_historical_features_with_current_sources(self):
        import json
        import re
        root = Path(__file__).resolve().parents[1]
        matrix_path = root / "artifacts/audit/alfred-master-feature-matrix.json"
        rows = json.loads(matrix_path.read_text(encoding="utf-8"))
        tracker_path = "docs/PROJECT_STATUS.md"
        tracker = (root / tracker_path).read_text(encoding="utf-8")
        inventory = tracker.split("## All 143 capabilities", 1)[1]
        sections = re.findall(r"^### ([A-Z]+-\d+) [^\n]+\n(.*?)(?=^### |^## |\Z)", inventory, re.M | re.S)
        self.assertEqual(len(rows), 143)
        self.assertCountEqual([feature for feature, _ in sections], [row["id"] for row in rows])
        for feature, section in sections:
            self.assertRegex(section, r"\*\*(?:COMPLETE_VERIFIED|IMPLEMENTED_NOT_ACCEPTED|PARTIALLY_IMPLEMENTED|NOT_IMPLEMENTED|BLOCKED_EXTERNAL|BLOCKED_APPROVAL|REQUIRES_RESEARCH|UNKNOWN)\*\*", feature)
        for match in audit.LINK.finditer(tracker):
            target = audit.link_target(root, tracker_path, match[1].strip("<>"))
            if target is not None:
                self.assertTrue(target.is_file(), match[1])


if __name__ == "__main__":
    unittest.main()
