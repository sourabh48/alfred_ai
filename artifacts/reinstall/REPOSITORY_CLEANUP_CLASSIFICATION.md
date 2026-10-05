# Repository cleanup classification

Inventory date: 2026-10-05. No disposable file was blindly deleted. No tracked private/runtime file was found in the initial inventory; therefore no `git rm --cached` removal is currently required.

| Classification | Paths/groups | Decision/evidence |
|---|---|---|
| KEEP IN GIT | `alfred_ai/`, `apps/`, migrations, tests, templates, `static/`, `guide/`, root launchers and packaging source | Required source application; preserve existing bounded engineering changes and new money migrations/tests |
| KEEP IN GIT | requirements, Windows constraints, `.github/`, scripts, AGENTS, docs, reviewed `artifacts/audit/*.md`, `artifacts/reinstall/*.md` | Rebuild, validation, continuation and recovery instructions |
| KEEP IN GIT | `.agents/skills/`, `.codex/skills/graphify/`, `.codex/hooks.json`, `skills-lock.json` | Reusable project instructions; no global cache or credentials |
| KEEP IN GIT | Bootstrap, Chart.js and Leaflet vendored browser libraries | Required offline/static/packaging assets; maximum tracked file size below 250 KB |
| PRIVATE BACKUP; KEEP LOCALLY | actual SQLite databases and durable queue, private config, real media/uploads, durable model/training state, application backup archives | Outside Git already; backup both discovered installation roots before formatting |
| GENERATED; KEEP IGNORED | `.venv/`, bytecode, caches, coverage, test/browser/OCR output, logs, `build/`, `dist/`, `release/`, `staticfiles/`, `graphify-out/` | Regenerable; no deletion needed for a clean source repository |
| RELEASE ASSET ONLY | generated EXE/MSI/installer/ZIP output under ignored build/release paths | Preserve existing local release if desired; not required to rebuild source and not source-controlled |
| MACHINE ALIAS; KEEP LOCALLY | `.claude/skills/` absolute junctions | Machine-specific aliases to canonical skills; ignore, recreate from documentation |
| REVIEW | historical Docker/WSL virtual disks, private-state locations outside the two discovered roots | No active Compose engine was found; resolve backup coverage before the reinstall gate |

Tracked extensions were checked for EXE/MSI/ZIP/PDF/DB/SQLite/model binaries/images/video; none were found. Source conflict-marker search returned no unresolved markers. Temporary `.bak/.old/.orig/.tmp/.copy` files are ignored; no required source is removed just because a filename resembles a temporary file.

The broad artifacts ignore was narrowed to retain only reviewed audit/reinstall Markdown. Raw scan reports, test proof, browser output and runtime artifacts remain ignored. Existing generated/private files remain on disk until a separately verified backup and an explicit need for deletion exist.
