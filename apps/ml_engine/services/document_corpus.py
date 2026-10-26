"""Owner-consented unverified text/index in the existing Windows vault, never sync facts."""
from datetime import datetime, timedelta
from base64 import b64encode, b64decode
from hashlib import sha256
from itertools import islice
import json
from pathlib import Path
import re
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.http import Http404
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from alfred_ai.services.bounded_parser import run_bounded_parser
from alfred_ai.services.upload_limits import UploadLimitExceeded
from .canonical_evidence import _discovery_catalog, SourceSelectionConflict
from .document_knowledge import document_text, matching_passages, _passages, _terms, TEXT_BYTES, RESULT_LIMIT, EVIDENCE_LIMITATION
from .memory_sync import valid_id
from .persistent_memory import _owner, MemoryConflict

MAX_DOCUMENTS = 10
MAX_GLOBAL_DOCUMENTS = 128
MAX_SELECTED = 3
MAX_TOKENS = 20000
MAX_RECORD_BYTES = 1024 * 1024
MAX_OWNER_BYTES = 4 * 1024 * 1024
MAX_GLOBAL_BYTES = 32 * 1024 * 1024
MAX_LINKED_RECORDS = 256
MAX_UPLOAD_BYTES = 512 * 1024
LIMITATION = (EVIDENCE_LIMITATION + 'Only explicitly selected local encrypted copies are searched. '
    'No model, verified memory, conversation history or cloud sync is used. Missing matches do not prove absence. '
    'Linked financial sources are checked again on access; changed/unavailable copies are removed. '
    'Uploaded originals remain encrypted with their index until deletion or expiry. Scanned/image-only PDFs remain unsupported.')


def source_revision(user, kind, document_id):
    _, rows, stamp, count = _discovery_catalog(user, kind, document_id)
    if count > MAX_LINKED_RECORDS:
        raise ValueError('The document exceeds the linked-record revision limit.')
    digest = sha256(); size = 0
    for row in rows.order_by('pk').values().iterator(chunk_size=64):
        encoded = json.dumps(row, sort_keys=True, allow_nan=False, default=str).encode()
        size += len(encoded)
        if size > MAX_RECORD_BYTES:
            raise ValueError('The source revision exceeds its size limit.')
        digest.update(len(encoded).to_bytes(8, 'big')); digest.update(encoded)
    return dict(stamp, linked_records=digest.hexdigest())


def _encoded(record):
    encoded = json.dumps(record, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    if len(encoded) > MAX_RECORD_BYTES:
        raise ValueError('The document index exceeds its size limit.')
    return encoded


class DocumentCorpus:
    def __init__(self, store):
        self.store = store

    def _rows(self, db, owner):
        rows = db.execute('SELECT id,wrapped,record FROM document_corpus WHERE owner=? ORDER BY id LIMIT ?',
            (owner, MAX_DOCUMENTS + 1)).fetchall()
        if len(rows) > MAX_DOCUMENTS:
            raise RuntimeError('Document knowledge count exceeds its limit; existing data is preserved.')
        return rows

    def _decode(self, db, owner, identity, wrapped, ciphertext):
        try:
            if len(ciphertext) > 2 * MAX_RECORD_BYTES or len(wrapped) > 1024:
                raise ValueError()
            cipher = Fernet(self.store._cipher(db).decrypt(wrapped))
            record = json.loads(cipher.decrypt(ciphertext))
            if (record['schema'] != 'document-corpus-v1' or record['owner'] != owner or record['id'] != identity
                    or record['verified'] is not False or record['financial_authority'] is not False
                    or record['source']['kind'] not in ('expense', 'loan', 'investment', 'upload')
                    or not isinstance(record['revision'], dict)
                    or not isinstance(record['text'], str) or len(record['text'].encode()) > TEXT_BYTES
                    or sha256(record['text'].encode()).hexdigest() != record['text_digest']
                    or not isinstance(record['index'], dict)
                    or any(not isinstance(key, str) or not isinstance(spans, list) for key, spans in record['index'].items())
                    or sum(map(len, record['index'].values())) > MAX_TOKENS):
                raise ValueError()
            if record['source']['kind'] == 'upload':
                original = b64decode(record['original'], validate=True)
                if (not 0 < len(original) <= MAX_UPLOAD_BYTES or record['source']['document_id'] != identity
                        or record['source']['original_format'] not in ('pdf', 'txt')
                        or sha256(original).hexdigest() != record['source']['source_fingerprint']
                        or record['revision'] != {'original': record['source']['source_fingerprint']}
                        or record['source']['source_url'] != f'/api/ai/document-corpus/{identity}/original/'):
                    raise ValueError()
            elif type(record['source']['document_id']) is not int or record['source']['document_id'] < 1:
                raise ValueError()
            for term, spans in record['index'].items():
                previous = -1
                for span in spans:
                    if (not isinstance(span, list) or len(span) != 2 or any(type(n) is not int for n in span)
                            or not previous < span[0] < span[1] <= len(record['text'])
                            or record['text'][span[0]:span[1]].casefold() != term):
                        raise ValueError()
                    previous = span[0]
            created, expiry = (datetime.fromisoformat(record[key]) for key in ('created_at', 'expires_at'))
            if created.tzinfo is None or expiry.tzinfo is None or not created < expiry <= created + timedelta(days=30):
                raise ValueError()
            _encoded(record)
            return record
        except (InvalidToken, ValueError, TypeError, KeyError, AttributeError):
            raise RuntimeError('Document knowledge verification failed; existing data is preserved.') from None

    def _prune(self, db, owner):
        now = timezone.now(); days = min(30, self.store._retention(db, owner))
        for identity, wrapped, ciphertext in self._rows(db, owner):
            record = self._decode(db, owner, identity, wrapped, ciphertext)
            expiry = min(datetime.fromisoformat(record['expires_at']),
                datetime.fromisoformat(record['created_at']) + timedelta(days=days))
            if expiry <= now:
                db.execute('DELETE FROM document_corpus WHERE id=? AND owner=?', (identity, owner))
            elif expiry < datetime.fromisoformat(record['expires_at']):
                record['expires_at'] = expiry.isoformat()
                cipher = Fernet(self.store._cipher(db).decrypt(wrapped))
                db.execute('UPDATE document_corpus SET record=? WHERE id=? AND owner=?',
                    (cipher.encrypt(_encoded(record)), identity, owner))

    def _clear(self, db, owner):
        if db.execute('SELECT 1 FROM document_corpus WHERE owner=?', (owner,)).fetchone():
            self.store._cipher(db)
            db.execute('DELETE FROM document_corpus WHERE owner=?', (owner,))

    def _live(self, db, user, records):
        owner = _owner(user); live = []
        for record in records:
            if record['source']['kind'] == 'upload':
                live.append(record)
                continue
            try:
                current = source_revision(user, record['source']['kind'], record['source']['document_id'])
            except (Http404, ValueError):
                current = None
            if current != record['revision']:
                db.execute('DELETE FROM document_corpus WHERE id=? AND owner=?', (record['id'], owner))
            else:
                live.append(record)
        return live

    @staticmethod
    def _summary(record):
        return dict(record['source'], id=record['id'], created_at=record['created_at'], expires_at=record['expires_at'])

    def list(self, user):
        owner = _owner(user)
        with self.store._transaction() as db:
            self.store._cipher(db); self._prune(db, owner)
            records = [self._decode(db, owner, *row) for row in self._rows(db, owner)]
            records = self._live(db, user, records)
            return dict(documents=[self._summary(record) for record in records], maximum_documents=MAX_DOCUMENTS,
                maximum_selected=MAX_SELECTED, maximum_retention_days=min(30, self.store._retention(db, owner)),
                maximum_text_bytes=TEXT_BYTES, maximum_index_tokens=MAX_TOKENS, maximum_owner_bytes=MAX_OWNER_BYTES,
                maximum_linked_records=MAX_LINKED_RECORDS, maximum_upload_bytes=MAX_UPLOAD_BYTES,
                maximum_record_bytes=MAX_RECORD_BYTES,
                rollback_requires_clear=bool(records), limitation=LIMITATION)

    def _begin(self, user, consent, days):
        owner = _owner(user)
        if consent is not True or type(days) is not int or not 1 <= days <= 30:
            raise ValueError('Explicit local document consent and 1–30 days retention are required.')
        with self.store._transaction() as db:
            self.store._cipher(db)
            return db.execute('SELECT epoch FROM owner_epochs WHERE owner=?', (owner,)).fetchone()

    def ingest(self, user, kind, document_id, *, catalog_token, consent, days):
        if kind not in ('expense', 'loan', 'investment') or type(document_id) is not int or document_id < 1:
            raise ValueError('Choose a supported owned document.')
        epoch = self._begin(user, consent, days)
        revision = source_revision(user, kind, document_id)
        source, text, _ = document_text(user, kind, document_id, catalog_token=catalog_token)
        if source['status'] != 'searched':
            return dict(stored=False, **source, limitation=LIMITATION)
        return self._save(user, source, text, revision, days, epoch)

    def upload(self, user, upload, *, consent, days):
        epoch = self._begin(user, consent, days)
        if not isinstance(upload, UploadedFile) or not isinstance(upload.name, str):
            raise ValueError('Choose one PDF or UTF-8 text file.')
        name = Path(upload.name.replace('\\', '/')).name
        extension = Path(name).suffix.lower()
        if not name.strip() or len(name) > 160 or any(ord(c) < 32 or ord(c) == 127 for c in name) or extension not in ('.pdf', '.txt'):
            raise ValueError('Choose a PDF or UTF-8 .txt file with a short valid name.')
        upload.seek(0); raw = upload.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise UploadLimitExceeded()
        if extension == '.pdf':
            parsed = run_bounded_parser('document_text_layer', raw, name)
            text, method = parsed['text'], parsed['method']
        else:
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeError:
                raise ValueError('Text documents must use UTF-8 encoding.') from None
            if any(ord(c) < 32 and c not in '\n\r\t' or ord(c) == 127 for c in text):
                raise ValueError('Binary/control characters are not supported in text documents.')
            method = 'utf8_text'
        if len(text.encode()) > TEXT_BYTES:
            raise UploadLimitExceeded()
        if not text.strip():
            return dict(stored=False, status='extraction_unavailable', limitation=LIMITATION)
        identity = uuid4().hex; fingerprint = sha256(raw).hexdigest()
        source = dict(status='searched', kind='upload', document_id=identity, document_name=name,
            source_fingerprint=fingerprint, source_url=f'/api/ai/document-corpus/{identity}/original/',
            text_origin='uploaded_pdf_text_layer' if extension == '.pdf' else 'uploaded_utf8_text',
            original_format=extension[1:], extraction_method=method)
        return self._save(user, source, text, {'original': fingerprint}, days, epoch, original=raw)

    def _save(self, user, source, text, revision, days, epoch, *, original=None):
        owner = _owner(user); kind = source['kind']; document_id = source['document_id']
        index = {}; count = 0
        for match in re.finditer(r'\w+', text):
            term = match.group().casefold()
            if len(term) < 2:
                continue
            count += 1
            if count > MAX_TOKENS:
                raise ValueError('The document exceeds the index token limit.')
            index.setdefault(term, []).append([match.start(), match.end()])
        with self.store._transaction() as db:
            if db.execute('SELECT epoch FROM owner_epochs WHERE owner=?', (owner,)).fetchone() != epoch:
                raise MemoryConflict('Document ingestion was invalidated by an owner reset.')
            self._prune(db, owner)
            records = self._live(db, user, [self._decode(db, owner, *row) for row in self._rows(db, owner)])
            if kind != 'upload' and source_revision(user, kind, document_id) != revision:
                raise SourceSelectionConflict()
            existing = [record['id'] for record in records if (record['source']['kind'], record['source']['document_id']) == (kind, document_id)]
            if len(records) - len(existing) >= MAX_DOCUMENTS:
                raise ValueError('Document knowledge count limit reached.')
            now = timezone.now()
            record = dict(schema='document-corpus-v1', id=document_id if kind == 'upload' else uuid4().hex, owner=owner, verified=False,
                financial_authority=False, source=source, revision=revision, text=text,
                text_digest=sha256(text.encode()).hexdigest(), index=index, created_at=now.isoformat(),
                expires_at=(now + timedelta(days=min(days, self.store._retention(db, owner)))).isoformat())
            if original is not None:
                record['original'] = b64encode(original).decode('ascii')
            key = Fernet.generate_key(); ciphertext = Fernet(key).encrypt(_encoded(record))
            for identity in existing:
                db.execute('DELETE FROM document_corpus WHERE id=? AND owner=?', (identity, owner))
            total, size = db.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(record)),0) FROM document_corpus').fetchone()
            owner_size = db.execute('SELECT COALESCE(SUM(LENGTH(record)),0) FROM document_corpus WHERE owner=?', (owner,)).fetchone()[0]
            if total >= MAX_GLOBAL_DOCUMENTS or size + len(ciphertext) > MAX_GLOBAL_BYTES or owner_size + len(ciphertext) > MAX_OWNER_BYTES:
                raise ValueError('Document knowledge storage quota reached.')
            db.execute('INSERT INTO document_corpus VALUES(?,?,?,?)',
                (record['id'], owner, self.store._cipher(db).encrypt(key), ciphertext))
        return dict(stored=True, document=self._summary(record), limitation=LIMITATION)

    def original(self, user, identity):
        if not valid_id(identity):
            raise ValueError('Choose a valid private document.')
        result = None; owner = _owner(user)
        with self.store._transaction() as db:
            self._prune(db, owner)
            for row in self._rows(db, owner):
                if row[0] == identity:
                    record = self._decode(db, owner, *row)
                    if record['source']['kind'] == 'upload':
                        result = self._summary(record), b64decode(record['original'], validate=True)
        if result is None:
            raise Http404
        return result

    def search(self, user, identities, query, *, full_context=False):
        owner = _owner(user); terms = None if full_context else _terms(query)
        if (not isinstance(identities, list) or not 1 <= len(identities) <= MAX_SELECTED
                or any(not valid_id(identity) for identity in identities) or len(set(identities)) != len(identities)):
            raise ValueError('Select one to three distinct private documents.')
        with self.store._transaction() as db:
            self._prune(db, owner)
            rows = {row[0]: row for row in self._rows(db, owner) if row[0] in identities}
            records = self._live(db, user, [self._decode(db, owner, *rows[identity]) for identity in identities if identity in rows])
            matches = []
            for record in records:
                if full_context:
                    passages = (dict(start=start, end=end, excerpt=excerpt)
                        for start, end, excerpt in _passages(record['text']))
                    matches.extend(dict(hit, **self._summary(record)) for hit in islice(passages, RESULT_LIMIT + 1))
                else:
                    matches.extend(dict(hit, **self._summary(record)) for hit in matching_passages(record['text'], terms, record['index']))
            live = self._live(db, user, records)
            conflict = len(records) != len(identities) or len(live) != len(records)
        # Commit expiry/invalidation before reporting a stale selection.
        if conflict:
            raise SourceSelectionConflict()
        return dict(results=matches[:RESULT_LIMIT], more_matches=len(matches) > RESULT_LIMIT,
            checked_at=timezone.now().isoformat(), result_limit=RESULT_LIMIT,
            full_text_qa=False, financial_authority=False, limitation=LIMITATION)

    def delete(self, user, identity):
        if not valid_id(identity):
            raise ValueError('Choose a valid private document.')
        with self.store._transaction() as db:
            self.store._cipher(db)
            if not db.execute('DELETE FROM document_corpus WHERE id=? AND owner=?', (identity, _owner(user))).rowcount:
                raise Http404

    def delete_source(self, user, kind, document_id):
        owner = _owner(user)
        with self.store._transaction() as db:
            for row in self._rows(db, owner):
                record = self._decode(db, owner, *row)
                if (record['source']['kind'], record['source']['document_id']) == (kind, document_id):
                    db.execute('DELETE FROM document_corpus WHERE id=? AND owner=?', (record['id'], owner))
