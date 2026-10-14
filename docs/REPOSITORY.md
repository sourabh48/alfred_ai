# Repository map and cleanup

**Current repository state — 2026-10-15:** Deployed/GitHub master is 3932f391. Isolated audit documentation and unfinished M20 work must not be confused with production source. Protected operator edits in main are preserved; no audit push or live source update is authorized. Use [master matrix](ALFRED_MASTER_FEATURE_MATRIX.md) and [roadmap](ALFRED_COMPLETION_ROADMAP.md); the earlier cleanup below is historical and does not prove all experimental code is safe.

| Location | Purpose |
| --- | --- |
| `alfred_native.py`, `alfred_launcher.py`, `alfred_tray.py` | Windows server, launcher and notification icon |
| `alfred_ai/`, `apps/` | Runtime configuration and application features |
| `templates/`, `static/` | Browser interface and bundled assets |
| `tests/` | Automated regression coverage |
| `scripts/` | Operational, verification and release tools |
| `packaging/` | Installer, bundle specification and project identity |
| `docs/index.html`, `docs/guide/` | Product website and offline installation guide |
| `docs/*.md`, `docs/releases/` | Technical guides, historical evidence and release notes |
| `config/` | Examples and ignored local configuration |
| `dist/`, `release/`, `build/`, `artifacts/` | Ignored generated packages, installers and verification evidence |
| `db.sqlite3`, `media/`, private model/configuration files | Ignored user data; retain when updating or cleaning |

## 28 September cleanup

Removed ten empty, unreferenced placeholder modules: the old cron and external
update script, six training scripts, and two preprocessing files. Removed the
obsolete `scripts/training_scripts/train_salary_model.py`, which imported
nonexistent exports and depended on an absent CSV. The maintained salary trainer
remains in `apps/ml_engine/training/train_salary.py`, used by the orchestrator.

Required `__init__.py` files, active training paths, database migrations, useful
test evidence and historical verification reports remain. History is available
in Git. This cleanup does not assert that every unused branch in the application
has been proven unreachable.
