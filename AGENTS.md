# Local Hosting Guidance

## Codex execution protocol

- Start with `docs/EXECUTION_STATE.md`, `git status -sb` and actual HEAD. Read
  relevant `docs/ALFRED_2_0_REQUIREMENTS.md` and queued task scope before editing.
- `continue`: resume the current incomplete step; if finished, report
  READY_FOR_NEXT and stop. Never select another task automatically.
- `next`: finish/checkpoint or explicitly defer the current task, then select one
  eligible task from `docs/EXECUTION_QUEUE.md`; stop when completed or blocked.
- `status`: read-only Git/PR/task/baseline/extensions/blocker report; no mutations.
- `sprint`: continuous safe queue selection during this active execution. Commit
  locally validated isolated section PRs, then code the next eligible independent
  scope while CI runs. Reconcile at milestones; never idle-poll, transfer green
  checks between SHAs, or call CI_PENDING fully accepted.
- Follow phases IMPLEMENTED_NOT_ACCEPTED → PARTIALLY_IMPLEMENTED → BLOCKED
  (approval/external) → NOT_IMPLEMENTED, module-by-module. Skip only actual
  blockers; document later-phase prerequisite exceptions. Do not repeat verified work.
- PROJECT_STATUS owns exactly 143 original IDs and evidence; requirements own
  intent, the queue owns selection, EXECUTION_STATE owns the compact checkpoint.
  New 2.0 stories have a separate ledger. Never inflate verification from source presence.
- Persist weighted progress/evidence/refs/dirty work/next command after milestones
  and before interruption. Preserve uncertain/uncommitted work and staging choices.
- Run `scripts/project_execution.py --check` with the configured SDK after tracker
  changes; use `--write` only for its generated views. Do not regenerate unrelated docs.
- No production, Pages/protection change, unapproved merge, private history/upload,
  paid/new credentials, currency/valuation change, privileged runtime change,
  destructive operation or security/AI weakening without explicit approval.
  Private knowledge Git sync stays disabled. Source acceptance is not release approval.

- ALFRED is a local or LAN-hosted application in this repository.
- Do not add cloud deployment wiring, cloud credentials, or cloud-specific
  runtime templates without an explicit new decision.
- Keep runtime secrets in untracked local environment files such as
  `config/local.env`.

## Permanent upstream adoption contract

- For a relevant selected scope read `docs/UPSTREAM_REFERENCE_MATRIX.md` and
  `docs/ALFRED_2_0_INTEGRATION_ARCHITECTURE.md`. Pin upstream branch/SHA, verify
  component license, inspect source/tests/dependencies, compare accepted ALFRED
  behavior, and record exactly one disposition, target IDs and validation.
  Uninspected behavior is UNVERIFIED. Do not duplicate accepted services.
- Aurelio: algorithm reference only; independently refine canonical Decimal and
  reconciliation services. Never integrate its application/runtime/FX policy.
- TradingAgents: compatible Python engine reuse first through a thin consent,
  evidence and data adapter. Preserve analyst/debate/risk/memory/recovery/backtest
  engines; isolate/test dependency conflicts rather than rebuilding the framework.
- TREK: AGPL-3.0 inspiration, independent Django implementation only. No source,
  bundle or asset copying without license approval. Preserve desktop/accessibility,
  motorcycle evidence and approved maps; exclude collaboration/public sharing,
  settlements and mobile-specific expansion.
- Career Ops: `https://github.com/career-ops-hq/career-ops` is resolved. Port useful
  MIT business workflows incrementally into existing Django Career; attribution
  for adapted code. No permanent Node/Go backend or CLI-infrastructure conversion.
- The existing queue alone selects work: 143 original IDs and 13 extensions stay
  separate. Mapping is not integration/live accuracy. No implicit provider, cloud,
  private disclosure, sending, booking, trading or financial-record mutation.

## Non-blocking section pipeline

- `docs/CI_PIPELINE_STATE.md` records section state, branch/source/base/PR/run,
  local evidence, CI, dependencies/reviews/publication blockers, merge SHA,
  post-merge checks and recovery action. EXECUTION_STATE owns active coding.
- States: SELECTED → IMPLEMENTING → LOCAL_TESTING → LOCAL_ACCEPTED →
  COMMITTED_PUSHED → CI_PENDING → CI_PASSED/CI_FAILED; then MERGE_BLOCKED or
  MERGE_READY → MERGED → POST_MERGE_VERIFYING → MERGED_VERIFIED.
  BLOCKED_APPROVAL/BLOCKED_EXTERNAL stay explicit; CI_PENDING is at most 95%.
  Bounded acceptance never automatically verifies its parent capability.
- Maximum three outstanding integration candidates initially, including cumulative
  PR #16; one active coding scope, isolated branches/worktrees. Distinct PR refs
  isolate workflow concurrency. Do not push unrelated sections into a testing PR,
  disable cancellation or change coverage/sharding without regression evidence.
- Use verified bases; explicitly stack dependent PRs and pin their base SHA.
  Retarget/revalidate against eventual master before merge. Never call a stacked
  or cumulative diff independent of its prerequisites.
- Reconcile at task selection, local acceptance, push, pre-merge and handoff.
  No polling daemon is needed: use existing GitHub tooling. At the candidate cap,
  reconcile/repair, prepare safe local work, or checkpoint instead of spinning.

## ALFRED — conditional automatic section merge policy

- Owner's 2026-10-26 contract supersedes the former manual-owner-only merge rule.
  Codex owns implementation/tests/CI repair, section commits/development pushes
  and automatic scoped merges ONLY when every required gate passes.
- Recheck exact source/base/merge-base and complete diff, required CI with no invalid
  skips, independent reviews (including project rules), protection/rulesets,
  privacy/security, compatibility/rollback, dependencies and authorized publication.
  PR #16 requires its entire cumulative diff reviewed; it is not an isolated slice.
- Before the first automated merge verify Pages source/workflows and request
  explicit publishing approval for the concrete scope. Changed consequences need
  new approval; application deployment remains separately prohibited.
- All gates pass: READY_TO_MERGE YES, perform a supported protection-compliant merge.
  Native auto-merge only if enabled and all non-CI gates already pass. Otherwise
  report NO, exact blockers/responsible party, and preserve the PR. Never repeatedly
  retry denied access or silently waive governance/reviews.
- Confirm GitHub merge/master source containment, merge SHA and post-merge CI;
  investigate failures before healthy-integration claims. Synchronize safely without
  reset/rebase/force, preserve worktrees and update README/status/state/pipeline.
- Merging never authorizes production or publication beyond the approved scope.
  `continue` resumes integration; `next` selects one scope; explicit `sprint`
  authorizes continuous selection only during that active execution.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
