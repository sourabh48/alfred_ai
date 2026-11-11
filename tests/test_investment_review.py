"""Isolated owner-reviewed investment imports, using canonical Decimal posting."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError, connections
from django.test import Client, TestCase, TransactionTestCase, override_settings

from apps.investments.models import Investment, InvestmentImportDocument
from apps.investments.services.import_review import (
    stage_investment_document, investment_preview, edit_investment_review, confirm_investment_review, InvestmentReviewConflict)
from alfred_ai.services.document_review import _retry_investment_document, apply_correction, delete_document
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_investment_import_acceptance import portfolio_pdf


def extraction(**changes):
    row = dict(asset_name='Synthetic Fund', asset_type='mutual_fund', institution='Synthetic Broker',
        account_number='SYNTHETIC-01', invested_amount='10000.015', current_value='11000.005',
        monthly_sip='100.005', annual_return_rate='0', currency='INR')
    row.update(changes)
    return dict(broker='Synthetic Broker', confidence=.8, investments=[row], extracted_text='Synthetic source')


class InvestmentReviewTests(TestCase):
    def test_review_serializer_keeps_layout_status_without_raw_extracted_payload(self):
        from apps.investments.serializers import InvestmentImportDocumentSerializer
        layout = {'status':'needs_review','reason':'Check uncertain amounts','raw':'SYNTHETIC-PRIVATE-SOURCE'}
        document = self.stage({**extraction(), 'payload':{'layout_review':layout}})
        self.assertEqual(document.extracted_payload['layout_review'], layout)
        payload = InvestmentImportDocumentSerializer(document).data['extracted_payload']
        self.assertEqual(payload, {'review_state':'pending','layout_review':{
            'status':'needs_review','reason':'Check uncertain amounts'}})

    def test_saving_other_fields_preserves_estimates_until_explicit_field_review(self):
        document = self.stage()
        document.extracted_payload['import_review']['candidate'][0]['field_status']['invested_amount'] = 'estimated'
        document.save(update_fields=['extracted_payload'])
        url = f'/investments/import-uploads/{document.pk}/review/'
        row = self.client.get(url).context['preview']['rows'][0]
        data = {f"row-0-{field['name']}": field['value'] for field in row['form_fields']}
        data.update(action='save', revision=0, page=1, **{'row-0-action':'create','row-0-currency':'USD'})
        self.assertEqual(self.client.post(url, data).status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.extracted_payload['import_review']['candidate'][0]['field_status']['invested_amount'], 'estimated')
        self.assertFalse(investment_preview(document)['can_confirm'])
        data.update(revision=1, **{'row-0-reviewed-invested_amount':'yes'})
        self.assertEqual(self.client.post(url, data).status_code, 302)
        document.refresh_from_db()
        self.assertEqual(document.extracted_payload['import_review']['candidate'][0]['field_status']['invested_amount'], 'owner_entered')
        self.assertTrue(investment_preview(document)['can_confirm'])
        self.assertFalse(Investment.objects.exists())

    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-investment-review-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        self.owner = get_user_model().objects.create_user(username='synthetic-investment-review-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-investment-review-other')
        self.client.force_login(self.owner)

    def stage(self, parsed=None):
        return stage_investment_document(user=self.owner, parsed=parsed or extraction(),
            upload_file=SimpleUploadedFile('synthetic-investment.pdf', b'%PDF-1.4 synthetic retained source'))

    def confirm(self, document, token=None):
        return self.client.post(f'/api/investments/import-uploads/{document.pk}/confirm/',
            dict(confirm=True, token=token or investment_preview(document)['token']), content_type='application/json')

    def test_preview_decimal_confirmation_replay_and_source_retention(self):
        document = self.stage(); self.assertFalse(Investment.objects.exists())
        token = investment_preview(document)['token']
        self.assertEqual(self.confirm(document, token).status_code, 200)
        row = Investment.objects.get()
        self.assertEqual((row.invested_amount, row.current_value, row.monthly_sip),
            (Decimal('10000.02'), Decimal('11000.01'), Decimal('100.01')))
        before = list(Investment.objects.values())
        self.assertTrue(self.confirm(document, token).json()['replayed'])
        self.assertEqual(list(Investment.objects.values()), before)
        self.assertTrue(Path(document.uploaded_file.path).is_file())

    def test_existing_identity_conflicts_link_without_any_canonical_change(self):
        data = extraction()['investments'][0]
        existing = Investment.objects.create(user=self.owner, **{**data, 'current_value': '500'})
        before = list(Investment.objects.values())
        document = self.stage()
        self.assertEqual(investment_preview(document)['rows'][0]['action'], 'link')
        self.assertIn('current_value', investment_preview(document)['rows'][0]['conflicts'])
        self.assertEqual(self.confirm(document).status_code, 200)
        self.assertEqual(list(Investment.objects.values()), before)
        self.assertEqual(document.linked_investments.get(), existing)

    def test_missing_estimated_unsupported_and_nonfinite_values_cannot_post(self):
        for changes in (dict(currency=None), dict(currency='JPY'), dict(current_value=None),
                        dict(current_value='-1'), dict(current_value='1e50'), dict(annual_return_rate=True),
                        dict(annual_return_rate='NaN'), dict(field_status={'current_value': 'estimated'})):
            document = self.stage(extraction(**changes))
            self.assertFalse(investment_preview(document)['can_confirm'], changes)
            self.assertEqual(self.confirm(document).status_code, 409)
        self.assertFalse(Investment.objects.exists())

    def test_owner_csrf_expiry_revision_source_and_dependency_binding(self):
        document = self.stage(); token = investment_preview(document)['token']
        path = f'/api/investments/import-uploads/{document.pk}'
        outsider = Client(); outsider.force_login(self.other)
        self.assertEqual(outsider.get(path+'/preview/').status_code, 404)
        self.assertEqual(outsider.post(path+'/confirm/', dict(confirm=True, token=token), content_type='application/json').status_code, 404)
        csrf = Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post(path+'/confirm/', dict(confirm=True, token=token), content_type='application/json').status_code, 403)
        with patch('django.core.signing.time.time', return_value=1): expired = investment_preview(document)['token']
        self.assertEqual(self.confirm(document, expired).status_code, 409)
        edited = edit_investment_review(document, revision=0, edits=[dict(index=0, current_value='0')])
        self.assertEqual(self.confirm(edited, token).status_code, 409)
        self.assertEqual(edited.extracted_payload['import_review']['original'][0]['current_value'], '11000.005')
        fresh = investment_preview(edited)['token']
        Investment.objects.create(user=self.owner, **extraction()['investments'][0])
        self.assertEqual(self.confirm(edited, fresh).status_code, 409)
        Path(document.uploaded_file.path).write_bytes(b'%PDF changed')
        self.assertFalse(investment_preview(edited)['source_ok'])

    def test_duplicates_retry_races_rollback_and_source_removal(self):
        document = self.stage(); token = investment_preview(document)['token']
        with patch('apps.investments.services.import_review.capture_import', side_effect=OperationalError('synthetic failure')):
            self.assertEqual(self.confirm(document, token).status_code, 409)
        self.assertFalse(Investment.objects.exists())
        def parsed(*args, **kwargs):
            self.assertEqual(self.confirm(document, token).status_code, 200)
            return extraction()
        with patch('alfred_ai.services.document_review.portfolio_intelligence_service.parse_portfolio_document', side_effect=parsed):
            with self.assertRaises(InvestmentReviewConflict): _retry_investment_document(self.owner, document.pk)
        duplicate = self.stage()
        self.assertIn(document.pk, investment_preview(duplicate)['duplicate_documents'])
        self.assertEqual(self.confirm(duplicate).json()['created_count'], 0)
        before = list(Investment.objects.values())
        delete_document(self.owner, scope='investment_document', document_id=duplicate.pk)
        delete_document(self.owner, scope='investment_document', document_id=document.pk)
        self.assertEqual(list(Investment.objects.values()), before)

    def test_correction_only_edits_draft_and_retry_preserves_edits(self):
        document = self.stage(); self.assertEqual(self.confirm(document).status_code, 200)
        before = list(Investment.objects.values())
        apply_correction(self.owner, scope='investment_document', document_id=document.pk, corrections={'current_value': '0'})
        self.assertEqual(list(Investment.objects.values()), before)
        with self.assertRaises(InvestmentReviewConflict): _retry_investment_document(self.owner, document.pk)
        document.refresh_from_db()
        self.assertEqual(document.extracted_payload['import_review']['candidate'][0]['current_value'], '0.00')

    def test_real_pdf_is_retained_and_requires_reviewed_terms_before_confirmation(self):
        pdf = portfolio_pdf([('SYNTHETIC-01', '100.25', '110.20')])
        response = self.client.post('/api/investments/import-pdf/',
            {'file': SimpleUploadedFile('synthetic.pdf', pdf, content_type='application/pdf')})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertFalse(Investment.objects.exists())
        document = InvestmentImportDocument.objects.get(pk=response.json()['upload']['id'])
        preview = investment_preview(document)
        self.assertFalse(preview['can_confirm'])
        values = {key: preview['rows'][0][key] for key in ('asset_type', 'invested_amount', 'current_value', 'annual_return_rate')}
        document = edit_investment_review(document, revision=0, edits=[dict(index=0, **values, currency='INR', monthly_sip='0')])
        self.assertEqual(self.confirm(document).status_code, 200)
        self.assertEqual(Investment.objects.get().current_value, Decimal('110.20'))

    def test_parser_failure_is_recoverable_and_private(self):
        with patch('apps.investments.services.portfolio_intelligence.portfolio_intelligence_service.parse_portfolio_document', side_effect=RuntimeError('SYNTHETIC PRIVATE ERROR')):
            response = self.client.post('/api/investments/import-pdf/',
                {'file': SimpleUploadedFile('synthetic.pdf', b'%PDF synthetic source')})
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('SYNTHETIC PRIVATE ERROR', response.content.decode())
        document = InvestmentImportDocument.objects.get()
        self.assertTrue(Path(document.uploaded_file.path).is_file())
        self.assertFalse(Investment.objects.exists())

    def test_expired_draft_invalid_corrections_foreign_links_and_file_formats(self):
        document = self.stage()
        foreign = Investment.objects.create(user=self.other, asset_type='cash', asset_name='Foreign synthetic')
        path = f'/api/investments/import-uploads/{document.pk}/preview/'
        for fields in (dict(current_value='NaN'), dict(monthly_sip=-1), dict(annual_return_rate=True), dict(target_id=foreign.pk)):
            result = self.client.patch(path, dict(revision=0, edits=[dict(index=0, **fields)]), content_type='application/json')
            self.assertEqual(result.status_code, 400)
        document.refresh_from_db(); self.assertEqual(document.extracted_payload['import_review']['revision'], 0)
        token = investment_preview(document)['token']
        document.extracted_payload['import_review']['expires_at'] = '2020-01-01T00:00:00+00:00'
        document.save(update_fields=['extracted_payload'])
        self.assertFalse(investment_preview(document)['can_confirm'])
        self.assertEqual(self.confirm(document, token).status_code, 409)
        result = self.client.post('/api/investments/import-pdf/', {'file': SimpleUploadedFile('wrong.txt', b'text')})
        self.assertEqual(result.status_code, 400)
        self.assertFalse(Investment.objects.filter(user=self.owner).exists())

    def test_pdf_decimal_precision_and_negative_sign_are_not_silently_changed(self):
        from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service
        from io import BytesIO
        source = portfolio_pdf([('SYNTHETIC-01', '-10000.015', '-11000.005')])
        parsed = portfolio_intelligence_service.parse_portfolio_document(BytesIO(source), user=self.owner, filename='synthetic.pdf')
        self.assertEqual(parsed['investments'][0]['invested_amount'], '-10000.015')
        self.assertEqual(parsed['investments'][0]['current_value'], '-11000.005')
        document = stage_investment_document(user=self.owner, parsed=parsed,
            upload_file=SimpleUploadedFile('synthetic.pdf', source))
        self.assertFalse(investment_preview(document)['can_confirm'])
        self.assertFalse(Investment.objects.filter(user=self.owner).exists())

    def test_binary_attachment_caller_retains_owned_source_without_posting(self):
        from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service
        from io import BytesIO
        stream = BytesIO(portfolio_pdf([('SYNTHETIC-ATTACHMENT', '100', '120')]))
        result = portfolio_intelligence_service.parse_portfolio_pdf(stream, self.owner, filename='synthetic-attachment.pdf')
        document = InvestmentImportDocument.objects.get(pk=result['upload_id'], user=self.owner)
        self.assertTrue(Path(document.uploaded_file.path).is_file())
        self.assertEqual(document.file_name, 'synthetic-attachment.pdf')
        self.assertEqual((result['created'], result['updated']), (0, 0))
        self.assertIn('/review/', result['review_url'])
        self.assertFalse(Investment.objects.filter(user=self.owner).exists())


class InvestmentConcurrentConfirmationTests(TransactionTestCase):
    def test_concurrent_confirmation_and_idempotent_retry(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-investment-race-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(_offline_fixture_patches())
        owner = get_user_model().objects.create_user(username='synthetic-investment-race-owner')
        document = stage_investment_document(user=owner, parsed=extraction(),
            upload_file=SimpleUploadedFile('synthetic-race.pdf', b'%PDF synthetic'))
        token = investment_preview(document)['token']; barrier = Barrier(2, timeout=10)
        def preview(*args, **kwargs):
            result = investment_preview(*args, **kwargs); barrier.wait(); return result
        def confirm(_):
            try: return confirm_investment_review(document, token=token)
            except (OperationalError, InvestmentReviewConflict): return 'retry'
            finally: connections.close_all()
        with patch('apps.investments.services.import_review.investment_preview', side_effect=preview):
            with ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(confirm, range(2)))
        self.assertLessEqual(Investment.objects.count(), 1)
        confirm_investment_review(document, token=token)
        self.assertTrue(confirm_investment_review(document, token=token)['replayed'])
        self.assertEqual(Investment.objects.count(), 1)
