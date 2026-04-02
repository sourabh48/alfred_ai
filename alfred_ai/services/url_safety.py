from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "host.docker.internal",
}
ALLOWED_SCHEMES = {"http", "https"}


def validate_public_http_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    hostname = (parsed.hostname or "").strip().lower()

    if scheme not in ALLOWED_SCHEMES:
        raise ValueError("Only public HTTP(S) URLs are allowed.")
    if not hostname:
        raise ValueError("A valid URL host is required.")
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise ValueError("Local or internal hosts are not allowed.")

    resolved_ips = _resolve_host_ips(hostname, parsed.port)
    for address in resolved_ips:
        if not address.is_global:
            raise ValueError("Private, loopback, link-local, and internal IP targets are not allowed.")

    return url


def _resolve_host_ips(hostname: str, port: int | None) -> list[ipaddress._BaseAddress]:
    try:
        return [ipaddress.ip_address(hostname)]
    except ValueError:
        pass

    try:
        records = socket.getaddrinfo(hostname, port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("URL host could not be resolved safely.") from exc

    addresses: list[ipaddress._BaseAddress] = []
    for record in records:
        sockaddr = record[4]
        if not sockaddr:
            continue
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue

    if not addresses:
        raise ValueError("URL host could not be resolved safely.")
    return addresses
