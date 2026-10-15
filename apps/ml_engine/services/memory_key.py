"""Windows user-bound vault keys; no plaintext key fallback."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import time


class MemoryStorageUnavailable(RuntimeError):
    pass


def private_directory(path, *, deadline=None):
    if os.name != 'nt':
        raise MemoryStorageUnavailable('Private memory requires Windows user-bound key protection.')
    from alfred_private_storage import private_directory as protect_directory, PrivateStorageUnavailable
    try:
        protect_directory(path, deadline=deadline)
    except (OSError, ValueError, PrivateStorageUnavailable):
        raise MemoryStorageUnavailable('Private memory directory protection is unavailable.') from None


def protect_key(data, *, decrypt=False):
    if os.name != 'nt':
        raise MemoryStorageUnavailable('Private memory requires Windows user-bound key protection.')
    class Blob(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    library = ctypes.WinDLL('crypt32', use_last_error=True)
    function = library.CryptUnprotectData if decrypt else library.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    # UI forbidden; omit LOCAL_MACHINE so only the current Windows user can unwrap.
    if not function(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise MemoryStorageUnavailable('Private memory key protection is unavailable.')
    try:
        return ctypes.string_at(outgoing.data, outgoing.length)
    finally:
        kernel.LocalFree(outgoing.data)
