"""Investment field receipts integrate with existing local canonical tools, never cloud."""
from pathlib import Path
import json
from unittest.mock import patch
from django.db import transaction
from django.test import TestCase
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.investments.models import InvestmentImportDocument, InvestmentDocumentEvidence
from apps.investments.services.document_evidence import evidence, review, capture_import, FIELDS
from apps.ml_engine.services.canonical_evidence import record_source
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from apps.ml_engine.services.persistent_memory import MemoryConflict
from tests import test_canonical_grounding as fixtures


class InvestmentGroundingTests(TestCase):
    def setUp(self):
        fixtures.CanonicalGroundingTests.setUp(self)
        self.document=InvestmentImportDocument.objects.create(user=self.owner,file_name='SYNTHETIC-PRIVATE-DOC-NAME.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC-INVESTMENT'),parser_status='parsed',
            extracted_text='SYNTHETIC-NEVER-PROMPT-OR-CLOUD',extracted_payload={'originals':'SYNTHETIC-NEVER-PROMPT-OR-CLOUD'})
        self.document.linked_investments.add(self.investment)
        raw=dict(asset_name=self.investment.asset_name,institution=self.investment.institution,
            current_value='1.23',invested_amount='2.34',monthly_sip='3.45')
        capture_import(self.document,[self.investment],extraction=[raw])

    def confirm(self, fields=None, revoke=False):
        return review(self.owner,self.document.pk,self.investment.pk,revision=evidence(self.owner,self.document.pk,self.investment.pk)['revision'],
            fields=list(FIELDS) if fields is None else fields,confirm=True,revoke=revoke)

    def source(self): return record_source(self.owner,'investment',self.investment.pk)

    def answer(self, **changes):
        return hybrid_answer(self.store,self.owner,'Explain this record',**(dict(scope='financial_records',
            record_type='investment',record_id=self.investment.pk,local=self.local)|changes))

    def test_field_attestation_never_verifies_unselected_fields_or_original_extraction(self):
        self.assertEqual(self.source()['data']['verification'],'imported_record_not_field_verified')
        self.confirm(['current_value']); source=self.source()
        current=source['data']['amounts']['current_value']
        self.assertEqual(current['amount'],'2345.67'); self.assertEqual(current['evidence_status'],'owner_confirmed_document_field')
        self.assertIsNone(current['currency']); self.assertEqual(current['source_document_ids'],[self.document.pk])
        self.assertNotEqual(source['data']['amounts']['monthly_sip']['evidence_status'],'owner_confirmed_document_field')
        self.assertEqual(InvestmentDocumentEvidence.objects.get().source_values['current_value'],'1.23')
        self.assertTrue(self.client.get(source['url']).content.find(b'Review source document')>=0)

    def test_confirmed_sources_use_exact_owner_citation_and_allowlisted_local_prompt_only(self):
        self.confirm(); before=list(type(self.investment).objects.values())
        result=self.answer(); source=self.source()
        self.assertEqual(result['provider'],'ollama')
        self.assertEqual(source['url'],evidence(self.owner,self.document.pk,self.investment.pk)['citation_url'])
        self.assertEqual(result['sources'][0]['url'],source['url'])
        payload=json.dumps(self.local.reason.call_args.args[0])
        for private in ('SYNTHETIC-NEVER-PROMPT-OR-CLOUD','SYNTHETIC-PRIVATE-DOC-NAME',self.investment.asset_name,
                        self.investment.account_number,'/documents/investments/','1.23'):
            self.assertNotIn(private,payload)
        self.assertIn('2345.67',payload); self.cloud.assert_not_called(); self.provider.assert_not_called()
        self.assertEqual(list(type(self.investment).objects.values()),before)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(source['url']).status_code,404)

    def test_evidence_changes_during_inference_reject_the_entire_answer(self):
        contents=Path(self.document.uploaded_file.path).read_bytes()
        changes=[lambda:self.confirm(['current_value'],revoke=True),lambda:self.document.linked_investments.clear(),
            lambda:Path(self.document.uploaded_file.path).unlink(),
            lambda:Path(self.document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-REPLACED'),
            lambda:InvestmentImportDocument.objects.filter(pk=self.document.pk).update(user=self.other)]
        for change in changes:
            with self.subTest(change=changes.index(change)),transaction.atomic():
                self.confirm()
                def changing(*args,**kwargs): change(); return 'SYNTHETIC-STALE-ANSWER'
                self.local.reason.side_effect=changing
                with self.assertRaises(MemoryConflict): self.answer()
                transaction.set_rollback(True)
            Path(self.document.uploaded_file.path).write_bytes(contents)

    def test_revoked_or_lost_document_does_not_discard_current_register_or_retain_verified_label(self):
        self.confirm(); self.confirm(['current_value'],revoke=True)
        source=self.source()
        self.assertEqual(source['data']['amounts']['current_value']['amount'],'2345.67')
        self.assertNotEqual(source['data']['amounts']['current_value']['evidence_status'],'owner_confirmed_document_field')
        Path(self.document.uploaded_file.path).unlink(); source=self.source()
        self.assertTrue(all(not value['source_document_ids'] for value in source['data']['amounts'].values()))
        self.assertEqual(source['data']['document_sources'][0]['source_status'],'source_unavailable')
        self.assertEqual(source['data']['verification'],'imported_record_not_field_verified')

    def test_explicit_cloud_consent_is_refused_even_for_confirmed_financial_fields(self):
        self.confirm()
        with self.assertRaises(PermissionDenied): self.answer(cloud_consent=True)
        self.local.reason.assert_not_called(); self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_document_review_budget_is_bounded_and_foreign_sources_fail_closed(self):
        for index in range(5):
            document=InvestmentImportDocument.objects.create(user=self.owner,file_name=f'synthetic-{index}.pdf')
            document.linked_investments.add(self.investment)
        source=self.source(); self.assertFalse(source['available'])
        self.assertEqual(source['data']['verification'],'source_review_limit')
        self.assertTrue(all(value['amount'] is None for value in source['data']['amounts'].values()))
        InvestmentImportDocument.objects.filter(pk=self.document.pk).update(user=self.other)
        with self.assertRaises(Http404): self.source()

    def test_a_newer_confirmed_value_cannot_certify_an_older_canonical_snapshot(self):
        from apps.investments.services import document_evidence as service
        original=service.evidence
        def changed(*args,**kwargs):
            type(self.investment).objects.filter(pk=self.investment.pk).update(current_value='3456.78')
            with patch.object(service,'evidence',original): self.confirm()
            return original(*args,**kwargs)
        with patch.object(service,'evidence',side_effect=changed): source=self.source()
        value=source['data']['amounts']['current_value']
        self.assertEqual(value['amount'],'2345.67')
        self.assertNotEqual(value['evidence_status'],'owner_confirmed_document_field')
        self.assertEqual(value['source_document_ids'],[])
