"""Budget-only forward/reverse and independent synthetic recovery rehearsal."""
from datetime import date, timedelta
from decimal import Decimal
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest


class BudgetMoneyMigrationTests(TransactionTestCase):
    before = ('budgets', '0001_initial')
    after = ('budgets', '0002_budget_money_decimal')

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        self.old_targets = [self.before if target[0] == 'budgets' else target for target in self.leaves]
        executor.migrate(self.old_targets)
        self.old = executor.loader.project_state(self.old_targets).apps
        self.owner = self.old.get_model('users', 'User').objects.create(username='budget-legacy-owner')
        self.module = import_module('apps.budgets.migrations.0002_budget_money_decimal')

    def seed(self):
        return self.old.get_model('budgets', 'Budget').objects.create(user_id=self.owner.pk,
            month='Oct 2026', base_budget=2.675, inflation_adjusted=10.005, spent=.1 + .2)

    def upgrade(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.leaves)
        return executor.loader.project_state(self.leaves).apps

    def test_conversion_retains_values_ownership_and_exact_reverse(self):
        row = self.seed()
        apps = self.upgrade()
        new = apps.get_model('budgets', 'Budget').objects.get(pk=row.pk)
        self.assertEqual((new.base_budget, new.inflation_adjusted, new.spent),
                         (Decimal('2.68'), Decimal('10.01'), Decimal('0.30')))
        snapshot = apps.get_model('budgets', 'BudgetMoneySnapshot').objects.get()
        self.assertEqual(snapshot.source_values, {'base_budget': '2.675', 'inflation_adjusted': '10.005', 'spent': repr(.1 + .2)})
        self.assertEqual((new.pk, new.user_id, new.month), (row.pk, row.user_id, row.month))
        self.assertEqual((snapshot.original_budget_id, snapshot.budget_id, snapshot.user_id), (row.pk, row.pk, row.user_id))
        self.assertIsNotNone(snapshot.applied_at)
        MigrationExecutor(connection).migrate(self.old_targets)
        restored = self.old.get_model('budgets', 'Budget').objects.get(pk=row.pk)
        self.assertEqual((restored.base_budget, restored.inflation_adjusted, restored.spent),
                         (row.base_budget, row.inflation_adjusted, row.spent))

    def test_idempotence_and_reverse_preserve_edits_new_rows_and_changed_owners(self):
        row = self.seed()
        changed_owner = self.seed()
        apps = self.upgrade()
        New, Snapshot = apps.get_model('budgets', 'Budget'), apps.get_model('budgets', 'BudgetMoneySnapshot')
        retained = Snapshot.objects.get(original_budget_id=row.pk).source_values
        New.objects.filter(pk=row.pk).update(base_budget=50)
        other = apps.get_model('users', 'User').objects.create(username='changed-budget-owner')
        New.objects.filter(pk=changed_owner.pk).update(user_id=other.pk)
        with connection.schema_editor() as editor:
            self.module.capture_legacy_money(apps, editor)
            self.module.apply_normalized_money(apps, editor)
            self.module.apply_normalized_money(apps, editor)
        self.assertEqual(Snapshot.objects.get(original_budget_id=row.pk).source_values, retained)
        self.assertEqual(New.objects.get(pk=row.pk).base_budget, 50)
        fresh = New.objects.create(user_id=self.owner.pk, month='New', base_budget=12, inflation_adjusted=12)
        MigrationExecutor(connection).migrate(self.old_targets)
        Old = self.old.get_model('budgets', 'Budget')
        restored = Old.objects.get(pk=row.pk)
        self.assertEqual((restored.base_budget, restored.inflation_adjusted), (50, 10.005))
        self.assertEqual(Old.objects.get(pk=changed_owner.pk).base_budget, 2.68)
        self.assertEqual(Old.objects.get(pk=fresh.pk).base_budget, 12)

    def test_unapplied_and_deleted_evidence_do_not_restore(self):
        row = self.seed()
        deleted = self.seed()
        apps = self.upgrade()
        Snapshot = apps.get_model('budgets', 'BudgetMoneySnapshot')
        Snapshot.objects.filter(original_budget_id=row.pk).update(applied_at=None)
        apps.get_model('budgets', 'Budget').objects.get(pk=deleted.pk).delete()
        self.assertIsNone(Snapshot.objects.get(original_budget_id=deleted.pk).budget_id)
        MigrationExecutor(connection).migrate(self.old_targets)
        Old = self.old.get_model('budgets', 'Budget')
        self.assertEqual(Old.objects.get(pk=row.pk).base_budget, 2.68)
        self.assertFalse(Old.objects.filter(pk=deleted.pk).exists())

    def test_invalid_legacy_rows_abort_before_any_snapshot_writes(self):
        good = self.seed()
        invalid = self.seed()
        Old = self.old.get_model('budgets', 'Budget')
        for amount in (-1, float('inf'), 1000000000000):
            Old.objects.filter(pk=invalid.pk).update(base_budget=amount)
            with self.assertRaises(ValueError):
                self.upgrade()
            self.assertNotIn('budgets_budgetmoneysnapshot', connection.introspection.table_names())
            self.assertEqual(Old.objects.get(pk=good.pk).base_budget, 2.675)
        Old.objects.filter(pk=invalid.pk).update(base_budget=2.675)

    def test_disposable_backup_restore_and_forward_reverse_reconcile_all_other_tables(self):
        with TemporaryDirectory(prefix='alfred-budget-rehearsal-') as directory:
            root = Path(directory)
            source, candidate, restored = [root / name for name in ('source.sqlite3', 'candidate.sqlite3', 'restored.sqlite3')]
            alias = 'budget_money_rehearsal'
            db = connection.copy(alias=alias)
            db.settings_dict['NAME'] = str(source)
            connections[alias] = db
            try:
                executor = MigrationExecutor(db)
                executor.migrate(self.old_targets)
                state = executor.loader.project_state(self.old_targets).apps
                user = state.get_model('users', 'User').objects.using(alias).create(username='rehearsal-owner', monthly_income=10000)
                other = state.get_model('users', 'User').objects.using(alias).create(username='rehearsal-other')
                state.get_model('budgets', 'Budget').objects.using(alias).create(user_id=user.pk, month='Oct 2026',
                    base_budget=2.675, inflation_adjusted=10.005, spent=.1 + .2)
                account = state.get_model('expenses', 'BankAccount').objects.using(alias).create(user_id=user.pk,
                    account_number='SYNTHETIC-BUDGET', current_balance='123.45')
                for direction in ('debit', 'credit'):
                    state.get_model('expenses', 'Expense').objects.using(alias).create(user_id=user.pk, bank_account_id=account.pk,
                        amount='12.34', category='transfer', direction=direction, transaction_date=date(2026, 10, 1),
                        transaction_fingerprint='synthetic-transfer-' + direction, external_reference='SYNTHETIC-REF')
                state.get_model('loans', 'Loan').objects.using(alias).create(user_id=user.pk, loan_type='personal', lender='Synthetic',
                    principal='200.01', remaining_balance='100.01', emi='20.01', interest_rate=5, tenure_months=10, start_date=date(2026, 1, 1))
                state.get_model('investments', 'Investment').objects.using(alias).create(user_id=user.pk,
                    asset_type='cash', asset_name='Synthetic', invested_amount='12.34', current_value='15.67')
                state.get_model('family', 'FamilyAccountLink').objects.using(alias).create(created_by_id=user.pk,
                    linked_user_id=other.pk, invite_code_hash='synthetic-budget-link', status='active',
                    expires_at=timezone.now() + timedelta(days=1), share_financial_summary=False)
                db.close()
                original_hash = file_hash(source)
                before, _ = read_database(source)
                copy_database(source, candidate)
                copy_database(source, restored)
                self.assertEqual(read_database(restored), read_database(source))
                db.settings_dict['NAME'] = str(candidate)
                executor = MigrationExecutor(db)
                executor.migrate(self.leaves)
                apps = executor.loader.project_state(self.leaves).apps
                converted = apps.get_model('budgets', 'Budget').objects.using(alias).get()
                self.assertEqual((converted.base_budget, converted.inflation_adjusted, converted.spent),
                                 (Decimal('2.68'), Decimal('10.01'), Decimal('0.30')))
                self.assertEqual(apps.get_model('budgets', 'BudgetMoneySnapshot').objects.using(alias).get().user_id, user.pk)
                db.close()
                after, _ = read_database(candidate)
                for table in before.keys() - {'budgets_budget', 'django_migrations'}:
                    self.assertEqual(table_digest(before[table]), table_digest(after[table]), table)
                executor = MigrationExecutor(db)
                executor.migrate(self.old_targets)
                db.close()
                reverse, _ = read_database(candidate)
                self.assertEqual({table: table_digest(rows) for table, rows in reverse.items()},
                                 {table: table_digest(rows) for table, rows in before.items()})
                self.assertEqual(file_hash(source), original_hash)
            finally:
                db.close()
                del connections[alias]
