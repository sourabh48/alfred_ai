from io import StringIO
import base64
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from apps.integrations.models import EmailConnection, _email_token_cipher
from apps.integrations.services.token_rotation import reencrypt_email_tokens


@override_settings(SECRET_KEY='synthetic-new-primary', SECRET_KEY_FALLBACKS=['synthetic-old-primary'])
class TokenRotationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='rotation-synthetic')
        with override_settings(SECRET_KEY='synthetic-old-primary', SECRET_KEY_FALLBACKS=[]):
            self.old = EmailConnection.objects.create(user=self.user, provider='GMAIL', email_address='old@example.invalid', access_token='synthetic-old-access', refresh_token='synthetic-old-refresh')
        self.current = EmailConnection.objects.create(user=self.user, provider='OUTLOOK', email_address='new@example.invalid', access_token='synthetic-new-access', refresh_token=None)
        self.legacy = EmailConnection.objects.create(user=self.user, provider='IMAP', email_address='legacy@example.invalid')
        EmailConnection.objects.filter(pk=self.legacy.pk).update(access_token='synthetic-legacy-token')

    def snapshot(self):
        return list(EmailConnection.objects.order_by('pk').values())

    def test_dry_run_reads_mixed_keys_without_mutation_or_secret_output(self):
        before = self.snapshot()
        output = StringIO()
        call_command('reencrypt_email_tokens', stdout=output)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('"fallback": 2', output.getvalue())
        self.assertIn('"legacy": 1', output.getvalue())
        for marker in ('synthetic-old-access', 'synthetic-old-refresh', 'synthetic-legacy-token', 'enc::', 'example.invalid'):
            self.assertNotIn(marker, output.getvalue())

    def test_apply_verifies_every_value_without_fallback_then_is_idempotent(self):
        report = reencrypt_email_tokens(apply=True)
        self.assertEqual(report['verified'], 4)
        self.assertEqual(report['fallback'], 2)
        with override_settings(SECRET_KEY_FALLBACKS=[]):
            self.old.refresh_from_db()
            self.assertEqual(self.old.get_access_token(), 'synthetic-old-access')
            self.assertEqual(self.old.get_refresh_token(), 'synthetic-old-refresh')
            self.legacy.refresh_from_db()
            self.assertEqual(self.legacy.get_access_token(), 'synthetic-legacy-token')
        after = self.snapshot()
        second = reencrypt_email_tokens(apply=True)
        self.assertEqual(second['fallback'], 0)
        self.assertEqual(second['legacy'], 0)
        self.assertEqual(self.snapshot(), after)

    def test_invalid_later_row_rolls_back_earlier_rotation(self):
        EmailConnection.objects.filter(pk=self.legacy.pk).update(refresh_token='enc::synthetic-corrupt-token')
        before = self.snapshot()
        output = StringIO()
        with self.assertRaises(CommandError) as failure:
            call_command('reencrypt_email_tokens', apply=True, stdout=output)
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn('synthetic-corrupt-token', str(failure.exception) + output.getvalue())

    def test_unreadable_dry_run_reports_count_and_requires_keys_retained(self):
        with override_settings(SECRET_KEY_FALLBACKS=[]), self.assertRaises(CommandError):
            call_command('reencrypt_email_tokens', stdout=StringIO())
        self.old.refresh_from_db()
        self.assertEqual(self.old.get_access_token(), 'synthetic-old-access')

    def test_reread_verification_failure_rolls_back(self):
        before = self.snapshot()
        with patch('apps.integrations.services.token_rotation.compare_digest', side_effect=[True, True, False]), self.assertRaises(CommandError):
            call_command('reencrypt_email_tokens', apply=True, stdout=StringIO())
        self.assertEqual(self.snapshot(), before)

    def test_rotated_token_preserves_issuance_timestamp(self):
        timestamp = base64.urlsafe_b64decode(self.old.access_token[5:].encode())[1:9]
        reencrypt_email_tokens(apply=True)
        self.old.refresh_from_db()
        self.assertEqual(base64.urlsafe_b64decode(self.old.access_token[5:].encode())[1:9], timestamp)

    def test_concurrent_update_conflict_preserves_originals(self):
        before = self.snapshot()
        with patch('django.db.models.query.QuerySet.update', return_value=0), self.assertRaises(CommandError):
            call_command('reencrypt_email_tokens', apply=True, stdout=StringIO())
        self.assertEqual(self.snapshot(), before)
