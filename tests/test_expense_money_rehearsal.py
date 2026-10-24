"""End-to-end disposable rehearsal and refusal to overwrite existing evidence."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from scripts.rehearse_money_migrations import file_hash, main


class MoneyRehearsalTests(TransactionTestCase):
    def test_combined_rehearsal_retains_source_and_restores_exact_originals(self):
        with TemporaryDirectory(prefix="alfred-money-rehearsal-") as directory:
            root = Path(directory)
            private = root / "private"
            private.mkdir()
            source = private / "db.sqlite3"
            alias = "combined_money_rehearsal"
            disposable = connection.copy(alias=alias)
            disposable.settings_dict["NAME"] = str(source)
            connections[alias] = disposable
            try:
                executor = MigrationExecutor(disposable)
                targets = [
                    ("expenses", "0004_statementupload_extracted_payload_and_more") if node[0] == "expenses"
                    else ("investments", "0003_rename_investmenti_user_id_a9ad33_idx_investments_user_id_cbfa4c_idx_and_more") if node[0] == "investments"
                    else ("mobility", "0012_travel_bus_mode") if node[0] == "mobility"
                    else node for node in executor.loader.graph.leaf_nodes()
                ]
                executor.migrate(targets)
                apps = executor.loader.project_state(targets).apps
                user = apps.get_model("users", "User").objects.using(alias).create(username="combined-owner")
                account = apps.get_model("expenses", "BankAccount").objects.using(alias).create(user_id=user.pk, account_number="SYNTHETIC", current_balance=-1.005)
                apps.get_model("expenses", "Expense").objects.using(alias).create(user_id=user.pk, bank_account_id=account.pk, amount=2.675, closing_balance=10.005, source="bank_statement", external_reference="SYNTHETIC-REF", transaction_fingerprint="retained-historical-hash", category="transfer")
                apps.get_model("investments", "Investment").objects.using(alias).create(user_id=user.pk, asset_name="Synthetic", invested_amount=2.675, monthly_sip=.005, current_value=3.335)
            finally:
                disposable.close()
                del connections[alias]
            before = file_hash(source)
            output = root / "rehearsal"
            run = subprocess.run([sys.executable, "scripts/rehearse_money_migrations.py", "--source", str(source), "--output-dir", str(output)], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=120)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            result = json.loads((output / "private-rehearsal-result.json").read_text())
            self.assertTrue(result["private_db_unchanged"])
            self.assertTrue(result["repeat_apply_unchanged"])
            self.assertTrue(result["unedited_rollback_exact"])
            self.assertEqual(result["reconciliation"]["identity"]["reference_signature_mismatches"], 0)
            self.assertEqual(file_hash(source), before)
            from alfred_private_storage import verify_private
            self.assertTrue(verify_private(output))
            self.assertTrue(verify_private(output / "rehearsal-runtime"))
            self.assertTrue(verify_private(output / "fresh-pre-migration-backup.sqlite3"))
            # A retained evidence directory must never be reused or overwritten.
            with patch("sys.argv", ["rehearse", "--source", str(source), "--output-dir", str(output)]), self.assertRaises(FileExistsError):
                main()
            with patch("sys.argv", ["rehearse", "--source", str(source), "--output-dir", str(private / "unsafe")]), self.assertRaises(ValueError):
                main()
