"""Bounded public HTTPS transport. No ambient proxy, cookies, credentials or redirects.

Connect to the validated IP, retaining the original TLS SNI/hostname check. This
avoids the validate-then-resolve-again DNS rebinding gap. Never include upstream
URLs, response bodies or exception strings in an error returned to callers.
"""
from dataclasses import dataclass
import hashlib
import ipaddress
import json
import ssl
from time import monotonic
from urllib.parse import urlencode, urlsplit, urlunsplit

import urllib3

from .url_safety import BLOCKED_HOSTNAMES, _resolve_host_ips


class PublicHTTPError(Exception):
    def __init__(self, code, retry_after=60):
        self.code = code
        self.retry_after = retry_after
        super().__init__(code)


@dataclass(frozen=True)
class PublicResponse:
    content: bytes
    content_type: str

    @property
    def response_hash(self):
        return hashlib.sha256(self.content).hexdigest()

    def json(self):
        return json.loads(self.content)


def normalized_link(raw_url):
    """Syntactic link validation, with no DNS calls while rendering saved plans.

Server fetches additionally validate DNS and pin the socket target below.
"""
    if not isinstance(raw_url, str) or len(raw_url) > 2048:
        return ""
    url = raw_url.strip()
    if any(ord(c) <= 32 or ord(c) == 127 for c in url) or "\\" in url:
        return ""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").encode("idna").decode("ascii").lower()
        if parts.scheme.lower() != "https" or not host or parts.username is not None or parts.password is not None:
            return ""
        if parts.port not in (None, 443) or host in BLOCKED_HOSTNAMES or "." not in host or host.endswith((".localhost", ".local", ".internal")):
            return ""
        try:
            if not ipaddress.ip_address(host).is_global:
                return ""
        except ValueError:
            pass
        return urlunsplit(("https", host, parts.path or "/", parts.query, parts.fragment))
    except (ValueError, UnicodeError):
        return ""


def request(method, url, *, params=None, headers=None, json_body=None, data=None,
            content_types=("application/json", "application/geo+json", "application/sparql-results+json"),
            max_bytes=4_000_000):
    safe = normalized_link(url)
    if not safe or urlsplit(safe).fragment or method not in {"GET", "POST"}:
        raise PublicHTTPError("unsafe_url")
    parts = urlsplit(safe)
    try:
        addresses = _resolve_host_ips(parts.hostname, 443)
        if not addresses or any(not a.is_global for a in addresses):
            raise ValueError()
    except (ValueError, OSError):
        raise PublicHTTPError("unsafe_url") from None
    query = parts.query
    if params:
        query += ("&" if query else "") + urlencode(params, doseq=True)
    target = urlunsplit(("", "", parts.path or "/", query, ""))
    outgoing = {"User-Agent": "ALFRED-travel/1.2 (+https://github.com/sourabh48/alfred_ai)",
                "Accept": ", ".join(content_types), "Accept-Encoding": "identity"}
    outgoing.update(headers or {})
    # Caller cannot change the peer, connection behavior or compression limits.
    for key in list(outgoing):
        if key.lower() in {"host", "connection", "accept-encoding", "cookie", "proxy-authorization"}:
            del outgoing[key]
    outgoing.update({"Host": parts.hostname, "Accept-Encoding": "identity", "Connection": "close"})
    body = None
    if json_body is not None:
        body = json.dumps(json_body, allow_nan=False).encode("utf-8")
        outgoing["Content-Type"] = "application/json"
    elif data is not None:
        body = urlencode(data).encode("utf-8") if isinstance(data, dict) else data
        outgoing["Content-Type"] = "application/x-www-form-urlencoded"
    pool = urllib3.HTTPSConnectionPool(str(addresses[0]), port=443, server_hostname=parts.hostname,
        assert_hostname=parts.hostname, ssl_context=ssl.create_default_context(),
        timeout=urllib3.Timeout(connect=5, read=5, total=20), maxsize=1, retries=False)
    response = None
    started = monotonic()
    try:
        response = pool.urlopen(method, target, body=body, headers=outgoing, redirect=False,
                                retries=False, preload_content=False, assert_same_host=False)
        if response.status == 429:
            retry = str(response.headers.get("Retry-After", "60"))
            raise PublicHTTPError("quota_exhausted", min(int(retry), 86400) if retry.isdigit() else 60)
        if response.status in (401, 403):
            raise PublicHTTPError("authorization_failed", 3600)
        if 300 <= response.status < 400:
            # No second request, even for same-origin redirects. Never forward a key.
            raise PublicHTTPError("redirect_blocked")
        if response.status not in (200, 201):
            raise PublicHTTPError("api_error")
        mime = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if mime not in content_types:
            raise PublicHTTPError("unexpected_content_type")
        encoding = response.headers.get("Content-Encoding", "identity").lower()
        if encoding not in {"", "identity"}:
            # Refuse unsolicited compression, including decompression bombs.
            raise PublicHTTPError("unexpected_content_encoding")
        length = response.headers.get("Content-Length", "")
        if length and (not length.isdigit() or int(length) > max_bytes):
            raise PublicHTTPError("response_too_large")
        chunks, count = [], 0
        while True:
            chunk = response.read(min(65536, max_bytes-count+1), decode_content=False)
            if monotonic()-started > 20:
                raise PublicHTTPError("timeout")
            if not chunk:
                break
            count += len(chunk)
            if count > max_bytes:
                raise PublicHTTPError("response_too_large")
            chunks.append(chunk)
        return PublicResponse(b"".join(chunks), mime)
    except urllib3.exceptions.TimeoutError:
        raise PublicHTTPError("timeout") from None
    except (urllib3.exceptions.HTTPError, OSError):
        raise PublicHTTPError("network_error") from None
    finally:
        if response is not None:
            response.close()
        pool.close()
