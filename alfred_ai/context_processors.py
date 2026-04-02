from __future__ import annotations

from alfred_ai.services.ui_config import load_ui_config


def global_ui_config(_request):
    return {"ui_config": load_ui_config()}
