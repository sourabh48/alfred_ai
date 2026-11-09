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
