"""Opt-in real local fictional benchmark: test success is not an accuracy verdict."""
import json
import os
from pathlib import Path
from unittest import skipUnless

from django.test import TestCase

from apps.ml_engine.services.retrieval_quality import MODELS, compare


@skipUnless(os.environ.get('ALFRED_RUN_OLLAMA_GROUNDING')=='true','Explicit fictional local acceptance required.')
class RealRetrievalQualityTests(TestCase):
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
