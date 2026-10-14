"""Diagnostic inventory helpers use only generated public-source fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from scripts import audit_project as audit


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


if __name__ == "__main__":
    unittest.main()
