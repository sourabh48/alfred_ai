from __future__ import annotations

from django.utils import timezone


def internal_now():
    return timezone.now()


def clock_snapshot(moment=None) -> dict:
    current = moment or internal_now()
    local_current = timezone.localtime(current)
    return {
        "generated_at_utc": current.isoformat(),
        "generated_at_local": local_current.isoformat(),
        "local_date": local_current.date().isoformat(),
        "local_time": local_current.strftime("%H:%M:%S"),
        "timezone": timezone.get_current_timezone_name(),
        "clock_label": local_current.strftime("%d %b %Y %H:%M:%S"),
    }
