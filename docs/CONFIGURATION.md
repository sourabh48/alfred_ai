# Configuration

**Current native configuration — 2026-10-15:** Preserve operator files/keys; this audit did not load or overwrite their values. The selected live data directory is F:/ALFRED/restored-runtime, with explicit db.sqlite3 there. Do not initialize a new checkout database when resuming. ALFRED_MEMORY_OPENAI_AUTHORIZED and ALFRED_MEMORY_CLOUD_AUTHORIZED remain false, and no real sync provider is selected. Config/native.env/local.env must be untracked and owner-protected; current broad read grants are an audit finding requiring separately approved maintenance. See [provider activation boundaries](ALFRED_EXTERNAL_INTEGRATIONS.md).

ALFRED now supports a config-backed UI copy layer so the shared brand, auth, error-page, expense, and ML-runtime guidance text does not need to stay hardcoded in templates.

## Files

Post-audit Windows development checks private SQLite/config/cache permissions
before use and protects retained/temporary uploads before writing data. A fresh
source installation should select an empty private data directory and explicit
SQLite path outside the code checkout. Use `ALFRED_DATA_DIR` for local config/key
selection and `DATABASE_URL=sqlite:///...` for the matching absolute database path;
verify the selected path before any initialization. Existing native data, keys or
operator edits must be preserved, not moved or replaced by these examples.
Broad existing file/directory ACLs fail safely and need the separately authorized
[permission repair](NATIVE_WINDOWS.md#private-storage-permission-repair). No startup
silently repairs production. No new migration is introduced by this protection.

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
