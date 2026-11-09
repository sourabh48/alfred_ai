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

Current new statement-import scope: NOT_RUN until implementation. These earlier
receipts do not validate new financial writes or a packaged release. No owner
account acceptance, current installer upgrade, independent full audit or 3.0 tests.

GitHub MCP commit-workflow lookup for a9947bc returned no pull-request-triggered
runs (that endpoint's documented filter). Current source commits are local only;
no new CI run was dispatched. Historical c730360 CI is separate exact-source evidence.
