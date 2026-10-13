# M15 UI release candidate - local acceptance

M15-UI-A/B/C/D/E COMPLETE. Production promotion remains NOT READY.
Worktree F:/ALFRED_DEV/m15-ui, codex/m15-ui-integration-20261012.
Build source 559663546184d1342d052913b5ed1e52bddaa2d1. Stable M14 ancestry merged
at b801579fe7c72e1391ffd63d618f33755905a27f; its parser correction and tests already
had identical blobs in M15. The merge changed tracked audit documentation only.
9a5290c changes one native test label assertion. Runtime code/assets remain identical
to the build source; these commits are not identical full Git trees. Final review
HEAD/source archive/portable hashes are recorded in the external UI final manifest.
Original 03ab0ae and hardened 081e30e frozen candidates remain unchanged.

| Actual final gate | Result | Evidence under F:/ALFRED_DEV/isolated-tests |
| --- | --- | --- |
| Combined backend, including upload/resource, loan diagnostics and Expense identity | 308 PASS, 182.769s, zero failures/skips | m15-ui-final-combined.log/.ps1 |
| Development Chrome across assistant, memory, Finance/Banking, Loans, Investments, Family and Travel | 14 PASS, 151.079s, zero failures/skips | m15-ui-final-chrome.log; m15-ui-chrome/browser_regression_summary.json |
| Fresh packaged native, workers/scheduler, real local Ollama, restart, encrypted vault recovery | 32 PASS, run 860fcd4a09 | m15-ui-native.log; m15-ui/artifacts/ops/native_exe_verification.json |
| Packaged browser | 6 PASS, included in the 32 native checks | Same report; m15-ui/artifacts/native-tests/860fcd4a09/*.png |
| Packaged launcher/progress/tray/offline guide/no system Python/stop | PASS | m15-ui-launcher.log; m15-ui/artifacts/ops/packaged_launcher_verification.json |
| Configuration/system/migration drift | PASS; no new migrations | m15-ui-config.log |
| Fresh bundle files/private paths/changed asset digests | 10,895 files PASS; 1,228,232,348 bytes; zero private paths | m15-ui-bundle-inspection.json |
| Actual screenshot review | PASS: desktop/dark/390px, currency evidence, memory correction and module controls | m15-ui-chrome/user-data; native-tests/860fcd4a09 |

Earlier overlapping focused results are not added to these counts. Failed fixture,
selector and case-sensitive-label runs are preserved. The final native/launcher
processes stopped gracefully; live port 8000 and its private database were not used.
AST-only graph update completed without semantic API calls.

## Resulting interface and limits

Existing Django/Bootstrap/JavaScript stack retained. Offline fonts, shared styles,
light/dark appearance, everyday navigation, mobile menu, conversational messages,
provider/outage/draft/retry states and safe source panels are integrated. Conversations
remain transient because no saved-chat backend exists; no plaintext history is added.
Memory search/categories/provenance/review/correction/selected deletion use real
owner endpoints, preserve drafts and stale-edit protection, and retain encrypted
revocation/recovery controls. Sync/policy settings never present synthetic access as
real cloud success. Budget reservations are not claimed as billing measurements.
Banking is owner-only read access with actual pagination and masked references;
existing Expense imports/date filters and Loan/Investment/Travel workflows remain.

AI financial numbers/currency claims are conservatively withheld. Independent
canonical Decimal source cards retain cents, missing evidence and provenance.
Current financial models do not store currency codes: assistant currency remains
NOT RECORDED, while legacy screens explicitly retain their INR convention. The
formatter accepts explicitly supplied INR/USD/EUR/GBP metadata; this does not add
multi-currency accounting. Numerical financial hypotheses/examples may be withheld.
Grounding scope remains owned memories, canonical baseline, owner Travel preferences
and verified loan closure amount/date; broader document ingestion is not claimed.
WCAG 2.2 AA is a practical target, not a complete accessibility certification.

## Source/configuration/migration and rollback preparation

The source comparison is stable 30e0b3f..final review HEAD. Stable M14 is now an
ancestor of the isolated candidate; do not infer current remote ancestry from it.
No source push, stable merge, deployment, credential export or live database write
was performed. Existing M13C/M13D migrations remain intact; family.0004 was already
applied in M14 and is not repeated. No new Django migration is introduced.
Shared static assets and private memory/provider APIs gain additive safe fields;
legacy numeric finance contracts and canonical calculations remain unchanged.
Existing local memory settings/provider flags are reused. Real cloud storage and
OpenAI remain disabled by default and require separate operator authorization.

Before any later live promotion, approve the exact candidate, consistent private
database/configuration/key/media/jobs backups and a recovery rehearsal. Gracefully
stop the matching runtime/writers using its established data directory. Preserve
post-backup writes and diagnostic evidence before rollback; restore the exact M14
source/package/configuration and separately verified private backup when required.
Preserve M15 encrypted vaults/journals/keys even if rolling source back to M14;
M14 does not provide the M15 memory interface. Do not re-encrypt live tokens.

## Release blockers retained

- Independent off-device archive plus separately recoverable key restore PENDING.
  Existing backups preserved; cancelled sealing/passphrase dialogs stay cancelled.
- Real cloud-provider selection, permissions/cost/retention approval and acceptance
  PENDING. No real cloud upload or paid OpenAI call occurred.
- Separate-PC, installer lifecycle and normal real-account browser acceptance
  PENDING. Portable same-device synthetic acceptance does not replace these checks.

M15 UI LOCAL INTEGRATION GATE = PASS.
M15 PRODUCTION / UI LIVE RELEASE READY = NO.
Next action: approved independent recovery and remaining real-environment acceptance;
hold the frozen UI candidate and continue later feature work on a separate branch.
