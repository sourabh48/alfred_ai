"""Synthetic field receipts reuse loan corrections without changing the financial register."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.db.models import F
from django.test import TestCase, Client, override_settings

from apps.expenses.models import Expense, BankAccount
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.loans.models import Loan, LoanImportDocument, LoanDocumentEvidence, LoanPaymentHistory
from apps.loans.services import document_evidence as service
from alfred_ai.services.document_review import apply_correction, retry_review_item
from tests import test_canonical_evidence as fixtures


class LoanEvidenceTests(TestCase):
    def setUp(self):
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.loan.lender='SYNTHETIC-LENDER'; self.loan.loan_account_number='SYNTHETIC-PRIVATE-LOAN'; self.loan.save()
        self.raw=dict(lender=self.loan.lender,loan_type='other',loan_account_number=self.loan.loan_account_number,
            principal='10000.0100',emi='100.0100',remaining_balance='9000.0100',interest_rate=5,
            tenure_months=100,start_date='2026-01-01')
        self.document=LoanImportDocument.objects.create(user=self.owner,file_name='synthetic-loan.pdf',
            uploaded_file=SimpleUploadedFile('synthetic-loan.pdf',b'%PDF-SYNTHETIC-LOAN'),parser_status='parsed',
            extracted_payload={'loans':[dict(self.raw,start_date='2026-01-01')],'ocr':'SYNTHETIC-DO-NOT-DISCLOSE'},
            extracted_text='SYNTHETIC-RAW-LOAN-NOT-FOR-MODELS')
        self.document.linked_loans.add(self.loan)
        service.capture_import(self.document,[self.loan],extraction=[self.raw])

    def current(self): return service.evidence(self.owner,self.document.pk,self.loan.pk)

    def endpoint(self): return f'/api/ai/loan-evidence/{self.document.pk}/{self.loan.pk}/'

    def confirm(self, fields=None, *, method='post', revision=None, **values):
        data=dict(revision=revision or self.current()['revision'],fields=fields if fields is not None else ['emi'],confirm=True)|values
        return getattr(self.client,method)(self.endpoint(),json.dumps(data),content_type='application/json')

    def test_explicit_field_review_preserves_financial_rows_fingerprints_baseline_and_verification(self):
        models=(Loan,LoanPaymentHistory,Expense,BankAccount,type(self.owner))
        before=[list(model.objects.order_by('pk').values()) for model in models]
        baseline=resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts']
        result=self.confirm(); self.assertEqual(result.status_code,200)
        fields=result.json()['fields']
        self.assertEqual(fields['emi']['original'],'100.0100'); self.assertEqual(fields['emi']['current'],'100.01')
        self.assertEqual(fields['emi']['verification'],'owner_confirmed')
        self.assertEqual(fields['principal']['verification'],'needs_owner_review')
        self.assertEqual(fields['emi']['currency_status'],'not_recorded'); self.assertIsNone(fields['emi']['currency'])
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts'],baseline)
        self.assertFalse(Path(settings.ALFRED_MEMORY_DIR).exists()); self.assertIn('no-store',result['Cache-Control'])
        Loan.objects.filter(pk=self.loan.pk).update(verification_status='estimated')
        self.assertEqual(self.confirm().status_code,200)
        self.loan.refresh_from_db(); self.assertEqual(self.loan.verification_status,'estimated')

    def test_invalid_implicit_and_missing_amount_confirmation_do_not_write(self):
        before=list(LoanDocumentEvidence.objects.values())
        for fields in ([],['unknown'],['emi','emi'],True,[{}]):
            with self.subTest(fields=fields): self.assertEqual(self.confirm(fields).status_code,400)
        for value in (False,'true',1,None): self.assertEqual(self.confirm(confirm=value).status_code,400)
        self.assertEqual(list(LoanDocumentEvidence.objects.values()),before)
        Loan.objects.filter(pk=self.loan.pk).update(remaining_balance=None)
        detail=self.current()['fields']['remaining_balance']
        self.assertIsNone(detail['current']); self.assertEqual(detail['verification'],'not_recorded')
        self.assertEqual(self.confirm(['remaining_balance']).status_code,400)

    def test_owner_session_csrf_citation_and_download_boundaries(self):
        detail=self.current()
        self.assertEqual(self.client.get(detail['citation_url']).status_code,200)
        download=self.client.get(detail['source_download_url']); self.addCleanup(download.close)
        self.assertEqual(download.status_code,200)
        for actor in (None,self.other):
            client=Client()
            if actor: client.force_login(actor)
            for url in (self.endpoint(),detail['citation_url'],detail['source_download_url']):
                self.assertIn(client.get(url).status_code,(302,403,404))
            self.assertIn(client.post(self.endpoint(),dict(revision=detail['revision'],fields=['emi'],confirm=True),content_type='application/json').status_code,(403,404))
        client=Client(enforce_csrf_checks=True); client.force_login(self.owner)
        data=dict(revision=detail['revision'],fields=['emi'],confirm=True)
        self.assertEqual(client.post(self.endpoint(),data,content_type='application/json').status_code,403)
        client.get(detail['citation_url'])
        self.assertEqual(client.post(self.endpoint(),data,content_type='application/json',HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code,200)

    def test_api_and_html_do_not_disclose_raw_text_account_or_diagnostics(self):
        for url in (self.endpoint(),self.current()['citation_url']):
            response=self.client.get(url); self.assertEqual(response.status_code,200)
            for secret in ('SYNTHETIC-PRIVATE-LOAN','SYNTHETIC-DO-NOT-DISCLOSE','SYNTHETIC-RAW-LOAN'):
                self.assertNotIn(secret,response.content.decode())
        self.assertFalse(Path(settings.ALFRED_MEMORY_DIR).exists())

    def test_existing_loan_edit_wins_over_original_and_invalidates_confirmation(self):
        self.confirm(); revision=self.current()['revision']
        response=self.client.patch(f'/api/loans/{self.loan.pk}/',{'emi':'123.45'},content_type='application/json')
        self.assertEqual(response.status_code,200)
        field=self.current()['fields']['emi']
        self.assertEqual(field['current'],'123.45'); self.assertEqual(field['original'],'100.0100')
        self.assertEqual(field['verification'],'needs_owner_review')
        self.assertEqual(self.confirm(revision=revision).status_code,409)
        self.assertEqual(self.confirm().status_code,200)

    def test_document_identity_correction_retry_and_reimport_preserve_first_original(self):
        self.confirm(); original=deepcopy(LoanDocumentEvidence.objects.get().source_values)
        apply_correction(self.owner,scope='loan_document',document_id=self.document.pk,corrections={'lender':'SYNTHETIC-CORRECTED'})
        self.assertEqual(self.current()['fields']['emi']['verification'],'needs_owner_review')
        raw=dict(self.raw,emi='1.23')
        with patch('alfred_ai.services.document_review.loan_pdf_parser.parse_document',return_value={
            'loans':[raw],'document_type':'loan_statement','confidence':.9,'extracted_text':'SYNTHETIC-RETRY'}):
            retry_review_item(self.owner,scope='loan_document',document_id=self.document.pk)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.lender,'SYNTHETIC-CORRECTED')
        self.assertEqual(self.current()['fields']['emi']['current'],'1.23')
        self.assertEqual(LoanDocumentEvidence.objects.get().source_values,original)
        service.capture_import(self.document,[self.loan],extraction=[raw])
        self.assertEqual(LoanDocumentEvidence.objects.get().source_values,original)

    def test_changed_missing_partial_and_unlinked_sources_reject_stale_confirmation(self):
        self.confirm(); stale=self.current()['revision']
        Path(self.document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-CHANGED')
        self.assertEqual(self.confirm(revision=stale).status_code,409)
        self.confirm(); self.document.extracted_payload['ocr_progress']={'is_partial':True}; self.document.save()
        self.assertFalse(self.current()['review_allowed']); self.assertEqual(self.confirm().status_code,409)
        Path(self.document.uploaded_file.path).unlink()
        self.assertEqual(self.current()['fields']['emi']['verification'],'source_unavailable')
        self.assertEqual(self.confirm(method='delete').status_code,200)
        self.document.linked_loans.clear(); self.assertEqual(self.client.get(self.endpoint()).status_code,404)

    def test_field_revocation_and_aba_protection(self):
        self.confirm(list(service.FIELDS)); stale=self.current()['revision']
        result=self.confirm(['emi'],method='delete').json()['fields']
        self.assertEqual(result['emi']['verification'],'needs_owner_review')
        self.assertEqual(result['principal']['verification'],'owner_confirmed')
        self.assertEqual(self.confirm(revision=stale).status_code,409)

    def test_legacy_or_ambiguous_originals_remain_unknown(self):
        LoanDocumentEvidence.objects.all().delete()
        self.assertEqual(self.current()['fields']['emi']['original_status'],'not_retained')
        self.assertEqual(self.confirm().status_code,200)
        self.assertEqual(LoanDocumentEvidence.objects.get().source_values,{})
        LoanDocumentEvidence.objects.all().delete()
        service.capture_import(self.document,[self.loan],extraction=[self.raw,self.raw])
        self.assertEqual(LoanDocumentEvidence.objects.get().source_values,{})

    def test_foreign_link_and_foreign_capture_rejected_atomically_original_survives_loan_deletion(self):
        foreign=Loan.objects.create(user=self.other,principal=1,emi=1,interest_rate=1,start_date=date(2026,1,1))
        self.document.linked_loans.add(foreign)
        self.assertEqual(self.client.get(self.endpoint()).status_code,404)
        LoanDocumentEvidence.objects.all().delete()
        with self.assertRaises(ValueError): service.capture_import(self.document,[self.loan,foreign],extraction=[self.raw])
        self.assertEqual(LoanDocumentEvidence.objects.count(),0)
        self.document.linked_loans.remove(foreign); service.capture_import(self.document,[self.loan],extraction=[self.raw])
        self.loan.delete(); proof=LoanDocumentEvidence.objects.get()
        self.assertIsNone(proof.loan_id); self.assertEqual(proof.source_values['emi'],'100.0100')
        self.document.delete(); self.assertEqual(LoanDocumentEvidence.objects.count(),0)

    def test_generation_cas_rejects_a_concurrent_confirmation(self):
        revision=self.current()['revision']; original=service._state
        def changed(*args):
            result=original(*args); LoanDocumentEvidence.objects.update(review_generation=F('review_generation')+1)
            return result
        with patch.object(service,'_state',side_effect=changed),self.assertRaises(service.EvidenceConflict):
            service.review(self.owner,self.document.pk,self.loan.pk,revision=revision,fields=['emi'],confirm=True)
        self.assertEqual(LoanDocumentEvidence.objects.get().reviewed_fields,{})

    def test_displayed_snapshot_revision_rejects_an_edit_racing_the_initial_read(self):
        owned=service._owned
        def changed(*args):
            document,row=owned(*args); Loan.objects.filter(pk=row.pk).update(emi='123.45'); return document,row
        with patch.object(service,'_owned',side_effect=changed): stale=self.current()
        self.assertEqual(stale['fields']['emi']['current'],'100.01')
        self.assertEqual(self.confirm(revision=stale['revision']).status_code,409)

    def test_new_upload_records_parser_precision_only_after_bounded_extraction(self):
        from alfred_ai.services.upload_limits import begin_upload_writes
        baseline=len(connection.atomic_blocks); raw=dict(self.raw,loan_account_number='SYNTHETIC-NEW',emi='2.675')
        def parsed(*args,**kwargs):
            self.assertEqual(len(connection.atomic_blocks),baseline); begin_upload_writes()
            return dict(loans=[raw],confidence=.9,document_type='loan_statement',extracted_text='SYNTHETIC')
        with patch('apps.loans.views.loan_pdf_parser.parse_document',side_effect=parsed):
            response=self.client.post('/api/loans/import-pdf/',{'file':SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC')})
        self.assertEqual(response.status_code,201)
        row=Loan.objects.get(loan_account_number='SYNTHETIC-NEW'); proof=LoanDocumentEvidence.objects.get(loan=row)
        self.assertEqual(str(row.emi),'2.68'); self.assertEqual(proof.source_values['emi'],'2.675')
        self.assertEqual(proof.reviewed_fields,{})

    def test_failed_receipt_capture_rolls_back_import_without_disclosing_exception(self):
        from alfred_ai.services.upload_limits import begin_upload_writes
        raw=dict(self.raw,loan_account_number='SYNTHETIC-ROLLBACK')
        def parsed(*args,**kwargs):
            begin_upload_writes()
            return dict(loans=[raw],confidence=.9,document_type='loan_statement')
        before=list(Loan.objects.values())
        with patch('apps.loans.views.loan_pdf_parser.parse_document',side_effect=parsed),patch.object(service,'capture_import',side_effect=RuntimeError('SYNTHETIC-PRIVATE-ERROR')):
            response=self.client.post('/api/loans/import-pdf/',{'file':SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC')})
        self.assertEqual(response.status_code,500); self.assertNotIn('SYNTHETIC-PRIVATE-ERROR',response.content.decode())
        self.assertEqual(list(Loan.objects.values()),before); self.assertEqual(LoanImportDocument.objects.count(),1)

    def test_source_limits_and_operational_failures_are_safe(self):
        citation=self.current()['citation_url']
        with override_settings(ALFRED_UPLOAD_FILE_BYTES=8):
            for url in (self.endpoint(),citation,f'/ai/financial-records/loan/{self.loan.pk}/'):
                self.assertEqual(self.client.get(url).status_code,413)
        with patch.object(service,'evidence',side_effect=RuntimeError('SYNTHETIC-PRIVATE-ERROR C:/private/document.pdf')):
            response=self.client.get(citation); self.assertEqual(response.status_code,503)
            self.assertTrue(response.json()['error_id']); self.assertNotIn('SYNTHETIC-PRIVATE-ERROR',response.content.decode())
        with patch.object(service,'file_reference',side_effect=RuntimeError('SYNTHETIC-PRIVATE-ERROR C:/private/document.pdf')):
            for url in (self.endpoint(),citation,f'/ai/financial-records/loan/{self.loan.pk}/',f'/api/ai/financial-evidence/loan/{self.loan.pk}/'):
                response=self.client.get(url); self.assertEqual(response.status_code,503)
                self.assertTrue(response.json()['error_id']); self.assertNotIn('SYNTHETIC-PRIVATE-ERROR',response.content.decode())
