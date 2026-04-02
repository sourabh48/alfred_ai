from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from apps.ml_engine.training.runtime import sklearn_runtime_status, training_runtime_status


POLICY_BLOCK_TOKENS = (
    "application control policy",
    "blocked this file",
    "dll load failed",
    "_libsvm",
)


def _approved_superuser():
    user_model = get_user_model()
    return (
        user_model.objects.filter(is_superuser=True, ml_training_consent_granted=True)
        .order_by("ml_training_consent_given_at", "id")
        .first()
    )


def _approval_payload() -> dict[str, Any]:
    try:
        approver = _approved_superuser()
    except (OperationalError, ProgrammingError):
        approver = None
    return {
        "granted": approver is not None,
        "approved_by": getattr(approver, "username", ""),
        "approved_at": approver.ml_training_consent_given_at.isoformat() if getattr(approver, "ml_training_consent_given_at", None) else "",
    }


def training_bootstrap_allowed() -> tuple[bool, str]:
    approval = _approval_payload()
    if not approval["granted"]:
        return False, "awaiting_superuser_approval"
    runtime_ready, runtime_reason = training_runtime_status()
    if not runtime_ready:
        return False, runtime_reason or "training_runtime_unavailable"
    return True, "ok"


def grant_training_consent(user) -> None:
    if not getattr(user, "is_superuser", False):
        raise PermissionError("Only superusers can approve startup training.")
    user.ml_training_consent_granted = True
    user.ml_training_consent_given_at = timezone.now()
    user.save(update_fields=["ml_training_consent_granted", "ml_training_consent_given_at"])


def revoke_training_consent(user) -> None:
    if not getattr(user, "is_superuser", False):
        raise PermissionError("Only superusers can revoke startup training.")
    user.ml_training_consent_granted = False
    user.ml_training_consent_given_at = None
    user.save(update_fields=["ml_training_consent_granted", "ml_training_consent_given_at"])


def build_runtime_status(user=None) -> dict[str, Any]:
    approval = _approval_payload()
    runtime_ready, runtime_reason = training_runtime_status()
    runtime_reason = str(runtime_reason or "")
    sklearn_ready, sklearn_reason = sklearn_runtime_status()
    sklearn_reason = str(sklearn_reason or "")
    policy_blocked = bool(sklearn_reason and any(token in sklearn_reason.lower() for token in POLICY_BLOCK_TOKENS))
    startup_ready = bool(getattr(settings, "ALFRED_AUTO_TRAIN_ON_STARTUP", True) and approval["granted"] and runtime_ready)
    can_manage = bool(getattr(user, "is_authenticated", False) and getattr(user, "is_superuser", False))

    if not getattr(settings, "ALFRED_AUTO_TRAIN_ON_STARTUP", True):
        setup_state = "disabled"
    elif not approval["granted"]:
        setup_state = "awaiting_approval"
    elif not runtime_ready:
        setup_state = "runtime_blocked"
    else:
        setup_state = "ready"

    recommended_steps = []
    if setup_state == "awaiting_approval":
        recommended_steps.append("Approve ALFRED startup training once as a superuser.")
    if not runtime_ready:
        recommended_steps.append("Install the missing ALFRED training runtime dependencies in the active environment.")
    if runtime_ready and not sklearn_ready:
        if policy_blocked:
            recommended_steps.append("Allow the Python environment to load scikit-learn native files in Windows Application Control or your endpoint security policy.")
        else:
            recommended_steps.append("Install or repair scikit-learn in the active Alfred environment to enable the preferred backend.")
    if approval["granted"] and runtime_ready:
        recommended_steps.append("Use 'Run now' once to seed fresh model artifacts, then let startup auto-training continue on its own.")

    return {
        "can_manage": can_manage,
        "auto_train_enabled": bool(getattr(settings, "ALFRED_AUTO_TRAIN_ON_STARTUP", True)),
        "approval": approval,
        "runtime": {
            "ready": runtime_ready,
            "reason": runtime_reason,
            "policy_blocked": policy_blocked,
            "sklearn_ready": sklearn_ready,
            "sklearn_reason": sklearn_reason,
        },
        "startup_ready": startup_ready,
        "setup_state": setup_state,
        "recommended_steps": recommended_steps,
    }
