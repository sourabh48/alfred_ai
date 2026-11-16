# ALFRED workflow and automation brief

Owner request, 16 November 2026: simplify routine use; the application manages memory, travel preferences and scheduled bots. Preserve the research journal and stock search/history. Improve travel discovery, selected-place photos, attractions/hotels, itinerary and route review. Modernize charts and reduce clutter.

## Compact implementation prompt

Inspect current master and relevant unmerged fixes before changing ALFRED. Read AGENTS.md and existing services. Work in an isolated branch; preserve dirty checkouts and personal runtime. Reuse the local Django/Huey, finance, memory, travel, research and UI components. Implement and verify, not just propose.

1. Travel: a request such as “I have a 2-day holiday; plan a trip” should produce a relevant shortlist once the start city is known. Use transparent, editable assumptions for optional budget/style rather than blocking discovery. Selecting a place builds a draft automatically and shows photos, attractions, hotels, map access and next actions. Keep chat, selected destination, itinerary and saved plan consistent. Support further questions and adjustments without losing edits.
2. Photos: accessible selected-place carousel, manual previous/next and keyboard controls, captions/credits, bounded on-demand loading, honest unavailable/error states. Use approved Google Places data; protect keys and owners; never persist restricted photo references or substitute unrelated/generated scenery.
3. Itinerary: reuse existing day editor and route optimiser. Show source-backed road routes separately from estimated ordering. Offer offbeat candidates from real source evidence without claiming popularity or access that is unknown. Preserve route, weather and price limitations.
4. Hotels: offer dated hotel searches, selection/review and external booking continuation. A real reservation requires an authorized booking-capable provider plus explicit confirmation of hotel, room, dates, guests, total price/currency and terms. Show original provider check times and hide expired prices/availability. Revalidate an offer before confirmation; changed dates, guests or price invalidate it. Links are not bookings; never invent availability, payment or success.
5. Memory and bots: routine local maintenance and preference learning are system-managed. Remove training/maintenance tasks from ordinary user flows. Put recovery tools in Health, behind an actual status/problem. Retain minimal privacy, correction, deletion and external-service consent controls. Automated observations must not silently become verified financial facts.
6. Assistant/settings: prioritize conversation, useful suggestions and items needing attention. Group essential settings and move operational detail to Health. Keep existing functions reachable and accessible; avoid decorative controls or new dashboards duplicating current services.
7. Investment: keep search and research journal; make writing a personal thesis optional. Save bounded private search/research history automatically with clear deletion controls. Reuse and validate existing fresh evidence for proactive reviews; abstain from personal/amount recommendations when suitability data is missing. Do not train users or silently alter their holdings.
8. Charts: shared modern styling, meaningful enter/update animation, readable tooltips and responsive sizes; respect reduced motion and retain accurate scales, source descriptions and accessible values.

Test synthetic end-to-end journeys, ownership, stale evidence, missing keys, async cancellation/session switching, saved-plan reopening, mobile/keyboard use and reduced motion. Inspect browser screenshots. Commit locally in reviewable phases. Report exact implemented versus blocked capability and checks; do not push, deploy, install over the owner's app, trade or execute a booking without its specific authorization.

## Scope checkpoint

- Branch: `work/travel-workflow-2026-11-16`, base `1377eff`.
- Existing travel photo/UI work continues; expanded scope is explicitly authorized by the owner's screenshots and message.
- No live provider calls or private runtime inspection are required for implementation/testing.
- Existing integrations provide hotel research links, not a verified reservation API. Real booking capability is an external integration dependency, not a UI completion claim.

The owner has no hotel API account. Follow `LIVE_TRAVEL_SETUP_20261116.md`: evaluate the free Nuitée Connect sandbox first; production credentials, costs, inventory coverage and a tested booking adapter remain separate dependencies. Never ask for API secrets in chat. Daily stock observations must not be labelled real-time quotes.
