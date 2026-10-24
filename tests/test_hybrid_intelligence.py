"""Synthetic Ollama-first, owner, canonical tool and fallback boundaries."""
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.utils import timezone

from apps.ml_engine.services.persistent_memory import MemoryStore, MemoryConflict, _owner
from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from apps.ml_engine.services.hybrid_intelligence import hybrid_answer, OllamaReasoner, source_context
from apps.ml_engine.services.memory_reasoning import MockReasoner, configure_reasoning, ReasoningBudgetExceeded
from tests.test_persistent_memory import SyntheticEmbeddings


class HybridIntelligenceTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-hybrid-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.root/'vault'),ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'limits'),
            ALFRED_MEMORY_MOCK_REASONING=False,ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_RELEVANCE_MIN_SCORE=0.20))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.store=MemoryStore(self.root/'vault'); self.alice=get_user_model().objects.create_user(username='synthetic-hybrid-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-hybrid-bob')
        self.local=Mock(); self.local.reason.return_value='Synthetic AI hypothesis. Verify recommendations.'
        self.cloud=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reasoning_provider',return_value=MockReasoner()))

    def save(self,user=None,sensitivity='sensitive'):
        return self.store.save_verified(user or self.alice,{'statement':'SYNTHETIC-PRIVATE mountain hiking'},
            {'source':'synthetic owner review'},verified=True,sensitivity=sensitivity)

    def answer(self,query='mountain',**kwargs):
        return hybrid_answer(self.store,self.alice,query,local=self.local,**kwargs)

    def test_local_first_never_contacts_cloud_and_does_not_auto_save_hypotheses(self):
        identity=self.save(); self.save(self.bob)
        result=self.answer(cloud_consent=True,query_sensitivity='public')
        self.cloud.assert_not_called(); self.assertFalse(result['financial_authority'])
        self.assertEqual(result['provider'],'ollama'); self.assertEqual(result['sources'][0]['ref'],identity)
        self.assertEqual(result['classification'],'ai_generated_hypothesis')
        self.assertEqual(len(self.store.list_memories(self.alice)),1)
        payload=self.local.reason.call_args.args[0]
        self.assertEqual(len(payload['sources']),1); self.assertNotIn(_owner(self.bob),str(payload))

    def test_unrelated_query_abstains_from_memory_and_bounds_context(self):
        self.save(); result=self.answer('coast')
        self.assertEqual(result['sources'],[])
        self.store.save_verified(self.alice,{'statement':'mountain '+'x'*5000},{'source':'synthetic large'},verified=True)
        result=self.answer()
        self.assertEqual(result['context_omitted'],1)
        self.assertLessEqual(len(str(self.local.reason.call_args.args[0]).encode()),4096)

    def test_no_consent_private_query_and_domain_context_never_fall_back(self):
        self.local.reason.side_effect=EmbeddingUnavailable('synthetic local failure')
        for kwargs in ({},{'cloud_consent':True},{'cloud_consent':True,'query_sensitivity':'public','scope':'travel'}):
            with self.assertRaises(EmbeddingUnavailable): self.answer(**kwargs)
        self.cloud.assert_not_called()

    def test_public_fallback_keeps_existing_consent_filter_and_budget(self):
        identity=self.save(sensitivity='public'); self.local.reason.side_effect=EmbeddingUnavailable('synthetic local failure')
        result=self.answer(cloud_consent=True,query_sensitivity='public')
        self.assertEqual(result['provider'],'mock'); self.assertEqual(result['sources'][0]['ref'],identity)
        with self.store._transaction() as db:
            self.assertGreater(self.store._sync_state(db,_owner(self.alice))['reasoning']['reserved'],0)
        with self.assertRaises(PermissionError): self.answer('loan balance',cloud_consent=True,query_sensitivity='public')

    def test_embedding_outage_preserves_local_first_and_safe_observability(self):
        identity=self.save()
        with patch.object(self.store,'retrieve',side_effect=EmbeddingUnavailable('SYNTHETIC-SECRET F:\\synthetic\\private.pdf')), self.assertLogs('apps.ml_engine.services.hybrid_intelligence',level='ERROR') as logs:
            result=self.answer()
        self.assertEqual(result['provider'],'ollama'); self.assertFalse(result['memory_retrieval_available'])
        self.assertEqual(result['sources'],[]); self.assertTrue(result['retrieval_error']['error_id'])
        self.assertIn('EmbeddingUnavailable',str(logs.output)); self.assertNotIn('SYNTHETIC-SECRET',str(logs.output)+str(result))
        self.cloud.assert_not_called(); self.assertEqual(self.store.list_memories(self.alice)[0]['id'],identity)

    def test_full_local_outage_only_sends_explicit_public_query_without_memories(self):
        self.save(); self.local.reason.side_effect=EmbeddingUnavailable('synthetic server offline')
        provider=Mock(); provider.name='mock'; provider.reason.return_value='Synthetic public hypothesis'
        self.cloud.return_value=provider
        with patch.object(self.store,'retrieve',side_effect=EmbeddingUnavailable('synthetic embedding offline')):
            with self.assertRaises(EmbeddingUnavailable): self.answer()
            self.cloud.assert_not_called()
            result=self.answer(cloud_consent=True,query_sensitivity='public')
            self.assertEqual(provider.reason.call_args.args[0],{'query':'mountain','memories':[]})
            self.assertEqual(result['grounding'],'public_query_only'); self.assertFalse(result['memory_retrieval_available'])
            with self.assertRaises(PermissionError): self.answer('loan balance',cloud_consent=True,query_sensitivity='public')
        with patch.object(self.store,'retrieve',side_effect=RuntimeError('synthetic storage failure')):
            with self.assertRaises(RuntimeError): self.answer(cloud_consent=True,query_sensitivity='public')

    def test_sensitive_memory_cannot_leave_device_even_when_query_is_marked_public(self):
        self.save(); self.local.reason.side_effect=EmbeddingUnavailable('synthetic local failure')
        with self.assertRaises(PermissionError): self.answer(cloud_consent=True,query_sensitivity='public')

    def test_configured_owner_policy_and_caps_also_apply_to_mock_fallback(self):
        self.save(sensitivity='public'); self.local.reason.side_effect=EmbeddingUnavailable('synthetic unavailable')
        configure_reasoning(self.store,self.alice,enabled=True,consent=True,daily_tokens=1,daily_microusd=1000)
        with self.assertRaises(ReasoningBudgetExceeded): self.answer(cloud_consent=True,query_sensitivity='public')
        configure_reasoning(self.store,self.alice,enabled=False,daily_tokens=4096,daily_microusd=1000)
        with self.assertRaises(PermissionError): self.answer(cloud_consent=True,query_sensitivity='public')

    def test_disabled_provider_status_reads_only_local_owner_state_without_network(self):
        self.client.force_login(self.alice)
        with patch('apps.ml_engine.api.memory.memory_sync',side_effect=AssertionError('status must not connect')):
            response=self.client.get('/api/ai/memories/sync/')
        self.assertEqual(response.status_code,200); self.assertFalse(response.json()['available'])
        self.assertEqual(response.json()['provider'],'disabled'); self.assertIn('no-store',response['Cache-Control'])
        reason=self.client.get('/api/ai/memories/reason/').json()
        self.assertFalse(reason['provider_available']); self.assertNotIn('openai_key',str(reason))

    def test_deleted_context_during_local_and_cloud_inference_is_not_returned(self):
        identity=self.save()
        def deleting(*args,**kwargs):
            self.store.delete_memory(self.alice,identity); return 'synthetic withdrawn hypothesis'
        self.local.reason.side_effect=deleting
        with self.assertRaises(MemoryConflict): self.answer()
        identity=self.save(sensitivity='public'); self.local.reason.side_effect=EmbeddingUnavailable('synthetic unavailable')
        provider=MockReasoner()
        with patch.object(provider,'reason',side_effect=deleting),patch('apps.ml_engine.services.hybrid_intelligence.reasoning_provider',return_value=provider),self.assertRaises(MemoryConflict):
            self.answer(cloud_consent=True,query_sensitivity='public')
        self.assertEqual(self.store.restore_owner(self.alice),0)

    def test_canonical_finance_tool_is_owner_scoped_and_model_cannot_change_values(self):
        from apps.expenses.models import BankAccount
        from apps.family.models import FamilyAccountLink
        BankAccount.objects.create(user=self.alice,account_number='SYNTHETIC-A',current_balance=1234)
        BankAccount.objects.create(user=self.bob,account_number='SYNTHETIC-B',current_balance=9000)
        FamilyAccountLink.objects.create(created_by=self.alice,linked_user=self.bob,status='accepted',invite_code_hash='a'*64,
            invite_code_hint='SYN',expires_at=timezone.now()+timedelta(days=1),share_financial_summary=False)
        self.local.reason.return_value='Synthetic hypothesis: a fabricated balance of 999999.'
        result=self.answer('finance',scope='finance')
        facts=result['sources'][0]['data']; self.assertIsNone(facts['liquid_cash'])
        self.assertEqual(facts['amounts']['liquid_cash']['evidence_status'],'unavailable')
        self.assertIn('metric_states',facts); self.assertFalse(result['financial_authority'])
        self.assertEqual(BankAccount.objects.get(user=self.alice).current_balance,1234)
        self.assertNotIn('9000',str(self.local.reason.call_args))

    def test_document_evidence_requires_owner_verification_and_never_exposes_raw_ocr(self):
        from apps.loans.models import Loan, LoanClosureDocument
        loan=Loan.objects.create(user=self.alice,loan_type='personal',lender='synthetic',principal=1000,
            interest_rate=10,tenure_months=12,emi=100,start_date=date(2026,1,1))
        document=LoanClosureDocument.objects.create(loan=loan,file_name=r'F:\private\SYNTHETIC-TOKEN',
            extracted_text='SYNTHETIC-PRIVATE OCR',extracted_payload={'error':'SYNTHETIC-PRIVATE stack trace'},
            verification_status='verified',closure_amount=100)
        result=self.answer('closure',scope='documents',document_id=document.pk)
        self.assertEqual(result['sources'][0]['data']['closure_amount'],100)
        self.assertNotIn('SYNTHETIC-PRIVATE',str(result)+str(self.local.reason.call_args))
        self.assertNotIn('SYNTHETIC-TOKEN',str(result)+str(self.local.reason.call_args))
        with self.assertRaises(PermissionError): source_context(self.bob,'documents',document.pk)
        document.verification_status='pending'; document.save()
        with self.assertRaises(PermissionError): self.answer('closure',scope='documents',document_id=document.pk)

    def test_travel_preferences_are_read_only_and_owner_scoped(self):
        from apps.mobility.models import TravelPreferenceProfile
        TravelPreferenceProfile.objects.create(user=self.alice,preferences={'terrain':'mountains'})
        TravelPreferenceProfile.objects.create(user=self.bob,preferences={'private':'SYNTHETIC-BOB'})
        result=self.answer(scope='travel')
        self.assertEqual(result['sources'][0]['data']['preferences'],{'terrain':'mountains'})
        self.assertNotIn('SYNTHETIC-BOB',str(result))

    def test_insights_api_session_csrf_validation_safe_errors_and_no_store(self):
        url='/api/ai/personal-insights/'; data={'query':'mountain'}
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(url,data,content_type='application/json').status_code,403)
        client.force_login(self.alice); self.assertEqual(client.post(url,data,content_type='application/json').status_code,403)
        self.client.force_login(self.alice)
        for bad in (data|{'owner':self.bob.pk},data|{'cloud_consent':'true'},data|{'scope':'delete-loan'},data|{'document_id':True}):
            self.assertEqual(self.client.post(url,bad,content_type='application/json').status_code,400)
        with patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=self.local):
            response=self.client.post(url,data,content_type='application/json')
        self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control'])
        with patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE token')):
            response=self.client.post(url,data,content_type='application/json')
        self.assertEqual(response.status_code,503); self.assertNotIn('SYNTHETIC-PRIVATE',str(response.content))


class OllamaReasonerBoundaryTests(SimpleTestCase):
    def test_fixed_local_nonstreaming_model_no_tools_and_bounded_output(self):
        reasoner=OllamaReasoner()
        result={'model':reasoner.model,'done':True,'message':{'role':'assistant','content':'Synthetic grounded hypothesis.'}}
        with patch.object(reasoner,'_digest',return_value='a'*64),patch.object(reasoner,'_request',return_value=result) as http:
            self.assertIn('hypothesis',reasoner.reason({'query':'synthetic','sources':[]},deadline=time.monotonic()+5))
        _,path,body=http.call_args.args
        self.assertEqual(path,'/api/chat'); self.assertFalse(body['stream']); self.assertFalse(body['think'])
        self.assertNotIn('tools',body); self.assertEqual(body['options']['num_predict'],256)

    def test_remote_models_malformed_outputs_tool_calls_and_model_changes_are_rejected(self):
        reasoner=OllamaReasoner()
        for change in ({'done':False},{'model':'other'},{'message':{'role':'assistant','content':'','tool_calls':[]}},
                {'message':{'role':'assistant','content':'synthetic','tool_calls':[{'name':'delete'}]}}):
            response={'model':reasoner.model,'done':True,'message':{'role':'assistant','content':'synthetic'}}|change
            with patch.object(reasoner,'_digest',return_value='a'*64),patch.object(reasoner,'_request',return_value=response),self.assertRaises(EmbeddingUnavailable):
                reasoner.reason({'query':'synthetic'},deadline=time.monotonic()+5)
        with override_settings(ALFRED_MEMORY_OLLAMA_MODEL='model:cloud'),self.assertRaises(EmbeddingUnavailable): OllamaReasoner()
        with patch.object(reasoner,'_request',return_value={'models':[{'name':reasoner.model,'digest':'a'*64,'remote_host':'remote'}]}),self.assertRaises(EmbeddingUnavailable):
            reasoner.reason({'query':'synthetic'},deadline=time.monotonic()+5)
        with patch.object(reasoner,'_digest',side_effect=['a'*64,'b'*64]),patch.object(reasoner,'_request',return_value=response|{'message':{'role':'assistant','content':'synthetic'}}),self.assertRaises(EmbeddingUnavailable):
            reasoner.reason({'query':'synthetic'},deadline=time.monotonic()+5)

    def test_expired_local_deadline_makes_no_request(self):
        with patch('apps.ml_engine.services.local_embeddings.HTTPConnection') as connection,self.assertRaises(EmbeddingUnavailable):
            OllamaReasoner()._request('POST','/api/chat',deadline=time.monotonic()-1)
        connection.assert_not_called()
