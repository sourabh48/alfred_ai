"""Verified owner-scoped local memories and an encrypted append-only restore journal."""
from contextlib import contextmanager, closing
from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from math import hypot, isfinite
import os
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

from .local_embeddings import OllamaEmbeddings, validate_vector, EmbeddingUnavailable
from .memory_key import private_directory, protect_key, MemoryStorageUnavailable


SENSITIVITIES = {'public', 'personal', 'sensitive'}


class MemoryConflict(ValueError):
    """A reviewed memory changed before the operation could finish."""


def _json(value):
    try:
        encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(encoded.encode('utf-8')) > 8192:
            raise ValueError()
        return encoded
    except (ValueError, TypeError):
        raise ValueError('Memory/provenance must be bounded valid JSON.') from None


def _owner(user):
    if not getattr(user, 'is_authenticated', False) or not isinstance(getattr(user, 'pk', None), int) or user.pk < 1 or not getattr(user, 'created_at', None):
        raise PermissionError('An authenticated persisted owner is required.')
    timestamp = user.created_at.astimezone(timezone.utc).isoformat()
    return sha256(f'{user.pk}:{timestamp}'.encode()).hexdigest()


class MemoryStore:
    def __init__(self, directory, *, embedder=None, timeout=10):
        if not Path(directory).is_absolute():
            raise ValueError('Memory storage requires an absolute persistent directory.')
        deadline=time.monotonic()+timeout
        private_directory(Path(directory).absolute(), deadline=deadline)
        self.directory = Path(directory).resolve()
        self.database = self.directory / 'verified.sqlite3'
        self.key_file = self.directory / 'journal.key'
        self.embedder = embedder if embedder is not None else OllamaEmbeddings()
        if self.database.exists():
            with closing(sqlite3.connect(self.database.as_uri() + '?mode=ro', uri=True, timeout=max(0.001,deadline-time.monotonic()))) as old:
                previous = old.execute("SELECT sql FROM sqlite_master WHERE name='memories'").fetchone()
                if previous and 'record TEXT' in previous[0]:
                    raise MemoryStorageUnavailable('Legacy plaintext memory vault is preserved; use a new protected vault.')
        with self._transaction(timeout=max(0.001,deadline-time.monotonic())) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, record BLOB NOT NULL);
                CREATE INDEX IF NOT EXISTS memories_owner ON memories(owner);
                CREATE TABLE IF NOT EXISTS memory_keys (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, wrapped BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS policies (owner TEXT PRIMARY KEY, encrypted BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS owner_epochs (owner TEXT PRIMARY KEY, epoch INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS memory_sync (owner TEXT PRIMARY KEY, encrypted BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS memory_candidates (id TEXT PRIMARY KEY, owner TEXT NOT NULL, record BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                    owner TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'save', ciphertext BLOB NOT NULL);
                CREATE INDEX IF NOT EXISTS events_owner ON events(owner, sequence);
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT, 'Journal events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT, 'Journal events are append-only'); END;
            ''')

    @contextmanager
    def _transaction(self, timeout=10):
        db = sqlite3.connect(self.database, timeout=timeout)
        try:
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA secure_delete=ON')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _cipher(self, db):
        if not self.key_file.exists():
            if any(db.execute('SELECT EXISTS(SELECT 1 FROM '+table+')').fetchone()[0]
                   for table in ('events', 'memory_keys', 'policies', 'memory_sync')):
                raise RuntimeError('Memory recovery key is missing; restore its protected backup.')
            protected = b'M15DPAPI1\0' + protect_key(Fernet.generate_key())
            descriptor = os.open(self.key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(protected)
                stream.flush()
                os.fsync(stream.fileno())
        try:
            blob = self.key_file.read_bytes()
            if not blob.startswith(b'M15DPAPI1\0'):
                raise ValueError()
            return Fernet(protect_key(blob[10:], decrypt=True))
        except (ValueError, OSError, MemoryStorageUnavailable):
            raise RuntimeError('Memory recovery key is unavailable; keep its protected backup.') from None

    def _memory_cipher(self, db, identity, owner):
        row = db.execute('SELECT wrapped FROM memory_keys WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if not row:
            raise RuntimeError('Memory access has been revoked.')
        try:
            return Fernet(self._cipher(db).decrypt(row[0]))
        except (InvalidToken, ValueError):
            raise RuntimeError('Memory encryption verification failed.') from None

    def _decode(self, db, identity, owner, ciphertext):
        try:
            record = json.loads(self._memory_cipher(db, identity, owner).decrypt(ciphertext))
            if record['id'] != identity or record['owner'] != owner or record['verified'] is not True or record['sensitivity'] not in SENSITIVITIES:
                raise ValueError()
            validate_vector(record['embedding'])
            _json(record['content'])
            _json(record['provenance'])
            datetime.fromisoformat(record['verified_at']).astimezone(timezone.utc)
            return record
        except (InvalidToken, ValueError, KeyError, TypeError, EmbeddingUnavailable):
            raise RuntimeError('Memory journal verification failed; existing memories are preserved.') from None

    def _retention(self, db, owner):
        row = db.execute('SELECT encrypted FROM policies WHERE owner=?', (owner,)).fetchone()
        return json.loads(self._cipher(db).decrypt(row[0]))['days'] if row else 30

    def _sync_state(self, db, owner):
        row = db.execute('SELECT encrypted FROM memory_sync WHERE owner=?', (owner,)).fetchone()
        state = json.loads(self._cipher(db).decrypt(row[0])) if row else {'owner': owner, 'enabled': False,
            'revision': 0, 'identity': None, 'ack': None, 'pending': False, 'failures': 0, 'retry_at': 0, 'conflict': False}
        if state['owner'] != owner:
            raise RuntimeError('Memory synchronization ownership verification failed.')
        return state

    def _write_sync_state(self, db, owner, state):
        encrypted = self._cipher(db).encrypt(_json(state).encode())
        db.execute('INSERT INTO memory_sync VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET encrypted=excluded.encrypted', (owner, encrypted))

    def _sync_dirty(self, db, owner):
        if db.execute('SELECT 1 FROM memory_sync WHERE owner=?', (owner,)).fetchone():
            state = self._sync_state(db, owner)
            state['pending'] = True
            self._write_sync_state(db, owner, state)

    def _revoke(self, db, owner, identities, *, kind='delete'):
        if not identities:
            return 0
        published=[identity for identity in identities if db.execute('SELECT 1 FROM events WHERE id=? AND owner=? AND kind="save"',(identity,owner)).fetchone()]
        if published:
            event = self._cipher(db).encrypt(json.dumps({'kind': kind, 'ids': published}).encode())
            db.execute('INSERT INTO events(id,owner,kind,ciphertext) VALUES(?,?,?,?)', (uuid4().hex, owner, kind, event))
        for identity in identities:
            db.execute('DELETE FROM memories WHERE id=? AND owner=?', (identity, owner))
            db.execute('DELETE FROM memory_keys WHERE id=? AND owner=?', (identity, owner))
            db.execute('DELETE FROM memory_candidates WHERE id=? AND owner=?', (identity, owner))
        if published: self._sync_dirty(db, owner)
        return len(identities)

    def _expire(self, db, owner):
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention(db, owner))
        expired = []
        for identity, ciphertext in db.execute('SELECT events.id,events.ciphertext FROM events JOIN memory_keys USING(id,owner) WHERE owner=? AND kind="save"', (owner,)):
            record = self._decode(db, identity, owner, ciphertext)
            if datetime.fromisoformat(record['verified_at']) <= cutoff:
                expired.append(identity)
        for identity, ciphertext in db.execute('SELECT id,record FROM memory_candidates WHERE owner=?', (owner,)):
            candidate=json.loads(self._memory_cipher(db,identity,owner).decrypt(ciphertext))
            if candidate['owner']!=owner or candidate['id']!=identity: raise RuntimeError('Candidate ownership verification failed.')
            if datetime.fromisoformat(candidate['created_at'])<=cutoff: expired.append(identity)
        return self._revoke(db, owner, expired, kind='expire')

    def list_memories(self, user):
        owner = _owner(user)
        with self._transaction() as db:
            self._expire(db, owner)
            records = [self._decode(db, identity, owner, ciphertext) for identity, ciphertext in
                db.execute('SELECT id,record FROM memories WHERE owner=? ORDER BY id', (owner,))]
        return [dict(id=r['id'], content=r['content'], provenance=r['provenance'], sensitivity=r['sensitivity'], verified_at=r['verified_at']) for r in records]

    def retention_days(self, user):
        with self._transaction() as db:
            return self._retention(db, _owner(user))

    def set_retention(self, user, days):
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 365:
            raise ValueError('Memory retention must be between 1 and 365 days.')
        owner = _owner(user)
        with self._transaction() as db:
            encrypted = self._cipher(db).encrypt(json.dumps({'days': days}).encode())
            db.execute('INSERT INTO policies(owner,encrypted) VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET encrypted=excluded.encrypted', (owner, encrypted))
            self._sync_dirty(db, owner)
            return self._expire(db, owner)

    def delete_memory(self, user, identity):
        owner = _owner(user)
        with self._transaction() as db:
            exists = db.execute('SELECT 1 FROM memory_keys WHERE id=? AND owner=?', (identity, owner)).fetchone()
            return self._revoke(db, owner, [identity]) if exists else 0

    def reset_owner(self, user):
        owner = _owner(user)
        with self._transaction() as db:
            db.execute('INSERT INTO owner_epochs(owner,epoch) VALUES(?,1) ON CONFLICT(owner) DO UPDATE SET epoch=epoch+1', (owner,))
            self._sync_dirty(db, owner)
            identities = [r[0] for r in db.execute('SELECT id FROM memory_keys WHERE owner=?', (owner,))]
            return self._revoke(db, owner, identities, kind='reset')

    def expire_all(self):
        with self._transaction() as db:
            owners = [r[0] for r in db.execute('SELECT DISTINCT owner FROM memory_keys ORDER BY owner')]
            return sum(self._expire(db, owner) for owner in owners)

    def save_verified(self, user, content, provenance, *, sensitivity='sensitive', verified=False, supersedes=(), candidate_id=None):
        owner = _owner(user)
        if verified is not True or not isinstance(content, dict) or not content or not isinstance(provenance, dict) or not isinstance(provenance.get('source'), str) or not provenance['source'].strip() or sensitivity not in SENSITIVITIES:
            raise ValueError('Confirm a structured memory, its source and sensitivity before saving.')
        text = _json(content)
        content = json.loads(text)
        provenance = json.loads(_json(provenance))
        if not isinstance(supersedes,(list,tuple)) or len(supersedes)>20 or any(not isinstance(i,str) for i in supersedes) or len(set(supersedes))!=len(supersedes):
            raise ValueError('Choose at most twenty distinct owned memories to replace.')
        with self._transaction() as db:
            row = db.execute('SELECT epoch FROM owner_epochs WHERE owner=?', (owner,)).fetchone()
            epoch = row[0] if row else 0
        vector, model = self.embedder.embed(text)
        validate_vector(vector)
        if not isinstance(model, str) or not 1 <= len(model) <= 256:
            raise EmbeddingUnavailable('Local embedding model identity is invalid.')
        record = dict(id=uuid4().hex, owner=owner, content=content, provenance=provenance,
            sensitivity=sensitivity, verified=True, verified_at=datetime.now(timezone.utc).isoformat(),
            embedding=vector, embedding_model=model)
        encoded = json.dumps(record, sort_keys=True, allow_nan=False).encode()
        with self._transaction() as db:
            row = db.execute('SELECT epoch FROM owner_epochs WHERE owner=?', (owner,)).fetchone()
            if (row[0] if row else 0) != epoch:
                raise ValueError('Memory verification must be repeated after an account reset.')
            self._expire(db, owner)
            for identity in supersedes:
                if not db.execute('SELECT 1 FROM memories WHERE id=? AND owner=?',(identity,owner)).fetchone():
                    raise MemoryConflict('A replaced memory is no longer available.')
            if candidate_id and not db.execute('SELECT 1 FROM memory_candidates WHERE id=? AND owner=?',(candidate_id,owner)).fetchone():
                raise MemoryConflict('Candidate verification is no longer available.')
            if not supersedes and not candidate_id:
                for identity,ciphertext in db.execute('SELECT id,record FROM memories WHERE owner=? ORDER BY id',(owner,)):
                    existing=self._decode(db,identity,owner,ciphertext)
                    if _json(existing['content'])==_json(content) and _json(existing['provenance'])==_json(provenance) and existing['sensitivity']==sensitivity:
                        return identity
            if db.execute('SELECT COUNT(*) FROM memories WHERE owner=?', (owner,)).fetchone()[0]-len(supersedes) >= 512:
                raise ValueError('The local memory slice supports at most 512 verified memories per owner.')
            # shortcut: bound retained encrypted history; add tested journal compaction before raising this cap.
            if db.execute('SELECT COUNT(*) FROM events WHERE owner=?', (owner,)).fetchone()[0]+1+bool(supersedes) > 4096:
                raise ValueError('The local encrypted memory history limit has been reached.')
            key = Fernet.generate_key()
            ciphertext = Fernet(key).encrypt(encoded)
            db.execute('INSERT INTO memory_keys(id,owner,wrapped) VALUES(?,?,?)', (record['id'], owner, self._cipher(db).encrypt(key)))
            db.execute('INSERT INTO events(id,owner,ciphertext) VALUES(?,?,?)', (record['id'], owner, ciphertext))
            db.execute('INSERT INTO memories(id,owner,record) VALUES(?,?,?)', (record['id'], owner, ciphertext))
            self._revoke(db,owner,[*supersedes,*([candidate_id] if candidate_id else [])])
            self._sync_dirty(db, owner)
        return record['id']

    def retrieve(self, user, query, *, limit=3, cloud=False, cloud_consent=False, min_score=None):
        owner = _owner(user)
        if not isinstance(cloud, bool) or not isinstance(cloud_consent, bool):
            raise ValueError('Cloud reasoning requires explicit boolean consent.')
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError('Retrieval limit must be between 1 and 20.')
        if min_score is not None and (isinstance(min_score,bool) or not isinstance(min_score,(int,float)) or not isfinite(min_score) or not -1<=min_score<=1):
            raise ValueError('Retrieval relevance must be a finite cosine threshold.')
        if cloud and cloud_consent is not True:
            raise PermissionError('Explicit cloud reasoning consent is required.')
        with self._transaction() as db:
            self._expire(db, owner)
            records = [self._decode(db, identity, owner, ciphertext) for identity, ciphertext in
                db.execute('SELECT id,record FROM memories WHERE owner=? ORDER BY id', (owner,))]
        if not records:
            return []
        vector, model = self.embedder.embed(query)
        validate_vector(vector)
        results = []
        # shortcut: cosine scans at most 512 owner memories; add an index before raising that bound.
        for record in records:
            stored = validate_vector(record['embedding'])
            if record['embedding_model'] != model or len(stored) != len(vector):
                raise EmbeddingUnavailable('Stored memories require the original local embedding model.')
            score = sum(a * b for a, b in zip(vector, stored)) / (hypot(*vector) * hypot(*stored))
            results.append(dict(id=record['id'], content=record['content'], provenance=record['provenance'],
                sensitivity=record['sensitivity'], verified_at=record['verified_at'], score=score))
        results.sort(key=lambda item: (-item['score'], item['id']))
        # Re-check revocation after local inference; a concurrent reset cannot return old context.
        with self._transaction() as db:
            self._expire(db, owner)
            live = {r[0] for r in db.execute('SELECT id FROM memory_keys WHERE owner=?', (owner,))}
            results = [item for item in results if item['id'] in live and (min_score is None or item['score']>=min_score)][:limit]
        if cloud and any(item['sensitivity'] != 'public' for item in results):
            raise PermissionError('Private memory is not approved for cloud reasoning.')
        return results

    def restore_owner(self, user):
        owner = _owner(user)
        with self._transaction() as db:
            self._cipher(db)
            self._expire(db, owner)
            records = []
            for event_id, ciphertext in db.execute('SELECT events.id,events.ciphertext FROM events JOIN memory_keys USING(id,owner) WHERE owner=? AND kind="save" ORDER BY sequence', (owner,)):
                records.append(self._decode(db, event_id, owner, ciphertext))
            if len(records) > 512:
                raise ValueError('Memory journal exceeds the local slice limit.')
            existing = {row[0] for row in db.execute('SELECT id FROM memories WHERE owner=?', (owner,))}
            if not existing.issubset({record['id'] for record in records}):
                raise RuntimeError('Memory journal is incomplete; existing memories are preserved.')
            # Verify every event before replacing only this owner's derived memory index.
            db.execute('DELETE FROM memories WHERE owner=?', (owner,))
            for record in records:
                db.execute('INSERT INTO memories(id,owner,record) VALUES(?,?,?)',
                    (record['id'], owner, self._memory_cipher(db, record['id'], owner).encrypt(json.dumps(record, sort_keys=True, allow_nan=False).encode())))
        return len(records)
