"""Versioned fictional retrieval contracts; no private vaults, training or model activation."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from tempfile import TemporaryDirectory
import time
from types import SimpleNamespace

from .local_embeddings import EmbeddingUnavailable, OllamaEmbeddings
from .memory_learning import MemoryLearning
from .persistent_memory import MemoryConflict, MemoryStore, RETRIEVAL_PROTOCOLS


MODELS = ('all-minilm:latest', 'nomic-embed-text:latest')
SECONDS = 120
POLICY = {'version': 'synthetic-retrieval-v1', 'min_precision': .90, 'min_recall': .85,
    'min_abstention_rate': .95, 'min_citation_correctness': 1., 'max_metric_drop': .05,
    'max_owner_violations': 0, 'require_stale_rejection': True}
# Labels are source-reviewed fictional expectations, never inferred model truth.
COHORTS = (
    {'id': 'preferences-v1', 'records': {
        'trail': 'Fictional Mira prefers quiet alpine hiking trails over city visits.',
        'coast': 'Fictional Mira enjoys coastal vacations and beach walks.',
        'food': 'Fictional Mira prefers vegetarian meals when traveling.',
        'train': 'Fictional Mira chooses rail journeys over short flights.',
        'old': 'Fictional Mira prefers crowded city museums.',
        'deleted': 'Fictional Mira studies medieval manuscript restoration.',
        'foreign': 'Fictional Neve studies pulsars and neutron stars.'},
     'correction': ('old', 'Fictional Mira prefers quiet mountain walks and alpine hiking.'),
     'cases': (
        ('Which hiking scenery does Mira prefer?', ('trail', 'corrected')),
        ('Where does Mira enjoy beach walks?', ('coast',)),
        ('What dietary meals does Mira prefer?', ('food',)),
        ('Does Mira prefer rail journeys to short flights?', ('train',)),
        ('Which places does Mira choose for alpine hiking?', ('trail', 'corrected')),
        ('What vacations along the coast does Mira enjoy?', ('coast',)),
        ('How do neutron stars produce pulsars?', ()),
        ('How can medieval manuscripts be restored?', ()),
        ('How should a compiler optimize register allocation?', ()),
        ('What is the chemistry of lithium battery electrodes?', ()),
        ('What dosage treats fictional medical condition Z?', ()),
        ('What are the verified terms of an unknown loan?', ()))},
    {'id': 'corrections-conflicts-v1', 'records': {
        'coast': 'Fictional Rowan prefers coastal vacations and beach walks.',
        'contrary': 'Fictional Rowan avoids coastal vacations and beach walks.',
        'bike': 'Fictional Rowan records motorcycle maintenance each spring.',
        'camp': 'Fictional Rowan prefers tent camping to indoor accommodation.',
        'old': 'Fictional Rowan prefers traveling in summer.',
        'deleted': 'Fictional Rowan researches volcanic mineral spectroscopy.',
        'foreign': 'Fictional Ivo studies deep ocean microbial genomes.'},
     'correction': ('old', 'Fictional Rowan now prefers traveling in winter.'),
     'cases': (
        ('What statements describe Rowan and coastal beach vacations?', ('coast', 'contrary')),
        ('When does Rowan record motorcycle maintenance?', ('bike',)),
        ('Does Rowan prefer tent camping or indoor accommodation?', ('camp',)),
        ('Which travel season does Rowan prefer now?', ('corrected',)),
        ('What conflicting preferences concern coastal vacations?', ('coast', 'contrary')),
        ('What kind of overnight outdoor accommodation does Rowan prefer?', ('camp',)),
        ('What are deep ocean microbial genomes?', ()),
        ('Which minerals are identified by volcanic spectroscopy?', ()),
        ('How does a compiler optimize a recursive function?', ()),
        ('What is an unspecified bank account balance?', ()),
        ('Which medicine should a fictional patient take?', ()),
        ('What is the expansion rate of the universe?', ()))},
)
COHORT_ID = sha256(json.dumps(COHORTS, sort_keys=True).encode()).hexdigest()


def configuration():
    return dict(models=list(MODELS), policy=POLICY.copy(), cohort_id=COHORT_ID,
        cohorts=len(COHORTS), cases=sum(len(c['cases']) for c in COHORTS), seconds=SECONDS,
        scope='reviewed_fictional_sources_only', promotion_requires_approval=True)


class _BudgetedEmbeddings:
    def __init__(self, adapter, deadline):
        self.adapter, self.deadline, self.before_embed = adapter, deadline, None

    def embed(self, text, *, deadline=None):
        deadline = min(self.deadline, deadline) if deadline is not None else self.deadline
        if time.monotonic() >= deadline: raise EmbeddingUnavailable('Synthetic comparison deadline exceeded.')
        if self.before_embed:
            callback, self.before_embed = self.before_embed, None
            callback()
        result = self.adapter.embed(text, deadline=deadline)
        if time.monotonic() >= deadline: raise EmbeddingUnavailable('Synthetic comparison deadline exceeded.')
        return result


class _SyntheticCache:
    """Per-comparison fictional inputs only; no private or persistent embedding cache."""
    def __init__(self,adapter): self.adapter,self.cache=adapter,{}

    def embed(self,text,*,deadline=None):
        if text in self.cache:
            vector,model=self.cache[text]
            if model!=self.adapter.model+'@'+self.adapter._digest(deadline=deadline):
                raise EmbeddingUnavailable('Synthetic comparison model changed.')
        else:
            if len(self.cache)>=128: raise EmbeddingUnavailable('Synthetic comparison cache budget exceeded.')
            vector,model=self.adapter.embed(text,deadline=deadline)
            self.cache[text]=(tuple(vector),model)
        return list(vector),model


def _measure(adapter, deadline, *, protocol=RETRIEVAL_PROTOCOLS[0]):
    owner = SimpleNamespace(pk=1, created_at=datetime(2020, 1, 1, tzinfo=timezone.utc), is_authenticated=True)
    other = SimpleNamespace(pk=2, created_at=owner.created_at, is_authenticated=True)
    results = []
    for cohort in COHORTS:
        with TemporaryDirectory(prefix='alfred-quality-fictional-') as directory:
            embedder = _BudgetedEmbeddings(adapter, deadline)
            store = MemoryStore(directory, embedder=embedder,retrieval_protocol=protocol)
            learning = MemoryLearning(store)
            ids = {key: store.save_verified(other if key == 'foreign' else owner,
                {'statement': text}, {'source': cohort['id']}, verified=True)
                for key, text in cohort['records'].items()}
            old, correction = cohort['correction']
            ids['corrected'] = learning.revise(owner, [ids[old]], {'statement': correction}, verified=True)
            store.delete_memory(owner, ids['deleted'])
            cases = [dict(query=query, expected_ids=[ids[key] for key in expected]) for query, expected in cohort['cases']]
            report = learning.evaluate(owner, cases, min_score=.45)
            aliases={identity:key for key,identity in ids.items()}
            explanations=[]
            for case, (question, expected) in zip(report['per_case'],cohort['cases']):
                returned=[aliases[cite['id']] for cite in case['citations']]
                explanations.append(dict(
                    **{key:value for key,value in case.items() if key not in ('expected_ids','citations')},
                    fictional_question=question, expected_sources=list(expected), returned_sources=returned,
                    unexpected_sources=[key for key in returned if key not in expected],
                    missing_sources=[key for key in expected if key not in returned]))
            forbidden = {ids[old], ids['deleted'], ids['foreign']}
            violations = sum(cite['id'] in forbidden for case in report['per_case'] for cite in case['citations'])
            try:
                learning.evaluate(owner, [dict(query='Fictional owner probe', expected_ids=[ids['foreign']])])
            except ValueError:
                owner_rejected = True
            else:
                owner_rejected = False
            # Delete a live reviewed source during the real retrieval boundary.
            current = ids['corrected']
            embedder.before_embed = lambda: store.delete_memory(owner, current)
            try:
                learning.evaluate(owner, [dict(query=correction, expected_ids=[current])], min_score=.45)
            except MemoryConflict:
                stale_rejected = True
            else:
                stale_rejected = False
            results.append(dict(cohort=cohort['id'], cases=report['cases'], positive_cases=report['positive_cases'],
                negative_cases=report['negative_cases'], precision=report['precision'], recall=report['recall'],
                precision_at_k=report['precision_at_k'],recall_at_k=report['recall_at_k'],retrieval_errors=report['retrieval_errors'],
                abstention_rate=report['abstention_rate'], citation_correctness=report['citation_correctness'],
                owner_violations=violations, owner_reference_rejected=owner_rejected, stale_rejected=stale_rejected,
                context=report['retrieval_context'],
                per_case=explanations))
    if len({(r['context']['embedding_identity'],r['context']['dimensions']) for r in results}) != 1:
        raise EmbeddingUnavailable('Local embedding model changed between cohorts.')
    return dict(cohort_id=COHORT_ID, cutoff=.45, protocol=protocol, results=results)


def assess(baseline, candidate):
    """Objective development recommendation only; incomplete evidence cannot pass."""
    reasons, differences = [], []
    if (baseline.get('cohort_id') != COHORT_ID or candidate.get('cohort_id') != COHORT_ID
            or baseline.get('cutoff') != .45 or candidate.get('cutoff') != .45
            or len(baseline.get('results', [])) != len(COHORTS) or len(candidate.get('results', [])) != len(COHORTS)):
        return dict(decision='BLOCKED', reasons=['incomparable_or_incomplete_cohort'], differences=[])
    metrics = ('precision', 'recall', 'abstention_rate', 'citation_correctness')
    for contract, before, after in zip(COHORTS, baseline['results'], candidate['results']):
        if any(result.get('cohort') != contract['id'] or result.get('cases') != len(contract['cases'])
                or result.get('positive_cases') != 6 or result.get('negative_cases') != 6
                or len(result.get('per_case', [])) != len(contract['cases'])
                for result in (before, after)):
            return dict(decision='BLOCKED', reasons=['incomplete_case_coverage'], differences=[])
        for metric in metrics:
            values = (before.get(metric), after.get(metric))
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or not 0 <= v <= 1 for v in values):
                return dict(decision='BLOCKED', reasons=['missing_or_invalid_metric'], differences=[])
            delta = after[metric] - before[metric]
            differences.append(dict(cohort=contract['id'], metric=metric, baseline=before[metric], candidate=after[metric], delta=delta))
            if after[metric] < POLICY['min_' + metric]: reasons.append(contract['id'] + ':' + metric + '_floor')
            tolerance = 0 if metric == 'citation_correctness' else POLICY['max_metric_drop']
            if delta < -tolerance - 1e-12: reasons.append(contract['id'] + ':' + metric + '_regression')
        for label, result in (('baseline', before), ('candidate', after)):
            if type(result.get('owner_violations')) is not int or result['owner_violations'] != 0 or result.get('owner_reference_rejected') is not True or result.get('stale_rejected') is not True:
                reasons.append(label + ':' + contract['id'] + ':privacy_or_stale_guard')
    return dict(decision='REJECT' if reasons else 'ELIGIBLE_FOR_REVIEW', reasons=reasons, differences=differences)


def compare(baseline_model, candidate_model, *, adapters=None, baseline_protocol=RETRIEVAL_PROTOCOLS[0], candidate_protocol=RETRIEVAL_PROTOCOLS[0]):
    if baseline_model not in MODELS or candidate_model not in MODELS: raise ValueError('Choose an approved local embedding model.')
    if baseline_protocol not in RETRIEVAL_PROTOCOLS or candidate_protocol not in RETRIEVAL_PROTOCOLS: raise ValueError('Choose a supported retrieval protocol.')
    deadline = time.monotonic() + SECONDS
    local_adapters={}
    def adapter(model):
        if adapters is not None: return adapters[model]
        if model not in local_adapters:
            result = OllamaEmbeddings(); result.model = model
            local_adapters[model]=_SyntheticCache(result)
        return local_adapters[model]
    try:
        baseline = _measure(adapter(baseline_model), deadline,protocol=baseline_protocol)
        reused=candidate_model==baseline_model and candidate_protocol==baseline_protocol
        candidate = baseline if reused else _measure(adapter(candidate_model), deadline,protocol=candidate_protocol)
    except MemoryConflict:
        return dict(configuration(), decision='REJECT', reasons=['source_or_owner_revalidation_failed'],
            baseline=None, candidate=None, differences=[], runtime_changed=False)
    assessment=assess(baseline,candidate)
    if reused and assessment['decision']=='ELIGIBLE_FOR_REVIEW': assessment['decision']='REFERENCE_ONLY'
    return dict(configuration(), **assessment, baseline=baseline, candidate=candidate,
        candidate_execution='baseline_reference_reused' if reused else 'independent_protocol_run' if baseline_model==candidate_model else 'independent_model_run',
        baseline_protocol=baseline_protocol,candidate_protocol=candidate_protocol,
        baseline_model=baseline_model, candidate_model=candidate_model, runtime_changed=False)
