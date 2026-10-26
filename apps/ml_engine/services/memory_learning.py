"""Local proposals and explicit user verification; no canonical financial writes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
import time
from math import isfinite
from uuid import uuid4

from cryptography.fernet import Fernet

from .persistent_memory import _owner, _json, SENSITIVITIES, MemoryConflict
from .memory_sync import valid_id
from .local_embeddings import EmbeddingUnavailable

EVALUATION_SECONDS=60


class MemoryLearning:
    def __init__(self,store): self.store=store

    def candidates(self,user):
        owner=_owner(user)
        with self.store._transaction() as db:
            self.store._expire(db,owner)
            result=[]
            for identity,ciphertext in db.execute('SELECT id,record FROM memory_candidates WHERE owner=? ORDER BY id',(owner,)):
                record=json.loads(self.store._memory_cipher(db,identity,owner).decrypt(ciphertext))
                if record['owner']!=owner or record['id']!=identity: raise RuntimeError('Candidate ownership verification failed.')
                result.append({k:v for k,v in record.items() if k not in ('owner','fingerprint')})
        return result

    def extract(self,user,text,provenance,*,sensitivity='sensitive'):
        owner=_owner(user)
        if not isinstance(text,str) or not text.strip() or len(text.encode())>8192 or sensitivity not in SENSITIVITIES or not isinstance(provenance,dict) or not isinstance(provenance.get('source'),str) or not provenance['source'].strip():
            raise ValueError('Select bounded text, source and sensitivity for local review.')
        provenance=json.loads(_json(provenance)); statements=[line.strip() for line in text.splitlines() if line.strip()]
        if len(statements)>8: raise ValueError('Select at most eight statements at a time.')
        with self.store._transaction() as db:
            self.store._expire(db,owner)
            master=self.store._cipher(db); existing={}
            for identity,encrypted in db.execute('SELECT id,record FROM memory_candidates WHERE owner=?',(owner,)):
                record=json.loads(self.store._memory_cipher(db,identity,owner).decrypt(encrypted)); existing[record['fingerprint']]=identity
            result=[]
            for statement in statements:
                content={'statement':statement}; fingerprint=sha256(_json([content,provenance,sensitivity]).encode()).hexdigest()
                if fingerprint in existing:
                    result.append(existing[fingerprint]); continue
                if db.execute('SELECT COUNT(*) FROM memory_candidates WHERE owner=?',(owner,)).fetchone()[0]>=256:
                    raise ValueError('The local candidate review limit has been reached.')
                identity=uuid4().hex
                record=dict(id=identity,owner=owner,content=content,provenance=provenance,sensitivity=sensitivity,
                    confidence=0.5,classification='unverified_candidate',created_at=datetime.now(timezone.utc).isoformat(),fingerprint=fingerprint)
                key=Fernet.generate_key(); ciphertext=Fernet(key).encrypt(_json(record).encode())
                db.execute('INSERT INTO memory_keys VALUES(?,?,?)',(identity,owner,master.encrypt(key)))
                db.execute('INSERT INTO memory_candidates VALUES(?,?,?)',(identity,owner,ciphertext))
                self.store._learning_dirty(db,owner)
                existing[fingerprint]=identity; result.append(identity)
        return result

    def verify(self,user,identity,*,verified=False,content=None):
        if not valid_id(identity): raise ValueError('Choose an available candidate.')
        if verified is not True: raise PermissionError('Explicit candidate verification is required.')
        candidate=next((r for r in self.candidates(user) if r['id']==identity),None)
        if not candidate:
            previous=next((r for r in self.store.list_memories(user) if r['provenance'].get('candidate_id')==identity),None)
            if previous:
                if content is not None and _json(content)!=_json(previous['content']):
                    raise MemoryConflict('Candidate was already verified with different content.')
                return previous['id']
            raise ValueError('Candidate is no longer available.')
        provenance=candidate['provenance']|{'candidate_id':identity,'verification':'user_verified','extraction_confidence':candidate['confidence']}
        return self.store.save_verified(user,content if content is not None else candidate['content'],provenance,
            sensitivity=candidate['sensitivity'],verified=True,candidate_id=identity)

    def revise(self,user,identities,content,*,verified=False,reembed=False):
        if verified is not True or not isinstance(identities,list) or not 1<=len(identities)<=20 or any(not valid_id(i) for i in identities) or len(set(identities))!=len(identities):
            raise PermissionError('Explicit correction/consolidation verification is required.')
        records={r['id']:r for r in self.store.list_memories(user)}
        if any(identity not in records for identity in identities): raise MemoryConflict('Choose available owner memories.')
        selected=[records[i] for i in identities]
        if reembed and len(selected)!=1: raise ValueError('Re-embed one changed memory at a time.')
        sensitivity=max((r['sensitivity'] for r in selected),key=lambda value:['public','personal','sensitive'].index(value))
        provenance={'source':'owner verified correction/consolidation','source_refs':[r['provenance'] for r in selected],
            'supersedes':identities,'verification':'user_verified'}
        return self.store.save_verified(user,selected[0]['content'] if reembed else content,provenance,
            sensitivity=sensitivity,verified=True,supersedes=identities)

    def evaluate(self,user,cases,*,min_score=None):
        deadline=time.monotonic()+EVALUATION_SECONDS
        records={r['id']:r for r in self.store.list_memories(user)}
        if not isinstance(cases,list) or not 1<=len(cases)<=20: raise ValueError('Provide at most twenty evaluation cases.')
        if min_score is not None and (isinstance(min_score,bool) or not isinstance(min_score,(int,float)) or not isfinite(min_score) or not -1<=min_score<=1):
            raise ValueError('Choose a finite local relevance threshold.')
        expected_cases=[]; query_bytes=0
        for case in cases:
            if (not isinstance(case,dict) or set(case) not in ({'query','expected_id'},{'query','expected_ids'})
                    or not isinstance(case['query'],str) or not case['query'].strip()):
                raise ValueError('Evaluation requires bounded queries and owned verified ground truth.')
            identities=case.get('expected_ids') if 'expected_ids' in case else ([] if case['expected_id'] is None else [case['expected_id']])
            if (not isinstance(identities,list) or len(identities)>20
                    or any(not valid_id(identity) or identity not in records for identity in identities)
                    or len(set(identities))!=len(identities)):
                raise ValueError('Choose current owner-confirmed expected memories, or no expected match.')
            query_bytes+=len(case['query'].encode())
            if query_bytes>8192: raise ValueError('Evaluation questions must total at most 8192 bytes.')
            expected_cases.append(set(identities))
        profile=self.store.retrieval_profile(user)
        ranks=[]; false_positives=0; negative_cases=0; per_case=[]
        total_relevant=0; total_returned=0; total_expected=0
        for index,(case,expected) in enumerate(zip(cases,expected_cases),1):
            if time.monotonic()>=deadline: raise EmbeddingUnavailable('Local evaluation deadline exceeded.')
            results=self.store.retrieve(user,case['query'],limit=3,deadline=deadline,**({'min_score':min_score} if min_score is not None else {}))
            if time.monotonic()>=deadline: raise EmbeddingUnavailable('Local evaluation deadline exceeded.')
            if (not isinstance(results,list) or len(results)>3 or any(not isinstance(item,dict)
                    or not valid_id(item.get('id')) or item['id'] not in records
                    or isinstance(item.get('score'),bool) or not isinstance(item.get('score'),(int,float))
                    or not isfinite(item['score']) or abs(item['score'])>1.000001 for item in results)
                    or len({item['id'] for item in results})!=len(results)):
                raise MemoryConflict('Retrieval references are no longer valid for this owner.')
            scores=[item['score'] for item in results]
            if scores!=sorted(scores,reverse=True) or (min_score is not None and any(score<min_score for score in scores)):
                raise MemoryConflict('Retrieval no longer matches the reviewed ranking or cutoff.')
            for item in results:
                if any(key in item and item[key]!=records[item['id']][key] for key in ('content','provenance','sensitivity','verified_at')):
                    raise MemoryConflict('Retrieved memory changed during evaluation.')
            retrieved={item['id'] for item in results}; relevant=len(expected & retrieved)
            rank=next((1/(i+1) for i,item in enumerate(results) if item['id'] in expected),0)
            if not expected:
                negative_cases+=1; false_positives+=bool(results)
            else: ranks.append(rank)
            total_relevant+=relevant; total_returned+=len(results); total_expected+=len(expected)
            per_case.append(dict(case=index,expected_ids=sorted(expected),returned=len(results),matched=relevant,
                missed=len(expected-retrieved),irrelevant=len(retrieved-expected),abstained=not results,
                exact_match=expected==retrieved,precision=relevant/len(results) if results else None,
                recall=relevant/len(expected) if expected else None,reciprocal_rank=rank if expected else None,
                citations=[dict(id=item['id'],rank=i,score=item['score'],relevant=item['id'] in expected,
                    url=f"/settings/#memory-{item['id']}") for i,item in enumerate(results,1)]))
        # No partial report survives correction, deletion, expiry or owner-state changes.
        if (self.store.retrieval_profile(user)!=profile
                or {r['id']:r for r in self.store.list_memories(user)}!=records):
            raise MemoryConflict('Memory changed during evaluation.')
        if time.monotonic()>=deadline: raise EmbeddingUnavailable('Local evaluation deadline exceeded.')
        score_bands=[dict(lower=lower,upper=upper,returned=0,relevant=0)
            for lower,upper in ((-1,.5),(.5,.75),(.75,.9),(.9,1))]
        for case in per_case:
            for citation in case['citations']:
                band=next(band for band in score_bands if citation['score']<band['upper'] or band['upper']==1)
                band['returned']+=1; band['relevant']+=citation['relevant']
        for band in score_bands:
            band['observed_precision']=band['relevant']/band['returned'] if band['returned'] else None
        return {'cases':len(cases),'positive_cases':len(ranks),'negative_cases':negative_cases,
            'recall_at_3':sum(case['recall'] for case in per_case if case['recall'] is not None)/len(ranks) if ranks else None,
            'mean_reciprocal_rank':sum(ranks)/len(ranks) if ranks else None,
            'top_1_accuracy':sum(rank==1 for rank in ranks)/len(ranks) if ranks else None,
            'false_positive_rate':false_positives/negative_cases if negative_cases else None,
            'abstention_rate':1-false_positives/negative_cases if negative_cases else None,
            'precision':total_relevant/total_returned if total_returned else None,
            'recall':total_relevant/total_expected if total_expected else None,
            'exact_match_rate':sum(case['exact_match'] for case in per_case)/len(cases),
            'citation_correctness':1.0 if total_returned else None,'checked_citations':total_returned,
            'precision_at_k':{str(k):sum(sum(c['relevant'] for c in case['citations'][:k])/k for case in per_case if case['expected_ids'])/len(ranks) if ranks else None for k in (1,2,3)},
            'recall_at_k':{str(k):sum(sum(c['relevant'] for c in case['citations'][:k])/len(case['expected_ids']) for case in per_case if case['expected_ids'])/len(ranks) if ranks else None for k in (1,2,3)},
            'retrieval_errors':dict(unexpected_references=total_returned-total_relevant,missed_references=total_expected-total_relevant,
                false_abstentions=sum(bool(case['expected_ids']) and case['abstained'] for case in per_case),false_matches=false_positives),
            'ranking_metric_scope':'positive_cases_only_fixed_k_denominator; negative_cases_measured_by_abstention',
            'min_score':min_score,'result_limit':3,'per_case':per_case,
            'score_diagnostics':dict(bands=score_bands,scope='reviewed_cases_in_this_run_only',
                score_is_probability=False,automatic_threshold_change=False),
            'processing_budget_seconds':EVALUATION_SECONDS,
            'retrieval_context':dict(protocol=self.store.retrieval_protocol,**profile,
                comparison='same_model_cutoff_reviewed_cases_and_source_revisions_required',cohort_persistence='none'),
            'privacy':'owner_only_local','source_check':'unchanged_owner_snapshot',
            'ground_truth':'user_verified','generated_hypotheses_are_facts':False}
