"""Real-page acceptance of synthetic financial data and its explanations."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import threading
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.core.handlers.base import BaseHandler
from django.test import override_settings

from apps.expenses.models import Expense
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests import test_document_review_browser as browser_support
from tests.user_acceptance_scenario import PASSWORD, month_start, seed_acceptance_user


@unittest.skipUnless(browser_support.RUN_BROWSER_TESTS, "Set ALFRED_RUN_BROWSER_TESTS=true to run browser acceptance.")
class UserDataBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        cls.By = By
        cls.active_requests = 0
        cls.request_lock = threading.Lock()
        original_get_response = BaseHandler.get_response

        def tracked_response(handler, request):
            with cls.request_lock:
                cls.active_requests += 1
            try:
                return original_get_response(handler, request)
            finally:
                with cls.request_lock:
                    cls.active_requests -= 1

        tracker = patch.object(BaseHandler, "get_response", tracked_response)
        tracker.start()
        cls.addClassCleanup(tracker.stop)
        cls.browser = browser_support.DocumentReviewBrowserTests._create_driver(webdriver)
        cls.browser.set_window_size(1440, 1200)
        cls.wait = WebDriverWait(cls.browser, 20)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "browser", None):
            cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-browser-invite-limits-"))
        self.enterContext(override_settings(ALFRED_FAMILY_INVITE_THROTTLE_DIR=directory,
            ALFRED_ABUSE_THROTTLE_DIR=str(Path(directory) / 'runtime-limits')))
        self.browser.get("about:blank")
        cache.clear()
        self.offline = _offline_fixture_patches()
        self.addCleanup(self.offline.close)
        self.scenario = seed_acceptance_user(self.client)
        self.browser.delete_all_cookies()
        self.artifacts = Path(os.environ.get("ALFRED_BROWSER_ARTIFACT_DIR", "artifacts/browser")) / "user-data"
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.browser.get("about:blank")
        # Drain real live-server requests before TransactionTestCase flushes
        # users and sessions; navigation can abort a fetch while its server
        # handler is still completing the response.
        self.wait.until(lambda _: self.active_requests == 0)
        super().tearDown()

    def login(self, username="acceptance_demo"):
        self.browser.get(self.live_server_url + "/login/")
        self.browser.find_element(self.By.NAME, "username").send_keys(username)
        self.browser.find_element(self.By.NAME, "password").send_keys(PASSWORD)
        self.wait.until(lambda driver: driver.execute_script("return !document.getAnimations().some(a => a.playState === 'running' && a.effect?.target?.closest('.auth-panel'))"))
        self.browser.find_element(self.By.CSS_SELECTOR, 'button[type="submit"]').click()
        self.wait.until(lambda driver: driver.find_elements(self.By.ID, "dashboardPeriodNote"))
        self.wait.until(lambda driver: self.text("dashboardPeriodNote") and "Loading" not in self.text("dashboardPeriodNote"))
        self.wait.until(lambda driver: self.text("dashboardSummaryCards"))

    def text(self, element_id):
        return self.browser.find_element(self.By.ID, element_id).text

    def memory_post(self,path,payload,csrf=True):
        return self.browser.execute_async_script('''
            const [path,payload,csrf,done]=arguments;
            const headers={'Content-Type':'application/json'};
            if(csrf) headers['X-CSRFToken']=decodeURIComponent(document.cookie.split('; ').find(x=>x.startsWith('csrftoken=')).split('=')[1]);
            fetch('/api/ai/memories/'+path+'/',{method:'POST',headers,body:JSON.stringify(payload)})
              .then(async response=>done({status:response.status,data:await response.json(),cache:response.headers.get('Cache-Control')}));
        ''',path,payload,csrf)

    def memory_click(self,selector):
        element=self.browser.find_element(self.By.CSS_SELECTOR,selector)
        self.browser.execute_script("arguments[0].scrollIntoView({behavior:'instant',block:'center'});",element)
        self.wait.until(lambda _: element.is_displayed() and element.is_enabled())
        element.click()

    def test_user_decimal_profile_save_and_reload_keeps_exact_owned_cents(self):
        from decimal import Decimal
        self.login()
        self.browser.get(self.live_server_url + '/settings/')
        self.wait.until(lambda _: self.text('settingsProfileStatus') == 'Synced')
        values = {'monthly_income': '10000.01', 'variable_income': '200.02', 'rent_or_emi': '1000.03'}
        for field, amount in values.items():
            element = self.browser.find_element(self.By.CSS_SELECTOR, f'#accountProfileForm [name="{field}"]')
            element.clear(); element.send_keys(amount)
        self.memory_click('#accountProfileForm button[type=submit]')
        self.wait.until(lambda _: 'Profile saved' in self.text('settingsProfileFeedback'))
        self.browser.refresh()
        self.wait.until(lambda _: self.text('settingsProfileStatus') == 'Synced')
        self.scenario['user'].refresh_from_db()
        for field, amount in values.items():
            self.assertEqual(getattr(self.scenario['user'], field), Decimal(amount))
            self.assertEqual(self.browser.find_element(self.By.CSS_SELECTOR,
                f'#accountProfileForm [name="{field}"]').get_attribute('value'), amount)
        self.capture('user-decimal-profile-reload')

    def test_career_decimal_salary_save_and_reload_preserves_experience(self):
        from decimal import Decimal
        from apps.career.models import CareerProfile
        self.login(); self.browser.get(self.live_server_url + '/career/')
        self.wait.until(lambda _: self.browser.find_element(self.By.CSS_SELECTOR,
            '#careerProfileForm [name=last_salary]').get_attribute('value') != '')
        for field, value in {'last_salary': '12345.67', 'experience_years': '4.5', 'skills': 'Python, SQL'}.items():
            element = self.browser.find_element(self.By.CSS_SELECTOR, f'#careerProfileForm [name="{field}"]')
            element.clear(); element.send_keys(value)
        self.memory_click('#careerProfileForm button[type=submit]')
        self.wait.until(lambda _: 'updated' in self.text('careerFormFeedback'))
        self.browser.refresh()
        self.wait.until(lambda _: self.browser.find_element(self.By.CSS_SELECTOR,
            '#careerProfileForm [name=last_salary]').get_attribute('value') == '12345.67')
        row = CareerProfile.objects.get(user=self.scenario['user'])
        self.assertEqual((row.last_salary, row.experience_years), (Decimal('12345.67'), 4.5))
        self.capture('career-decimal-salary-reload')

    def memory_evaluation_fixture(self):
        from unittest.mock import Mock
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from tests.test_memory_evaluation import synthetic_embedding
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-evaluation-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_MEMORY_OPENAI_AUTHORIZED=False,
            ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_SYNC_PROVIDER='',ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False))
        embedder=Mock(); embedder.embed.side_effect=synthetic_embedding
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=embedder))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']
        identities=[store.save_verified(owner,{'statement':text},{'source':'Synthetic owner review'},verified=True)
            for text in ('mountain preference','I prefer the coast','I dislike the coast')]
        self.login(); self.browser.get(self.live_server_url+'/settings/')
        self.wait.until(lambda _: len(self.browser.find_element(self.By.ID,'memoryEvaluationExpected').find_elements(self.By.TAG_NAME,'option'))==4)
        return store,owner,identities

    def test_multi_case_memory_evaluation_metrics_citations_mobile_and_clearing(self):
        from selenium.webdriver.support.ui import Select
        store,owner,identities=self.memory_evaluation_fixture()
        query=self.browser.find_element(self.By.ID,'memoryEvaluationQuery')
        expected=Select(self.browser.find_element(self.By.ID,'memoryEvaluationExpected'))
        query.send_keys('mountain hiking'); expected.select_by_value(identities[0]); self.memory_click('#memoryEvaluationAdd')
        query.send_keys('coast preference'); expected.select_by_value(identities[1]); expected.select_by_value(identities[2])
        self.memory_click('#memoryEvaluationAdd')
        query.send_keys('astronomy <img src=x onerror="window.evaluationLeak=true">')
        self.memory_click('#memoryEvaluationAdd')
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryEvaluationCases > li')),3)
        self.memory_click('#memoryEvaluationForm button[type="submit"]')
        self.wait.until(lambda _: '3 questions. Precision: 100.0%. Recall: 100.0%.' in self.text('memoryEvaluationResult'))
        self.assertIn('Negative-case abstention: 100.0%',self.text('memoryEvaluationResult'))
        self.assertIn('Owner-checked citations: 3',self.text('memoryEvaluationResult'))
        self.assertIn('record correctness: 100.0%',self.text('memoryEvaluationResult'))
        self.assertIn('Indexed model fingerprint:',self.text('memoryEvaluationResult'))
        self.assertIn('4 dimensions; 3 memories.',self.text('memoryEvaluationResult'))
        self.assertIn('This run alone cannot establish model drift.',self.text('memoryEvaluationResult'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryEvaluationDetails > li')),3)
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryEvaluationDetails a')),3)
        self.assertFalse(self.browser.execute_script('return Boolean(window.evaluationLeak)'))
        self.assertIn('astronomy <img',self.text('memoryEvaluationDetails'))
        self.browser.execute_script("document.querySelector('#memoryEvaluationForm').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('memory-evaluation-multi-case-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.querySelector('#memoryEvaluationResult').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('memory-evaluation-multi-case-mobile')
        self.memory_click(f'#memoryEvaluationDetails a[href="/settings/#memory-{identities[0]}"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,f'memory-{identities[0]}').is_displayed())
        self.assertIn('mountain preference',self.browser.find_element(self.By.ID,f'memory-{identities[0]}').text)
        self.memory_click('#memoryEvaluationClear')
        self.assertEqual(self.text('memoryEvaluationCases'),''); self.assertEqual(self.text('memoryEvaluationDetails'),'')
        self.browser.find_element(self.By.ID,'memoryEvaluationQuery').send_keys('private synthetic draft')
        self.memory_click('#memoryEvaluationAdd')
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        for identity in ('memoryEvaluationCases','memoryEvaluationDetails','memoryEvaluationResult','memoryEvaluationFeedback'):
            self.assertEqual(self.text(identity),'')
        self.assertEqual(self.browser.find_element(self.By.ID,'memoryEvaluationQuery').get_property('value'),'')

    def test_reviewed_synthetic_model_comparison_verdict_metrics_outage_and_mobile(self):
        from selenium.webdriver.support.ui import Select
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        from apps.ml_engine.services.retrieval_quality import compare, MODELS
        from apps.ml_engine.services.persistent_memory import RETRIEVAL_PROTOCOLS
        from apps.ml_engine.services.retrieval_holdout import cohort
        from tests.test_retrieval_quality import contract_comparison, ContractEmbeddings
        self.enterContext(override_settings(ALFRED_SYNTHETIC_QUALITY_ENABLED=True))
        self.memory_evaluation_fixture()
        report=contract_comparison()
        with patch('apps.ml_engine.services.retrieval_quality.compare',return_value=report):
            self.memory_click('#memoryComparisonForm button')
            self.wait.until(lambda _: 'ELIGIBLE FOR REVIEW' in self.text('memoryComparisonStatus'))
        self.assertIn('Active model unchanged',self.text('memoryComparisonStatus'))
        self.assertIn('policy synthetic-retrieval-v1',self.text('memoryComparisonResults'))
        self.assertIn('independent baseline and candidate measurements',self.text('memoryComparisonResults'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryComparisonResults details')),24)
        self.memory_click('#memoryComparisonResults details summary')
        self.assertIn('Expected: trail, corrected',self.text('memoryComparisonResults'))
        self.assertIn('24 questions per model',self.text('memoryComparisonPolicy'))
        self.assertIn('candidate 100.0%',self.text('memoryComparisonResults'))
        self.assertIn('stale source rejected: true',self.text('memoryComparisonResults'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryComparisonResults article')),2)
        self.assertIn('Development — not independent acceptance',self.text('memoryComparisonResults'))
        self.assertIn('Positive-case precision@k / recall@k',self.text('memoryComparisonResults'))
        self.assertIn('Precision divides by k; recall divides by expected references.',self.text('memoryComparisonResults'))
        self.assertIn('Retrieval errors: 0 unexpected references',self.text('memoryComparisonResults'))
        heldout=compare(MODELS[0],MODELS[0],adapters={MODELS[0]:ContractEmbeddings(cohorts=(cohort(),))},suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        Select(self.browser.find_element(self.By.ID,'memoryComparisonSuite')).select_by_value('held_out')
        Select(self.browser.find_element(self.By.ID,'memoryComparisonProtocol')).select_by_value(RETRIEVAL_PROTOCOLS[1])
        self.assertIn('12 questions per model',self.text('memoryComparisonPolicy'))
        with patch('apps.ml_engine.services.retrieval_quality.compare',return_value=heldout) as compared:
            self.memory_click('#memoryComparisonForm button')
            self.wait.until(lambda _: 'Independent held-out — evaluation only' in self.text('memoryComparisonResults'))
        self.assertEqual(compared.call_args.kwargs,dict(suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1]))
        self.assertIn('same installed model; independent protocol measurements',self.text('memoryComparisonResults'))
        self.assertIn('Retrieval source frozen at 0651e7a9fb48',self.text('memoryComparisonResults'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryComparisonResults details')),12)
        self.memory_click('#memoryComparisonResults details summary')
        self.assertIn('Expected: pigment, counterclaim',self.text('memoryComparisonResults'))
        self.capture('independent-heldout-contract-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.browser.execute_script("document.querySelector('#memoryComparisonStatus').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('independent-heldout-contract-mobile')
        self.assertLessEqual(self.browser.execute_script('return document.documentElement.scrollWidth'),390)
        Select(self.browser.find_element(self.By.ID,'memoryComparisonSuite')).select_by_value('development')
        Select(self.browser.find_element(self.By.ID,'memoryComparisonProtocol')).select_by_value(RETRIEVAL_PROTOCOLS[0])
        guarded=report|dict(decision='REJECT',baseline=None,candidate=None,differences=[],reasons=['source_or_owner_revalidation_failed'])
        guarded.pop('candidate_execution')
        with patch('apps.ml_engine.services.retrieval_quality.compare',return_value=guarded):
            self.memory_click('#memoryComparisonForm button')
            self.wait.until(lambda _: 'incomplete model evidence' in self.text('memoryComparisonResults'))
        self.assertNotIn('independent baseline and candidate measurements',self.text('memoryComparisonResults'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryComparisonResults article')),0)
        from threading import Event
        started,finish=Event(),Event()
        def delayed_comparison(*args,**kwargs):
            started.set(); finish.wait(10); return report
        with patch('apps.ml_engine.services.retrieval_quality.compare',side_effect=delayed_comparison):
            self.memory_click('#memoryComparisonForm button')
            self.wait.until(lambda _: started.is_set())
            self.memory_click('#memoryRefreshButton')
            self.wait.until(lambda _: 'cancelled by refresh' in self.text('memoryComparisonStatus'))
            finish.set()
            self.browser.execute_async_script('const done=arguments[0];setTimeout(done,400)')
        self.assertEqual(self.text('memoryComparisonResults'),'')
        self.assertNotIn('Comparing',self.text('memoryComparisonStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID,'memoryComparisonForm').get_attribute('aria-busy'),'false')
        started.clear(); finish.clear()
        with patch('apps.ml_engine.services.retrieval_quality.compare',side_effect=delayed_comparison):
            self.memory_click('#memoryComparisonForm button')
            self.wait.until(lambda _: started.is_set())
            with patch('apps.ml_engine.services.memory_learning.MemoryLearning.candidates',side_effect=EmbeddingUnavailable('SYNTHETIC refresh unavailable')):
                self.memory_click('#memoryRefreshButton')
                self.wait.until(lambda _: 'Local model is unavailable' in self.text('memoryFeedback'))
            self.assertIn('cancelled by refresh',self.text('memoryComparisonStatus'))
            self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,'#memoryComparisonForm button').is_enabled())
            finish.set()
        with patch('apps.ml_engine.services.retrieval_quality.compare',side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE outage')):
            self.memory_click('#memoryComparisonForm button')
            self.wait.until(lambda _: 'Comparison incomplete:' in self.text('memoryComparisonStatus'))
        self.assertEqual(self.text('memoryComparisonResults'),'')
        self.assertNotIn('SYNTHETIC-PRIVATE',self.text('memoryComparisonStatus'))
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('memoryComparisonStatus'),'')

    def test_multi_case_memory_evaluation_stale_source_and_model_outage_keep_drafts(self):
        from selenium.webdriver.support.ui import Select
        from apps.ml_engine.services.memory_learning import MemoryLearning
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        store,owner,identities=self.memory_evaluation_fixture()
        query=self.browser.find_element(self.By.ID,'memoryEvaluationQuery')
        Select(self.browser.find_element(self.By.ID,'memoryEvaluationExpected')).select_by_value(identities[0])
        query.send_keys('mountain private draft'); self.memory_click('#memoryEvaluationAdd')
        retrieve=MemoryStore.retrieve
        def correcting(instance,user,text,**kwargs):
            result=retrieve(instance,user,text,**kwargs)
            MemoryLearning(store).revise(owner,[identities[0]],{'statement':'corrected mountain preference'},verified=True)
            return result
        with patch.object(MemoryStore,'retrieve',autospec=True,side_effect=correcting):
            self.memory_click('#memoryEvaluationForm button[type="submit"]')
            self.wait.until(lambda _: 'Memory changed.' in self.text('memoryEvaluationFeedback'))
        self.assertIn('mountain private draft',self.text('memoryEvaluationCases'))
        self.assertEqual(self.text('memoryEvaluationResult'),''); self.assertEqual(self.text('memoryEvaluationDetails'),'')
        self.memory_click('#memoryRefreshButton')
        self.wait.until(lambda _: 'corrected mountain preference' in self.text('memoryList'))
        self.assertIn('An expected source changed',self.text('memoryEvaluationCases'))
        self.memory_click('#memoryEvaluationForm button[type="submit"]')
        self.wait.until(lambda _: 'cannot be substituted automatically' in self.text('memoryEvaluationFeedback'))
        self.memory_click('#memoryEvaluationCases button')
        current=next(record['id'] for record in store.list_memories(owner) if 'corrected' in record['content']['statement'])
        query.send_keys('mountain retry draft'); Select(self.browser.find_element(self.By.ID,'memoryEvaluationExpected')).select_by_value(current)
        with patch.object(MemoryStore,'retrieve',side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE F:/synthetic/private-key.txt')):
            self.memory_click('#memoryEvaluationForm button[type="submit"]')
            self.wait.until(lambda _: 'Local model is unavailable.' in self.text('memoryEvaluationFeedback'))
        self.assertEqual(query.get_property('value'),'mountain retry draft')
        self.assertNotIn('SYNTHETIC-PRIVATE',self.text('memoryEvaluationFeedback'))
        self.memory_click('#memoryEvaluationForm button[type="submit"]')
        self.wait.until(lambda _: 'First match correct: yes.' in self.text('memoryEvaluationResult'))
        self.browser.execute_script("document.querySelector('#memoryEvaluationResult').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('memory-evaluation-stale-source-and-retry')

    def test_memory_evaluation_pending_pagehide_discards_late_response_and_over_limit_preserves_cases(self):
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.memory_learning import MemoryLearning
        store,owner,identities=self.memory_evaluation_fixture()
        query=self.browser.find_element(self.By.ID,'memoryEvaluationQuery')
        query.send_keys('mountain pending draft'); self.memory_click('#memoryEvaluationAdd')
        entered=threading.Event(); release=threading.Event(); self.addCleanup(release.set)
        retrieve=MemoryStore.retrieve
        def delayed(instance,user,text,**kwargs):
            entered.set(); release.wait(10); return retrieve(instance,user,text,**kwargs)
        with patch.object(MemoryStore,'retrieve',autospec=True,side_effect=delayed):
            self.memory_click('#memoryEvaluationForm button[type="submit"]')
            self.wait.until(lambda _: entered.is_set())
            self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
            release.set(); self.wait.until(lambda _: type(self).active_requests==0)
            self.assertEqual(self.text('memoryEvaluationDetails'),''); self.assertEqual(self.text('memoryEvaluationCases'),'')
            self.assertEqual(self.text('memoryEvaluationResult'),''); self.assertEqual(query.get_property('value'),'')
            self.assertEqual(self.browser.find_element(self.By.ID,'memoryEvaluationForm').get_attribute('aria-busy'),'false')
        self.browser.execute_script("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        self.wait.until(lambda _: len(self.browser.find_element(self.By.ID,'memoryEvaluationExpected').find_elements(self.By.TAG_NAME,'option'))==4)
        self.assertEqual(self.browser.execute_script("return [...document.querySelector('#memoryEvaluationExpected').selectedOptions].map(option=>option.value)"),[''])
        for index in range(20):
            query.send_keys(f'synthetic question {index+1}'); self.memory_click('#memoryEvaluationAdd')
        query.send_keys('synthetic question 21')
        with patch.object(MemoryLearning,'evaluate',side_effect=AssertionError('An oversized cohort must not run')) as evaluate:
            self.memory_click('#memoryEvaluationAdd')
            self.assertIn('no cases were dropped',self.text('memoryEvaluationFeedback'))
            self.memory_click('#memoryEvaluationForm button[type="submit"]')
            self.assertIn('no cases were dropped',self.text('memoryEvaluationFeedback'))
            evaluate.assert_not_called()
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#memoryEvaluationCases > li')),20)
        self.assertEqual(query.get_property('value'),'synthetic question 21')
        self.capture('memory-evaluation-limit-preserves-cases')

    def test_candidate_verification_and_correction_refresh_owned_settings(self):
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-learning-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']
        self.login(); self.browser.get(self.live_server_url+'/settings/')
        self.wait.until(lambda _: 'No verified memories saved.' in self.text('memoryList'))
        payload={'action':'extract','text':'synthetic mountain <img src=x onerror="window.memoryLeak=true">','provenance':{'source':'synthetic browser review'},'sensitivity':'public'}
        self.assertEqual(self.memory_post('learning',payload,False)['status'],403)
        extracted=self.memory_post('learning',payload); self.assertEqual(extracted['status'],201); self.assertIn('no-store',extracted['cache'])
        self.assertEqual(store.list_memories(owner),[])
        candidate=extracted['data']['candidate_ids'][0]
        self.assertEqual(self.memory_post('learning',{'action':'verify','id':candidate,'verified':False})['status'],400)
        verified=self.memory_post('learning',{'action':'verify','id':candidate,'verified':True})
        self.assertEqual(verified['status'],200); identity=verified['data']['id']
        self.browser.refresh(); self.wait.until(lambda _: 'synthetic mountain' in self.text('memoryList'))
        self.assertFalse(self.browser.execute_script('return Boolean(window.memoryLeak)'))
        self.memory_click('#memoryList details[data-memory-correction] summary')
        correction=self.browser.find_element(self.By.CSS_SELECTOR,'#memoryList textarea')
        correction.clear(); correction.send_keys('synthetic corrected hiking preference')
        self.memory_click('#memoryList form button')
        self.assertEqual(store.list_memories(owner)[0]['id'],identity)
        self.memory_click('#memoryList details[data-memory-correction] input[type="checkbox"]')
        self.memory_click('#memoryList form button')
        self.wait.until(lambda _: self.text('memoryFeedback')=='Verified correction saved.')
        self.wait.until(lambda _: 'synthetic corrected hiking preference' in self.text('memoryList'))
        self.assertNotIn('<img',self.browser.find_element(self.By.ID,'memoryList').get_attribute('innerHTML'))
        self.assertEqual(store.restore_owner(owner),1); self.assertNotEqual(store.list_memories(owner)[0]['id'],identity)
        from selenium.webdriver.support.ui import Select
        query=self.browser.find_element(self.By.ID,'memoryEvaluationQuery')
        query.send_keys('synthetic hiking question')
        Select(self.browser.find_element(self.By.ID,'memoryEvaluationExpected')).select_by_value(store.list_memories(owner)[0]['id'])
        self.memory_click('#memoryEvaluationForm button')
        self.wait.until(lambda _: 'First match correct: yes.' in self.text('memoryEvaluationResult'))
        Select(self.browser.find_element(self.By.ID,'memoryEvaluationExpected')).select_by_value('')
        self.memory_click('#memoryEvaluationForm button')
        self.wait.until(lambda _: 'Unexpected match returned.' in self.text('memoryEvaluationResult'))
        self.capture('memory-candidate-explicit-verification-correction')

    def test_stale_correction_keeps_draft_and_requires_review_of_current_memory(self):
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.memory_learning import MemoryLearning
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-quality-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']
        original=store.save_verified(owner,{'statement':'synthetic original'}, {'source':'synthetic owner review'},verified=True)
        self.login(); self.browser.get(self.live_server_url+'/settings/')
        self.wait.until(lambda _: 'synthetic original' in self.text('memoryList'))
        self.memory_click('#memoryList details[data-memory-correction] summary')
        correction=self.browser.find_element(self.By.CSS_SELECTOR,'#memoryList textarea')
        correction.clear(); correction.send_keys('synthetic stale draft <img src=x onerror="window.memoryLeak=true">')
        self.memory_click('#memoryList details[data-memory-correction] input[type="checkbox"]')
        winner=MemoryLearning(store).revise(owner,[original],{'statement':'synthetic current winner'},verified=True)
        self.memory_click('#memoryList form button')
        self.wait.until(lambda _: 'Memory changed.' in self.text('memoryFeedback'))
        self.assertIn('synthetic stale draft',correction.get_attribute('value'))
        self.assertEqual(store.list_memories(owner)[0]['id'],winner)
        self.memory_click('#memoryRefreshButton')
        self.wait.until(lambda _: 'synthetic current winner' in self.text('memoryList'))
        self.assertFalse(self.browser.execute_script('return Boolean(window.memoryLeak)'))
        self.browser.find_element(self.By.ID,'memoryEvaluationQuery').send_keys('synthetic transient private query')
        self.browser.execute_script("window.dispatchEvent(new PageTransitionEvent('pagehide'));")
        self.assertEqual(self.text('memoryList'),'')
        self.assertEqual(self.browser.find_element(self.By.ID,'memoryEvaluationQuery').get_attribute('value'),'')
        self.assertEqual(self.text('memoryEvaluationResult'),'')
        self.capture('memory-stale-edit-requires-refresh')

    def test_encrypted_memory_sync_and_mock_reasoning_use_session_scope(self):
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-sync-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),
            ALFRED_MEMORY_SYNC_MOCK_DIR=str(root/'mock'),ALFRED_MEMORY_MOCK_REASONING=True))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']
        store.save_verified(owner,{'note':'synthetic public mountain preference'},{'source':'synthetic'},sensitivity='public',verified=True)
        self.login(); self.browser.get(self.live_server_url+'/settings/')
        self.wait.until(lambda _: 'synthetic public mountain preference' in self.text('memoryList'))
        post=self.memory_post
        configure={'action':'configure','enabled':True,'consent':True}
        self.assertEqual(post('sync',configure,False)['status'],403)
        self.assertEqual(post('sync',configure)['status'],200)
        uploaded=post('sync',{'action':'sync'}); self.assertEqual(uploaded['data']['result'],'uploaded')
        self.assertIn('no-store',uploaded['cache'])
        self.assertEqual(post('reason',{'query':'mountain','consent':False,'query_sensitivity':'public'})['status'],400)
        self.assertEqual(post('reason',{'query':'mountain','consent':True,'query_sensitivity':'public'})['status'],200)
        self.assertEqual(post('reset',{'confirm':True})['data']['deleted'],1)
        self.assertEqual(post('sync',{'action':'sync'})['status'],200)
        self.assertEqual(store.restore_owner(owner),0)
        sync=MemorySynchronizer(store,MockCloudProvider(root/'mock'))
        self.assertEqual(sync.status(owner)['revision'],2)
        self.capture('memory-encrypted-mock-sync-session')

    def test_module_navigation_banking_pagination_and_loaded_record_filters(self):
        from selenium.webdriver.common.keys import Keys
        from apps.expenses.models import BankAccount
        from apps.loans.models import Loan
        from datetime import date
        owner=self.scenario['user']; foreign=get_user_model().objects.create_user(username='synthetic-banking-other')
        BankAccount.objects.create(user=foreign,bank_name='FOREIGN-BANK-NOT-VISIBLE',account_number='987654321000',current_balance=999)
        for index in range(27):
            BankAccount.objects.create(user=owner,bank_name=f'Synthetic Bank {index:02d}',account_number=f'10000000{index:04d}',current_balance=None if index==0 else 0)
        Loan.objects.create(user=owner,loan_type='personal',lender='Zebra Synthetic Loan',principal=1000,remaining_balance=1000,emi=100,
            interest_rate=5,tenure_months=10,start_date=date(2026,1,1))
        self.login(); self.browser.get(self.live_server_url+'/expenses/#bankAccountsPanel')
        self.wait.until(lambda _: 'owned accounts' in self.text('bankAccountsStatus'))
        self.assertNotIn('FOREIGN-BANK-NOT-VISIBLE',self.text('bankAccountsPanel'))
        self.assertIn('Balance unavailable',self.text('bankAccountsBody'))
        self.assertIn('****0000',self.text('bankAccountsBody'))
        self.assertNotIn('100000000000',self.text('bankAccountsBody'))
        self.memory_click('#bankAccountsNext')
        self.wait.until(lambda _: 'page 2' in self.text('bankAccountsStatus'))
        self.assertTrue(self.browser.find_element(self.By.ID,'bankAccountsPrevious').is_enabled())
        self.capture('ui-d-banking-owned-pagination')
        self.browser.get(self.live_server_url+'/loans/')
        self.wait.until(lambda _: 'Zebra Synthetic Loan' in self.text('loanTableBody'))
        search=self.browser.find_element(self.By.ID,'loanTableBodySearch'); search.send_keys('Zebra')
        self.assertIn('1 matching',self.browser.find_element(self.By.CSS_SELECTOR,'[data-table-controls="loanTableBody"] [data-table-count]').text)
        self.assertIn('Zebra',self.text('loanTableBody'))
        self.browser.execute_script("document.querySelector('[data-table-controls=loanTableBody]').scrollIntoView({block:'center',behavior:'instant'})")
        self.capture('ui-d-loan-filter')
        search.send_keys(Keys.CONTROL,'a',Keys.BACKSPACE)
        original=[row.text for row in self.browser.find_elements(self.By.CSS_SELECTOR,'#loanTableBody tr')]
        from selenium.webdriver.support.ui import Select
        Select(self.browser.find_element(self.By.ID,'loanTableBodySort')).select_by_value('desc')
        self.assertIn('Zebra',self.browser.find_elements(self.By.CSS_SELECTOR,'#loanTableBody tr')[0].text)
        Select(self.browser.find_element(self.By.ID,'loanTableBodySort')).select_by_value('')
        self.assertEqual([row.text for row in self.browser.find_elements(self.By.CSS_SELECTOR,'#loanTableBody tr')],original)
        from selenium.common.exceptions import StaleElementReferenceException
        def select_current_row(_):
            try:
                self.memory_click('#loanTableBody input[type=checkbox]')
                return True
            except StaleElementReferenceException:
                return False
        self.wait.until(select_current_row)
        search.send_keys('NO-MATCH-SYNTHETIC')
        self.assertIn('selected records retained',self.browser.find_element(self.By.CSS_SELECTOR,'[data-table-controls="loanTableBody"] [data-table-count]').text)
        self.browser.get(self.live_server_url+'/investments/')
        self.wait.until(lambda _: self.text('investmentPositionsBody'))
        search=self.browser.find_element(self.By.ID,'investmentPositionsBodySearch'); search.send_keys('NO-MATCH-SYNTHETIC')
        self.assertEqual(self.text('investmentPositionsBody'),'')
        self.assertIn('0 matching',self.browser.find_element(self.By.CSS_SELECTOR,'[data-table-controls="investmentPositionsBody"] [data-table-count]').text)
        self.browser.execute_script("document.querySelector('[data-table-controls=investmentPositionsBody]').scrollIntoView({block:'center',behavior:'instant'})")
        self.capture('ui-d-investment-empty-filter')
        self.browser.get(self.live_server_url+'/mobility/')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'plannerComposer').is_displayed())
        self.memory_click('a[href="/ai/insights/?scope=travel#intelligencePanel"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceScope').get_attribute('value')=='travel')

    def test_loan_refresh_response_does_not_replace_rows_during_table_interaction(self):
        self.login()
        self.browser.get(self.live_server_url + '/loans/')
        self.wait.until(lambda _: self.browser.find_elements(self.By.CSS_SELECTOR, '#loanTableBody input[type=checkbox]'))
        self.browser.execute_script('''
            Alfred.disableLiveRefresh('loans-live');
            const original = Alfred.fetchJSON;
            Alfred.fetchJSON = (url, options) => url !== '/api/loans/summary/' ? original(url, options) :
                original(url, options).then(payload => new Promise(resolve => {
                    window.releaseLoanResponse = () => { Alfred.fetchJSON = original; resolve(payload); };
                }));
            window.loanRefreshFinished = false;
            loadLoanPage({live:true}).finally(() => { window.loanRefreshFinished = true; });
        ''')
        self.wait.until(lambda _: self.browser.execute_script('return typeof window.releaseLoanResponse === "function"'))
        checkbox = self.browser.find_element(self.By.CSS_SELECTOR, '#loanTableBody input[type=checkbox]')
        self.browser.execute_script('window.loanRowBeforeRefresh = arguments[0]', checkbox)
        search = self.browser.find_element(self.By.ID, 'loanTableBodySearch')
        search.send_keys('NO-MATCH-SYNTHETIC')
        self.browser.execute_script('window.releaseLoanResponse()')
        self.wait.until(lambda _: self.browser.execute_script('return window.loanRefreshFinished'))
        self.assertTrue(checkbox.get_property('isConnected'))
        self.assertEqual(search.get_attribute('value'), 'NO-MATCH-SYNTHETIC')
        self.assertIn('0 matching', self.browser.find_element(self.By.CSS_SELECTOR,
            '[data-table-controls="loanTableBody"] [data-table-count]').text)
        self.assertFalse(self.browser.execute_async_script('''
            const done = arguments[0];
            document.activeElement.blur();
            document.getElementById('loanPlannerRoot').dataset.liveRefreshLockedUntil = '0';
            loadLoanPage({live:true}).then(() => done(window.loanRowBeforeRefresh.isConnected));
        '''))

    def test_currency_source_cards_and_exact_decimal_formatting(self):
        from unittest.mock import Mock
        from selenium.webdriver.support.ui import Select
        from decimal import Decimal
        from datetime import date
        from apps.loans.models import LoanClosureDocument,Loan
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-currency-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_MOCK_REASONING=False))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        local=Mock(); local.reason.return_value='Your verified closure cost $99.00 USD.'
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=local))
        owner=self.scenario['user']; loan=Loan.objects.filter(user=owner).first()
        document=LoanClosureDocument.objects.create(loan=loan,file_name='synthetic-currency.pdf',closure_amount=Decimal('1000000.01'),closure_date=date(2026,1,2),verification_status='verified')
        self.login()
        fmt=lambda amount,currency:self.browser.execute_script('return Alfred.formatRecordedMoney(arguments[0])',{'amount':amount,'currency':currency,'evidence_status':'verified'})
        self.assertEqual(fmt('1234567.89','INR'),'₹12,34,567.89 INR')
        self.assertEqual(fmt('999999999999999.99','USD'),'$999,999,999,999,999.99 USD')
        self.assertEqual(fmt('0.10','EUR'),'€0.10 EUR')
        self.assertEqual(fmt('-0.50','GBP'),'-£0.50 GBP')
        self.assertIn('Currency not recorded',fmt('1.00','UNKNOWN'))
        self.assertEqual(fmt('NaN','INR'),'Amount unavailable')
        self.assertEqual(self.browser.execute_script("return Alfred.formatRecordedMoney({amount:'0.00',currency:'INR',evidence_status:'unavailable'})"),'Financial evidence unavailable')
        self.browser.get(self.live_server_url+'/ai/insights/')
        self.wait.until(lambda _: len(self.browser.find_element(self.By.ID,'intelligenceDocument').find_elements(self.By.TAG_NAME,'option'))>1)
        Select(self.browser.find_element(self.By.ID,'intelligenceScope')).select_by_value('documents')
        Select(self.browser.find_element(self.By.ID,'intelligenceDocument')).select_by_value(str(document.pk))
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain my closure evidence')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'Unsupported model figures' in self.text('intelligenceFeedback'))
        self.assertNotIn('$99.00',self.text('intelligenceAnswers'))
        self.assertIn('1,000,000.01 · Currency not recorded',self.text('intelligenceAnswers'))
        self.assertIn('verified',self.text('intelligenceAnswers'))
        self.capture('ui-c-canonical-currency-narrative-protection')
        self.browser.get(self.live_server_url+'/')
        self.wait.until(lambda _: self.text('dashboardSummaryCards'))
        self.capture('ui-c-finance-overview')
        self.memory_click('a[href="/ai/insights/?scope=finance#intelligencePanel"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceScope').get_attribute('value')=='finance')

    def test_memory_search_candidate_review_and_selected_revocation(self):
        from selenium.webdriver.support.ui import Select
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.memory_learning import MemoryLearning
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-ui-review-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_MOCK_REASONING=False))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']; learning=MemoryLearning(store)
        first=store.save_verified(owner,{'statement':'synthetic mountain hiking','category':'Travel'},{'source':'synthetic checked itinerary'},verified=True)
        second=store.save_verified(owner,{'statement':'synthetic quiet evenings','category':'Preferences'},{'source':'synthetic owner'},verified=True)
        accept=learning.extract(owner,'synthetic preference to review',{'source':'synthetic hypothesis'})[0]
        reject=learning.extract(owner,'synthetic incorrect suggestion',{'source':'synthetic hypothesis'})[0]
        foreign=get_user_model().objects.create_user(username='synthetic-ui-review-other')
        learning.extract(foreign,'FOREIGN-UI-CANDIDATE',{'source':'synthetic other'})
        self.login(); self.browser.get(self.live_server_url+'/settings/#privateMemoryPanel')
        self.wait.until(lambda _: 'mountain hiking' in self.text('memoryList') and 'NEEDS REVIEW' in self.text('memoryCandidates'))
        self.assertEqual(self.browser.find_element(self.By.CSS_SELECTOR,'#sidebarMenu a[href="/settings/#privateMemoryPanel"]').get_attribute('aria-current'),'page')
        self.assertNotIn('FOREIGN-UI-CANDIDATE',self.text('privateMemoryPanel'))
        Select(self.browser.find_element(self.By.ID,'memoryCategory')).select_by_value('Travel')
        self.assertIn('1 of 2',self.text('memoryCount'))
        self.assertNotIn('quiet evenings',self.text('memoryList'))
        self.memory_click(f'#memory-{first} details[data-memory-correction] summary')
        correction=self.browser.find_element(self.By.CSS_SELECTOR,f'#memory-{first} details[data-memory-correction] textarea')
        correction.clear(); correction.send_keys('synthetic unsaved correction')
        search=self.browser.find_element(self.By.ID,'memorySearch'); search.send_keys('no such fact')
        self.assertIn('0 of 2',self.text('memoryCount')); search.clear(); search.send_keys('mountain')
        self.assertEqual(correction.get_attribute('value'),'synthetic unsaved correction')
        search.clear(); Select(self.browser.find_element(self.By.ID,'memoryCategory')).select_by_value('')
        accept_row=f'#memoryCandidates [data-candidate-id="{accept}"]'
        self.memory_click(accept_row+' input[type=checkbox]'); self.memory_click(accept_row+' button[type=submit]')
        self.wait.until(lambda _: 'User-confirmed memory saved' in self.text('memoryFeedback'))
        self.assertEqual(len(store.list_memories(owner)),3)
        self.assertEqual(self.browser.find_element(self.By.CSS_SELECTOR,f'#memory-{first} details[data-memory-correction] textarea').get_attribute('value'),'synthetic unsaved correction')
        self.memory_click(f'#memoryCandidates [data-candidate-id="{reject}"] button[type=button]')
        self.wait.until(lambda _: 'Suggestion rejected' in self.text('memoryFeedback'))
        self.assertEqual(learning.candidates(owner),[])
        self.memory_click(f'#memory-{first} input[data-memory-select]'); self.memory_click('#memorySelectedReset')
        self.wait.until(lambda driver: driver.switch_to.alert); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: '1 selected memories deleted' in self.text('memoryFeedback'))
        store.restore_owner(owner)
        self.assertNotIn(first,{r['id'] for r in store.list_memories(owner)})
        self.assertIn(second,{r['id'] for r in store.list_memories(owner)})
        self.assertIn('OpenAI disabled',self.text('memoryReasoningStatus'))
        self.assertIn('Billing measurements are unavailable',self.text('memoryReasoningUsage'))
        self.browser.execute_script("document.getElementById('privateMemoryPanel').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('ui-b-memory-search-review-revocation')

    def test_assistant_responsive_keyboard_retry_and_new_conversation(self):
        from unittest.mock import Mock
        from selenium.webdriver.common.keys import Keys
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        from tests.test_persistent_memory import SyntheticEmbeddings
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-ui-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'), ALFRED_MEMORY_OPENAI_AUTHORIZED=False, ALFRED_MEMORY_MOCK_REASONING=False))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=SyntheticEmbeddings()))
        local = Mock(); local.reason.side_effect = EmbeddingUnavailable('private-file-secret')
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner', return_value=local))
        self.enterContext(patch('apps.ml_engine.api.views.OllamaReasoner', return_value=local))
        self.browser.set_window_size(1440,1200)
        self.addCleanup(self.browser.set_window_size,1440,1200)
        self.login()
        self.browser.execute_script("localStorage.setItem('alfred.appearance','light')")
        self.browser.get(self.live_server_url+'/ai/insights/')
        self.wait.until(lambda _: 'Ollama available' in self.text('intelligenceLocalStatus'))
        self.assertEqual(self.text('intelligenceCloudStatus'), 'OpenAI disabled')
        question = self.browser.find_element(self.By.ID, 'intelligenceQuery')
        question.send_keys('Synthetic outage draft', Keys.CONTROL, Keys.ENTER)
        self.wait.until(lambda _: 'Ollama unavailable' in self.text('intelligenceLocalStatus'))
        self.assertEqual(question.get_attribute('value'), 'Synthetic outage draft')
        self.assertNotIn('private-file-secret', self.text('intelligenceFeedback'))
        self.capture('ui-a-outage-draft-preserved')
        local.reason.side_effect = None; local.reason.return_value = 'Synthetic hypothesis <img src=x onerror="window.uiLeak=true">'
        self.memory_click('#intelligenceRetry')
        self.wait.until(lambda _: 'AI hypothesis' in self.text('intelligenceAnswers'))
        self.assertFalse(self.browser.execute_script('return Boolean(window.uiLeak)'))
        self.assertIn('Insufficient evidence', self.text('intelligenceAnswers'))
        self.browser.execute_script("document.getElementById('alfredMainScroll').scrollTo({top:0,behavior:'instant'}); window.scrollTo({top:0,behavior:'instant'})")
        self.capture('ui-a-conversation-desktop')
        self.memory_click('#workspaceTheme')
        self.assertEqual(self.browser.execute_script('return document.documentElement.dataset.theme'), 'dark')
        contrast = """function light(rgb) { const v=rgb.match(/\\d+/g).slice(0,3).map(n=>{n=Number(n)/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4});return .2126*v[0]+.7152*v[1]+.0722*v[2] }
            const a=light(getComputedStyle(document.querySelector('#sidebarMenu .nav-link')).color), b=light(getComputedStyle(document.getElementById('sidebarMenu')).backgroundColor);
            return (Math.max(a,b)+.05)/(Math.min(a,b)+.05)"""
        self.wait.until(lambda _: self.browser.execute_script(contrast)>4.5)
        self.capture('ui-a-conversation-dark')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd, 'Emulation.clearDeviceMetricsOverride', {})
        self.memory_click('#intelligenceNew')
        self.assertEqual(self.text('intelligenceAnswers'), '')
        self.assertTrue(self.browser.find_element(self.By.ID,'intelligenceEmpty').is_displayed())
        self.assertEqual(self.browser.switch_to.active_element.get_attribute('id'), 'intelligenceQuery')
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.assertEqual(self.browser.execute_script('return innerWidth'), 390)
        self.memory_click('[aria-controls="sidebarMenu"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'sidebarMenu').is_displayed())
        self.assertIn('AI Memory', self.text('sidebarMenu'))
        self.browser.switch_to.active_element.send_keys(Keys.ESCAPE)
        self.wait.until(lambda _: not self.browser.find_element(self.By.ID,'sidebarMenu').is_displayed())
        self.browser.execute_script("document.getElementById('alfredMainScroll').scrollTo({top:0,behavior:'instant'}); window.scrollTo({top:0,behavior:'instant'})")
        self.capture('ui-a-conversation-mobile')
        self.memory_click('#workspaceTheme'); self.browser.execute_cdp_cmd('Emulation.clearDeviceMetricsOverride', {})

    def test_hybrid_insights_local_sources_verified_save_and_fresh_settings(self):
        from unittest.mock import Mock
        from selenium.webdriver.support.ui import Select
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-hybrid-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_MOCK_REASONING=False))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        local=Mock(); local.reason.return_value='Synthetic hypothesis <img src=x onerror="window.memoryLeak=true">'
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=local))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']
        identity=store.save_verified(owner,{'statement':'synthetic mountain preference'},{'source':'synthetic owner review'},verified=True)
        self.login(); self.browser.get(self.live_server_url+'/ai/insights/')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceScope').is_displayed())
        self.assertFalse(self.browser.find_element(self.By.ID,'intelligenceCloudConsent').is_enabled())
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('synthetic mountain question')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'AI hypothesis' in self.text('intelligenceAnswers'))
        self.assertIn(identity,self.text('intelligenceAnswers')); self.assertFalse(self.browser.execute_script('return Boolean(window.memoryLeak)'))
        self.assertEqual(len(store.list_memories(owner)),1)
        Select(self.browser.find_element(self.By.ID,'intelligenceScope')).select_by_value('finance')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('show my financial snapshot')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'canonical-finance' in self.text('intelligenceAnswers'))
        self.assertIn('canonical_financial_baseline',self.text('intelligenceAnswers'))
        from apps.mobility.models import TravelPreferenceProfile
        TravelPreferenceProfile.objects.update_or_create(user=owner,defaults={'novelty':0.4,'preferences':{'pace':'quiet'}})
        Select(self.browser.find_element(self.By.ID,'intelligenceScope')).select_by_value('travel')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('show my Travel preferences')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'travel-preferences' in self.text('intelligenceAnswers'))
        self.assertIn('novelty: 0.4',self.text('intelligenceAnswers'))
        self.memory_click('#intelligenceMemorySave summary')
        self.browser.find_element(self.By.ID,'intelligenceMemoryText').send_keys('synthetic owner checked hiking fact')
        self.memory_click('#intelligenceMemoryForm button')
        self.assertEqual(len(store.list_memories(owner)),1)
        self.memory_click('#intelligenceMemoryVerified'); self.memory_click('#intelligenceMemoryForm button')
        self.wait.until(lambda _: 'Verified memory saved locally.' in self.text('intelligenceFeedback'))
        self.assertEqual(len(store.list_memories(owner)),2)
        self.capture('hybrid-insights-local-grounding-verified-memory')
        self.browser.get(self.live_server_url+'/settings/')
        self.wait.until(lambda _: 'synthetic owner checked hiking fact' in self.text('memoryList'))
        self.assertEqual(MemoryStore(root/'vault').restore_owner(owner),2)

    def test_settings_sync_consent_budgets_and_explicit_public_mock_fallback(self):
        from unittest.mock import Mock
        from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-policy-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_MEMORY_SYNC_MOCK_DIR=str(root/'mock'),
            ALFRED_MEMORY_SYNC_PROVIDER='',ALFRED_MEMORY_MOCK_REASONING=True))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        local=Mock(); local.reason.side_effect=EmbeddingUnavailable('synthetic local failure')
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=local))
        store=MemoryStore(root/'vault'); owner=self.scenario['user']
        store.save_verified(owner,{'statement':'synthetic public mountain preference'},{'source':'synthetic review'},verified=True,sensitivity='public')
        self.login(); self.browser.get(self.live_server_url+'/settings/')
        self.wait.until(lambda _: 'Provider: mock.' in self.text('memorySyncStatus'))
        self.memory_click('#memorySyncEnabled'); self.memory_click('#memorySyncForm button[type=submit]')
        self.wait.until(lambda _: 'Synchronization consent saved.' in self.text('memoryCloudFeedback'))
        self.memory_click('#memorySyncNow')
        self.wait.until(lambda _: 'Revision 1;' in self.text('memorySyncStatus'))
        self.memory_click('#memoryReasoningEnabled')
        tokens=self.browser.find_element(self.By.ID,'memoryReasoningTokens'); tokens.clear(); tokens.send_keys('2000')
        dollars=self.browser.find_element(self.By.ID,'memoryReasoningDollars'); dollars.clear(); dollars.send_keys('0.005')
        self.memory_click('#memoryReasoningForm button')
        self.wait.until(lambda _: 'Reasoning policy saved.' in self.text('memoryCloudFeedback'))
        with store._transaction() as db:
            self.assertEqual(store._sync_state(db,_owner(owner))['reasoning_policy']['daily_microusd'],5000)
        self.capture('memory-sync-reasoning-owner-policy')
        self.browser.get(self.live_server_url+'/ai/insights/')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceCloudConsent').is_enabled())
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('synthetic public mountain question')
        self.memory_click('#intelligenceCloudConsent'); self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'AI hypothesis' in self.text('intelligenceAnswers'))
        self.assertIn('Mock (synthetic)',self.text('intelligenceAnswers'))
        self.assertFalse(self.browser.find_element(self.By.ID,'intelligenceCloudConsent').is_selected())
        self.capture('hybrid-public-consent-sync-policy')
        failed=Mock(); failed.embed.side_effect=EmbeddingUnavailable('synthetic local server offline')
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=failed))
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('synthetic public question while offline')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'unavailable' in self.text('intelligenceFeedback').lower())
        self.memory_click('#intelligenceCloudConsent'); self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'no saved-memory grounding' in self.text('intelligenceFeedback'))
        self.assertFalse(self.browser.find_element(self.By.ID,'intelligenceCloudConsent').is_selected())
        self.capture('hybrid-local-outage-public-query-only')

    def test_private_memory_delete_retention_reset_keep_family_isolated(self):
        from datetime import datetime, timezone, timedelta
        from selenium.webdriver.support import expected_conditions as EC
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from tests.test_persistent_memory import SyntheticEmbeddings
        root = self.enterContext(TemporaryDirectory(prefix='alfred-memory-browser-synthetic-'))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=root))
        store = MemoryStore(root, embedder=SyntheticEmbeddings())
        owner = self.scenario['user']
        other = get_user_model().objects.create_user(username='synthetic-memory-browser-family')
        removed = store.save_verified(owner, {'note': 'synthetic-delete <img src=x onerror="window.memoryLeak=true">'}, {'source': 'synthetic'}, verified=True)
        other_id = store.save_verified(other, {'note': 'synthetic-other-owner-private'}, {'source': 'synthetic'}, verified=True)
        store.save_verified(owner, {'note': 'synthetic-current-memory'}, {'source': 'synthetic'}, verified=True)
        with patch('apps.ml_engine.services.persistent_memory.datetime') as clock:
            clock.now.return_value = datetime.now(timezone.utc) - timedelta(days=10)
            clock.fromisoformat = datetime.fromisoformat
            store.save_verified(owner, {'note': 'synthetic-expiring-memory'}, {'source': 'synthetic'}, verified=True)
        self.login()
        self.browser.get(self.live_server_url + '/settings/')
        self.wait.until(lambda _: 'synthetic-delete' in self.text('memoryList'))
        self.assertNotIn('synthetic-other-owner-private', self.text('memoryList'))
        self.assertFalse(self.browser.execute_script('return Boolean(window.memoryLeak)'))
        remove=self.browser.find_element(self.By.XPATH, "//div[@id='memoryList']/div[p[contains(.,'synthetic-delete')]]/button")
        self.browser.execute_script("arguments[0].scrollIntoView({behavior:'instant',block:'center'});",remove)
        remove.click()
        self.wait.until(EC.alert_is_present()).accept()
        self.wait.until(lambda _: self.text('memoryFeedback') == 'Memory deleted.')
        self.assertNotIn('synthetic-delete', self.text('memoryList'))
        self.assertNotIn(removed, [r['id'] for r in store.list_memories(owner)])
        self.assertEqual(store.restore_owner(owner), 2)
        days = self.browser.find_element(self.By.ID, 'memoryRetentionDays')
        days.clear()
        days.send_keys('1')
        self.memory_click('#memoryRetentionForm button')
        self.wait.until(lambda _: self.text('memoryFeedback') == 'Memory retention saved.')
        self.assertNotIn('synthetic-expiring-memory', self.text('memoryList'))
        self.assertIn('synthetic-current-memory', self.text('memoryList'))
        self.memory_click('#memoryResetButton')
        self.wait.until(EC.alert_is_present()).accept()
        self.wait.until(lambda _: self.text('memoryFeedback') == 'Your memories were reset.')
        self.assertIn('No verified memories saved.', self.text('memoryList'))
        self.assertEqual(store.restore_owner(owner), 0)
        self.assertEqual(store.list_memories(other)[0]['id'], other_id)

    def test_login_limit_shows_feedback_then_recovers_after_window(self):
        from datetime import timedelta
        from django.utils import timezone
        from selenium.webdriver.support import expected_conditions as EC
        now = timezone.now()
        with override_settings(ALFRED_LOGIN_ACCOUNT_LIMIT=1), patch('django.utils.timezone.now', return_value=now):
            self.browser.get(self.live_server_url + '/login/')
            self.browser.find_element(self.By.NAME, 'username').send_keys('acceptance_demo')
            self.browser.find_element(self.By.NAME, 'password').send_keys('synthetic-wrong-password')
            self.browser.find_element(self.By.CSS_SELECTOR, 'button[type="submit"]').click()
            self.wait.until(EC.text_to_be_present_in_element((self.By.TAG_NAME, 'body'), 'Invalid username or password'))
            self.browser.get(self.live_server_url + '/login/')
            self.browser.find_element(self.By.NAME, 'username').send_keys('acceptance_demo')
            self.browser.find_element(self.By.NAME, 'password').send_keys(PASSWORD)
            self.browser.find_element(self.By.CSS_SELECTOR, 'button[type="submit"]').click()
            self.wait.until(EC.text_to_be_present_in_element((self.By.TAG_NAME, 'body'), 'Too many requests'))
            self.capture('m14-login-limit-feedback')
        with patch('django.utils.timezone.now', return_value=now + timedelta(seconds=601)):
            self.login()
            self.capture('m14-login-limit-recovered')

    def private_history_fixture(self, authorized=True):
        from unittest.mock import Mock
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.conversation_history import ConversationHistory
        from tests.test_persistent_memory import SyntheticEmbeddings
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-history-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),
            ALFRED_CONVERSATION_HISTORY_AUTHORIZED=authorized, ALFRED_MEMORY_OPENAI_AUTHORIZED=False,
            ALFRED_MEMORY_MOCK_REASONING=False, ALFRED_MEMORY_SYNC_PROVIDER=''))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=SyntheticEmbeddings()))
        local = Mock(); local.reason.return_value = 'Synthetic historical hypothesis <img src=x onerror="window.historyLeak=true">'
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner', return_value=local))
        self.enterContext(patch('apps.ml_engine.api.views.OllamaReasoner', return_value=local))
        self.login(); self.browser.get(self.live_server_url+'/ai/insights/')
        self.wait.until(lambda _: self.text('conversationHistoryStatus') != 'Checking local policy')
        self.memory_click('#conversationHistoryPanel > summary')
        return ConversationHistory(MemoryStore(root/'vault')), local

    def enable_private_history_ui(self):
        self.memory_click('#conversationHistoryConsent')
        self.memory_click('#conversationHistoryForm button')
        self.wait.until(lambda _: self.text('conversationHistoryStatus') == 'On · local only')

    def ask_history_question(self, text):
        from selenium.webdriver.common.keys import Keys
        question = self.browser.find_element(self.By.ID, 'intelligenceQuery')
        self.wait.until(lambda _: not question.get_property('readOnly') and
            self.browser.find_element(self.By.CSS_SELECTOR, '#intelligenceForm button[type=submit]').is_enabled())
        question.clear(); question.send_keys(text, Keys.CONTROL, Keys.ENTER)

    def test_private_history_consent_reload_delete_clear_disable_and_mobile(self):
        from django.contrib.auth import get_user_model
        history, local = self.private_history_fixture(); owner = self.scenario['user']
        self.assertFalse(history.policy(owner)['enabled'])
        self.ask_history_question('Synthetic unsaved question')
        self.wait.until(lambda _: 'AI hypothesis' in self.text('intelligenceAnswers'))
        self.assertEqual(history.policy(owner)['conversations'], 0)
        self.enable_private_history_ui()
        self.assertEqual(self.text('intelligenceAnswers'), '')
        title = 'Synthetic <img src=x onerror="window.historyLeak=true">'
        self.browser.find_element(self.By.ID, 'conversationHistoryTitle').send_keys(title)
        self.ask_history_question('Synthetic private saved question')
        self.wait.until(lambda _: 'Saved locally' in self.text('conversationHistoryCurrent'))
        self.wait.until(lambda _: bool(self.browser.find_elements(self.By.CSS_SELECTOR, '#conversationHistoryList button')))
        self.assertTrue(self.browser.find_element(self.By.ID, 'intelligenceCloudConsent').get_property('disabled'))
        self.assertEqual(len(history.list(owner)), 1)
        self.assertEqual(len(history.get(owner, history.list(owner)[0]['id'])['turns']), 1)
        self.assertEqual(history.store.list_memories(owner), [])
        calls = local.reason.call_count
        self.browser.refresh()
        self.wait.until(lambda _: self.text('conversationHistoryStatus') == 'On · local only')
        self.assertEqual(self.text('intelligenceAnswers'), '')
        self.memory_click('#conversationHistoryPanel > summary')
        self.memory_click('#conversationHistoryList li button:first-child')
        self.wait.until(lambda _: 'Historical AI hypothesis' in self.text('intelligenceAnswers'))
        self.assertEqual(local.reason.call_count, calls)
        self.assertFalse(self.browser.execute_script('return Boolean(window.historyLeak)'))
        self.assertFalse(self.browser.find_elements(self.By.CSS_SELECTOR, '#intelligenceAnswers .recorded-amount'))
        self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR, '#intelligenceAnswers button').is_displayed())
        stored = self.browser.execute_script('return JSON.stringify(localStorage)+JSON.stringify(sessionStorage)')
        self.assertNotIn(title, stored); self.assertNotIn('Synthetic private saved question', stored)
        self.capture('history-reopened-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd, 'Emulation.clearDeviceMetricsOverride', {})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.capture('history-reopened-mobile')
        other = get_user_model().objects.create_user(username='history-browser-other')
        history.configure(other, enabled=True, consent=True, days=1); history.create(other, 'Other owner')
        self.memory_click('#conversationHistoryList li button:nth-child(2)'); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: history.policy(owner)['conversations'] == 0)
        self.wait.until(lambda _: not self.browser.find_elements(self.By.CSS_SELECTOR, '#conversationHistoryList button'))
        self.ask_history_question('Synthetic second saved question')
        self.wait.until(lambda _: history.policy(owner)['conversations'] == 1)
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, 'conversationHistoryClear').is_enabled())
        self.memory_click('#conversationHistoryClear'); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: history.policy(owner)['conversations'] == 0)
        self.wait.until(lambda _: 'cleared' in self.text('conversationHistoryFeedback'))
        self.assertTrue(history.policy(owner)['enabled'])
        self.ask_history_question('Synthetic third saved question')
        self.wait.until(lambda _: history.policy(owner)['conversations'] == 1)
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, 'conversationHistoryDisable').is_enabled())
        self.memory_click('#conversationHistoryDisable'); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: self.text('conversationHistoryStatus') == 'Off')
        self.assertEqual(history.policy(owner)['conversations'], 0)
        self.assertEqual(len(history.list(other)), 1)

    def test_private_history_outage_stale_edit_and_clear_keep_drafts(self):
        from uuid import uuid4
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        history, local = self.private_history_fixture(); owner = self.scenario['user']
        self.enable_private_history_ui()
        local.reason.side_effect = EmbeddingUnavailable('synthetic-private-exception')
        self.ask_history_question('Synthetic retry draft')
        self.wait.until(lambda _: 'Ollama unavailable' in self.text('intelligenceLocalStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), 'Synthetic retry draft')
        self.assertNotIn('synthetic-private-exception', self.text('intelligenceFeedback'))
        local.reason.side_effect = None
        self.memory_click('#intelligenceRetry')
        self.wait.until(lambda _: 'AI hypothesis' in self.text('intelligenceAnswers'))
        self.wait.until(lambda _: not self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('readOnly'))
        record = history.list(owner)[0]; request_id = uuid4().hex
        question = dict(query='Synthetic concurrent question', scope='general', document_id=None)
        generation, _ = history.prepare(owner, record['id'], record['revision'], request_id, question)
        history.append(owner, record['id'], record['revision'], request_id, question,
            dict(answer='Synthetic concurrent answer', provider='ollama', classification='ai_generated_hypothesis', financial_authority=False), generation)
        calls = local.reason.call_count
        self.ask_history_question('Synthetic stale draft')
        self.wait.until(lambda _: 'Reopen this conversation' in self.text('intelligenceFeedback'))
        self.assertEqual(local.reason.call_count, calls)
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), 'Synthetic stale draft')
        self.assertFalse(self.browser.find_element(self.By.ID, 'intelligenceRetry').is_displayed())
        self.memory_click('#conversationHistoryList li button:first-child')
        self.wait.until(lambda _: 'Synthetic concurrent answer' in self.text('intelligenceAnswers'))
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), 'Synthetic stale draft')
        self.ask_history_question('Synthetic stale draft')
        try:
            self.wait.until(lambda _: history.get(owner, record['id'])['revision'] == 3)
        except Exception:
            self.capture('history-reopen-save-failure')
            raise
        self.wait.until(lambda _: not self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('readOnly'))
        def clear_during_answer(*args, **kwargs):
            history.clear(owner)
            return 'Synthetic answer rejected after clear'
        local.reason.side_effect = clear_during_answer
        self.ask_history_question('Synthetic clear draft')
        self.wait.until(lambda _: 'Conversation no longer available' in self.text('intelligenceFeedback'))
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), 'Synthetic clear draft')
        self.assertEqual(self.text('intelligenceAnswers'), '')
        self.assertEqual(history.list(owner), [])
        self.capture('history-stale-draft-preserved')

    def test_private_history_operator_gate_logout_and_cached_page_clear(self):
        from django.conf import settings
        from django.contrib.sessions.models import Session
        history, local = self.private_history_fixture(authorized=False); owner = self.scenario['user']
        self.assertIn('operator retention/recovery approval', self.text('conversationHistoryStatus'))
        self.assertFalse(self.browser.find_element(self.By.ID, 'conversationHistoryConsent').is_enabled())
        self.assertFalse(history.policy(owner)['enabled'])
        settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED = True
        self.browser.refresh()
        self.wait.until(lambda _: self.text('conversationHistoryStatus') == 'Off')
        self.memory_click('#conversationHistoryPanel > summary'); self.enable_private_history_ui()
        self.ask_history_question('Synthetic sensitive conversation')
        self.wait.until(lambda _: 'AI hypothesis' in self.text('intelligenceAnswers'))
        self.wait.until(lambda _: not self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('readOnly'))
        self.browser.find_element(self.By.ID, 'intelligenceQuery').send_keys('Synthetic unsent private draft')
        self.browser.execute_script("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
        self.assertEqual(self.text('intelligenceAnswers'), '')
        self.assertEqual(self.text('conversationHistoryList'), '')
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), '')
        self.browser.execute_script("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        self.wait.until(lambda _: self.text('conversationHistoryStatus') == 'On · local only')
        self.memory_click('#conversationHistoryList li button:first-child')
        self.wait.until(lambda _: 'Historical AI hypothesis' in self.text('intelligenceAnswers'))
        session_key = self.browser.get_cookie('sessionid')['value']
        def logout_during_answer(*args, **kwargs):
            Session.objects.filter(session_key=session_key).delete()
            return 'Synthetic answer rejected after logout'
        local.reason.side_effect = logout_during_answer
        self.ask_history_question('Synthetic logout draft')
        self.wait.until(lambda _: 'Session or history permission' in self.text('intelligenceFeedback'))
        self.assertEqual(self.text('intelligenceAnswers'), '')
        self.assertEqual(self.text('conversationHistoryList'), '')
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), '')
        self.assertEqual(len(history.get(owner, history.list(owner)[0]['id'])['turns']), 1)
        self.capture('history-logout-cleared')

    def test_private_history_never_reuses_public_cloud_consent(self):
        from apps.ml_engine.services.memory_reasoning import configure_reasoning
        from apps.ml_engine.services.hybrid_intelligence import hybrid_answer
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        history, local = self.private_history_fixture()
        self.enterContext(override_settings(ALFRED_MEMORY_MOCK_REASONING=True))
        configure_reasoning(history.store, self.scenario['user'], enabled=True, consent=True,
            daily_tokens=4096, daily_microusd=10000)
        local.reason.side_effect = EmbeddingUnavailable('synthetic local outage')
        self.browser.refresh()
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, 'intelligenceCloudConsent').is_enabled())
        self.assertIn('OpenAI disabled', self.text('intelligenceCloudStatus'))
        with patch('apps.ml_engine.api.views.hybrid_answer', wraps=hybrid_answer) as request:
            self.ask_history_question('Synthetic public retry question')
            self.wait.until(lambda _: 'Ollama unavailable' in self.text('intelligenceLocalStatus'))
            self.assertFalse(request.call_args.kwargs['cloud_consent'])
            self.memory_click('#intelligenceCloudConsent'); self.memory_click('#intelligenceRetry')
            self.wait.until(lambda _: 'Mock (synthetic)' in self.text('intelligenceAnswers'))
            self.assertTrue(request.call_args.kwargs['cloud_consent'])
            self.memory_click('#conversationHistoryPanel > summary'); self.enable_private_history_ui()
            self.assertFalse(self.browser.find_element(self.By.ID, 'intelligenceCloudConsent').is_enabled())
            self.browser.execute_script("document.getElementById('intelligenceCloudConsent').checked=true")
            self.ask_history_question('Synthetic private local draft')
            self.wait.until(lambda _: 'Ollama unavailable' in self.text('intelligenceLocalStatus'))
            self.assertFalse(request.call_args.kwargs['cloud_consent'])
        self.assertEqual(self.browser.find_element(self.By.ID, 'intelligenceQuery').get_property('value'), 'Synthetic private local draft')
        record = history.list(self.scenario['user'])[0]
        self.assertEqual(history.get(self.scenario['user'], record['id'])['turns'], [])

    def capture(self, name):
        self.browser.save_screenshot(str(self.artifacts / f"{name}.png"))
        (self.artifacts / f"{name}.txt").write_text(self.browser.find_element(self.By.TAG_NAME, "body").text, encoding="utf-8")

    def bank_statement_evidence_fixture(self):
        from datetime import date
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.expenses.models import BankAccount, StatementUpload
        from apps.expenses.services.statement_lifecycle import _import_statement_transactions
        from apps.expenses.services.statement_evidence import evidence
        from tests.test_expense_money_identity import parsed_fixture
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-ground-browser-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media', ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
            ALFRED_MEMORY_DIR=str(root/'unused-vault'),ALFRED_MEMORY_OPENAI_AUTHORIZED=False,
            ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_SYNC_PROVIDER=''))
        owner=self.scenario['user']
        account=BankAccount.objects.create(user=owner,account_number='TEST0001',current_balance='10.01')
        upload=StatementUpload.objects.create(user=owner,bank_account=account,account_number=account.account_number,
            source='bank_statement',parser_status='parsed',file_name='Synthetic September statement.pdf',
            original_file=SimpleUploadedFile('synthetic-source.pdf',b'%PDF-synthetic-bank-source-only'),
            statement_start=date(2026,9,1),statement_end=date(2026,9,30),
            extracted_payload={'raw_text_excerpt':'SYNTHETIC-RAW-DOCUMENT-NEVER-PROMPT'})
        _import_statement_transactions(user=owner,upload=upload,bank_account=account,parsed=parsed_fixture())
        row=Expense.objects.get(statement_upload=upload)
        return row,upload,evidence(owner,row.pk)

    def test_bank_statement_citation_confirmation_correction_and_revocation(self):
        from apps.expenses.models import BankAccount
        from apps.expenses.services.statement_evidence import evidence
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        row,upload,item=self.bank_statement_evidence_fixture(); owner=self.scenario['user']
        self.login(); self.browser.get(self.live_server_url+item['citation_url'])
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='needs_owner_review')
        self.capture('bank-evidence-initial')
        self.assertEqual(self.text('statementEvidenceStatus'),'needs_owner_review')
        before=[list(model.objects.values()) for model in (Expense,BankAccount)]
        baseline=resolve_canonical_financial_baseline(owner)['decimal_amounts']
        self.memory_click('#statementEvidenceForm button[type=submit]')
        self.assertEqual(evidence(owner,row.pk)['verification'],'needs_owner_review')
        self.memory_click('#statementEvidenceConfirm'); self.memory_click('#statementEvidenceForm button[type=submit]')
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='owner_confirmed')
        self.assertEqual([list(model.objects.values()) for model in (Expense,BankAccount)],before)
        self.assertEqual(resolve_canonical_financial_baseline(owner)['decimal_amounts'],baseline)
        self.capture('bank-evidence-owner-confirmed')
        status=self.browser.execute_async_script('''
            const [id,done]=arguments;
            Alfred.fetchJSON(`/api/expenses/${id}/`,{method:'PATCH',body:JSON.stringify({amount:'7.77'})})
                .then(()=>done(200)).catch(error=>done(error.status));
        ''',row.pk)
        self.assertEqual(status,200)
        self.browser.refresh()
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='needs_owner_review')
        self.assertEqual(self.text('statementEvidenceStatus'),'needs_owner_review')
        self.assertIn('7.77',self.text('statementEvidence')); self.assertIn('2.68',self.text('statementEvidence'))
        self.memory_click('#statementEvidenceConfirm'); self.memory_click('#statementEvidenceForm button[type=submit]')
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='owner_confirmed')
        self.memory_click('#statementEvidenceRevoke'); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='needs_owner_review')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.capture('bank-evidence-correction-mobile')

    def test_bank_grounding_review_to_answer_correction_and_private_citation(self):
        from datetime import date
        from unittest.mock import Mock
        from apps.expenses.models import BankAccount
        from apps.expenses.services.statement_evidence import evidence, review
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from tests.test_persistent_memory import SyntheticEmbeddings
        row,upload,item=self.bank_statement_evidence_fixture(); owner=self.scenario['user']
        # An older citation must reopen even when it is outside the bounded recent-record menu.
        Expense.objects.bulk_create([Expense(user=owner,bank_account=row.bank_account,statement_upload=upload,
            source='bank_statement',amount='1.23',transaction_date=date(2026,9,day)) for day in range(2,22)])
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        local=Mock(); local.reason.return_value='Synthetic hypothesis: review this selected record and its source.'
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=local))
        self.enterContext(patch('apps.ml_engine.api.views.OllamaReasoner',return_value=Mock()))
        cloud=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reason_with_memory',side_effect=AssertionError('No bank cloud')))
        self.login(); self.browser.get(self.live_server_url+f'/ai/insights/?scope=bank_statements&transaction={row.pk}')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceStatement').get_property('value')==str(row.pk))
        question='Explain this synthetic statement record'
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys(question)
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'Insufficient evidence.' in self.text('intelligenceFeedback'))
        self.assertIn('Local evidence check',self.text('intelligenceAnswers'))
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceQuery').get_property('value'),question)
        local.reason.assert_not_called()
        self.assertFalse(self.browser.find_element(self.By.ID,'intelligenceCloudConsent').is_enabled())
        self.capture('bank-grounding-unreviewed')
        self.memory_click('#intelligenceAnswers a[href^="/documents/statements/"]')
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='needs_owner_review')
        self.memory_click('#statementEvidenceConfirm'); self.memory_click('#statementEvidenceForm button[type=submit]')
        self.wait.until(lambda _: self.text('statementEvidenceStatus')=='owner_confirmed')
        self.memory_click('a[href^="/ai/insights/?scope=bank_statements"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceStatement').get_property('value')==str(row.pk))
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys(question)
        before=[list(model.objects.values()) for model in (Expense,BankAccount)]
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'owner_confirmed_statement_record' in self.text('intelligenceAnswers'))
        self.assertIn(upload.file_name,self.text('intelligenceAnswers'))
        self.assertIn('2.68 · Currency not recorded',self.text('intelligenceAnswers'))
        self.assertIn('2026-09-01',self.text('intelligenceAnswers'))
        self.assertEqual([list(model.objects.values()) for model in (Expense,BankAccount)],before)
        self.assertEqual(MemoryStore(settings.ALFRED_MEMORY_DIR,embedder=SyntheticEmbeddings()).list_memories(owner),[])
        self.capture('bank-grounding-confirmed-source-card')
        status=self.browser.execute_async_script('''
            const [id,done]=arguments;
            Alfred.fetchJSON(`/api/expenses/${id}/`,{method:'PATCH',body:JSON.stringify({amount:'7.77'})})
                .then(()=>done(200)).catch(error=>done(error.status));
        ''',row.pk)
        self.assertEqual(status,200)
        self.memory_click('#intelligenceNew')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys(question)
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'Insufficient evidence.' in self.text('intelligenceFeedback'))
        self.assertNotIn('2.68',self.text('intelligenceAnswers'))
        self.assertNotIn('7.77',self.text('intelligenceAnswers'))
        self.assertEqual(evidence(owner,row.pk)['original']['amount'],'2.68')
        current=evidence(owner,row.pk); review(owner,row.pk,revision=current['revision'],confirm=True)
        self.memory_click('#intelligenceRetry')
        self.wait.until(lambda _: '7.77 · Currency not recorded' in self.text('intelligenceAnswers'))
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.querySelector('#intelligenceAnswers article:last-child').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('bank-grounding-corrected-mobile')
        self.browser.execute_script("document.querySelector('#intelligenceAnswers article:last-child .recorded-amount').scrollIntoView({block:'center',behavior:'instant'})")
        self.capture('bank-grounding-corrected-amount-mobile')
        cloud.assert_not_called()

    def test_bank_grounding_outage_and_source_revocation_preserve_draft(self):
        from unittest.mock import Mock
        from apps.expenses.services.statement_evidence import evidence, review
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        from tests.test_persistent_memory import SyntheticEmbeddings
        row,upload,item=self.bank_statement_evidence_fixture(); owner=self.scenario['user']
        review(owner,row.pk,revision=item['revision'],confirm=True)
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        local=Mock(); local.reason.side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE-DETAIL')
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=local))
        self.enterContext(patch('apps.ml_engine.api.views.OllamaReasoner',return_value=Mock()))
        cloud=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reasoning_provider',side_effect=AssertionError('No fallback')))
        self.login(); self.browser.get(self.live_server_url+f'/ai/insights/?scope=bank_statements&transaction={row.pk}')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceStatement').get_property('value')==str(row.pk))
        question='Keep this synthetic question through outage'
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys(question)
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'Ollama unavailable' in self.text('intelligenceLocalStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceQuery').get_property('value'),question)
        self.assertNotIn('SYNTHETIC-PRIVATE-DETAIL',self.text('intelligenceFeedback'))
        current=evidence(owner,row.pk); review(owner,row.pk,revision=current['revision'],confirm=True,revoke=True)
        local.reason.side_effect=None; local.reason.return_value='Synthetic local answer'
        local.reason.reset_mock()
        self.memory_click('#intelligenceRetry')
        self.wait.until(lambda _: 'Insufficient evidence.' in self.text('intelligenceFeedback'))
        local.reason.assert_not_called(); cloud.assert_not_called()
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceQuery').get_property('value'),question)
        self.assertEqual(self.text('conversationHistoryStatus'),'Unavailable · operator retention/recovery approval required')
        self.capture('bank-grounding-outage-revocation-draft')
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('intelligenceAnswers'),'')
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceStatement').find_elements(self.By.TAG_NAME,'option'),[])

    def canonical_grounding_fixture(self):
        from datetime import date
        from unittest.mock import Mock
        from apps.budgets.models import Budget
        from apps.loans.models import Loan
        from apps.investments.models import Investment
        from tests.test_persistent_memory import SyntheticEmbeddings
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-canonical-browser-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'),ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
            ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_CLOUD_AUTHORIZED=False,ALFRED_MEMORY_SYNC_PROVIDER=''))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings',return_value=SyntheticEmbeddings()))
        local=Mock(); local.reason.return_value='Synthetic recorded-value hypothesis. Review the owner source and limitations.'
        self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner',return_value=local))
        self.enterContext(patch('apps.ml_engine.api.views.OllamaReasoner',return_value=Mock()))
        owner=self.scenario['user']
        rows={'expense':Expense.objects.create(user=owner,amount='12.34',source='manual',transaction_date=date(2026,9,1)),
            'budget':Budget.objects.create(user=owner,month='Jan 2025',base_budget='234.56',inflation_adjusted='245.67',spent='12.34'),
            'loan':Loan.objects.create(user=owner,principal='1000.01',emi='100.01',remaining_balance='900.01',
                interest_rate=5,tenure_months=12,start_date=date(2026,1,1)),
            'investment':Investment.objects.create(user=owner,asset_name='SYNTHETIC-PRIVATE-ASSET',asset_type='equity',
                invested_amount='1234.56',current_value='2345.67'), 'baseline':owner}
        return rows,local

    def financial_source_selection_fixture(self,kind):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.investments.models import InvestmentImportDocument
        from apps.investments.services import document_evidence as investment
        from apps.loans.models import LoanImportDocument
        from apps.loans.services import document_evidence as loan
        rows,local=self.canonical_grounding_fixture(); row=rows[kind]; owner=self.scenario['user']
        media=Path(self.enterContext(TemporaryDirectory(prefix='alfred-source-selection-browser-')))
        self.enterContext(override_settings(MEDIA_ROOT=media))
        model,service=(InvestmentImportDocument,investment) if kind=='investment' else (LoanImportDocument,loan)
        documents=[]
        for index in range(7):
            document=model.objects.create(user=owner,file_name=f'Synthetic {kind} source {index+1}.pdf',
                uploaded_file=SimpleUploadedFile('synthetic.pdf',f'%PDF-SYNTHETIC-{kind}-{index}'.encode()),parser_status='parsed')
            getattr(document,f'linked_{kind}s').add(row); service.capture_import(document,[row])
            service.review(owner,document.pk,row.pk,revision=service.evidence(owner,document.pk,row.pk)['revision'],
                fields=list(service.FIELDS),confirm=True)
            documents.append(document)
        self.login()
        self.browser.get(self.live_server_url+f'/ai/insights/?scope=financial_records&record_type={kind}&record_id={row.pk}')
        self.wait.until(lambda _: '7 linked files' in self.text('intelligenceSourcesStatus'))
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceSourcesNext').is_enabled())
        return row,documents,service,local

    def financial_document_question_fixture(self):
        from decimal import Decimal
        row,documents,service,local=self.financial_source_selection_fixture('investment')
        owner=self.scenario['user']; document=documents[-1]
        document.file_name='Synthetic <img src=x onerror="window.documentQuestionLeak=true">.pdf'; document.save()
        records=[row]
        for index in range(6):
            records.append(type(row).objects.create(user=owner,asset_type='equity',asset_name=f'Synthetic selected holding {index}',
                invested_amount='100.01',current_value=Decimal('120.05')+index,monthly_sip='1.00'))
        document.linked_investments.add(*records); service.capture_import(document,records)
        for record in records:
            detail=service.evidence(owner,document.pk,record.pk)
            service.review(owner,document.pk,record.pk,revision=detail['revision'],fields=['current_value'],confirm=True)
        return document,records,service,local

    def test_financial_document_questions_explicit_records_pages_citations_and_privacy(self):
        from selenium.webdriver.support.ui import Select
        document,records,service,local=self.financial_document_question_fixture()
        self.browser.get(self.live_server_url+'/documents/')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'documentSourcesKind').is_enabled())
        Select(self.browser.find_element(self.By.ID,'documentSourcesKind')).select_by_value('investment')
        self.wait.until(lambda _: '7 supported entries' in self.text('documentSourcesStatus'))
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('documentSourcesStatus'))
        self.memory_click(f'#documentSourcesItems button[data-document-id="{document.pk}"]')
        self.wait.until(lambda _: 'linked records' in self.text('documentSourcesStatus'))
        self.memory_click('#documentSourcesItems a[href*="scope=financial_document"]')
        self.wait.until(lambda _: '7 linked records' in self.text('intelligenceSourcesStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceScope').get_property('value'),'financial_document')
        self.assertIn('0/3 selected',self.text('intelligenceSourcesStatus'))
        self.assertIn('page-only',self.text('conversationHistoryCurrent'))
        self.assertTrue(self.browser.find_element(self.By.ID,'intelligenceCloudConsent').get_property('disabled'))
        draft=self.browser.find_element(self.By.ID,'intelligenceQuery'); draft.send_keys('Explain selected records')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.assertIn('Choose current reviewed',self.text('intelligenceFeedback')); local.reason.assert_not_called()
        for record in records[:2]: self.memory_click(f'#intelligenceSourceItems input[value="{record.pk}"]')
        self.memory_click('#intelligenceSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('intelligenceSourcesStatus'))
        self.memory_click(f'#intelligenceSourceItems input[value="{records[-1].pk}"]')
        self.memory_click(f'#intelligenceSourceItems input[value="{records[-2].pk}"]')
        self.assertIn('Three-record limit',self.text('intelligenceSourcesStatus'))
        self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{records[-2].pk}"]').is_selected())
        self.memory_click('#intelligenceSourcesPrevious')
        self.wait.until(lambda _: 'Page 1' in self.text('intelligenceSourcesStatus'))
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{records[0].pk}"]').is_selected())
        self.assertIn('3/3 selected',self.text('intelligenceSourcesStatus'))
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: f'canonical-investment-{records[-1].pk}' in self.text('intelligenceAnswers'))
        selected=(records[0],records[1],records[-1]); owner=self.scenario['user']
        for record in selected:
            citation=service.evidence(owner,document.pk,record.pk)['citation_url']
            self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceAnswers a[href="{citation}"]').is_displayed())
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#intelligenceAnswers .recorded-amount')),3)
        self.assertNotIn(f'canonical-investment-{records[2].pk}',self.text('intelligenceAnswers'))
        self.assertIn('Currency not recorded',self.text('intelligenceAnswers'))
        self.assertIn('not_reviewed_from_selected_document',self.text('intelligenceAnswers'))
        prompt=json.dumps(local.reason.call_args.args[0])
        self.assertNotIn('documentQuestionLeak',prompt); self.assertNotIn('/documents/',prompt)
        self.assertFalse(self.browser.execute_script('return Boolean(window.documentQuestionLeak)'))
        self.assertEqual(draft.get_property('value'),'')
        self.browser.execute_script("document.getElementById('intelligenceSources').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('document-questions-record-picker-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.getElementById('intelligenceSources').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('document-questions-record-picker-mobile')
        citation=service.evidence(owner,document.pk,records[1].pk)['citation_url']
        self.memory_click(f'#intelligenceAnswers a[href="{citation}"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.assertIn('120.05',self.text('statementEvidence')); self.capture('document-questions-private-citation')
        self.browser.back()
        self.wait.until(lambda _: '7 linked records' in self.text('intelligenceSourcesStatus'))
        self.assertIn('0/3 selected',self.text('intelligenceSourcesStatus'))
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        for identity in ('intelligenceSourceItems','intelligenceSourcesSelected','intelligenceFinancialDocumentContext','intelligenceAnswers'):
            self.assertEqual(self.text(identity),'')

    def test_financial_document_field_questions_require_every_selected_reviewed_value(self):
        document,records,service,local=self.financial_document_question_fixture(); owner=self.scenario['user']
        detail=service.evidence(owner,document.pk,records[0].pk)
        service.review(owner,document.pk,records[0].pk,revision=detail['revision'],fields=['invested_amount'],confirm=True)
        cloud=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reasoning_provider'))
        self.browser.get(self.live_server_url+f'/ai/insights/?scope=financial_document&record_type=investment&document_id={document.pk}')
        self.wait.until(lambda _: '7 linked records' in self.text('intelligenceSourcesStatus'))
        for row in records[:2]: self.memory_click(f'#intelligenceSourceItems input[value="{row.pk}"]')
        draft=self.browser.find_element(self.By.ID,'intelligenceQuery'); draft.send_keys('Show invested amount')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Insufficient evidence' in self.text('intelligenceFeedback'))
        self.assertEqual(draft.get_property('value'),'Show invested amount'); local.reason.assert_not_called()
        self.memory_click(f'#intelligenceSourceItems input[value="{records[1].pk}"]')
        self.memory_click('#intelligenceRetry')
        self.wait.until(lambda _: 'Ollama available' in self.text('intelligenceLocalStatus'))
        self.assertIn('1,234.56',self.text('intelligenceAnswers')); self.assertEqual(draft.get_property('value'),'')
        self.assertEqual(local.reason.call_count,1)
        records[0].current_value='4321.09'; records[0].save()
        detail=service.evidence(owner,document.pk,records[0].pk)
        service.review(owner,document.pk,records[0].pk,revision=detail['revision'],fields=['current_value'],confirm=True)
        local.reason.reset_mock(); draft.send_keys('Show current value')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Selected evidence changed' in self.text('intelligenceSourcesStatus'))
        self.assertEqual(draft.get_property('value'),'Show current value'); local.reason.assert_not_called()
        self.memory_click('#intelligenceSourcesRefresh')
        self.wait.until(lambda _: '0/3 selected' in self.text('intelligenceSourcesStatus'))
        self.memory_click(f'#intelligenceSourceItems input[value="{records[0].pk}"]')
        local.reason.return_value='The amount is INR 99999.99.'
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Unsupported model figures were withheld' in self.text('intelligenceFeedback'))
        self.assertIn('4,321.09',self.text('intelligenceAnswers')); self.assertIn('Currency not recorded',self.text('intelligenceAnswers'))
        self.assertNotIn('99999.99',self.text('intelligenceAnswers'))
        citation=service.evidence(owner,document.pk,records[0].pk)['citation_url']
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceAnswers a[href="{citation}"]').is_displayed())
        cloud.assert_not_called()
        self.browser.execute_script("document.querySelector('#intelligenceAnswers > article:last-child').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('document-field-questions-reviewed-current-values')

    def test_financial_document_questions_stale_outage_retry_and_no_history(self):
        from selenium.webdriver.support.ui import Select
        from uuid import uuid4
        from apps.ml_engine.services.conversation_history import ConversationHistory
        from apps.ml_engine.services.persistent_memory import MemoryStore
        from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
        document,records,service,local=self.financial_document_question_fixture()
        # Synthetic consent only: document questions must remain page-only even for an opted-in owner.
        self.enterContext(override_settings(ALFRED_CONVERSATION_HISTORY_AUTHORIZED=True))
        history=ConversationHistory(MemoryStore(settings.ALFRED_MEMORY_DIR)); owner=self.scenario['user']
        history.configure(owner,enabled=True,consent=True,days=1); saved=history.create(owner,'Synthetic retained empty conversation')
        self.browser.get(self.live_server_url+f'/ai/insights/?scope=financial_document&record_type=investment&document_id={document.pk}')
        self.wait.until(lambda _: '7 linked records' in self.text('intelligenceSourcesStatus'))
        self.assertEqual(self.text('conversationHistoryStatus'),'On · local only')
        self.assertIn('never saved',self.text('conversationHistoryCurrent'))
        self.memory_click('#conversationHistoryPanel > summary')
        self.memory_click('#conversationHistoryList li button:first-child')
        self.wait.until(lambda _: 'Historical hypotheses only' in self.text('conversationHistoryFeedback'))
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceScope').is_enabled())
        self.wait.until(lambda _: '7 linked records' in self.text('intelligenceSourcesStatus'))
        self.wait.until(lambda _: self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{records[0].pk}"]').is_enabled())
        Select(self.browser.find_element(self.By.ID,'intelligenceScope')).select_by_value('general')
        question=dict(query='Synthetic competing history turn',scope='general',document_id=None); identity=uuid4().hex
        generation,_=history.prepare(owner,saved['id'],0,identity,question)
        history.append(owner,saved['id'],0,identity,question,dict(answer='Synthetic saved competing hypothesis',
            provider='ollama',classification='ai_generated_hypothesis',financial_authority=False),generation)
        draft=self.browser.find_element(self.By.ID,'intelligenceQuery'); draft.send_keys('Explain selected records')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Reopen this conversation' in self.text('intelligenceFeedback'))
        local.reason.assert_not_called()
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceScope').is_enabled())
        Select(self.browser.find_element(self.By.ID,'intelligenceScope')).select_by_value('financial_document')
        self.wait.until(lambda _: '7 linked records' in self.text('intelligenceSourcesStatus'))
        self.assertIn('never saved',self.text('conversationHistoryCurrent'))
        self.memory_click(f'#intelligenceSourceItems input[value="{records[0].pk}"]')
        local.reason.side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE-OCR C:/private/source.pdf')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Ollama unavailable' in self.text('intelligenceLocalStatus'))
        self.assertEqual(draft.get_property('value'),'Explain selected records')
        self.assertIn('1/3 selected',self.text('intelligenceSourcesStatus'))
        self.assertNotIn('SYNTHETIC-PRIVATE-OCR',self.text('intelligenceFeedback'))
        detail=service.evidence(owner,document.pk,records[0].pk)
        service.review(owner,document.pk,records[0].pk,revision=detail['revision'],fields=list(service.FIELDS),confirm=True,revoke=True)
        local.reason.side_effect=None; local.reason.reset_mock()
        self.memory_click('#intelligenceRetry')
        self.wait.until(lambda _: 'Refresh the source list' in self.text('intelligenceSourcesStatus'))
        self.assertEqual(draft.get_property('value'),'Explain selected records')
        self.assertEqual(self.text('intelligenceAnswers'),''); local.reason.assert_not_called()
        self.capture('document-questions-stale-draft')
        records[1].current_value='321.09'; records[1].save()
        detail=service.evidence(owner,document.pk,records[1].pk)
        service.review(owner,document.pk,records[1].pk,revision=detail['revision'],fields=['current_value'],confirm=True)
        self.memory_click('#intelligenceSourcesRefresh')
        self.wait.until(lambda _: '0/3 selected' in self.text('intelligenceSourcesStatus'))
        self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{records[0].pk}"]').is_enabled())
        self.memory_click(f'#intelligenceSourceItems input[value="{records[1].pk}"]')
        started=threading.Event(); finish=threading.Event(); self.addCleanup(finish.set)
        def delayed_answer(*args,**kwargs):
            started.set()
            if not finish.wait(10): raise RuntimeError('Synthetic delayed-answer test did not release the model')
            return 'Synthetic current reviewed-field hypothesis'
        local.reason.side_effect=delayed_answer
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: started.is_set())
        self.assertFalse(self.browser.find_element(self.By.ID,'intelligenceScope').is_enabled())
        self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{records[1].pk}"]').is_enabled())
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceScope').get_property('value'),'financial_document')
        finish.set()
        self.wait.until(lambda _: '321.09' in self.text('intelligenceAnswers'))
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceScope').is_enabled())
        self.assertNotIn('120.05',self.text('intelligenceAnswers')); self.assertEqual(draft.get_property('value'),'')
        self.assertEqual(len(history.list(owner)),1); self.assertEqual(history.get(owner,saved['id'])['revision'],1)
        self.assertEqual([turn['query'] for turn in history.get(owner,saved['id'])['turns']],['Synthetic competing history turn'])
        self.assertEqual(MemoryStore(settings.ALFRED_MEMORY_DIR).list_memories(owner),[])

    def test_financial_sources_page_selection_limit_exact_citations_mobile_and_privacy(self):
        row,documents,service,local=self.financial_source_selection_fixture('investment')
        self.assertIn('Eligible fields only: invested amount, monthly sip, current value',self.text('intelligenceSourceItems'))
        self.assertIn('Full-document Q&A is unsupported',self.text('intelligenceSourceItems'))
        for document in documents[:4]: self.memory_click(f'#intelligenceSourceItems input[value="{document.pk}"]')
        self.memory_click('#intelligenceSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('intelligenceSourcesStatus'))
        self.memory_click(f'#intelligenceSourceItems input[value="{documents[-1].pk}"]')
        self.memory_click(f'#intelligenceSourceItems input[value="{documents[-2].pk}"]')
        self.assertIn('Five-source limit',self.text('intelligenceSourcesStatus'))
        self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{documents[-2].pk}"]').is_selected())
        self.memory_click('#intelligenceSourcesPrevious')
        self.wait.until(lambda _: 'Page 1' in self.text('intelligenceSourcesStatus'))
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{documents[0].pk}"]').is_selected())
        for document in documents[1:4]: self.memory_click(f'#intelligenceSourceItems input[value="{document.pk}"]')
        self.assertIn('2/5 selected',self.text('intelligenceSourcesStatus'))
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this record')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: f'canonical-investment-{row.pk}' in self.text('intelligenceAnswers'))
        self.assertIn('2,345.67 · Currency not recorded',self.text('intelligenceAnswers'))
        for document in (documents[0],documents[-1]):
            url=service.evidence(self.scenario['user'],document.pk,row.pk)['citation_url']
            self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceAnswers a[href="{url}"]').is_displayed())
        self.assertNotIn('Synthetic investment source 2.pdf',self.text('intelligenceAnswers'))
        self.assertNotIn('Synthetic investment source',json.dumps(local.reason.call_args.args[0]))
        self.browser.execute_script("document.querySelector('#intelligenceSources').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('financial-source-picker-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.querySelector('#intelligenceSources').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('financial-source-picker-mobile')
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('intelligenceSourceItems'),''); self.assertEqual(self.text('intelligenceSourcesSelected'),'')
        self.assertEqual(self.text('intelligenceAnswers'),'')

    def document_metadata_filter_fixture(self):
        from datetime import datetime,timezone
        from selenium.webdriver.support.ui import Select
        row,documents,service,local=self.financial_source_selection_fixture('investment')
        owner=self.scenario['user']
        for index,document in enumerate(documents):
            stamp=datetime(2026,10,20 if index<6 else 21,0 if index==0 else 23,0 if index==0 else 59,0 if index==0 else 59,
                0 if index==0 else 999999,tzinfo=timezone.utc)
            filename='Synthetic report.pdf' if index else 'Synthetic <img src=x onerror="window.filterLeak=true"> report.pdf'
            type(document).objects.filter(pk=document.pk).update(file_name=filename,created_at=stamp)
            detail=service.evidence(owner,document.pk,row.pk)
            service.review(owner,document.pk,row.pk,revision=detail['revision'],fields=list(service.FIELDS),confirm=True)
        other=get_user_model().objects.create_user(username='synthetic-metadata-foreign')
        type(documents[0]).objects.create(user=other,file_name='Synthetic report.pdf')
        self.browser.get(self.live_server_url+'/documents/')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'documentSourcesKind').is_enabled())
        Select(self.browser.find_element(self.By.ID,'documentSourcesKind')).select_by_value('investment')
        self.wait.until(lambda _: '7 supported entries' in self.text('documentSourcesStatus'))
        self.browser.find_element(self.By.ID,'documentSourcesName').send_keys('report')
        self.browser.execute_script("document.getElementById('documentSourcesFrom').value='2026-10-20';document.getElementById('documentSourcesTo').value='2026-10-20';")
        self.memory_click('#documentSourcesApply')
        self.wait.until(lambda _: '6 supported entries' in self.text('documentSourcesStatus'))
        return row,documents,service,local

    def test_document_metadata_filters_pages_names_dates_and_privacy(self):
        row,documents,service,local=self.document_metadata_filter_fixture()
        self.assertIn('filters applied',self.text('documentSourcesStatus'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#documentSourcesItems article')),5)
        self.assertFalse(self.browser.execute_script('return Boolean(window.filterLeak)'))
        draft=self.browser.find_element(self.By.ID,'documentChatGPTRawText'); draft.send_keys('SYNTHETIC unsent upload draft')
        self.browser.execute_script('''
            window.documentFilterRequests=[];const original=window.fetch;
            window.fetch=function(input,options){const url=typeof input==='string'?input:input.url;
                if(url.includes('/api/ai/financial-documents/'))window.documentFilterRequests.push({url,method:options?.method||'GET'});
                return original.apply(this,arguments);};
        ''')
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('documentSourcesStatus'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#documentSourcesItems article')),1)
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#documentSourcesItems button[data-document-id="{documents[5].pk}"]').is_displayed())
        self.memory_click('#documentSourcesPrevious')
        self.wait.until(lambda _: 'Page 1' in self.text('documentSourcesStatus'))
        self.browser.execute_script("document.getElementById('documentSourcesFilters').scrollIntoView({block:'center',behavior:'instant'})")
        self.capture('document-filters-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.getElementById('documentSourcesFilters').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('document-filters-mobile')
        name=self.browser.find_element(self.By.ID,'documentSourcesName'); name.clear(); name.send_keys('absent')
        self.memory_click('#documentSourcesApply')
        self.wait.until(lambda _: '0 supported entries' in self.text('documentSourcesStatus'))
        self.assertIn('No documents match',self.text('documentSourcesItems'))
        self.assertFalse(self.browser.find_element(self.By.ID,'documentSourcesNext').is_enabled())
        self.assertEqual(draft.get_property('value'),'SYNTHETIC unsent upload draft')
        self.browser.execute_script("document.getElementById('documentSourcesFrom').value='2026-10-21';")
        self.memory_click('#documentSourcesApply')
        self.wait.until(lambda _: 'Sources unavailable or changed' in self.text('documentSourcesStatus'))
        self.assertEqual(name.get_property('value'),'absent')
        self.assertEqual(self.browser.find_element(self.By.ID,'documentSourcesFrom').get_property('value'),'2026-10-21')
        requests=self.browser.execute_script('return window.documentFilterRequests')
        self.assertTrue(requests); self.assertTrue(all(item['method']=='POST' and '?' not in item['url'] for item in requests))
        self.assertEqual(self.browser.current_url,self.live_server_url+'/documents/')
        self.memory_click('#documentSourcesClear')
        self.wait.until(lambda _: '7 supported entries' in self.text('documentSourcesStatus'))
        for identity in ('documentSourcesName','documentSourcesFrom','documentSourcesTo'):
            self.assertEqual(self.browser.find_element(self.By.ID,identity).get_property('value'),'')
        name.send_keys('SYNTHETIC-PRIVATE-DRAFT')
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        for identity in ('documentSourcesName','documentSourcesFrom','documentSourcesTo'):
            self.assertEqual(self.browser.find_element(self.By.ID,identity).get_property('value'),'')
        self.assertEqual(self.text('documentSourcesItems'),''); self.assertEqual(self.text('documentSourcesStatus'),'')
        self.browser.execute_script("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        self.wait.until(lambda _: '7 supported entries' in self.text('documentSourcesStatus'))
        self.assertEqual(name.get_property('value'),''); local.reason.assert_not_called()

    def test_document_filters_stale_refresh_and_reviewed_question_selection(self):
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        row,documents,service,local=self.document_metadata_filter_fixture(); owner=self.scenario['user']
        cloud=self.enterContext(patch('apps.ml_engine.services.hybrid_intelligence.reasoning_provider'))
        before=resolve_canonical_financial_baseline(owner,fresh=True)['decimal_amounts']
        type(documents[0]).objects.filter(pk=documents[5].pk).update(file_name='Synthetic report revised.pdf')
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Sources unavailable or changed' in self.text('documentSourcesStatus'))
        self.assertEqual(self.text('documentSourcesItems'),'')
        self.assertEqual(self.browser.find_element(self.By.ID,'documentSourcesName').get_property('value'),'report')
        self.memory_click('#documentSourcesRefresh')
        self.wait.until(lambda _: '6 supported entries' in self.text('documentSourcesStatus'))
        self.memory_click(f'#documentSourcesItems button[data-document-id="{documents[0].pk}"]')
        self.wait.until(lambda _: 'linked records' in self.text('documentSourcesStatus'))
        self.assertFalse(self.browser.find_element(self.By.ID,'documentSourcesName').is_enabled())
        self.memory_click('#documentSourcesDocuments')
        self.wait.until(lambda _: '6 supported entries' in self.text('documentSourcesStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID,'documentSourcesName').get_property('value'),'report')
        self.memory_click(f'#documentSourcesItems button[data-document-id="{documents[0].pk}"]')
        self.wait.until(lambda _: 'linked records' in self.text('documentSourcesStatus'))
        self.memory_click('#documentSourcesItems a[href*="scope=financial_document"]')
        self.wait.until(lambda _: '1 linked records' in self.text('intelligenceSourcesStatus'))
        self.memory_click(f'#intelligenceSourceItems input[value="{row.pk}"]')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain selected records')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: '2,345.67' in self.text('intelligenceAnswers'))
        citation=service.evidence(owner,documents[0].pk,row.pk)['citation_url']
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceAnswers a[href="{citation}"]').is_displayed())
        self.assertIn('Currency not recorded',self.text('intelligenceAnswers'))
        self.assertNotIn('filterLeak',json.dumps(local.reason.call_args.args[0]))
        detail=service.evidence(owner,documents[0].pk,row.pk)
        service.review(owner,documents[0].pk,row.pk,revision=detail['revision'],fields=list(service.FIELDS),confirm=True,revoke=True)
        local.reason.reset_mock()
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain selected records')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Selected evidence changed' in self.text('intelligenceSourcesStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceQuery').get_property('value'),'Explain selected records')
        local.reason.assert_not_called(); cloud.assert_not_called()
        self.assertEqual(resolve_canonical_financial_baseline(owner,fresh=True)['decimal_amounts'],before)

    def test_document_center_owned_source_discovery_review_pages_and_stale_refresh(self):
        from selenium.webdriver.support.ui import Select
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.investments.models import InvestmentImportDocument
        row,documents,service,local=self.financial_source_selection_fixture('investment')
        owner=self.scenario['user']; document=documents[-1]
        document.file_name='Synthetic <img src=x onerror="window.discoveryLeak=true">.pdf'; document.save()
        linked=[row]
        for index in range(6):
            extra=type(row).objects.create(user=owner,asset_type='equity',asset_name=f'Synthetic discovery asset {index}',
                invested_amount='100.01',current_value='120.05',monthly_sip='1.00')
            document.linked_investments.add(extra); linked.append(extra)
        service.capture_import(document,linked)
        for current in linked:
            detail=service.evidence(owner,document.pk,current.pk)
            service.review(owner,document.pk,current.pk,revision=detail['revision'],fields=['current_value'],confirm=True)
        self.browser.get(self.live_server_url+'/documents/')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'documentSourcesKind').is_enabled())
        Select(self.browser.find_element(self.By.ID,'documentSourcesKind')).select_by_value('investment')
        self.wait.until(lambda _: '7 supported entries' in self.text('documentSourcesStatus'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#documentSourcesItems article')),5)
        draft=self.browser.find_element(self.By.ID,'documentChatGPTRawText'); draft.send_keys('SYNTHETIC unsent upload draft')
        # Membership changes invalidate the old list instead of dropping a newly eligible document.
        added=InvestmentImportDocument.objects.create(user=owner,file_name='Synthetic added.pdf',parser_status='parsed',
            uploaded_file=SimpleUploadedFile('new.pdf',b'%PDF-SYNTHETIC-ADDED'))
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Sources unavailable or changed' in self.text('documentSourcesStatus'))
        self.assertEqual(self.text('documentSourcesItems'),'')
        self.assertEqual(draft.get_property('value'),'SYNTHETIC unsent upload draft')
        self.memory_click('#documentSourcesRefresh')
        self.wait.until(lambda _: '8 supported entries' in self.text('documentSourcesStatus'))
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('documentSourcesStatus'))
        self.assertIn('<img src=x onerror=',self.text('documentSourcesItems'))
        self.assertFalse(self.browser.execute_script('return Boolean(window.discoveryLeak)'))
        self.memory_click(f'#documentSourcesItems button[data-document-id="{document.pk}"]')
        self.wait.until(lambda _: 'linked records' in self.text('documentSourcesStatus'))
        self.assertIn('7 supported entries',self.text('documentSourcesStatus'))
        self.assertIn('Eligible reviewed fields: reviewed fields only',self.text('documentSourcesItems'))
        self.assertIn('not retained',self.text('documentSourcesItems'))
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('documentSourcesStatus'))
        self.assertEqual(len(self.browser.find_elements(self.By.CSS_SELECTOR,'#documentSourcesItems article')),2)
        last=linked[-1]; detail=service.evidence(owner,document.pk,last.pk)
        service.review(owner,document.pk,last.pk,revision=detail['revision'],fields=['current_value'],confirm=True,revoke=True)
        self.memory_click('#documentSourcesRefresh')
        self.wait.until(lambda _: 'Page 1' in self.text('documentSourcesStatus'))
        self.memory_click('#documentSourcesNext')
        self.wait.until(lambda _: 'Not eligible: owner review required' in self.text('documentSourcesItems'))
        self.assertEqual(draft.get_property('value'),'SYNTHETIC unsent upload draft')
        self.browser.execute_script("document.getElementById('documentSourcesStatus').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('document-discovery-records-desktop')
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertLessEqual(self.browser.execute_script('return document.documentElement.scrollWidth'),390)
        self.browser.execute_script("document.getElementById('documentSourcesTitle').scrollIntoView({block:'center',behavior:'instant'})")
        self.capture('document-discovery-records-mobile')
        citation=detail['citation_url']
        self.memory_click(f'#documentSourcesItems a[href="{citation}"]')
        self.wait.until(lambda _: 'needs_owner_review' in self.text('statementEvidence'))
        self.assertIn('120.05',self.text('statementEvidence'))
        self.capture('document-discovery-exact-review')
        local.reason.assert_not_called()
        self.browser.get(self.live_server_url+'/documents/')
        self.wait.until(lambda _: 'Documents' in self.text('documentSourcesStatus'))
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('documentSourcesItems'),''); self.assertEqual(self.text('documentSourcesStatus'),'')

    def test_financial_sources_stale_selection_refresh_and_exact_older_loan_citation(self):
        row,documents,service,local=self.financial_source_selection_fixture('loan')
        self.memory_click('#intelligenceSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('intelligenceSourcesStatus'))
        document=documents[-1]
        self.memory_click(f'#intelligenceSourceItems input[value="{document.pk}"]')
        detail=service.evidence(self.scenario['user'],document.pk,row.pk)
        service.review(self.scenario['user'],document.pk,row.pk,revision=detail['revision'],fields=list(service.FIELDS),confirm=True,revoke=True)
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this record')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Refresh the source list' in self.text('intelligenceSourcesStatus'))
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceQuery').get_property('value'),'Explain this record')
        self.assertEqual(self.text('intelligenceAnswers'),''); local.reason.assert_not_called()
        self.capture('financial-source-stale-draft')
        self.memory_click('#intelligenceSourcesRefresh')
        self.wait.until(lambda _: 'Page 1' in self.text('intelligenceSourcesStatus'))
        self.assertNotIn('source 7.pdf',self.text('intelligenceSourcesSelected'))
        self.memory_click('#intelligenceSourcesNext')
        self.wait.until(lambda _: 'Page 2' in self.text('intelligenceSourcesStatus'))
        self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR,f'#intelligenceSourceItems input[value="{document.pk}"]').is_enabled())
        self.assertIn('Not eligible: owner review required',self.text('intelligenceSourceItems'))
        self.memory_click(f'#intelligenceSourceItems input[value="{documents[-2].pk}"]')
        self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: f'canonical-loan-{row.pk}' in self.text('intelligenceAnswers'))
        url=service.evidence(self.scenario['user'],documents[-2].pk,row.pk)['citation_url']
        self.memory_click(f'#intelligenceAnswers a[href="{url}"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.assertIn('100.01',self.text('statementEvidence')); self.capture('financial-selected-older-loan-citation')

    def loan_document_fixture(self,row):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.loans.models import LoanImportDocument
        from apps.loans.services.document_evidence import capture_import
        media=Path(self.enterContext(TemporaryDirectory(prefix='alfred-loan-field-browser-')))
        self.enterContext(override_settings(MEDIA_ROOT=media))
        raw=dict(lender=row.lender,loan_type=row.loan_type,loan_account_number=row.loan_account_number,
            principal=str(row.principal),emi='100.0100',remaining_balance=str(row.remaining_balance))
        document=LoanImportDocument.objects.create(user=self.scenario['user'],file_name='synthetic-loan.pdf',
            uploaded_file=SimpleUploadedFile('synthetic-loan.pdf',b'%PDF-SYNTHETIC-FIELDS'),parser_status='parsed',
            extracted_payload={'loans':[raw],'text':'SYNTHETIC-DO-NOT-DISPLAY'})
        document.linked_loans.add(row); capture_import(document,[row],extraction=[raw])
        return document

    def test_loan_field_confirmation_revocation_correction_and_stale_mobile_source(self):
        from apps.loans.models import Loan
        rows,_=self.canonical_grounding_fixture(); row=rows['loan']
        document=self.loan_document_fixture(row)
        self.login(); self.browser.get(self.live_server_url+f'/documents/loans/{document.pk}/records/{row.pk}/')
        self.wait.until(lambda _: '100.0100' in self.text('statementEvidence'))
        self.assertIn('not bank authentication',self.text('statementEvidence'))
        self.assertNotIn('SYNTHETIC-DO-NOT-DISPLAY',self.browser.page_source)
        self.memory_click('#statementEvidenceForm [value="emi"]'); self.memory_click('#statementEvidenceConfirm')
        self.memory_click('#statementEvidenceForm button[type="submit"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.capture('loan-single-field-confirmed')
        self.memory_click('#statementEvidenceForm [value="emi"]'); self.memory_click('#statementEvidenceRevoke')
        self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: 'needs_owner_review' in self.text('statementEvidence') and 'owner_confirmed' not in self.text('statementEvidence'))
        Loan.objects.filter(pk=row.pk).update(emi='123.45')
        self.browser.refresh(); self.wait.until(lambda _: '123.45' in self.text('statementEvidence'))
        self.assertIn('100.0100',self.text('statementEvidence'))
        self.memory_click('#statementEvidenceForm [value="emi"]'); self.memory_click('#statementEvidenceConfirm')
        Path(document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-REPLACED-SOURCE')
        self.memory_click('#statementEvidenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Reference:' in self.text('statementEvidenceFeedback'))
        self.assertTrue(self.browser.find_element(self.By.ID,'statementEvidenceConfirm').is_selected())
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,'[name="fields"][value="emi"]').is_selected())
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.querySelector('#statementEvidence').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('loan-field-stale-mobile')
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('statementEvidence'),'')

    def test_loan_grounded_answer_opens_owner_confirmed_field_citation(self):
        from apps.loans.services.document_evidence import evidence, review, FIELDS
        rows,local=self.canonical_grounding_fixture(); row=rows['loan']; owner=self.scenario['user']
        document=self.loan_document_fixture(row); detail=evidence(owner,document.pk,row.pk)
        review(owner,document.pk,row.pk,revision=detail['revision'],fields=list(FIELDS),confirm=True)
        self.login(); self.browser.get(self.live_server_url+f'/ai/financial-records/loan/{row.pk}/')
        self.wait.until(lambda _: 'owner_confirmed_document_field' in self.text('canonicalEvidence'))
        self.memory_click('#canonicalEvidence a[href^="/ai/insights/"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceFinancial').get_property('value')==f'loan:{row.pk}')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this record')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: f'canonical-loan-{row.pk}' in self.text('intelligenceAnswers'))
        self.assertIn('100.01 · Currency not recorded',self.text('intelligenceAnswers'))
        self.assertNotIn('document sources: [',self.text('intelligenceAnswers'))
        self.assertEqual(self.text('intelligenceCloudStatus'),'OpenAI disabled')
        self.capture('loan-grounded-field-citation')
        self.memory_click(f'#intelligenceAnswers a[href="{detail["citation_url"]}"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.assertIn('100.0100',self.text('statementEvidence'))
        self.assertNotIn('synthetic-loan.pdf',json.dumps(local.reason.call_args.args[0]))

    def test_loan_payment_reference_opens_bank_review_and_tracks_revocation(self):
        from apps.loans.models import LoanPaymentHistory
        bank_row,upload,bank_detail=self.bank_statement_evidence_fixture()
        rows,local=self.canonical_grounding_fixture(); row=rows['loan']
        LoanPaymentHistory.objects.create(loan=row,payment_date=bank_row.transaction_date,amount=bank_row.amount,
            expense_reference=bank_row,match_status='matched',loan_effect_applied=True)
        citation=f'/ai/financial-records/loan/{row.pk}/'
        self.login(); self.browser.get(self.live_server_url+citation)
        self.wait.until(lambda _: 'unverified_transaction_reference' in self.text('canonicalEvidence'))
        self.memory_click(f'#canonicalEvidence a[href="{bank_detail["citation_url"]}"]')
        self.wait.until(lambda _: 'needs_owner_review' in self.text('statementEvidence'))
        self.memory_click('#statementEvidenceConfirm'); self.memory_click('#statementEvidenceForm button[type="submit"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.browser.get(self.live_server_url+citation)
        self.wait.until(lambda _: 'owner_confirmed_statement_reference' in self.text('canonicalEvidence'))
        self.assertIn('recorded association only',self.text('canonicalEvidence'))
        self.capture('loan-payment-owner-statement-reference')
        self.memory_click('#canonicalEvidence a[href^="/ai/insights/"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceFinancial').get_property('value')==f'loan:{row.pk}')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Show my repayment status')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: f'canonical-loan-{row.pk}' in self.text('intelligenceAnswers'))
        self.assertNotIn('applied payment source:',self.text('intelligenceAnswers'))
        self.assertNotIn('/documents/statements/',json.dumps(local.reason.call_args.args[0]))
        self.assertEqual(self.text('intelligenceCloudStatus'),'OpenAI disabled')
        self.memory_click(f'#intelligenceAnswers a[href="{citation}"]')
        self.wait.until(lambda _: 'owner_confirmed_statement_reference' in self.text('canonicalEvidence'))
        self.memory_click(f'#canonicalEvidence a[href="{bank_detail["citation_url"]}"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.memory_click('#statementEvidenceRevoke'); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: 'needs_owner_review' in self.text('statementEvidence') and 'owner_confirmed' not in self.text('statementEvidence'))
        self.browser.get(self.live_server_url+citation)
        self.wait.until(lambda _: 'unverified_transaction_reference' in self.text('canonicalEvidence'))

    def investment_document_fixture(self,row):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.investments.models import InvestmentImportDocument
        from apps.investments.services.document_evidence import capture_import
        media=Path(self.enterContext(TemporaryDirectory(prefix='alfred-investment-field-browser-')))
        self.enterContext(override_settings(MEDIA_ROOT=media))
        raw=dict(asset_name=row.asset_name,institution=row.institution,current_value='2345.6700',
            invested_amount=str(row.invested_amount),monthly_sip=str(row.monthly_sip))
        document=InvestmentImportDocument.objects.create(user=self.scenario['user'],file_name='synthetic-portfolio.pdf',
            uploaded_file=SimpleUploadedFile('synthetic-portfolio.pdf',b'%PDF-SYNTHETIC-FIELDS'),parser_status='parsed',
            extracted_payload={'investments':[raw],'text':'SYNTHETIC-DO-NOT-DISPLAY'})
        document.linked_investments.add(row); capture_import(document,[row],extraction=[raw])
        return document

    def test_investment_field_review_correction_revocation_and_stale_source(self):
        from apps.investments.models import Investment
        rows,_=self.canonical_grounding_fixture(); row=rows['investment']
        document=self.investment_document_fixture(row)
        self.login(); self.browser.get(self.live_server_url+f'/documents/investments/{document.pk}/records/{row.pk}/')
        self.wait.until(lambda _: '2345.6700' in self.text('statementEvidence'))
        self.assertNotIn('SYNTHETIC-DO-NOT-DISPLAY',self.browser.page_source)
        self.memory_click('#statementEvidenceForm [value="current_value"]')
        self.memory_click('#statementEvidenceConfirm'); self.memory_click('#statementEvidenceForm button[type="submit"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.capture('investment-single-field-confirmed')
        self.memory_click('#statementEvidenceForm [value="current_value"]')
        self.memory_click('#statementEvidenceRevoke'); self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: 'needs_owner_review' in self.text('statementEvidence') and 'owner_confirmed' not in self.text('statementEvidence'))
        Investment.objects.filter(pk=row.pk).update(current_value='3456.78')
        self.browser.refresh(); self.wait.until(lambda _: '3456.78' in self.text('statementEvidence'))
        self.assertIn('2345.6700',self.text('statementEvidence'))
        self.memory_click('#statementEvidenceForm [value="current_value"]'); self.memory_click('#statementEvidenceConfirm')
        Path(document.uploaded_file.path).write_bytes(b'%PDF-SYNTHETIC-REPLACED-SOURCE')
        self.memory_click('#statementEvidenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Reference:' in self.text('statementEvidenceFeedback'))
        self.assertTrue(self.browser.find_element(self.By.ID,'statementEvidenceConfirm').is_selected())
        self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR,'[name="fields"][value="current_value"]').is_selected())
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.querySelector('#statementEvidence').scrollIntoView({block:'start',behavior:'instant'})")
        self.capture('investment-field-stale-mobile')
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('statementEvidence'),'')

    def test_investment_grounded_answer_opens_exact_private_field_citation(self):
        from apps.investments.services.document_evidence import evidence, review, FIELDS
        rows,local=self.canonical_grounding_fixture(); row=rows['investment']; owner=self.scenario['user']
        document=self.investment_document_fixture(row)
        detail=evidence(owner,document.pk,row.pk)
        review(owner,document.pk,row.pk,revision=detail['revision'],fields=list(FIELDS),confirm=True)
        self.login(); self.browser.get(self.live_server_url+f'/ai/financial-records/investment/{row.pk}/')
        self.wait.until(lambda _: 'owner_confirmed_document_field' in self.text('canonicalEvidence'))
        self.memory_click('#canonicalEvidence a[href^="/ai/insights/"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceFinancial').get_property('value')==f'investment:{row.pk}')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this record')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: f'canonical-investment-{row.pk}' in self.text('intelligenceAnswers'))
        self.assertIn('2,345.67 · Currency not recorded',self.text('intelligenceAnswers'))
        self.assertNotIn('document sources: [',self.text('intelligenceAnswers'))
        self.assertEqual(self.text('intelligenceCloudStatus'),'OpenAI disabled')
        self.capture('investment-grounded-field-citation')
        self.memory_click(f'#intelligenceAnswers a[href="{detail["citation_url"]}"]')
        self.wait.until(lambda _: 'owner_confirmed' in self.text('statementEvidence'))
        self.assertIn('2345.6700',self.text('statementEvidence'))
        self.assertNotIn('synthetic-portfolio.pdf',json.dumps(local.reason.call_args.args[0]))

    def test_canonical_financial_sources_corrections_citations_and_mobile(self):
        from selenium.webdriver.support.ui import Select
        from apps.expenses.models import BankAccount
        from apps.budgets.models import Budget
        from apps.investments.models import Investment
        from apps.loans.models import Loan
        rows,local=self.canonical_grounding_fixture()
        self.login(); self.browser.get(self.live_server_url+'/ai/insights/')
        self.wait.until(lambda _: len(self.browser.find_element(self.By.ID,'intelligenceFinancial').find_elements(self.By.TAG_NAME,'option'))>4)
        Select(self.browser.find_element(self.By.ID,'intelligenceScope')).select_by_value('financial_records')
        models=(Expense,BankAccount,Budget,Loan,Investment)
        before=[list(model.objects.order_by('pk').values()) for model in models]
        for kind,field,value in (('expense','amount','12.34'),('budget','base budget','234.56'),
                                ('loan','emi','100.01'),('investment','current value','2,345.67')):
            Select(self.browser.find_element(self.By.ID,'intelligenceFinancial')).select_by_value(f'{kind}:{rows[kind].pk}')
            self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this record')
            self.memory_click('#intelligenceForm button')
            self.wait.until(lambda _: f'canonical-{kind}-{rows[kind].pk}' in self.text('intelligenceAnswers'))
            text=self.browser.find_element(self.By.CSS_SELECTOR,'#intelligenceAnswers article:last-child').text
            self.assertIn(f'{field}: {value} · Currency not recorded',text)
            self.assertFalse(self.browser.find_element(self.By.ID,'intelligenceCloudConsent').is_enabled())
        self.assertEqual([list(model.objects.order_by('pk').values()) for model in models],before)
        self.capture('canonical-multi-domain-source-cards')
        self.memory_click(f'#intelligenceAnswers article:last-child a[href="/ai/financial-records/investment/{rows["investment"].pk}/"]')
        self.wait.until(lambda _: '2345.67' in self.text('canonicalEvidence'))
        self.assertIn('not live market quotes',self.text('canonicalEvidence'))
        self.assertIn('Currency was not recorded',self.text('canonicalEvidence'))
        self.capture('canonical-owned-portfolio-citation')
        Investment.objects.filter(pk=rows['investment'].pk).update(current_value='3456.78')
        self.browser.refresh(); self.wait.until(lambda _: '3456.78' in self.text('canonicalEvidence'))
        self.assertNotIn('2345.67',self.text('canonicalEvidence'))
        self.memory_click('#canonicalEvidence a[href^="/ai/insights/"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceFinancial').get_property('value')==f'investment:{rows["investment"].pk}')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this record')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: '3,456.78 · Currency not recorded' in self.text('intelligenceAnswers'))
        self.browser.execute_cdp_cmd('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
        self.addCleanup(self.browser.execute_cdp_cmd,'Emulation.clearDeviceMetricsOverride',{})
        self.assertTrue(self.browser.execute_script('return document.documentElement.scrollWidth <= innerWidth'))
        self.browser.execute_script("document.querySelector('#intelligenceAnswers .recorded-amount').scrollIntoView({block:'center',behavior:'instant'})")
        self.capture('canonical-corrected-record-mobile')

    def test_canonical_unsupported_stale_and_owner_only_citations_keep_drafts(self):
        from apps.investments.models import Investment
        from apps.ml_engine.services.canonical_evidence import record_source
        rows,local=self.canonical_grounding_fixture(); row=rows['investment']
        source=record_source(self.scenario['user'],'investment',row.pk)
        foreign=get_user_model().objects.create_user(username='synthetic-canonical-browser-foreign')
        from django.test import Client
        client=Client(); client.force_login(foreign)
        self.assertEqual(client.get(source['url']).status_code,404)
        self.login(); self.browser.get(self.live_server_url+f'/ai/insights/?scope=financial_records&record_type=investment&record_id={row.pk}')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceFinancial').get_property('value')==f'investment:{row.pk}')
        question='Convert this investment to USD'
        query=self.browser.find_element(self.By.ID,'intelligenceQuery'); query.send_keys(question)
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: 'Insufficient evidence.' in self.text('intelligenceFeedback'))
        local.reason.assert_not_called()
        self.assertEqual(query.get_property('value'),question)
        self.memory_click('#intelligenceNew')
        query.send_keys('Show my loan status'); self.memory_click('#intelligenceForm button[type="submit"]')
        self.wait.until(lambda _: 'Show my loan status' in self.text('intelligenceAnswers'))
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceAnswers').get_attribute('aria-busy')=='false')
        self.assertIn('Insufficient evidence.',self.text('intelligenceFeedback'))
        self.assertEqual(query.get_property('value'),'Show my loan status'); local.reason.assert_not_called()
        self.capture('canonical-question-domain-abstention')
        self.memory_click('#intelligenceNew')
        def changing(payload,**kwargs):
            Investment.objects.filter(pk=row.pk).update(current_value='4567.89')
            return 'SYNTHETIC-STALE-BROWSER-ANSWER'
        local.reason.side_effect=changing
        query.send_keys('Explain this record'); self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceAnswers').get_attribute('aria-busy')=='false')
        self.assertNotIn('SYNTHETIC-STALE-BROWSER-ANSWER',self.text('intelligenceAnswers'))
        self.assertEqual(query.get_property('value'),'Explain this record')
        self.capture('canonical-stale-draft-preserved')
        self.browser.get(self.live_server_url+source['url'])
        self.wait.until(lambda _: '4567.89' in self.text('canonicalEvidence'))
        self.browser.execute_script("window.dispatchEvent(new Event('pagehide'))")
        self.assertEqual(self.text('canonicalEvidence'),'')

    def test_verified_closure_exact_citation_file_liveness_and_metadata_limit(self):
        from datetime import date
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.loans.models import LoanClosureDocument
        rows,local=self.canonical_grounding_fixture()
        root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-closure-browser-synthetic-')))
        self.enterContext(override_settings(MEDIA_ROOT=root/'media'))
        document=LoanClosureDocument.objects.create(loan=rows['loan'],verification_status='verified',closure_amount='123.45',
            closure_date=date(2026,9,1),file_name='Synthetic closure.pdf',
            uploaded_file=SimpleUploadedFile('synthetic-closure.pdf',b'%PDF-synthetic-browser-closure'))
        self.login(); self.browser.get(self.live_server_url+f'/documents/loan-closures/{document.pk}/')
        self.wait.until(lambda _: '123.45' in self.text('canonicalEvidence'))
        self.assertIn('Retained file is accessible to its owner',self.text('canonicalEvidence'))
        self.memory_click('#canonicalEvidence a[href^="/ai/insights/"]')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceDocument').get_property('value')==str(document.pk))
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this closure record')
        self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: f'loan-closure-{document.pk}' in self.text('intelligenceAnswers'))
        self.assertIn('123.45 · Currency not recorded',self.text('intelligenceAnswers'))
        self.assertTrue(self.browser.find_elements(self.By.CSS_SELECTOR,f'#intelligenceAnswers a[href="/documents/loan-closures/{document.pk}/"]'))
        self.capture('closure-exact-private-source-citation')
        Path(document.uploaded_file.path).unlink()
        self.memory_click('#intelligenceNew')
        self.browser.find_element(self.By.ID,'intelligenceQuery').send_keys('Explain this closure record')
        local.reason.reset_mock(); self.memory_click('#intelligenceForm button')
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,'intelligenceAnswers').get_attribute('aria-busy')=='false')
        local.reason.assert_not_called()
        self.assertEqual(self.browser.find_element(self.By.ID,'intelligenceQuery').get_property('value'),'Explain this closure record')
        document.uploaded_file=''; document.save(update_fields=['uploaded_file'])
        self.browser.get(self.live_server_url+f'/documents/loan-closures/{document.pk}/')
        self.wait.until(lambda _: 'Original file is not retained' in self.text('canonicalEvidence'))
        self.assertFalse(self.browser.find_elements(self.By.CSS_SELECTOR,'#canonicalEvidence a[href^="/media/"]'))
        self.capture('closure-metadata-only-limit')

    def click_upload_button(self, form_id):
        button = self.browser.find_element(self.By.CSS_SELECTOR, f"#{form_id} button[type=submit]")
        self.browser.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", button)
        self.wait.until(lambda _: button.is_enabled())
        button.click()

    @override_settings(ALFRED_UPLOAD_FILE_BYTES=1024, ALFRED_UPLOAD_REQUEST_BYTES=4096)
    def test_document_size_limit_feedback_then_valid_resume(self):
        from apps.career.models import CareerResume
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-browser-upload-fixture-"))
        oversized = Path(directory) / "oversized.txt"
        valid = Path(directory) / "resume.txt"
        oversized.write_bytes(b"X" * 1025)
        valid.write_text("Synthetic Analyst\nPython SQL\n4 years experience", encoding="utf-8")
        before = CareerResume.objects.count()
        self.login()
        self.browser.get(self.live_server_url + "/documents/")
        field = self.wait.until(lambda driver: driver.find_element(self.By.ID, "documentResumeFile"))
        field.send_keys(str(oversized))
        self.click_upload_button("documentResumeForm")
        self.wait.until(lambda _: "configured" in self.text("documentResumeFeedback"))
        self.assertEqual(CareerResume.objects.count(), before)
        self.capture("upload-size-rejected")
        self.browser.execute_script("document.getElementById('documentResumeFile').value = '';")
        self.browser.find_element(self.By.ID, "documentResumeFile").send_keys(str(valid))
        self.click_upload_button("documentResumeForm")
        self.wait.until(lambda _: CareerResume.objects.count() == before + 1)
        self.wait.until(lambda _: "uploaded" in self.text("documentResumeFeedback").casefold())
        self.capture("upload-valid-resume")

    def test_loan_diagnostics_are_safe_then_real_pdf_import_and_reimport_work(self):
        import fitz
        from apps.loans.models import Loan, LoanImportDocument
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-m14f-browser-"))
        file = Path(directory) / "synthetic-loan.pdf"
        with fitz.open() as pdf:
            page = pdf.new_page()
            page.insert_text((40, 40), "HDFC PERSONAL LOAN\nLoan Number TESTM14F42\nLoan Amount 1000.00\n"
                             "EMI Amount 100.00\nOutstanding Amount 500.00\nTenure 10 months")
            file.write_bytes(pdf.tobytes())
        owner = get_user_model().objects.get(username="acceptance_demo")
        marker = r"C:\synthetic-private\loan.pdf; fake-token-M14F-browser; OCR PRIVATE LOAN"
        LoanImportDocument.objects.create(user=owner, file_name="historical-loan.pdf", parser_status="failed",
                                         summary=marker, extracted_payload={"error": marker, "raw_text_excerpt": marker})
        self.login()
        self.browser.get(self.live_server_url + "/loans/")
        self.wait.until(lambda _: "historical-loan.pdf" in self.text("loanImportHistory"))
        self.assertNotIn(marker, self.browser.page_source)
        self.browser.find_element(self.By.ID, "loanPdfFile").send_keys(str(file))
        button = self.browser.find_element(self.By.ID, "loanImportBtn")
        self.browser.execute_script("arguments[0].scrollIntoView({behavior:'instant', block:'center'});", button)
        self.wait.until(lambda driver: driver.execute_script(
            "const r = document.getElementById('loanImportBtn').getBoundingClientRect(); return r.top >= 78 && r.bottom <= innerHeight;"))
        with patch("apps.loans.views.loan_pdf_parser.parse_document", side_effect=RuntimeError(marker)):
            button.click()
            self.wait.until(lambda _: LoanImportDocument.objects.filter(file_name=file.name, parser_status="failed").exists())
            self.wait.until(lambda _: "review" in self.text("loanImportStatus").casefold())
        self.assertNotIn(marker, self.browser.page_source)
        self.capture("loan-safe-parser-failure")
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, "loanImportBtn").is_enabled())
        for attempt in (1, 2):
            self.browser.find_element(self.By.ID, "loanPdfFile").send_keys(str(file))
            self.browser.execute_script("document.getElementById('loanImportBtn').scrollIntoView({behavior:'instant', block:'center'});")
            self.browser.find_element(self.By.ID, "loanImportBtn").click()
            self.wait.until(lambda _: LoanImportDocument.objects.filter(file_name=file.name, parser_status="parsed").count() == attempt)
            self.wait.until(lambda _: self.browser.find_element(self.By.ID, "loanImportBtn").is_enabled())
            rows = list(Loan.objects.filter(user=owner, loan_account_number="TESTM14F42").values_list("pk", "principal", "remaining_balance", "emi"))
            self.assertEqual(len(rows), 1)
            if attempt == 1:
                expected = rows
            else:
                self.assertEqual(rows, expected)
        self.capture("loan-real-pdf-reimport")
        self.browser.get(self.live_server_url + "/documents/")
        self.wait.until(lambda _: "historical-loan.pdf" in self.browser.find_element(self.By.TAG_NAME, "body").text)
        self.assertNotIn(marker, self.browser.page_source)
        self.capture("loan-safe-historical-review")

    def test_statement_real_pdf_reimport_preserves_fingerprints_and_balance(self):
        import fitz
        from apps.expenses.models import BankAccount, StatementUpload
        directory = self.enterContext(TemporaryDirectory(prefix="alfred-browser-statement-fixture-"))
        statement = Path(directory) / "synthetic-statement.pdf"
        header = (f"{'Date':<12}{'Narration':<35}{'Chq./Ref.No.':<18}{'Value Dt':<12}"
                  f"{'Withdrawal Amt.':<20}{'Deposit Amt.':<20}Closing Balance")
        line = (f"{'31/03/26':<12}{'UPI-SYNTHETIC-SHOP':<35}{'123456789012':<18}{'31/03/26':<12}"
                f"{'40.00':>16}    {'':>16}    {'1,210.00':>16}")
        with fitz.open() as pdf:
            page = pdf.new_page(width=1100, height=800)
            for top, text in ((40, "HDFC BANK Statement From: 01/03/2026 To: 31/03/2026"),
                              (55, "Account No: 999988887777"), (70, header), (100, line)):
                page.insert_text((30, top), text, fontname="cour", fontsize=9)
            statement.write_bytes(pdf.tobytes())
        self.login()
        self.browser.get(self.live_server_url + "/documents/")
        self.wait.until(lambda driver: driver.find_element(self.By.ID, "documentStatementFile"))
        for attempt in (1, 2):
            self.browser.execute_script("document.getElementById('documentStatementFile').value = '';")
            self.browser.find_element(self.By.ID, "documentStatementFile").send_keys(str(statement))
            self.click_upload_button("documentStatementForm")
            self.wait.until(lambda _: StatementUpload.objects.filter(file_name=statement.name).count() == attempt)
            self.wait.until(lambda _: "processed" in self.text("documentStatementFeedback").casefold())
            rows = list(Expense.objects.filter(source="bank_statement", bank_account__account_number="999988887777").values_list("transaction_fingerprint", "external_reference", "amount"))
            balances = list(BankAccount.objects.filter(account_number="999988887777").values_list("current_balance", flat=True))
            if attempt == 1:
                self.assertEqual(len(rows), 1)
                expected_rows, expected_balances = rows, balances
            else:
                self.assertEqual(rows, expected_rows)
                self.assertEqual(balances, expected_balances)
        self.capture("upload-statement-deduplication")

    def test_family_invitation_limits_show_safe_feedback_then_allow_valid_acceptance(self):
        from datetime import timedelta
        from django.utils import timezone
        from apps.family.models import FamilyAccountLink
        from apps.family.services import create_family_link_invite, family_financial_user_ids
        self.login()
        owner = get_user_model().objects.get(username="acceptance_demo")
        inviter = get_user_model().objects.create_user(username="browser_inviter", password=PASSWORD)
        link, code = create_family_link_invite(inviter)
        now = timezone.now()
        with override_settings(ALFRED_FAMILY_INVITE_CREATE_LIMIT=1, ALFRED_FAMILY_INVITE_CREATE_WINDOW_SECONDS=60,
                               ALFRED_FAMILY_INVITE_ACCEPT_LIMIT=1, ALFRED_FAMILY_INVITE_ACCEPT_WINDOW_SECONDS=60), patch(
                                   "django.utils.timezone.now", side_effect=lambda: now):
            self.browser.get(self.live_server_url + "/settings/")
            self.browser.find_element(self.By.ID, "settingsGenerateInviteBtn").click()
            self.wait.until(lambda _: "code generated" in self.text("settingsLinkFeedback"))
            self.assertTrue(self.text("settingsInviteCode").startswith("ALF-"))
            count = FamilyAccountLink.objects.count()
            self.browser.find_element(self.By.ID, "settingsGenerateInviteBtn").click()
            self.wait.until(lambda _: "throttled" in self.text("settingsLinkFeedback"))
            self.assertEqual(FamilyAccountLink.objects.count(), count)
            self.capture("family-create-throttled")
            field = self.browser.find_element(self.By.ID, "settingsInviteCodeInput")
            submit = self.browser.find_element(self.By.CSS_SELECTOR, '#settingsAcceptInviteForm button[type="submit"]')
            field.send_keys("ALF-AAAA-AAAA")
            submit.click()
            self.wait.until(lambda _: "cannot be accepted" in self.text("settingsLinkFeedback"))
            field.clear()
            field.send_keys(code)
            submit.click()
            self.wait.until(lambda _: "throttled" in self.text("settingsLinkFeedback"))
            link.refresh_from_db()
            self.assertEqual(link.status, "pending")
            self.capture("family-accept-throttled")
            now += timedelta(seconds=60)
            submit.click()
            self.wait.until(lambda _: "account connected" in self.text("settingsLinkFeedback"))
            self.wait.until(lambda _: "browser_inviter" in self.text("settingsLinkedAccountsList"))
            link.refresh_from_db()
            self.assertEqual(link.linked_user_id, owner.pk)
            self.assertEqual(family_financial_user_ids(owner), [owner.pk])
            self.capture("family-accept-after-retry")

    def test_family_growth_failure_shows_safe_message_and_can_recover(self):
        self.login()
        cache.clear()
        marker = "synthetic-private-family-finance-token"
        with patch("apps.family.views._family_growth_payload", side_effect=RuntimeError(marker)):
            self.browser.get(self.live_server_url + "/family/")
            self.wait.until(lambda _: "Family growth is temporarily unavailable. Please try again." in self.text("familyRoot"))
            self.assertNotIn(marker, self.browser.find_element(self.By.TAG_NAME, "body").text)
            self.capture("family-growth-safe-error")
        self.browser.refresh()
        self.wait.until(lambda _: "current net worth" in self.text("familySummaryCards").casefold())
        self.assertNotIn("temporarily unavailable", self.text("familyRoot"))
        self.capture("family-growth-safe-error-recovery")

    def test_family_financial_sharing_requires_owner_opt_in_and_can_be_revoked(self):
        from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
        from apps.family.services import accept_family_link_code, create_family_link_invite, family_financial_user_ids
        owner = get_user_model().objects.get(username="acceptance_demo")
        member = get_user_model().objects.create_user(username="browser_family_member", password=PASSWORD)
        link, code = create_family_link_invite(owner)
        accept_family_link_code(member, code)
        self.login()
        self.browser.get(self.live_server_url + "/settings/")
        selector = f'[data-family-link-action="financial-sharing"][data-family-link-id="{link.pk}"]'
        self.wait.until(lambda driver: driver.find_elements(self.By.CSS_SELECTOR, selector))
        self.assertIn("Share my financial summary", self.text("settingsLinkedAccountsList"))
        self.assertEqual(family_financial_user_ids(member), [member.pk])
        self.browser.find_element(self.By.CSS_SELECTOR, selector).click()
        self.wait.until(lambda driver: driver.switch_to.alert)
        self.assertIn("monthly income", self.browser.switch_to.alert.text)
        self.browser.switch_to.alert.dismiss()
        self.assertEqual(family_financial_user_ids(member), [member.pk])
        self.browser.find_element(self.By.CSS_SELECTOR, selector).click()
        self.browser.switch_to.alert.accept()
        self.wait.until(lambda _: "Stop sharing my financial summary" in self.text("settingsLinkedAccountsList"))
        self.assertEqual(set(family_financial_user_ids(member)), {owner.pk, member.pk})
        self.assertEqual(family_financial_user_ids(owner), [owner.pk])
        self.browser.refresh()
        self.wait.until(lambda _: "Stop sharing my financial summary" in self.text("settingsLinkedAccountsList"))
        expected_net_worth = resolve_canonical_financial_baseline(owner)["net_worth"]
        self.browser.delete_all_cookies()
        self.login("browser_family_member")
        self.browser.get(self.live_server_url + "/family/")
        expected_text = self.browser.execute_script("return Alfred.formatCurrency(arguments[0]);", float(expected_net_worth))
        self.wait.until(lambda _: self.text("familyNetWorthValue") == expected_text)
        self.browser.delete_all_cookies()
        self.login()
        self.browser.get(self.live_server_url + "/settings/")
        self.wait.until(lambda _: "Stop sharing my financial summary" in self.text("settingsLinkedAccountsList"))
        self.browser.find_element(self.By.CSS_SELECTOR, selector).click()
        self.wait.until(lambda _: "Share my financial summary" in self.text("settingsLinkedAccountsList"))
        self.assertEqual(family_financial_user_ids(member), [member.pk])
        self.assertIn("Connected", self.text("settingsLinkedAccountsList"))
        self.capture("family-financial-opt-in-revoked")
        self.browser.delete_all_cookies()
        self.login("browser_family_member")
        self.browser.get(self.live_server_url + "/family/")
        private_text = self.browser.execute_script("return Alfred.formatCurrency(0);")
        self.wait.until(lambda _: self.text("familyNetWorthValue") == private_text)

    def test_tax_planning_uses_selected_year_and_income(self):
        self.login()
        self.browser.get(self.live_server_url + "/tax-optimizer/")
        self.wait.until(lambda _: "Official-source rules verified" in self.text("taxPolicyCopy"))
        self.assertIn("FY 2025-26", self.text("taxPolicyCopy"))
        self.assertIn("AY 2026-27", self.text("taxPolicyCopy"))
        income = self.browser.find_element(self.By.ID, "taxAnnualIncome")
        income.clear()
        income.send_keys("1500000")
        self.browser.find_element(self.By.CSS_SELECTOR, "#taxInputForm button[type=submit]").click()
        self.wait.until(lambda _: "97,500" in self.text("taxAnnualValue"))
        self.assertEqual(self.text("taxRegimeValue"), "NEW")
        self.assertEqual(self.browser.find_element(self.By.ID, "taxFinancialYear").get_attribute("value"), "2025-26")
        self.capture("tax-policy-2025-26")

    def test_inferred_loan_requires_explicit_confirmation_on_real_page(self):
        from django.utils import timezone
        from apps.loans.models import Loan
        from selenium.common.exceptions import StaleElementReferenceException

        user = get_user_model().objects.get(username="acceptance_demo")
        loan = Loan.objects.create(
            user=user, loan_type="personal", lender="Estimated Test Lender",
            principal=240000, remaining_balance=240000, interest_rate=10, emi=10000,
            tenure_months=24, start_date=timezone.localdate(), auto_detected=True,
            verification_status="estimated", verification_source="emi_pattern",
        )
        self.login()
        self.browser.get(self.live_server_url + "/loans/")
        self.wait.until(lambda _: "1 estimated loan(s)" in self.text("loanVerificationNotice"))
        self.assertIn("1,00,000", self.text("loanSummaryCards"))
        self.assertNotIn("3,40,000", self.text("loanSummaryCards"))
        self.assertIn("Excluded from financial totals", self.text("loanTableBody"))
        self.capture("loan-estimate-excluded")
        def open_review(driver):
            try:
                driver.find_element(self.By.CSS_SELECTOR, f'button[onclick="editLoan({loan.pk})"]').click()
                return True
            except StaleElementReferenceException:
                # The live summary may replace a row between locating and clicking it.
                return False

        self.wait.until(open_review)
        self.assertFalse(self.browser.find_element(self.By.ID, "loanConfirmEstimate").is_selected())
        for field_id, value in (("manualLoanPrincipal", "200000"), ("manualLoanInterest", "8"),
                                ("manualLoanEmi", "9000"), ("manualLoanBalance", "150000")):
            field = self.browser.find_element(self.By.ID, field_id)
            field.clear()
            field.send_keys(value)
        self.browser.find_element(self.By.ID, "loanConfirmEstimate").click()
        self.browser.execute_script("document.getElementById('loanVerificationFields').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.capture("loan-terms-review")
        self.browser.find_element(self.By.ID, "loanSubmitButton").click()
        self.wait.until(lambda _: "2,50,000" in self.text("loanSummaryCards"))
        self.assertIn("19,000", self.text("loanSummaryCards"))
        self.assertFalse(self.browser.find_element(self.By.ID, "loanVerificationNotice").is_displayed())
        loan.refresh_from_db()
        self.assertEqual(loan.verification_status, "confirmed")
        self.assertEqual(loan.remaining_balance, 150000)
        self.browser.execute_script("document.getElementById('loanSummaryCards').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.wait.until(lambda driver: driver.execute_script(
            "const r = document.getElementById('loanSummaryCards').getBoundingClientRect(); return r.top >= 78 && r.bottom <= innerHeight;"
        ))
        self.capture("loan-estimate-confirmed")

    def test_vehicle_value_and_running_costs_are_separate_on_real_page(self):
        from django.utils import timezone
        from apps.mobility.models import BikeProfile, BikeServiceRecord

        user = get_user_model().objects.get(username="acceptance_demo")
        profile = BikeProfile.objects.create(
            user=user, display_name="Personal Test Scooter", model_name="Test Scooter",
            usage_pattern="personal", estimated_market_value=50000,
        )
        BikeServiceRecord.objects.create(
            user=user, bike_profile=profile, bike_name=profile.display_name,
            service_date=timezone.localdate(), cost=6000,
        )
        self.login()
        self.browser.get(self.live_server_url + "/expenses/")
        self.wait.until(lambda _: "Personal Test Scooter" in self.text("balanceSheetPanel"))
        cards = self.text("balanceSheetCards")
        self.assertIn("2,10,000", cards)
        self.assertIn("1,00,000", cards)
        panel = self.text("balanceSheetPanel")
        self.assertIn("Estimated asset ₹50,000", panel)
        self.assertIn("Recorded running costs ₹6,000", panel)
        self.assertIn("all history", panel)
        self.assertNotIn("Lifestyle vehicle burden", panel)
        self.browser.execute_script("document.getElementById('balanceSheetPanel').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.capture("vehicle-value-and-running-costs")

    def test_investment_projection_starts_with_recorded_value_on_real_page(self):
        self.login()
        self.browser.get(self.live_server_url + "/investments/")
        self.wait.until(lambda _: "1,10,000" in self.text("investmentHeroValue"))
        self.wait.until(lambda driver: driver.execute_script(
            "return Boolean(Chart.getChart(document.getElementById('growthChart')));"
        ))
        chart = self.browser.execute_script(
            "const d = Chart.getChart(document.getElementById('growthChart')).data; "
            "return {labels: d.labels, values: d.datasets[0].data};"
        )
        self.assertEqual(len(chart["labels"]), 13)
        self.assertEqual(len(chart["values"]), 13)
        self.assertEqual(chart["values"][0], 110000)
        self.assertEqual(chart["values"][1], 115766.67)
        factor = 1 + 8 / 1200
        expected_year = 110000 * factor ** 12 + 5000 * factor * (factor ** 12 - 1) / (factor - 1)
        self.assertAlmostEqual(chart["values"][12], expected_year, places=2)
        assumptions = self.text("investmentGrowthAssumptions")
        self.assertIn("Month 0", assumptions)
        self.assertIn("beginning of each month", assumptions)
        (self.artifacts / "investment-growth-values.json").write_text(json.dumps(chart, indent=2), encoding="utf-8")
        self.browser.execute_script("document.getElementById('growthChart').scrollIntoView({behavior: 'instant', block: 'center'});")
        self.capture("investment-month-zero-projection")

    def test_sample_totals_and_explanations_on_real_pages(self):
        self.login()
        summary = self.text("dashboardSummaryCards")
        for expected in ("30,000", "80,000", "47,000", "1,00,000", "Confirmed Outflow"):
            self.assertIn(expected.lower(), summary.lower())
        self.assertIn("33,000", self.text("dashboardFocusStrip"))
        self.assertIn("48.8%", self.text("dashboardFocusStrip"))
        self.assertIn("All recorded months", self.text("dashboardFocusStrip"))
        self.assertIn("60,000", self.text("dashboardReviewNotice"))
        self.assertIn("excluded", self.text("dashboardReviewNotice"))
        self.assertEqual(self.text("healthScoreValue"), "—")
        self.assertIn("Review transactions first", self.text("healthRiskPill"))
        charts = self.browser.execute_script("return Chart.getChart(document.getElementById('dashboardMonthlyChart')).data.datasets.map(d => ({label:d.label, last:d.data.at(-1)}));")
        amounts = {item["label"]: item["last"] for item in charts}
        self.assertEqual(amounts["Card payments"], 2000)
        self.assertEqual(amounts["Investments"], 5000)
        self.assertEqual(sum(amount for label, amount in amounts.items() if label != "Income"), 47000)
        (self.artifacts / "chart-values.json").write_text(json.dumps(amounts, indent=2), encoding="utf-8")
        self.capture("dashboard")

        self.browser.get(self.live_server_url + "/budgets/")
        self.wait.until(lambda driver: "10,000" in self.text("budgetSummaryCards"))
        self.assertIn("30,000", self.text("budgetPlanValue"))
        self.assertIn("20,000", self.text("budgetRemainingValue"))
        self.assertIn("20,000", self.text("budgetAffordabilityPanel"))
        self.assertIn("already reserved", self.text("budgetRoot"))
        self.assertIn("6,000", self.text("budgetCategoryBody"))
        self.assertIn("4,000", self.text("budgetCategoryBody"))
        self.capture("budget")

        self.browser.get(self.live_server_url + "/loans/")
        self.wait.until(lambda driver: "1,00,000" in self.text("loanSummaryCards"))
        self.assertIn("10,000", self.text("loanSummaryCards"))
        self.assertIn("Recorded Loan Balance".lower(), self.text("loanSummaryCards").lower())
        self.capture("loans")

        self.browser.get(self.live_server_url + "/investments/")
        self.wait.until(lambda driver: "1,10,000" in self.text("investmentHeroValue"))
        self.assertIn("10,000", self.text("investmentSummaryCards"))
        self.assertIn("unrealized", self.text("investmentSummaryCards").lower())
        self.capture("investments")

    def test_empty_account_displays_missing_history_instead_of_a_bad_score(self):
        get_user_model().objects.create_user(username="empty_acceptance", password=PASSWORD)
        self.login("empty_acceptance")
        self.assertEqual(self.text("healthScoreValue"), "—")
        self.assertIn("No transactions yet", self.text("dashboardPeriodNote"))
        self.assertIn("—", self.text("dashboardFocusStrip"))
        self.capture("empty-dashboard")

    def test_expense_form_preserves_import_identity_and_bank_cents(self):
        from decimal import Decimal
        from types import SimpleNamespace
        from apps.expenses.models import BankAccount
        from apps.expenses.serializers import ExpenseSerializer
        from apps.expenses.services.statement_lifecycle import _import_statement_transactions
        from tests.test_expense_money_identity import parsed_fixture
        from apps.expenses.models import StatementUpload
        from django.utils import timezone

        user = self.scenario["user"]
        account = BankAccount.objects.create(user=user, account_number="TEST0001", current_balance="10.005")
        serializer = ExpenseSerializer(data={"amount": "2.675", "closing_balance": "10.005", "bank_account": account.pk, "transaction_date": timezone.localdate().isoformat(), "source": "bank_statement", "raw_description": "UPI SAMPLE MERCHANT", "description": "UPI SAMPLE MERCHANT", "external_reference": "REF-001", "category": "shopping"}, context={"request": SimpleNamespace(user=user)})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        row = serializer.save(user=user)
        row.refresh_from_db()
        fingerprint, identity = row.transaction_fingerprint, row.transaction_identity
        self.login()
        self.browser.get(self.live_server_url + "/expenses/")
        self.wait.until(lambda driver: driver.execute_script("return expenseIndex.has(arguments[0]);", row.pk))
        self.browser.execute_script("openEditModal(arguments[0]);", row.pk)
        self.wait.until(lambda _: self.browser.find_element(self.By.ID, "expenseSubmitBtn").is_displayed())
        form = self.browser.find_element(self.By.ID, "expenseForm")
        self.assertEqual(form.find_element(self.By.NAME, "amount").get_attribute("value"), "2.68")
        from selenium.webdriver.support.ui import Select
        Select(form.find_element(self.By.NAME, "category")).select_by_value("food")
        self.browser.find_element(self.By.ID, "expenseSubmitBtn").click()
        self.wait.until(lambda _: not self.browser.find_element(self.By.ID, "expenseSubmitBtn").is_displayed())
        row.refresh_from_db()
        account.refresh_from_db()
        self.assertEqual(row.category, "food")
        self.assertEqual((row.transaction_fingerprint, row.transaction_identity), (fingerprint, identity))
        self.assertEqual((row.amount, row.closing_balance, account.current_balance), (Decimal("2.68"), Decimal("10.01"), Decimal("10.01")))
        upload = StatementUpload.objects.create(user=user, bank_account=account, file_name="synthetic.pdf")
        parsed = parsed_fixture(closing=15.005)
        parsed.transactions[0].transaction_date = row.transaction_date
        created, skipped = _import_statement_transactions(user=user, upload=upload, bank_account=account, parsed=parsed)
        self.assertEqual((len(created), skipped), (0, 1))
        payload = self.browser.execute_async_script("const done=arguments[0]; fetch('/api/expenses/').then(r=>r.json()).then(done);")
        rows = payload if isinstance(payload, list) else payload["results"]
        displayed = next(item for item in rows if item["id"] == row.pk)
        self.assertEqual(displayed["amount"], 2.68)
        self.assertEqual(displayed["closing_balance"], 10.01)
        self.capture("expense-money-identity")

    def test_old_transactions_show_their_actual_reporting_month(self):
        Expense.objects.filter(user=self.scenario["user"]).update(transaction_date=month_start(-1))
        cache.clear()
        self.login()
        self.assertIn(month_start(-1).strftime("%B %Y"), self.text("dashboardPeriodNote"))
        self.assertNotIn("Current Month", self.text("dashboardSummaryCards"))
        self.capture("older-history-dashboard")
