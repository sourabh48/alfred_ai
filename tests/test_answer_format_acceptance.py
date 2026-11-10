"""Opt-in real Chrome/Ollama formatting acceptance with an isolated synthetic user."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
import time
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.handlers.base import BaseHandler
from django.test import override_settings

from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches
from tests import test_document_review_browser as browser_support


@skipUnless(os.environ.get('ALFRED_RUN_LOCAL_AI_ACCEPTANCE') == 'true' and os.environ.get('ALFRED_RUN_BROWSER_TESTS') == 'true',
            'Requires explicit actual local model and browser acceptance')
class AnswerFormatAcceptance(StaticLiveServerTestCase):
    def test_actual_local_model_renders_a_formatted_comparison(self):
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        lock = Lock(); original = BaseHandler.get_response
        def serialized(handler,request):
            # Same in-memory SQLite request boundary as the existing browser suite.
            with lock: return original(handler,request)
        with TemporaryDirectory(prefix='alfred-format-real-synthetic-') as directory, override_settings(
                ALFRED_MEMORY_DIR=str(Path(directory)/'vault'),ALFRED_CONVERSATION_HISTORY_AUTHORIZED=False,
                ALFRED_MEMORY_OPENAI_AUTHORIZED=False,ALFRED_MEMORY_CLOUD_AUTHORIZED=False), \
                _offline_fixture_patches(), patch.object(BaseHandler,'get_response',serialized):
            owner = get_user_model().objects.create_user(username='synthetic-format-real-model')
            self.client.force_login(owner)
            browser = browser_support.DocumentReviewBrowserTests._create_driver(webdriver)
            try:
                browser.get(self.live_server_url+'/login/')
                browser.add_cookie(dict(name=settings.SESSION_COOKIE_NAME,value=self.client.session.session_key,path='/'))
                browser.get(self.live_server_url+'/ai/insights/')
                wait = WebDriverWait(browser,40)
                wait.until(lambda _: 'Ollama available' in browser.find_element(By.ID,'intelligenceLocalStatus').text)
                query = ('Use a Markdown heading Fictional painting and a two-column pipe table (Style, Mood). '
                         'For the first row use Style=Calm, Mood=Quiet. For the next row use Style=Lively, Mood=Bright. This is fiction.')
                started = time.monotonic()
                browser.find_element(By.ID,'intelligenceQuery').send_keys(query,Keys.CONTROL,Keys.ENTER)
                wait.until(lambda _: bool(browser.find_elements(By.CSS_SELECTOR,'.assistant-answer table')))
                wait.until(lambda _: browser.find_element(By.ID,'intelligenceQuery').get_property('value') == '')
                answer = browser.find_element(By.CSS_SELECTOR,'.assistant-answer')
                self.assertIn('Calm',answer.text); self.assertIn('Lively',answer.text)
                self.assertEqual(len(answer.find_elements(By.CSS_SELECTOR,'tbody tr')),2)
                self.assertTrue(answer.find_elements(By.CSS_SELECTOR,'h3,h4,h5,h6'))
                self.assertIn('Ollama (local)',browser.find_element(By.ID,'intelligenceAnswers').text)
                artifacts = Path('artifacts/answer-format-20261110'); artifacts.mkdir(parents=True,exist_ok=True)
                browser.save_screenshot(str(artifacts/'actual-local-formatted-answer.png'))
                print(f'ACTUAL_LOCAL_FORMATTED_BROWSER_PASS seconds={time.monotonic()-started:.3f}')
            finally:
                browser.quit()
