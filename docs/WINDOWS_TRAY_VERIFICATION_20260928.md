# Tray, website and branding verification — 28 September 2026

Product: **Alfred - Finance Assistant**. Copyright owner: **Life on our Trails**.

## Completed source and website checks

- 16 focused native-boundary, launcher and tray tests passed after branding changes.
- 18 source native runtime checks passed, covering real HTTP, duplicate startup,
  jobs, retries, worker recovery, scheduled heartbeat, queue persistence and restore.
- The homepage and illustrated guide passed desktop (1365 px) and mobile (390 px)
  layout checks. Images loaded, with no horizontal overflow. Titles, descriptions,
  canonical URLs, product JSON-LD and the two-entry sitemap were checked.
- Removed 11 obsolete files as recorded in [Repository map](REPOSITORY.md).
- Added the copyright notice, stable public project identifier and release
  manifest attribution. See [Ownership](OWNERSHIP.md) for their limits.

## Windows package

The branded build completed successfully from source commit `65dd94b` (the
runtime/branding changes are in `1cf4b83`; the later commit adds the audit prompt).
The final distribution was packaged from `5d6c64e`, incorporating the owner's
2026 copyright correction. ZIP comparison confirmed that only
`project-identity.json` changed; both tested executables are byte-identical.

| Check | Result |
| --- | --- |
| Packaged desktop launcher | Progress window observed; correct brand; exit 0 without system Python on PATH |
| Windows tray | Windows API confirmed the real icon; offline guide bundled; icon removed after graceful stop |
| Packaged native runtime | **23 checks passed** in fresh run `b19f96b008` |
| Concurrent local use | **24 users, 480 writes, 3,962 timed requests, zero errors**; correct isolated totals |
| Load timing | 120-second read window per user; p95 2.687 seconds; total 178.69 seconds; synthetic local traffic |
| Responsive layouts | **28 checks passed** across seven pages and four widths |
| Automated accessibility | **14 audits**, zero serious/critical findings; keyboard skip link passed |
| OCR and recovery | Bundled document/statement OCR, worker recovery, retries, queued work after restart, database/upload/queue restore passed |
| Distribution | 12,624 bundle files inspected; no private runtime paths; ZIP CRC and SHA-256 checks completed |
| Installed upgrade | Existing 1.0.0 upgraded to 1.0.1; database hash retained; executable matches release; uninstaller present |

The first packaged native attempt lost its local test-server connection and
failed after the two startup checks. Its report is preserved; no pass is claimed
for that attempt. The fresh complete run above passed. The original interruption
has not been independently attributed to a specific cause.

A real registered installation now exists on this PC. The isolated installer
lifecycle runner refused to overwrite it. The current upgrade was verified with
a stopped-data backup and retained database hash. The six full install/upgrade/
uninstall checks in the 27 September report belong to the previous release;
fresh uninstall acceptance for this release remains for an isolated Windows
user or second PC. Personal data was not uninstalled for testing.

The public homepage, guide, sitemap and tray illustration returned HTTP 200 and
matched their source files. GitHub Pages publishes only documentation.

Both the checkout and the registered installed copy were restarted and passed
health plus actual Windows tray-registration checks. They retain their separate
data folders. The verified candidate was promoted to `dist/ALFRED` and the
installer/ZIP to `release/`. Previous program/release folders and stopped-data
backups were retained outside the repository under
`F:\ALFRED-retired\20260928-before-tray`.

The prior observation was cancelled for the controlled upgrade and retained.
A fresh observation is running against the updated checkout with sign-in
verification enabled. It is **not a completed pass**; inspect the current report
for its status and expected finish.

### Release fingerprints

- Installer SHA-256: `da0d19be607ce2ca58de251bdc008c7a9a083977bb48be5e6fc61ebb4d7e6b83`
- ZIP SHA-256: `af2f69032df2a2bc05430c31d85a9525d533d9301eb33d3726f53869dee437cc`
- Native executable SHA-256: `3fa0011ed2f0251131a61e6c661b03a142310331a0102ce4d8c6c14a5d1bd115`

The release manifest records source commit, clean tracked-source status, product
identity, notice hash and executable hashes. These are not digital signatures.

## Evidence locations

Generated evidence stays in ignored `artifacts/` folders and is not application
data included in public downloads:

- `artifacts/tray-brand-tests-20260928.log`
- `artifacts/ops/native-tray-source-20260928.json`
- `artifacts/ops/website-verification-20260928.json`
- `artifacts/ops/published-website-20260928.json`
- `artifacts/ops/packaged-tray-20260928.json`
- `artifacts/ops/native-tray-first-attempt-20260928.json` (failed attempt)
- `artifacts/ops/native-tray-package-passed-20260928.json`
- `artifacts/ops/installed-tray-upgrade-20260928.json`
- `artifacts/ops/checkout-tray-backup-20260928.json`
- `artifacts/ops/live-tray-upgrade-20260928.json`
- `artifacts/ops/tray-program-upgrade-20260928.json`

## Remaining acceptance

Clean second-PC install/reboot, uninterrupted observation of scheduled business
outcomes, human screen-reader testing, heavier real usage and independently
checked real-data/model accuracy remain open. Starting an observation does not
count as passing it. Interrupted attempts remain separate records.

The installer is unsigned. Search Console ownership and sitemap submission
require the owner's Google account; search indexing and ranking are not
guaranteed. [Website operations](WEBSITE.md) lists the steps.
