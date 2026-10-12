"""Synthetic assistant availability, safe failures and existing GET compatibility."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from tests.test_persistent_memory import SyntheticEmbeddings


class IntelligenceUITests(TestCase):
    def setUp(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-ui-synthetic-')))
        self.enterContext(override_settings(ALFRED_MEMORY_DIR=str(root/'vault'), ALFRED_ABUSE_THROTTLE_DIR=str(root/'limits')))
        self.enterContext(patch('apps.ml_engine.services.persistent_memory.OllamaEmbeddings', return_value=SyntheticEmbeddings()))
        self.user = get_user_model().objects.create_user(username='synthetic-ui-owner')
        self.client.force_login(self.user)

    def test_status_is_bounded_local_only_and_does_not_build_financial_insights(self):
        with patch('apps.ml_engine.api.views.OllamaReasoner') as model, patch('apps.ml_engine.api.views.build_financial_intelligence') as finance:
            before = time.monotonic()
            response = self.client.get('/api/ai/personal-insights/?assistant_status=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['local_model_status'], 'available')
        self.assertLessEqual(model.return_value._digest.call_args.kwargs['deadline'], before+1.5)
        finance.assert_not_called()
        self.assertIn('no-store', response['Cache-Control'])

    def test_unavailable_status_does_not_expose_internal_diagnostics(self):
        with patch('apps.ml_engine.api.views.OllamaReasoner') as model:
            model.return_value._digest.side_effect = EmbeddingUnavailable('C:/private/loan-123.txt secret-token')
            response = self.client.get('/api/ai/personal-insights/?assistant_status=1')
        self.assertEqual(response.json()['local_model_status'], 'unavailable')
        self.assertNotIn('secret-token', str(response.json()))

    def test_generation_failure_preserves_safe_code_reference_and_status(self):
        with patch('apps.ml_engine.services.hybrid_intelligence.OllamaReasoner') as model:
            model.return_value.reason.side_effect = EmbeddingUnavailable('C:/private/OCR-sensitive')
            response = self.client.post('/api/ai/personal-insights/', {'query':'synthetic question'}, content_type='application/json')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'local_model_unavailable')
        self.assertTrue(response.json()['error_id'])
        self.assertNotIn('OCR-sensitive', str(response.json()))

    def test_existing_insights_get_does_not_probe_or_replace_its_contract(self):
        with patch('apps.ml_engine.api.views.OllamaReasoner') as model, patch('apps.ml_engine.api.views.build_financial_intelligence', return_value={'metrics':{'known':42}}):
            response = self.client.get('/api/ai/personal-insights/')
        model.assert_not_called()
        self.assertEqual(response.json()['metrics'], {'known':42})
