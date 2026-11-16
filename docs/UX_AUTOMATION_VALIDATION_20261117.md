# Workflow automation validation — 17 November 2026

## Scope and source

Local implementation in `F:\ALFRED_DEV\travel-workflow-1116`, branch `work/travel-workflow-2026-11-16`, based on `1377eff37191d61ea190b9d5f261c36f89987ab2`. Implementation commit `2213702f590b6bad20981771ba9812ef9fdefd40`; checks ran on the identical precommit code files. Bounded workflow acceptance only: this is not a full-repository clean bill of health or release approval. Tests used disposable databases/media with inherited provider credentials removed. No real user data was migrated, no provider account was created, and no booking/trade/push/deployment occurred.

The primary checkout remains on `1377eff` with its existing dirty `alfred_ai/services/materialized_cache.py` preserved. The clean `owner-decisions-1112` repair branch remains at `2987931`, 21 commits ahead of this base. The fund-price fix from `f3976cb` was deliberately reused; the chart-theme defect addressed in `4ce8991` was also corrected here. Other repair-branch changes are not implicitly included.

## Implemented and verified

- Travel: once origin and duration are known, a transparent mid-range assumption allows a shortlist without another budget question. Choosing a destination builds a draft and queues selected-place research. Suggestions support attractions, stays and offbeat research. Existing day editing, route comparison, maps and saved-trip reopening remain available.
- Photos: selected-place carousel with keyboard controls, author credits, bounded requests, fresh Google photo references and no persisted image bytes. The owner-scoped endpoint accepts only places in that trip; API keys stay server-side. Missing credentials or uncertain place identity yields an unavailable state.
- Usability: routine memory and travel-style maintenance is described as automatic. Privacy, correction, deletion and external-service consent remain reachable. Manual bot recovery, model readiness and memory evaluation are in Health; assistant answer/source controls are folded. The assistant welcome has useful trip/research/attention links.
- Charts: shared current-theme palette, restrained animation and runtime reduced-motion support. Existing financial scales/definitions remain unchanged.
- Research: stock and market-symbol searches retain at most 20 owner-private history entries. The existing scheduler reviews up to three daily; a personal journal thesis is optional. Clear history/account reset removes these records, and a late background result cannot resurrect or overwrite a newer search. The additive `investments.0010_researchsearch` migration has only been applied to synthetic test databases.
- Freshness: explicit daily-feed labels, original cached fetch times, refresh on lookup, stale/future/nonfinite evidence guards and currency-consistent ratios. Stale/conflicting AMFI NAVs cannot revalue holdings or produce hold/sell guidance. Expired hotel evidence hides old price and availability values.

## Local evidence

Paths below are local receipts outside the source tree. Runs overlap; counts must not be summed as unique coverage.

| Receipt in `F:\ALFRED_DEV` | Result / scope |
|---|---|
| `ux-backend-acceptance.log` | 191 PASS, 196.253 s: travel/providers/photos, research, bots, user-data and release-validation checks |
| `ux-final-backend-delta.log` | 66 PASS, 60.395 s after fund-price reuse and freshness guards |
| `ux-research-final.log` | 10 PASS, 0.981 s after the background-failure concurrency fix |
| `ux-browser-final-report.json` | All 17 travel/workflow tests PASS; the additional assistant test initially stopped because the worktree lacked CI's axe scanner |
| `ux-assistant-contrast-final-report.json` | 1 PASS, 22.777 s suite: keyboard/retry, desktop/mobile, light/dark; zero automated WCAG violations in all four views |
| `ux-browser-secondary.log`, `ux-browser-final-fixes.log` | Focused journal, memory evaluation, model readiness, research packet, knowledge-pack and privacy flows passed across targeted runs |
| `ux-migration-final.log` | `makemigrations --check --dry-run`: no changes detected |

Initial browser failures from obsolete Build-itinerary/Settings expectations and stale finance fixtures were corrected. The assistant rerun found a real light-theme link contrast failure; the heading link now uses the theme's readable ink colour. Its focused rerun passed. Expected synthetic outage, conflict and cancellation logs are retained in receipts.

Changed JavaScript passed `node --check`; `git diff --check` passed. Browser durations include measured new/renamed tests. Collection-only CI planning found exactly 229 tests and assigned all of them to three shards (75/77/77); its inventory exactly matches the timing manifest. This is not a full browser-suite run. `scripts/project_execution.py --check` passed with no capability-ledger changes. Screenshots and accessibility results are in `F:\ALFRED_DEV\ux-browser-1116`; the photo carousel tests use a clearly synthetic image fixture, not live destination imagery. AST-only graph refresh completed (16,118 nodes, 46,072 edges); graph community labels were not regenerated with an external model.

## Existing release artifacts — read-only verification

The `owner-decisions-1112/artifacts/windows-release-20261115` manifest records clean source `1377eff`. Both outer hashes match the manifest and SHA256SUMS:

- `ALFRED-Setup.exe`, 450,258,535 bytes: `83be069ca1153c0e0a6a019f91fb8b0e1630acd177ba42dd57601b063ce689e5`. Authenticode reports **NotSigned**.
- `ALFRED-Windows-x64.zip`, 503,043,348 bytes: `deb836b9ddad38e1e33b57a5731164122cd67f827195afa0bf474f5fd451b204`.
- ZIP: 11,958 entries; CRC check passed; no absolute/traversal entry names; both bundled executable hashes match the manifest. No `.env`, `local.env` or runtime SQLite filenames were found. This is not a full binary secret scan.

These packages do not contain this workflow implementation. Neither installer nor bundled executable was launched during this phase. Install/uninstall, upgrade, reboot and real-user packaged acceptance remain unverified.

## Prioritized remaining gaps

1. **Live hotels/booking — BLOCKED_EXTERNAL.** Google supplies listings/photos, not room inventory. No booking API account or reservation adapter is connected. Follow `LIVE_TRAVEL_SETUP_20261116.md` to evaluate Nuitée's sandbox, then eligibility, coverage, production costs and a tested Rates → Prebook → confirmed booking integration. Sandbox fixtures and external links cannot prove live availability.
2. **Real-time investment quotes and suitability — not implemented by this change.** The current public feed provides daily observations. Proactive research is evidence review, not a personalized amount recommendation or an executable quote. Genuine forecasting/agent quality still needs independent evaluation; no new TradingAgents engine or model training is claimed.
3. **Integration/release — pending.** Reconcile this branch with the unmerged audit repairs before release, especially public-query privacy, streaming-test isolation and additional bot changes. Do not overwrite either branch. Obtain the owner's authorization before master push/deployment or applying the new migration to personal runtime.
4. **Broader acceptance — unverified here.** The reported complete-backend order-dependent `test_local_chat_stream` failure and historical full-browser errors were not rerun as whole suites in this phase. The repair branch has a streaming-test isolation commit (`e6fac16`), but its presence is not verification on this branch. Run the full exact-source suite and packaged checks after integration; then install/upgrade/uninstall in a disposable Windows environment.
5. **Live travel quality — pending.** Test configured Google services with real trip dates, image credits, route applicability and hotel coverage. Offbeat suggestions remain sourced leads; access, weather and route suitability are not guarantees. Scheduled work runs while the native worker/scheduler is available.

The compact owner-approved implementation brief is `UX_AUTOMATION_BRIEF_20261116.md`. No original capability-ledger status or percentage was inflated for this bounded phase.
