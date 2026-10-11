"""Bind the local listener exclusively before starting Waitress threads."""
import os
import socket


def create_native_server(application, port):
    from waitress import create_server
    from .upload_limits import limit, validate_limits

    validate_limits()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if os.name == "nt":
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", port))
        listener.listen(128)
        return create_server(application, sockets=[listener], threads=4,
                             max_request_body_size=limit("ALFRED_UPLOAD_REQUEST_BYTES") + 1,
                             connection_limit=limit("ALFRED_UPLOAD_CONNECTIONS"))
    except BaseException:
        listener.close()
        raise
