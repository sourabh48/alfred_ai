"""Opt-in real local embeddings, fictional memories only; outside mocked release labels."""
import json
import os
from pathlib import Path
from unittest import skipUnless

from django.conf import settings
from django.test import TestCase

from apps.ml_engine.services.local_embeddings import OllamaEmbeddings
from apps.ml_engine.services.memory_learning import MemoryLearning
from apps.ml_engine.services.persistent_memory import MemoryStore
from tests import test_memory_learning as fixtures


@skipUnless(os.environ.get('ALFRED_RUN_OLLAMA_GROUNDING')=='true','Explicit synthetic real-local acceptance required.')
class MemoryEvaluationOllamaAcceptance(TestCase):
    def test_real_local_multi_case_quality_and_reopened_encrypted_index(self):
        fixtures.MemoryLearningTests.setUp(self)
        self.assertFalse(settings.ALFRED_MEMORY_OPENAI_AUTHORIZED)
        self.assertFalse(settings.ALFRED_MEMORY_CLOUD_AUTHORIZED)
        self.assertFalse(settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED)
        store=MemoryStore(self.root/'real-vault',embedder=OllamaEmbeddings()); learning=MemoryLearning(store)
        def save(user,text):
            return store.save_verified(user,{'statement':text},{'source':'Fictional owner-reviewed evaluation fixture'},verified=True)
        old=save(self.alice,'A fictional traveler prefers city museums and art galleries.')
        current=learning.revise(self.alice,[old],{'statement':'A fictional traveler prefers quiet alpine hikes and mountain trails.'},verified=True)
        coast=save(self.alice,'A fictional traveler prefers coastal vacations and beach walks.')
        contrary=save(self.alice,'A fictional traveler avoids coastal vacations and beach walks.')
        deleted=save(self.alice,'A fictional rider schedules motorcycle service at an annual interval.'); store.delete_memory(self.alice,deleted)
        foreign=save(self.bob,'A different fictional traveler studies neutron stars and supernovae.')
        fresh=MemoryStore(self.root/'real-vault',embedder=OllamaEmbeddings())
        cases=[dict(query='quiet alpine hiking and mountain trails',expected_ids=[current]),
            dict(query='coastal vacations and beach walks',expected_ids=[coast,contrary]),
            dict(query='How are neutron stars formed in a supernova?',expected_ids=[])]
        before=fresh.list_memories(self.alice)
        report=MemoryLearning(fresh).evaluate(self.alice,cases,min_score=.45)
        measurement={key:value for key,value in report.items() if key!='per_case'}
        measurement['per_case']=[{key:value for key,value in case.items() if key not in ('citations','expected_ids')} for case in report['per_case']]
        measurement['embedding_model']=fresh.embedder.model
        Path(os.environ['ALFRED_DIAGNOSTIC_OUTPUT']).with_name('quality.json').write_text(json.dumps(measurement,indent=2),encoding='utf-8')
        self.assertEqual(report['citation_correctness'],1)
        self.assertGreaterEqual(report['recall'],.5)
        self.assertEqual(fresh.list_memories(self.alice),before)
        for identity in (old,deleted,foreign): self.assertNotIn(identity,json.dumps(report))
        self.assertEqual(fresh.list_memories(self.bob)[0]['id'],foreign)
        self.assertFalse(report['generated_hypotheses_are_facts'])
