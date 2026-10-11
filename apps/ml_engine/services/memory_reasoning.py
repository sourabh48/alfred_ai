"""Optional explicit public-context reasoning; no real OpenAI adapter is supplied."""
from datetime import datetime, timezone
import time

from .memory_sync import encoded, remaining, SyncUnavailable
from .persistent_memory import _owner


class ReasoningBudgetExceeded(RuntimeError):
    pass


class MockReasoner:
    def reason(self,payload,*,max_output_tokens,deadline):
        remaining(deadline)
        return 'Synthetic reasoning completed using approved public context.'


def reason_with_memory(store,user,query,*,consent=False,query_sensitivity=None,provider=None,daily_tokens=4096):
    owner=_owner(user)
    if consent is not True or query_sensitivity!='public':
        raise PermissionError('Confirm public query classification and explicit reasoning consent.')
    if not isinstance(query,str) or not query.strip() or len(query.encode())>1024:
        raise ValueError('Reasoning query exceeds the bounded slice.')
    if type(daily_tokens) is not int or not 1<=daily_tokens<=65536:
        raise ValueError('Reasoning budget must be bounded.')
    if provider is None: raise SyncUnavailable('No approved reasoning provider is configured.')
    memories=store.retrieve(user,query,cloud=True,cloud_consent=True)
    payload={'query':query,'memories':[item['content'] for item in memories]}
    # Reserve a conservative byte-token upper bound plus output/adapter overhead, including failed calls.
    reserve=len(encoded(payload))+512+256
    day=datetime.now(timezone.utc).date().isoformat()
    with store._transaction() as db:
        live={r[0] for r in db.execute('SELECT id FROM memory_keys WHERE owner=?',(owner,))}
        if any(item['id'] not in live for item in memories): raise PermissionError('Context was revoked before reasoning.')
        state=store._sync_state(db,owner)
        ledger=state.get('reasoning',{'day':day,'reserved':0})
        if ledger['day']!=day: ledger={'day':day,'reserved':0}
        if ledger['reserved']+reserve>daily_tokens: raise ReasoningBudgetExceeded('Daily reasoning budget exhausted.')
        ledger['reserved']+=reserve; state['reasoning']=ledger; store._write_sync_state(db,owner,state)
    try:
        answer=provider.reason(payload,max_output_tokens=512,deadline=time.monotonic()+5)
        if not isinstance(answer,str) or len(answer.encode())>8192: raise ValueError()
    except Exception:
        raise SyncUnavailable('Optional reasoning is unavailable; its reserved budget is retained.') from None
    return {'answer':answer,'provider':'mock','reserved_tokens':reserve,'remaining_tokens':daily_tokens-ledger['reserved']}
