"""Loan field evidence augments canonical facts; never changes financial authority."""
import json
from pathlib import Path
from unittest.mock import patch
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import Http404
from django.test import TestCase

from apps.loans.models import Loan, LoanImportDocument
from apps.loans.services.document_evidence import capture_import, evidence, review, FIELDS
from apps.ml_engine.services.canonical_evidence import record_source
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from apps.ml_engine.services.persistent_memory import MemoryConflict
from tests import test_canonical_grounding as fixtures


class LoanGroundingTests(TestCase):
    def setUp(self):
        fixtures.CanonicalGroundingTests.setUp(self)
        self.loan.loan_account_number='SYNTHETIC-PRIVATE-ACCOUNT'; self.loan.save()
        self.document=LoanImportDocument.objects.create(user=self.owner,file_name='SYNTHETIC-PRIVATE-DOC-NAME.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC-LOAN'),parser_status='parsed',
            extracted_text='SYNTHETIC-NEVER-PROMPT-OR-CLOUD',extracted_payload={'ocr':'SYNTHETIC-NEVER-PROMPT-OR-CLOUD'})
        self.document.linked_loans.add(self.loan)
        raw=dict(loan_account_number=self.loan.loan_account_number,emi='1.23',principal='2.34',remaining_balance='3.45')
        capture_import(self.document,[self.loan],extraction=[raw])

    def confirm(self, fields=None, revoke=False):
        return review(self.owner,self.document.pk,self.loan.pk,revision=evidence(self.owner,self.document.pk,self.loan.pk)['revision'],
            fields=list(FIELDS) if fields is None else fields,confirm=True,revoke=revoke)

    def source(self): return record_source(self.owner,'loan',self.loan.pk)

    def answer(self, **changes):
        return hybrid_answer(self.store,self.owner,'Explain this record',**(dict(scope='financial_records',
            record_type='loan',record_id=self.loan.pk,local=self.local)|changes))

    def test_partial_field_review_does_not_verify_other_fields_or_paid_totals(self):
        self.assertEqual(self.source()['data']['document_verification'],'imported_record_not_field_verified')
        self.confirm(['emi']); source=self.source(); fields=source['data']['amounts']
        self.assertEqual(source['data']['verification'],'confirmed')
        self.assertEqual(fields['emi']['evidence_status'],'owner_confirmed_document_field')
        self.assertEqual(fields['emi']['amount'],'100.01'); self.assertEqual(fields['emi']['source_document_ids'],[self.document.pk])
        for name in ('principal','remaining_balance','total_paid'):
            self.assertNotEqual(fields[name]['evidence_status'],'owner_confirmed_document_field')
            self.assertEqual(fields[name]['source_document_ids'],[])
        self.assertIn(evidence(self.owner,self.document.pk,self.loan.pk)['citation_url'],self.client.get(source['url']).content.decode())

    def test_local_answer_uses_current_values_and_exact_private_citation_without_raw_context(self):
        self.confirm(); before=list(Loan.objects.values()); result=self.answer(); source=self.source()
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        self.assertEqual(source['url'],evidence(self.owner,self.document.pk,self.loan.pk)['citation_url'])
        self.assertEqual(result['sources'][0]['url'],source['url'])
        payload=json.dumps(self.local.reason.call_args.args[0])
        for private in ('SYNTHETIC-NEVER-PROMPT-OR-CLOUD','SYNTHETIC-PRIVATE-DOC-NAME','SYNTHETIC-PRIVATE-ACCOUNT','/documents/loans/','1.23'):
            self.assertNotIn(private,payload)
        self.assertIn('100.01',payload); self.cloud.assert_not_called(); self.provider.assert_not_called()
        self.assertEqual(list(Loan.objects.values()),before)
        self.client.force_login(self.other); self.assertEqual(self.client.get(source['url']).status_code,404)

    def test_revocation_unlink_file_replacement_deletion_and_reparenting_during_inference_reject_answer(self):
        contents=Path(self.document.uploaded_file.path).read_bytes()
        changes=[lambda:self.confirm(['emi'],revoke=True),lambda:self.document.linked_loans.clear(),
            lambda:Path(self.document.uploaded_file.path).unlink(),
            lambda:Path(self.document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-CHANGED'),
            lambda:LoanImportDocument.objects.filter(pk=self.document.pk).update(user=self.other),
            lambda:LoanImportDocument.objects.filter(pk=self.document.pk).delete()]
        for index,change in enumerate(changes):
            with self.subTest(change=index),transaction.atomic():
                self.confirm()
                def changed(*args,**kwargs): change(); return 'SYNTHETIC-STALE-ANSWER'
                self.local.reason.side_effect=changed
                with self.assertRaises(MemoryConflict): self.answer()
                transaction.set_rollback(True)
            Path(self.document.uploaded_file.path).write_bytes(contents)

    def test_lost_source_preserves_canonical_facts_without_document_verification(self):
        self.confirm(); self.confirm(['emi'],revoke=True)
        source=self.source(); self.assertEqual(source['data']['amounts']['emi']['amount'],'100.01')
        self.assertNotEqual(source['data']['amounts']['emi']['evidence_status'],'owner_confirmed_document_field')
        Path(self.document.uploaded_file.path).unlink(); source=self.source()
        self.assertTrue(all(not value['source_document_ids'] for value in source['data']['amounts'].values()))
        self.assertEqual(source['data']['document_sources'][0]['source_status'],'source_unavailable')
        self.assertEqual(source['data']['document_verification'],'imported_record_not_field_verified')

    def test_cloud_consent_is_refused_for_private_financial_fields(self):
        self.confirm()
        with self.assertRaises(PermissionDenied): self.answer(cloud_consent=True)
        self.local.reason.assert_not_called(); self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_excessive_source_count_and_foreign_sources_fail_closed(self):
        for index in range(5):
            document=LoanImportDocument.objects.create(user=self.owner,file_name=f'synthetic-{index}.pdf')
            document.linked_loans.add(self.loan)
        source=self.source(); self.assertFalse(source['available'])
        self.assertEqual(source['data']['document_verification'],'source_review_limit')
        self.assertTrue(all(value['amount'] is None for value in source['data']['amounts'].values()))
        LoanImportDocument.objects.filter(pk=self.document.pk).update(user=self.other)
        with self.assertRaises(Http404): self.source()

    def test_newer_confirmed_value_cannot_certify_an_older_canonical_snapshot(self):
        from apps.loans.services import document_evidence as service
        original=service.evidence
        def changed(*args,**kwargs):
            Loan.objects.filter(pk=self.loan.pk).update(emi='123.45')
            with patch.object(service,'evidence',original): self.confirm()
            return original(*args,**kwargs)
        with patch.object(service,'evidence',side_effect=changed): source=self.source()
        value=source['data']['amounts']['emi']; self.assertEqual(value['amount'],'100.01')
        self.assertNotEqual(value['evidence_status'],'owner_confirmed_document_field'); self.assertEqual(value['source_document_ids'],[])

    def test_field_confirmation_does_not_override_estimated_contract_or_missing_balance(self):
        self.confirm(); Loan.objects.filter(pk=self.loan.pk).update(verification_status='estimated')
        self.confirm(); source=self.source(); self.assertFalse(source['available'])
        self.assertEqual(source['data']['verification'],'estimated')
        self.assertEqual(self.answer()['provider'],'local_evidence'); self.local.reason.assert_not_called()
        Loan.objects.filter(pk=self.loan.pk).update(verification_status='confirmed',remaining_balance=None)
        self.confirm(['emi']); fields=self.source()['data']['amounts']
        self.assertIsNone(fields['remaining_balance']['amount']); self.assertIsNone(fields['emi']['currency'])
        self.assertEqual(fields['emi']['currency_status'],'not_recorded')
