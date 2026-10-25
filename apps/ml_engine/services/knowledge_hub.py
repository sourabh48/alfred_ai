"""Owner-reviewed data packs; never code, training input or canonical financial facts."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
import time
from uuid import uuid4

from cryptography.fernet import Fernet

from .persistent_memory import _owner, MemoryConflict
from .memory_reasoning import public_payload
from .memory_sync import MemorySynchronizer, SyncConflict, SyncUnavailable, encoded, valid_id, remaining

MAX_PACKS = 32
MAX_BUNDLE = 256 * 1024


def fingerprint(record):
    return sha256(encoded({key: record[key] for key in ('id', 'content', 'provenance', 'sensitivity', 'verified_at')})).hexdigest()


def screen(entries):
    # IDs/digests have a separate strict grammar; screen the actual human-supplied text.
    narrative = [{'statement': item['statement'], 'source': item['source']} for item in entries]
    public_payload(narrative)
    text = encoded(narrative).decode()
    if re.search(r'(?i)(ignore.{0,30}(?:instruction|previous)|system\s*(?:prompt|:)|developer\s*:|<\|[^>]+\|>|(?:execute|run)\s+(?:code|command|shell)|(?:change|update|modify)\s+(?:model|code)|tool_call|javascript:|<script)', text):
        raise PermissionError('Instruction-like material cannot be promoted as knowledge.')


class KnowledgeHub:
    def __init__(self, store, *, deadline=None):
        self.store = store
        self.deadline = deadline

    def _transaction(self):
        return self.store._transaction(timeout=remaining(self.deadline) if self.deadline else 10)

    def _state(self, db, owner):
        state = self.store._sync_state(db, owner)
        return state, state.setdefault('knowledge_hub', {'enabled': False, 'remote_consent': False})

    def _write(self, db, owner, record, *, new=False):
        key = Fernet.generate_key()
        wrapped = self.store._cipher(db).encrypt(key)
        body = Fernet(key).encrypt(encoded(record))
        if new:
            db.execute('INSERT INTO knowledge_packs VALUES(?,?,?,?)', (record['id'], owner, wrapped, body))
        else:
            db.execute('UPDATE knowledge_packs SET wrapped=?,record=? WHERE id=? AND owner=?', (wrapped, body, record['id'], owner))

    def _validate(self, owner, record):
        try:
            if (not isinstance(record, dict) or set(record) != {'id', 'owner', 'schema', 'lineage', 'parent', 'version', 'created_at', 'expires_at', 'entries', 'digest', 'state', 'origin'}
                    or record['owner'] != owner or record['schema'] != 1 or type(record['schema']) is not int
                    or not valid_id(record['id']) or not valid_id(record['lineage'])
                    or (record['parent'] is not None and not valid_id(record['parent'], 64))
                    or type(record['version']) is not int or not 1 <= record['version'] <= 4096
                    or (record['version'] == 1) != (record['parent'] is None)
                    or record['state'] not in ('draft', 'promoted', 'withdrawn') or record['origin'] not in ('local', 'remote')
                    or not isinstance(record['entries'], list) or not 1 <= len(record['entries']) <= 8
                    or len(encoded(record)) > 16384):
                raise ValueError()
            created = datetime.fromisoformat(record['created_at'])
            expires = datetime.fromisoformat(record['expires_at'])
            if created.utcoffset() is None or expires.utcoffset() is None or created > datetime.now(timezone.utc) + timedelta(minutes=5) or expires <= created or expires > created + timedelta(days=365):
                raise ValueError()
            identities = set()
            for item in record['entries']:
                if (not isinstance(item, dict) or set(item) != {'id', 'statement', 'source', 'citation', 'fingerprint'}
                        or not valid_id(item['id']) or item['id'] in identities or not valid_id(item['fingerprint'], 64)
                        or item['citation'] != '/settings/#memory-' + item['id']
                        or not all(isinstance(item[k], str) and item[k].strip() for k in ('statement', 'source'))):
                    raise ValueError()
                identities.add(item['id'])
            screen(record['entries'])
            payload = {k: v for k, v in record.items() if k not in ('digest', 'state', 'origin')}
            if record['digest'] != sha256(encoded(payload)).hexdigest():
                raise ValueError()
            return record
        except (ValueError, KeyError, TypeError, OverflowError, PermissionError):
            raise MemoryConflict('Knowledge pack validation failed; existing data is preserved.') from None

    def _records(self, db, owner):
        records = []
        for identity, wrapped, body in db.execute('SELECT id,wrapped,record FROM knowledge_packs WHERE owner=? ORDER BY id', (owner,)):
            record = json.loads(Fernet(self.store._cipher(db).decrypt(wrapped)).decrypt(body))
            self._validate(owner, record)
            if record['id'] != identity:
                raise MemoryConflict('Knowledge pack ownership verification failed.')
            records.append(record)
        if len(records) > MAX_PACKS:
            raise MemoryConflict('Knowledge pack count exceeds the local budget.')
        return records

    def _sources(self, db, owner):
        self.store._expire(db, owner)
        return {identity: self.store._decode(db, identity, owner, body) for identity, body in
                db.execute('SELECT id,record FROM memories WHERE owner=?', (owner,))}

    def _status(self, record, sources):
        if datetime.fromisoformat(record['expires_at']) <= datetime.now(timezone.utc):
            return 'STALE'
        if record['origin'] == 'remote':
            return 'WITHDRAWN' if record['state'] == 'withdrawn' else 'REMOTE_REVIEW_REQUIRED'
        if any(item['id'] not in sources or fingerprint(sources[item['id']]) != item['fingerprint'] for item in record['entries']):
            return 'SOURCE_CHANGED'
        return record['state'].upper()

    def _prune(self, db, owner):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.store._retention(db, owner))
        for record in self._records(db, owner):
            if datetime.fromisoformat(record['created_at']) <= cutoff:
                db.execute('DELETE FROM knowledge_packs WHERE id=? AND owner=?', (record['id'], owner))
                self.store._learning_dirty(db, owner)

    def snapshot(self, user):
        owner = _owner(user)
        with self._transaction() as db:
            self._prune(db, owner)
            sources = self._sources(db, owner)
            state, policy = self._state(db, owner)
            records = self._records(db, owner)
            return {'enabled': policy['enabled'], 'remote_consent': policy['remote_consent'],
                    'revision': state.get('learning_revision', 0), 'checkpoint': policy.get('checkpoint', 0),
                    'pending': policy.get('pending', False), 'failures': policy.get('failures', 0),
                    'conflict': policy.get('conflict', False), 'last_success_at': policy.get('last_success_at'),
                    'review_head': policy.get('review_head'), 'review_digest': policy.get('review_digest'),
                    'packs': [dict(record, status=self._status(record, sources)) for record in records],
                    'sources': [{'id': r['id'], 'source': r['provenance']['source'], 'statement': r['content']['statement']}
                                for r in sources.values() if r['sensitivity'] == 'public' and set(r['content']) == {'statement'} and isinstance(r['content']['statement'], str)],
                    'authority': 'owner_reviewed_supplementary_data_only', 'automatic_training': False}

    def configure(self, user, *, enabled, consent=False):
        if type(enabled) is not bool or (enabled and consent is not True):
            raise PermissionError('Explicit local knowledge-pack review consent is required.')
        owner = _owner(user)
        with self._transaction() as db:
            state, policy = self._state(db, owner)
            policy['enabled'] = enabled
            if not enabled:
                policy['remote_consent'] = False
            self.store._write_sync_state(db, owner, state)

    def draft(self, user, identities, *, parent=None):
        owner = _owner(user)
        if not isinstance(identities, list) or not 1 <= len(identities) <= 8 or any(not valid_id(i) for i in identities) or len(set(identities)) != len(identities):
            raise ValueError('Select one to eight current public memories.')
        with self._transaction() as db:
            self._prune(db, owner)
            state, policy = self._state(db, owner)
            if not policy['enabled']:
                raise PermissionError('Enable local knowledge-pack review first.')
            sources = self._sources(db, owner)
            records = self._records(db, owner)
            previous = next((r for r in records if r['id'] == parent and r['origin'] == 'local' and r['state'] == 'promoted'), None)
            if parent is not None and previous is None:
                raise MemoryConflict('Choose a current promoted parent pack.')
            entries = []
            for identity in identities:
                source = sources.get(identity)
                if source is None or source['sensitivity'] != 'public' or set(source['content']) != {'statement'} or not isinstance(source['content']['statement'], str):
                    raise MemoryConflict('Selected public memory is unavailable or changed.')
                entries.append(dict(id=identity, statement=source['content']['statement'], source=source['provenance']['source'],
                                    citation='/settings/#memory-' + identity, fingerprint=fingerprint(source)))
            screen(entries)
            for record in records:
                if record['state'] == 'draft' and record['origin'] == 'local' and record['entries'] == entries and record['parent'] == (previous['digest'] if previous else None):
                    return record['id']
            if len(records) >= MAX_PACKS:
                raise ValueError('The local knowledge-pack limit has been reached.')
            now = datetime.now(timezone.utc)
            expiry = min(datetime.fromisoformat(sources[i]['verified_at']) + timedelta(days=self.store._retention(db, owner)) for i in identities)
            identity = uuid4().hex
            record = dict(id=identity, owner=owner, schema=1, lineage=previous['lineage'] if previous else identity,
                          parent=previous['digest'] if previous else None, version=previous['version'] + 1 if previous else 1,
                          created_at=now.isoformat(), expires_at=expiry.isoformat(), entries=entries)
            record.update(digest=sha256(encoded(record)).hexdigest(), state='draft', origin='local')
            self._validate(owner, record)
            self._write(db, owner, record, new=True)
            self.store._learning_dirty(db, owner)
            return identity

    def review(self, user, identity, digest, *, promote=False, reviewed=False):
        if not valid_id(identity) or not valid_id(digest, 64) or type(promote) is not bool or reviewed is not True:
            raise PermissionError('Review the exact pack and explicitly confirm your decision.')
        owner = _owner(user)
        with self._transaction() as db:
            state, policy = self._state(db, owner)
            records = self._records(db, owner)
            record = next((r for r in records if r['id'] == identity and r['digest'] == digest), None)
            if record is None or record['origin'] != 'local':
                raise MemoryConflict('Pack changed or belongs to a different owner.')
            if promote:
                if not policy['enabled'] or self._status(record, self._sources(db, owner)) not in ('DRAFT', 'PROMOTED'):
                    raise MemoryConflict('Review current sources before promotion.')
                heads = [r for r in records if r['lineage'] == record['lineage'] and r['state'] == 'promoted' and r['id'] != identity]
                if (record['version'] == 1 and heads) or (record['version'] > 1 and (len(heads) != 1 or heads[0]['digest'] != record['parent'])):
                    raise MemoryConflict('Another pack version was promoted; both drafts are preserved.')
                for head in heads:
                    head['state'] = 'withdrawn'
                    self._write(db, owner, head)
            record['state'] = 'promoted' if promote else 'withdrawn'
            self._write(db, owner, record)
            policy['pending'] = True
            self.store._write_sync_state(db, owner, state)
            self.store._learning_dirty(db, owner)

    def checkpoint(self, user):
        """Acknowledge validated local state only; never contacts a provider."""
        owner = _owner(user)
        with self._transaction() as db:
            self._prune(db, owner)
            self._sources(db, owner)
            state, policy = self._state(db, owner)
            policy['checkpoint'] = state.get('learning_revision', 0)
            self.store._write_sync_state(db, owner, state)
        return policy['checkpoint']

    def resolve_conflict(self, user, head, digest, *, reviewed=False):
        if reviewed is not True or not valid_id(head, 40) or not valid_id(digest, 64):
            raise PermissionError('Review the exact cached remote checkpoint before reconciling.')
        owner = _owner(user)
        with self._transaction() as db:
            state, policy = self._state(db, owner)
            if not policy['enabled'] or not policy['remote_consent'] or policy.get('review_head') != head or policy.get('review_digest') != digest:
                raise MemoryConflict('Remote review checkpoint changed; local versions are retained.')
            policy.update(head=head, pending=True, retry_at=0, conflict=False)
            policy.pop('review_head', None)
            policy.pop('review_digest', None)
            self.store._write_sync_state(db, owner, state)

    def sync(self, user, provider, *, seconds=5):
        """Only explicitly opted-in reviewed packs cross the separate Git boundary."""
        if type(seconds) not in (int, float) or not 0 < seconds <= 5:
            raise ValueError('Choose a bounded knowledge synchronization deadline.')
        deadline = time.monotonic() + seconds
        if self.deadline:
            deadline = min(deadline, self.deadline)
        self.deadline = deadline
        owner = _owner(user)
        with self._transaction() as db:
            state, policy = self._state(db, owner)
            if not policy['enabled'] or not policy['remote_consent']:
                return 'disabled'
            if policy.get('retry_at', 0) > time.time():
                return 'queued'
            revision = state.get('learning_revision', 0)
            epoch_row = db.execute('SELECT epoch FROM owner_epochs WHERE owner=?', (owner,)).fetchone()
            epoch = epoch_row[0] if epoch_row else 0
        try:
            current = self.snapshot(user)
            local = [dict(r, state='withdrawn' if r['status'] in ('SOURCE_CHANGED', 'STALE') else r['state'])
                     for r in current['packs'] if r['origin'] == 'local' and r['state'] in ('promoted', 'withdrawn')]
            local = [{k: v for k, v in r.items() if k != 'status'} for r in local]
            cipher = MemorySynchronizer(self.store, None)._key(owner)
            remote = provider.read(owner, deadline=deadline)
            remote_records = []
            if remote:
                payload = json.loads(cipher.decrypt(remote['body']))
                if not isinstance(payload, dict) or set(payload) != {'schema', 'owner', 'epoch', 'packs'} or payload['schema'] != 1 or type(payload['schema']) is not int or payload['owner'] != owner or type(payload['epoch']) is not int or payload['epoch'] < 0 or not isinstance(payload['packs'], list) or len(payload['packs']) > MAX_PACKS:
                    raise SyncUnavailable('Remote knowledge bundle is invalid.')
                if payload['epoch'] != epoch:
                    raise SyncConflict('Account reset generation differs; old remote knowledge cannot be restored automatically.')
                remote_records = [self._validate(owner, row) for row in payload['packs']]
                if any(r['state'] == 'draft' for r in remote_records):
                    raise SyncUnavailable('Unreviewed remote drafts are refused.')
                if len({r['id'] for r in remote_records}) != len(remote_records):
                    raise SyncConflict('Duplicate remote pack identities are refused.')
            needs_review = False
            with self._transaction() as db:
                state, policy = self._state(db, owner)
                if policy.get('head') and (not remote or policy['head'] not in remote['history']):
                    raise SyncConflict('Remote history does not extend the trusted checkpoint.')
                needs_review = bool(remote and policy.get('head') not in (None, remote['head']) and policy.get('pending'))
                cached = self._records(db, owner)
                by_id = {r['id']: r for r in cached}
                for record in remote_records:
                    if record['id'] in by_id and record['digest'] != by_id[record['id']]['digest']:
                        raise SyncConflict('Conflicting pack identities are preserved without replacement.')
                    if record['id'] not in by_id:
                        if len(by_id) >= MAX_PACKS:
                            raise SyncUnavailable('Remote packs exceed the local review budget.')
                        record = dict(record, origin='remote')
                        self._write(db, owner, record, new=True)
                        by_id[record['id']] = record
                    elif by_id[record['id']]['origin'] == 'remote':
                        self._write(db, owner, dict(record, origin='remote'))
                if needs_review:
                    policy.update(review_head=remote['head'], review_digest=sha256(remote['body']).hexdigest())
                self.store._write_sync_state(db, owner, state)
            if needs_review:
                raise SyncConflict('Remote knowledge changed; review cached versions before reconciling.')
            # Remote data is cached for review, never installed in verified memory or models.
            merged = {r['id']: r for r in remote_records if datetime.fromisoformat(r['expires_at']) > datetime.now(timezone.utc)}
            for record in local:
                merged[record['id']] = record
            if len(merged) > MAX_PACKS:
                raise SyncUnavailable('Knowledge bundle exceeds the review budget.')
            payload = encoded(dict(schema=1, owner=owner, epoch=epoch, packs=list(sorted(merged.values(), key=lambda r: r['id']))))
            if len(payload) > MAX_BUNDLE - 1024:
                raise SyncUnavailable('Knowledge bundle exceeds its processing budget.')
            content_hash = sha256(payload).hexdigest()
            with self._transaction() as db:
                latest, policy = self._state(db, owner)
                if not policy['enabled'] or not policy['remote_consent'] or latest.get('learning_revision', 0) != revision:
                    raise SyncConflict('Local knowledge or consent changed during synchronization.')
                # Serialize consent withdrawal/corrections with the bounded publish and acknowledgement.
                head = remote['head'] if remote else None
                if not remote or payload != encoded(json.loads(cipher.decrypt(remote['body']))):
                    head = provider.publish(owner, head, cipher.encrypt(payload), deadline=deadline)
                policy.update(head=head, pending=False,
                              failures=0, retry_at=0, conflict=False, digest=content_hash,
                              last_success_at=datetime.now(timezone.utc).isoformat())
                self.store._write_sync_state(db, owner, latest)
            return 'synchronized'
        except Exception as exc:
            # Persist retry metadata even when the shared network deadline has expired.
            with self.store._transaction(timeout=0.1) as db:
                state, policy = self._state(db, owner)
                failures = min(policy.get('failures', 0) + 1, 16)
                policy.update(pending=True, failures=failures, retry_at=time.time() + min(300, 2 ** failures), conflict=isinstance(exc, SyncConflict))
                self.store._write_sync_state(db, owner, state)
            if isinstance(exc, SyncConflict):
                raise
            raise SyncUnavailable('Knowledge sync is unavailable; encrypted local state remains queued.') from None
