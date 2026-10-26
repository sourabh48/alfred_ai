# Consolidation preparation — 2026-10-26

**Blocked canonical integration; local reconciliation only.** Canonical development
remains `d5cc181faae5c61d6de65f00ce21375ce73de33b`; master remains
`c47fed95f919859aa62f1875512e3cb8452f2d48`. PR16 remains the sole development-to-master
PR. PR18/19 cannot be closed before permitted, verified integration.

## Sources and dependency order

| Scope | Original source | Dependency / preserved evidence |
| --- | --- | --- |
| Upstream policy / PR17 | `503b84864cc9f61f8f254c8436e4b0183d04e513` | Owner merged as `d5cc181`; run40300637754 PASS |
| INV-02 scopes / AMFI | `8907f28`, `45a91a7`, `79a26ae` | Already in canonical development; original receipts in PROJECT_STATUS and EXECUTION_STATE |
| Yahoo / PR18 | `daed068adef0ce1ea091dc5efe08d52068f1b77f` | Contains developmentd5cc181; run40325761619 all3 PASS;80 backend/12 metadata/one Chrome/four overlapping Axe/privacy0 |
| Discovery / PR19 | `d8f57bead981abc2647fcc0f94aee2c57550a87b` | Independent base developmentd5cc181;66 backend/12 metadata/one Chrome/four overlapping Axe/privacy0; run40336191319 cancelled |
| Geography implementation | `1c5f11ec9c2f4f476562af0de619f0068cd031df` | Independent base developmentd5cc181, does not contain Discovery;56 backend/12 metadata/one Chrome/four overlapping Axe/privacy0 |
| Geography checkpoint | `dc96b19b03f61409f8803a2928d0e907c8c18292` | Documentation-only successor; no CI; source manifests and cancellation ZIP retained |

Local preparation worktree `F:/ALFRED_DEV/consolidation-review`, branch
`preparation/alfred-consolidation-20261026`: trial merge `c3e0fbd` contains Yahoo,
`060fda8` adds Discovery, `52c71ff` adds both Geography commits. These merges retain
original ancestry for review/rollback; none moves canonical development or master.
Final preparation HEAD is resolved with `git rev-parse HEAD`, not embedded in itself.

All older local development/release/audit branches are ancestors of canonical
development. The only original local branches outside it are the three sources
above. Remote agent/browser-regression-maturity-gate is also outside canonical
ancestry; it is preserved, with no open PR or verified scope acceptance, and is
not silently adopted. No source or branch was discarded.

## Deliberate reconciliation

- Yahoo service, investment API cache revision, styling and standalone tests retain
  PR18 content. Discovery and Geography do not replace investment implementation.
- Career normalization combines Discovery's source status/citations/safe feed rows
  with Geography's unspecified location and explicit worldwide flag. The location
  parser/filter/relevance changes retain country/state restrictions and abstention.
- Career owner cache retains both `discovery-v2` and `geography-v2` revisions and
  recomputes evidence expiry on every response. No owned profile/financial writes.
- Career UI retains safe posting/source URLs and freshness/availability labels,
  plus unspecified-location text, geographic warning, manual-filter focus handling,
  response-query ordering and preservation of unsaved edits. Both templates' copy
  changes coexist. Shared code auto-merged; its result was inspected and tested.
- The only executable merge conflict was the backend test profile. Its union
  explicitly keeps Discovery, Geography and Yahoo test modules once each. Browser
  test auto-merges retain all three original test methods; no assertion removed.
- Requirements preserve both discovery provenance and geography intent. Reference
  matrix retains both Career dispositions and Yahoo evidence. Historical status
  entries remain dated evidence. Current INV-05/CAREER-03 entries and generated
  views are reconciled to describe local preparation versus canonical integration.
  EXECUTION_STATE and CI_PIPELINE_STATE are compact current ledgers; their original
  versions remain recoverable from the untouched source refs and Git bundle.
- AGENTS and the pipeline document the owner's permanent single-branch/PR16
  workflow. Independent reviews, mandatory checks, protections and master/Pages
  authorization remain required; no minor-section PR or protection bypass added.

## Validation and evidence boundary

Fresh PR19 exact-source backend66 PASS, zero skips: original post-audit worktree
`artifacts/ci-repair-ac05515/consolidation-pr19-exact-corrected.json` and log.
The first invocation ran0 tests because of an incorrect settings-module argument;
its diagnostic receipt is retained and never counted as passing evidence.

Consolidated code source52c71ff: **309 backend,19 metadata and3 original Chrome
workflows PASS, zero skips;12 overlapping Axe audits with zero violations**.
Migration drift/system checks and source ancestry/test-body containment PASS.
AST Graphify refresh PASS:11,237 nodes/31,092 edges/506 communities, no LLM call.
Axe color-contrast incomplete and manual screen-reader remain unverified.
Final documentation changes preserve the accepted executable hashes; final clean
source/history privacy must PASS at the resolved preparation HEAD before reuse.
The interrupted expanded metadata attempt has no result and is not counted.

Consolidated candidate receipts are in this worktree's
`artifacts/ci-repair-ac05515/consolidation-*.json` and
`artifacts/consolidation-20261026/`. Final status must be read from EXECUTION_STATE
and source-bound receipts. Pending remote CI and reviews are never called accepted.
Original scope totals overlap and must not be added to candidate totals.
No earlier green CI is transferred to the prepared HEAD.

Original ignored artifacts stay in post-audit and career-geography worktrees.
Discovery manifests: `artifacts/career-discovery-d5cc181/`; Yahoo manifests:
`artifacts/sprint-8f505a3/yahoo/post-pr17/`; Geography manifests:
`artifacts/career-location-d5cc181/`. Recovery bundle/refs/API receipts:
`F:/ALFRED_DEV/consolidation-recovery-20261026/`. No private data/artifacts uploaded.

## Exact blockers and next action

1. All three PR review lists/threads are empty. AGENTS requires independent project
   review. **Stop PR18 merge**, despite exact-head green CI and no GitHub protection.
2. PR19 Selenium check121618292489 explicitly exceeded30m0s. Its final summary step
   was skipped. One targeted retry returned403 Resource not accessible by integration;
   no retry queued. Authorized maintainer CI action and independent review are needed.
3. Geography has no CI/review and diverged from Discovery. Local combined validation
   is preparation; it cannot enter canonical development around the blocked scopes.
4. Authenticated protection GETs return404 Branch not protected; rulesets/effective
   rules are empty for both branches. This resolves earlier visibility uncertainty,
   without changing settings or waiving the independent project-review requirement.
5. Pages publishes publicly from legacy `master:/docs`. Explicit full-scope publishing
   authorization is absent. Master additionally needs full cumulative review, newest
   exact-head CI, source privacy/security and rollback gates. No production deployment.

After gates pass, recheck source/base heads, integrate through permitted mechanisms,
verify canonical containment and new consolidated exact-head CI, and only then close
superseded PR18/19 with original SHAs/receipts. Keep their branches until rollback
evidence is confirmed. No new PR, force push or deletion is necessary.
Stage7 feature selection follows consolidation; it has not been reached.

Original inventory remains **143 IDs,75 verified (52.4%)**; extensions remain
**13 defined,0 accepted**. INV-02, INV-05 and CAREER-03 retain full-capability
limitations. Live provider/terms, real accounts, arbitrary geography/legal work
eligibility, manual screen-reader and packaged/production acceptance remain unverified.
