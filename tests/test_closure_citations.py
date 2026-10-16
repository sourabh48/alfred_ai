"""Owner-only verified closure records and retained source liveness; synthetic files."""
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings

from apps.loans.models import Loan, LoanClosureDocument
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer, source_context
from apps.ml_engine.services.persistent_memory import MemoryStore, MemoryConflict
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests.test_persistent_memory import SyntheticEmbeddings


class ClosureCitationTests(TestCase):
    def setUp(self):
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-closure-citation-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media',ALFRED_MEMORY_DIR=str(root/'vault'),
            ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits'),ALFRED_MEMORY_OPENAI_AUTHORIZED=False,
            ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_SYNC_PROVIDER='',ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False))
        self.enterContext(_offline_fixture_patches())
        self.owner=get_user_model().objects.create_user(username='closure-citation-owner')
        self.other=get_user_model().objects.create_user(username='closure-citation-other')
        self.loan=Loan.objects.create(user=self.owner,principal='1000.01',emi='100.01',interest_rate=5,tenure_months=12,start_date=date(2026,1,1))
        self.document=LoanClosureDocument.objects.create(loan=self.loan,verification_status='verified',closure_amount='123.45',
            closure_date=date(2026,9,1),file_name=r'F:\synthetic\PRIVATE-TOKEN.pdf',extracted_text='SYNTHETIC-OCR-NEVER-PROMPT',
            uploaded_file=SimpleUploadedFile('synthetic-closure.pdf',b'%PDF-synthetic-closure-only'))
        self.local=Mock(); self.local.reason.return_value='Review the supplied verified metadata and source limitations.'
        self.store=MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=SyntheticEmbeddings())
        self.client.force_login(self.owner)

    def source(self):
        return source_context(self.owner,'documents',document_id=self.document.pk)[0]

    def answer(self):
        return hybrid_answer(self.store,self.owner,'Explain this closure evidence',scope='documents',document_id=self.document.pk,local=self.local)

    def test_exact_owned_citation_file_download_and_minimal_local_prompt(self):
        source=self.source(); self.assertEqual(source['source_file_status'],'available')
        self.assertEqual(source['record_id'],self.document.pk); self.assertEqual(len(source['revision']),64)
        for url in (source['url'],f'/api/ai/closure-evidence/{self.document.pk}/',source['source_download_url']):
            response=self.client.get(url); self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control']); response.close()
        result=self.answer(); self.assertEqual(result['sources'][0]['data']['amounts']['closure_amount']['amount'],'123.45')
        for private in ('PRIVATE-TOKEN','SYNTHETIC-OCR',source['url'],source['source_download_url']):
            self.assertNotIn(private,str(self.local.reason.call_args))

    def test_foreign_anonymous_and_withdrawn_citation_never_disclose(self):
        source=self.source()
        for actor in (None,self.other):
            client=Client()
            if actor: client.force_login(actor)
            for url in (source['url'],source['source_download_url'],f'/api/ai/closure-evidence/{self.document.pk}/'):
                self.assertIn(client.get(url).status_code,(302,401,403,404))
        self.document.verification_status='rejected'; self.document.save()
        self.assertEqual(self.client.get(source['url']).status_code,404)
        self.assertEqual(self.client.get(f'/api/ai/closure-evidence/{self.document.pk}/').status_code,404)

    def test_missing_replaced_and_in_flight_source_file_reject_stale_answers(self):
        original=self.source()['revision']
        Path(self.document.uploaded_file.path).write_bytes(b'%PDF-synthetic-replaced-source')
        self.assertNotEqual(self.source()['revision'],original)
        def removing(payload,**kwargs):
            Path(self.document.uploaded_file.path).unlink(); return 'SYNTHETIC-STALE-ANSWER'
        self.local.reason.side_effect=removing
        with self.assertRaises(MemoryConflict): self.answer()
        self.assertEqual(self.client.get(f'/documents/loan-closures/{self.document.pk}/').status_code,409)

    def test_legacy_metadata_without_file_is_explicit_and_financial_rows_unchanged(self):
        self.document.uploaded_file=''; self.document.save(update_fields=['uploaded_file'])
        before=[list(model.objects.values()) for model in (Loan,LoanClosureDocument)]
        source=self.source(); self.assertEqual(source['source_file_status'],'not_retained')
        self.assertIsNone(source['source_download_url'])
        self.assertContains(self.client.get(source['url']),'Original file is not retained')
        self.answer(); self.assertEqual([list(model.objects.values()) for model in (Loan,LoanClosureDocument)],before)
        self.assertIsNone(source['data']['amounts']['closure_amount']['currency'])

    @override_settings(ALFRED_UPLOAD_FILE_BYTES=4)
    def test_source_resource_limit_returns_safe_413_without_parser_diagnostics(self):
        response=self.client.get(f'/documents/loan-closures/{self.document.pk}/')
        self.assertEqual(response.status_code,413)
        self.assertNotIn(str(settings.MEDIA_ROOT),response.content.decode())
        self.assertNotIn('PRIVATE-TOKEN',response.content.decode())
