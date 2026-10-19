"""Opt-in real local fictional benchmark: test success is not an accuracy verdict."""
import json
import os
from pathlib import Path
from unittest import skipUnless

from django.test import TestCase

from apps.ml_engine.services.retrieval_quality import MODELS, compare
from apps.ml_engine.services.persistent_memory import RETRIEVAL_PROTOCOLS


@skipUnless(os.environ.get('ALFRED_RUN_OLLAMA_GROUNDING')=='true','Explicit fictional local acceptance required.')
class RealRetrievalQualityTests(TestCase):
    def test_independent_heldout_protocol_candidate_is_measured_without_tuning_or_activation(self):
        from apps.ml_engine.services.retrieval_holdout import FIXTURE_SHA256, POLICY_SHA256
        report=compare(MODELS[0],MODELS[0],suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        Path(os.environ['ALFRED_DIAGNOSTIC_OUTPUT']).with_name('independent-heldout-protocol.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        # A completed experiment can correctly REJECT; never force a passing accuracy verdict.
        self.assertIn(report['decision'],('ELIGIBLE_FOR_REVIEW','REJECT'))
        self.assertEqual(report['cohort_id'],FIXTURE_SHA256); self.assertEqual(report['frozen_policy_sha256'],POLICY_SHA256)
        self.assertEqual(report['suite'],'held_out'); self.assertEqual(report['cases'],12)
        self.assertEqual(report['candidate_execution'],'independent_protocol_run'); self.assertFalse(report['runtime_changed'])
        for side in ('baseline','candidate'):
            cohort=report[side]['results'][0]
            self.assertEqual(cohort['owner_violations'],0); self.assertTrue(cohort['stale_rejected'])
            self.assertTrue(cohort['owner_reference_rejected']); self.assertEqual(len(cohort['per_case']),12)
            self.assertEqual(set(cohort['precision_at_k']),{'1','2','3'})

    def test_development_protocol_candidate_is_measured_without_activation(self):
        report=compare(MODELS[0],MODELS[0],candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        Path(os.environ['ALFRED_DIAGNOSTIC_OUTPUT']).with_name('development-protocol.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        self.assertIn(report['decision'],('ELIGIBLE_FOR_REVIEW','REJECT'))
        self.assertEqual(report['candidate_execution'],'independent_protocol_run')
        self.assertFalse(report['runtime_changed']); self.assertEqual(report['cases'],24)
        self.assertEqual(report['baseline_protocol'],RETRIEVAL_PROTOCOLS[0])
        for side in ('baseline','candidate'):
            for result in report[side]['results']:
                self.assertEqual(result['owner_violations'],0); self.assertTrue(result['stale_rejected'])
                self.assertTrue(result['owner_reference_rejected'])
                self.assertEqual(set(result['precision_at_k']),{'1','2','3'})

    def test_reviewed_cohorts_produce_measured_verdict_without_model_activation(self):
        report=compare(MODELS[0],MODELS[0])
        Path(os.environ['ALFRED_DIAGNOSTIC_OUTPUT']).with_name('cohort-quality.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        self.assertIn(report['decision'],('REFERENCE_ONLY','REJECT'))
        self.assertEqual(report['candidate_execution'],'baseline_reference_reused')
        self.assertFalse(report['runtime_changed']); self.assertEqual(report['cases'],24)
        for side in ('baseline','candidate'):
            self.assertEqual(len(report[side]['results']),2)
            for cohort in report[side]['results']:
                self.assertEqual(cohort['owner_violations'],0)
                self.assertTrue(cohort['stale_rejected']); self.assertTrue(cohort['owner_reference_rejected'])
        for row in report['differences']: self.assertAlmostEqual(row['delta'],0,places=6)
