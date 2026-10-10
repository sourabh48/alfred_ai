# Loan diagnostic privacy (M14F)

Loan import and payoff APIs use the existing class/reference-only error logger.
Exception messages, causes, tracebacks, document bytes and OCR text are never
formatted into their errors. Each failure has a random error reference that can
be matched to local logs; logs record the exception class and processing stage,
without exception text or financial amounts.

An unexpected import parser failure still saves a reviewable document and
returns HTTP 201 with `success=false`, failed parser status, a stable error code,
safe message and reference. A failure saving that record returns a logged 500.
Payoff operational failures return 500; validation remains 400, missing loans
404, pending reconciliation 202 and confirmed closure 200. Shared resource
errors retain their 400/413/503 statuses and fixed public messages.

Public import/closure serializers allowlist diagnostic metadata and regenerate
summary, verification, linkage and reconciliation messages from status. Arbitrary
historical payload keys, raw parser output, extraction notes, OCR previews,
review artifacts and nested settlement diagnostics are omitted. The same policy
covers loan review/resolve/retry responses, operational-log serialization and
the foreclosure watchlist. Cache revisions prevent older summaries being reused.
Normal owned loan fields, structured settlement amounts/components, document
links, statuses and reviewed business fields remain available. Diagnostic payload
contents are deliberately narrower; clients must not use them as raw evidence.

New loan parsers keep source evidence in the existing private extracted-text
field and structured business fields, without copying source text into diagnostic
payloads. New failure records contain only safe error metadata. Loan cleanup
metadata is filtered before persistence and response; it excludes storage paths
and filenames. Source-file retention/deletion policy is unchanged.

Historical records are filtered when read, never rewritten by M14F. Existing
private forensic evidence, files, corrections and recovery backups are preserved.
No schema or data migration is created. Raw evidence is intentionally unavailable
in the public loan extraction-review UI; manual business-field corrections and
the retained local document remain usable under existing ownership controls.

Validation uses synthetic data and isolated SQLite/media only. Focused M14F:
19 tests passed. Final focused cleanup/retry gate: 36 passed, 0 failures/skips,
19.551 seconds. Affected backend gate: 192 passed, 0 failures/skips, 112.330
seconds (before the final cleanup-metadata producer filter; covered by the final
36 and subsequent combined gate). Chrome: 4 passed, 0 skipped, 51.461 seconds;
driver-backed success confirmed. System checks and migration-drift checks pass.
Combined M14 evidence is recorded in the security readiness report.

Evidence: `F:\ALFRED_DEV\isolated-tests\m14f-*`. Earlier failed test runs are
retained: the initial focused test expected pagination incorrectly; the first
Chrome run used the wrong in-memory harness and an off-screen click; the next
run relied on a filename in the now-filtered diagnostic display. Corrected
checks verify the actual saved closure on the Loans page. No unresolved failure
from these checks remains. No private/live document was used.
