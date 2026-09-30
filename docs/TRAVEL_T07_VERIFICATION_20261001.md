# Travel T07 verification — 1 October 2026

Branch: codex/native-runtime-hardening-20260918. Validation base commit:
e68e8fd1c49085ed714b315d7982b77a7554b334. Implementation committed as 46113c968b1e6d85d4c0d05cbcfa0270174a5a56.
This follows the completed [earlier validation](TRAVEL_CONTINUATION_VERIFICATION_20260930.md).
The September frozen candidate and the earlier 517-pass full backend suite predate T07.

## Change

Itinerary edits reuse the existing Decimal helpers for stay reductions, low/high
ranges and targets. A ₹1,006 stay allowance becomes ₹755 after a 25% reduction,
using half-up rounding. Whole-rupee per-person targets use the same rounding order
as initial budgets. Edited category totals, daily totals and line-item ranges agree;
the original emergency buffer and unrelated days remain intact. Legacy plans without
line items keep matching low/minimum and high/comfortable aliases.

Selected quote filtering accepts exact decimal strings and normalizes older numeric
quotes to strings. Currency, whole-trip scope, availability, source and aware expiry
guards remain. Malformed evidence cannot crash an otherwise valid estimated plan.
Quotes stay separate from estimates. The shared quote serializer rejects scale above
28 fractional digits to bound exponent expansion; it does not round provider prices.
Provider normalization failures remain visible as malformed_response.

Changed runtime files: apps/mobility/services/travel_itinerary.py,
apps/mobility/services/travel/costs.py, apps/mobility/services/travel/money.py.
Regression files: tests/test_travel_planner.py and tests/test_travel_providers.py.
No model/schema/provider selection/configuration change; no new migration.

## Validation

All Python commands use F:\ALFRED\.venv\Scripts\python.exe from PyCharm after
get_python_environment(filePath="manage.py"). Backend/browser validation uses the
isolated environment documented in the earlier report and continuation state.

1. Before implementation, three new regressions reproduced 2 assertion failures and
   1 error, 0 passed, 0 skipped, 3.070 s. artifacts/travel-t07-before-20261001.log.
   Command: manage.py test tests.test_travel_planner.TravelPlannerTests.test_budget_edit_rounds_half_up_and_preserves_totals tests.test_travel_planner.TravelPlannerTests.test_edit_normalizes_decimal_budget_target_like_initial_budget tests.test_travel_providers.TravelCostBikeTests.test_current_quote_preserves_decimal_precision_without_replacing_estimates --noinput --verbosity 1
2. Focused checks passed 10, failed 0, skipped 0, 6.276 s.
   artifacts/travel-t07-focused-20261001.log.
   Command: manage.py test tests.test_travel_providers.TravelCostBikeTests tests.test_travel_planner.TravelPlannerTests.test_budget_edit_rounds_half_up_and_preserves_totals tests.test_travel_planner.TravelPlannerTests.test_edit_normalizes_decimal_budget_target_like_initial_budget tests.test_travel_planner.TravelPlannerTests.test_budget_edit_decreases_cost tests.test_travel_planner.TravelPlannerTests.test_day_edit_after_hotel_research_survives_recheck --noinput --verbosity 1
3. Full travel backend passed 95, failed 0, skipped 0, 78.424 s.
   artifacts/travel-t07-backend-20261001.log.
   Command: manage.py test tests.test_travel_providers tests.test_travel_planner tests.test_travel_continuation tests.test_travel_http tests.test_travel_web --noinput --verbosity 1
4. Chrome travel workflows passed 3, failed 0, skipped 0, 34.977 s (44.328 s runner).
   artifacts/travel-t07-browser-20261001.log and
   artifacts/browser-travel-t07-20261001/browser_regression_summary.json.
   Command: scripts/run_browser_regressions.py tests.test_travel_planner_browser --browser Chrome --require-browser --artifact-dir artifacts/browser-travel-t07-20261001 --proof-label travel-t07-20261001
5. Command: manage.py check. Exit 0, no issues;
   artifacts/travel-t07-check-20261001.log. git diff --check also passed.
6. Source-native offline probe passed startup/migrations, saving, scoped edits,
   queued-research recovery and saved context through restart. Handoff: 0.078 s.
   Command: scripts/verify_travel_runtime.py --report artifacts/ops/travel-t07-source-runtime-20261001.json
   Providers disabled using the exact environment in the earlier verification report.
   Zero sources checked; weather UNKNOWN. Log: artifacts/travel-t07-native-20261001.log.
   Disposable data only; no real user database/configuration changed.

## Continuation

T07 is complete. Next independent work is T09 telemetry retention, preserving
current-month quota accounting and provider evidence/cache records. No new live
provider proof, key requirement, booking capability or release promotion is claimed.
Rebuild and reverify the frozen candidate before promoting a release with T07.
