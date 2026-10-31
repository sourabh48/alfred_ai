"""User money persistence, existing-account compatibility and owned recovery."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from importlib import import_module
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import connection, connections
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.expenses.models import Expense
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.loans.models import Loan
from apps.users.models import UserMoneySnapshot
from apps.users.services import clear_user_fed_data
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest

FIELDS = ('monthly_income', 'variable_income', 'rent_or_emi')


class UserMoneyRuntimeTests(TestCase):
    def setUp(self):
        cache.clear()
        self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='user-money-owner', monthly_income='10000.01',
            variable_income='200.02', rent_or_emi='1000.03')
        self.other = get_user_model().objects.create_user(username='user-money-other', monthly_income='20.01')
        self.client.force_login(self.owner)

    def test_exact_cents_large_values_numeric_api_and_owner_assignment(self):
        result = self.client.patch('/api/users/profile/', json.dumps({'id': self.other.pk,
            'monthly_income': '123456789012.34', 'variable_income': '0.01', 'rent_or_emi': '0.00'}), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['id'], self.owner.pk)
        self.assertIsInstance(result.json()['monthly_income'], float)
        self.owner.refresh_from_db(); self.other.refresh_from_db()
        self.assertEqual(tuple(getattr(self.owner, field) for field in FIELDS),
            (Decimal('123456789012.34'), Decimal('0.01'), Decimal('0.00')))
        self.assertEqual(self.other.monthly_income, Decimal('20.01'))
        self.assertNotIn('currency', result.json())
        self.assertNotIn('money_snapshot', result.json())

    def test_canonical_cross_module_baseline_retains_exact_cent_inputs(self):
        Loan.objects.create(user=self.owner, principal='1000.01', remaining_balance='1000.01', emi='500.01',
            interest_rate=5, tenure_months=10, start_date=date(2026, 1, 1))
        from django.utils import timezone
        for amount in ('0.10', '0.20'):
            Expense.objects.create(user=self.owner, amount=amount, category='food', transaction_date=timezone.localdate())
        baseline = resolve_canonical_financial_baseline(self.owner)
        self.assertEqual({key: baseline[key] for key in ('monthly_income', 'annual_income', 'fixed_obligations', 'disposable_cash_flow')},
            {'monthly_income': 10000.01, 'annual_income': 120000.12, 'fixed_obligations': 1500.04, 'disposable_cash_flow': 8499.97})
        self.assertEqual(baseline['savings_capacity'], 8499.67)

    def test_reset_clears_only_owned_snapshot_and_account_deletion_cascades(self):
        for user in (self.owner, self.other):
            UserMoneySnapshot.objects.create(user=user, original_user_id=user.pk,
                source_values=dict.fromkeys(FIELDS, '0.005'), normalized_values=dict.fromkeys(FIELDS, '0.01'))
        clear_user_fed_data(self.owner)
        self.owner.refresh_from_db()
        self.assertEqual(tuple(getattr(self.owner, field) for field in FIELDS), (0, 0, 0))
        self.assertEqual(UserMoneySnapshot.objects.get().user_id, self.other.pk)
        self.other.delete()
        self.assertFalse(UserMoneySnapshot.objects.exists())


class UserMoneyMigrationTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.enterContext(_offline_fixture_patches())
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        self.old_targets = [('users', '0002_user_ml_training_consent') if item[0] == 'users' else item for item in self.leaves]
        executor.migrate(self.old_targets)
        self.old = executor.loader.project_state(self.old_targets).apps
        self.owner = self.old.get_model('users', 'User').objects.create(username='existing-money-owner',
            password=make_password('SyntheticLogin42!'), monthly_income=2.675, variable_income=.1 + .2, rent_or_emi=10.005)
        self.module = import_module('apps.users.migrations.0003_user_money_decimal')

    def upgrade(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.leaves)
        return executor.loader.project_state(self.leaves).apps

    def test_existing_account_password_groups_session_and_original_values_survive(self):
        group = self.old.get_model('auth', 'Group').objects.create(name='synthetic-owner-role')
        self.owner.groups.add(group)
        # The live model has fields newer than this historical schema.
        self.client.force_login(get_user_model().objects.defer('monthly_income_basis').get(pk=self.owner.pk))
        key = self.client.session.session_key
        before = self.old.get_model('users', 'User').objects.values().get(pk=self.owner.pk)
        apps = self.upgrade()
        row = apps.get_model('users', 'User').objects.get(pk=self.owner.pk)
        self.assertEqual(tuple(getattr(row, field) for field in FIELDS), (Decimal('2.68'), Decimal('0.30'), Decimal('10.01')))
        self.assertEqual(row.password, before['password'])
        self.assertEqual(list(row.groups.values_list('id', flat=True)), [group.pk])
        self.assertEqual(self.client.get('/api/users/profile/').status_code, 200)
        self.assertEqual(self.client.session.session_key, key)
        snapshot = apps.get_model('users', 'UserMoneySnapshot').objects.get()
        self.assertEqual(snapshot.source_values, {field: repr(before[field]) for field in FIELDS})
        self.assertEqual(snapshot.user_id, snapshot.original_user_id)
        self.assertIsNotNone(snapshot.applied_at)
        after = apps.get_model('users', 'User').objects.values().get(pk=row.pk)
        self.assertEqual({field: value for field, value in before.items() if field not in FIELDS},
                         {field: value for field, value in after.items() if field not in (*FIELDS, 'monthly_income_basis')})
        MigrationExecutor(connection).migrate(self.old_targets)
        restored = self.old.get_model('users', 'User').objects.get(pk=row.pk)
        self.assertEqual(tuple(getattr(restored, field) for field in FIELDS), tuple(before[field] for field in FIELDS))

    def test_repeat_apply_and_reverse_preserve_corrections_and_new_accounts(self):
        apps = self.upgrade()
        User, Snapshot = apps.get_model('users', 'User'), apps.get_model('users', 'UserMoneySnapshot')
        original = Snapshot.objects.get().source_values
        User.objects.filter(pk=self.owner.pk).update(monthly_income=50)
        with connection.schema_editor() as editor:
            self.module.capture_legacy_money(apps, editor)
            self.module.apply_normalized_money(apps, editor)
            self.module.apply_normalized_money(apps, editor)
        self.assertEqual(Snapshot.objects.get().source_values, original)
        new = User.objects.create(username='post-migration-user', monthly_income=12)
        MigrationExecutor(connection).migrate(self.old_targets)
        Old = self.old.get_model('users', 'User')
        row = Old.objects.get(pk=self.owner.pk)
        self.assertEqual((row.monthly_income, row.rent_or_emi), (50, 10.005))
        self.assertEqual(Old.objects.get(pk=new.pk).monthly_income, 12)

    def test_wrong_owner_and_unapplied_evidence_cannot_restore(self):
        apps = self.upgrade()
        User, Snapshot = apps.get_model('users', 'User'), apps.get_model('users', 'UserMoneySnapshot')
        other = User.objects.create(username='different-money-owner', monthly_income=30)
        snapshot = Snapshot.objects.get()
        snapshot.user_id = other.pk
        snapshot.save(update_fields=['user'])
        with connection.schema_editor() as editor:
            self.module.restore_legacy_money(apps, editor)
        self.assertEqual(User.objects.get(pk=other.pk).monthly_income, 30)
        Snapshot.objects.filter(pk=snapshot.pk).update(user_id=self.owner.pk, applied_at=None)
        MigrationExecutor(connection).migrate(self.old_targets)
        self.assertEqual(self.old.get_model('users', 'User').objects.get(pk=self.owner.pk).monthly_income, 2.68)

    def test_invalid_history_rolls_back_entire_migration(self):
        Old = self.old.get_model('users', 'User')
        for value in (-1, float('inf'), 1000000000000):
            Old.objects.filter(pk=self.owner.pk).update(monthly_income=value)
            with self.assertRaises(ValueError):
                self.upgrade()
            self.assertNotIn('users_usermoneysnapshot', connection.introspection.table_names())
            self.assertEqual(Old.objects.get(pk=self.owner.pk).rent_or_emi, 10.005)
        Old.objects.filter(pk=self.owner.pk).update(monthly_income=2.675)

    def test_cent_history_financial_baseline_has_zero_mismatches(self):
        self.old.get_model('users', 'User').objects.filter(pk=self.owner.pk).update(monthly_income=10000.01, variable_income=200.02, rent_or_emi=1000.03)
        # The live model has fields newer than this historical schema.
        old_owner = get_user_model().objects.defer('monthly_income_basis').get(pk=self.owner.pk)
        old_owner.monthly_income_basis = 'monthly'
        before = resolve_canonical_financial_baseline(old_owner)
        self.upgrade(); cache.clear()
        get_user_model().objects.filter(pk=self.owner.pk).update(monthly_income_basis='monthly')
        after = resolve_canonical_financial_baseline(get_user_model().objects.get(pk=self.owner.pk))
        self.assertEqual(before, after)

    def test_disposable_alias_backup_restore_and_full_financial_reconciliation(self):
        with TemporaryDirectory(prefix='alfred-user-money-rehearsal-') as directory:
            root = Path(directory)
            source, candidate, restored = [root / name for name in ('source.sqlite3', 'candidate.sqlite3', 'restored.sqlite3')]
            alias = 'user_money_rehearsal'
            db = connection.copy(alias=alias); db.settings_dict['NAME'] = str(source); connections[alias] = db
            try:
                executor = MigrationExecutor(db); executor.migrate(self.old_targets)
                state = executor.loader.project_state(self.old_targets).apps
                owner = state.get_model('users', 'User').objects.using(alias).create(username='synthetic-rehearsal-owner', monthly_income=2.675, rent_or_emi=10.005)
                other = state.get_model('users', 'User').objects.using(alias).create(username='synthetic-rehearsal-other', monthly_income=20.01)
                from django.utils import timezone
                from datetime import timedelta
                state.get_model('family', 'FamilyAccountLink').objects.using(alias).create(created_by_id=owner.pk,
                    linked_user_id=other.pk, invite_code_hash='synthetic-user-money-family', status='active',
                    expires_at=timezone.now() + timedelta(days=1), share_financial_summary=False)
                account = state.get_model('expenses', 'BankAccount').objects.using(alias).create(user_id=owner.pk, account_number='SYNTHETIC', current_balance='123.45')
                for direction in ('debit', 'credit'):
                    state.get_model('expenses', 'Expense').objects.using(alias).create(user_id=owner.pk, bank_account_id=account.pk,
                        amount='12.34', category='transfer', direction=direction, transaction_date=date(2026, 10, 1),
                        transaction_fingerprint='synthetic-user-' + direction, external_reference='SYNTHETIC')
                state.get_model('loans', 'Loan').objects.using(alias).create(user_id=owner.pk, principal='200.01', emi='20.01',
                    interest_rate=5, tenure_months=10, remaining_balance='100.01', start_date=date(2026, 1, 1))
                state.get_model('investments', 'Investment').objects.using(alias).create(user_id=owner.pk,
                    asset_name='Synthetic', invested_amount='12.34', current_value='15.67')
                db.close(); original_hash = file_hash(source)
                before, _ = read_database(source)
                copy_database(source, candidate); copy_database(source, restored)
                self.assertEqual(read_database(restored), read_database(source))
                db.settings_dict['NAME'] = str(candidate)
                executor = MigrationExecutor(db); executor.migrate(self.leaves)
                db.close(); after, _ = read_database(candidate)
                for table in before.keys() - {'users_user', 'django_migrations'}:
                    self.assertEqual(table_digest(before[table]), table_digest(after[table]), table)
                updated = {row['id']: row for row in after['users_user']}
                self.assertEqual(set(updated), {row['id'] for row in before['users_user']})
                for old in before['users_user']:
                    for field, value in old.items():
                        expected = Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP) if field in FIELDS else value
                        actual = Decimal(str(updated[old['id']][field])) if field in FIELDS else updated[old['id']][field]
                        self.assertEqual(expected, actual, field)
                executor = MigrationExecutor(db); executor.migrate(self.old_targets)
                db.close(); reverse, _ = read_database(candidate)
                self.assertEqual({table: table_digest(rows) for table, rows in reverse.items()},
                                 {table: table_digest(rows) for table, rows in before.items()})
                self.assertEqual(file_hash(source), original_hash)
                self.assertEqual(self.old.get_model('users', 'User').objects.get(pk=self.owner.pk).monthly_income, 2.675)
            finally:
                db.close(); del connections[alias]
