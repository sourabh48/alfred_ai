"""Opt-in bounded real-local acceptance; deliberately outside the mocked release labels."""
import os
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase

from apps.ml_engine.services.hybrid_intelligence import hybrid_answer, OllamaReasoner
from apps.ml_engine.services.local_embeddings import OllamaEmbeddings
from apps.ml_engine.services.persistent_memory import MemoryStore
from tests import test_canonical_evidence as fixtures


@skipUnless(os.environ.get('ALFRED_RUN_OLLAMA_GROUNDING')=='true','Explicit synthetic real-local acceptance required.')
class CanonicalOllamaAcceptance(TestCase):
    def test_real_local_explicit_reviewed_current_value_question(self):
        from tests.test_financial_source_selection import FinancialSourceSelectionTests
        FinancialSourceSelectionTests.setUp(self)
        document,page=FinancialSourceSelectionTests.document_question_fixture(self,count=2)
        result=hybrid_answer(None,self.owner,'Show current value',scope='financial_document',record_type='investment',
            document_id=document.pk,source_catalog=page['catalog_token'],
            selected_records=[dict(id=item['record_id'],revision=item['revision']) for item in page['items']],local=OllamaReasoner())
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        self.assertEqual([item['data']['amounts']['current_value']['amount'] for item in result['sources']],['2345.67','120.05'])
        self.assertEqual([item['url'] for item in result['sources']],[item['url'] for item in page['items']])
        self.assertTrue(all(item['data']['amounts']['current_value']['currency'] is None for item in result['sources']))
        self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_real_local_bounded_records_from_one_reviewed_document(self):
        from tests.test_financial_source_selection import FinancialSourceSelectionTests
        FinancialSourceSelectionTests.setUp(self)
        document,page=FinancialSourceSelectionTests.document_question_fixture(self,count=2)
        result=hybrid_answer(None,self.owner,'Explain selected records',scope='financial_document',
            record_type='investment',document_id=document.pk,source_catalog=page['catalog_token'],
            selected_records=[dict(id=item['record_id'],revision=item['revision']) for item in page['items']],local=OllamaReasoner())
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        self.assertEqual(len(result['sources']),2); self.assertEqual(result['context_omitted'],0)
        self.assertEqual(result['sources'][0]['data']['amounts']['current_value']['amount'],'2345.67')
        self.assertEqual(result['sources'][1]['data']['amounts']['current_value']['amount'],'120.05')
        for source,item in zip(result['sources'],page['items']):
            self.assertEqual(source['url'],item['url'])
            self.assertTrue(all(value['currency'] is None for value in source['data']['amounts'].values()))
        self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_real_local_explicit_selection_beyond_five_documents(self):
        from tests import test_financial_source_selection as selection_fixtures
        from apps.ml_engine.services.canonical_evidence import document_page
        fixtures.CanonicalEvidenceTests.setUp(self)
        selection_fixtures.FinancialSourceSelectionTests.documents(self,'loan')
        first=document_page(self.owner,'loan',self.loan.pk)
        second=document_page(self.owner,'loan',self.loan.pk,cursor=first['next_cursor'])
        chosen=second['items'][-1]
        store=MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=OllamaEmbeddings())
        with patch('apps.ml_engine.services.hybrid_intelligence.reason_with_memory',side_effect=AssertionError('No external reasoning')):
            result=hybrid_answer(store,self.owner,'Explain this record',scope='financial_records',
                record_type='loan',record_id=self.loan.pk,local=OllamaReasoner(),
                selected_documents=[dict(id=chosen['document_id'],revision=chosen['revision'])],source_catalog=first['catalog_token'])
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        source=result['sources'][0]
        self.assertEqual(source['url'],chosen['url'])
        self.assertEqual(source['data']['document_selection']['linked_count'],7)
        self.assertEqual(source['data']['document_selection']['selected_count'],1)
        self.assertEqual(source['data']['amounts']['emi']['amount'],'100.01')
        self.assertIsNone(source['data']['amounts']['emi']['currency'])

    def test_real_local_inference_from_owner_confirmed_loan_fields(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.loans.models import LoanImportDocument
        from apps.loans.services.document_evidence import capture_import, evidence, review, FIELDS
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.assertFalse(settings.ALFRED_MEMORY_OPENAI_AUTHORIZED)
        self.assertFalse(settings.ALFRED_MEMORY_CLOUD_AUTHORIZED)
        self.assertFalse(settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED)
        document=LoanImportDocument.objects.create(user=self.owner,file_name='synthetic-loan.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC-LOAN'),parser_status='parsed')
        document.linked_loans.add(self.loan); capture_import(document,[self.loan])
        detail=evidence(self.owner,document.pk,self.loan.pk)
        review(self.owner,document.pk,self.loan.pk,revision=detail['revision'],fields=list(FIELDS),confirm=True)
        store=MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=OllamaEmbeddings())
        with patch('apps.ml_engine.services.hybrid_intelligence.reason_with_memory',side_effect=AssertionError('No external reasoning')):
            result=hybrid_answer(store,self.owner,'Explain this record',scope='financial_records',
                record_type='loan',record_id=self.loan.pk,local=OllamaReasoner())
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        source=next(item for item in result['sources'] if item['ref']==f'canonical-loan-{self.loan.pk}')
        self.assertEqual(source['data']['amounts']['emi']['amount'],'100.01')
        self.assertIsNone(source['data']['amounts']['emi']['currency'])
        self.assertEqual(source['data']['amounts']['emi']['evidence_status'],'owner_confirmed_document_field')
        self.assertNotEqual(source['data']['amounts']['total_paid']['evidence_status'],'owner_confirmed_document_field')
        self.assertEqual(source['url'],detail['citation_url'])

    def test_real_local_inference_from_owner_confirmed_investment_fields(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.investments.models import InvestmentImportDocument
        from apps.investments.services.document_evidence import capture_import, evidence, review, FIELDS
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.assertFalse(settings.ALFRED_MEMORY_OPENAI_AUTHORIZED)
        self.assertFalse(settings.ALFRED_MEMORY_CLOUD_AUTHORIZED)
        self.assertFalse(settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED)
        document=InvestmentImportDocument.objects.create(user=self.owner,file_name='synthetic-portfolio.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf',b'%PDF-SYNTHETIC-INVESTMENT'),parser_status='parsed')
        document.linked_investments.add(self.investment)
        capture_import(document,[self.investment])
        detail=evidence(self.owner,document.pk,self.investment.pk)
        review(self.owner,document.pk,self.investment.pk,revision=detail['revision'],fields=list(FIELDS),confirm=True)
        store=MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=OllamaEmbeddings())
        with patch('apps.ml_engine.services.hybrid_intelligence.reason_with_memory',side_effect=AssertionError('No external reasoning')):
            result=hybrid_answer(store,self.owner,'Explain this record',scope='financial_records',
                record_type='investment',record_id=self.investment.pk,local=OllamaReasoner())
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        source=next(item for item in result['sources'] if item['ref']==f'canonical-investment-{self.investment.pk}')
        self.assertEqual(source['data']['amounts']['current_value']['amount'],'2345.67')
        self.assertIsNone(source['data']['amounts']['current_value']['currency'])
        self.assertEqual(source['data']['amounts']['current_value']['evidence_status'],'owner_confirmed_document_field')
        self.assertEqual(source['url'],detail['citation_url'])

    def test_real_local_inference_and_encrypted_memory_reopen_with_synthetic_record(self):
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.assertFalse(settings.ALFRED_MEMORY_OPENAI_AUTHORIZED)
        self.assertFalse(settings.ALFRED_MEMORY_CLOUD_AUTHORIZED)
        self.assertFalse(settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED)
        store=MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=OllamaEmbeddings())
        identity=store.save_verified(self.owner,{'statement':'Synthetic practice record only; not a real purchase.'},
            {'source':'explicit synthetic owner verification'},sensitivity='sensitive',verified=True)
        with patch('apps.ml_engine.services.hybrid_intelligence.reason_with_memory',side_effect=AssertionError('No external reasoning')):
            result=hybrid_answer(store,self.owner,'Explain this record',scope='financial_records',
                record_type='expense',record_id=self.expense.pk,local=OllamaReasoner())
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['financial_authority'])
        source=next(item for item in result['sources'] if item['ref']==f'canonical-expense-{self.expense.pk}')
        self.assertEqual(source['data']['amounts']['amount']['amount'],'12.34')
        self.assertIsNone(source['data']['amounts']['amount']['currency'])
        self.assertTrue(result['answer'])
        fresh=MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=OllamaEmbeddings())
        self.assertEqual(fresh.list_memories(self.owner)[0]['id'],identity)
        self.assertEqual(fresh.retrieve(self.other,'Explain this record'),[])
