---
name: alfred-travel-engineering
description: Implement or review ALFRED Travel planning, provider integrations, route choices, trip persistence, or travel-cost behavior.
---

# ALFRED Travel engineering

- Use `AGENTS.md` and a scoped graph query to locate the affected path. Read `docs/TRAVEL_PLANNER.md` for product behavior and `docs/TRAVEL_PROVIDERS.md` for the provider touched by the request.
- Reuse the current Travel service/provider/result structures under `apps/mobility/services/travel/`. Keep provider configuration in untracked local environment files; do not add cloud hosting or commit private trip messages/photos.
- Preserve explicit origin, destination, mode and user choices through planning and persistence. Keep live provider evidence, estimates, unavailable results and fallbacks distinguishable in the existing UI/API contract.
- Preserve the completed Decimal Travel cost behavior recorded in `docs/TRAVEL_T07_VERIFICATION_20261001.md`; do not reintroduce float currency arithmetic at posting boundaries.
- Trace shared callers before changing a provider guard or route helper. Use bounded timeouts and existing retry/cache behavior; provider failure must not manufacture a successful quote or destroy saved plans.
- Verify the affected flow using mocked provider responses and isolated database/cache state, including the relevant failure or explicit-zero case. Browser checks are useful when changing user choices or rendered routes.
- Consult the current master checkpoint for remaining Travel work; earlier verification does not establish completion of newly expanded requirements.
