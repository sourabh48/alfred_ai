"""Career salary cents without changing experience, provenance or owner scope."""
from datetime import date, timedelta
from decimal import Decimal
from importlib import import_module
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.career.models import CareerProfile, CareerProfileMoneySnapshot
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.users.services import clear_user_fed_data
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest


class CareerMoneyRuntimeTests(TestCase):
    def setUp(self):
        cache.clear(); self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='career-money-owner')
        self.other = get_user_model().objects.create_user(username='career-money-other')
        self.row = CareerProfile.objects.create(user=self.owner, role='Synthetic role', skills='Python', experience_years=4.123456, last_salary='10000.01')
        self.client.force_login(self.owner)

    def test_numeric_api_half_up_and_owner_scope_preserve_measurements(self):
        payload = {'user': self.other.pk, 'role': self.row.role, 'skills': self.row.skills,
                   'experience_years': self.row.experience_years, 'last_salary': '2.675'}
        invalid = self.client.put('/api/career/', json.dumps({**payload, 'skills': ''}), content_type='application/json')
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('skills', invalid.json())
        result = self.client.put('/api/career/', json.dumps(payload), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertIsInstance(result.json()['last_salary'], float)
        self.row.refresh_from_db()
        self.assertEqual((self.row.last_salary, self.row.user_id, self.row.experience_years), (Decimal('2.68'), self.owner.pk, 4.123456))
        self.assertNotIn('money_snapshots', result.json())
        self.assertNotIn('currency', result.json())

    def test_invalid_api_and_orm_values_do_not_mutate_salary(self):
        for value in ('NaN', 'Infinity', '-Infinity', True, '1000000000000', 'bad'):
            with self.subTest(value=value):
                result = self.client.patch('/api/career/', json.dumps({'last_salary': value, 'role': 'changed'}), content_type='application/json')
                self.assertEqual(result.status_code, 400)
                with self.assertRaises(ValidationError), transaction.atomic():
                    CareerProfile.objects.filter(pk=self.row.pk).update(last_salary=value)
                self.row.refresh_from_db()
                self.assertEqual((self.row.last_salary, self.row.role), (Decimal('10000.01'), 'Synthetic role'))

    def test_signed_legacy_cents_zero_and_large_amount_round_trip(self):
        for value, expected in (('-1.005', '-1.01'), ('0', '0.00'), ('999999999999.99', '999999999999.99')):
            CareerProfile.objects.filter(pk=self.row.pk).update(last_salary=value)
            self.row.refresh_from_db()
            self.assertEqual(self.row.last_salary, Decimal(expected))

    def test_salary_fallback_baseline_and_owned_orphan_reset(self):
        self.assertEqual(resolve_canonical_financial_baseline(self.owner)['monthly_income'], 10000.01)
        for owner in (self.owner, self.other):
            row = self.row if owner == self.owner else CareerProfile.objects.create(user=owner, role='Other', skills='', experience_years=0)
            CareerProfileMoneySnapshot.objects.create(user=owner, career_profile=row, original_career_profile_id=row.pk,
                source_values={'last_salary': '1.005'}, normalized_values={'last_salary': '1.01'})
            row.delete()
        clear_user_fed_data(self.owner)
        self.assertEqual(CareerProfileMoneySnapshot.objects.get().user_id, self.other.pk)


class CareerMoneyMigrationTests(TransactionTestCase):
    def setUp(self):
        cache.clear(); self.enterContext(_offline_fixture_patches())
        executor = MigrationExecutor(connection)
        self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        self.old_targets = [('career', '0004_alter_careerjobanalysis_options_and_more') if item[0] == 'career' else item for item in self.leaves]
        executor.migrate(self.old_targets)
        self.old = executor.loader.project_state(self.old_targets).apps
        self.owner = self.old.get_model('users', 'User').objects.create(username='career-legacy-owner')
        self.row = self.old.get_model('career', 'CareerProfile').objects.create(user_id=self.owner.pk, role='Synthetic', skills='Python',
            experience_years=4.123456, last_salary=2.675)
        self.module = import_module('apps.career.migrations.0005_career_salary_decimal')

    def upgrade(self):
        executor = MigrationExecutor(connection); executor.migrate(self.leaves)
        return executor.loader.project_state(self.leaves).apps

    def test_forward_reverse_retains_salary_and_all_nonmoney_fields(self):
        before = self.old.get_model('career', 'CareerProfile').objects.values().get(pk=self.row.pk)
        apps = self.upgrade()
        row = apps.get_model('career', 'CareerProfile').objects.get(pk=self.row.pk)
        self.assertEqual(row.last_salary, Decimal('2.68'))
        self.assertEqual((row.user_id, row.experience_years, row.skills), (self.owner.pk, before['experience_years'], before['skills']))
        snapshot = apps.get_model('career', 'CareerProfileMoneySnapshot').objects.get()
        self.assertEqual(snapshot.source_values, {'last_salary': '2.675'})
        self.assertIsNotNone(snapshot.applied_at)
        MigrationExecutor(connection).migrate(self.old_targets)
        self.assertEqual(self.old.get_model('career', 'CareerProfile').objects.values().get(pk=self.row.pk), before)

    def test_repeat_apply_and_reverse_preserve_edits_and_new_records(self):
        apps = self.upgrade(); Profile = apps.get_model('career', 'CareerProfile')
        Profile.objects.filter(pk=self.row.pk).update(last_salary=50)
        with connection.schema_editor() as editor:
            self.module.capture_legacy_money(apps, editor); self.module.apply_normalized_money(apps, editor)
        other = apps.get_model('users', 'User').objects.create(username='new-career-owner')
        fresh = Profile.objects.create(user_id=other.pk, role='New', skills='', experience_years=0, last_salary=12)
        MigrationExecutor(connection).migrate(self.old_targets)
        Old = self.old.get_model('career', 'CareerProfile')
        self.assertEqual(Old.objects.get(pk=self.row.pk).last_salary, 50)
        self.assertEqual(Old.objects.get(pk=fresh.pk).last_salary, 12)

    def test_changed_owner_and_unapplied_evidence_cannot_restore(self):
        apps = self.upgrade(); Profile = apps.get_model('career', 'CareerProfile')
        Snapshot = apps.get_model('career', 'CareerProfileMoneySnapshot')
        other = apps.get_model('users', 'User').objects.create(username='changed-career-owner')
        Profile.objects.filter(pk=self.row.pk).update(user_id=other.pk)
        with connection.schema_editor() as editor:
            self.module.restore_legacy_money(apps, editor)
        self.assertEqual(Profile.objects.get(pk=self.row.pk).last_salary, Decimal('2.68'))
        Profile.objects.filter(pk=self.row.pk).update(user_id=self.owner.pk)
        Snapshot.objects.filter(career_profile_id=self.row.pk).update(applied_at=None)
        MigrationExecutor(connection).migrate(self.old_targets)
        self.assertEqual(self.old.get_model('career', 'CareerProfile').objects.get(pk=self.row.pk).last_salary, 2.68)

    def test_invalid_history_aborts_atomically(self):
        Old = self.old.get_model('career', 'CareerProfile')
        for amount in (float('inf'), -float('inf'), 1000000000000):
            Old.objects.filter(pk=self.row.pk).update(last_salary=amount)
            with self.assertRaises(ValueError): self.upgrade()
            self.assertNotIn('career_careerprofilemoneysnapshot', connection.introspection.table_names())
        Old.objects.filter(pk=self.row.pk).update(last_salary=2.675)

    def test_cent_salary_baseline_has_zero_mismatches(self):
        self.old.get_model('career', 'CareerProfile').objects.filter(pk=self.row.pk).update(last_salary=10000.01)
        before = resolve_canonical_financial_baseline(get_user_model().objects.get(pk=self.owner.pk))
        self.upgrade(); cache.clear()
        self.assertEqual(before, resolve_canonical_financial_baseline(get_user_model().objects.get(pk=self.owner.pk)))

    def test_disposable_alias_backup_restore_and_unrelated_financial_rows(self):
        with TemporaryDirectory(prefix='alfred-career-money-') as directory:
            root = Path(directory); source = root/'source.sqlite3'; candidate = root/'candidate.sqlite3'
            alias = 'career_money_rehearsal'
            db = connection.copy(alias=alias); db.settings_dict['NAME'] = str(source); connections[alias] = db
            try:
                executor = MigrationExecutor(db); executor.migrate(self.old_targets)
                state = executor.loader.project_state(self.old_targets).apps
                user = state.get_model('users', 'User').objects.using(alias).create(username='career-copy-owner')
                other = state.get_model('users', 'User').objects.using(alias).create(username='career-copy-other')
                state.get_model('career', 'CareerProfile').objects.using(alias).create(user_id=user.pk, role='Synthetic', skills='SQL',
                    experience_years=4.123456, last_salary=-1.005)
                state.get_model('career', 'CareerResume').objects.using(alias).create(user_id=user.pk, file_name='synthetic.txt',
                    parse_confidence=.9123456, extracted_payload={'source_salary': '-1.005'})
                account = state.get_model('expenses', 'BankAccount').objects.using(alias).create(user_id=user.pk, account_number='SYNTHETIC', current_balance='123.45')
                for direction in ('debit', 'credit'):
                    state.get_model('expenses', 'Expense').objects.using(alias).create(user_id=user.pk, bank_account_id=account.pk,
                        amount='12.34', direction=direction, category='transfer', transaction_date=date(2026, 10, 1),
                        transaction_fingerprint='synthetic-career-'+direction, external_reference='SYNTHETIC')
                state.get_model('loans', 'Loan').objects.using(alias).create(user_id=user.pk, principal='200.01', emi='20.01',
                    interest_rate=5, tenure_months=10, remaining_balance='100.01', start_date=date(2026, 1, 1))
                state.get_model('investments', 'Investment').objects.using(alias).create(user_id=user.pk,
                    asset_name='Synthetic', invested_amount='12.34', current_value='15.67')
                state.get_model('family', 'FamilyAccountLink').objects.using(alias).create(created_by_id=user.pk, linked_user_id=other.pk,
                    invite_code_hash='synthetic-career-family', status='active', expires_at=timezone.now()+timedelta(days=1))
                db.close(); before, _ = read_database(source); source_hash = file_hash(source)
                copy_database(source, candidate); copy_database(source, root/'restored.sqlite3')
                self.assertEqual(read_database(source), read_database(root/'restored.sqlite3'))
                db.settings_dict['NAME'] = str(candidate)
                executor = MigrationExecutor(db); executor.migrate(self.leaves); db.close()
                after, _ = read_database(candidate)
                for table in before.keys()-{'career_careerprofile','django_migrations'}:
                    self.assertEqual(table_digest(before[table]),table_digest(after[table]),table)
                old, new = before['career_careerprofile'][0], after['career_careerprofile'][0]
                self.assertEqual(Decimal(str(new['last_salary'])), Decimal('-1.01'))
                self.assertEqual({k:v for k,v in old.items() if k!='last_salary'}, {k:v for k,v in new.items() if k!='last_salary'})
                executor = MigrationExecutor(db); executor.migrate(self.old_targets); db.close()
                reverse, _ = read_database(candidate)
                self.assertEqual({k:table_digest(v) for k,v in before.items()}, {k:table_digest(v) for k,v in reverse.items()})
                self.assertEqual(file_hash(source),source_hash)
            finally:
                db.close(); del connections[alias]
