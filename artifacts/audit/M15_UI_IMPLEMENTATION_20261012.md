# M15 UI implementation evidence

Work only in F:/ALFRED_DEV/m15-ui, codex/m15-ui-integration-20261012, based on
081e30e1259936a0898798c89e7f30f76a0d500c. Original 03ab0ae and hardened 081e30e
review candidates remain unchanged. The preceding package was built from f6c686e:
f6c686e..081e30e changes tests/documentation only, not application code. Its freshly
verified portable SHA256 is A862C1AEDFA2A929E2476559C16B317CD6A948A3FC669D6356AC258047C6DE3A.
It does not validate this new UI source.

## Actionable inventory

| Milestone | Existing surface | Required bounded change |
| --- | --- | --- |
| UI-A | base/partials, Insights, intelligence.js | Shared offline typography, light/dark styles, everyday navigation, responsive conversation, local availability, draft/retry/new conversation |
| UI-B | Settings memory.js, existing learning/sync/reason APIs | Search/review/provenance, candidate rejection, safe source links, actual sync and policy status |
| UI-C | canonical baseline, loan closure sources, dashboard | Deterministic Decimal currency objects, suppress unsupported model financial claims, dashboard presentation |
| UI-D | existing Expense/Loan/Investment/Travel templates/scripts | Reusable search controls, upload errors, record/evidence distinctions, mobile layouts |
| UI-E | established native build and acceptance scripts | Fresh asset/package inspection, synthetic browser/runtime/restart gate |

No separate conversation-history storage exists. Conversations stay on the page;
new conversation clears that page. No plaintext chat persistence is introduced.
Banking has existing APIs but no separate supported UI route; do not invent a
navigation destination. Proposed/superseded/expired labels must reflect the actual
memory schema rather than fabricated states. Real provider/OpenAI remain disabled.

## Baseline

One actual synthetic Chrome workflow PASS, 13.756s, zero failures/skips. Screenshot
F:/ALFRED_DEV/isolated-tests/m15-ui-chrome/user-data/hybrid-insights-local-grounding-verified-memory.png
was reviewed before edits. Subsequent captures overwrite this filename; it is not
an immutable baseline image. The preceding packaged baseline screenshots remain
preserved under m15-hardening/artifacts/native-tests/786b0b27ee/.

Focused UI-A backend: 32 PASS, 11.072s, no failures/skips. Log:
F:/ALFRED_DEV/isolated-tests/m15-ui-a-backend.log. Final Chrome: 3 PASS, 30.647s,
zero failures/skips (m15-ui-a-gate.log). Actual desktop, dark, outage and 390px mobile
screenshots reviewed under m15-ui-chrome/user-data/ui-a-*.png. Dark navigation
contrast exceeds 4.5:1 after theme transition; Escape closes an opening mobile menu.
Source AST update PASS: 8452 nodes, 22119 edges; no semantic/cloud calls.
UI-A COMPLETE. Shared package inspector requires and digest-checks new UI assets;
fresh packaging remains UI-E, and the old package is not new-UI acceptance.
All fixtures synthetic. No live source/database/key/backup mutation or real cloud calls.
Independent off-device recovery/key portability remain PENDING; cancelled dialogs
stay cancelled. Installer, separate-PC and real-account acceptance remain pending.

## UI-B - 2026-10-13 COMPLETE

Current encrypted memories have searchable/category-filtered cards, owner-confirmed
labels, provenance/timestamps, immutable-ID corrections and atomic selected deletion
(1–20 IDs). Any stale/foreign selection rejects the entire request. Other records
and owners survive; selected memories cannot return through journal recovery.
Suggestions remain inferred/unverified until explicitly checked; rejection reuses
the existing owner-scoped revocation endpoint. Search and unrelated review actions
preserve correction/candidate drafts. Existing stale-edit conflict handling stays intact.
Source links point only to supported local records; answers can be explicitly saved
as unverified local proposals. No automatic verified memory or financial mutation.

Sync status shows actual transfer timestamp/retry state, encrypted pending batch and
conflicts. Synthetic provider labels never imply real cloud success. Conflict merge
uses the existing explicitly confirmed endpoint. Reasoning preferences keep real
OpenAI disabled; usage is explicitly conservative reservations, not billing telemetry.
No keys, raw provider errors or private diagnostic fields are returned.

Focused related backend: 110 PASS, 60.186s, zero failures/skips
(m15-ui-b-backend.log). Final Chrome: 4 PASS, 46.985s, zero failures/skips
(m15-ui-b-gate.log), including search/review/selected revocation, verification,
stale correction drafts and synthetic consent/budget fallback. Actual screenshot
m15-ui-chrome/user-data/ui-b-memory-search-review-revocation.png reviewed PASS.
AST update: 8461 nodes, 22156 edges, no semantic API cost. No new migration.
Earlier failed test selectors/failure logs are retained; counts are actual runs,
not overlapping sums. Next: UI-C canonical Decimal display and currency protection.
