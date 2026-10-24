"""Synthetic source provenance and owner confirmation, never private bank fixtures."""
from datetime import date, timedelta
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from apps.expenses.models import Expense, BankAccount, StatementUpload, StatementTransactionEvidence
from apps.expenses.services.statement_evidence import evidence
from apps.expenses.services.statement_lifecycle import _import_statement_transactions, retry_statement_upload
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_expense_money_identity import parsed_fixture


class StatementEvidenceTests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-statement-evidence-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits'),
            ALFRED_MEMORY_DIR=str(root/'unused-vault'), ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
            ALFRED_MEMORY_OPENAI_AUTHORIZED=False, ALFRED_MEMORY_CLOUD_AUTHORIZED=False))
        self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='source-owner')
        self.other = get_user_model().objects.create_user(username='source-other')
        self.account = BankAccount.objects.create(user=self.owner, account_number='TEST0001', current_balance='10.01')
        self.upload = StatementUpload.objects.create(user=self.owner, bank_account=self.account,
            account_number='TEST0001', source='bank_statement', parser_status='parsed',
            original_file=SimpleUploadedFile('synthetic-bank.pdf', b'%PDF-synthetic-evidence-only'),
            file_name='synthetic-bank.pdf', statement_start=date(2026,9,1), statement_end=date(2026,9,30),
            extracted_payload={'raw_text_excerpt':'SYNTHETIC-NO-EXTERNAL-RAW-CONTENT'})
        self.import_rows()
        self.row = Expense.objects.get(statement_upload=self.upload)
        self.client.force_login(self.owner)

    def import_rows(self, parsed=None, **changes):
        return _import_statement_transactions(user=self.owner, upload=self.upload, bank_account=self.account,
            parsed=parsed or parsed_fixture(), **changes)

    def endpoint(self, row=None):
        return f'/api/ai/statement-evidence/{(row or self.row).pk}/'

    def confirm(self, *, revision=None, confirm=True, method='post', **extra):
        return getattr(self.client, method)(self.endpoint(), json.dumps(dict(
            revision=revision or evidence(self.owner,self.row.pk)['revision'], confirm=confirm, **extra)), content_type='application/json')

    def test_import_snapshot_and_duplicate_retry_preserve_original_source_and_fingerprints(self):
        proof = self.row.statement_evidence
        self.assertEqual(proof.source_values['amount'], '2.68')
        self.assertEqual(proof.source_values['parser_identity']['amount'], '2.675')
        self.assertEqual(proof.statement_upload_id, self.upload.pk)
        before = list(Expense.objects.values())
        source = proof.source_values.copy()
        self.assertEqual(self.import_rows()[1], 1)
        self.assertEqual(list(Expense.objects.values()), before)
        self.assertEqual(StatementTransactionEvidence.objects.count(), 1)
        self.assertEqual(StatementTransactionEvidence.objects.get().source_values, source)
        duplicate = StatementUpload.objects.create(user=self.owner, bank_account=self.account, file_name='duplicate.pdf')
        _import_statement_transactions(user=self.owner, upload=duplicate, bank_account=self.account, parsed=parsed_fixture())
        self.row.refresh_from_db()
        self.assertEqual(self.row.statement_upload_id, self.upload.pk)
        self.assertEqual(StatementTransactionEvidence.objects.count(), 1)

    def test_explicit_confirmation_and_revocation_are_owner_metadata_only(self):
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        baseline=resolve_canonical_financial_baseline(self.owner)['decimal_amounts']
        before = [list(model.objects.values()) for model in (Expense, BankAccount, StatementUpload, get_user_model())]
        first = self.client.get(self.endpoint())
        self.assertEqual(first.json()['verification'], 'needs_owner_review')
        self.assertIn('no-store', first['Cache-Control'])
        self.assertEqual(self.confirm(confirm=False).status_code, 400)
        response = self.confirm(); self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['verification'], 'owner_confirmed')
        self.assertNotIn('SYNTHETIC-NO-EXTERNAL-RAW-CONTENT', response.content.decode())
        self.assertEqual(self.confirm(method='delete').json()['verification'], 'needs_owner_review')
        self.assertEqual([list(model.objects.values()) for model in (Expense, BankAccount, StatementUpload, get_user_model())], before)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner)['decimal_amounts'],baseline)
        self.assertFalse(Path(settings.ALFRED_MEMORY_DIR).exists())

    def test_current_owner_correction_wins_and_original_snapshot_never_changes(self):
        self.confirm(); original = self.row.statement_evidence.source_values.copy()
        response = self.client.patch(f'/api/expenses/{self.row.pk}/', json.dumps({'amount':'7.77'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        current = evidence(self.owner, self.row.pk)
        self.assertEqual(current['current']['amount'], '7.77')
        self.assertEqual(current['original']['amount'], '2.68')
        self.assertEqual(current['verification'], 'needs_owner_review')
        self.assertEqual(self.confirm().json()['verification'], 'owner_confirmed')
        self.assertEqual(StatementTransactionEvidence.objects.get(expense=self.row).source_values, original)

    def test_metadata_correction_and_file_changes_invalidate_confirmation(self):
        self.confirm(); revision = evidence(self.owner,self.row.pk)['revision']
        self.upload.statement_end = date(2026,10,1); self.upload.save(update_fields=['statement_end'])
        self.assertEqual(self.confirm(revision=revision).status_code, 409)
        self.assertEqual(evidence(self.owner,self.row.pk)['verification'], 'needs_owner_review')
        self.confirm()
        Path(self.upload.original_file.path).write_bytes(b'%PDF-replaced-synthetic-source')
        self.assertEqual(evidence(self.owner,self.row.pk)['verification'], 'needs_owner_review')
        self.confirm()
        Path(self.upload.original_file.path).unlink()
        current = evidence(self.owner,self.row.pk)
        self.assertEqual(current['verification'], 'source_unavailable')
        self.assertIsNone(current['source_download_url']); self.assertEqual(self.confirm().status_code,409)

    def test_foreign_ids_family_consent_and_unauthorized_citations_never_disclose(self):
        from apps.family.models import FamilyAccountLink
        FamilyAccountLink.objects.create(created_by=self.owner, linked_user=self.other, invite_code_hash='b'*64,
            status='accepted', share_financial_summary=True, linked_user_share_financial_summary=True,
            expires_at=timezone.now()+timedelta(days=1))
        item = evidence(self.owner,self.row.pk)
        self.assertEqual(self.client.get(item['citation_url']).status_code,200)
        download = self.client.get(item['source_download_url']); self.assertEqual(download.status_code,200); download.close()
        for actor in (None, self.other):
            client = Client()
            if actor: client.force_login(actor)
            for url in (self.endpoint(), item['citation_url'], item['source_download_url']):
                response = client.get(url)
                self.assertIn(response.status_code,(302,401,403,404))
                self.assertNotIn(self.upload.file_name,response.content.decode())
            response=client.post(self.endpoint(),json.dumps({'revision':item['revision'],'confirm':True}),content_type='application/json')
            self.assertIn(response.status_code,(401,403,404))
        self.client.force_login(self.other)
        self.assertEqual(self.client.get('/api/ai/statement-evidence/').json()['records'], [])

    def test_csrf_unknown_fields_and_wrong_statement_pair_are_rejected(self):
        guarded=Client(enforce_csrf_checks=True); guarded.force_login(self.owner)
        self.assertEqual(guarded.post(self.endpoint(),{'confirm':True}).status_code,403)
        self.assertEqual(self.confirm(owner=self.other.pk).status_code,400)
        self.assertEqual(self.client.get(f'/documents/statements/{self.upload.pk+1}/transactions/{self.row.pk}/').status_code,404)
        self.client.logout(); self.client.cookies['sessionid']='invalid-synthetic-session'
        self.assertIn(self.client.get(self.endpoint()).status_code,(401,403))

    def test_partial_unverified_conflicting_and_missing_source_states(self):
        for change, expected in (({'parser_status':'needs_review'},'document_needs_review'),
                ({'statement_start':date(2026,10,1)},'conflicting_source'),
                ({'account_number':'OTHER0001'},'conflicting_source'),
                ({'extracted_payload':{'preview_only':True}},'document_needs_review')):
            before={key:getattr(self.upload,key) for key in change}
            for key,value in change.items(): setattr(self.upload,key,value)
            self.upload.save(update_fields=list(change))
            self.assertEqual(evidence(self.owner,self.row.pk)['verification'],expected)
            self.assertEqual(self.confirm().status_code,409)
            for key,value in before.items(): setattr(self.upload,key,value)
            self.upload.save(update_fields=list(change))
        duplicate=Expense.objects.create(user=self.owner,bank_account=self.account,statement_upload=self.upload,
            source='bank_statement',amount='9.00',transaction_date=self.row.transaction_date,
            direction=self.row.direction,external_reference=self.row.external_reference,raw_description=self.row.raw_description)
        self.assertEqual(evidence(self.owner,self.row.pk)['verification'],'conflicting_records')
        duplicate.delete()
        self.upload.original_file=''; self.upload.save(update_fields=['original_file'])
        self.assertEqual(evidence(self.owner,self.row.pk)['verification'],'source_removed')

    def test_legacy_records_do_not_acquire_invented_original_extraction(self):
        StatementTransactionEvidence.objects.all().delete()
        first=evidence(self.owner,self.row.pk)
        self.assertEqual(first['original_status'],'not_retained'); self.assertIsNone(first['original'])
        confirmed=self.confirm().json()
        self.assertEqual(confirmed['verification'],'owner_confirmed')
        self.assertIsNone(confirmed['original'])
        self.assertEqual(confirmed['current']['amount'],'2.68')

    def test_deleted_and_reparented_evidence_is_inaccessible(self):
        other_account=BankAccount.objects.create(user=self.other,account_number='FOREIGN')
        self.upload.bank_account=other_account; self.upload.save(update_fields=['bank_account'])
        self.assertEqual(self.client.get(self.endpoint()).status_code,404)
        self.upload.bank_account=self.account; self.upload.save(update_fields=['bank_account'])
        self.row.delete()
        self.assertEqual(self.client.get(self.endpoint()).status_code,404)
        self.assertEqual(StatementTransactionEvidence.objects.count(),0)

    def test_transfer_legs_remain_separate_and_no_spend_or_balance_changes(self):
        from apps.expenses.services.cashflow_treatment import rounded_cashflow_bucket, summarize_cashflow
        self.row.delete()
        second=BankAccount.objects.create(user=self.owner,account_number='TEST0002',current_balance='50.00')
        upload=StatementUpload.objects.create(user=self.owner,bank_account=second,source='bank_statement',file_name='credit.pdf',parser_status='parsed')
        self.import_rows(parsed_fixture(amount=50,closing=950,category='transfer'))
        _import_statement_transactions(user=self.owner,upload=upload,bank_account=second,
            parsed=parsed_fixture(amount=50,closing=50,direction='credit',category='transfer',account='TEST0002'))
        rows=list(Expense.objects.filter(user=self.owner)); before=list(Expense.objects.values())
        self.assertEqual(StatementTransactionEvidence.objects.count(),2)
        for row in rows: evidence(self.owner,row.pk)
        totals=rounded_cashflow_bucket(summarize_cashflow(rows))
        self.assertEqual((totals['expense_total'],totals['transfer_out_total'],totals['transfer_in_total']),(0,50,50))
        self.assertEqual(list(Expense.objects.values()),before)

    def test_source_paths_and_unsafe_filenames_are_not_disclosed(self):
        self.upload.file_name='C:\\private\\financial\\<img src=x onerror="window.leak=true">.pdf'
        self.upload.save(update_fields=['file_name'])
        result=evidence(self.owner,self.row.pk)
        self.assertNotIn('C:',result['statement']['document_name'])
        page=self.client.get(result['citation_url'])
        self.assertNotIn('<img src=x',page.content.decode())
        self.upload.original_file='../outside-private.pdf'; self.upload.save(update_fields=['original_file'])
        self.assertIsNone(evidence(self.owner,self.row.pk)['source_download_url'])

    def test_saved_statement_date_corrections_survive_retry(self):
        self.upload.extracted_payload.update(accepted_corrections={'statement_start':'2026-08-31','statement_end':'2026-10-01'})
        self.upload.save(update_fields=['extracted_payload'])
        original=self.row.statement_evidence.source_values.copy()
        with patch('apps.expenses.services.statement_lifecycle.parse_bank_statement',return_value=parsed_fixture()):
            retry_statement_upload(self.upload)
        self.upload.refresh_from_db()
        self.assertEqual((self.upload.statement_start,self.upload.statement_end),(date(2026,8,31),date(2026,10,1)))
        self.assertEqual(Expense.objects.count(),1)
        self.assertEqual(StatementTransactionEvidence.objects.get().source_values,original)

    def test_withdrawal_invalidates_old_confirmation_even_when_values_match_again(self):
        old=evidence(self.owner,self.row.pk)['revision']
        with patch('django.utils.timezone.now',return_value=timezone.now()):
            self.confirm(); self.confirm(method='delete')
        self.assertEqual(self.confirm(revision=old).status_code,409)
        self.assertEqual(evidence(self.owner,self.row.pk)['verification'],'needs_owner_review')

    def test_provenance_failure_rolls_back_the_complete_import(self):
        from apps.expenses.services.statement_lifecycle import apply_parsed_statement_upload
        from django.db.utils import OperationalError
        before=[list(model.objects.values()) for model in (Expense,BankAccount,StatementUpload,StatementTransactionEvidence)]
        with patch('apps.expenses.services.statement_evidence.StatementTransactionEvidence.objects.bulk_create',side_effect=OperationalError('Synthetic receipt failure')):
            with self.assertRaises(OperationalError):
                apply_parsed_statement_upload(user=self.owner,parsed=parsed_fixture(reference='NEW-REFERENCE'),statement_kind='bank_statement')
        self.assertEqual([list(model.objects.values()) for model in (Expense,BankAccount,StatementUpload,StatementTransactionEvidence)],before)
