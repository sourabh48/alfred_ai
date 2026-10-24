"""Travel telemetry expires independently of quota, owned evidence and financial data."""
from contextlib import closing
from datetime import datetime, timedelta, timezone as utc
from decimal import Decimal
from io import StringIO
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.test import TestCase, override_settings

from alfred_private_storage import private_directory
from apps.expenses.models import Expense
from apps.mobility.models import TravelPlan, TravelProviderRequest, TravelProviderState
from apps.mobility.services.travel.cache import cleanup_request_history, query
from tests.test_travel_providers import FakeProvider
from scripts.release_promotion import canonical_snapshot
from scripts.release_recovery import database_snapshot


@override_settings(TRAVEL_PROVIDER_REQUEST_RETENTION_DAYS=7,
                   TRAVEL_PROVIDER_NETWORK_RETENTION_DAYS=90,
                   TRAVEL_PROVIDER_CLEANUP_BATCH_SIZE=1000)
class TravelRetentionTests(TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 12, tzinfo=utc.utc)
        timer = patch('apps.mobility.services.travel.cache.timezone.now', return_value=self.now)
        timer.start()
        self.addCleanup(timer.stop)

    def event(self, *, days=100, network=False, provider='fixture', status='ok', at=None):
        row = TravelProviderRequest.objects.create(provider=provider, category='weather',
            cache_key='synthetic', parameters={'place': 'Synthetic public place'},
            status=status, network_call=network)
        TravelProviderRequest.objects.filter(pk=row.pk).update(created_at=at or self.now-timedelta(days=days))
        return row

    def test_expired_attempts_prune_but_active_and_current_work_survive(self):
        expired = self.event()
        abandoned = self.event(network=True, status='in_progress')
        recent = self.event(days=0, network=True, status='in_progress')
        active = self.event(provider='active', network=True, status='in_progress')
        self.event(provider='active', network=True, status='ok')
        TravelProviderState.objects.create(provider='active', lease_until=self.now+timedelta(minutes=1))
        result = cleanup_request_history(apply=True)
        self.assertEqual((result['deleted'], result['retained_active']), (3, 1))
        self.assertFalse(TravelProviderRequest.objects.filter(pk__in=[expired.pk, abandoned.pk]).exists())
        self.assertSetEqual(set(TravelProviderRequest.objects.values_list('pk', flat=True)), {recent.pk, active.pk})
        TravelProviderState.objects.filter(provider='active').update(lease_until=self.now-timedelta(seconds=1))
        self.assertEqual(cleanup_request_history(apply=True)['deleted'], 1)

    @override_settings(TRAVEL_PROVIDER_NETWORK_RETENTION_DAYS=1)
    def test_cleanup_cannot_replenish_current_month_provider_quota(self):
        for _ in range(2):
            self.event(days=10, network=True)
        self.event(days=40, network=True)
        self.assertEqual(cleanup_request_history(apply=True)['deleted'], 1)
        provider = FakeProvider()
        provider.limits = {'month': 2}
        provider.fetch = Mock(side_effect=AssertionError('No network allowed'))
        self.assertEqual(query(provider, {}, force=True).error, 'local_quota_exhausted')
        provider.fetch.assert_not_called()
        self.assertEqual(TravelProviderRequest.objects.filter(network_call=True).count(), 2)

    @override_settings(TRAVEL_PROVIDER_NETWORK_RETENTION_DAYS=1)
    def test_month_rollover_preserves_previous_hour_and_exact_cutoff(self):
        now = datetime(2027, 1, 1, 0, 20, tzinfo=utc.utc)
        with patch('apps.mobility.services.travel.cache.timezone.now', return_value=now):
            hour = self.event(network=True, at=now-timedelta(minutes=30))
            boundary = self.event(network=True, at=now-timedelta(days=1))
            self.event(network=True, at=now-timedelta(days=1, seconds=1))
            self.assertEqual(cleanup_request_history(apply=True)['deleted'], 1)
            self.assertSetEqual(set(TravelProviderRequest.objects.values_list('pk', flat=True)), {hour.pk, boundary.pk})

    @override_settings(TRAVEL_PROVIDER_CLEANUP_BATCH_SIZE=2)
    def test_dry_run_bounded_order_restart_and_idempotence(self):
        rows = [self.event() for _ in range(3)]
        preview = cleanup_request_history()
        self.assertEqual((preview['eligible'], preview['selected'], preview['deleted']), (3, 2, 0))
        result = cleanup_request_history(apply=True)
        self.assertEqual((result['deleted'], result['remaining']), (2, 1))
        self.assertEqual(list(TravelProviderRequest.objects.values_list('pk', flat=True)), [rows[-1].pk])
        self.assertEqual(cleanup_request_history(apply=True)['deleted'], 1)
        self.assertEqual(cleanup_request_history(apply=True)['deleted'], 0)

    def test_invalid_configuration_never_deletes(self):
        self.event()
        for name, value in (('TRAVEL_PROVIDER_REQUEST_RETENTION_DAYS', 0),
                            ('TRAVEL_PROVIDER_NETWORK_RETENTION_DAYS', -1),
                            ('TRAVEL_PROVIDER_CLEANUP_BATCH_SIZE', True),
                            ('TRAVEL_PROVIDER_CLEANUP_BATCH_SIZE', 10001)):
            with self.subTest(setting=name), override_settings(**{name: value}):
                with self.assertRaises(ImproperlyConfigured):
                    cleanup_request_history(apply=True)
            self.assertEqual(TravelProviderRequest.objects.count(), 1)

    def test_owners_expenses_plans_and_provider_state_are_not_cleanup_targets(self):
        owners = [get_user_model().objects.create_user(username=name) for name in ('retention-owner', 'retention-other')]
        for owner in owners:
            Expense.objects.create(user=owner, amount=Decimal('123.45'), description='Synthetic retained record')
            TravelPlan.objects.create(user=owner, title='Synthetic retained plan')
        state = TravelProviderState.objects.create(provider='idle', quota_remaining=123)
        before = list(Expense.objects.values()), list(TravelPlan.objects.values()), list(get_user_model().objects.values())
        self.event()
        cleanup_request_history(apply=True)
        self.assertEqual(before, (list(Expense.objects.values()), list(TravelPlan.objects.values()), list(get_user_model().objects.values())))
        state.refresh_from_db()
        self.assertEqual(state.quota_remaining, 123)

    def test_command_is_dry_by_default_and_only_reports_safe_counts(self):
        self.event()
        output = StringIO()
        call_command('cleanup_travel_requests', stdout=output)
        self.assertTrue(json.loads(output.getvalue())['dry_run'])
        self.assertEqual(TravelProviderRequest.objects.count(), 1)
        output = StringIO()
        call_command('cleanup_travel_requests', apply=True, stdout=output)
        self.assertEqual(json.loads(output.getvalue())['deleted'], 1)
        self.assertNotIn('Synthetic public place', output.getvalue())
        self.assertNotIn('fixture', output.getvalue())

    def test_source_and_native_schedulers_use_the_same_bounded_cleanup(self):
        from apps.mobility.tasks import cleanup_travel_request_history
        from alfred_ai.native_tasks import native_travel_request_cleanup
        schedule = settings.CELERY_BEAT_SCHEDULE['travel-request-cleanup']
        self.assertEqual(schedule['task'], 'apps.mobility.tasks.cleanup_travel_request_history')
        self.assertEqual(schedule['schedule'], timedelta(minutes=15))
        self.event()
        self.assertEqual(cleanup_travel_request_history()['deleted'], 1)
        with patch('alfred_ai.native_tasks.cleanup_travel_request_history', return_value={'deleted': 0}) as cleanup:
            self.assertEqual(native_travel_request_cleanup.call_local(), {'deleted': 0})
        cleanup.assert_called_once_with()

    def test_reconciliation_excludes_only_request_telemetry_and_backup_keeps_it(self):
        with TemporaryDirectory() as directory:
            root = private_directory(Path(directory))
            path = root / 'synthetic.sqlite3'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE mobility_travelplan (id INTEGER, owner_id INTEGER, amount TEXT)')
                db.execute("INSERT INTO mobility_travelplan VALUES (1,1,'123.45')")
                db.execute('CREATE TABLE mobility_travelproviderrequest (id INTEGER)')
                db.execute('INSERT INTO mobility_travelproviderrequest VALUES (1)')
            before, complete = canonical_snapshot(path), database_snapshot(path)
            self.assertIn('mobility_travelproviderrequest', complete)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('DELETE FROM mobility_travelproviderrequest')
            self.assertEqual(before, canonical_snapshot(path))
            self.assertNotEqual(complete, database_snapshot(path))
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE mobility_travelplan SET amount='123.46'")
            self.assertNotEqual(before, canonical_snapshot(path))
