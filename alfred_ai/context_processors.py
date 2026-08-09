from __future__ import annotations

from django.conf import settings

from alfred_ai.services.ui_config import load_ui_config


def _session_security_payload() -> dict:
    timeout_seconds = max(0, int(getattr(settings, "SESSION_COOKIE_AGE", 0) or 0))
    warning_seconds = max(0, int(getattr(settings, "ALFRED_SESSION_WARNING_SECONDS", 0) or 0))
    return {
        "timeout_seconds": timeout_seconds,
        "warning_seconds": min(warning_seconds, timeout_seconds) if timeout_seconds else 0,
    }


def global_ui_config(_request):
    return {
        "ui_config": load_ui_config(),
        "session_security": _session_security_payload(),
    }
