"""Windows user-bound vault keys; no plaintext key fallback."""
import csv
import ctypes
from ctypes import wintypes
import io
import os
from pathlib import Path
import subprocess
import time


class MemoryStorageUnavailable(RuntimeError):
    pass


def private_directory(path, *, deadline=None):
    path = Path(path)
    if os.name != 'nt':
        raise MemoryStorageUnavailable('Private memory requires Windows user-bound key protection.')
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or ancestor.is_junction():
            raise MemoryStorageUnavailable('Private memory cannot use linked storage directories.')
    path.mkdir(parents=True, exist_ok=True)
    def timeout():
        seconds = 5 if deadline is None else deadline - time.monotonic()
        if seconds <= 0:
            raise MemoryStorageUnavailable('Private memory protection deadline expired.')
        return min(seconds, 5)
    try:
        identity = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'], capture_output=True, text=True, check=True, timeout=timeout())
        sid = next(csv.reader(io.StringIO(identity.stdout)))[1]
        if not sid.startswith('S-1-'):
            raise ValueError()
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r',
            f'*{sid}:(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=timeout())
    except (OSError, subprocess.SubprocessError, ValueError, IndexError, StopIteration):
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
