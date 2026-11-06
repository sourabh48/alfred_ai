"""SYNC-02: Cloudflare R2 provider for encrypted memory sync (owner approved cloud sync 2026-11-06).

Only ciphertext leaves the PC: MemorySynchronizer encrypts every snapshot and manifest
with the owner's local key before publish. The endpoint is built from the R2 account id,
never taken from configuration, so sync cannot be pointed at another host. Requests use
the S3 API with Signature V4 and conditional writes (If-None-Match / If-Match) for the
provider contract's immutable objects and atomic head compare-and-swap.
"""
import base64
from datetime import datetime, timezone
from hashlib import sha256
import hmac
import re
from urllib.parse import parse_qsl, quote, urlencode, urlsplit
from xml.etree import ElementTree as ET

from django.conf import settings

from alfred_ai.services.public_http import PublicHTTPError, request
from .memory_sync import MAX_HEAD, MAX_OBJECT, SyncConflict, SyncUnavailable, encoded, remaining, valid_id

REGION = 'auto'
PROFILE_FIELDS = ('account_id', 'bucket', 'access_key', 'secret_key', 'jurisdiction')


def signed_headers(method, url, data, profile, headers=None, *, now=None):
    """S3 Signature V4, checked against AWS's published GET example (R2 uses the same scheme)."""
    parts = urlsplit(url); now = now or datetime.now(timezone.utc)
    stamp = now.strftime('%Y%m%dT%H%M%SZ'); date = stamp[:8]
    outgoing = {k.lower(): ' '.join(str(v).split()) for k, v in (headers or {}).items()}
    outgoing.update(host=parts.hostname, **{'x-amz-date': stamp, 'x-amz-content-sha256': sha256(data).hexdigest()})
    if profile.get('session_token'): outgoing['x-amz-security-token'] = profile['session_token']
    names = ';'.join(sorted(outgoing)); canonical_headers = ''.join(k + ':' + outgoing[k] + '\n' for k in sorted(outgoing))
    query = '&'.join(quote(k, safe='-_.~') + '=' + quote(v, safe='-_.~') for k, v in sorted(parse_qsl(parts.query, keep_blank_values=True)))
    canonical = '\n'.join((method, parts.path or '/', query, canonical_headers, names, outgoing['x-amz-content-sha256']))
    scope = '/'.join((date, profile['region'], 's3', 'aws4_request'))
    message = '\n'.join(('AWS4-HMAC-SHA256', stamp, scope, sha256(canonical.encode()).hexdigest()))
    key = ('AWS4' + profile['secret_key']).encode()
    for component in (date, profile['region'], 's3', 'aws4_request'): key = hmac.new(key, component.encode(), 'sha256').digest()
    signature = hmac.new(key, message.encode(), 'sha256').hexdigest()
    outgoing['Authorization'] = f"AWS4-HMAC-SHA256 Credential={profile['access_key']}/{scope}, SignedHeaders={names}, Signature={signature}"
    return outgoing


def validate_profile(profile):
    if not isinstance(profile, dict) or set(profile) != set(PROFILE_FIELDS) or not all(isinstance(v, str) for v in profile.values()):
        raise ValueError('A complete R2 profile is required.')
    if not re.fullmatch('[a-f0-9]{32}', profile['account_id']):
        raise ValueError('The R2 account id is 32 lowercase hexadecimal characters.')
    if not re.fullmatch('[a-z0-9][a-z0-9-]{1,61}[a-z0-9]', profile['bucket']):
        raise ValueError('Use a plain R2 bucket name: lowercase letters, digits and hyphens.')
    if not re.fullmatch('[A-Za-z0-9]{16,128}', profile['access_key']) or not re.fullmatch('[\x21-\x7e]{32,128}', profile['secret_key']):
        raise ValueError('A restricted R2 API token key pair is required.')
    if profile['jurisdiction'] not in ('', 'eu'):
        raise ValueError('Leave the R2 jurisdiction empty, or use eu.')
    return dict(profile, region=REGION)


def configured_profile():
    """The owner's R2 settings from config/local.env, or None when incomplete or invalid."""
    profile = {name: getattr(settings, 'ALFRED_MEMORY_R2_' + name.upper(), '') or '' for name in PROFILE_FIELDS}
    try:
        return validate_profile(profile)
    except ValueError:
        return None


class R2MemoryProvider:
    name = 'r2'

    def __init__(self, owner, profile):
        if not valid_id(owner, 64): raise PermissionError('Invalid cloud owner.')
        self.owner = owner; self.profile = validate_profile({k: profile[k] for k in PROFILE_FIELDS}); self.checked = False
        host = self.profile['account_id'] + ('.eu' if self.profile['jurisdiction'] else '') + '.r2.cloudflarestorage.com'
        self.base = f"https://{host}/{self.profile['bucket']}"
        self.prefix = 'alfred-memory-v1/' + owner + '/'
        self.etag = None

    def _send(self, method, key='', *, query=None, data=b'', headers=None, deadline, maximum=MAX_OBJECT, statuses=(200,)):
        remaining(deadline)
        url = self.base + ('/' + key if key else '') + ('?' + urlencode(query, quote_via=quote) if query is not None else '')
        headers = dict(headers or {})
        if method == 'PUT': headers['content-type'] = 'application/octet-stream'
        try:
            return request(method, url, headers=signed_headers(method, url, data, self.profile, headers), data=data if method == 'PUT' else None,
                content_types=('application/octet-stream', 'application/xml', 'text/xml', 'application/json', ''),
                accepted_statuses=statuses, max_bytes=maximum, deadline=deadline)
        except PublicHTTPError as error:  # codes are fixed words such as authorization_failed; never credentials
            raise SyncUnavailable(f'Cloud storage refused or failed the request ({error.code}); local data is retained.') from None
        except OSError:
            raise SyncUnavailable('Cloud storage is unreachable; local updates stay queued.') from None

    def _scope(self, owner, deadline):
        if owner != self.owner: raise PermissionError('Cloud access is owner-scoped.')
        if not self.checked:  # one signed listing proves the token can reach this bucket before any upload
            self._list(deadline, max_keys='1')
            self.checked = True

    def _list(self, deadline, *, max_keys='1000', token=None):
        query = {'list-type': '2', 'prefix': self.prefix + 'snapshots/', 'max-keys': max_keys}
        if token: query['continuation-token'] = token
        body = self._send('GET', query=query, deadline=deadline, maximum=512 * 1024).content
        if b'<!' in body: raise SyncUnavailable('Invalid snapshot listing.')
        try:
            return ET.fromstring(body)
        except ET.ParseError:
            raise SyncUnavailable('Invalid snapshot listing.') from None

    def head(self, owner, *, deadline):
        self._scope(owner, deadline)
        response = self._send('GET', self.prefix + 'head', deadline=deadline, maximum=MAX_HEAD * 2, statuses=(200, 404))
        self.etag = response.headers.get('ETag')
        if response.status == 404: self.etag = None; return None
        if not isinstance(self.etag, str) or not re.fullmatch('"[a-zA-Z0-9-]{1,128}"', self.etag): raise SyncUnavailable('Missing cloud concurrency token.')
        try:
            packet = response.json()
            if set(packet) != {'revision', 'identity', 'manifest'} or type(packet['revision']) is not int or packet['revision'] < 1 or not valid_id(packet['identity'], 64): raise ValueError()
            manifest = base64.b64decode(packet['manifest'], validate=True)
            if len(manifest) > MAX_HEAD: raise ValueError()
        except (ValueError, TypeError, KeyError): raise SyncUnavailable('Invalid encrypted cloud head.') from None
        return packet | {'manifest': manifest}

    def download(self, owner, identity, *, deadline, maximum=MAX_OBJECT):
        self._scope(owner, deadline)
        if not valid_id(identity, 64) or not 0 < maximum <= MAX_OBJECT: raise SyncUnavailable('Invalid encrypted snapshot reference.')
        content = self._send('GET', self.prefix + 'snapshots/' + identity, deadline=deadline, maximum=maximum).content
        if sha256(content).hexdigest() != identity: raise SyncUnavailable('Encrypted snapshot integrity failed.')
        return content

    def publish(self, owner, expected_revision, identity, ciphertext, manifest, *, deadline):
        self._scope(owner, deadline)
        if type(expected_revision) is not int or expected_revision < 0 or not valid_id(identity, 64) or sha256(ciphertext).hexdigest() != identity or len(ciphertext) > MAX_OBJECT or len(manifest) > MAX_HEAD:
            raise SyncUnavailable('Invalid bounded encrypted publication.')
        head = self.head(owner, deadline=deadline)
        if (head['revision'] if head else 0) != expected_revision: raise SyncConflict('Concurrent cloud changes require verified recovery.')
        etag = self.etag
        response = self._send('PUT', self.prefix + 'snapshots/' + identity, data=ciphertext, headers={'if-none-match': '*'}, deadline=deadline, maximum=16384, statuses=(200, 409, 412))
        if response.status == 409: raise SyncConflict('Concurrent encrypted object publication; retry safely.')
        if response.status == 412: self.download(owner, identity, deadline=deadline)  # already stored: verify, never overwrite
        packet = {'revision': expected_revision + 1, 'identity': identity, 'manifest': base64.b64encode(manifest).decode('ascii')}
        condition = {'if-match': etag} if head else {'if-none-match': '*'}
        response = self._send('PUT', self.prefix + 'head', data=encoded(packet), headers=condition, deadline=deadline, maximum=16384, statuses=(200, 409, 412))
        if response.status in (409, 412): raise SyncConflict('Concurrent cloud head publication; local updates remain queued.')
        return packet | {'manifest': manifest}

    def snapshots(self, owner, *, deadline):
        self._scope(owner, deadline); token = None; result = []
        for _ in range(4):
            root = self._list(deadline, token=token)
            tag = lambda name: '{' + root.tag.split('}')[0][1:] + '}' + name if root.tag.startswith('{') else name
            for row in root.findall(tag('Contents')):
                key = row.findtext(tag('Key')) or ''; identity = key.removeprefix(self.prefix + 'snapshots/')
                if not valid_id(identity, 64): raise SyncUnavailable('Invalid scoped snapshot listing.')
                try:
                    when = datetime.fromisoformat((row.findtext(tag('LastModified')) or '').replace('Z', '+00:00'))
                except ValueError:
                    raise SyncUnavailable('Invalid snapshot timestamp.') from None
                if when.tzinfo is None: raise SyncUnavailable('Invalid snapshot timestamp.')
                result.append((identity, when.timestamp()))
            if root.findtext(tag('IsTruncated')) == 'false': return result
            token = root.findtext(tag('NextContinuationToken'))
            if not token: break
        raise SyncUnavailable('Snapshot listing exceeds the bounded retention pass.')

    def remove_snapshot(self, owner, identity, *, deadline):
        self._scope(owner, deadline)
        if not valid_id(identity, 64): raise PermissionError('Invalid snapshot removal scope.')
        self._send('DELETE', self.prefix + 'snapshots/' + identity, deadline=deadline, maximum=16384, statuses=(204,))
