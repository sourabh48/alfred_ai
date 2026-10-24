"""Deterministic reviewed-fictional comparison contracts, not model accuracy claims."""
from copy import deepcopy
import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.ml_engine.services.local_embeddings import EmbeddingUnavailable
from apps.ml_engine.services.persistent_memory import MemoryConflict
from apps.ml_engine.services.retrieval_quality import COHORTS, MODELS, POLICY, _BudgetedEmbeddings, _SyntheticCache, assess, compare, configuration
from apps.ml_engine.services.persistent_memory import RETRIEVAL_PROTOCOLS
from tests import test_memory_learning as fixtures


class ContractEmbeddings:
    def __init__(self, identity='contract-baseline-v1', degraded=False, *, cohorts=COHORTS):
        self.identity, self.degraded = identity, degraded
        # Expected-label vectors validate metrics/control flow only, never real accuracy.
        self.cohorts=cohorts
        self.mapping = {}
        offset = 0
        for cohort in cohorts:
            local = {key: offset+i for i, key in enumerate(cohort['records'])}
            local['corrected'] = local['trail'] if 'trail' in local else offset+7
            if 'contrary' in local: local['contrary'] = local['coast']
            if 'counterclaim' in local: local['counterclaim'] = local['pigment']
            for key, text in cohort['records'].items(): self.mapping[text] = local[key]
            self.mapping[cohort['correction'][1]] = local['corrected']
            for i, (query, expected) in enumerate(cohort['cases']):
                self.mapping[query] = local[expected[0]] if expected else offset+8+i
            offset += 25

    def embed(self, text, *, deadline=None):
        if text.startswith('{'): text = json.loads(text)['statement']
        index = self.mapping[text]
        if self.degraded and text in {c['cases'][0][0] for c in self.cohorts}: index = 63
        return [int(i == index) for i in range(64)], self.identity


def contract_comparison(degraded=False, *, suite='development', candidate_protocol=RETRIEVAL_PROTOCOLS[0]):
    from apps.ml_engine.services.retrieval_quality import _contract
    cohorts,_=_contract(suite)
    return compare(*MODELS, adapters={MODELS[0]:ContractEmbeddings(cohorts=cohorts), MODELS[1]:ContractEmbeddings('contract-candidate-v2', degraded,cohorts=cohorts)},suite=suite,candidate_protocol=candidate_protocol)


class RetrievalQualityTests(TestCase):
    def setUp(self):
        fixtures.MemoryLearningTests.setUp(self)

    def test_two_independent_cohorts_model_profiles_and_safety_probes(self):
        report = contract_comparison()
        self.assertEqual(report['decision'], 'ELIGIBLE_FOR_REVIEW')
        self.assertFalse(report['runtime_changed']); self.assertTrue(report['promotion_requires_approval'])
        self.assertEqual(report['cases'],24); self.assertEqual(len(report['differences']),8)
        self.assertEqual(report['policy'],POLICY)
        for result in report['candidate']['results']:
            for metric in ('precision','recall','citation_correctness','abstention_rate'): self.assertEqual(result[metric],1)
            self.assertEqual(result['owner_violations'],0)
            self.assertTrue(result['owner_reference_rejected']); self.assertTrue(result['stale_rejected'])
            self.assertEqual(len(result['per_case']),12)
            for case in result['per_case']:
                self.assertEqual(case['unexpected_sources'],[]); self.assertEqual(case['missing_sources'],[])
                self.assertEqual(set(case['expected_sources']),set(case['returned_sources']))
                self.assertNotIn('citations',case); self.assertNotIn('expected_ids',case)
        before,after = report['baseline']['results'][0],report['candidate']['results'][0]
        self.assertNotEqual(before['context']['embedding_identity'],after['context']['embedding_identity'])
        self.assertEqual(self.store.list_memories(self.alice),[])

    def test_real_retrieval_regression_rejects_candidate_without_model_switch(self):
        report = contract_comparison(degraded=True)
        self.assertEqual(report['decision'],'REJECT'); self.assertFalse(report['runtime_changed'])
        self.assertTrue(any(reason.endswith('recall_regression') for reason in report['reasons']))
        self.assertLess(report['candidate']['results'][0]['recall'],1)
        self.assertEqual(report['candidate']['results'][0]['per_case'][0]['missing_sources'],['trail','corrected'])

    def test_identical_model_uses_one_reference_and_is_not_new_model_promotion_evidence(self):
        baseline=contract_comparison()['baseline']
        with patch('apps.ml_engine.services.retrieval_quality._measure',return_value=baseline) as measure:
            result=compare(MODELS[0],MODELS[0])
        measure.assert_called_once()
        self.assertEqual(result['decision'],'REFERENCE_ONLY')
        self.assertEqual(result['candidate_execution'],'baseline_reference_reused')

    def test_guard_failure_rejects_without_claiming_completed_model_measurements(self):
        with patch('apps.ml_engine.services.retrieval_quality._measure',side_effect=MemoryConflict('Synthetic stale source')):
            report=compare(*MODELS)
        self.assertEqual(report['decision'],'REJECT')
        self.assertIsNone(report['baseline']); self.assertIsNone(report['candidate'])
        self.assertNotIn('candidate_execution',report)

    def test_protocol_comparison_is_not_reused_or_automatic_runtime_activation(self):
        report=compare(MODELS[0],MODELS[0],adapters={MODELS[0]:ContractEmbeddings()},candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        self.assertEqual(report['decision'],'ELIGIBLE_FOR_REVIEW')
        self.assertEqual(report['candidate_execution'],'independent_protocol_run')
        self.assertFalse(report['runtime_changed'])
        self.assertEqual(report['candidate']['results'][0]['context']['protocol'],RETRIEVAL_PROTOCOLS[1])
        self.assertNotEqual(report['baseline']['results'][0]['context']['embedding_identity'],report['candidate']['results'][0]['context']['embedding_identity'])

    def test_independent_holdout_commitment_and_partition_separation(self):
        from hashlib import sha256
        from apps.ml_engine.services import retrieval_holdout as held
        self.assertEqual(len(held.RAW.encode()),1587)
        self.assertEqual(sha256(held.RAW.encode()).hexdigest(),held.FIXTURE_SHA256)
        cohort=held.cohort()
        self.assertEqual(len(cohort['cases']),12)
        self.assertEqual(sum(bool(expected) for _,expected in cohort['cases']),6)
        self.assertFalse(set(cohort['records'].values()) & {value for item in COHORTS for value in item['records'].values()})
        self.assertFalse({query for query,_ in cohort['cases']} & {query for item in COHORTS for query,_ in item['cases']})
        cohort['records'].clear()
        self.assertEqual(len(held.cohort()['records']),7)  # No mutable shared fixture.
        self.assertEqual(POLICY['min_precision'],.90); self.assertEqual(POLICY['min_recall'],.85)
        self.assertEqual(POLICY['min_abstention_rate'],.95); self.assertEqual(POLICY['max_metric_drop'],.05)

    def test_heldout_binds_labels_policy_and_complete_metrics_without_runtime_changes(self):
        from apps.ml_engine.services.retrieval_holdout import FIXTURE_SHA256, POLICY_COMMIT, POLICY_SHA256
        report=contract_comparison(suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        self.assertEqual(report['suite'],'held_out'); self.assertEqual(report['cohort_id'],FIXTURE_SHA256)
        self.assertEqual(report['frozen_policy_commit'],POLICY_COMMIT); self.assertEqual(report['frozen_policy_sha256'],POLICY_SHA256)
        self.assertEqual(report['cases'],12); self.assertEqual(report['decision'],'ELIGIBLE_FOR_REVIEW')
        self.assertEqual(report['quality_scope'],'selected_partition_only_no_automatic_promotion')
        self.assertFalse(report['runtime_changed']); self.assertEqual(self.store.list_memories(self.alice),[])
        cohort=report['candidate']['results'][0]
        self.assertCountEqual(cohort['per_case'][0]['returned_sources'],['pigment','counterclaim'])
        self.assertEqual(cohort['retrieval_errors'],dict(unexpected_references=0,missed_references=0,false_abstentions=0,false_matches=0))
        for k in ('1','2','3'):
            self.assertIn(k,cohort['precision_at_k']); self.assertIn(k,cohort['recall_at_k'])
        self.assertEqual(assess(report['baseline'],report['candidate'])['decision'],'BLOCKED')
        missing=deepcopy(report['candidate']); missing['results'][0]['per_case'].pop()
        self.assertEqual(assess(report['baseline'],missing,suite='held_out')['decision'],'BLOCKED')
        for case in cohort['per_case']:
            self.assertNotIn('expected_ids',case); self.assertNotIn('citations',case)
        self.assertEqual(contract_comparison(True,suite='held_out')['decision'],'REJECT')

    def test_modified_holdout_or_policy_blocks_before_model_and_does_not_break_default_configuration(self):
        from apps.ml_engine.services import retrieval_holdout as held
        for path,value in (('RAW',held.RAW+' '),('POLICY_SHA256','0'*64)):
            with self.subTest(path=path),patch.object(held,path,value):
                self.assertFalse(configuration()['held_out_available'])
                with patch('apps.ml_engine.services.retrieval_quality.OllamaEmbeddings') as model:
                    with self.assertRaises(ValueError): compare(*MODELS,suite='held_out')
                    model.assert_not_called()
        with patch.object(held.Path,'read_bytes',side_effect=OSError('SYNTHETIC-private path')):
            self.assertFalse(configuration()['held_out_available'])
        for suite in ('remote',None,{}):
            with self.assertRaises(ValueError): compare(*MODELS,suite=suite)

    def test_synthetic_cache_reuses_only_identical_inputs_and_rechecks_real_model_identity(self):
        from unittest.mock import Mock
        raw=Mock(); raw.model=MODELS[0]; raw.embed.return_value=([1,0],MODELS[0]+'@'+'1'*64); raw._digest.return_value='1'*64
        cache=_SyntheticCache(raw)
        first=cache.embed('Fictional input',deadline=30); first[0][0]=0
        self.assertEqual(cache.embed('Fictional input',deadline=30)[0],[1,0]); self.assertEqual(raw.embed.call_count,1)
        raw._digest.return_value='2'*64
        with self.assertRaises(EmbeddingUnavailable): cache.embed('Fictional input',deadline=30)

    def test_thresholds_boundaries_missing_metrics_tamper_and_incomparable_cohorts(self):
        report=contract_comparison(); baseline=report['baseline']
        for metric in ('precision','recall','citation_correctness','abstention_rate'):
            changed=deepcopy(baseline); changed['results'][0][metric]=POLICY['min_'+metric]-.01
            with self.subTest(metric=metric): self.assertEqual(assess(baseline,changed)['decision'],'REJECT')
            for invalid in (None,float('nan'),True,1.1):
                changed['results'][0][metric]=invalid
                self.assertEqual(assess(baseline,changed)['decision'],'BLOCKED')
        for key,value in (('owner_violations',1),('owner_reference_rejected',False),('stale_rejected',False)):
            changed=deepcopy(baseline); changed['results'][0][key]=value
            self.assertEqual(assess(baseline,changed)['decision'],'REJECT')
        for key,value in (('cohort_id','unreviewed'),('cutoff',.2),('results',[])):
            self.assertEqual(assess(baseline,baseline|{key:value})['decision'],'BLOCKED')

    def test_disabled_and_invalid_api_does_not_read_private_vault_or_call_any_model(self):
        self.client.force_login(self.alice)
        payload=dict(action='compare',baseline_model=MODELS[0],candidate_model=MODELS[1])
        with patch('apps.ml_engine.api.memory.memory_store',side_effect=AssertionError('No private vault')):
            self.assertEqual(self.client.post('/api/ai/memories/learning/',payload,content_type='application/json').status_code,403)
            with override_settings(ALFRED_SYNTHETIC_QUALITY_ENABLED=True):
                for extra in ({'candidate_model':'remote-model:cloud'},{'cases':[]},{'policy':{'min_recall':0}},{'suite':'unreviewed'},{'candidate_protocol':'unknown'}):
                    self.assertEqual(self.client.post('/api/ai/memories/learning/',payload|extra,content_type='application/json').status_code,400)

    @override_settings(ALFRED_SYNTHETIC_QUALITY_ENABLED=True)
    def test_api_selects_frozen_holdout_only_and_never_reads_private_memory_or_cloud(self):
        self.client.force_login(self.alice)
        payload=dict(action='compare',baseline_model=MODELS[0],candidate_model=MODELS[1],suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        report=contract_comparison(suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        with patch('apps.ml_engine.api.memory.memory_store',side_effect=AssertionError('No private vault')),patch('apps.ml_engine.services.retrieval_quality.compare',return_value=report) as compared:
            response=self.client.post('/api/ai/memories/learning/',payload,content_type='application/json')
        self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control'])
        compared.assert_called_once_with(*MODELS,suite='held_out',candidate_protocol=RETRIEVAL_PROTOCOLS[1])
        self.assertEqual(response.json()['cases'],12); self.assertEqual(response.json()['suite'],'held_out')
        with patch('apps.ml_engine.services.retrieval_holdout.POLICY_SHA256','0'*64):
            response=self.client.post('/api/ai/memories/learning/',payload,content_type='application/json')
        self.assertEqual(response.status_code,400)
        self.assertNotIn('persistent_memory',response.content.decode())

    @override_settings(ALFRED_SYNTHETIC_QUALITY_ENABLED=True)
    def test_session_csrf_no_store_and_offline_failure(self):
        payload=dict(action='compare',baseline_model=MODELS[0],candidate_model=MODELS[1])
        self.assertIn(self.client.post('/api/ai/memories/learning/',payload,content_type='application/json').status_code,(401,403))
        csrf=APIClient(enforce_csrf_checks=True); csrf.force_login(self.alice)
        self.assertEqual(csrf.post('/api/ai/memories/learning/',payload,format='json').status_code,403)
        self.client.force_login(self.alice)
        with patch('apps.ml_engine.services.retrieval_quality.compare',return_value=contract_comparison()):
            response=self.client.post('/api/ai/memories/learning/',payload,content_type='application/json')
        self.assertEqual(response.status_code,200); self.assertIn('no-store',response['Cache-Control'])
        with patch('apps.ml_engine.services.retrieval_quality.compare',side_effect=EmbeddingUnavailable('SYNTHETIC-PRIVATE outage')):
            response=self.client.post('/api/ai/memories/learning/',payload,content_type='application/json')
        self.assertEqual(response.status_code,503); self.assertNotIn('SYNTHETIC-PRIVATE',response.content.decode())

    def test_comparison_deadline_stops_before_any_embedding(self):
        with patch('apps.ml_engine.services.retrieval_quality.time.monotonic',return_value=121):
            adapter=ContractEmbeddings()
            with patch.object(adapter,'embed') as embed, self.assertRaises(EmbeddingUnavailable):
                _BudgetedEmbeddings(adapter,120).embed('Not sent to model')
            embed.assert_not_called()
