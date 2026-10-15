"""Historical S3 protocol quarantine: synthetic ciphertext tests only, no network transport.

AWS was removed from application runtime; keep its old CAS regressions here while
a separately approved non-AWS adapter is developed. This is not a live provider.
"""
from contextlib import closing
from datetime import datetime, timezone
import hmac
from hashlib import sha256
import json
import sqlite3
import time
from urllib.parse import urlsplit, parse_qs

from alfred_ai.services.public_http import PublicResponse
import base64
import re
from urllib.parse import quote, urlencode, parse_qsl
from xml.etree import ElementTree as ET
from apps.ml_engine.services.memory_sync import MAX_HEAD, MAX_OBJECT, SyncConflict, SyncUnavailable, encoded, remaining, valid_id


def request(*args, **kwargs):
    raise AssertionError('Historical S3 fixture has no network transport; use the synthetic wire only.')

# Public AWS documentation example, never an ALFRED credential.
PROFILE={'bucket':'synthetic-memory-bucket','region':'us-east-1','account':'123456789012',
    'access_key':'AKIAIOSFODNN7EXAMPLE','secret_key':'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY','session_token':''}


class SignedS3Fixture:
    def __init__(self,database):
        self.database=database; self.calls=0; self.offline=False; self.version=''; self.public=True; self.ownership='BucketOwnerEnforced'
        self.fail_head_once=False; self.lose_ack_once=False; self.partial=False; self.before_head=None
        with closing(sqlite3.connect(database)) as db:
            db.execute('CREATE TABLE IF NOT EXISTS wire_objects(key TEXT PRIMARY KEY,body BLOB,etag TEXT,created REAL)')

    def request(self,method,url,*,headers,data=None,**kwargs):
        self.calls+=1
        if self.offline: raise OSError('SYNTHETIC-NETWORK-SECRET')
        body=data or b''; outgoing={k.lower():v for k,v in headers.items()}
        stamp=datetime.strptime(outgoing['x-amz-date'],'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        selected={k:outgoing[k] for k in outgoing['authorization'].split('SignedHeaders=')[1].split(',')[0].split(';')}
        expected=signed_headers(method,url,body,PROFILE,selected,now=stamp)['Authorization']
        if not hmac.compare_digest(expected,outgoing['authorization']) or outgoing.get('x-amz-expected-bucket-owner')!=PROFILE['account']:
            return PublicResponse(b'<Error/>','application/xml',403)
        parts=urlsplit(url); query=parse_qs(parts.query,keep_blank_values=True); key=parts.path.lstrip('/')
        if not key and method=='GET':
            if 'versioning' in query: xml='<VersioningConfiguration>'+('<Status>'+self.version+'</Status>' if self.version else '')+'</VersioningConfiguration>'
            elif 'publicAccessBlock' in query: xml='<PublicAccessBlockConfiguration>'+''.join('<'+k+'>'+str(self.public).lower()+'</'+k+'>' for k in ('BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets'))+'</PublicAccessBlockConfiguration>'
            elif 'ownershipControls' in query: xml='<OwnershipControls><Rule><ObjectOwnership>'+self.ownership+'</ObjectOwnership></Rule></OwnershipControls>'
            else:
                prefix=query['prefix'][0]
                with closing(sqlite3.connect(self.database)) as db: rows=db.execute('SELECT key,created FROM wire_objects WHERE key LIKE ?',(prefix+'%',)).fetchall()
                xml='<ListBucketResult><IsTruncated>false</IsTruncated>'+''.join('<Contents><Key>'+k+'</Key><LastModified>'+datetime.fromtimestamp(t,timezone.utc).isoformat()+'</LastModified></Contents>' for k,t in rows)+'</ListBucketResult>'
            return PublicResponse(xml.encode(),'application/xml')
        if '/snapshots/' not in key and not key.endswith('/head'): raise AssertionError('Unexpected synthetic cloud object')
        with closing(sqlite3.connect(self.database)) as db:
            db.execute('BEGIN IMMEDIATE'); row=db.execute('SELECT body,etag FROM wire_objects WHERE key=?',(key,)).fetchone()
            if method=='GET':
                if not row: return PublicResponse(b'<Error/>','application/xml',404)
                return PublicResponse(row[0][:-1] if self.partial else row[0],'application/octet-stream',200,{'ETag':row[1]})
            if method=='DELETE':
                db.execute('DELETE FROM wire_objects WHERE key=?',(key,)); db.commit()
                return PublicResponse(b'','',204)
            assert outgoing['x-amz-server-side-encryption']=='AES256' and outgoing['content-type']=='application/octet-stream'
            if key.endswith('/head') and self.fail_head_once:
                self.fail_head_once=False; raise OSError('SYNTHETIC-INTERRUPTION')
            if key.endswith('/head') and self.before_head:
                self.before_head(); return PublicResponse(b'<Error/>','application/xml',412)
            if (outgoing.get('if-none-match')=='*' and row) or ('if-match' in outgoing and (not row or row[1]!=outgoing['if-match'])):
                return PublicResponse(b'<Error/>','application/xml',412)
            etag='"'+sha256(body).hexdigest()+'"'
            db.execute('INSERT INTO wire_objects VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET body=excluded.body,etag=excluded.etag,created=excluded.created',(key,body,etag,time.time())); db.commit()
            if key.endswith('/head') and self.lose_ack_once:
                self.lose_ack_once=False; raise OSError('SYNTHETIC-LOST-ACK')
            return PublicResponse(b'','',200,{'ETag':etag})


def signed_headers(method,url,data,profile,headers=None,*,now=None):
    """AWS Signature V4, tested against AWS's published GET example."""
    parts=urlsplit(url); now=now or datetime.now(timezone.utc)
    stamp=now.strftime('%Y%m%dT%H%M%SZ'); date=stamp[:8]
    outgoing={k.lower():' '.join(str(v).split()) for k,v in (headers or {}).items()}
    outgoing.update(host=parts.hostname,**{'x-amz-date':stamp,'x-amz-content-sha256':sha256(data).hexdigest()})
    if profile.get('session_token'): outgoing['x-amz-security-token']=profile['session_token']
    names=';'.join(sorted(outgoing)); canonical_headers=''.join(k+':'+outgoing[k]+'\n' for k in sorted(outgoing))
    query='&'.join(quote(k,safe='-_.~')+'='+quote(v,safe='-_.~') for k,v in sorted(parse_qsl(parts.query,keep_blank_values=True)))
    canonical='\n'.join((method,parts.path or '/',query,canonical_headers,names,outgoing['x-amz-content-sha256']))
    scope='/'.join((date,profile['region'],'s3','aws4_request'))
    message='\n'.join(('AWS4-HMAC-SHA256',stamp,scope,sha256(canonical.encode()).hexdigest()))
    key=('AWS4'+profile['secret_key']).encode()
    for component in (date,profile['region'],'s3','aws4_request'): key=hmac.new(key,component.encode(),'sha256').digest()
    signature=hmac.new(key,message.encode(),'sha256').hexdigest()
    outgoing['Authorization']=f"AWS4-HMAC-SHA256 Credential={profile['access_key']}/{scope}, SignedHeaders={names}, Signature={signature}"
    return outgoing


def validate_profile(profile):
    fields={'bucket','region','account','access_key','secret_key','session_token'}
    if not isinstance(profile,dict) or set(profile)!=fields: raise ValueError('A complete restricted S3 profile is required.')
    if any(not isinstance(v,str) or len(v)>4096 or any(ord(c)<33 or ord(c)>126 for c in v) for k,v in profile.items() if k!='session_token'):
        raise ValueError('Invalid S3 configuration.')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{1,61}[a-z0-9]',profile['bucket']) or profile['bucket'].startswith(('xn--','sthree-','amzn-s3-demo-')) or profile['bucket'].endswith(('-s3alias','--ol-s3','--x-s3','--table-s3')):
        raise ValueError('Use an ordinary private S3 bucket without dots or aliases.')
    if not re.fullmatch(r'(us|eu|ap|ca|sa|af|me|il|mx)-[a-z]+-\d',profile['region']) or not re.fullmatch(r'\d{12}',profile['account']):
        raise ValueError('A supported AWS region and expected bucket account are required.')
    if not re.fullmatch('[A-Z0-9]{16,128}',profile['access_key']) or len(profile['secret_key'])<32 or len(profile['secret_key'])>128:
        raise ValueError('Restricted S3 credentials are required.')
    token=profile['session_token']
    if not isinstance(token,str) or len(token)>4096 or any(ord(c)<33 or ord(c)>126 for c in token): raise ValueError('Invalid temporary credential token.')
    return dict(profile)


class LegacyS3FixtureProvider:
    name='s3'
    def __init__(self,owner,profile):
        if not valid_id(owner,64): raise PermissionError('Invalid cloud owner.')
        self.owner=owner; self.profile=validate_profile(profile); self.checked=False
        self.base=f"https://{self.profile['bucket']}.s3.{self.profile['region']}.amazonaws.com"
        self.prefix='alfred-memory-v1/'+owner+'/'
        self.etag=None

    def _send(self,method,key='',*,query=None,data=b'',headers=None,deadline,maximum=MAX_OBJECT,statuses=(200,201)):
        remaining(deadline)
        url=self.base+'/'+key+('?' + urlencode(query,quote_via=quote) if query is not None else '')
        headers={'x-amz-expected-bucket-owner':self.profile['account'],**(headers or {})}
        if method=='PUT': headers.update({'content-type':'application/octet-stream','x-amz-server-side-encryption':'AES256'})
        return request(method,url,headers=signed_headers(method,url,data,self.profile,headers),data=data if method=='PUT' else None,
            content_types=('application/octet-stream','application/xml','text/xml','application/json',''),
            accepted_statuses=statuses,max_bytes=maximum,deadline=deadline)

    def _scope(self,owner,deadline):
        if owner!=self.owner: raise PermissionError('Cloud access is owner-scoped.')
        if self.checked: return
        responses=[]
        for flag in ('versioning','publicAccessBlock','ownershipControls'):
            body=self._send('GET',query={flag:''},deadline=deadline,maximum=16384).content
            if b'<!' in body: raise SyncUnavailable('Unsafe bucket configuration response.')
            try:
                root=ET.fromstring(body)
                expected={'versioning':'VersioningConfiguration','publicAccessBlock':'PublicAccessBlockConfiguration','ownershipControls':'OwnershipControls'}[flag]
                if root.tag.rsplit('}',1)[-1]!=expected: raise ET.ParseError()
                responses.append({node.tag.rsplit('}',1)[-1]:node.text or '' for node in root.iter()})
            except ET.ParseError: raise SyncUnavailable('Invalid bucket configuration response.') from None
        version,public,ownership=responses
        if version.get('Status') or any(public.get(k)!='true' for k in ('BlockPublicAcls','IgnorePublicAcls','BlockPublicPolicy','RestrictPublicBuckets')) or ownership.get('ObjectOwnership')!='BucketOwnerEnforced':
            raise SyncUnavailable('A private owner-enforced bucket with no key-manifest version history is required.')
        self.checked=True

    def head(self,owner,*,deadline):
        self._scope(owner,deadline)
        response=self._send('GET',self.prefix+'head',deadline=deadline,maximum=MAX_HEAD*2,statuses=(200,404))
        self.etag=response.headers.get('ETag')
        if response.status==404: self.etag=None; return None
        if not isinstance(self.etag,str) or not re.fullmatch('"[a-zA-Z0-9-]{1,128}"',self.etag): raise SyncUnavailable('Missing cloud concurrency token.')
        try:
            packet=response.json()
            if set(packet)!= {'revision','identity','manifest'} or type(packet['revision']) is not int or packet['revision']<1 or not valid_id(packet['identity'],64): raise ValueError()
            manifest=base64.b64decode(packet['manifest'],validate=True)
            if len(manifest)>MAX_HEAD: raise ValueError()
        except (ValueError,TypeError,KeyError): raise SyncUnavailable('Invalid encrypted cloud head.') from None
        return packet|{'manifest':manifest}

    def download(self,owner,identity,*,deadline,maximum=MAX_OBJECT):
        self._scope(owner,deadline)
        if not valid_id(identity,64) or not 0<maximum<=MAX_OBJECT: raise SyncUnavailable('Invalid encrypted snapshot reference.')
        content=self._send('GET',self.prefix+'snapshots/'+identity,deadline=deadline,maximum=maximum).content
        if sha256(content).hexdigest()!=identity: raise SyncUnavailable('Encrypted snapshot integrity failed.')
        return content

    def publish(self,owner,expected_revision,identity,ciphertext,manifest,*,deadline):
        self._scope(owner,deadline)
        if type(expected_revision) is not int or expected_revision<0 or not valid_id(identity,64) or sha256(ciphertext).hexdigest()!=identity or len(ciphertext)>MAX_OBJECT or len(manifest)>MAX_HEAD:
            raise SyncUnavailable('Invalid bounded encrypted publication.')
        head=self.head(owner,deadline=deadline)
        if (head['revision'] if head else 0)!=expected_revision: raise SyncConflict('Concurrent cloud changes require verified recovery.')
        etag=self.etag
        response=self._send('PUT',self.prefix+'snapshots/'+identity,data=ciphertext,headers={'if-none-match':'*'},deadline=deadline,maximum=16384,statuses=(200,409,412))
        if response.status==409: raise SyncConflict('Concurrent encrypted object publication; retry safely.')
        if response.status==412: self.download(owner,identity,deadline=deadline)
        packet={'revision':expected_revision+1,'identity':identity,'manifest':base64.b64encode(manifest).decode('ascii')}
        condition={'if-match':etag} if head else {'if-none-match':'*'}
        response=self._send('PUT',self.prefix+'head',data=encoded(packet),headers=condition,deadline=deadline,maximum=16384,statuses=(200,409,412))
        if response.status in (409,412): raise SyncConflict('Concurrent cloud head publication; local updates remain queued.')
        return packet|{'manifest':manifest}

    def snapshots(self,owner,*,deadline):
        self._scope(owner,deadline); token=None; result=[]
        for _ in range(4):
            query={'list-type':'2','prefix':self.prefix+'snapshots/','max-keys':'1000'}
            if token: query['continuation-token']=token
            body=self._send('GET',query=query,deadline=deadline,maximum=512*1024).content
            if b'<!' in body: raise SyncUnavailable('Invalid snapshot listing.')
            root=ET.fromstring(body); tag=lambda name:'{'+root.tag.split('}')[0][1:]+'}'+name if root.tag.startswith('{') else name
            for row in root.findall(tag('Contents')):
                key=row.findtext(tag('Key')) or ''; identity=key.removeprefix(self.prefix+'snapshots/')
                if not valid_id(identity,64): raise SyncUnavailable('Invalid scoped snapshot listing.')
                when=datetime.fromisoformat(row.findtext(tag('LastModified')).replace('Z','+00:00'))
                if when.tzinfo is None: raise SyncUnavailable('Invalid snapshot timestamp.')
                result.append((identity,when.timestamp()))
            if root.findtext(tag('IsTruncated'))=='false': return result
            token=root.findtext(tag('NextContinuationToken'))
            if not token: break
        raise SyncUnavailable('Snapshot listing exceeds the bounded retention pass.')

    def remove_snapshot(self,owner,identity,*,deadline):
        self._scope(owner,deadline)
        if not valid_id(identity,64): raise PermissionError('Invalid snapshot removal scope.')
        self._send('DELETE',self.prefix+'snapshots/'+identity,deadline=deadline,maximum=16384,statuses=(204,))


