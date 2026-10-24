# Release-specific operator acceptance

Record the release ID, exact candidate SHA, date, browser/Windows version and
PASS/FAIL/PENDING for each item. Sign in normally; never enter a password in
agent chat or evidence files. Synthetic HTTP/browser checks do not fill this list.

| Check | Observation | Status |
| --- | --- | --- |
| Existing-account login and logout | Expected historical records; session ends | PENDING |
| Dashboard | Canonical totals, INR convention and review notices | PENDING |
| Expenses and Banking | Owned transactions/accounts, unchanged fingerprints | PENDING |
| Loans and Investments | EMI/positions and canonical source amounts | PENDING |
| Family | Relationships preserved; financial visibility follows explicit opt-in | PENDING |
| Travel | Saved plans/preferences; cached/estimated availability labeled | PENDING |
| Documents | Owned evidence accessible; other users denied | PENDING |
| Ollama conversation | Local status, grounded references, outage draft/retry | PENDING |
| Encrypted memories | Owner-only review/correction/delete and restart persistence | PENDING |
| Interface | Light/dark, narrow viewport, keyboard and screen-reader behavior | PENDING |

For clean-PC/reboot/install/upgrade/uninstall evidence, use the existing
[Windows acceptance procedure](WINDOWS_ACCEPTANCE.md) and
[manual accessibility checks](MANUAL_ACCEPTANCE.md). A disposable directory on
this development PC does not prove separate-PC or installer lifecycle acceptance.

External recovery has four separate observations: copied archive integrity,
separate portable key recovery, authenticated decryption and independent restored
data reconciliation without this Windows profile. Hashes alone cannot prove these.
The previous M15 waiver remains specific to M15 and is not future authorization.

Attach safe evidence to a release-specific `record` input. Keep credentials,
financial values, documents and decrypted keys out of evidence and reports. A
recorded human attestation is labeled as such, rather than automatically verified.
