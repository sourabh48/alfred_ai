"""Choose Django's TIME_ZONE: explicit override, then the Windows system zone, then a logged fallback.

This runs once as settings load, so a system zone change applies after a restart.
"""
import ctypes
from zoneinfo import ZoneInfo

# The owner is in Bengaluru, so a failed detection keeps their day and month boundaries right.
FALLBACK_TIME_ZONE = "Asia/Kolkata"
LOAD_LIBRARY_SEARCH_SYSTEM32 = 0x800


def windows_zone_name():
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation") as key:
        return winreg.QueryValueEx(key, "TimeZoneKeyName")[0]


def iana_for_windows_zone(name):
    """Use the CLDR mapping in Windows' own ICU (1903 and later); an unknown name returns ""."""
    lookup = ctypes.CDLL("icu.dll", winmode=LOAD_LIBRARY_SEARCH_SYSTEM32).ucal_getTimeZoneIDForWindowsID
    lookup.argtypes = [ctypes.c_wchar_p, ctypes.c_int32, ctypes.c_char_p, ctypes.c_wchar_p, ctypes.c_int32,
                       ctypes.POINTER(ctypes.c_int)]
    lookup.restype = ctypes.c_int32
    buffer, status = ctypes.create_unicode_buffer(128), ctypes.c_int(0)
    size = lookup(name, -1, None, buffer, len(buffer), ctypes.byref(status))
    return buffer.value if status.value <= 0 and size > 0 else ""


def _known(zone):
    try:
        ZoneInfo(zone)
    except (ValueError, KeyError, OSError):
        return False
    return True


def resolve_time_zone(override=""):
    """Return (zone, warning). The warning is empty unless the requested source could not be used."""
    problems = []
    override = override.strip()
    if override:
        if _known(override):
            return override, ""
        problems.append(f"ALFRED_TIME_ZONE {override!r} is not a known time zone")
    try:
        windows_name = windows_zone_name()
        zone = iana_for_windows_zone(windows_name)
    except Exception as error:  # Detection must never stop startup.
        zone = FALLBACK_TIME_ZONE
        problems.append(f"system time zone detection failed ({type(error).__name__})")
    else:
        if not _known(zone):
            zone = FALLBACK_TIME_ZONE
            problems.append(f"Windows zone {windows_name!r} has no known time zone")
    return zone, f"{'; '.join(problems)}; using {zone}." if problems else ""
