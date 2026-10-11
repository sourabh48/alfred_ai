"""Authenticated encrypted snapshots, current-key manifests and durable owner retries.

All providers must enforce
authenticated owner scope, immutable objects, atomic CAS and this total deadline.
"""
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken

from .memory_key import private_directory, protect_key
from .persistent_memory import _owner, _json, SENSITIVITIES
from .local_embeddings import validate_vector

MAX_OBJECT = 32 * 1024 * 1024
MAX_HEAD = 128 * 1024

class SyncUnavailable(RuntimeError):
    pass

class SyncConflict(RuntimeError):
    pass

def remaining(deadline):
    seconds = deadline - time.monotonic()
    if seconds <= 0:
        raise SyncUnavailable('Memory synchronization deadline expired; local data is retained.')
    return min(seconds, 5)

def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(',', ':')).encode()

def digest(value):
    return sha256(encoded(value)).hexdigest()

def valid_id(value, length=32):
    return isinstance(value, str) and bool(re.fullmatch('[a-f0-9]{'+str(length)+'}', value))

class MockCloudProvider:
    """Local ciphertext-only mock; never sends data over a network."""
    def __init__(self, directory, *, timeout=5):
        deadline=time.monotonic()+timeout
        directory = Path(directory)
        if not directory.is_absolute():
            raise ValueError('Mock synchronization requires an absolute isolated directory.')
        private_directory(directory,deadline=deadline)
        self.database = directory / 'mock-cloud.sqlite3'
        self.offline = False
        with closing(sqlite3.connect(self.database,timeout=remaining(deadline))) as db:
            db.executescript('''
                PRAGMA secure_delete=ON;
                CREATE TABLE IF NOT EXISTS objects(owner TEXT, identity TEXT, ciphertext BLOB, PRIMARY KEY(owner,identity));
                CREATE TABLE IF NOT EXISTS heads(owner TEXT PRIMARY KEY, revision INTEGER, identity TEXT, manifest BLOB);
                CREATE TABLE IF NOT EXISTS object_times(owner TEXT, identity TEXT, created REAL, PRIMARY KEY(owner,identity));
                CREATE TRIGGER IF NOT EXISTS objects_immutable_update BEFORE UPDATE ON objects BEGIN SELECT RAISE(ABORT,'Immutable snapshot'); END;
                CREATE TRIGGER IF NOT EXISTS objects_immutable_delete BEFORE DELETE ON objects BEGIN SELECT RAISE(ABORT,'Immutable snapshot'); END;
            ''')

    def _connection(self, owner, deadline):
        if not valid_id(owner, 64):
            raise PermissionError('Invalid synchronization owner.')
        if self.offline:
            raise SyncUnavailable('Mock provider is offline; local updates are queued.')
        return sqlite3.connect(self.database, timeout=remaining(deadline))

    def head(self, owner, *, deadline):
        with closing(self._connection(owner, deadline)) as db:
            size = db.execute('SELECT length(manifest) FROM heads WHERE owner=?', (owner,)).fetchone()
            if size and size[0]>MAX_HEAD: raise SyncUnavailable('Remote head exceeds the download budget.')
            row = db.execute('SELECT revision,identity,manifest FROM heads WHERE owner=?', (owner,)).fetchone()
        remaining(deadline)
        return dict(revision=row[0], identity=row[1], manifest=row[2]) if row else None

    def download(self, owner, identity, *, deadline, maximum=MAX_OBJECT):
        if not valid_id(identity, 64):
            raise SyncUnavailable('Invalid snapshot reference.')
        with closing(self._connection(owner, deadline)) as db:
            size = db.execute('SELECT length(ciphertext) FROM objects WHERE owner=? AND identity=?', (owner,identity)).fetchone()
            if not size or size[0]>maximum: raise SyncUnavailable('Snapshot is missing or exceeds the download budget.')
            row=db.execute('SELECT ciphertext FROM objects WHERE owner=? AND identity=?',(owner,identity)).fetchone()
        remaining(deadline)
        return row[0]

    def publish(self, owner, expected_revision, identity, ciphertext, manifest, *, deadline):
        if not valid_id(identity, 64) or sha256(ciphertext).hexdigest() != identity or len(ciphertext)>MAX_OBJECT or len(manifest)>MAX_HEAD:
            raise SyncUnavailable('Snapshot exceeds the synchronization budget.')
        with closing(self._connection(owner, deadline)) as db:
            db.execute('PRAGMA secure_delete=ON')
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT revision FROM heads WHERE owner=?',(owner,)).fetchone()
            if (row[0] if row else 0) != expected_revision:
                raise SyncConflict('Concurrent remote updates require verified recovery.')
            remaining(deadline)
            db.execute('INSERT OR IGNORE INTO objects VALUES(?,?,?)',(owner,identity,ciphertext))
            db.execute('INSERT OR IGNORE INTO object_times VALUES(?,?,?)',(owner,identity,time.time()))
            db.execute('INSERT INTO heads VALUES(?,?,?,?) ON CONFLICT(owner) DO UPDATE SET revision=excluded.revision,identity=excluded.identity,manifest=excluded.manifest',
                (owner,expected_revision+1,identity,manifest))
            db.commit()
        return {'revision':expected_revision+1,'identity':identity,'manifest':manifest}

    def snapshots(self,owner,*,deadline):
        with closing(self._connection(owner,deadline)) as db:
            rows=db.execute('SELECT objects.identity,COALESCE(object_times.created,?) FROM objects LEFT JOIN object_times USING(owner,identity) WHERE objects.owner=? LIMIT 4097',(time.time(),owner)).fetchall()
        if len(rows)>4096: raise SyncUnavailable('Snapshot listing exceeds the bounded retention pass.')
        return rows

    def remove_snapshot(self,owner,identity,*,deadline):
        if not valid_id(identity,64): raise PermissionError('Invalid snapshot removal scope.')
        with closing(self._connection(owner,deadline)) as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM heads WHERE owner=? AND identity=?',(owner,identity)).fetchone(): raise SyncConflict('Current snapshot cannot be pruned.')
            # Retention is the sole deletion exception; DDL and removal commit atomically.
            db.execute('DROP TRIGGER objects_immutable_delete')
            db.execute('DELETE FROM objects WHERE owner=? AND identity=?',(owner,identity))
            db.execute('DELETE FROM object_times WHERE owner=? AND identity=?',(owner,identity))
            db.execute("CREATE TRIGGER objects_immutable_delete BEFORE DELETE ON objects BEGIN SELECT RAISE(ABORT,'Immutable snapshot'); END")
            remaining(deadline); db.commit()

class MemorySynchronizer:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider

    def _key(self, owner, *, create=False):
        path=self.store.directory / ('sync-'+owner+'.key')
        if path.is_symlink() or path.is_junction(): raise SyncUnavailable('Linked synchronization keys are refused.')
        if not path.exists() and create:
            protected=b'M15SYNC1\0'+protect_key(Fernet.generate_key())
            descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(protected); stream.flush(); os.fsync(stream.fileno())
        try:
            blob=path.read_bytes()
            if not blob.startswith(b'M15SYNC1\0'): raise ValueError()
            return Fernet(protect_key(blob[9:],decrypt=True))
        except (ValueError,OSError):
            raise SyncUnavailable('Restore the protected synchronization key; it is never replaced automatically.') from None

    def configure(self, user, *, enabled, consent=False):
        owner=_owner(user)
        if not isinstance(enabled,bool) or (enabled and consent is not True):
            raise PermissionError('Explicit owner consent is required for encrypted synchronization.')
        with self.store._transaction() as db:
            state=self.store._sync_state(db,owner)
            if enabled:
                self._key(owner,create=not state.get('key_created',False))
                state['key_created']=True
            state.update(enabled=enabled)
            self.store._write_sync_state(db,owner,state)
        return self.status(user)

    def status(self,user):
        with self.store._transaction() as db:
            state=self.store._sync_state(db,_owner(user))
            return {k:state[k] for k in ('enabled','pending','revision','conflict','failures')}

    def export_checkpoint(self,user,*,confirm=False):
        if confirm is not True: raise PermissionError('Explicit recovery checkpoint export confirmation is required.')
        owner=_owner(user); cipher=self._key(owner)
        with self.store._transaction() as db:
            state=self.store._sync_state(db,owner)
            if not state['revision'] or not valid_id(state['identity'],64) or state['pending'] or state['conflict'] or state['ack']!=digest(self._snapshot(db,owner)):
                raise SyncConflict('Synchronize local changes and revocations before exporting a trusted checkpoint.')
            return cipher.encrypt(encoded({'schema':1,'owner':owner,'revision':state['revision'],'identity':state['identity']}))

    def import_checkpoint(self,user,checkpoint,*,confirm=False):
        if confirm is not True: raise PermissionError('Explicit trusted checkpoint import confirmation is required.')
        owner=_owner(user); cipher=self._key(owner)
        try:
            if not isinstance(checkpoint,bytes) or not 1<=len(checkpoint)<=4096: raise ValueError()
            anchor=json.loads(cipher.decrypt(checkpoint))
            if not isinstance(anchor,dict) or set(anchor)!= {'schema','owner','revision','identity'} or type(anchor['schema']) is not int or anchor['schema']!=1 or anchor['owner']!=owner or type(anchor['revision']) is not int or not 1<=anchor['revision']<2**63 or not valid_id(anchor['identity'],64): raise ValueError()
        except (InvalidToken,ValueError,TypeError,KeyError,UnicodeError):
            raise SyncUnavailable('Memory checkpoint verification failed; existing keys and data are retained.') from None
        floor={'revision':anchor['revision'],'identity':anchor['identity']}
        with self.store._transaction() as db:
            state=self.store._sync_state(db,owner); local=self._snapshot(db,owner)
            if state['revision'] or state['pending'] or local['records'] or local['revoked'] or local['epoch'] or local['retention']!=30 or (state.get('recovery_checkpoint') and state['recovery_checkpoint']!=floor):
                raise SyncConflict('Import requires an unused owner vault; existing data and checkpoints are preserved.')
            state.update(recovery_checkpoint=floor,key_created=True,enabled=False)
            self.store._write_sync_state(db,owner,state)

    def prune(self,user,*,confirm=False):
        if confirm is not True: raise PermissionError('Explicit snapshot pruning confirmation is required.')
        owner=_owner(user); deadline=time.monotonic()+5
        with self.store._transaction(timeout=remaining(deadline)) as db:
            state=self.store._sync_state(db,owner)
            if not state['enabled'] or state['pending'] or state['conflict']: raise SyncConflict('Synchronize current local changes before pruning.')
        cipher=self._key(owner); head=self.provider.head(owner,deadline=deadline)
        if not head: return 0
        snapshot,parent=self._verify(owner,head,cipher,deadline)
        if head['revision']!=state['revision'] or head['identity']!=state['identity']: raise SyncConflict('Refresh the current trusted checkpoint before pruning.')
        retained={head['identity']}; revision=head['revision']-1; downloaded=0
        cutoff=time.time()-self.store.retention_days(user)*86400
        # Preserve all ancestors needed by the bounded 128-version recovery window.
        for _ in range(128):
            if parent is None: break
            body=self.provider.download(owner,parent,deadline=deadline)
            downloaded+=len(body)
            if downloaded>64*1024*1024: raise SyncUnavailable('Snapshot pruning verification budget exceeded.')
            try:
                payload=json.loads(cipher.decrypt(body))
                if sha256(body).hexdigest()!=parent or type(payload['schema']) is not int or payload['schema']!=1 or payload['owner']!=owner or type(payload['revision']) is not int or payload['revision']!=revision or (revision==1 and payload['parent'] is not None) or (revision>1 and not valid_id(payload['parent'],64)): raise ValueError()
                cutoff=min(cutoff,cipher.extract_timestamp(body)-86400)
            except (ValueError,KeyError,InvalidToken): raise SyncUnavailable('Snapshot pruning history verification failed.') from None
            retained.add(parent); parent=payload['parent']; revision-=1
        objects=self.provider.snapshots(owner,deadline=deadline)
        if self.provider.head(owner,deadline=deadline)!=head: raise SyncConflict('Cloud changed during pruning verification.')
        with self.store._transaction(timeout=remaining(deadline)) as db:
            latest=self.store._sync_state(db,owner)
            if not latest['enabled'] or latest['pending'] or latest['revision']!=state['revision']: raise SyncConflict('Local consent or memory changed during pruning.')
        count=0
        for identity,created in objects:
            if identity not in retained and created<cutoff and count<16:
                self.provider.remove_snapshot(owner,identity,deadline=deadline); count+=1
        return count

    def _snapshot(self, db, owner):
        self.store._expire(db,owner)
        records={}; keys={}; revoked=set()
        master=self.store._cipher(db)
        for identity,kind,ciphertext in db.execute('SELECT id,kind,ciphertext FROM events WHERE owner=? ORDER BY sequence',(owner,)):
            if kind != 'save':
                revoked.update(json.loads(master.decrypt(ciphertext))['ids'])
                continue
            row=db.execute('SELECT wrapped FROM memory_keys WHERE id=? AND owner=?',(identity,owner)).fetchone()
            if row:
                self.store._decode(db,identity,owner,ciphertext)
                records[identity]=ciphertext.decode('ascii')
                keys[identity]=master.decrypt(row[0]).decode('ascii')
        epoch=db.execute('SELECT epoch FROM owner_epochs WHERE owner=?',(owner,)).fetchone()
        return {'owner':owner,'epoch':epoch[0] if epoch else 0,'retention':self.store._retention(db,owner),
            'records':records,'keys':keys,'revoked':sorted(revoked)}

    def _verify(self,owner,head,cipher,deadline):
        if not isinstance(head,dict) or set(head)!= {'revision','identity','manifest'} or isinstance(head['revision'],bool) or not isinstance(head['revision'],int) or head['revision']<1 or not valid_id(head['identity'],64) or not isinstance(head['manifest'],bytes) or len(head['manifest'])>MAX_HEAD:
            raise SyncUnavailable('Remote memory verification failed; existing data is retained.')
        try:
            manifest=json.loads(cipher.decrypt(head['manifest']))
            body=self.provider.download(owner,head['identity'],deadline=deadline,maximum=MAX_OBJECT)
            if not isinstance(body,bytes) or len(body)>MAX_OBJECT or sha256(body).hexdigest()!=head['identity']:
                raise ValueError()
            snapshot=json.loads(cipher.decrypt(body))
            if type(snapshot['schema']) is not int or snapshot['schema']!=1 or snapshot['owner']!=owner or type(snapshot['revision']) is not int or snapshot['revision']!=head['revision'] or manifest['owner']!=owner or type(manifest['revision']) is not int or manifest['revision']!=head['revision'] or manifest['identity']!=head['identity']:
                raise ValueError()
            if set(snapshot)!= {'schema','owner','revision','parent','epoch','retention','records','revoked'} or set(manifest)!= {'owner','revision','identity','keys'}:
                raise ValueError()
            if isinstance(snapshot['epoch'],bool) or not isinstance(snapshot['epoch'],int) or snapshot['epoch']<0 or isinstance(snapshot['retention'],bool) or not isinstance(snapshot['retention'],int) or not 1<=snapshot['retention']<=365:
                raise ValueError()
            if (head['revision']==1 and snapshot['parent'] is not None) or (head['revision']>1 and not valid_id(snapshot['parent'],64)): raise ValueError()
            records=snapshot['records']; keys=manifest['keys']; revoked=snapshot['revoked']
            if not isinstance(records,dict) or not isinstance(keys,dict) or len(records)>512 or set(records)!=set(keys) or not isinstance(revoked,list) or len(revoked)>4096 or len(set(revoked))!=len(revoked) or any(not valid_id(i) for i in [*records,*revoked]) or set(records)&set(revoked):
                raise ValueError()
            for identity,encrypted in records.items():
                remaining(deadline)
                if not isinstance(encrypted,str) or len(encrypted)>256*1024: raise ValueError()
                record=json.loads(Fernet(keys[identity].encode('ascii')).decrypt(encrypted.encode('ascii')))
                if record['id']!=identity or record['owner']!=owner or record['verified'] is not True or record['sensitivity'] not in SENSITIVITIES or not isinstance(record['content'],dict) or not record['content'] or not isinstance(record['provenance'],dict) or not isinstance(record['provenance'].get('source'),str) or not record['provenance']['source'].strip() or not isinstance(record['embedding_model'],str) or not 1<=len(record['embedding_model'])<=256:
                    raise ValueError()
                validate_vector(record['embedding']); _json(record['content']); _json(record['provenance'])
                stamp=datetime.fromisoformat(record['verified_at'])
                if stamp.tzinfo is None or stamp>datetime.now(timezone.utc): raise ValueError()
            parent=snapshot.pop('parent'); snapshot.pop('schema'); snapshot.pop('revision')
            snapshot['keys']=keys
            remaining(deadline)
            return snapshot,parent
        except (InvalidToken,ValueError,TypeError,KeyError,UnicodeError):
            raise SyncUnavailable('Remote memory verification failed; existing data is retained.') from None

    def _history(self,owner,head,parent,state,cipher,deadline):
        revision=head['revision']-1; total=0
        # shortcut: verify at most 128 ancestors/64 MiB; recover a trusted newer checkpoint for larger gaps.
        for _ in range(128):
            if revision==state['revision']:
                if parent!=state['identity']: raise SyncConflict('Remote history fork detected.')
                return
            body=self.provider.download(owner,parent,deadline=deadline,maximum=MAX_OBJECT)
            total+=len(body)
            if total>64*1024*1024 or sha256(body).hexdigest()!=parent: raise SyncUnavailable('History exceeds the verification budget.')
            try:
                ancestor=json.loads(cipher.decrypt(body))
                if ancestor['owner']!=owner or type(ancestor['schema']) is not int or ancestor['schema']!=1 or type(ancestor['revision']) is not int or ancestor['revision']!=revision or not valid_id(ancestor['parent'],64): raise ValueError()
                parent=ancestor['parent']; revision-=1
            except (InvalidToken,ValueError,TypeError,KeyError):
                raise SyncUnavailable('Remote history verification failed.') from None
            remaining(deadline)
        raise SyncUnavailable('Remote history gap requires a trusted recovery checkpoint.')

    def _apply(self,db,owner,snapshot):
        current=self._snapshot(db,owner)
        revoked=set(current['revoked'])|set(snapshot['revoked'])
        events=db.execute('SELECT COUNT(*) FROM events WHERE owner=?',(owner,)).fetchone()[0]
        additions=sum(not db.execute('SELECT 1 FROM events WHERE id=?',(identity,)).fetchone() for identity in snapshot['records'])
        if events+additions+2>4096:
            raise SyncUnavailable('Recovered history exceeds the bounded memory slice.')
        if set(snapshot['records']) & revoked:
            raise SyncConflict('A revoked memory cannot be restored from an older snapshot.')
        self.store._revoke(db,owner,sorted(set(current['records'])-set(snapshot['records'])))
        master=self.store._cipher(db)
        for identity,ciphertext in snapshot['records'].items():
            for table in ('memories','memory_keys','events'):
                row=db.execute('SELECT owner FROM '+table+' WHERE id=?',(identity,)).fetchone()
                if row and row[0]!=owner: raise SyncConflict('Memory identity belongs to another owner.')
            if identity in current['records'] and (ciphertext!=current['records'][identity] or snapshot['keys'][identity]!=current['keys'][identity]):
                raise SyncConflict('Immutable memory identity collision; existing data is retained.')
            indexed=db.execute('SELECT record FROM memories WHERE id=? AND owner=?',(identity,owner)).fetchone()
            if identity in current['records'] and indexed and indexed[0]==ciphertext.encode(): continue
            db.execute('INSERT INTO memory_keys VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET wrapped=excluded.wrapped',
                (identity,owner,master.encrypt(snapshot['keys'][identity].encode())))
            db.execute('INSERT OR IGNORE INTO events(id,owner,ciphertext) VALUES(?,?,?)',(identity,owner,ciphertext.encode()))
            db.execute('INSERT INTO memories VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET record=excluded.record', (identity,owner,ciphertext.encode()))
        unseen=sorted(revoked-set(current['revoked']))
        if unseen:
            db.execute('INSERT INTO events(id,owner,kind,ciphertext) VALUES(?,?,?,?)',(uuid4().hex,owner,'delete',master.encrypt(encoded({'kind':'delete','ids':unseen}))))
        db.execute('INSERT INTO owner_epochs VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET epoch=excluded.epoch',(owner,snapshot['epoch']))
        db.execute('INSERT INTO policies VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET encrypted=excluded.encrypted', (owner,master.encrypt(encoded({'days':snapshot['retention']}))))
        self.store._expire(db,owner)

    def run(self,user,*,seconds=5,recover=False):
        if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not 0<seconds<=5 or not isinstance(recover,bool):
            raise ValueError('Synchronization must have a positive bounded deadline.')
        owner=_owner(user); deadline=time.monotonic()+seconds
        with self.store._transaction(timeout=remaining(deadline)) as db:
            state=self.store._sync_state(db,owner)
            if not state['enabled']: return 'disabled'
            if state['retry_at']>time.time() and not recover: return 'queued'
            local=self._snapshot(db,owner); fingerprint=digest(local)
            dirty=state['pending'] or (state['ack'] is not None and state['ack']!=fingerprint) or (state['ack'] is None and bool(local['records'] or local['revoked'] or local['epoch'] or local['retention']!=30))
        try:
            cipher=self._key(owner)
            head=self.provider.head(owner,deadline=deadline)
            remote,parent=self._verify(owner,head,cipher,deadline) if head else (None,None)
            revision=head['revision'] if head else 0
            anchor=state if state['revision'] else state.get('recovery_checkpoint')
            # Lost publish responses already have identical authenticated local data.
            if remote and not anchor and not (state['pending'] and digest(remote)==fingerprint):
                raise SyncConflict('A fresh vault requires a trusted recovery checkpoint before cloud download.')
            if anchor and (revision<anchor['revision'] or (revision==anchor['revision'] and head and head['identity']!=anchor['identity'])):
                raise SyncConflict('Remote history rollback detected; trusted local data is retained.')
            if head and anchor and revision>anchor['revision']:
                self._history(owner,head,parent,anchor,cipher,deadline)
            if remote and revision>state['revision'] and digest(remote)==fingerprint:
                # A successful CAS with a lost response is acknowledged without duplicating it.
                with self.store._transaction(timeout=remaining(deadline)) as db:
                    latest=self.store._sync_state(db,owner)
                    if digest(self._snapshot(db,owner))!=fingerprint: raise SyncConflict('Local memory changed during acknowledgement.')
                    latest.update(revision=revision,identity=head['identity'],ack=fingerprint,pending=False,failures=0,retry_at=0,conflict=False)
                    self.store._write_sync_state(db,owner,latest)
                return 'current'
            if revision>state['revision'] and dirty and not recover:
                # Apply only authenticated revocations immediately, even during an edit conflict.
                with self.store._transaction(timeout=remaining(deadline)) as db:
                    revoked=set(local['records']) if remote['epoch']>local['epoch'] else set(local['records'])&set(remote['revoked'])
                    self.store._revoke(db,owner,sorted(revoked))
                    if remote['epoch']>local['epoch']:
                        db.execute('INSERT INTO owner_epochs VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET epoch=excluded.epoch',(owner,remote['epoch']))
                raise SyncConflict('Local and remote changes require explicit verified merge.')
            if remote and revision>state['revision'] and not dirty:
                with self.store._transaction(timeout=remaining(deadline)) as db:
                    latest=self.store._sync_state(db,owner)
                    if not latest['enabled']: raise SyncConflict('Synchronization consent changed during download.')
                    if digest(self._snapshot(db,owner))!=fingerprint: raise SyncConflict('Local memory changed during download.')
                    self._apply(db,owner,remote)
                    applied=digest(self._snapshot(db,owner))
                    latest.update(revision=revision,identity=head['identity'],ack=digest(remote),pending=applied!=digest(remote),failures=0,retry_at=0,conflict=False)
                    self.store._write_sync_state(db,owner,latest)
                return 'downloaded'
            if recover and remote:
                revoked=set(local['revoked'])|set(remote['revoked'])
                if local['epoch']==remote['epoch']:
                    for identity in set(local['records'])&set(remote['records']):
                        if local['records'][identity]!=remote['records'][identity] or local['keys'][identity]!=remote['keys'][identity]:
                            raise SyncConflict('Immutable memory identity collision.')
                    records={**remote['records'],**local['records']}; keys={**remote['keys'],**local['keys']}
                else:
                    newer=local if local['epoch']>remote['epoch'] else remote
                    older=remote if newer is local else local
                    revoked.update(older['records'])
                    records=dict(newer['records']); keys=dict(newer['keys'])
                local={'owner':owner,'epoch':max(local['epoch'],remote['epoch']),'retention':min(local['retention'],remote['retention']),
                    'records':{i:v for i,v in records.items() if i not in revoked},'keys':{i:v for i,v in keys.items() if i not in revoked},'revoked':sorted(revoked)}
                dirty=True
            if not dirty and head: return 'current'
            if len(local['records'])>512 or len(local['revoked'])>4096:
                raise SyncUnavailable('Merged snapshot exceeds the bounded memory slice.')
            payload={k:v for k,v in local.items() if k!='keys'}
            payload.update(schema=1,revision=revision+1,parent=head['identity'] if head else None)
            ciphertext=cipher.encrypt(encoded(payload))
            # shortcut: 32 MiB encrypted snapshots; add bounded encrypted chunks before increasing this cap.
            if len(ciphertext)>MAX_OBJECT: raise SyncUnavailable('Encrypted snapshot exceeds the upload budget.')
            identity=sha256(ciphertext).hexdigest()
            manifest=cipher.encrypt(encoded({'owner':owner,'revision':revision+1,'identity':identity,'keys':local['keys']}))
            with self.store._transaction(timeout=remaining(deadline)) as db:
                latest=self.store._sync_state(db,owner)
                if not latest['enabled'] or digest(self._snapshot(db,owner))!=fingerprint:
                    raise SyncConflict('Local memory or consent changed before upload.')
            published=self.provider.publish(owner,revision,identity,ciphertext,manifest,deadline=deadline)
            with self.store._transaction(timeout=remaining(deadline)) as db:
                latest=self.store._sync_state(db,owner)
                changed=digest(self._snapshot(db,owner))!=fingerprint
                if recover and not changed: self._apply(db,owner,local)
                applied=digest(self._snapshot(db,owner))
                latest.update(revision=published['revision'],identity=identity,ack=digest(local),
                    pending=changed or applied!=digest(local),failures=0,retry_at=0,conflict=False)
                self.store._write_sync_state(db,owner,latest)
            return 'uploaded'
        except Exception as exc:
            with self.store._transaction(timeout=max(0.001,min(deadline-time.monotonic(),0.1))) as db:
                latest=self.store._sync_state(db,owner)
                latest.update(pending=True,failures=min(latest['failures']+1,16),retry_at=time.time()+min(300,2**min(latest['failures'],8)),conflict=isinstance(exc,SyncConflict))
                self.store._write_sync_state(db,owner,latest)
            if isinstance(exc,SyncConflict): raise
            raise SyncUnavailable('Memory synchronization is unavailable; encrypted local updates remain queued.') from None
