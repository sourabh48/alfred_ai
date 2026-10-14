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

    def test_authoritative_matrix_and_prompt_cover_every_remaining_feature(self):
        import json
        root = Path(__file__).resolve().parents[1]
        matrix_path = root / "artifacts/audit/alfred-master-feature-matrix.json"
        rows = json.loads(matrix_path.read_text(encoding="utf-8"))
        self.assertEqual(audit.validate_matrix(root, matrix_path), [])
        matrix = (root / "docs/ALFRED_MASTER_FEATURE_MATRIX.md").read_text(encoding="utf-8")
        prompt = (root / "artifacts/audit/ALFRED_MASTER_COMPLETION_CODEX_PROMPT.md").read_text(encoding="utf-8")
        for row in rows:
            self.assertIn(row["id"], matrix)
            if row["status"] != "COMPLETE_VERIFIED":
                self.assertIn(row["id"], prompt)


if __name__ == "__main__":
    unittest.main()
