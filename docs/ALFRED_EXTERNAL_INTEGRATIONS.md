# ALFRED external integration register

Reviewed 2026-10-15 against source 3932f391aa4eed7b3200ad3b034f7991435e01e4. This is a code/authorization/contract register, not proof that any credential is configured. No secret values, authenticated provider calls, paid requests or private uploads were inspected or executed.

**IMPLEMENTED** means source adapter; **CONFIGURED** requires a safe actual runtime configuration check; **REAL-LIVE-TESTED** requires a dated receipt with actual provider/account scope. Mock acceptance never becomes real acceptance. Account-specific limits, regions and contracts remain unverified unless explicitly stated.

## Register

| Provider | Feature / source | Code status | Authorization / actual verification | Credential / cost / free usage | Limits, cache, privacy and next action |
| --- | --- | --- | --- | --- | --- |
| Ollama, loopback only | Inference/embeddings; local_embeddings.py, hybrid_intelligence.py | IMPLEMENTED | Historical actual local restart/retrieval plus synthetic contracts; current live app unavailable | Installed local models; no paid API; device compute/storage cost | Fixed loopback, no remote/cloud model; context/response/digest validation. Accept model availability on each target PC |
| OpenAI Responses | memory_reasoning.py | IMPLEMENTED, synthetic-only provider acceptance | Real access DISABLED; operator + owner + per-request public consent required | Restricted encrypted owner key; current pinned rates below; no free use assumed | Public-query-only; fixed endpoint, deadlines/output/usage/budgets, no private finance. Model retirement decision and separately approved paid acceptance |
| AWS S3 | memory_cloud.py | IMPLEMENTED; signed synthetic S3 accepted | No selected real bucket/account/region; real sync DISABLED | Restricted IAM/session credentials in encrypted owner vault; storage/request/egress region costs, no free-tier entitlement assumed | AWS virtual-host endpoint restrictions, expected owner, private bucket/account checks, conditional writes, client-authenticated ciphertext + SSE. Not a generic arbitrary endpoint adapter |
| Mock cloud / local S3 wire fixture | memory_sync.py, tests/memory_s3_fixture.py | IMPLEMENTED / SYNTHETIC | Synthetic only; not off-device protection | No real credential/billing | Exercises corruption, conflicts, delete/retry/restart. Do not display as real sync |
| Azure / Google Drive / OneDrive memory sync | No adapter demonstrated | NOT AVAILABLE | Not approved/selected | Unknown; requires product/provider choice | Existing manual recovery staging is not a sync adapter; do not add cloud wiring implicitly |
| Open-Meteo weather/geocoding | travel/providers/weather.py, geocoding.py; verified_intelligence.py | IMPLEMENTED | Public source historical/fixture evidence; new real requests NOT_RUN | Free noncommercial API; paid commercial plans; no key on basic free endpoint | Current published free limits below. Forecast horizon, cache and UNKNOWN guards; query locations leave device |
| OpenRouteService | travel/providers/routing.py | IMPLEMENTED, REQUIRES CREDENTIALS | Current account/key/live acceptance not established | API key; account plan governs costs/quotas | Current plans page requires interactive rendering; quotas are UNVERIFIED here. Earlier 2,000/day and 40/min are dated guidance, not guaranteed current rights. Real alternate/bike-legal routes incomplete |
| Duffel Stays | travel/providers/accommodation.py | IMPLEMENTED, REQUIRES CREDENTIALS/CONTRACT | Disabled without approved account/service access; NOT_REAL_LIVE_TESTED | Bearer token, commercial service/contract/search charges | Source result freshness/expiry and disabled states; no fake hotel availability. Accept private synthetic traveler searches only after approval |
| Duffel Flights | travel/providers/transport.py | IMPLEMENTED, REQUIRES CREDENTIALS/CONTRACT | Disabled without authorization; NOT_REAL_LIVE_TESTED | Bearer token, commercial/search/booking charges | No automatic booking/payment; search-budget opt-in and freshness. Current excess-search policy below |
| Indian Rail / IRCTC | IndianRailProvider | UNAVAILABLE for live inventory | REQUIRES CONTRACT; provider always reports unavailable | Authorized distribution/API contract; price/rate unverified | User-provided timetable ≠ available seat/fare/waitlist. No unauthorized scraping |
| Bus operators / aggregators | travel/links.py | Link-outs only; no inventory adapter | NOT AVAILABLE / provider decision needed | Unknown contract/API | Link-outs cannot be advertised as live availability |
| Permit authorities | travel/providers/permits.py | Dated reference lookup | No verified live permit-availability provider | Official authority-specific rights/fees | Cite effective date/URL; no invented permit/road closure availability |
| Brave Search | travel/providers/web.py | IMPLEMENTED | Keyed contact/paid/storage opt-ins required; real acceptance not established | API key; published search pricing below | Query privacy and plan-specific storage rights. Third-party page rights are separate; do not train/cache unlawfully |
| SearXNG | travel/providers/web.py | IMPLEMENTED | Operator-selected approved instance required; no blanket instance consent | Instance authentication/hosting costs as configured | Instance/upstream engine terms, destination allowlist and retention must be checked |
| Wikivoyage / Wikimedia | travel/providers/web.py | IMPLEMENTED public research | Historical public discovery evidence; this audit made no new Travel query | Generally public read APIs, no purchased inventory | Attribution/license and current endpoint limits matter; travel prose is research, not real-time booking evidence |
| Overpass / OpenStreetMap POIs | travel/providers/places.py | IMPLEMENTED | Optional queries; no booking inventory | Public fair-use endpoints; no quota/SLA promise | Bounded query, attribution, freshness; no verified camping availability from a POI |
| OpenStreetMap tiles / Leaflet | travel/mapping.py; static UI | IMPLEMENTED opt-in tiles/local geometry | Actual current provider acceptance NOT_RUN | Public policy applies; not unrestricted free bulk map storage | No bulk offline prefetch; attribution. Geometry usable without external tiles |
| Google Maps | travel/links.py | External link-outs, not authenticated Maps APIs | No full provider selection/acceptance | Keys/billing needed only if separately implemented | Do not call link-outs a Google routing/offline dataset integration |
| AMFI NAV/history | investments/services/portfolio_intelligence.py | IMPLEMENTED bounded public fetch/cache | Historical/fixture evidence; current real check NOT_RUN | Public data; permission/terms/current throttles unverified | Eight-hour application cache and failure cache are implementation settings, not licensed redistribution rights |
| Yahoo Finance / yfinance | verified_intelligence.py, portfolio_intelligence.py | IMPLEMENTED optional adapter | Current reliability/terms acceptance NOT_RUN | Public/third-party library behavior; no commercial entitlement inferred | Quotes/history may be cached/stale/unavailable; not broker execution or guaranteed live market feed |
| World Bank | verified_intelligence.py | IMPLEMENTED public indicator | Current real provider check NOT_RUN | Public indicator API; no commercial rate assumed | Macro publication lag is not real-time finance; show source/year/freshness |
| Google News RSS | verified_intelligence.py | IMPLEMENTED public news discovery | Current terms/reliability acceptance NOT_RUN | No account contract proven | Headlines/context are not licensed full-text training or proven forecasts |
| Remotive / Arbeitnow / RemoteOK | verified_intelligence.py and career/job_intelligence.py | IMPLEMENTED feeds | Actual geography/coverage/current terms acceptance incomplete | Public feeds, terms/rates not currently verified | Role/geography filtering and source links; no automatic job applications or comprehensive local market |
| JSON-LD / Greenhouse / Lever / Workday / Ashby job pages | career/job_intelligence.py | IMPLEMENTED parsing adapters | URL-specific permission/current layouts need acceptance | Public accessible page does not imply unrestricted automation rights | Shared safe HTTP, bounded parse and no login bypass/scraping escalation |
| Credit bureaus | credit_score_tracker.py / credit_report_parser.py | Uploaded evidence + labelled estimates; live official connection unaccepted | REQUIRES CONTRACT / consent | Bureau/account-specific authentication and cost unknown | Never save estimates as official pulls; uploaded personal reports remain owner scoped |
| Gmail / Outlook / IMAP | integrations/services/email_integration.py; EmailConnection | PARTIAL / legacy helper unsafe | Automatic mail onboarding/live acceptance absent | OAuth/IMAP permissions, approved credentials | Unrouted Gmail helper writes plaintext token JSON; must be retired/replaced with encrypted model before use |
| Google speech / gTTS | ml_engine/services/voice_assistant.py | Legacy optional service, no routed workflow demonstrated | No approved live voice acceptance | External audio/text requests if activated; cost/retention unverified | Prefer local speech; explicit consent before external processing |
| GitHub Actions / Pages | .github/workflows/browser-regression.yml; docs site | IMPLEMENTED PR/manual CI + documentation site | Fresh remote SHA matches M15; Pages run does not prove application CI | Account CI minutes/storage rules; current limits unverified | No runtime/private source upload; M20 CI publish/settings need authorization. Documentation hosting is not app hosting |

Paths abbreviated in the table resolve under apps/ unless otherwise stated; full verified source references are in the [feature matrix](ALFRED_MASTER_FEATURE_MATRIX.md).

## Verified official pricing/lifecycle facts

The pinned OpenAI model is gpt-4.1-mini-2025-04-14. Official documentation lists $0.40 uncached input and $1.60 output per million tokens, matching the current conservative reservation constants. It was deprecated on 2026-10-14 with removal scheduled for 2027-01-14. A replacement requires an explicit model/quality/rate decision; no adapter model was changed. [Model page](https://developers.openai.com/api/docs/models/gpt-4.1-mini), [deprecation schedule](https://developers.openai.com/api/docs/deprecations).

OpenAI store:false is not a guarantee of zero retention: default abuse-monitoring logs can retain content up to 30 days, with account-specific controls/exceptions. The public-only gate remains necessary. [Official data controls](https://developers.openai.com/api/docs/guides/your-data).

Open-Meteo currently publishes free noncommercial limits of 600/minute, 5,000/hour, 10,000/day and 300,000/month, without an uptime guarantee. Paid commercial access is a separate plan/account. Request weights and actual account rights must be considered before activation. [Official pricing](https://open-meteo.com/en/pricing).

Brave advertises Search at $5 per 1,000 requests with $5 monthly credits and 50 queries/second. These are published plan facts, not a verified user entitlement or unrestricted content-storage right. Its privacy notice describes query logging for up to 90 days; storage/training rights require review of the applicable plan/terms. [Official Search pricing](https://brave.com/search/api/), [privacy notice](https://api-dashboard.search.brave.com/documentation/resources/privacy-notice).

Duffel's documented excess-search allowance is one booking per 1,500 searches, with $0.005 per excess search. Specific Stays/Flights services, fees and account eligibility need approved contract review; the application should not assume its requests are free. [Official excess-search policy](https://help.duffel.com/hc/en-gb/articles/4412912264466-What-is-Excess-Search), [pricing](https://duffel.com/pricing).

AWS documents If-None-Match for creation and If-Match for ETag-conditioned updates with SigV4 and required object permissions. Application synthetic CAS tests are compatible in design; real bucket policies/races/owner permissions remain unaccepted. Storage/requests/egress are region/account-specific; no fixed price was verified for an unselected destination. [Official conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).

Current ORS plan numbers were not readable from the fetched interactive [official plans page](https://account.heigit.org/info/plans); keep them UNVERIFIED rather than recycling old limits.

## Safe activation procedure

1. User selects provider/account/location and explicitly approves the operation scope and cost.
2. Review current model/contract/license, per-account quotas, data retention and cache/storage rights.
3. Provision least-privilege credentials through masked/encrypted house tooling; never chat, Git, markup, process arguments or plaintext files.
4. Prove owner namespace/consent, authenticated encryption, key/checkpoint recovery and deletion/retention behavior.
5. Run capped synthetic-only real acceptance: timeouts, offline/retry, partial/corrupt response, conflicts, account isolation and source freshness.
6. Record exact source, provider/account reference without secrets, date, costs and limitations.
7. Keep activation separate from application release approval. Never export raw private SQLite/WAL/SHM or recovery keys through memory synchronization.

No new external storage destination was invented and no cancelled key-sealing dialog was restarted.
