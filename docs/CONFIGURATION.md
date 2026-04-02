# Configuration

ALFRED now supports a config-backed UI copy layer so the shared brand, auth, error-page, expense, and ML-runtime guidance text does not need to stay hardcoded in templates.

## Files

- `config/alfred_ui.example.json`
  Tracked example config committed to the repo.
- `config/alfred_ui.json`
  Optional local override file. This file is ignored by git.

## Load order

1. `config/alfred_ui.json`
2. `config/alfred_ui.example.json`
3. Built-in defaults in `alfred_ai/services/ui_config.py`

If the local file is missing, ALFRED falls back to the example file. If both files are missing or invalid, ALFRED falls back to the built-in defaults in code so the app still renders.

## Suggested workflow

1. Copy `config/alfred_ui.example.json` to `config/alfred_ui.json`
2. Adjust brand or copy text locally
3. Keep secrets and machine-specific wording out of the tracked example file

## Why this exists

- Keeps shared UI copy in one place
- Reduces repeated hardcoded strings across templates and JavaScript
- Lets developers customize local branding or wording without editing templates directly

## ML runtime note

The ML runtime banner explains both startup approval and scikit-learn availability. ALFRED prefers scikit-learn for tabular model training when Windows allows it, but it still falls back to the in-repo deterministic models if scikit-learn DLLs are blocked.
