"""Local proposals and explicit user verification; no canonical financial writes."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4

from cryptography.fernet import Fernet

from .persistent_memory import _owner, _json, SENSITIVITIES, MemoryConflict
from .memory_sync import valid_id


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
        records={r['id'] for r in self.store.list_memories(user)}
        if not isinstance(cases,list) or not 1<=len(cases)<=20: raise ValueError('Provide at most twenty evaluation cases.')
        for case in cases:
            if not isinstance(case,dict) or set(case)!= {'query','expected_id'} or not isinstance(case['query'],str) or not case['query'].strip() or len(case['query'].encode())>8192 or (case['expected_id'] is not None and (not valid_id(case['expected_id']) or case['expected_id'] not in records)):
                raise ValueError('Evaluation requires bounded queries and owned verified ground truth.')
        ranks=[]; false_positives=0; negative_cases=0
        for case in cases:
            results=self.store.retrieve(user,case['query'],limit=3,**({'min_score':min_score} if min_score is not None else {}))
            if case['expected_id'] is None:
                negative_cases+=1; false_positives+=bool(results)
            else:
                ranks.append(next((1/(i+1) for i,r in enumerate(results) if r['id']==case['expected_id']),0))
        # Immutable IDs make edits/deletions detectable without retaining private queries.
        if {r['id'] for r in self.store.list_memories(user)}!=records:
            raise MemoryConflict('Memory changed during evaluation.')
        return {'cases':len(cases),'positive_cases':len(ranks),'negative_cases':negative_cases,
            'recall_at_3':sum(bool(rank) for rank in ranks)/len(ranks) if ranks else None,
            'mean_reciprocal_rank':sum(ranks)/len(ranks) if ranks else None,
            'top_1_accuracy':sum(rank==1 for rank in ranks)/len(ranks) if ranks else None,
            'false_positive_rate':false_positives/negative_cases if negative_cases else None,
            'abstention_rate':1-false_positives/negative_cases if negative_cases else None,
            'ground_truth':'user_verified','generated_hypotheses_are_facts':False}
