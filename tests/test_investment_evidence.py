"""Synthetic original extraction, owner attestation and unchanged financial authority."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import F
from django.http import Http404
from django.test import Client, TestCase

from apps.expenses.models import Expense, BankAccount
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.investments.models import Investment, InvestmentImportDocument, InvestmentDocumentEvidence
from apps.investments.services import document_evidence as service
from alfred_ai.services.document_review import apply_correction, retry_review_item
from tests import test_canonical_evidence as fixtures


class InvestmentEvidenceTests(TestCase):
    def setUp(self):
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.raw=dict(asset_name=self.investment.asset_name, institution='', asset_type='equity',account_number=self.investment.account_number,
            invested_amount='2000.0100',current_value='2345.6700',monthly_sip='123.4500')
        self.document=InvestmentImportDocument.objects.create(user=self.owner,file_name='synthetic-portfolio.pdf',
            uploaded_file=SimpleUploadedFile('synthetic-portfolio.pdf',b'%PDF-SYNTHETIC-PORTFOLIO'),
            parser_status='parsed',extracted_payload={'investments':[deepcopy(self.raw)],'ocr':'SYNTHETIC-DO-NOT-DISCLOSE'},
            extracted_text='SYNTHETIC-RAW-DOCUMENT-NOT-FOR-MODELS')
        self.document.linked_investments.add(self.investment)
        service.capture_import(self.document,[self.investment],extraction=[self.raw])

    def current(self): return service.evidence(self.owner,self.document.pk,self.investment.pk)

    def endpoint(self): return f'/api/ai/investment-evidence/{self.document.pk}/{self.investment.pk}/'

    def confirm(self, fields=None, *, method='post', revision=None, **values):
        return getattr(self.client,method)(self.endpoint(),json.dumps(dict(revision=revision or self.current()['revision'],
            fields=fields if fields is not None else ['current_value'],confirm=True)|values),content_type='application/json')

    def test_individual_confirmation_preserves_originals_and_all_financial_rows_and_baseline(self):
        models=(Investment,Expense,BankAccount,type(self.owner))
        before=[list(model.objects.order_by('pk').values()) for model in models]
        baseline=resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts']
        self.assertEqual(self.current()['fields']['current_value']['original'],'2345.6700')
        response=self.confirm(); self.assertEqual(response.status_code,200)
        result=response.json(); self.assertEqual(result['fields']['current_value']['verification'],'owner_confirmed')
        self.assertEqual(result['fields']['monthly_sip']['verification'],'needs_owner_review')
        self.assertIsNone(result['fields']['current_value']['currency'])
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts'],baseline)
        self.assertFalse(Path(settings.ALFRED_MEMORY_DIR).exists())
        self.assertIn('no-store',response['Cache-Control'])

    def test_invalid_or_implicit_confirmation_is_rejected_without_any_receipt_mutation(self):
        before=list(InvestmentDocumentEvidence.objects.values())
        for fields in ([],['unknown'],['current_value','current_value'],True,[{}]):
            with self.subTest(fields=fields): self.assertEqual(self.confirm(fields).status_code,400)
        for value in (False,'true',1,None):
            self.assertEqual(self.confirm(confirm=value).status_code,400)
        self.assertEqual(list(InvestmentDocumentEvidence.objects.values()),before)

    def test_owner_only_api_citation_download_and_csrf(self):
        detail=self.current()
        self.assertEqual(self.client.get(detail['citation_url']).status_code,200)
        self.assertEqual(self.client.get(detail['source_download_url']).status_code,200)
        for actor in (None,self.other):
            client=Client()
            if actor: client.force_login(actor)
            for url in (self.endpoint(),detail['citation_url'],detail['source_download_url']):
                self.assertIn(client.get(url).status_code,(302,403,404))
            self.assertIn(client.post(self.endpoint(),dict(revision=detail['revision'],fields=['current_value'],confirm=True),content_type='application/json').status_code,(403,404))
        client=Client(enforce_csrf_checks=True); client.force_login(self.owner)
        data=dict(revision=detail['revision'],fields=['current_value'],confirm=True)
        self.assertEqual(client.post(self.endpoint(),data,content_type='application/json').status_code,403)
        client.get(detail['citation_url'])
        self.assertEqual(client.post(self.endpoint(),data,content_type='application/json',HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)

    def test_no_raw_text_account_or_private_model_content_in_new_api(self):
        self.investment.account_number='SYNTHETIC-PRIVATE-ACCOUNT'; self.investment.save()
        response=self.client.get(self.endpoint()); self.assertEqual(response.status_code,200)
        for secret in ('SYNTHETIC-DO-NOT-DISCLOSE','SYNTHETIC-RAW-DOCUMENT','SYNTHETIC-PRIVATE-ACCOUNT'):
            self.assertNotIn(secret,response.content.decode())
        self.assertFalse(Path(settings.ALFRED_MEMORY_DIR).exists())

    def test_correction_uses_existing_workflow_current_precedence_and_immutable_parser_values(self):
        self.confirm()
        original=deepcopy(InvestmentDocumentEvidence.objects.get().source_values)
        apply_correction(self.owner,scope='investment_document',document_id=self.document.pk,corrections={'current_value':'3456.78'})
        result=self.current()['fields']['current_value']
        self.assertEqual(result['current'],'3456.78'); self.assertEqual(result['original'],'2345.6700')
        self.assertEqual(result['verification'],'needs_owner_review')
        self.assertEqual(InvestmentDocumentEvidence.objects.get().source_values,original)
        self.assertEqual(self.confirm().json()['fields']['current_value']['verification'],'owner_confirmed')

    def test_retry_preserves_first_original_and_existing_accepted_correction(self):
        apply_correction(self.owner,scope='investment_document',document_id=self.document.pk,corrections={'current_value':'3456.78'})
        self.confirm(); raw=deepcopy(self.raw); raw['current_value']='1.23'
        parsed=dict(investments=[raw],payload={'investments':[raw]},broker='',confidence=.9,parser_status='parsed',extracted_text='SYNTHETIC-RETRY')
        with patch('alfred_ai.services.document_review.portfolio_intelligence_service.parse_portfolio_document',return_value=parsed):
            retry_review_item(self.owner,scope='investment_document',document_id=self.document.pk)
        result=self.current()['fields']['current_value']
        self.assertEqual(result['current'],'3456.78'); self.assertEqual(result['original'],'2345.6700')
        self.assertEqual(result['verification'],'needs_owner_review')

    def test_record_edit_source_replacement_and_partial_parse_invalidate_receipts(self):
        self.confirm(); stale=self.current()['revision']
        Investment.objects.filter(pk=self.investment.pk).update(current_value='4567.89')
        self.assertEqual(self.current()['fields']['current_value']['verification'],'needs_owner_review')
        self.assertEqual(self.confirm(revision=stale).status_code,409)
        self.confirm(); stale=self.current()['revision']
        Path(self.document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-REPLACEMENT')
        self.assertEqual(self.confirm(revision=stale).status_code,409)
        self.document.extracted_payload['preview_only']=True; self.document.save()
        self.assertFalse(self.current()['review_allowed']); self.assertEqual(self.confirm().status_code,409)

    def test_missing_or_deleted_source_does_not_remain_confirmed(self):
        self.confirm(); Path(self.document.uploaded_file.path).unlink()
        self.assertFalse(self.current()['review_allowed'])
        self.assertEqual(self.current()['fields']['current_value']['verification'],'source_unavailable')
        self.assertEqual(self.confirm(method='delete').status_code,200)
        self.document.delete()
        self.assertEqual(self.client.get(self.endpoint()).status_code,404)
        self.assertEqual(InvestmentDocumentEvidence.objects.count(),0)

    def test_revocation_is_field_scoped_and_rejects_aba_reuse(self):
        self.confirm(list(service.FIELDS)); stale=self.current()['revision']
        result=self.confirm(['current_value'],method='delete').json()
        self.assertEqual(result['fields']['current_value']['verification'],'needs_owner_review')
        self.assertEqual(result['fields']['monthly_sip']['verification'],'owner_confirmed')
        self.assertEqual(self.confirm(revision=stale).status_code,409)
        self.assertEqual(self.confirm().status_code,200)

    def test_legacy_records_do_not_gain_invented_original_extraction(self):
        InvestmentDocumentEvidence.objects.all().delete()
        self.assertEqual(self.current()['fields']['current_value']['original_status'],'not_retained')
        self.assertEqual(self.confirm().status_code,200)
        self.assertEqual(InvestmentDocumentEvidence.objects.get().source_values,{})

    def test_reimport_and_ambiguous_rows_never_overwrite_first_snapshot(self):
        raw=deepcopy(self.raw); raw['current_value']='1.23'
        service.capture_import(self.document,[self.investment],extraction=[raw])
        self.assertEqual(self.current()['fields']['current_value']['original'],'2345.6700')
        InvestmentDocumentEvidence.objects.all().delete()
        service.capture_import(self.document,[self.investment],extraction=[self.raw,raw])
        self.assertEqual(self.current()['fields']['current_value']['original_status'],'not_retained')

    def test_parent_ownership_and_unlinked_or_deleted_holding_are_denied(self):
        foreign=Investment.objects.create(user=self.other,asset_type='equity',asset_name='SYNTHETIC-FOREIGN')
        self.document.linked_investments.add(foreign)
        self.assertEqual(self.client.get(self.endpoint()).status_code,404)
        self.document.linked_investments.remove(foreign)
        self.investment.delete()
        proof=InvestmentDocumentEvidence.objects.get(); self.assertIsNone(proof.investment_id)
        self.assertEqual(proof.source_values['current_value'],'2345.6700')
        with self.assertRaises(Http404): service.evidence(self.owner,self.document.pk,proof.original_investment_id)

    def test_generation_compare_and_swap_rejects_a_concurrent_confirmation(self):
        revision=self.current()['revision']; original=service._state
        def changed(*args):
            result=original(*args)
            InvestmentDocumentEvidence.objects.update(review_generation=F('review_generation')+1)
            return result
        with patch.object(service,'_state',side_effect=changed), self.assertRaises(service.EvidenceConflict):
            service.review(self.owner,self.document.pk,self.investment.pk,revision=revision,fields=['current_value'],confirm=True)
        self.assertEqual(InvestmentDocumentEvidence.objects.get().reviewed_fields,{})

    def test_renamed_holding_retains_original_field_evidence_without_inheriting_confirmation(self):
        self.confirm()
        apply_correction(self.owner,scope='investment_document',document_id=self.document.pk,
            corrections={'asset_name':'SYNTHETIC-RENAMED-HOLDING','current_value':'3456.78'})
        replacement=self.document.linked_investments.get(asset_name='SYNTHETIC-RENAMED-HOLDING')
        detail=service.evidence(self.owner,self.document.pk,replacement.pk)
        self.assertEqual(detail['fields']['current_value']['original'],'2345.6700')
        self.assertEqual(detail['fields']['current_value']['current'],'3456.78')
        self.assertEqual(detail['fields']['current_value']['verification'],'needs_owner_review')
        self.assertTrue(InvestmentDocumentEvidence.objects.filter(source_values__current_value='2345.6700').exists())

    def test_failed_receipt_capture_rolls_back_new_imported_financial_records(self):
        def parsed(*args,**kwargs):
            row=Investment.objects.create(user=self.owner,asset_type='equity',asset_name='SYNTHETIC-ATOMIC-IMPORT')
            return dict(investments=[row],payload={'investments':[]})
        before=list(Investment.objects.values())
        with patch('apps.investments.views.portfolio_intelligence_service.parse_portfolio_pdf',side_effect=parsed), \
                patch.object(service,'capture_import',side_effect=RuntimeError('synthetic-metadata-failure')):
            response=self.client.post('/api/investments/import-pdf/',{'file':SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC',content_type='application/pdf')})
        self.assertEqual(response.status_code,500); self.assertTrue(response.json()['error_id'])
        self.assertNotIn('synthetic-metadata-failure',response.content.decode())
        self.assertEqual(list(Investment.objects.values()),before)
        self.assertEqual(InvestmentImportDocument.objects.count(),1)

    def test_new_upload_captures_exact_parser_value_without_automatic_confirmation(self):
        raw=dict(asset_name='SYNTHETIC-NEW-IMPORT',institution='',current_value='2.675')
        def parsed(*args,**kwargs):
            row=Investment.objects.create(user=self.owner,asset_type='equity',asset_name=raw['asset_name'],current_value=raw['current_value'])
            return dict(investments=[row],payload={'investments':[raw]})
        with patch('apps.investments.views.portfolio_intelligence_service.parse_portfolio_pdf',side_effect=parsed):
            response=self.client.post('/api/investments/import-pdf/',{'file':SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC',content_type='application/pdf')})
        self.assertEqual(response.status_code,201)
        row=Investment.objects.get(asset_name=raw['asset_name'])
        proof=InvestmentDocumentEvidence.objects.get(investment=row)
        self.assertEqual(str(row.current_value),'2.68'); self.assertEqual(proof.source_values['current_value'],'2.675')
        self.assertEqual(proof.reviewed_fields,{})

    def test_snapshot_capture_rejects_foreign_rows_atomically(self):
        other=Investment.objects.create(user=self.other,asset_type='equity',asset_name='SYNTHETIC-FOREIGN')
        second=Investment.objects.create(user=self.owner,asset_type='equity',asset_name='SYNTHETIC-SECOND')
        before=list(InvestmentDocumentEvidence.objects.values())
        with self.assertRaises(ValueError): service.capture_import(self.document,[second,other])
        self.assertEqual(list(InvestmentDocumentEvidence.objects.values()),before)
