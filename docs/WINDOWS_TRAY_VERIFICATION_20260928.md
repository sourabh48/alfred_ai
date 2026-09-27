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

The branded package rebuild and packaged tray/installer verification are in
progress. The previous release remains recorded separately; its results do not
establish that this new package has passed. This section is updated from actual
packaged test reports before publishing the new release.

## Evidence locations

Generated evidence stays in ignored `artifacts/` folders and is not application
data included in public downloads:

- `artifacts/tray-brand-tests-20260928.log`
- `artifacts/ops/native-tray-source-20260928.json`
- `artifacts/ops/website-verification-20260928.json`

## Remaining acceptance

Clean second-PC install/reboot, uninterrupted observation of scheduled business
outcomes, human screen-reader testing, heavier real usage and independently
checked real-data/model accuracy remain open. Starting an observation does not
count as passing it. Interrupted attempts remain separate records.

The installer is unsigned. Search Console ownership and sitemap submission
require the owner's Google account; search indexing and ranking are not
guaranteed. [Website operations](WEBSITE.md) lists the steps.
