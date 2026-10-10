"""Verified owner-scoped local memories and an encrypted append-only restore journal."""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import hypot
import os
from pathlib import Path
import sqlite3
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

from .local_embeddings import OllamaEmbeddings, validate_vector, EmbeddingUnavailable


SENSITIVITIES = {'public', 'personal', 'sensitive'}


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
    def __init__(self, directory, *, embedder=None):
        if not Path(directory).is_absolute():
            raise ValueError('Memory storage requires an absolute persistent directory.')
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.database = self.directory / 'verified.sqlite3'
        self.key_file = self.directory / 'journal.key'
        self.embedder = embedder if embedder is not None else OllamaEmbeddings()
        with self._transaction() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, record TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS memories_owner ON memories(owner);
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT NOT NULL UNIQUE,
                    owner TEXT NOT NULL, ciphertext BLOB NOT NULL);
                CREATE INDEX IF NOT EXISTS events_owner ON events(owner, sequence);
                CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
                    BEGIN SELECT RAISE(ABORT, 'Journal events are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
                    BEGIN SELECT RAISE(ABORT, 'Journal events are append-only'); END;
            ''')

    @contextmanager
    def _transaction(self):
        db = sqlite3.connect(self.database, timeout=10)
        try:
            db.execute('PRAGMA journal_mode=WAL')
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
            if db.execute('SELECT EXISTS(SELECT 1 FROM events)').fetchone()[0]:
                raise RuntimeError('Memory recovery key is missing; restore its protected backup.')
            descriptor = os.open(self.key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(Fernet.generate_key())
                stream.flush()
                os.fsync(stream.fileno())
        try:
            return Fernet(self.key_file.read_bytes())
        except (ValueError, OSError):
            raise RuntimeError('Memory recovery key is unavailable; keep its protected backup.') from None

    def save_verified(self, user, content, provenance, *, sensitivity='sensitive', verified=False):
        owner = _owner(user)
        if verified is not True or not isinstance(content, dict) or not content or not isinstance(provenance, dict) or not isinstance(provenance.get('source'), str) or not provenance['source'].strip() or sensitivity not in SENSITIVITIES:
            raise ValueError('Confirm a structured memory, its source and sensitivity before saving.')
        text = _json(content)
        content = json.loads(text)
        provenance = json.loads(_json(provenance))
        vector, model = self.embedder.embed(text)
        validate_vector(vector)
        if not isinstance(model, str) or not 1 <= len(model) <= 256:
            raise EmbeddingUnavailable('Local embedding model identity is invalid.')
        record = dict(id=uuid4().hex, owner=owner, content=content, provenance=provenance,
            sensitivity=sensitivity, verified=True, verified_at=datetime.now(timezone.utc).isoformat(),
            embedding=vector, embedding_model=model)
        encoded = json.dumps(record, sort_keys=True, allow_nan=False).encode()
        with self._transaction() as db:
            if db.execute('SELECT COUNT(*) FROM memories WHERE owner=?', (owner,)).fetchone()[0] >= 512:
                raise ValueError('The local memory slice supports at most 512 verified memories per owner.')
            event = dict(version=1, record=record)
            ciphertext = self._cipher(db).encrypt(json.dumps(event, sort_keys=True, allow_nan=False).encode())
            db.execute('INSERT INTO events(id,owner,ciphertext) VALUES(?,?,?)', (record['id'], owner, ciphertext))
            db.execute('INSERT INTO memories(id,owner,record) VALUES(?,?,?)', (record['id'], owner, encoded.decode()))
        return record['id']

    def retrieve(self, user, query, *, limit=3, cloud=False, cloud_consent=False):
        owner = _owner(user)
        if not isinstance(cloud, bool) or not isinstance(cloud_consent, bool):
            raise ValueError('Cloud reasoning requires explicit boolean consent.')
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError('Retrieval limit must be between 1 and 20.')
        if cloud and cloud_consent is not True:
            raise PermissionError('Explicit cloud reasoning consent is required.')
        with self._transaction() as db:
            records = [json.loads(row[0]) for row in db.execute('SELECT record FROM memories WHERE owner=? ORDER BY id', (owner,))]
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
        results = results[:limit]
        if cloud and any(item['sensitivity'] != 'public' for item in results):
            raise PermissionError('Private memory is not approved for cloud reasoning.')
        return results

    def restore_owner(self, user):
        owner = _owner(user)
        with self._transaction() as db:
            cipher = self._cipher(db)
            records = []
            for event_id, ciphertext in db.execute('SELECT id,ciphertext FROM events WHERE owner=? ORDER BY sequence', (owner,)):
                try:
                    if len(ciphertext) > 256 * 1024:
                        raise ValueError()
                    event = json.loads(cipher.decrypt(ciphertext))
                    record = event['record']
                    if event['version'] != 1 or record['owner'] != owner or record['id'] != event_id or record['verified'] is not True or record['sensitivity'] not in SENSITIVITIES:
                        raise ValueError()
                    validate_vector(record['embedding'])
                    _json(record['content'])
                    _json(record['provenance'])
                    records.append(record)
                except (InvalidToken, ValueError, KeyError, TypeError, EmbeddingUnavailable):
                    raise RuntimeError('Memory journal verification failed; existing memories are preserved.') from None
            if len(records) > 512:
                raise ValueError('Memory journal exceeds the local slice limit.')
            existing = {row[0] for row in db.execute('SELECT id FROM memories WHERE owner=?', (owner,))}
            if not existing.issubset({record['id'] for record in records}):
                raise RuntimeError('Memory journal is incomplete; existing memories are preserved.')
            # Verify every event before replacing only this owner's derived memory index.
            db.execute('DELETE FROM memories WHERE owner=?', (owner,))
            for record in records:
                db.execute('INSERT INTO memories(id,owner,record) VALUES(?,?,?)',
                    (record['id'], owner, json.dumps(record, sort_keys=True, allow_nan=False)))
        return len(records)
