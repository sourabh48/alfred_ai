# Test evidence index

Prior scoped receipts: [usability evidence](../ALFRED_USABILITY_INTEGRATION.md)
and local `artifacts/usability-20261109/`. They include source hashes, failed
attempts and corrected runs. Do not count reruns twice or transfer CI green.

- 115 distinct backend cases PASS across overlapping scoped suites.
- Three actual Chrome journeys PASS; diagnostics four light/dark desktop/mobile
  Axe audits PASS, source-center desktop Axe PASS.
- Native source drill 19 checks PASS, run 1c88501943; synthetic accounts/data only.
- Actual Ollama multi-turn synthetic API acceptance 1 PASS after vault reopen.
- Local model benchmarks include cold and warm timings and reported GPU allocation.
- Tracker check, migration drift, JS syntax and diff whitespace PASS before recovery.

Statement-import source `0f3560557d6178c07f07dfeb05c4a975646c3e7b`:

- Final consolidated 157 backend cases PASS, zero failures/skips, 313.632 s:
  `artifacts/usability-20261109/statement-acceptance-final.log`.
- Actual Chrome upload → no canonical writes → correction → confirmation →
  reopen PASS; four full-page Axe light/dark desktop/mobile audits PASS:
  `statement-review-browser-final.json` and `artifacts/browser/user-data/statement-review-accessibility.json`.
- Current-source native Windows19 PASS, run d828ff2e92, including actual HTTP
  preview/confirmation, worker recovery, scheduler, restart and backup/restore:
  `artifacts/usability-20261109/native-reviewed-import.json`.
- Frozen identity/cent rounding, ownership/CSRF/expiry, stale dependencies, replay,
  provenance rollback and retry/confirmation races covered by real domain services.
- Initial121-case run had nine old-contract failures. A55-case correction run had
  one remaining assertion using the upload receipt instead of confirmation. Both
  failed receipts retained; final157 PASS is the acceptance receipt, not a sum.
- Clean exact-source preflight PASS (source/dependency/migration/privacy only):
  `artifacts/usability-20261109/clean-source-preflight/release.json`. First preflight
  rejected the unrelated dirty cache edit; it was preserved, with no waiver, and
  validation used a clean detached worktree. Release promotion remains BLOCKED.
- Migration drift: no changes; JS syntax/diff checks PASS. Graphify AST refreshed
  (13944 nodes,39669 edges). Guide/screenshot: [statement review](../STATEMENT_IMPORT_REVIEW_GUIDE.md).

No owner account acceptance, current installer upgrade, independent full audit
or 3.0 acceptance. Earlier receipts do not validate a packaged release.

GitHub MCP commit-workflow lookup for a9947bc returned no pull-request-triggered
runs (that endpoint's documented filter). Current source commits are local only;
no new CI run was dispatched. Historical c730360 CI is separate exact-source evidence.

## Loan review ? source88c1df826aa14fc56247678cabaa175356d62882

- Final consolidated215 backend PASS, zero failures/skips,206.670 s:
  `artifacts/loan-review-20261110/backend-final.log`. Focused13 PASS separately;
  measured7.076 s added to the established backend duration inventory.
- Two real Chrome journeys PASS,67.571 s suite: upload/preview/edit/confirm/reopen/
  refreshed register/Documents; safe parser failure and duplicate real PDF reimport.
  `browser.json`/`browser-final.log`. Runner records checkout8926e42 plus dirty scope;
  `loan-source-manifest.json` pins all28 tested source file hashes committed at88c1df8.
- Four light/dark1440/390 full-page Axe audits: zero violations, each retains one
  incomplete color-contrast rule for existing gradient surfaces. This is not full
  accessibility acceptance. Sanitized screenshot/guide committed.
- Native Windows22 PASS, run a47e15d1a9: `native.json`, `native-second.log`.
  Real PDF/HTTP owner boundary; concurrent confirmations both200, only one loan;
  idempotent receipt after restart; worker/cache/scheduler/retry/restart and private
  synthetic backup/independent restore. Source runtime only, no installed package.
- Clean exact-source source/privacy/dependency/migration preflight PASS:
  `clean-source-preflight-final/release.json`; promotion remains BLOCKED. Earlier
  attempt ran before worktree checkout completed and failed candidate_worktree_dirty;
  no waiver. Validation uses retained clean detached worktree usability-loan-check-88c1df8.
- Initial174 backend run:10 failures/3 errors (old posting/cleanup contracts and
  Decimal JSON draft persistence); corrected108 run: one old response assertion.
  Failed browser receipts retained (Decimal serialization, missing review link,
  duplicate hidden navigation selector, and one mistyped test selector). Final2 PASS.
- No new migrations; drift check reports no changes. JS syntax PASS; Graphify AST
  updated14001 nodes/39946 edges. Initial diff check warned about one terminal blank
  line in the new test; checkpoint normalizes it without changing test behavior.
- Only synthetic isolated data used. Existing owner runtime, secrets, models,
  backups and cache edit preserved. Source acceptance is not 2.0 release acceptance.

## Legacy source preservation follow-up ? c2d1517a364d385c7605ac346d3de86a35734326

- New synthetic regression FAIL before fix: `legacy-deletion-before.log`. It
  reproduced deletion of a confirmed canonical loan after removing its only old source.
-86 affected backend PASS,85.872 s, zero failures/skips: `legacy-deletion-after.log`.
  These overlap the215-case loan suite; do not sum them as new coverage.
-1 real Chrome deletion journey PASS,17.593 s suite: `legacy-browser.json`/log.
  Actual confirmation prompt checked; canonical loan unchanged after source removal.
- Seven changed files pinned in `legacy-source-manifest.json`; source commitc2d1517.
  Historical browser checkout2350cad plus the hashed dirty scope identifies the run.
- Clean source/privacy/dependency/migration preflight PASS atc2d1517:
  `preservation-preflight/release.json`. Broader native22/215 backend evidence remains
  pinned to88c1df8; no claim of new full exact-head CI, package or native rerun.
- Graphify AST refreshed after removal; JS syntax/diff/tracker checks PASS.
  No new dependencies/schema/runtime changes. Guide and deletion prompt describe
  preserved canonical loans. All evidence files under artifacts/loan-review-20261110.

## Investment review - sourceb42988b4ceeab3cfa07dec0a4ad9b345d2f3ec77

Receipts: `artifacts/investment-review-20261110/`.

-272 consolidated backend PASS, zero failures/skips,244.426 s:
  `backend-consolidated.log`. Earlier271-case green followed by an added negative
  sign case. Final non-Django binary-file wrapper is validated by45 overlapping
  backend cases PASS,77.468 s: `attachment-acceptance.log`. Do not sum reruns.
-12 investment-review cases in the45-case follow-up include real PDF extraction,
  Decimal precision/signs, missing/invalid fields, explicit zero, source evidence,
  duplicates, ownership/CSRF, expired token/draft, stale dependencies/source,
  correction/retry races, rollback/recovery, source removal and real concurrent
  confirmation. Measured16.863 s total recorded in the established duration inventory.
- Actual Chrome PDF upload -> no writes -> source review/corrections/currency/SIP ->
  confirmation -> reopen -> refreshed register PASS: `browser-final.json`/log,
 32.339 s suite. Four full-page1440/390 light/dark Axe audits: zero violations;
  each retains one incomplete color-contrast rule on gradient surfaces. Full
  manual accessibility acceptance remains open. Sanitized guide/screenshot committed.
- Native24 PASS, run dfac5d1fc9: `native.json` and `native-consolidated.log`.
  Real PDF/HTTP preview/edit/confirmation/replay and owner boundary, restart,
  worker/scheduler/cache/recovery and independent synthetic backup/restore.
  Source runtime only; no installer/portable or owner data acceptance.
- Native/Chrome broader runs preceded the final File wrapper for non-Django
  binary-file callers;45 focused cases validate the additional caller path. No
  new full exact-head CI is claimed. Browser checkout metadata is407789e plus dirty
  scope, pinned by30 final file hashes in `source-manifest.json` and source commit.
- Source/dependency/migration/privacy preflight PASS on clean exact source:
  `clean-source-preflight/release.json`. Promotion remains BLOCKED. Validation
  worktree retained at F:/ALFRED_DEV/usability-investment-check-b42988b.
- Failed receipts retained: first116-case compatibility run,97-case correction run
  and197-case run with one obsolete summary assertion. Initial Chrome caught decimal
  splitting; corrected extraction preserves full decimal text. Negative sign and
  attachment-caller checks added before final acceptance. No security checks waived.
- Migration drift reports no changes; JS syntax/diff checks PASS. Graphify AST
  refreshed14068 nodes/40240 edges. No dependencies/schema/valuation policy changed.
