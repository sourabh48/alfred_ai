# Acceptance continuation — 25 September 2026

ALFRED remains a local/LAN application. This continuation fixes defects found
in the earlier acceptance evidence and records the checks still requiring elapsed
time, another computer or human observations.

## Document correctness

The independently checked private source page showed a first-row deposit being
classified as a debit and a transaction recorded on its value date instead of
the printed transaction date. The parser now retains usable PDF withdrawal and
deposit columns and uses the transaction date. Four generated PDF regressions
cover first deposits, misleading credit words, month boundaries and descending
statement order.

The resume comparison had a checker defect: expected lowercase skill names were
compared against title-cased display names. The checker now compares casefolded
names without changing expected skills or application output.

Fresh private-file comparisons passed **68/68 checked fields**: resume 13/13,
statement 51/51 and credit report 4/4. Evidence is kept locally in
`artifacts/validation-private-20260918/after-fix-20260925.log` and
`checked_comparison_summary.json`. Sources, extracted content and expected
personal values remain ignored. This covers selected fields on three documents;
it does not establish accuracy for all layouts. Existing imported financial
records were not bulk rewritten or reimported.

## Browser and load checks

All **nine Chrome workflows passed with zero skips** in 85.124 seconds,
including new resume, loan and credit-report correction forms. The tests enter
values through the browser, preserve them through live refresh, save and reload.
The initial run exposed a stale-element race in the test while a closed form was
rendering; the final run waits for that render before interacting.

Evidence: `artifacts/acceptance-20260925-browser-final.log` and
`artifacts/browser-acceptance-20260925-final/browser_regression_summary.json`.

The source runtime passed **24 concurrent users, 480 writes and 3,704 timed
requests**, with zero errors and correct isolated totals. Each user continued
reading for 120 seconds after writing. Recorded p95 was 2.422 seconds and total
elapsed time 173.27 seconds while other verification/build work shared the PC.
This is synthetic local traffic, not a general capacity guarantee.

Responsive checks passed on Dashboard, Expenses, Settings, Documents, Loans,
Career and Credit Score at 360, 390, 768 and 1440 CSS pixels. The broader axe
scan found three unnamed dropdowns on Career and Credit Score. Explicit labels
were added; final packaged verification is recorded below when complete.

Initial source evidence: run `f57c0d7ea1`,
`artifacts/acceptance-20260925-native.log` and its `mobile-accessibility.json`.
That run failed the accessibility gate before the labels were fixed; its passing
load/layout checks do not make the entire initial run a pass.

## Runtime and release

- Windows current-user startup registration succeeded and was read back on
  25 September. Evidence: `artifacts/ops/native_startup_registration-20260925.json`.
  An actual sign-in has not yet been observed.
- The September 18 observer stopped sampling after 4.1344 hours. The new
  read-only status command correctly classifies that report as interrupted.
  Evidence: `artifacts/ops/native_overnight_status-20260925.json`.
- Observation now preserves prior report files, uses monotonic elapsed time
  and detects stale unfinished reports. Completed jobs with business failures
  cannot make an overnight report pass.
- The second-PC kit includes phase launchers, human instructions and a release
  manifest. It rejects the development machine and mismatched executables;
  reboot proof must come from the same PC as fresh-install proof.

The full backend suite passed: **413 discovered, 404 passed, nine browser cases
intentionally separate**, 754.498 seconds, exit zero. The nine browser cases also
passed in their dedicated Chrome run. Django reported no system-check issues.
Log: `artifacts/acceptance-20260925-full-suite.log`.

The [26 September package continuation](WINDOWS_PACKAGE_VERIFICATION_20260926.md)
completed packaged runtime, installer, launcher and uninstall verification.
The updated local runtime is running. A new completed overnight observation
remains pending.

## Acceptance still requiring external evidence

1. A separate Windows PC for installation, real reboot and uninstall-retention
   observations. Use [Windows acceptance](WINDOWS_ACCEPTANCE.md).
2. A completed uninterrupted overnight observation covering scheduled refresh,
   cleanup and eligible training. Starting a run is not a pass.
3. A real Windows sign-in after startup registration. Keep the PC running until
   the overnight observation finishes before signing out or rebooting it.
4. Human screen-reader/task testing and heavier real usage. Follow
   [Human acceptance checks](MANUAL_ACCEPTANCE.md).
5. More independently checked documents and consenting real model outcomes.
   The read-only `artifacts/ops/real_data_validation-20260925.json` still finds
   blockers for every recorded model; sample, quality, confidence and proxy-target
   gates remain in force. Three checked files do not close model readiness.

LAN access and live email/bureau integrations remain optional. No cloud runtime
or cloud credentials were introduced.
