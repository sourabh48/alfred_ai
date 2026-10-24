"""Explicit synthetic real-local evaluation; never part of mocked CI or private-data tests."""
import json
import os
from pathlib import Path
import time
from unittest import skipUnless

from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.ml_engine.services.document_questions import DocumentQuestionReasoner, answer_question
from tests import test_document_corpus as fixtures


@skipUnless(os.environ.get('ALFRED_RUN_DOCUMENT_QUESTIONS') == 'true', 'Explicit synthetic real-local evaluation required.')
class DocumentQuestionsOllamaTests(TestCase):
    make_document = fixtures.DocumentCorpusTests.make_document

    def setUp(self):
        fixtures.DocumentCorpusTests.setUp(self)
        self.ids=[]
        for text in ('Exit load applies for thirty days. No guaranteed returns.',):
            self.ids.append(self.corpus.upload(self.owner,SimpleUploadedFile('Synthetic policy.txt',text.encode()),consent=True,days=1)['document']['id'])

    def evaluate(self, question, expected, keywords='exit load'):
        outer=self
        class Measured(DocumentQuestionReasoner):
            def _request(self, method, path, payload=None, **kwargs):
                result=super()._request(method,path,payload,**kwargs)
                if path=='/api/chat':
                    outer.metrics={key:result.get(key) for key in ('model','done','done_reason','load_duration',
                        'prompt_eval_count','prompt_eval_duration','eval_count','eval_duration','total_duration')}
                    outer.model_output=result.get('message',{}).get('content')
                return result
        started=time.monotonic(); receipt=dict(case=self._testMethodName,status='RUNNING',expected=expected)
        try:
            result=answer_question(self.corpus,self.owner,self.ids,question,keywords,local=Measured())
            receipt.update(actual=result['status'],result_documents=[hit['document_name'] for hit in result['results']])
            self.assertEqual(result['status'],expected)
            self.assertFalse(result['financial_authority'])
            self.assertTrue(all(hit['id'] in self.ids for hit in result['results']))
            receipt['status']='PASS'
        except BaseException:
            receipt['status']='FAIL'
            raise
        finally:
            receipt.update(elapsed_seconds=round(time.monotonic()-started,3),metrics=getattr(self,'metrics',{}),
                model_output=getattr(self,'model_output',None))
            directory=Path(os.environ['ALFRED_DOCUMENT_QUESTION_EVIDENCE']); directory.mkdir(parents=True,exist_ok=True)
            (directory/(self._testMethodName+'.json')).write_text(json.dumps(receipt,indent=2))

    def test_real_positive_exact_excerpt(self):
        self.evaluate('For how long does the exit load apply?','excerpt_evidence')

    def test_real_missing_evidence_abstention(self):
        self.evaluate('Which interest rate is guaranteed?','insufficient_evidence')

    def test_real_conflicting_selected_policies(self):
        self.ids.append(self.corpus.upload(self.owner,SimpleUploadedFile('Synthetic conflicting policy.txt',
            b'Exit load applies for ninety days. This conflicts with the thirty-day policy.'),consent=True,days=1)['document']['id'])
        self.evaluate('For how long does the exit load apply in these policies?','conflicting_evidence')

    def test_real_statement_period(self):
        self.ids=[self.corpus.upload(self.owner,SimpleUploadedFile('Synthetic statement.txt',
            b'Statement period: 2026-09-01 to 2026-09-30. This is an unverified extraction.'),consent=True,days=1)['document']['id']]
        self.evaluate('What is the statement period?','excerpt_evidence','statement period')

    def test_real_loan_missing_penalty(self):
        self.ids=[self.corpus.upload(self.owner,SimpleUploadedFile('Synthetic loan.txt',
            b'This loan permits prepayment. The prepayment penalty is not specified.'),consent=True,days=1)['document']['id']]
        self.evaluate('How much is the prepayment penalty?','insufficient_evidence','prepayment penalty')

    def test_real_investment_advice_abstains(self):
        self.evaluate('Should I invest all my emergency savings in this product?','insufficient_evidence')
