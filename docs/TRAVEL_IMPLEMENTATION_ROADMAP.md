# Travel implementation roadmap (P0–P7)

**Proposal only, awaiting owner approval (2026-11-25).** Nothing here is built. Each task extends existing code on
`master` 6a17def; none recreates working providers. Status rules apply: implemented is not accepted, and the 143
original requirements and 13 extensions are tracked separately. Acceptance tests for each task are in
[TRAVEL_ACCEPTANCE_CRITERIA.md](TRAVEL_ACCEPTANCE_CRITERIA.md).

Order: P0 → P1 → P3 → P4 are free and need no outside approval. P2 waits for IMD. P5 waits for BMTC and BMRCL. P6
needs an owner decision. P7 holds items that cannot be delivered.

---

## P0 — Fix the docs and tracker drift (no code)

- **Scope:** correct `TRAVEL_PROVIDERS.md` (Open-Meteo archive is still called; non-commercial note);
  `ALFRED_EXTERNAL_INTEGRATIONS.md` Google Maps and Open-Meteo rows; TRAVEL-12 next step (Skyscanner requires an
  established business with over 100k monthly traffic, so Amadeus is the practical source); link the new research
  docs from `TRAVEL_PLANNER.md`.
- **Dependencies:** none. **Files:** the docs above, plus `docs/PROJECT_STATUS.md` TRAVEL-12 "Next" line only.
- **Database changes:** none. **Access:** none.
- **Risks:** editing PROJECT_STATUS by hand can break the tracker check.
- **Tests:** `scripts/project_execution.py --check` passes; counts stay at 85/143 and 0/13.
- **Acceptance:** A0 in the acceptance criteria.

## P1 — Official disaster and weather warnings from NDMA SACHET (TRAVEL-16 gap, TRAVEL-15 partly)

- **Scope:** new provider `providers/sachet.py` (class `SachetAlerts`) that reads the national CAP RSS (or the
  Karnataka feed) and the linked CAP 1.2 XML for active alerts. It keeps alerts whose area polygon or circle contains
  or touches the trip's destination and stops. It shows severity, event, issuing agency, effective and expiry time,
  and a link. The provider is added to `proactive.safety_steps` and to the research weather section. Alerts past
  `expires` are dropped.
- **Dependencies:** person-confirmed feed URL and terms (see the licensing doc). The existing `Provider`, cache,
  budget and `public_http` code.
- **Files:** `apps/mobility/services/travel/providers/sachet.py` (new), `proactive.py`, `research.py`,
  `planner_views.py` (provider list), `static/js/travel_planner.js` (one warnings block), `docs/TRAVEL_PROVIDERS.md`,
  and `tests/test_travel_sachet.py` (new, fixture XML).
- **Database changes:** none. Results go through the existing `VerifiedExternalInsight` cache and
  `TravelResearchEvidence`.
- **Access:** none (no key).
- **Risks:** XML parsing of an untrusted feed (use `defusedxml` if installed, otherwise standard-library parsing with
  entity expansion off and the existing `max_bytes`); CAP areas given as names only (then match by state or district
  name, and say so); feed outages (show "warnings not checked", never "no warnings").
- **Tests:** fixture with an active Karnataka alert, an expired one, one outside the area and a malformed one; a
  billion-laughs XML is refused; budget and backoff reuse; owner isolation of the evidence; browser check of the
  block with axe light and dark.
- **Acceptance:** A1.

## P2 — IMD district warnings, nowcast and highway warnings (after IMD grants access)

- **Scope:** provider `providers/imd.py` for `districtwarning`, `districtnowcast` and `cityforecastloc`, and the NHAI
  highway warnings if granted. It is used only when the owner's IMD grant is configured, and it complements Google
  Weather without replacing it.
- **Dependencies:** IMD whitelisting granted (the email in the research doc) and a **static public IP** on the PC.
  Without both, P2 stays BLOCKED_EXTERNAL.
- **Files:** `providers/imd.py` (new), `research.py`, `proactive.py`, Settings > Online services (one on/off; no key
  if IMD uses only the IP), `docs/TRAVEL_PROVIDERS.md`, and `tests/test_travel_imd.py` (fixtures from the public
  reference samples).
- **Database changes:** none.
- **Access:** IMD approval, which is per IP. The IMD terms are unknown until the grant arrives.
- **Risks:** a dynamic IP breaks access silently (show "IMD not reachable from this connection"); unknown quotas (use
  a low budget, such as 60 a day); terms may forbid redistribution or caching.
- **Tests:** fixture parsing; a 403 response maps to `ip_not_whitelisted`; budget; no request is sent when the grant
  is off.
- **Acceptance:** A2.

## P3 — Official reference datasets: toll plazas, road safety and monuments

- **Scope:** three dated, local reference files loaded like `world.py`, with no network at run time.
  1. NPCI Plaza Master plazas within about 2 km of the Google route line, shown as "Toll plazas on this route: N (fees
     not known)". Optional: Google Routes toll estimate, **only after Google's docs confirm India coverage**.
  2. MoRTH state road-accident and black-spot context: one line per state crossed, with year and source.
  3. ASI centrally protected monuments in Karnataka as a "protected monument" badge on Google place results that
     match by name and distance.
- **Dependencies:** a person confirms each file's licence (none is stated; see the licensing doc). The owner approves
  data sources under the "rules may be updated" decision.
- **Files:** `apps/mobility/services/travel/reference_data.py` (new), `static/vendor/travel_reference/*.json` (new,
  each with `source`, `checked_on` and licence note), `research.py`, `travel_planner.js`, and
  `tests/test_travel_reference_data.py`.
- **Database changes:** none.
- **Access:** none. A data.gov.in key is needed only if a dataset is pulled through its API rather than downloaded
  once.
- **Risks:** stale data (show `checked_on`; warn after 180 days); PDF tables converted by hand need a checked script
  kept outside the app; name-matching false positives for monuments (require name plus distance under 1 km).
- **Tests:** plaza-near-route geometry; no fee is ever shown; stale-date warning; monument badge positive and negative
  cases.
- **Acceptance:** A3.

## P4 — More permits and drone, foreigner and safari notes (TRAVEL-15)

- **Scope:** extend the `permits.py` reference list (same shape, a person reads each official page):
  - Aranya Vihaara treks beyond Kudremukh.
  - Sikkim and Ladakh, if their official portals are reachable by a person.
  - A PAP/RAP note when a saved traveller is marked as a foreign national.
  - A DigitalSky note and link when "drone" appears in the trip text.
  - Reviewed links for wildlife-safari booking pages.
- **Dependencies:** a person reviews each official page and records `reviewed` dates. This needs no new provider.
- **Files:** `providers/permits.py`, the `travel/understanding.py` keyword for drone, `tests/test_travel_providers.py`
  (permit cases), and `docs/TRAVEL_PROVIDERS.md`.
- **Database changes:** none, unless "traveller nationality" is new. Check the existing traveller fields first; if a
  column is needed, the migration needs owner approval.
- **Access:** none.
- **Risks:** fire-season closures (show "booking may be closed; check the portal"); permits are never shown as granted.
- **Tests:** every entry has an HTTPS official host, a reviewed date and a stale label after its window; the
  foreign-national note appears only when flagged.
- **Acceptance:** A4.

## P5 — Bengaluru bus and metro (BMTC, BMRCL)

- **Scope:** check `GoogleTransit` results for BMTC and Namma Metro on five synthetic city trips. If BMTC or BMRCL
  publish an official GTFS feed with a licence, import it offline (stops and routes, then a timetable) as a fallback.
- **Dependencies:** an official feed (the email in the research doc). Community feeds are not used.
- **Files:** only if a feed exists: `services/travel/gtfs.py` (new) and `tests/test_travel_gtfs.py`.
- **Database changes:** possibly a GTFS table set, which would need an owner-approved migration. A packed JSON file
  may be enough.
- **Access:** none, or the operator's terms.
- **Risks:** the feed never appears (Google Transit stays); timetable accuracy.
- **Tests:** GTFS fixture parsing; stop search; "timetable, not live".
- **Acceptance:** A5. Status: BLOCKED_EXTERNAL until a feed exists.

## P6 — Offline routing with self-hosted GraphHopper (owner decision needed)

- **Scope:** a local GraphHopper server (Apache-2.0, Java 17 or later) on a Geofabrik southern-zone or India extract,
  with a motorcycle profile and an optional curvature preference. It is used when Google Routes fails or when offline,
  and draws on the offline map with OSM attribution. It never claims motorcycle legality.
- **Dependencies:** the **owner reverses or narrows the 2026-11-14 "Google is the only router" decision**; a JDK in
  the package (size and licence check, such as Eclipse Temurin GPLv2+CE); disk (an India graph is several GB, not
  measured here) and RAM; the launcher starting and stopping the server; and the existing Valhalla-style
  `TRAVEL_*_URL` pattern (removed 2026-11-14, recoverable from git).
- **Files:** `providers/routing.py` (`LocalGraphHopper`), `routing_chain`, the native launcher and worker scripts,
  Settings > Offline maps (download the routing data per region, size shown first, as offline maps do),
  `tests/test_travel_local_routing.py`, and `docs/TRAVEL_PROVIDERS.md`.
- **Database changes:** none.
- **Access:** none (OSM data, ODbL).
- **Risks:** installer size and RAM on a modest PC; graph build time (minutes to hours); the Smart App Control and
  unsigned-installer limits (no paid signing, so a bundled Java may be blocked: test first); stale OSM data.
- **Tests:** fixture HTTP responses; fallback order Google → local → "no route"; attribution present; local route
  never drawn on Google tiles and Google route never drawn on the offline map.
- **Acceptance:** A6.

## P7 — Not deliverable now (hold; no code)

| Item | Why | Re-open when |
| --- | --- | --- |
| TRAVEL-13 train seats, fares and waitlist (IRCTC, CRIS) | PSP or agent contract, business KYC | The owner has a business and signs with a PSP |
| TRAVEL-14 bus live inventory | No public RTC API; aggregators are commercial | An operator publishes an API |
| TRAVEL-11 hotel live rates | Google Places has no rates; Amadeus Travel Builder has no hotels | An approved free hotel API exists |
| Skyscanner live fares | Business with over 100k monthly traffic | Unlikely; Amadeus covers search |
| FASTag balance or toll charges | NETC is for banks and acquirers only | Never for individuals |
| VAHAN / SARATHI lookups | Authorised entities only; personal data | Not needed |
| API Setu documents | Needs GST and an organisation (owner said no on 2026-11-25) | The owner registers a business |
| CWC flood API | State nodal officers only | CWC answers the email with "yes" |
| Live permit availability or closures | No official API exists | A state publishes one |

- **Database changes:** none. **Tests:** existing tests already show that these stay "unavailable" with links.
