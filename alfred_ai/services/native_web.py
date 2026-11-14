"""Bind the local listener exclusively before starting Waitress threads."""
import ipaddress
import os
import socket


# Home-network ranges only: Python's is_private also admits documentation and reserved blocks.
HOME_NETWORKS = tuple(ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fd00::/8"))


def home_network_client(address):
    """This PC or a private home-network address; never a public, link-local or unparseable one."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return ip.is_loopback or any(ip in network for network in HOME_NETWORKS)


def lan_addresses():
    """This PC's private IPv4 addresses, read at start; a new Wi-Fi address needs an ALFRED restart."""
    try:
        found = {info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    except OSError:
        return []
    return sorted(a for a in found if home_network_client(a) and not ipaddress.ip_address(a).is_loopback)


def private_clients_only(application):
    def guarded(environ, start_response):
        if home_network_client(environ.get("REMOTE_ADDR", "")):
            return application(environ, start_response)
        start_response("403 Forbidden", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"ALFRED only answers this PC and your home network."]
    return guarded


def create_native_server(application, port):
    from django.conf import settings
    from waitress import create_server
    from .upload_limits import limit, validate_limits

    validate_limits()
    # RUNTIME-15: home Wi-Fi access is opt-in (ALFRED_LAN_ACCESS in config/local.env); this PC only otherwise.
    lan = getattr(settings, "ALFRED_LAN_ACCESS", False)
    if lan:
        application = private_clients_only(application)

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("0.0.0.0" if lan else "127.0.0.1", port))
        listener.listen(128)
        return create_server(application, sockets=[listener], threads=4,
                             max_request_body_size=limit("ALFRED_UPLOAD_REQUEST_BYTES") + 1,
                             connection_limit=limit("ALFRED_UPLOAD_CONNECTIONS"))
    except BaseException:
        listener.close()
        raise
