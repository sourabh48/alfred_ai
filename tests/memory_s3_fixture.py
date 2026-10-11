"""Synthetic signed S3 wire fixture; stores ciphertext only and never uses a network."""
from contextlib import closing
from datetime import datetime, timezone
import hmac
from hashlib import sha256
import json
import sqlite3
import time
from urllib.parse import urlsplit, parse_qs

from alfred_ai.services.public_http import PublicResponse
from apps.ml_engine.services.memory_cloud import signed_headers

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
