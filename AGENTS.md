# Local Hosting Guidance

## Codex execution protocol

- Start with `docs/EXECUTION_STATE.md`, `git status -sb` and actual HEAD. Read
  relevant `docs/ALFRED_2_0_REQUIREMENTS.md` and queued task scope before editing.
- `continue`: resume the current incomplete step; if finished, report
  READY_FOR_NEXT and stop. Never select another task automatically.
- `next`: finish/checkpoint or explicitly defer the current task, then select one
  eligible task from `docs/EXECUTION_QUEUE.md`; stop when completed or blocked.
- `status`: read-only Git/PR/task/baseline/extensions/blocker report; no mutations.
- `sprint`: continuous safe queue selection during this active execution, using
  the branch, commit and push flow below. While long CI runs independently, keep
  coding in the worktree. Reconcile at milestones; never idle-poll, transfer green
  checks between SHAs, or call CI_PENDING fully accepted. Explicit `sprint`
  authorizes continuous selection only during that active execution.
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
- TradingAgents (Apache-2.0): the owner approved (2026-11-12) an independent,
  role-based implementation of its analyst, bull/bear researcher and risk-manager
  roles on the local model. Reusing its Python engine through a thin consent,
  evidence and data adapter is optional; isolate/test any dependency conflicts.
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

## Branch, commit and push flow (owner decision 2026-11-12)

- Work in a fresh git worktree branched from current `origin/master`. Never edit
  the owner's main checkout or personal runtime; test with synthetic, isolated data.
- Commit locally after each fix or phase. Push to master only after a whole phase
  is complete, or to fix CI, and only with the owner's OK for that push. Do not
  create or reopen a pull request unless the owner asks; preserve all source
  branches and commits. Master integration/publication still needs its separately
  required checks, reviews and authorization.
- Commits and pull requests carry only the owner's name: no co-author, tool or
  AI attribution lines.
- `docs/CI_PIPELINE_STATE.md` records section state, branch/source/base/run,
  local evidence, CI, dependencies/reviews/publication blockers, push SHA,
  post-push checks and recovery action. EXECUTION_STATE owns active coding.
- States: SELECTED → IMPLEMENTING → LOCAL_TESTING → LOCAL_ACCEPTED →
  COMMITTED_PUSHED → CI_PENDING → CI_PASSED/CI_FAILED; then MERGE_BLOCKED or
  MERGE_READY → MERGED → POST_MERGE_VERIFYING → MERGED_VERIFIED.
  BLOCKED_APPROVAL/BLOCKED_EXTERNAL stay explicit; CI_PENDING is at most 95%.
  Bounded acceptance never automatically verifies its parent capability.
- Pin source/base/dependencies and test receipts for each scope. Reconcile
  overlapping code and documentation deliberately, retaining accepted behavior.
  Record exact blockers and stop a blocked push; continue only safe preparation
  and validation.
- Recheck exact source/base/merge-base and complete diff, required CI with no invalid
  skips, independent reviews (including project rules), protection/rulesets,
  privacy/security, compatibility/rollback, dependencies and authorized publication.
  Do this before every push; a newer master HEAD invalidates an older readiness claim.
  Preserve existing cancellation/coverage policy unless a measured regression
  justifies a reviewed change.
- Before master integration verify Pages source/workflows and obtain explicit
  publishing authorization for the full concrete scope. Development integration
  does not authorize Pages or application deployment. Changed publishing
  consequences need new approval; application deployment remains separate.
- Never repeatedly retry denied access or silently waive governance/reviews.
- Confirm master source containment and post-push CI; investigate failures before
  healthy-integration claims. Synchronize safely without reset/rebase/force,
  preserve worktrees and update README/status/state/pipeline.
- Remove temporary worktrees/branches only after verified containment and
  rollback evidence; preserve dirty work and never delete unmerged sources.
- Merging never authorizes production or publication beyond the approved scope.

## Owner decisions in force

- Credit score is descoped (2026-11-12): FIN-17 is OWNER_DESCOPED and the 143
  original count stays 143. A card's credit limit is not a credit score.
- Local AI limits are configurable in `config/local.env` (`ALFRED_OLLAMA_*`,
  `ALFRED_LOCAL_AI_*`, `ALFRED_DOCUMENT_KNOWLEDGE_*`) with generous defaults.
  Ollama must stay on this PC or a private LAN address; owner isolation and
  citations always apply.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost). On this Windows host run graphify through the uv tool's Python (`~/AppData/Roaming/uv/tools/graphifyy/Scripts/python.exe -m graphify ...`), because Application Control blocks `graphify.exe`.
