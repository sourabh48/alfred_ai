"""Synthetic review-before-write, stale/replay and source preservation acceptance."""
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import Client, TestCase, override_settings

from apps.expenses.models import BankAccount, Expense, StatementTransactionEvidence, StatementUpload
from apps.expenses.services.statement_lifecycle import apply_parsed_statement_upload, retry_statement_upload
from apps.expenses.services.statement_review import confirm_statement, statement_preview
from apps.expenses.services.statement_review import StatementReviewConflict
from apps.expenses.services.transaction_intelligence import build_transaction_fingerprint
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_expense_money_identity import parsed_fixture


class StatementReviewTests(TestCase):
    def test_null_retry_metadata_does_not_block_owner_corrections(self):
        from apps.expenses.services.statement_review import edit_statement_preview
        upload = self.stage()
        upload.extracted_payload['background_retry'] = None
        upload.save(update_fields=['extracted_payload'])
        edit_statement_preview(upload, revision=0, edits=[{'index': 0, 'amount': '12.34'}])
        upload.refresh_from_db()
        self.assertEqual(statement_preview(upload)['rows'][0]['amount'], '12.34')

    def test_edit_during_running_worker_is_preserved_and_retry_is_superseded(self):
        from apps.expenses.services.statement_review import edit_statement_preview
        from apps.expenses.tasks import retry_statement_upload_task
        upload = self.stage()
        def parsed_after_owner_edit(*args, **kwargs):
            current = StatementUpload.objects.get(pk=upload.pk)
            self.assertEqual(current.extracted_payload['background_retry']['state'], 'running')
            edit_statement_preview(current, revision=0, edits=[{'index': 0, 'amount': '12.34'}])
            return parsed_fixture()
        with patch('apps.expenses.services.statement_lifecycle.parse_bank_statement', side_effect=parsed_after_owner_edit):
            self.assertEqual(retry_statement_upload_task.run(upload.pk)['status'], 'superseded')
        upload.refresh_from_db()
        self.assertEqual(upload.extracted_payload['background_retry']['state'], 'superseded')
        self.assertEqual(statement_preview(upload)['rows'][0]['amount'], '12.34')
        self.assertFalse(Expense.objects.exists())

    def test_queueing_a_stale_instance_cannot_erase_a_newer_owner_edit(self):
        from apps.expenses.services.statement_lifecycle import queue_statement_retry
        from apps.expenses.services.statement_review import edit_statement_preview
        upload = self.stage()
        stale = StatementUpload.objects.get(pk=upload.pk)
        edit_statement_preview(upload, revision=0, edits=[{'index': 0, 'amount': '12.34'}])
        upload.refresh_from_db()
        before = deepcopy(upload.extracted_payload)
        with self.assertRaises(StatementReviewConflict):
            queue_statement_retry(stale)
        upload.refresh_from_db()
        self.assertEqual(upload.extracted_payload, before)

    def test_owner_edit_supersedes_queued_worker_and_does_not_starve_other_retries(self):
        from apps.expenses.services.statement_lifecycle import queue_statement_retry
        from apps.expenses.services.statement_review import edit_statement_preview
        from apps.expenses.tasks import retry_statement_upload_task, retry_low_confidence_statement_uploads
        upload = self.stage()
        upload.parser_status = 'needs_review'; upload.save(update_fields=['parser_status'])
        queue_statement_retry(upload)
        edit_statement_preview(upload, revision=0, edits=[{'index': 0, 'amount': '12.34'}])
        upload.refresh_from_db()
        self.assertEqual(upload.extracted_payload['background_retry']['state'], 'superseded')
        eligible = self.stage()
        eligible.parser_status = 'needs_review'; eligible.save(update_fields=['parser_status'])
        with patch('apps.expenses.services.statement_lifecycle.parse_bank_statement', return_value=parsed_fixture()) as parser:
            self.assertEqual(retry_statement_upload_task.run(upload.pk)['status'], 'superseded')
            batch = retry_low_confidence_statement_uploads.run()
            self.assertEqual(batch['processed'], 1)
            eligible.refresh_from_db()
            self.assertEqual(batch['results'][0]['imported_count'], 0)
            self.assertEqual(batch['results'][0]['parser_status'], eligible.parser_status)
        parser.assert_called_once()
        upload.refresh_from_db()
        self.assertEqual(statement_preview(upload)['rows'][0]['amount'], '12.34')
        self.assertFalse(Expense.objects.exists())

    def test_missing_or_changed_retained_source_cannot_confirm(self):
        for action in ('replace', 'delete', 'unverified'):
            with self.subTest(action=action):
                upload = self.stage()
                token = statement_preview(upload)['token']
                if action == 'replace': Path(upload.original_file.path).write_bytes(b'%PDF changed synthetic source')
                elif action == 'delete': Path(upload.original_file.path).unlink()
                else:
                    upload.extracted_payload.pop('source_sha256')
                    upload.save(update_fields=['extracted_payload'])
                self.assertFalse(statement_preview(upload)['can_confirm'])
                self.assertEqual(self.confirm(upload, token).status_code, 409)
                self.assertFalse(Expense.objects.exists())

    def test_document_center_retry_conflict_preserves_edited_statement(self):
        from copy import deepcopy
        from apps.expenses.services.statement_review import edit_statement_preview
        upload = self.stage()
        edit_statement_preview(upload, revision=0, edits=[{'index':0,'amount':'12.34'}])
        upload.refresh_from_db()
        before = deepcopy(upload.extracted_payload)
        response = self.client.post('/api/documents/review-queue/retry/',
            {'scope':'statement_document','id':upload.pk}, content_type='application/json')
        self.assertEqual(response.status_code, 409)
        upload.refresh_from_db()
        self.assertEqual(upload.extracted_payload, before)
        self.assertFalse(Expense.objects.exists())

    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-statement-review-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='synthetic-review-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-review-other')
        self.client.force_login(self.owner)

    def stage(self):
        return apply_parsed_statement_upload(user=self.owner, parsed=parsed_fixture(), statement_kind='bank_statement',
            statement_file=SimpleUploadedFile('synthetic.pdf', b'%PDF-1.4 synthetic retained source')).upload

    def confirm(self, upload, token=None):
        return self.client.post(f'/api/expenses/uploads/{upload.pk}/confirm/', {
            'token': token or statement_preview(upload)['token'], 'confirm': True}, content_type='application/json')

    def test_preview_and_source_persist_without_canonical_writes_then_confirmation_is_idempotent(self):
        upload = self.stage()
        self.assertEqual((BankAccount.objects.count(), Expense.objects.count()), (0, 0))
        self.assertTrue(Path(upload.original_file.path).exists())
        preview = statement_preview(upload)
        self.assertTrue(preview['can_confirm'])
        response = self.confirm(upload, preview['token'])
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['imported_count'], len(parsed_fixture().transactions))
        before = list(Expense.objects.values())
        again = self.confirm(upload, preview['token'])
        self.assertEqual(again.status_code, 200)
        self.assertTrue(again.json()['replayed'])
        self.assertEqual(list(Expense.objects.values()), before)
        upload.refresh_from_db()
        self.assertTrue(Path(upload.original_file.path).exists())
        self.assertEqual(upload.extracted_payload['import_review']['state'], 'confirmed')

    def test_corrections_preserve_original_and_invalidate_old_review(self):
        upload = self.stage()
        preview = statement_preview(upload)
        original = preview['rows'][0]['original']['amount']
        response = self.client.patch(f'/api/expenses/uploads/{upload.pk}/preview/', {
            'revision': 0, 'edits': [{'index': 0, 'amount': '123.45'}]}, content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['rows'][0]['original']['amount'], original)
        self.assertEqual(self.confirm(upload, preview['token']).status_code, 409)
        upload.refresh_from_db()
        self.assertEqual(self.confirm(upload).status_code, 200)
        self.assertEqual(Expense.objects.order_by('pk').first().amount, Decimal('123.45'))

    def test_owner_csrf_expiry_and_current_account_binding(self):
        upload = self.stage()
        token = statement_preview(upload)['token']
        outsider = Client(); outsider.force_login(self.other)
        self.assertEqual(outsider.get(f'/api/expenses/uploads/{upload.pk}/preview/').status_code, 404)
        self.assertEqual(outsider.post(f'/api/expenses/uploads/{upload.pk}/confirm/', {'token': token, 'confirm': True}, content_type='application/json').status_code, 404)
        guarded = Client(enforce_csrf_checks=True); guarded.force_login(self.owner)
        self.assertEqual(guarded.post(f'/api/expenses/uploads/{upload.pk}/confirm/', {'token': token, 'confirm': True}, content_type='application/json').status_code, 403)
        BankAccount.objects.create(user=self.owner, account_number=parsed_fixture().account_number, current_balance='999.00')
        self.assertEqual(self.confirm(upload, token).status_code, 409)
        self.assertEqual(Expense.objects.count(), 0)
        with patch('django.core.signing.time.time', return_value=0):
            expired_token = statement_preview(upload)['token']
        self.assertEqual(self.confirm(upload, expired_token).status_code, 409)

    def test_provenance_failure_rolls_back_account_rows_and_confirmation_claim(self):
        upload = self.stage()
        token = statement_preview(upload)['token']
        with patch('apps.expenses.services.statement_evidence.StatementTransactionEvidence.objects.bulk_create',
                   side_effect=OperationalError('Synthetic receipt failure')):
            self.assertEqual(self.confirm(upload, token).status_code, 409)
        self.assertFalse(Expense.objects.exists())
        self.assertFalse(BankAccount.objects.exists())
        upload.refresh_from_db()
        self.assertEqual(upload.extracted_payload['import_review']['state'], 'pending')
        self.assertEqual(self.confirm(upload, token).status_code, 200)

    def test_retry_only_replaces_preview_and_never_posts(self):
        upload = self.stage()
        old_id = upload.extracted_payload['import_review']['id']
        with patch('apps.expenses.services.statement_lifecycle.parse_bank_statement', return_value=parsed_fixture()):
            result = retry_statement_upload(upload)
        self.assertEqual(result.new_import_count, 0)
        self.assertNotEqual(result.upload.extracted_payload['import_review']['id'], old_id)
        self.assertFalse(BankAccount.objects.exists())
        self.assertFalse(Expense.objects.exists())

    def test_duplicate_reimport_is_reported_and_retains_both_sources(self):
        first = self.stage(); self.assertEqual(self.confirm(first).status_code, 200)
        second = self.stage()
        preview = statement_preview(second)
        self.assertEqual(preview['duplicate_count'], preview['row_count'])
        before = Expense.objects.count()
        response = self.confirm(second)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['imported_count'], 0)
        self.assertEqual(Expense.objects.count(), before)
        self.assertEqual(StatementUpload.objects.count(), 2)
        for source in (first, second): self.assertTrue(Path(source.original_file.path).exists())

    def test_confirmation_preserves_legacy_identity_and_canonical_cent_rounding(self):
        upload = self.stage()
        self.assertEqual(self.confirm(upload).status_code, 200)
        row = Expense.objects.get(statement_upload=upload)
        original = parsed_fixture().transactions[0]
        expected = build_transaction_fingerprint(bank_account=row.bank_account, **{
            field: getattr(original, field) for field in ('transaction_date', 'amount', 'direction',
                'external_reference', 'raw_description', 'closing_balance')})
        self.assertEqual(row.transaction_fingerprint, expected)
        self.assertEqual(row.amount, Decimal('2.68'))
        self.assertEqual(row.bank_account.current_balance, Decimal('10.01'))

    def test_retry_cannot_overwrite_confirmation_during_parsing(self):
        upload = self.stage()
        def finish_parsing(*args, **kwargs):
            self.assertEqual(self.confirm(upload).status_code, 200)
            return parsed_fixture()
        with patch('apps.expenses.services.statement_lifecycle.parse_bank_statement', side_effect=finish_parsing):
            with self.assertRaises(StatementReviewConflict):
                retry_statement_upload(upload)
        upload.refresh_from_db()
        self.assertEqual(upload.extracted_payload['import_review']['state'], 'confirmed')
        self.assertEqual(Expense.objects.filter(statement_upload=upload).count(), 1)

    def test_invalid_corrections_and_edited_preview_retry_preserve_draft(self):
        upload = self.stage()
        for value in ('NaN', 'Infinity', '-1', '1e40'):
            response = self.client.patch(f'/api/expenses/uploads/{upload.pk}/preview/', {
                'revision': 0, 'edits': [{'index': 0, 'amount': value}]}, content_type='application/json')
            self.assertEqual(response.status_code, 400)
        response = self.client.patch(f'/api/expenses/uploads/{upload.pk}/preview/', {
            'revision': 0, 'edits': [{'index': 0, 'amount': '12.34'}]}, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        upload.refresh_from_db()
        with self.assertRaises(StatementReviewConflict): retry_statement_upload(upload)
        self.assertEqual(statement_preview(upload)['rows'][0]['amount'], '12.34')
        self.assertFalse(Expense.objects.exists())
