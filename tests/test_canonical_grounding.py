"""Local assistant canonical-source races, privacy and compatibility, synthetic only."""
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, Client, override_settings

from apps.budgets.models import Budget
from apps.expenses.models import Expense, BankAccount
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.investments.models import Investment
from apps.loans.models import Loan
from apps.ml_engine.services.canonical_evidence import record_source
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore, MemoryConflict
from tests import test_canonical_evidence as fixtures
from tests.test_persistent_memory import SyntheticEmbeddings


class CanonicalGroundingTests(TestCase):
    def setUp(self):
        fixtures.CanonicalEvidenceTests.setUp(self)
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.store=MemoryStore(settings.ALFRED_MEMORY_DIR)
        self.local=Mock(); self.local.reason.return_value='This is a recorded value, not independent authentication. Review the source and limitations.'
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=self.local))
        self.cloud=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reason_with_memory',side_effect=AssertionError('No cloud')))
        self.provider=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reasoning_provider',side_effect=AssertionError('No provider')))

    def answer(self, kind='expense', query='Explain this record', **changes):
        return hybrid_answer(self.store,self.owner,query,**(dict(scope='financial_records',record_type=kind,
            record_id=self.rows[kind].pk,local=self.local)|changes))

    def post(self, **changes):
        return self.client.post('/api/ai/personal-insights/',dict(query='Explain this record',scope='financial_records',
            record_type='expense',record_id=self.expense.pk)|changes,content_type='application/json')

    def test_each_domain_has_current_typed_provenance_and_local_only_context(self):
        for kind,row in self.rows.items():
            with self.subTest(kind=kind):
                result=self.answer(kind); self.assertEqual(result['provider'],'ollama')
                self.assertEqual(result['sources'][0],record_source(self.owner,kind,row.pk))
                self.assertFalse(result['financial_authority'])
                payload=str(self.local.reason.call_args.args[0])
                for secret in ('SYNTHETIC-NO-MODEL','SYNTHETIC-NAME','SYNTHETIC-NO-EXTERNAL','SYNTHETIC-ACCOUNT','/ai/financial-records/'):
                    self.assertNotIn(secret,payload)
                self.assertLessEqual(len(payload.encode()),4096)
        self.cloud.assert_not_called(); self.provider.assert_not_called()
        self.assertEqual(self.store.list_memories(self.owner),[])

    def test_unsupported_questions_and_conflicting_sources_never_retrieve_or_infer(self):
        with patch.object(self.store,'retrieve',side_effect=AssertionError('No unsupported inference')):
            for query in ('How much will stocks be worth tomorrow?','Convert this record to INR','Show total records','What is the weather?'):
                result=self.answer(query=query); self.assertEqual(result['grounding'],'insufficient_evidence')
                self.assertEqual(result['provider'],'local_evidence')
            Budget.objects.create(user=self.owner,month='2026-09',base_budget='999.99',inflation_adjusted='999.99')
            self.assertEqual(self.answer('budget')['provider'],'local_evidence')
            Loan.objects.filter(pk=self.loan.pk).update(verification_status='estimated')
            self.assertEqual(self.answer('loan')['provider'],'local_evidence')
        self.local.reason.assert_not_called()

    def test_currency_figures_never_come_from_model_and_amount_precision_is_preserved(self):
        self.local.reason.return_value='The amount is INR 99999999.99.'
        result=self.answer('investment')
        self.assertTrue(result['narrative_withheld']); self.assertNotIn('99999999',result['answer'])
        value=result['sources'][0]['data']['amounts']['current_value']
        self.assertEqual(value['amount'],'2345.67'); self.assertIsNone(value['currency'])
        for kind,field,new in (('expense','amount','56.78'),('budget','base_budget','234.56'),
                              ('loan','emi','123.45'),('investment','current_value','4567.89')):
            row=self.rows[kind]; type(row).objects.filter(pk=row.pk).update(**{field:new})
            self.assertEqual(self.answer(kind)['sources'][0]['data']['amounts'][field]['amount'],new)

    def test_each_record_change_delete_and_owner_reassignment_rejects_in_flight_answer(self):
        fields={'expense':'amount','budget':'spent','loan':'emi','investment':'current_value','baseline':'monthly_income'}
        for kind,row in self.rows.items():
            for action in ('edit','delete','owner'):
                if kind=='baseline' and action=='owner': continue
                with self.subTest(kind=kind,action=action),transaction.atomic():
                    def changing(payload,**kwargs):
                        selected=type(row).objects.filter(pk=row.pk)
                        if action=='edit': selected.update(**{fields[kind]:'789.01'})
                        elif action=='delete': selected.delete()
                        else: selected.update(user=self.other)
                        return 'SYNTHETIC-STALE-ANSWER'
                    self.local.reason.side_effect=changing
                    with self.assertRaises(MemoryConflict): self.answer(kind)
                    transaction.set_rollback(True)

    def test_new_conflicting_budget_during_inference_discards_answer(self):
        def conflicting(payload,**kwargs):
            Budget.objects.create(user=self.owner,month='2026-09',base_budget='999.99',inflation_adjusted='999.99')
            return 'SYNTHETIC-STALE-ANSWER'
        self.local.reason.side_effect=conflicting
        with self.assertRaises(MemoryConflict): self.answer('budget')

    def test_mismatched_question_domain_abstains_before_retrieval_or_inference(self):
        cases=(('expense','Show my loan status'),('budget','Show my investment'),
            ('loan','Show my expense'),('investment','Show my EMI'),('baseline','Review my loan'))
        for kind,question in cases:
            with self.subTest(kind=kind),patch.object(self.store,'retrieve',side_effect=AssertionError('No mismatched context')):
                result=self.answer(kind,query=question)
                self.assertEqual(result['provider'],'local_evidence')
                self.assertEqual(result['grounding'],'insufficient_evidence')
        self.local.reason.assert_not_called(); self.cloud.assert_not_called(); self.provider.assert_not_called()

    def test_cloud_consent_and_outage_never_exfiltrate_private_sources(self):
        self.assertEqual(self.post(cloud_consent=True,query_sensitivity='public').status_code,403)
        self.local.reason.assert_not_called()
        self.local.reason.side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE F:/synthetic/financial.pdf')
        response=self.post(query_sensitivity='public'); self.assertEqual(response.status_code,503)
        self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())
        self.cloud.assert_not_called(); self.provider.assert_not_called()
        self.assertFalse(settings.ALFRED_MEMORY_OPENAI_AUTHORIZED); self.assertFalse(settings.ALFRED_MEMORY_CLOUD_AUTHORIZED)

    def test_owner_session_csrf_and_strict_selection_validation(self):
        self.client.force_login(self.other); self.assertEqual(self.post().status_code,404)
        self.client.force_login(self.owner)
        for change in ({'record_type':'user'},{'record_id':True},{'record_id':None},{'scope':'general'},
                       {'document_id':1},{'transaction_id':1},{'owner':self.other.pk}):
            self.assertEqual(self.post(**change).status_code,400)
        csrf=Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post('/api/ai/personal-insights/',{'query':'Explain this record'}).status_code,403)
        response=self.post(); self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control'])

    def test_readonly_hybrid_keeps_financial_baseline_and_fingerprints_unchanged(self):
        models=(Expense,BankAccount,Budget,Loan,Investment,get_user_model())
        before=[list(model.objects.order_by('pk').values()) for model in models]
        baseline=resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts']
        for kind in self.rows: self.answer(kind)
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)
        self.assertEqual(resolve_canonical_financial_baseline(self.owner,fresh=True)['decimal_amounts'],baseline)
        self.assertEqual(self.store.list_memories(self.owner),[])

    def test_bank_selector_preserves_confirmation_revocation_and_original_snapshot(self):
        fixtures.CanonicalEvidenceTests.test_bank_record_selector_cannot_bypass_receipt_review(self)
        from apps.expenses.models import StatementTransactionEvidence
        row=Expense.objects.filter(source='bank_statement',user=self.owner).get()
        original=StatementTransactionEvidence.objects.get(expense=row).source_values.copy()
        result=self.answer(record_id=row.pk)
        self.assertEqual(result['provider'],'local_evidence'); self.local.reason.assert_not_called()
        self.assertEqual(StatementTransactionEvidence.objects.get(expense=row).source_values,original)

    def test_history_retains_only_local_hypothesis_references_and_warning_not_saved(self):
        from apps.ml_engine.services.conversation_history import ConversationHistory
        self.assertFalse(settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED)
        with override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True):
            history=ConversationHistory(self.store); history.configure(self.owner,enabled=True,consent=True,days=1)
            record=history.create(self.owner,'Synthetic canonical only')
            payload=dict(conversation_id=record['id'],conversation_revision=0,request_id=uuid4().hex)
            response=self.post(**payload); self.assertEqual(response.status_code,200)
            turn=history.get(self.owner,record['id'])['turns'][0]
            self.assertEqual(turn['record_type'],'expense'); self.assertEqual(turn['record_id'],self.expense.pk)
            self.assertNotIn('data',turn['sources'][0]); self.assertNotIn('12.34',str(turn))
            self.assertTrue(self.post(**payload).json()['historical'])
            self.assertEqual(self.post(**(payload|{'record_type':'loan','record_id':self.loan.pk})).status_code,409)
            record=history.create(self.owner,'Synthetic unsupported')
            payload.update(conversation_id=record['id'],request_id=uuid4().hex,query='Convert record to INR')
            self.assertEqual(self.post(**payload).status_code,200)
            self.assertEqual(history.get(self.owner,record['id'])['turns'],[])
            history.configure(self.owner,enabled=False)
