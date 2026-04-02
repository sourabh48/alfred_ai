from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from django.conf import settings


DEFAULT_UI_CONFIG: dict[str, Any] = {
    "brand": {
        "name": "ALFRED",
        "tagline": "Personal Finance & Life Intelligence",
        "home_path": "/dashboard/",
    },
    "navigation": {
        "menu_label": "Menu",
        "signed_in_prefix": "Signed in as",
        "remove_data_label": "Remove My Data",
        "sign_in_label": "Sign in",
        "sign_out_label": "Sign out",
        "create_account_label": "Create account",
    },
    "prompts": {
        "remove_data_confirm": "Remove all Alfred data for this account, including uploaded documents and cached summaries? Your login stays active, and you can start fresh afterward.",
        "remove_data_success": "Your Alfred data has been removed.",
        "remove_data_failure": "Could not remove your Alfred data.",
    },
    "auth": {
        "login": {
            "eyebrow": "Finance, credit, career, and life dashboards in one place",
            "title": "Sign in to Alfred",
            "description": "Open your finance, career, credit, and vehicle workspaces from the same account.",
            "highlights": [
                "Track expenses, debt, credit, and bank-linked evidence in one workspace.",
                "Use document-backed workflows for statements, foreclosure, and bureau uploads.",
                "Keep the same account even after using Remove My Data to start fresh.",
            ],
            "primary_cta": "Sign in",
            "secondary_cta": "Create account",
        },
        "signup": {
            "eyebrow": "Set up the core profile Alfred uses across modules",
            "title": "Create your Alfred account",
            "description": "Start with the identity and income fields Alfred uses for finance, career, risk, and lifestyle guidance.",
            "highlights": [
                "Finance and debt summaries stay tied to one user profile.",
                "Career and credit modules reuse the same verified profile data.",
                "You can wipe user-entered data later without losing the account.",
            ],
            "primary_cta": "Create account",
            "secondary_cta": "Sign in",
        },
    },
    "errors": {
        "404": {
            "eyebrow": "Route not found",
            "title": "That page does not exist in Alfred.",
            "description": "The link may be outdated, incomplete, or typed incorrectly. Use the links below to return to a working workspace.",
            "home_label": "Go to Home",
            "login_label": "Open Sign In",
        },
        "500": {
            "eyebrow": "Something failed",
            "title": "Alfred hit an unexpected error.",
            "description": "Return to the dashboard or sign in again. If the issue keeps repeating, check the system reports or server logs.",
            "home_label": "Back to Home",
            "login_label": "Open Sign In",
        },
    },
    "expenses": {
        "page": {
            "title": "Expense Timeline",
            "description": "Upload statements, classify outflows, and review only the transactions you need instead of scrolling through the full history.",
        },
        "timeline": {
            "title": "Timeline",
            "description": "Use filters to find a transaction by merchant, reference, fingerprint, or internal Alfred ID.",
            "search_placeholder": "Search merchant, reference, fingerprint, or note",
            "id_placeholder": "Transaction ID",
            "limit_label": "Rows",
            "clear_label": "Clear",
            "filtered_total_label": "Filtered Expense Total",
            "filtered_count_label": "Matching Transactions",
            "visible_count_label": "Visible Now",
        },
    },
    "ml_runtime": {
        "banner": {
            "approval_title": "ALFRED ML startup needs first-run approval",
            "approval_body": "Approve startup auto-training once. After that, ALFRED can run training automatically on future startups when the local runtime is healthy.",
            "runtime_title": "ALFRED ML runtime needs attention",
            "runtime_body": "Training can still use the built-in Alfred fallback models, but scikit-learn-backed training needs the local Windows policy to allow its native files.",
            "sklearn_title": "Why ALFRED uses scikit-learn",
            "sklearn_body": "ALFRED prefers scikit-learn for classic tabular model training because it is stable, explainable, and well-suited for salary, risk, parser-confidence, and relationship-style estimators. If Windows blocks sklearn DLLs, Alfred falls back to lighter in-repo models so the app still works.",
            "windows_steps": [
                "Approve startup auto-training once as a superuser.",
                "If Windows Application Control or Defender blocks sklearn DLLs, allow the active Python environment or add the Alfred virtual environment to your approved exclusions.",
                "Run one manual training cycle after approval so fresh model artifacts are written before normal startup refresh takes over.",
            ],
            "approve_label": "Approve Auto-Training",
            "run_now_label": "Run Initial Training Now",
            "revoke_label": "Revoke Approval",
            "runtime_detail_label": "Runtime detail",
            "sklearn_status_label": "Scikit-learn backend",
            "help_open_label": "Why scikit-learn?",
        }
    },
}


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged


def _config_candidates() -> list[Path]:
    base_dir = Path(settings.BASE_DIR)
    return [
        base_dir / "config" / "alfred_ui.json",
        base_dir / "config" / "alfred_ui.example.json",
    ]


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def load_ui_config() -> dict[str, Any]:
    config = deepcopy(DEFAULT_UI_CONFIG)
    source = "defaults"
    for path in _config_candidates():
        if not path.exists():
            continue
        try:
            config = _merge_dicts(config, _read_json(path))
            source = str(path.relative_to(settings.BASE_DIR))
            break
        except Exception:
            continue
    config.setdefault("meta", {})
    config["meta"]["source"] = source
    return config
