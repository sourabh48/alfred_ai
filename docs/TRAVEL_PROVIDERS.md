# Travel provider policy and architecture

Policy review: 29 September 2026. ALFRED remains a local/LAN application. The
planner sends public place/date/route search parameters, not conversations,
vehicle registrations, private history or photographs, to providers. Put secrets
in untracked `config/local.env`.

Source and native startup now read that file under the selected runtime data
directory. Process variables win over `config/local.env`, which wins over legacy
`.env`; native signing secrets remain in `config/native.env`. Restart the server
and worker after changing provider configuration. The staff usage panel displays
provider/category configuration status without credentials.

The existing planning session, research outbox, revision checks and evidence
models remain. `services/travel/cache.py` uses `VerifiedExternalInsight` for
normalized results and `TravelProviderState` / `TravelProviderRequest` for shared
leases, backoff, application budgets and usage. Fresh cache results are
RECENTLY_VERIFIED; expired fallback is CACHED with UNKNOWN confidence. LIVE means
a successful current API response, never guaranteed real-world conditions.

Money normalization preserves provider amounts as decimal strings, without assuming
that every currency has two decimal places. Values must be finite, nonnegative and
below the numerical input bounds in their supplied currency (one billion for the shared helper;
100 million for the selected whole-trip INR quote list). Quote serialization accepts
at most 28 fractional digits; excessive exponent expansion is rejected, not rounded.
Adapter normalization errors surface as `malformed_response`. Current compatible
selected quotes remain separate evidence and never replace estimated allowances.

| Category | Adapter / configuration | Cache | Terms and limitations |
| --- | --- | --- | --- |
| Geocoding | Open-Meteo / GeoNames | 90 days | Global place search; ambiguous names require selection |
| Routing | openrouteservice; `TRAVEL_ORS_API_KEY` | 5 days | Car/walking, highway/toll avoidance; car routes do not verify motorcycle legality or closures |
| Weather | Open-Meteo | 2 hours | Complete daily forecast within 16 days; official warnings unavailable |
| POIs | Overpass; `TRAVEL_OVERPASS_URL` | 7 days | Authorized/self-hosted instance required; OSM tags do not confirm opening, permits or availability |
| Permits | Dated official references | 6 hours near departure, otherwise 24 hours | No authorized live permit inventory API verified; opening remains unverified |
| Hotels | Duffel Stays | 15 minutes, capped by offer expiry | Live account and Stays access required; search result needs rate confirmation |
| Flights | Duffel Flights | 15 minutes, capped by offer expiry | Participating airline offers; recheck before purchase |
| Indian rail | Unavailable boundary | None | Authorized agreement/API required; timetable never implies seats, waitlist or fare |
| Bus | External operator/search links | None | No live inventory integration; availability unknown |
| Destination discovery | Wikivoyage | 14 days | Geotagged community guides, incomplete coverage; seed catalogue fallback |
| Web research | Brave / authorized SearXNG / Wikivoyage fallback | 6 hours; 30 minutes for inventory-related leads | Search snippets are unverified leads, not current rules or availability |

No-key wiki discovery/search is enabled by default; set `TRAVEL_WEB_ENABLED=false`
to disable those wiki requests. Optional broad search requires either
`TRAVEL_BRAVE_API_KEY`, `TRAVEL_BRAVE_STORAGE_ALLOWED=true` and
`TRAVEL_BRAVE_ALLOW_PAID_SEARCH=true`, or an authorized public HTTPS
`TRAVEL_SEARXNG_URL` with `TRAVEL_SEARXNG_TERMS_CONFIRMED=true`. These switches
record the operator's account/terms decision; they do not grant provider rights.
Leave paid/keyed providers unconfigured until that decision is made. See the
dated provider review in `artifacts/audit/TRAVEL_PROVIDER_RESEARCH.md`.

`TRAVEL_MAP_TILE_URL` selects a public HTTPS browser tile template without
credential query parameters. An empty value disables tiles while retaining
saved geometry. Tiles load only after the user chooses **Load map**.

Open-Meteo hosted free use requires `TRAVEL_USE_MODE=personal_noncommercial`.
Commercial use requires `TRAVEL_OPEN_METEO_API_KEY` and a subscription, using
the documented customer endpoint. Free limits: 600/minute, 5,000/hour,
10,000/day and 300,000/month; weighted requests can cost more than one call.
ALFRED's limits are lower (60/minute, 500/hour, 2,000/day, 50,000/month shared
across geocoding/weather). Attribution: Open-Meteo / GeoNames, CC BY 4.0.
See [pricing](https://open-meteo.com/en/pricing),
[terms](https://open-meteo.com/en/terms),
[geocoding](https://open-meteo.com/en/docs/geocoding-api) and
[forecast documentation](https://open-meteo.com/en/docs).

openrouteservice Standard is free with an individual account/key. Current
published directions limits are 2,000/day and 40/minute; ALFRED caps requests
below these. Results require attribution and CC BY-SA 4.0 compliance. Key stays
server-side. The current API base is `https://api.heigit.org/openrouteservice`.
See [plans](https://account.heigit.org/info/plans),
[terms](https://account.heigit.org/info/tos),
[routing options](https://giscience.github.io/openrouteservice/api-reference/endpoints/directions/routing-options)
and [FAQ](https://giscience.github.io/openrouteservice/frequently-asked-questions).

Public Nominatim was not enabled: its generated-application policy requires an
informed operator decision; it also requires identifying requests, attribution,
caching, no autocomplete and at most one request/second for the entire app.
See [usage policy](https://operations.osmfoundation.org/policies/nominatim/).

Shared public Overpass instances are not a default ALFRED backend. The operator's
[commons policy](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)
discourages that use. Published broad guidelines (~10,000 calls and 1 GB/day)
are not a reserved quota or service guarantee. OSM data is global, unevenly
mapped, and ODbL licensed. Arrange an authorized endpoint or self-host locally.

Maps use provider-neutral GeoJSON. OSM tiles require visible attribution,
ordinary browser caching/referer, and no bulk download or offline prefetch.
See [tile policy](https://operations.osmfoundation.org/policies/tiles/).
No Google billing or keys are configured automatically.

Permit references are evidence, not access clearance. The dated Chembra
reference points to [Kerala Tourism](https://www.keralatourism.org/destination/chembra-peak-wayanad/508/).
No page contents or booking inventory are scraped. Kerala Tourism's
[copyright terms](https://www.keralatourism.org/copyright) restrict reuse;
the forest booking site's terms do not establish an open inventory API.
Verify opening, quota, fees, ID and restrictions directly with the authority.

Duffel requires `TRAVEL_DUFFEL_API_KEY` and
`TRAVEL_DUFFEL_ALLOW_PAID_SEARCH=true`; test tokens are rejected by the live
planner. The current search-to-order allowance is 1500:1, with USD 0.005 per
excess search. This is **not a free inventory feed for a planner with no
bookings**. Stays access requires an account request; worldwide inventory varies.
The documented default live search rate is 10/minute; ALFRED caps the shared
provider at 8/minute, 20/hour, 40/day and 100/month. These are application caps,
not a guarantee of free usage. No orders, payments or ticket issuance are made.
No public booking URL is fabricated from an API offer ID. See
[pricing](https://duffel.com/pricing), [agreement](https://duffel.com/services-agreement),
[Stays setup](https://duffel.com/docs/guides/getting-started-with-stays),
[hotel search](https://duffel.com/docs/api/v2/search),
[flight search](https://duffel.com/docs/api/offer-requests),
[offer expiry](https://duffel.com/docs/api/offers) and
[rate limits](https://help.duffel.com/hc/en-gb/articles/10229200096786-What-is-the-API-rate-limit).

Amadeus Self-Service was rejected for a new integration: the current
[official portal](https://developers.amadeus.com/self-service/category/hotels)
states that Self-Service was decommissioned on July 17. Old indexed tutorials
and historical free quotas are not treated as current availability.

Indian rail live inventory is unsupported without an authorized provider.
IRCTC publishes an [information enquiry integration policy](https://contents.irctc.co.in/en/TIES_Policy.pdf);
this is not an open anonymous seat API. A future adapter needs its actual
agreement, schema, limits and credentials. Do not substitute unofficial scraping.
