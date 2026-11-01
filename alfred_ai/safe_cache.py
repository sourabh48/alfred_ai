"""diskcache storage that never unpickles.

diskcache reads a row through pickle whenever the row says it is pickled, and JSONDisk still does so
through its parent. A row planted in a cache file must not reach pickle.load, so this class refuses
those rows, without decoding them, and writes typed JSON only.
"""
import base64
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import json
import os.path as op
from uuid import UUID

from diskcache import Disk
from diskcache.core import MODE_BINARY, MODE_RAW, MODE_TEXT, UNKNOWN

TAG = "__alfred_cache__"
SQLITE_INTEGER = range(-(2 ** 63), 2 ** 63)


class UnsafeCacheEntry(OSError):
    """diskcache treats OSError from a read as a cache miss."""


class CacheIntegrityError(RuntimeError):
    """Not an OSError, so diskcache lets it reach the caller, which must fail closed."""


def encode(value):
    kind = type(value)
    if value is None or kind in (bool, int, float, str):
        return value
    if isinstance(value, list):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        if all(type(key) is str for key in value) and TAG not in value:
            return {key: encode(item) for key, item in value.items()}
        return {TAG: "dict", "v": [[encode(key), encode(item)] for key, item in value.items()]}
    if isinstance(value, tuple):
        return {TAG: "tuple", "v": [encode(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {TAG: "frozenset" if isinstance(value, frozenset) else "set", "v": [encode(item) for item in value]}
    if isinstance(value, Decimal):
        return {TAG: "decimal", "v": str(value)}
    if isinstance(value, datetime):
        return {TAG: "datetime", "v": value.isoformat()}
    if isinstance(value, date):
        return {TAG: "date", "v": value.isoformat()}
    if isinstance(value, time):
        return {TAG: "time", "v": value.isoformat()}
    if isinstance(value, timedelta):
        return {TAG: "timedelta", "v": [value.days, value.seconds, value.microseconds]}
    if isinstance(value, UUID):
        return {TAG: "uuid", "v": str(value)}
    if isinstance(value, (bytes, bytearray)):
        return {TAG: "bytes", "v": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, str):
        return str(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    raise TypeError(f"{kind.__name__} values cannot be cached safely")


DECODERS = {
    "tuple": lambda v: tuple(decode(item) for item in v),
    "set": lambda v: {decode(item) for item in v},
    "frozenset": lambda v: frozenset(decode(item) for item in v),
    "dict": lambda v: {decode(key): decode(item) for key, item in v},
    "decimal": Decimal,
    "datetime": datetime.fromisoformat,
    "date": date.fromisoformat,
    "time": time.fromisoformat,
    "timedelta": lambda v: timedelta(days=v[0], seconds=v[1], microseconds=v[2]),
    "uuid": UUID,
    "bytes": lambda v: base64.b64decode(v.encode("ascii"), validate=True),
}


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if isinstance(value, dict):
        if TAG in value:
            return DECODERS[value[TAG]](value["v"])
        return {key: decode(item) for key, item in value.items()}
    return value


def _inside_cache(filename):
    if not isinstance(filename, str) or op.isabs(filename) or op.splitdrive(filename)[0]:
        return False
    return not filename.replace("\\", "/").startswith("../") and ".." not in filename.replace("\\", "/").split("/")


class SafeDisk(Disk):
    error = UnsafeCacheEntry

    def put(self, key):
        if type(key) not in (str, bytes, int, float):
            raise TypeError("Cache keys must be text or numbers, which diskcache stores without pickle.")
        return super().put(key)

    def get(self, key, raw):
        if not raw:
            raise self.error("A pickled cache key was refused without decoding it.")
        return super().get(key, raw)

    def store(self, value, read, key=UNKNOWN):
        if read:
            raise TypeError("Streamed cache values are not supported.")
        # Whole numbers stay raw because Cache.incr works on them in place.
        if type(value) is float or (type(value) is int and value in SQLITE_INTEGER) or type(value) is bytes:
            return super().store(value, False, key=key)
        return super().store(json.dumps(encode(value), separators=(",", ":")), False, key=key)

    def fetch(self, mode, filename, value, read):
        if read or mode not in (MODE_RAW, MODE_BINARY, MODE_TEXT):
            raise self.error("A cache entry in an unsupported format was refused without decoding it.")
        if mode != MODE_RAW and not _inside_cache(filename):
            raise self.error("A cache entry pointing outside its folder was refused.")
        data = super().fetch(mode, filename, value, False)
        if not isinstance(data, str):
            return data
        try:
            return decode(json.loads(data))
        except (ValueError, KeyError, TypeError, ArithmeticError) as error:
            raise self.error("A corrupt cache entry was refused.") from error

    def remove(self, file_path):
        # A planted path must not turn cache cleanup into deleting files elsewhere.
        if _inside_cache(file_path):
            return super().remove(file_path)
        return None


class StrictDisk(SafeDisk):
    error = CacheIntegrityError
