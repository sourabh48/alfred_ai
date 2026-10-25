from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.utils import timezone

from apps.ml_engine.models import AdaptiveModelState
from apps.ml_engine.training.orchestrator import TRAINING_SPECS


class ServingReadinessTests(TestCase):
    URL='/api/ai/runtime-status/?serving_readiness=1'

    def setUp(self):
        self.root=Path(self.enterContext(TemporaryDirectory(prefix='alfred-serving-synthetic-')))
        self.owner=get_user_model().objects.create_user(username='synthetic-serving-owner')
        self.client.force_login(self.owner)
        self.artifact=self.root/'synthetic-unusable.pkl'; self.artifact.write_bytes(b'not a trained model')

    def state(self,**changes):
        values=dict(display_name='SYNTHETIC-PRIVATE-NAME',status='ready',sample_count=80,quality_score=80,
            confidence_estimate=80,artifact_path=str(self.artifact),notes='SYNTHETIC-PRIVATE-NOTE',
            next_refresh_due_at=timezone.now()+timedelta(hours=12),last_finished_at=None)
        values.update(changes)
        return AdaptiveModelState.objects.update_or_create(model_key='expense_forecaster',defaults=values)[0]

    def expense(self):
        response=self.client.get(self.URL); self.assertEqual(response.status_code,200)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        return next(item for item in response.json()['models'] if item['key']=='expense_forecaster')

    def test_public_projection_has_no_private_fields_or_accuracy_claims(self):
        self.state()
        response=self.client.get(self.URL); self.assertEqual(response.status_code,200)
        body=response.content.decode()
        for secret in ('SYNTHETIC-PRIVATE',str(self.root),'artifact_path','sample_count','quality_score','confidence_estimate','approved_by'):
            self.assertNotIn(secret,body)
        self.assertEqual({item['key'] for item in response.json()['models']},{spec.key for spec in TRAINING_SPECS})
        self.assertIn('does not prove',response.json()['scope'])
        self.assertEqual(self.expense()['status'],'registry_eligible')

    def test_missing_stale_nonfinite_or_inadequate_metadata_blocks_eligibility(self):
        cases=[dict(artifact_path=''),dict(artifact_path=str(self.root/'missing.pkl')),
            dict(next_refresh_due_at=timezone.now()-timedelta(seconds=1)),dict(sample_count=1),
            dict(quality_score=49),dict(confidence_estimate=54),dict(status='failed'),
            dict(last_finished_at=timezone.now()+timedelta(hours=1))]
        for changes in cases:
            with self.subTest(fields=sorted(changes)):
                self.state(**changes); result=self.expense()
                self.assertFalse(result['registry_eligible']); self.assertEqual(result['status'],'fallback')
        self.state(quality_score=float('inf')); self.assertFalse(self.expense()['registry_eligible'])

    def test_proxy_targets_are_never_presented_as_validated_serving(self):
        AdaptiveModelState.objects.create(model_key='burnout_rf',display_name='Synthetic',status='ready',
            sample_count=100,quality_score=99,confidence_estimate=99,artifact_path=str(self.artifact),
            next_refresh_due_at=timezone.now()+timedelta(hours=12))
        result=next(item for item in self.client.get(self.URL).json()['models'] if item['key']=='burnout_rf')
        self.assertFalse(result['registry_eligible']); self.assertEqual(result['status'],'fallback')

    def test_scores_above_their_declared_scale_never_enable_inference(self):
        for changes in (dict(quality_score=101),dict(confidence_estimate=101)):
            with self.subTest(fields=sorted(changes)):
                self.state(**changes)
                self.assertFalse(self.expense()['registry_eligible'])

    def test_eligible_registry_does_not_bypass_artifact_validation_or_fallback(self):
        from apps.ml_engine.inference_adapters.expense_lstm import ExpenseLSTMAdapter
        self.state(); self.assertTrue(self.expense()['registry_eligible'])
        with patch('apps.ml_engine.inference_adapters.expense_lstm.MODEL_PATH',str(self.artifact)):
            self.assertEqual(ExpenseLSTMAdapter().predict([10,20]),15)
        self.assertIn('recent median',self.expense()['fallback'])

    def test_out_of_range_artifact_scores_use_deterministic_fallback_without_prediction(self):
        from apps.ml_engine.inference_adapters.expense_lstm import ExpenseLSTMAdapter
        for changes in (dict(quality_score=101),dict(confidence_estimate=101)):
            with self.subTest(fields=sorted(changes)):
                model=Mock()
                payload=dict(model=model,trained_at=timezone.now().isoformat(),freshness_hours=12,
                    evaluation={'passed':True},sample_count=80,quality_score=80,confidence_estimate=80,window_size=10)
                payload.update(changes)
                with patch('apps.ml_engine.inference_adapters.expense_lstm.joblib.load',return_value=payload):
                    self.assertEqual(ExpenseLSTMAdapter().predict([10,20]),15)
                model.predict.assert_not_called()

    def test_authentication_parameter_validation_and_no_training_or_loading(self):
        self.assertEqual(Client().get(self.URL).status_code,403)
        for query in ('serving_readiness=0','serving_readiness=1&serving_readiness=1','serving_readiness=1&path=private'):
            self.assertEqual(self.client.get('/api/ai/runtime-status/?'+query).status_code,400)
        with patch('apps.ml_engine.api.views.run_training_cycle') as train, patch('joblib.load') as load:
            self.expense(); train.assert_not_called(); load.assert_not_called()

    def test_unknown_model_notes_and_runtime_errors_fail_closed(self):
        AdaptiveModelState.objects.create(model_key='SYNTHETIC-PRIVATE-UNKNOWN',display_name='SYNTHETIC-PRIVATE-NAME')
        self.assertNotIn('SYNTHETIC-PRIVATE',self.client.get(self.URL).content.decode())
        with patch('apps.ml_engine.api.views.serving_readiness_snapshot',side_effect=RuntimeError('SYNTHETIC-PRIVATE-DIAGNOSTIC')):
            response=self.client.get(self.URL)
        self.assertEqual(response.status_code,503); self.assertEqual(response['Cache-Control'],'no-store, private')
        self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())
