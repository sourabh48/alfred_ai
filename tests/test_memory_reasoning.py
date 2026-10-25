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
from apps.ml_engine.services.memory_reasoning import OpenAIReasoner, MODEL, ReasoningBudgetExceeded, configure_reasoning, reason_with_memory, reasoning_provider
from apps.ml_engine.services.memory_sync import SyncUnavailable
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from tests.test_persistent_memory import SyntheticEmbeddings

KEY='sk-SYNTHETIC-ONLY-NEVER-A-REAL-PAID-CREDENTIAL-9001'


class MemoryReasoningTests(TestCase):
    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-openai-synthetic-')))
        self.alice=get_user_model().objects.create_user(username='synthetic-reason-alice')
        self.bob=get_user_model().objects.create_user(username='synthetic-reason-bob')
        self.store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings()); self.owner=_owner(self.alice)
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(self.store.directory),ALFRED_MEMORY_MOCK_REASONING=False,
            ALFRED_ABUSE_THROTTLE_DIR=str(self.root/'request-limits'),
            ALFRED_MEMORY_OPENAI_AUTHORIZED=True,ALFRED_MEMORY_OPENAI_PRICING_DATE=datetime.now(timezone.utc).date().isoformat()))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        self.http=self.enterContext(patch('apps.ml_engine.services.memory_reasoning.request',side_effect=self.response))
        self.provider=OpenAIReasoner(KEY)
        configure_reasoning(self.store,self.alice,enabled=True,consent=True,daily_tokens=4096,daily_microusd=10000)
        with self.store._transaction() as db:
            state=self.store._sync_state(db,self.owner); state['openai_key']=KEY; self.store._write_sync_state(db,self.owner,state)

    def response(self,*args,**kwargs):
        return PublicResponse(json.dumps({'model':MODEL,'service_tier':'default','status':'completed','error':None,
            'usage':{'input_tokens':100,'output_tokens':12,'total_tokens':112},
            'output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'Synthetic public suggestion.'}]}]}).encode(),'application/json')

    def save(self,content=None,sensitivity='public'):
        return self.store.save_verified(self.alice,content or {'preference':'synthetic quiet mountain'}, {'source':'SYNTHETIC-PRIVATE-PROVENANCE'},sensitivity=sensitivity,verified=True)

    def reason(self,user=None,**kwargs):
        return reason_with_memory(self.store,user or self.alice,'mountain',consent=True,query_sensitivity='public',provider=self.provider,**kwargs)

    def test_default_disable_and_stale_price_review_prevent_calls(self):
        for change in ({'ALFRED_MEMORY_OPENAI_AUTHORIZED':False},{'ALFRED_MEMORY_OPENAI_PRICING_DATE':''},{'ALFRED_MEMORY_OPENAI_PRICING_DATE':'2000-01-01'}):
            with override_settings(**change):
                self.assertIsNone(reasoning_provider(self.store,self.alice))
                with self.assertRaises(PermissionError): self.reason()
        self.http.assert_not_called()

    def test_request_is_fixed_bounded_stateless_and_strips_private_provenance(self):
        self.save(); result=self.reason()
        method,url=self.http.call_args.args; options=self.http.call_args.kwargs; body=json.loads(options['data'])
        self.assertEqual((method,url),('POST','https://api.openai.com/v1/responses'))
        self.assertFalse(body['store']); self.assertFalse(body['background']); self.assertEqual(body['tools'],[]); self.assertEqual(body['tool_choice'],'none')
        self.assertEqual(body['service_tier'],'default')
        self.assertEqual(body['max_output_tokens'],512); self.assertEqual(options['max_bytes'],65536)
        self.assertNotIn('PROVENANCE',str(body)); self.assertNotIn(self.owner,str(body)); self.assertNotIn(KEY,str(body))
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
        cost=self.provider.budget({'query':'mountain','memories':[]},512)[1]
        configure_reasoning(self.store,self.alice,enabled=True,consent=True,daily_tokens=4096,daily_microusd=cost)
        self.http.side_effect=OSError('SYNTHETIC-SECRET-PATH-F:/private')
        with self.assertRaises(SyncUnavailable) as failure: self.reason()
        self.assertNotIn('SECRET',str(failure.exception)); self.store.reset_owner(self.alice)
        self.store=MemoryStore(self.root/'vault',embedder=SyntheticEmbeddings())
        with self.assertRaises(ReasoningBudgetExceeded): self.reason()
        self.assertEqual(self.http.call_count,1)
        with self.store._transaction() as db: self.assertEqual(self.store._sync_state(db,self.owner)['reasoning']['reserved_microusd'],cost)

    def test_lowered_owner_limits_and_token_cap_reject_without_mutation(self):
        for kwargs in ({'daily_tokens':1},{'daily_microusd':1}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ReasoningBudgetExceeded): self.reason(**kwargs)
        self.http.assert_not_called()
        with self.store._transaction() as db: self.assertNotIn('reasoning',self.store._sync_state(db,self.owner))
        for limits in ((99999,10000),(4096,10000000),(True,1)):
            with self.assertRaises(ValueError): configure_reasoning(self.store,self.alice,enabled=True,consent=True,daily_tokens=limits[0],daily_microusd=limits[1])

    def test_corrupt_usage_models_tools_and_oversized_answers_fail_safely(self):
        with override_settings(ALFRED_MEMORY_REASONING_DAILY_TOKENS=65536):
            configure_reasoning(self.store,self.alice,enabled=True,consent=True,daily_tokens=65536,daily_microusd=10000)
        original=self.response().json()
        changes=({'model':'different-model'},{'service_tier':'priority'},{'status':'incomplete'},{'usage':{'input_tokens':1,'output_tokens':513,'total_tokens':514}},
            {'usage':{'input_tokens':True,'output_tokens':1,'total_tokens':2}}, {'output':[{'type':'function_call'}]},
            {'output':[{'type':'message','role':'assistant','content':[{'type':'output_text','text':'x'*8193}]}]})
        for change in changes:
            with self.subTest(change=list(change)):
                self.http.side_effect=None; self.http.return_value=PublicResponse(json.dumps(original|change).encode(),'application/json')
                with self.assertRaises(SyncUnavailable): self.reason(daily_tokens=65536)

    def test_concurrent_requests_share_atomic_spending_reservations(self):
        from concurrent.futures import ThreadPoolExecutor
        cost=self.provider.budget({'query':'mountain','memories':[]},512)[1]
        configure_reasoning(self.store,self.alice,enabled=True,consent=True,daily_tokens=4096,daily_microusd=cost)
        def attempt():
            try: self.reason(); return 'success'
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
        configure_reasoning(self.store,self.alice,enabled=False,daily_tokens=4096,daily_microusd=10000)
        with patch('apps.ml_engine.management.commands.configure_memory_reasoning.sys.stdin.isatty',return_value=True),patch('apps.ml_engine.management.commands.configure_memory_reasoning.getpass',return_value=KEY):
            output=StringIO(); call_command('configure_memory_reasoning',user=self.alice.pk,stdout=output)
        self.assertNotIn(KEY,output.getvalue()); self.assertNotIn(KEY.encode(),(self.store.directory/'verified.sqlite3').read_bytes())
        with self.assertRaises(SyncUnavailable): reasoning_provider(self.store,self.bob)
        with patch('apps.ml_engine.management.commands.configure_memory_reasoning.sys.stdin.isatty',return_value=False),self.assertRaises(CommandError):
            call_command('configure_memory_reasoning',user=self.alice.pk,stdout=StringIO())
        self.http.assert_not_called()

    def test_policy_api_keeps_credentials_private_and_requires_session_csrf(self):
        client=Client(enforce_csrf_checks=True); url='/api/ai/memories/reason/'
        policy={'enabled':True,'consent':True,'daily_tokens':4096,'daily_microusd':10000}
        self.assertEqual(client.put(url,policy,content_type='application/json').status_code,403)
        client.force_login(self.alice); self.assertEqual(client.put(url,policy,content_type='application/json').status_code,403)
        client.get('/settings/'); csrf=client.cookies['csrftoken'].value
        self.assertEqual(client.put(url,policy|{'owner':self.bob.pk},content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,400)
        self.assertEqual(client.put(url,policy,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,200)
        response=client.get(url); self.assertIn('no-store',response['Cache-Control']); self.assertNotIn(KEY,str(response.content))
        payload={'query':'mountain','consent':True,'query_sensitivity':'public'}
        self.assertEqual(client.post(url,payload,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,200)
        client.force_login(self.bob); self.assertEqual(client.post(url,payload,content_type='application/json',HTTP_X_CSRFTOKEN=csrf).status_code,503)
