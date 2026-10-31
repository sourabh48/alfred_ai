"""Synthetic Mobility cents, parent ownership and reversible legacy evidence."""
from datetime import date, timedelta
from decimal import Decimal
from importlib import import_module
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.apps import apps as live_apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.mobility.models import MobilityMoneySnapshot, TravelPlanningSession
from apps.users.services import clear_user_fed_data
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from scripts.rehearse_money_migrations import copy_database, file_hash, read_database, table_digest

TODAY = date(2026, 10, 1)
FIELDS = {'BikeProfile': ('estimated_market_value', 'monthly_income_support'),
          'BikeServiceRecord': ('cost',), 'FuelRefillLog': ('total_cost',),
          'TravelPlan': ('budget',), 'TripLog': ('spend_amount',),
          'BikeIssueReport': ('projected_cost', 'actual_cost'), 'BikeDocument': ('premium_amount',)}


def mobility_rows(apps, user, alias='default', amount=2.675):
    def create(name, **values):
        return apps.get_model('mobility', name).objects.using(alias).create(user_id=user.pk, **values)
    profile = create('BikeProfile', display_name='Synthetic vehicle', model_name='Custom', engine_cc=349.123456,
                     estimated_market_value=amount, monthly_income_support=amount)
    document = create('BikeDocument', bike_profile_id=profile.pk, bike_name=profile.display_name, premium_amount=amount,
                      parse_confidence=.9123456, extracted_payload={'original_amount': str(amount)})
    service = create('BikeServiceRecord', bike_profile_id=profile.pk, source_document_id=document.pk,
                     bike_name=profile.display_name, service_date=TODAY, cost=amount, parsed_payload={'original_amount': str(amount)})
    refill = create('FuelRefillLog', bike_profile_id=profile.pk, bike_name=profile.display_name,
                    refill_date=TODAY, total_cost=amount, fuel_liters=2.123456, trip_meter_km=70.123456)
    plan = create('TravelPlan', vehicle_profile_id=profile.pk, title='Synthetic trip', destination='Synthetic town',
                  start_date=TODAY, end_date=TODAY, budget=amount)
    trip = create('TripLog', travel_plan_id=plan.pk, log_date=TODAY, title='Synthetic stop', spend_amount=amount, distance_km=20.123456)
    issue = create('BikeIssueReport', bike_profile_id=profile.pk, bike_service_id=service.pk, travel_plan_id=plan.pk,
                   title='Synthetic issue', symptom='Synthetic observation', projected_cost=amount, actual_cost=None)
    return {row.__class__.__name__: row for row in (profile, service, refill, plan, trip, issue, document)}


class MobilityMoneyRuntimeTests(TestCase):
    def setUp(self):
        cache.clear(); self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='mobility-money-owner', monthly_income='10000.01')
        self.other = get_user_model().objects.create_user(username='mobility-money-other')
        self.rows = mobility_rows(live_apps, self.owner)
        self.client.force_login(self.owner)

    def test_all_registers_store_exact_cents_without_rounding_measurements(self):
        for name, fields in FIELDS.items():
            row = self.rows[name]; row.refresh_from_db()
            for field in fields:
                self.assertEqual(getattr(row, field), None if field == 'actual_cost' else Decimal('2.68'), (name, field))
                for amount, expected in (('-1.005', '-1.01'), ('0', '0.00'), ('999999999999.99', '999999999999.99')):
                    row.__class__.objects.filter(pk=row.pk).update(**{field: amount})
                    row.refresh_from_db(); self.assertEqual(getattr(row, field), Decimal(expected))
        self.assertEqual(self.rows['BikeProfile'].engine_cc, 349.123456)
        self.assertEqual(self.rows['FuelRefillLog'].fuel_liters, 2.123456)
        self.assertEqual(self.rows['TripLog'].distance_km, 20.123456)
        self.assertEqual(self.rows['BikeDocument'].extracted_payload, {'original_amount': '2.675'})

    def test_nonfinite_malformed_boolean_and_overflow_never_write(self):
        for name, fields in FIELDS.items():
            row = self.rows[name]; row.refresh_from_db()
            before = {field: getattr(row, field) for field in fields}
            for field in fields:
                for amount in ('NaN', 'Infinity', '-Infinity', True, '1000000000000', 'bad'):
                    with self.subTest(name=name, field=field, amount=amount):
                        with self.assertRaises(ValidationError), transaction.atomic():
                            row.__class__.objects.filter(pk=row.pk).update(**{field: amount})
                row.refresh_from_db(); self.assertEqual(getattr(row, field), before[field])

    def test_numeric_apis_ownership_nullable_actual_and_readonly_prediction(self):
        routes = {'BikeProfile': 'bikes', 'BikeServiceRecord': 'bike-services', 'FuelRefillLog': 'bike-refills',
                  'TravelPlan': 'travel-plans', 'TripLog': 'trip-logs', 'BikeIssueReport': 'bike-issues', 'BikeDocument': 'bike-documents'}
        for name, route in routes.items():
            row = self.rows[name]
            response = self.client.get(f'/api/mobility/{route}/{row.pk}/')
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            for field in FIELDS[name]:
                if field != 'actual_cost': self.assertIsInstance(payload[field], (int, float))
            self.assertNotIn('money_snapshots', payload); self.assertNotIn('currency', payload)
            field = next(value for value in FIELDS[name] if value != 'projected_cost')
            for amount in ('NaN', 'Infinity', '-Infinity', '1000000000000', True, 'bad'):
                result = self.client.patch(f'/api/mobility/{route}/{row.pk}/', json.dumps({field: amount}), content_type='application/json')
                self.assertEqual(result.status_code, 400, (name, amount))
            result = self.client.patch(f'/api/mobility/{route}/{row.pk}/', json.dumps({field: '123.455', 'user': self.other.pk}), content_type='application/json')
            self.assertEqual(result.status_code, 200)
            row.refresh_from_db(); self.assertEqual((getattr(row, field), row.user_id), (Decimal('123.46'), self.owner.pk))
        issue = self.rows['BikeIssueReport']
        for amount, expected in ((None, None), ('0', Decimal('0')), ('2.675', Decimal('2.68'))):
            result = self.client.patch(f'/api/mobility/bike-issues/{issue.pk}/', json.dumps({'actual_cost': amount, 'projected_cost': 999}), content_type='application/json')
            self.assertEqual(result.status_code, 200); issue.refresh_from_db()
            self.assertEqual(issue.actual_cost, expected); self.assertNotEqual(issue.projected_cost, 999)
        foreign = mobility_rows(live_apps, self.other)
        service = self.rows['BikeServiceRecord']
        denied = self.client.patch(f'/api/mobility/bike-services/{service.pk}/', json.dumps({'bike_profile': foreign['BikeProfile'].pk, 'cost': '12.34'}), content_type='application/json')
        self.assertEqual(denied.status_code, 400)
        service.refresh_from_db(); self.assertEqual(service.cost, Decimal('123.46'))
        for name, route in routes.items():
            self.assertEqual(self.client.get(f'/api/mobility/{route}/{foreign[name].pk}/').status_code, 404)
        self.client.logout(); self.assertIn(self.client.get('/api/mobility/bikes/').status_code, (401, 403))

    def test_decimal_dashboards_and_plan_state_keep_numeric_json_contract(self):
        plan = self.rows['TravelPlan']
        session = TravelPlanningSession.objects.create(user=self.owner, plan=plan, state={})
        result = self.client.patch(f'/api/mobility/travel-plans/{plan.pk}/', json.dumps({'budget': '1234.565'}), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        session.refresh_from_db(); self.assertEqual(session.state['budget']['value'], 1234.57)
        refill = self.rows['FuelRefillLog']
        refill.__class__.objects.filter(pk=refill.pk).update(total_cost='5.35', fuel_liters=2)
        response = self.client.get(f'/api/mobility/bike-refills/{refill.pk}/')
        self.assertEqual(response.json()['fuel_price_per_liter'], 2.68)
        for path in ('dashboard', 'bike-service-dashboard'):
            result = self.client.get(f'/api/mobility/{path}/')
            self.assertEqual(result.status_code, 200)
            expected = {'total_trip_budget': 1234.57, 'total_trip_spend': 2.68} if path == 'dashboard' else {
                'total_service_cost': 2.68, 'fuel_cost_total': 5.35, 'trip_cost_total': 2.68, 'trip_cost_per_km': .13}
            for field, value in expected.items(): self.assertEqual(result.json()['summary'][field], value, field)
        baseline = resolve_canonical_financial_baseline(self.owner)
        self.assertEqual(baseline['total_assets'], 2.68)

    def test_owned_orphan_snapshots_follow_reset_and_account_deletion(self):
        for user in (self.owner, self.other):
            row = self.rows['BikeProfile'] if user == self.owner else mobility_rows(live_apps, user)['BikeProfile']
            MobilityMoneySnapshot.objects.create(user=user, bike_profile=row, source_model='BikeProfile', original_source_id=row.pk,
                source_values={'estimated_market_value': '2.675'}, normalized_values={'estimated_market_value': '2.68'})
            row.delete()
        clear_user_fed_data(self.owner)
        self.assertEqual(MobilityMoneySnapshot.objects.get().user_id, self.other.pk)
        self.other.delete(); self.assertFalse(MobilityMoneySnapshot.objects.exists())

    def test_saved_decimal_plan_reopens_and_learns_numeric_preferences(self):
        from apps.mobility.models import TravelPreferenceProfile
        from apps.mobility.services.travel_conversation import new_session, save_plan
        plan = self.rows['TravelPlan']; plan.refresh_from_db()
        session = new_session(self.owner, plan)
        self.assertEqual(session.state['budget']['value'], 2.68)
        session.itinerary = {'days': [{'stay': 'Synthetic stay'}], 'budget': {'expected': 2.68}}
        session.save()
        saved = save_plan(session)
        self.assertEqual(saved.budget, Decimal('2.68'))
        profile = TravelPreferenceProfile.objects.get(user=self.owner)
        self.assertEqual(profile.preferences['typical_spend']['value'], 2.68)
        result = self.client.post('/api/mobility/planner/feedback/', json.dumps({'plan_id': plan.pk, 'rating': 'good'}), content_type='application/json')
        self.assertEqual(result.status_code, 200)
        profile.refresh_from_db(); self.assertEqual(profile.preferences['typical_spend']['value'], 2.68)


class MobilityMoneyMigrationTests(TransactionTestCase):
    def setUp(self):
        cache.clear(); self.enterContext(_offline_fixture_patches())
        executor = MigrationExecutor(connection); self.leaves = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))
        self.old_targets = [('mobility', '0012_travel_bus_mode') if item[0] == 'mobility' else item for item in self.leaves]
        executor.migrate(self.old_targets); self.old = executor.loader.project_state(self.old_targets).apps
        self.owner = self.old.get_model('users', 'User').objects.create(username='mobility-legacy-owner')
        self.rows = mobility_rows(self.old, self.owner)
        self.module = import_module('apps.mobility.migrations.0013_mobility_money_decimal')

    def upgrade(self):
        executor = MigrationExecutor(connection); executor.migrate(self.leaves)
        return executor.loader.project_state(self.leaves).apps

    def test_every_register_forward_reverse_preserves_originals_parents_and_null(self):
        before = {name: self.old.get_model('mobility', name).objects.values().get(pk=row.pk) for name, row in self.rows.items()}
        apps = self.upgrade(); Snapshot = apps.get_model('mobility', 'MobilityMoneySnapshot')
        self.assertEqual(Snapshot.objects.count(), 7)
        for name, original in before.items():
            row = apps.get_model('mobility', name).objects.get(pk=original['id'])
            snapshot = Snapshot.objects.get(source_model=name)
            self.assertIsNotNone(snapshot.applied_at)
            self.assertEqual(snapshot.original_parent_ids, self.module.parent_ids(row))
            for field in FIELDS[name]:
                self.assertEqual(snapshot.source_values[field], None if field == 'actual_cost' else '2.675')
                self.assertEqual(getattr(row, field), None if field == 'actual_cost' else Decimal('2.68'))
        MigrationExecutor(connection).migrate(self.old_targets)
        self.assertEqual(before, {name: self.old.get_model('mobility', name).objects.values().get(pk=row.pk) for name, row in self.rows.items()})

    def test_repeat_and_reverse_preserve_edits_new_records_and_deleted_rows(self):
        apps = self.upgrade(); Service = apps.get_model('mobility', 'BikeServiceRecord')
        Service.objects.filter(pk=self.rows['BikeServiceRecord'].pk).update(cost=50)
        fresh = Service.objects.create(user_id=self.owner.pk, bike_name='New', service_date=TODAY, cost=12)
        apps.get_model('mobility', 'TripLog').objects.filter(pk=self.rows['TripLog'].pk).delete()
        with connection.schema_editor() as editor:
            self.module.capture_legacy_money(apps, editor); self.module.apply_normalized_money(apps, editor)
        self.assertEqual(Service.objects.get(pk=self.rows['BikeServiceRecord'].pk).cost, Decimal('50'))
        MigrationExecutor(connection).migrate(self.old_targets)
        Old = self.old.get_model('mobility', 'BikeServiceRecord')
        self.assertEqual(Old.objects.get(pk=self.rows['BikeServiceRecord'].pk).cost, 50)
        self.assertEqual(Old.objects.get(pk=fresh.pk).cost, 12)
        self.assertFalse(self.old.get_model('mobility', 'TripLog').objects.exists())

    def test_changed_owner_parent_unapplied_and_null_zero_block_stale_restore(self):
        apps = self.upgrade(); Snapshot = apps.get_model('mobility', 'MobilityMoneySnapshot')
        other = apps.get_model('users', 'User').objects.create(username='changed-mobility-owner')
        apps.get_model('mobility', 'BikeProfile').objects.filter(pk=self.rows['BikeProfile'].pk).update(user_id=other.pk)
        apps.get_model('mobility', 'BikeServiceRecord').objects.filter(pk=self.rows['BikeServiceRecord'].pk).update(source_document_id=None)
        Snapshot.objects.filter(source_model='FuelRefillLog').update(applied_at=None)
        apps.get_model('mobility', 'BikeIssueReport').objects.filter(pk=self.rows['BikeIssueReport'].pk).update(actual_cost=0)
        MigrationExecutor(connection).migrate(self.old_targets)
        for name, field in (('BikeProfile', 'estimated_market_value'), ('BikeServiceRecord', 'cost'), ('FuelRefillLog', 'total_cost')):
            self.assertEqual(self.old.get_model('mobility', name).objects.get(pk=self.rows[name].pk).__dict__[field], 2.68)
        self.assertEqual(self.old.get_model('mobility', 'BikeIssueReport').objects.get().actual_cost, 0)
        self.old.get_model('mobility', 'BikeProfile').objects.filter(pk=self.rows['BikeProfile'].pk).update(user_id=self.owner.pk)

    def test_invalid_history_and_cross_owner_parent_abort_before_capture(self):
        Profile = self.old.get_model('mobility', 'BikeProfile')
        for amount in (float('inf'), -float('inf'), 1000000000000):
            Profile.objects.filter(pk=self.rows['BikeProfile'].pk).update(estimated_market_value=amount)
            with self.assertRaises(ValueError): self.upgrade()
            self.assertNotIn('mobility_mobilitymoneysnapshot', connection.introspection.table_names())
        Profile.objects.filter(pk=self.rows['BikeProfile'].pk).update(estimated_market_value=2.675)
        other = self.old.get_model('users', 'User').objects.create(username='foreign-parent-owner')
        Profile.objects.filter(pk=self.rows['BikeProfile'].pk).update(user_id=other.pk)
        with self.assertRaisesMessage(ValueError, 'parent ownership mismatch'): self.upgrade()
        self.assertNotIn('mobility_mobilitymoneysnapshot', connection.introspection.table_names())
        Profile.objects.filter(pk=self.rows['BikeProfile'].pk).update(user_id=self.owner.pk)

    def test_cent_history_canonical_baseline_has_zero_mismatches(self):
        for name, fields in FIELDS.items():
            self.old.get_model('mobility', name).objects.filter(pk=self.rows[name].pk).update(**{field: 12.34 for field in fields})
        before = resolve_canonical_financial_baseline(get_user_model().objects.get(pk=self.owner.pk))
        self.upgrade(); cache.clear()
        self.assertEqual(before, resolve_canonical_financial_baseline(get_user_model().objects.get(pk=self.owner.pk)))

    def test_disposable_alias_backup_restore_and_all_other_financial_rows(self):
        prior = {'users': '0002_user_ml_training_consent', 'career': '0004_alter_careerjobanalysis_options_and_more',
                 'mobility': '0012_travel_bus_mode'}
        baseline_targets = [(app, prior.get(app, name)) for app, name in self.leaves]
        with TemporaryDirectory(prefix='alfred-mobility-money-') as directory:
            root = Path(directory); source = root/'source.sqlite3'; candidate = root/'candidate.sqlite3'
            alias = 'mobility_money_rehearsal'
            db = connection.copy(alias=alias); db.settings_dict['NAME'] = str(source); connections[alias] = db
            try:
                executor = MigrationExecutor(db); executor.migrate(baseline_targets)
                state = executor.loader.project_state(baseline_targets).apps
                user = state.get_model('users', 'User').objects.using(alias).create(username='mobility-copy-owner',
                    monthly_income=10000.01, variable_income=200.02, rent_or_emi=1000.03)
                other = state.get_model('users', 'User').objects.using(alias).create(username='mobility-copy-other')
                mobility_rows(state, user, alias, amount=-1.005)
                state.get_model('career', 'CareerProfile').objects.using(alias).create(user_id=user.pk, role='Synthetic', skills='SQL', last_salary='123.45', experience_years=4.5)
                state.get_model('budgets', 'Budget').objects.using(alias).create(user_id=user.pk, month='2026-10', base_budget='123.45', inflation_adjusted='123.45')
                account = state.get_model('expenses', 'BankAccount').objects.using(alias).create(user_id=user.pk, account_number='SYNTHETIC', current_balance='123.45')
                for direction in ('debit', 'credit'):
                    state.get_model('expenses', 'Expense').objects.using(alias).create(user_id=user.pk, bank_account_id=account.pk,
                        amount='12.34', direction=direction, category='transfer', transaction_date=TODAY,
                        transaction_fingerprint='synthetic-mobility-'+direction, external_reference='SYNTHETIC')
                state.get_model('loans', 'Loan').objects.using(alias).create(user_id=user.pk, principal='200.01', emi='20.01',
                    interest_rate=5, tenure_months=10, remaining_balance='100.01', start_date=TODAY)
                state.get_model('investments', 'Investment').objects.using(alias).create(user_id=user.pk,
                    asset_name='Synthetic', invested_amount='12.34', current_value='15.67')
                state.get_model('family', 'FamilyAccountLink').objects.using(alias).create(created_by_id=user.pk, linked_user_id=other.pk,
                    invite_code_hash='synthetic-mobility-family', status='active', expires_at=timezone.now()+timedelta(days=1))
                db.close(); before, _ = read_database(source); source_hash = file_hash(source)
                copy_database(source, candidate); copy_database(source, root/'restored.sqlite3')
                self.assertEqual(read_database(source), read_database(root/'restored.sqlite3'))
                db.settings_dict['NAME'] = str(candidate)
                executor = MigrationExecutor(db)
                self.assertEqual(sorted((migration.app_label, migration.name, reverse) for migration, reverse in executor.migration_plan(self.leaves)),
                    [('career', '0005_career_salary_decimal', False), ('mobility', '0013_mobility_money_decimal', False), ('users', '0003_user_money_decimal', False), ('users', '0004_user_monthly_income_basis', False)])
                executor.migrate(self.leaves); db.close()
                after, _ = read_database(candidate)
                profile_fields = {'users_user': ('monthly_income', 'variable_income', 'rent_or_emi'),
                                  'career_careerprofile': ('last_salary',)}
                changed_tables = {'mobility_'+name.lower() for name in FIELDS} | profile_fields.keys()
                for table in before.keys()-changed_tables-{'django_migrations'}:
                    self.assertEqual(table_digest(before[table]), table_digest(after[table]), table)
                for table, fields in profile_fields.items():
                    current = {row['id']: row for row in after[table]}
                    self.assertEqual(set(current), {row['id'] for row in before[table]})
                    for original in before[table]:
                        updated = current[original['id']]
                        self.assertEqual(table_digest([{k:v for k,v in original.items() if k not in fields}]),
                                         table_digest([{k:v for k,v in updated.items() if k not in fields and k != 'monthly_income_basis'}]))
                        for field in fields:
                            self.assertEqual(Decimal(str(original[field])), Decimal(str(updated[field])))
                for name, fields in FIELDS.items():
                    old, new = before['mobility_'+name.lower()][0], after['mobility_'+name.lower()][0]
                    self.assertEqual({k:v for k,v in old.items() if k not in fields}, {k:v for k,v in new.items() if k not in fields})
                    for field in fields:
                        self.assertEqual(None if new[field] is None else Decimal(str(new[field])), None if field == 'actual_cost' else Decimal('-1.01'))
                executor = MigrationExecutor(db); executor.migrate(baseline_targets); db.close()
                reverse, _ = read_database(candidate)
                self.assertEqual({k:table_digest(v) for k,v in before.items()}, {k:table_digest(v) for k,v in reverse.items()})
                self.assertEqual(file_hash(source), source_hash)
            finally:
                db.close(); del connections[alias]
