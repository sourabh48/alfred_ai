"""Rehearse M13C/D only on fresh copies; never open the source DB with SQLite.

The output contains private evidence and must stay outside version control.
Source DB/WAL/SHM hashes must be stable across capture and the whole rehearsal.
The separately retained backup requires independent verification before live use.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP
import hashlib
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [("investments", "0004_investment_money_decimal"), ("expenses", "0005_expense_bank_money_decimal")]
REGISTERS = {
    "investments_investment": ("Investment", "investment", ("invested_amount", "monthly_sip", "current_value")),
    "expenses_expense": ("Expense", "expense", ("amount", "closing_balance")),
    "expenses_bankaccount": ("BankAccount", "bank_account", ("current_balance",)),
}


def file_hash(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def source_hashes(source):
    return {path.name: file_hash(path) for suffix in ("", "-wal", "-shm") if (path := Path(str(source) + suffix)).exists()}


def read_database(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        assert db.execute("PRAGMA integrity_check").fetchall()[0][0] == "ok", "SQLite integrity failed"
        foreign_keys = sorted(tuple(row) for row in db.execute("PRAGMA foreign_key_check"))
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        rows = {table: [dict(row) for row in db.execute('SELECT * FROM "' + table.replace('"', '""') + '"')] for table in tables}
        return rows, foreign_keys


def table_digest(rows):
    # Column and row order are immaterial. Values and SQLite types are retained.
    return hashlib.sha256(json.dumps(sorted(json.dumps(row, sort_keys=True) for row in rows), ensure_ascii=False).encode()).hexdigest()


def database_digests(rows):
    return {table: {"count": len(items), "sha256": table_digest(items)} for table, items in rows.items()}


def copy_database(source, target):
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original, closing(sqlite3.connect(target)) as copy:
        original.backup(copy)


def cents(value):
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def identity_contract(rows, *, converted):
    from apps.expenses.money import identity_amount
    from apps.expenses.services.transaction_intelligence import build_reference_signature
    contracts = {}
    for row in rows:
        if row["source"] != "bank_statement":
            continue
        amount = identity_amount(json.loads(row["transaction_identity"]), "amount", row["amount"]) if converted else row["amount"]
        signature = build_reference_signature(transaction_date=row["transaction_date"], amount=amount, direction=row["direction"], external_reference=row["external_reference"], raw_description=row["raw_description"])
        contracts[row["id"]] = (row["user_id"], row["bank_account_id"], row["transaction_fingerprint"], signature)
    return contracts


def reconcile(before, after):
    results = {}
    for table, (model, link, fields) in REGISTERS.items():
        old = {row["id"]: row for row in before[table]}
        new = {row["id"]: row for row in after[table]}
        assert old.keys() == new.keys(), f"{model}: register IDs changed"
        snapshots = {row["original_" + link + "_id"]: row for row in after[table.rsplit("_", 1)[0] + "_" + model.lower() + "moneysnapshot"]}
        assert snapshots.keys() == old.keys(), f"{model}: snapshot coverage changed"
        for pk, original in old.items():
            updated, retained = new[pk], snapshots[pk]
            assert retained[link + "_id"] == pk and retained["user_id"] == original["user_id"] and retained["applied_at"], f"{model}: ownership/application marker mismatch"
            source, normalized = json.loads(retained["source_values"]), json.loads(retained["normalized_values"])
            for field in fields:
                expected = cents(original[field])
                assert cents(updated[field]) == expected, f"{model}: {field} currency mismatch"
                assert source[field] == (None if original[field] is None else repr(float(original[field]))), f"{model}: original lost"
                assert normalized[field] == (None if expected is None else format(expected, ".2f")), f"{model}: rounding evidence mismatch"
            for field, value in original.items():
                if field not in fields:
                    assert updated[field] == value, f"{model}: unrelated {field} changed"
        results[model] = {
            "rows": len(old), "snapshots": len(snapshots), "currency_mismatches": 0,
            "unrelated_field_mismatches": 0,
            "totals": {field: {
                "expected_cents": str(sum((cents(row[field]) or Decimal("0") for row in old.values()), Decimal("0"))),
                "actual_cents": str(sum((cents(row[field]) or Decimal("0") for row in new.values()), Decimal("0"))),
                "nulls": sum(row[field] is None for row in old.values()),
                "zeros": sum(row[field] == 0 for row in old.values()),
                "rounded_rows": sum(row[field] is not None and Decimal(str(row[field])) != cents(row[field]) for row in old.values()),
            } for field in fields},
        }
        assert all(item["expected_cents"] == item["actual_cents"] for item in results[model]["totals"].values())
    for table in before.keys() - REGISTERS.keys() - {"django_migrations"}:
        assert table_digest(before[table]) == table_digest(after[table]), f"Unrelated table changed: {table}"
    old_contract = identity_contract(before["expenses_expense"], converted=False)
    assert identity_contract(after["expenses_expense"], converted=True) == old_contract, "Historical fingerprint/reference deduplication contract changed"
    results["identity"] = {"statement_rows": len(old_contract), "fingerprint_mismatches": 0, "reference_signature_mismatches": 0,
                           "transfer_legs": sum(row["category"] == "transfer" for row in before["expenses_expense"])}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(strict=True), args.output_dir.resolve()
    if output == source.parent or source.parent in output.parents or output == ROOT or ROOT in output.parents:
        raise ValueError("Output must be outside the source runtime and repository.")
    output.mkdir(parents=True, exist_ok=False)
    captured = source_hashes(source)
    shadow = output / "source-shadow"
    shadow.mkdir()
    for name in captured:
        shutil.copy2(source.parent / name, shadow / name)
    assert captured == source_hashes(source), "Source changed during capture; retain evidence and retry a fresh capture"
    assert captured == {name: file_hash(shadow / name) for name in captured}, "Raw capture hash mismatch"
    original_rows, original_fk = read_database(shadow / source.name)
    backup = output / "fresh-pre-migration-backup.sqlite3"
    copy_database(shadow / source.name, backup)
    before, backup_fk = read_database(backup)
    assert database_digests(before) == database_digests(original_rows) and backup_fk == original_fk, "Fresh backup failed logical reconciliation"
    runtime = output / "rehearsal-runtime"
    runtime.mkdir()
    rehearsal = runtime / "db.sqlite3"
    copy_database(backup, rehearsal)
    os.environ.update(ALFRED_LOCAL_RUNTIME="true", ALFRED_AUTO_TRAIN_ON_STARTUP="false", ALFRED_DATA_DIR=str(runtime), DATABASE_URL="sqlite:///" + rehearsal.as_posix(), CACHE_BACKEND="django.core.cache.backends.locmem.LocMemCache", CACHE_LOCATION="money-rehearsal", DJANGO_SECRET_KEY="disposable-rehearsal-key-only", DJANGO_SETTINGS_MODULE="alfred_ai.settings")
    sys.path.insert(0, str(ROOT))
    import django
    django.setup()
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    assert Path(connection.settings_dict["NAME"]).resolve() == rehearsal, "Django DB is not disposable"
    executor = MigrationExecutor(connection)
    plan = [(migration.app_label, migration.name) for migration, reverse in executor.migration_plan(TARGETS) if not reverse]
    assert set(plan) == set(TARGETS) and len(plan) == 2, f"Unexpected migration plan: {plan}"
    old_targets = [("investments", "0003_rename_investmenti_user_id_a9ad33_idx_investments_user_id_cbfa4c_idx_and_more"), ("expenses", "0004_statementupload_extracted_payload_and_more")]
    executor.migrate(TARGETS)
    connection.close()
    after, migrated_fk = read_database(rehearsal)
    assert migrated_fk == original_fk, "Migration introduced foreign-key violations"
    reconciliation = reconcile(before, after)
    executor = MigrationExecutor(connection)
    assert not executor.migration_plan(TARGETS), "Repeat migration has pending work"
    executor.migrate(TARGETS)
    apps = executor.loader.project_state().apps
    with connection.schema_editor() as editor:
        for domain, name in TARGETS:
            import_module(f"apps.{domain}.migrations.{name}").apply_normalized_money(apps, editor)
    connection.close()
    repeated, _ = read_database(rehearsal)
    assert database_digests(repeated) == database_digests(after), "Repeat apply changed data"
    rollback = output / "rollback.sqlite3"
    copy_database(rehearsal, rollback)
    # Reverse on a second disposable copy, preserving the successful upgrade.
    connection.settings_dict["NAME"] = str(rollback)
    MigrationExecutor(connection).migrate(old_targets)
    connection.close()
    reversed_rows, reversed_fk = read_database(rollback)
    assert database_digests(reversed_rows) == database_digests(before) and reversed_fk == original_fk, "Unedited reverse did not restore original data"
    assert source_hashes(source) == captured, "Private source bytes changed during rehearsal"
    result = {"status": "passed", "migrations": TARGETS, "private_db_unchanged": True, "source_hashes": captured,
              "fresh_backup": {"path": str(backup), "sha256": file_hash(backup), "integrity": "ok", "logical_reconciliation": True, "independent_verification": "pending"},
              "pre_migration_tables": database_digests(before), "reconciliation": reconciliation,
              "foreign_key_violations_before": len(original_fk), "foreign_key_violations_after": len(migrated_fk),
              "repeat_apply_unchanged": True, "unedited_rollback_exact": True}
    (output / "private-rehearsal-result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": "passed", "private_db_unchanged": True, "register_rows": {key: value["rows"] for key, value in reconciliation.items() if key != "identity"}, "identity": reconciliation["identity"], "repeat_apply_unchanged": True, "unedited_rollback_exact": True}))


if __name__ == "__main__":
    main()
