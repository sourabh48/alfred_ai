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
