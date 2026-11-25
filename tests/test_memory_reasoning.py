from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings, Client

from alfred_ai.services.public_http import PublicResponse
from apps.ml_engine.services.memory_reasoning import CLOUD_OUTPUT_TOKENS, GeminiReasoner, ReasoningBudgetExceeded, configure_reasoning, reason_with_memory, reasoning_provider, remove_key, save_key
from apps.ml_engine.services.memory_sync import SyncUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.test_persistent_memory import SyntheticEmbeddings

KEY='AIza'+'SYNTHETIC-ONLY-NEVER-REAL-000009001'  # made-up, Gemini key shape
MODEL='gemini-synthetic-lite'


class MemoryReasoningTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-gemini-synthetic-')))
        self.alice=get_user_model().objects.create_user(username='synthetic-reason-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-reason-bob')
        self.store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings()); self.owner=_owner(self.alice)
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.store.directory),ALFRED_MEMORY_MOCK_REASONING=False,
            ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'request-limits'),ALFRED_GEMINI_MODEL=MODEL))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.http=self.enterContext(patch('apps.ml_engine.services.memory_reasoning.request',side_effect=self.response))
        self.provider=GeminiReasoner(KEY)
        configure_reasoning(self.store,self.alice,enabled=True,consent=True)
        with self.store._transaction() as db:
            state=self.store._sync_state(db,self.owner); state['gemini_key']=KEY; self.store._write_sync_state(db,self.owner,state)

    def response(self,*args,**kwargs):
        return PublicResponse(json.dumps({'modelVersion':MODEL,'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':12,'totalTokenCount':112},
            'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':'Synthetic public suggestion.'}]}}]}).encode(),'application/json')

    def save(self,content=None,sensitivity='public'):
        return self.store.save_verified(self.alice,content or {'preference':'synthetic quiet mountain'}, {'source':'SYNTHETIC-PRIVATE-PROVENANCE'},sensitivity=sensitivity,verified=True)

    def reason(self,user=None,**kwargs):
        return reason_with_memory(self.store,user or self.alice,'mountain',consent=True,query_sensitivity='public',provider=self.provider,**kwargs)

    def test_no_key_or_no_opt_in_prevents_calls(self):
        self.assertIsNone(reasoning_provider(self.store,self.bob))  # no key saved
        configure_reasoning(self.store,self.alice,enabled=False)
        with self.assertRaises(PermissionError): self.reason()  # key saved, opt-in off
        remove_key(self.store,self.alice)
        self.assertIsNone(reasoning_provider(self.store,self.alice))
        self.http.assert_not_called()

    def test_a_leftover_openai_key_is_forgotten_and_its_consent_does_not_carry_to_gemini(self):
        with self.store._transaction() as db:
            state=self.store._sync_state(db,self.owner); state.pop('gemini_key'); state['openai_key']='sk-'+'S'*30; self.store._write_sync_state(db,self.owner,state)
        self.assertIsNone(reasoning_provider(self.store,self.alice))
        with self.store._transaction() as db: state=self.store._sync_state(db,self.owner)
        self.assertNotIn('openai_key',state); self.assertFalse(state['reasoning_policy']['enabled'])
        save_key(self.store,self.alice,KEY)
        with self.assertRaises(PermissionError): self.reason()  # opts in again for Gemini first
        self.http.assert_not_called()

    def test_settings_key_api_saves_encrypted_never_returns_it_and_remove_turns_off(self):
        client=Client(enforce_csrf_checks=True); url='/api/ai/memories/reason/key/'
        client.force_login(self.bob); client.get('/settings/'); csrf=client.cookies['csrftoken'].value
        self.assertEqual(client.post(url,{'key':KEY},content_type='application/json').status_code,403)  # CSRF
        self.assertEqual(client.post(url,{'key':'not-a-key'},content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,400)
        self.assertEqual(client.post(url,{'key':KEY,'owner':self.alice.pk},content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,400)
        saved=client.post(url,{'key':KEY},content_type='application/json',HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(saved.json(),{'key_saved':True,'key_hint':'…9001','policy_enabled':False})
        self.assertNotIn(KEY,saved.content.decode()+client.get('/api/ai/memories/reason/').content.decode())
        self.assertNotIn(KEY.encode(),(self.store.directory/'verified.sqlite3').read_bytes())
        self.assertIsInstance(reasoning_provider(self.store,self.bob),GeminiReasoner)
        configure_reasoning(self.store,self.bob,enabled=True,consent=True)
        self.assertEqual(client.delete(url,HTTP_X_CSRFTOKEN=csrf).json(),{'key_saved':False,'key_hint':'','policy_enabled':False})
        self.assertIsNone(reasoning_provider(self.store,self.bob))
        self.assertIsInstance(reasoning_provider(self.store,self.alice),GeminiReasoner)  # other owners untouched
        # Owner check 2026-11-20: AI Studio's newer keys start with "AQ." (made-up value below).
        newer='AQ.'+'Synthetic_Only-Never.Real-'*2
        self.assertEqual(client.post(url,{'key':newer},content_type='application/json',HTTP_X_CSRFTOKEN=csrf).json()['key_hint'],'…eal-')
        for bad in ('AQ.short','AQ. has spaces inside the key value here','x'*513):
            with self.subTest(bad=bad[:20]):
                self.assertEqual(client.post(url,{'key':bad},content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,400)
        self.http.assert_not_called()

    def test_request_is_fixed_bounded_stateless_and_strips_private_provenance(self):
        self.save(); result=self.reason()
        method,url=self.http.call_args.args; options=self.http.call_args.kwargs; body=json.loads(options['data'])
        self.assertEqual((method,url),('POST',f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'))
        self.assertEqual(options['headers']['x-goog-api-key'],KEY); self.assertNotIn('tools',body); self.assertNotIn('toolConfig',body)
        self.assertEqual(body['generationConfig'],{'maxOutputTokens':CLOUD_OUTPUT_TOKENS,'candidateCount':1}); self.assertEqual(options['max_bytes'],65536)
        self.assertNotIn('PROVENANCE',str(body)); self.assertNotIn(self.owner,str(body)); self.assertNotIn(KEY,str(body))
        self.assertEqual(result['answer'],'Synthetic public suggestion.'); self.assertEqual(result['provider'],'gemini')
        self.assertEqual(result['classification'],'ai_generated_hypothesis'); self.assertFalse(result['financial_authority'])
        self.assertGreater(result['reserved_microusd'],0)

    def test_public_misclassification_financial_data_keys_tokens_paths_pii_denied(self):
        for text in ('loan SYNTHETIC-ACCOUNT-9001','email fake@example.invalid','OCR token SYNTHETIC-TOKEN','F:/private/file','123456789012','$123.45'):
            with self.subTest(text=text),self.assertRaises(PermissionError):
                reason_with_memory(self.store,self.alice,text,consent=True,query_sensitivity='public',provider=self.provider)
        self.save({'account_number':'SYNTHETIC-FAKE'})
        with self.assertRaises(PermissionError): self.reason()
        self.http.assert_not_called()

    def test_owner_policy_and_sensitive_context_are_independent_gates(self):
        with self.assertRaises(PermissionError): self.reason(self.bob)
        self.save(sensitivity='personal')
        with self.assertRaises(PermissionError): self.reason()
        self.http.assert_not_called()

    def test_spending_cap_reserved_before_call_and_survives_failure_reset_restart(self):
        cost=self.provider.budget({'query':'mountain','memories':[]},CLOUD_OUTPUT_TOKENS)[1]
        self.http.side_effect=OSError('SYNTHETIC-SECRET-PATH-F:/private')
        with self.assertRaises(SyncUnavailable) as failure: self.reason(daily_microusd=cost)
        self.assertNotIn('SECRET',str(failure.exception)); self.store.reset_owner(self.alice)
        self.store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings())
        with self.assertRaises(ReasoningBudgetExceeded): self.reason(daily_microusd=cost)
        self.assertEqual(self.http.call_count,1)
        with self.store._transaction() as db: self.assertEqual(self.store._sync_state(db,self.owner)['reasoning']['reserved_microusd'],cost)

    def test_token_and_spending_caps_reject_without_mutation(self):
        for kwargs in ({'daily_tokens':1},{'daily_microusd':1}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ReasoningBudgetExceeded): self.reason(**kwargs)
        self.http.assert_not_called()
        with self.store._transaction() as db: self.assertNotIn('reasoning',self.store._sync_state(db,self.owner))
        for kwargs in ({'daily_tokens':10_000_001},{'daily_microusd':1_000_001},{'daily_tokens':True}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError): self.reason(**kwargs)

    def test_old_per_person_limits_no_longer_cap_answers(self):
        # Before 2026-11-25 people typed their own limits; a saved 4096 tokens / USD 0.01 refused every web-backed question.
        with self.store._transaction() as db:
            state=self.store._sync_state(db,self.owner); state['reasoning_policy']|={'daily_tokens':1,'daily_microusd':1}
            self.store._write_sync_state(db,self.owner,state)
        self.assertEqual(self.reason(daily_tokens=65536,daily_microusd=1000000)['answer'],'Synthetic public suggestion.')

    def test_reported_usage_replaces_the_up_front_estimate(self):
        original=self.response().json(); self.http.side_effect=None
        self.http.return_value=PublicResponse(json.dumps(original|{'usageMetadata':{'promptTokenCount':100,'candidatesTokenCount':12,'thoughtsTokenCount':20}}).encode(),'application/json')
        result=self.reason(daily_tokens=65536,daily_microusd=1000000)
        with self.store._transaction() as db: ledger=self.store._sync_state(db,self.owner)['reasoning']
        self.assertEqual((ledger['reserved'],ledger['reserved_microusd']),(132,100+4*32))
        self.assertEqual((result['reserved_tokens'],result['reserved_microusd']),(132,228))
        self.http.return_value=PublicResponse(json.dumps(original|{'usageMetadata':{'promptTokenCount':100,'thoughtsTokenCount':'x'}}).encode(),'application/json')
        estimate=self.provider.budget({'query':'mountain','memories':[]},CLOUD_OUTPUT_TOKENS)
        self.reason(daily_tokens=65536,daily_microusd=1000000)  # unreadable thought count: the estimate stays counted
        with self.store._transaction() as db: ledger=self.store._sync_state(db,self.owner)['reasoning']
        self.assertEqual((ledger['reserved'],ledger['reserved_microusd']),(132+estimate[0],228+estimate[1]))

    def test_corrupt_usage_models_tools_and_oversized_answers_fail_safely(self):
        original=self.response().json()
        def answer(**candidate):
            return {'candidates':[{'finishReason':'STOP','content':{'role':'model','parts':[{'text':'ok'}]}}|candidate]}
        changes=({'modelVersion':'different-model'},{'promptFeedback':{'blockReason':'SAFETY'}},answer(finishReason='MAX_TOKENS'),
            {'usageMetadata':{'promptTokenCount':1,'candidatesTokenCount':CLOUD_OUTPUT_TOKENS+1}},{'usageMetadata':{'promptTokenCount':True}},
            answer(content={'role':'model','parts':[{'functionCall':{'name':'x'}}]}),answer(content={'role':'model','parts':[{'text':'x'*16385}]}),
            {'candidates':[]})
        for change in changes:
            with self.subTest(change=list(change)):
                self.http.side_effect=None; self.http.return_value=PublicResponse(json.dumps(original|change).encode(),'application/json')
                with self.assertRaises(SyncUnavailable): self.reason(daily_tokens=65536,daily_microusd=1000000)
        self.http.return_value=PublicResponse(json.dumps(original|answer(finishReason='MAX_TOKENS',content={'role':'model','parts':[{'text':'Synthetic cut-off'}]})).encode(),'application/json')
        with self.assertLogs('apps.ml_engine.services.memory_reasoning','WARNING') as logged, self.assertRaises(SyncUnavailable):
            self.reason(daily_tokens=65536,daily_microusd=1000000)
        self.assertEqual(logged.output,['WARNING:apps.ml_engine.services.memory_reasoning:Gemini reply not used: ValueError (MAX_TOKENS)'])

    def test_model_version_with_a_models_prefix_is_the_same_model(self):
        original=self.response().json()
        self.http.side_effect=None
        self.http.return_value=PublicResponse(json.dumps(original|{'modelVersion':'models/'+MODEL}).encode(),'application/json')
        self.reason(daily_tokens=65536,daily_microusd=1000000)
        self.http.return_value=PublicResponse(json.dumps(original|{'modelVersion':'models/different-model'}).encode(),'application/json')
        with self.assertRaises(SyncUnavailable): self.reason(daily_tokens=65536,daily_microusd=1000000)

    def test_concurrent_requests_share_atomic_spending_reservations(self):
        from concurrent.futures import ThreadPoolExecutor
        cost=self.provider.budget({'query':'mountain','memories':[]},CLOUD_OUTPUT_TOKENS)[1]
        def attempt():
            try: self.reason(daily_microusd=cost); return 'success'
            except ReasoningBudgetExceeded: return 'limited'
        with ThreadPoolExecutor(max_workers=2) as executor: results=list(executor.map(lambda _:attempt(),range(2)))
        self.assertEqual(sorted(results),['limited','success']); self.assertEqual(self.http.call_count,1)

    def test_revoked_context_cannot_dispatch_after_local_inference(self):
        identity=self.save(); original=self.store.retrieve
        def revoke(*args,**kwargs):
            result=original(*args,**kwargs); self.store.delete_memory(self.alice,identity); return result
        with patch.object(self.store,'retrieve',side_effect=revoke),self.assertRaises(PermissionError): self.reason()
        self.http.assert_not_called()

    def test_credential_provisioning_is_masked_encrypted_and_owner_isolated(self):
        configure_reasoning(self.store,self.alice,enabled=False)
        with patch('apps.ml_engine.management.commands.configure_memory_reasoning.sys.stdin.isatty',return_value=True),patch('apps.ml_engine.management.commands.configure_memory_reasoning.getpass',return_value=KEY):
            output=StringIO(); call_command('configure_memory_reasoning',user=self.alice.pk,stdout=output)
        self.assertNotIn(KEY,output.getvalue()); self.assertNotIn(KEY.encode(),(self.store.directory/'verified.sqlite3').read_bytes())
        self.assertIsNone(reasoning_provider(self.store,self.bob))
        with patch('apps.ml_engine.management.commands.configure_memory_reasoning.sys.stdin.isatty',return_value=False),self.assertRaises(CommandError):
            call_command('configure_memory_reasoning',user=self.alice.pk,stdout=StringIO())
        self.http.assert_not_called()

    def test_policy_api_keeps_credentials_private_and_requires_session_csrf(self):
        client=Client(enforce_csrf_checks=True); url='/api/ai/memories/reason/'
        policy={'enabled':True,'consent':True}
        self.assertEqual(client.put(url,policy,content_type='application/json').status_code,403)
        client.force_login(self.alice); self.assertEqual(client.put(url,policy,content_type='application/json').status_code,403)
        client.get('/settings/'); csrf=client.cookies['csrftoken'].value
        for extra in ({'owner':self.bob.pk},{'daily_tokens':4096}):  # limits are ALFRED's, not settable per person
            self.assertEqual(client.put(url,policy|extra,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,400)
        self.assertEqual(client.put(url,policy,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,200)
        response=client.get(url); self.assertIn('no-store',response['Cache-Control']); self.assertNotIn(KEY,str(response.content))
        payload={'query':'mountain','consent':True,'query_sensitivity':'public'}
        self.assertEqual(client.post(url,payload,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,200)
        client.force_login(self.bob); self.assertEqual(client.post(url,payload,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,503)
