# Travel provider policy and architecture

## Offline country maps

Settings > Offline maps keeps chosen countries' maps on this PC. Source: the free daily
[Protomaps](https://docs.protomaps.com/basemaps/downloads) OpenStreetMap build (ODbL; shown as
"© OpenStreetMap contributors, Protomaps"), read with HTTP range requests from `build.protomaps.com`.
ALFRED first reads only the build's tile index and shows the exact size; it downloads only after the
person who manages ALFRED confirms that size. Zoom 0-14 inside the country's boxes (from Natural Earth,
including areas any side claims) is stored in `ALFRED_DATA_DIR/maps/<country>.sqlite`; the map overzooms
for street level. Downloads resume after an interruption. Removing a country deletes only its file.
No account, key or personal data is involved. Google tiles cannot be stored offline under Google's terms,
so the Travel map uses these files only when Google tiles are missing or fail.

## Request telemetry retention

Post-audit development only; this policy has not been deployed. It deletes only
expired `TravelProviderRequest` telemetry. Saved plans, research evidence, cached
provider results, financial records, owners and provider lease/backoff state remain.

| Setting | Default | Allowed |
| --- | --- | --- |
| `TRAVEL_PROVIDER_REQUEST_RETENTION_DAYS` | 7 | 1–3650 days, non-network logs |
| `TRAVEL_PROVIDER_NETWORK_RETENTION_DAYS` | 90 | 1–3650 days, network attempts |
| `TRAVEL_PROVIDER_CLEANUP_BATCH_SIZE` | 1000 | 1–10000 rows per run |

The current UTC billing month and at least the previous day of network attempts
remain even with shorter retention, preserving existing minute/hour/day/month
quotas. Active in-progress attempts are deferred while their provider lease is
valid; expired abandoned attempts can age out. Old completed attempts can expire
while a provider is busy. Cleanup is deterministic and restart-safe, oldest first.
The result reports remaining/deferred counts; a partial batch does not claim that
all expired rows have gone. Both source Celery beat and native Huey run it every
15 minutes. Configuration errors fail before deletion.

In an explicitly configured disposable runtime:

```powershell
& $python manage.py cleanup_travel_requests
& $python manage.py cleanup_travel_requests --apply
```

The first command only previews safe counts. `--apply` deletes one bounded batch;
repeat as needed. Production maintenance remains separately authorized. No command
deletes or rewrites backups. Historical backups may retain expired telemetry.
Full SQLite recovery checks include that table; post-start financial comparison
excludes only this operational table.

## Selective research refresh

Post-audit development only. A specific follow-up such as **Refresh weather** or
**Show cheaper hotels** scopes the research job to that category. The scope comes
from the current message, not accumulated interests, and is not saved as a user
preference. **Recheck Trip** still explicitly refreshes the whole trip. Existing
provider quotas, backoff, shared leases, parameter validation and request limits
apply to every network attempt, including forced refreshes.

Unrelated providers use only their existing parameter/version/partition cache.
Fresh results retain their original timestamps and become RECENTLY_VERIFIED;
expired results remain CACHED with UNKNOWN confidence. A missing matching cache
entry is unavailable (`refresh_not_requested`), not a fresh network result. Changed
dates or route parameters cannot reuse an incompatible cache entry. Public web
research remains bounded to three topics; the latest requested topic has priority.

Rechecks reuse the saved destination, including explicitly selected coordinates,
without discovering new destinations first. A changed pending scope gets a new
revision, so an older job cannot overwrite the newer request. Edited itinerary
days and budget allowances survive background rechecks.

Date changes invalidate forecasts, offers, transport availability, permit/search
leads and selected price snapshots on both candidate cards and the itinerary.
Independent route/place evidence remains available with its actual expiry. The
previous research banner is marked **Recheck needed**; it cannot claim a current
forecast for the new dates. Historical evidence rows are retained. Plan/session
updates roll back together if invalidation fails. These changes do not activate a
provider, create a booking, alter canonical financial records or migrate a schema.
Current validation and release limitations are in [Project Status](PROJECT_STATUS.md).

## Verified booking links

ALFRED researches; the owner books on the external site. The planner shows the
`BOOKING_SITES` allow-list in `services/travel/links.py` for hotels, flights and
buses. Each entry is an HTTPS home page, so opening it sends nothing from the
trip. `booking_sites()` drops any entry that fails `normalized_link` or carries a
query or fragment. The list is static, so it also appears on saved and multi-stop
plans. Search links are separate: each label names the trip details in its URL
(dates, traveller and room counts, start city), and opening one is the owner's
choice. No inventory, price or availability is checked, and nothing is booked.

Reviewed 2 November 2026 with automated page reads, not a real browser:

| Site | Operator evidence |
| --- | --- |
| `www.ktdc.com` | Own page: "Official Website", book only through it. Booking runs on `booking.ktdcbooking.com` |
| `kstdc.co` | Linked from the Government of Karnataka's `karnatakatourism.org`, as a related link |
| `www.booking.com` | Wikipedia infobox only. Host answered over valid TLS with an empty 202, so its content was not read |
| `www.akasaair.com` | Own page: Akasa Air, flight booking |
| `www.airindiaexpress.com`, `www.spicejet.com` | Page title only; the body did not render for the reader |
| `www.ksrtc.in` | Linked for booking from the Government of Karnataka's `ksrtc.karnataka.gov.in` |
| `www.keralartc.com` | Own page: "Official Website of Kerala State Road Transport Corporation". Booking runs on `onlineksrtcswift.com` |
| `www.tnstc.in`, `www.tgsrtcbus.in` | Own page names the operator and offers booking; no government page confirmed it |

Left out until a person opens them in a real browser, because automated reads
timed out: `www.airindia.com`, `www.goindigo.in`, `www.makemytrip.com` and
`www.redbus.in`. Their domains match their Wikipedia infoboxes (`redbus.com` for
redBus). `www.apsrtconline.in` is left out because it redirected to plain HTTP.
`online.keralartc.com` refused the connection. Add a site only after the same
review.

**Provider status — 2026-10-15:** Code/fixture success is separate from configured and real-live-tested. No new provider credentials/calls were used in this audit. Provider pricing is in the [current register](ALFRED_EXTERNAL_INTEGRATIONS.md); contract-specific limits remain unverified. Keep old dated limits below as historical guidance. Never treat wiki/POIs/link-outs as booking or road-legality evidence.

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

Owner decision 2026-11-14: Google is the one travel data source wherever Google has the data, so one key
covers the map, place names, places, hotels, destinations, routes and weather. Flights wait for Skyscanner.
The key goes in Settings > Online services (or `TRAVEL_GOOGLE_MAPS_API_KEY` in `config/local.env`) and is
sent only in the `X-Goog-Api-Key` header. On that key enable **Map Tiles API, Places API (New), Routes API
and Weather API**; Geocoding is not needed because Places text search finds place names.

| Category | Adapter / configuration | Cache | Terms and limitations |
| --- | --- | --- | --- |
| Map | Google Map Tiles (2D roadmap) | Browser, one day | App cap 3000 tiles a day; offline country maps (Protomaps) are used only when Google tiles are missing or fail |
| Place names | `google_places`: Places text search | 30 days (Google allows keeping coordinates 30 days) | Ambiguous names ask you to choose |
| Places and hotels | `google_places_nearby`, `google_lodging`: Places nearby search | 1 day | Listings, ratings and price level only; no room rates or availability |
| Destination ideas | `google_destinations`: Places text search in a box around the start city | 1 day | Google Maps listings, not an official list; seed catalogue fallback |
| Routing | `google_routes`: Routes API | 1 hour | Two-wheeler, car or walking; up to three alternatives; distance and time only, no line on a non-Google map (Google terms); motorcycle legality and closures unverified |
| Weather | `google_weather`: Weather API daily forecast | 2 hours | Today and the next nine days only; trips further out show "not checked"; official warnings unavailable |
| Flights | `skyscanner`: Flights Live Prices v3; `TRAVEL_SKYSCANNER_API_KEY` | 15 minutes | Waiting for Skyscanner partner approval; until then each trip shows a Google Flights link |
| Permits | Dated official references | 6 hours near departure, otherwise 24 hours | No authorized live permit inventory API verified; opening remains unverified |
| Indian rail | Unavailable boundary | None | Authorized agreement/API required; timetable never implies seats, waitlist or fare |
| Bus | Reviewed state-operator links and a search link | None | No live inventory integration; availability unknown |

Every Google provider shares the app caps in code (10 a minute, 60 an hour, 200 a day, 3000 a month each),
well inside Google's monthly free usage. Removed on 2026-11-14 and no longer called: openrouteservice,
Valhalla, Open-Meteo, Overpass, Wikivoyage/Wikipedia, Brave, SearXNG, Duffel and Travelpayouts. Their old
keys in `config/local.env` are ignored and can be deleted.

### Skyscanner, once the key is approved

1. Apply at the [Skyscanner Travel API](https://www.partners.skyscanner.net/product/travel-api) partner page.
2. When approved, paste the key in Settings > Online services > Skyscanner. Nothing else changes: the
   planner starts showing live fares on the next trip check.
3. ALFRED sends only airport codes, dates, traveller count and cabin (`POST .../flights/live/search/create`,
   then up to two `poll` calls), with the key in the `x-api-key` header. It shows the ten cheapest
   itineraries in INR with the agent's own link. Prices are quotes to recheck; nothing is booked.
4. The adapter (`providers/transport.py::SkyscannerFlights`) follows Skyscanner's v3 documentation and is
   tested against fixtures; it is UNVERIFIED against a live key until the first real search.

Choose a displayed route explicitly before using it in a draft. Selection checks
the owned session revision, route identity and source timestamps. An expired or
changed result requires rechecking; a missing confirmed choice is not silently
replaced. Selection recalculates allowances through the existing Decimal budget
service and rebuilds that destination's draft days. Save explicitly afterwards.
Home-to-destination geometries cannot be selected as inter-stop legs in a
multi-stop itinerary. Distinct geometries do not establish distinct legal roads;
motorcycle legality, closures, traffic, scenic quality and corridor stops remain
unverified. Local synthetic acceptance does not establish live-provider coverage.

## Motorcycle restriction references

The Travel route panel can retain an owner's reviewed **public reference** for
one exact route and trip context. This is a local manual workflow: no provider is
activated and no page is fetched, scraped or authenticated. It accepts only
HTTPS `.gov.in`/`.nic.in` links, a road/segment, a supporting quotation and either
`PROHIBITED` or `CONDITIONAL`. The owner must explicitly attest that the quote
applies to the displayed route, motorcycle mode and dates. Permission for the
whole route is unsupported. The host policy is deliberately limited to Indian
government reference domains; matching a host is not independent authentication.

| Status | Meaning |
| --- | --- |
| VERIFIED | A consistent current reference was reviewed by this owner for this route/context. It is not independently verified law or whole-route clearance. |
| UNKNOWN | No matching reviewed evidence, withdrawal, conflicting claims, changed context or an invalid receipt. |
| STALE | The retained review expired; the quote is historical and supplies no current restriction conclusion. |
| UNAVAILABLE | Current routing/identity is absent, expired or unsupported, so the reference cannot establish a current route conclusion. |

`motorcycle_legal` always remains `UNKNOWN`. A car route, absence of a prohibition,
highway avoidance or a manually reviewed reference never establishes motorcycle
permission. No live closures, scenic quality, authority authenticity or future
travel clearance is certified. Refresh before relying on a dated display;
statuses are revalidated on every session read and submission.

The existing owned planner-session POST accepts `action=restriction_review`,
`revision`, `candidate_index`, `route_id`, `restriction`, `road`, `quote`,
`source_url`, `checked_at`, `expires_at` and `reviewed=true`. Check/expiry must
be timezone-aware, current and at most 24 hours apart; times normalize to UTC
before receipt hashing. Quotes are limited to 1,200 characters, road labels to
160, URLs to 1,000, retained rows to 20 per route/context and 100 per session.
Unknown fields, clearance claims, changed routes, active research, unreviewed or
expired references are rejected. Failed submissions retain the input draft.

`action=restriction_withdraw` takes the current `revision` and an owned
`evidence_id`. It withdraws the review while retaining its quotation/source and
records a timestamped conversation event. Corrections require a new review;
receipt mismatches are not promoted. References in `TravelResearchEvidence` stay
session/owner-scoped, including when another session has identical geometry.
Route geometry/profile/constraints and trip inputs/dates are bound into the
receipt scope. Reads and reviews never mutate canonical finance, itinerary days
or saved-plan allowances. Existing account/session cascades remain unchanged.

Maps use provider-neutral GeoJSON. Google tiles show Google's attribution; offline OpenStreetMap
files show "© OpenStreetMap contributors, Protomaps".

Permit references are evidence, not access clearance. The dated Chembra
reference points to [Kerala Tourism](https://www.keralatourism.org/destination/chembra-peak-wayanad/508/).
No page contents or booking inventory are scraped. Kerala Tourism's
[copyright terms](https://www.keralatourism.org/copyright) restrict reuse;
the forest booking site's terms do not establish an open inventory API.
Verify opening, quota, fees, ID and restrictions directly with the authority.

Google (checked 2026-11-13): map tiles read the key from the `X-Goog-Api-Key` header; 2D tiles have
100,000 free requests a month (700,000 for India-billed accounts), and ALFRED caps them at 3000 a day.
Places nearby and lodging ask only for Nearby Search Pro fields.

Amadeus Self-Service was rejected for a new integration: the current
[official portal](https://developers.amadeus.com/self-service/category/hotels)
states that Self-Service was decommissioned on July 17. Old indexed tutorials
and historical free quotas are not treated as current availability.

Indian rail live inventory is unsupported without an authorized provider.
IRCTC publishes an [information enquiry integration policy](https://contents.irctc.co.in/en/TIES_Policy.pdf);
this is not an open anonymous seat API. A future adapter needs its actual
agreement, schema, limits and credentials. Do not substitute unofficial scraping.
