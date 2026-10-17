"""Local-only transcripts in the existing vault; never memory facts or sync events."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from .persistent_memory import _owner, _json, MemoryConflict
from .memory_sync import valid_id

MAX_CONVERSATIONS = 50
MAX_TURNS = 20
MAX_RECORD = 262144


class ConversationConflict(MemoryConflict):
    pass


class ConversationPermission(PermissionError):
    pass


def _encoded(record):
    encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    if len(encoded) > MAX_RECORD:
        raise ValueError('Conversation size limit reached. Start a new conversation.')
    return encoded


class ConversationHistory:
    def __init__(self, store):
        self.store = store

    def _policy(self, db, owner):
        row = db.execute('SELECT encrypted FROM conversation_policies WHERE owner=?', (owner,)).fetchone()
        if not row:
            return dict(owner=owner, enabled=False, days=None, generation=0)
        try:
            policy = json.loads(self.store._cipher(db).decrypt(row[0]))
            if (policy['owner'] != owner or type(policy['enabled']) is not bool or type(policy['generation']) is not int
                    or policy['generation'] < 0 or (policy['days'] is not None and
                    (type(policy['days']) is not int or not 1 <= policy['days'] <= 30))):
                raise ValueError()
            if policy['enabled'] and policy['days'] is None: raise ValueError()
            return policy
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise RuntimeError('Private conversation policy verification failed.') from None

    def _write_policy(self, db, owner, policy):
        encrypted = self.store._cipher(db).encrypt(_json(policy).encode())
        db.execute('INSERT INTO conversation_policies VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET encrypted=excluded.encrypted', (owner, encrypted))

    def _enabled(self, db, owner):
        policy = self._policy(db, owner)
        if not settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED or not policy['enabled']:
            raise ConversationPermission('Private history requires operator availability and owner opt-in.')
        return policy

    def _read(self, db, owner, identity, wrapped, ciphertext):
        try:
            key = self.store._cipher(db).decrypt(wrapped)
            record = json.loads(Fernet(key).decrypt(ciphertext))
            if (record['kind'] != 'assistant_conversation' or type(record['schema']) is not int or record['schema'] != 1
                    or record['owner'] != owner or record['id'] != identity or type(record['revision']) is not int
                    or record['revision'] < 0 or not isinstance(record['turns'], list) or len(record['turns']) > MAX_TURNS
                    or not isinstance(record['title'], str) or not 1 <= len(record['title'].encode()) <= 128):
                raise ValueError()
            for field in ('created_at', 'updated_at', 'expires_at'):
                if datetime.fromisoformat(record[field]).tzinfo is None: raise ValueError()
            _encoded(record)
            return record
        except (InvalidToken, ValueError, KeyError, TypeError):
            raise RuntimeError('Private conversation verification failed; existing data is preserved.') from None

    def _rows(self, db, owner):
        rows = db.execute('SELECT id,wrapped,record FROM conversations WHERE owner=? ORDER BY id LIMIT ?',
                          (owner, MAX_CONVERSATIONS+1)).fetchall()
        if len(rows) > MAX_CONVERSATIONS: raise RuntimeError('Private conversation count exceeds its limit.')
        return rows

    def _expire(self, db, owner):
        policy = self._policy(db, owner)
        now = datetime.now(timezone.utc)
        for identity, wrapped, ciphertext in self._rows(db, owner):
            record = self._read(db, owner, identity, wrapped, ciphertext)
            expiry = datetime.fromisoformat(record['expires_at'])
            if policy['days'] is not None:
                expiry = min(expiry, datetime.fromisoformat(record['created_at'])+timedelta(days=policy['days']))
            if not policy['enabled'] or expiry <= now:
                db.execute('DELETE FROM conversations WHERE id=? AND owner=?', (identity, owner))
            elif expiry < datetime.fromisoformat(record['expires_at']):
                record['expires_at'] = expiry.isoformat()
                cipher = Fernet(self.store._cipher(db).decrypt(wrapped))
                db.execute('UPDATE conversations SET record=? WHERE id=? AND owner=?',
                           (cipher.encrypt(_encoded(record)), identity, owner))

    def _clear(self, db, owner, *, disable=False):
        policy = self._policy(db, owner)
        count = db.execute('SELECT COUNT(*) FROM conversations WHERE owner=?', (owner,)).fetchone()[0]
        if count or db.execute('SELECT 1 FROM conversation_policies WHERE owner=?', (owner,)).fetchone():
            policy['generation'] += 1
            if disable: policy['enabled'] = False
            self._write_policy(db, owner, policy)
            db.execute('DELETE FROM conversations WHERE owner=?', (owner,))
        return count

    def policy(self, user):
        owner = _owner(user)
        with self.store._transaction() as db:
            self._expire(db, owner)
            policy = self._policy(db, owner)
            count = db.execute('SELECT COUNT(*) FROM conversations WHERE owner=?', (owner,)).fetchone()[0]
        return dict(available=settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED, enabled=policy['enabled'],
                    retention_days=policy['days'], conversations=count, maximum_days=30,
                    rollback_requires_clear=policy['enabled'] or count > 0)

    def configure(self, user, *, enabled, consent=False, days=None):
        if type(enabled) is not bool or type(consent) is not bool:
            raise ValueError('Choose an explicit private history policy.')
        if enabled and (not settings.ALFRED_CONVERSATION_HISTORY_AUTHORIZED or consent is not True):
            raise ConversationPermission('Private history requires explicit local-only consent.')
        if enabled and (type(days) is not int or not 1 <= days <= 30):
            raise ValueError('Choose between one and thirty retention days.')
        owner = _owner(user)
        with self.store._transaction() as db:
            if not enabled: self._clear(db, owner, disable=True)
            policy = self._policy(db, owner)
            policy.update(enabled=enabled, days=days if enabled else policy['days'], generation=policy['generation']+1)
            self._write_policy(db, owner, policy)
            self._expire(db, owner)
        return self.policy(user)

    def clear(self, user):
        with self.store._transaction() as db:
            return self._clear(db, _owner(user))

    def list(self, user):
        owner = _owner(user)
        with self.store._transaction() as db:
            self._enabled(db, owner); self._expire(db, owner)
            records = [self._read(db, owner, *row) for row in self._rows(db, owner)]
        return [{key: record[key] for key in ('id', 'title', 'created_at', 'updated_at', 'expires_at', 'revision')}
                for record in sorted(records, key=lambda r:r['updated_at'], reverse=True)]

    def create(self, user, title):
        if not isinstance(title, str) or not 1 <= len(title.strip().encode()) <= 128 or any(ord(c) < 32 for c in title):
            raise ValueError('Use a bounded conversation title.')
        owner = _owner(user)
        with self.store._transaction() as db:
            policy = self._enabled(db, owner); self._expire(db, owner)
            if len(self._rows(db, owner)) >= MAX_CONVERSATIONS: raise ValueError('Private conversation limit reached.')
            now = datetime.now(timezone.utc)
            record = dict(kind='assistant_conversation', schema=1, owner=owner, id=uuid4().hex, title=title.strip(),
                revision=0, turns=[], created_at=now.isoformat(), updated_at=now.isoformat(),
                expires_at=(now+timedelta(days=policy['days'])).isoformat())
            key = Fernet.generate_key()
            db.execute('INSERT INTO conversations VALUES(?,?,?,?)', (record['id'], owner,
                self.store._cipher(db).encrypt(key), Fernet(key).encrypt(_encoded(record))))
        created = self.get(user, record['id'])
        if created is None: raise ConversationConflict('Conversation was cleared during creation.')
        return created

    def _get(self, db, owner, identity):
        if not valid_id(identity): raise ValueError('Choose a saved private conversation.')
        row = db.execute('SELECT wrapped,record FROM conversations WHERE id=? AND owner=?', (identity, owner)).fetchone()
        if row is None: return None
        return self._read(db, owner, identity, *row)

    def get(self, user, identity):
        owner = _owner(user)
        with self.store._transaction() as db:
            self._enabled(db, owner); self._expire(db, owner)
            record = self._get(db, owner, identity)
        return {key:value for key,value in record.items() if key not in ('owner','kind','schema')} if record else None

    def delete(self, user, identity):
        if not valid_id(identity): raise ValueError('Choose a saved private conversation.')
        with self.store._transaction() as db:
            return db.execute('DELETE FROM conversations WHERE id=? AND owner=?', (identity, _owner(user))).rowcount

    def prepare(self, user, identity, revision, request_id, question):
        if not valid_id(request_id) or type(revision) is not int or revision < 0: raise ValueError('Invalid conversation revision/request.')
        owner = _owner(user)
        digest = sha256(_json(question).encode()).hexdigest()
        with self.store._transaction() as db:
            policy = self._enabled(db, owner); self._expire(db, owner)
            record = self._get(db, owner, identity)
            if record is None: raise ConversationConflict('Conversation is no longer available.')
            for turn in record['turns']:
                if turn['request_id'] == request_id:
                    if turn['input_digest'] != digest: raise ConversationConflict('Request identity changed.')
                    return policy['generation'], turn
            if record['revision'] != revision or len(record['turns']) >= MAX_TURNS:
                raise ConversationConflict('Conversation changed or reached its turn limit.')
        return policy['generation'], None

    def append(self, user, identity, revision, request_id, question, result, generation):
        owner = _owner(user)
        if (result.get('provider') != 'ollama' or result.get('classification') != 'ai_generated_hypothesis'
                or result.get('financial_authority') is not False or not isinstance(result.get('answer'), str)
                or not 1 <= len(result['answer'].encode()) <= 8192):
            raise ValueError('Only a validated local assistant answer can be retained.')
        # Historical citations keep references only, never copied canonical amounts or memory content.
        sources = [{key:source[key] for key in ('ref','classification','url','verified_at') if key in source}
                   for source in result.get('sources', [])]
        for source in result.get('sources', []):
            if source.get('data', {}).get('document_selection', {}).get('mode') == 'explicit':
                sources += [dict(ref=f"{source['ref']}-document-{item['document_id']}",
                    classification='selected_document_reference',url=item['url'])
                    for item in source['data']['document_sources'] if item['url'] != source.get('url')]
        turn = dict(request_id=request_id, input_digest=sha256(_json(question).encode()).hexdigest(),
                    **question, answer=result['answer'], provider='ollama', classification='ai_generated_hypothesis',
                    financial_authority=False, sources=sources, narrative_withheld=bool(result.get('narrative_withheld')),
                    saved_at=datetime.now(timezone.utc).isoformat())
        with self.store._transaction() as db:
            policy = self._enabled(db, owner); self._expire(db, owner)
            record = self._get(db, owner, identity)
            if record is None or policy['generation'] != generation: raise ConversationConflict('Private history policy changed.')
            for existing in record['turns']:
                if existing['request_id'] == request_id:
                    if existing['input_digest'] != turn['input_digest']: raise ConversationConflict('Request identity changed.')
                    return record['revision']
            if record['revision'] != revision or len(record['turns']) >= MAX_TURNS: raise ConversationConflict('Conversation changed during inference.')
            record['turns'].append(turn); record['revision'] += 1; record['updated_at'] = turn['saved_at']
            wrapped = db.execute('SELECT wrapped FROM conversations WHERE id=? AND owner=?', (identity, owner)).fetchone()[0]
            cipher = Fernet(self.store._cipher(db).decrypt(wrapped))
            db.execute('UPDATE conversations SET record=? WHERE id=? AND owner=?', (cipher.encrypt(_encoded(record)), identity, owner))
            return record['revision']
