from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def training_runtime_status() -> tuple[bool, str]:
    try:
        import joblib  # noqa: F401
        import numpy  # noqa: F401
        import pandas  # noqa: F401
    except Exception as exc:
        return False, str(exc)
    return True, ""


@lru_cache(maxsize=1)
def sklearn_runtime_status() -> tuple[bool, str]:
    try:
        from sklearn.linear_model import LogisticRegression, Ridge  # noqa: F401
    except Exception as exc:
        return False, str(exc)
    return True, ""


@lru_cache(maxsize=1)
def torch_runtime_status() -> tuple[bool, str]:
    try:
        import torch  # noqa: F401
    except Exception as exc:
        return False, str(exc)
    return True, ""
