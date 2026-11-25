# Travel intelligence research: government APIs, access and repository audit

Research and docs only, 2026-11-25. Nothing was implemented, no migration was changed, nothing was committed or
pushed. No provider was called with a key, and the owner's runtime at `F:\ALFRED` was not touched.

Companion files:
[access matrix](TRAVEL_API_ACCESS_MATRIX.md), [licensing](TRAVEL_DATA_LICENSING.md),
[roadmap](TRAVEL_IMPLEMENTATION_ROADMAP.md) and [acceptance criteria](TRAVEL_ACCEPTANCE_CRITERIA.md).

## How this was checked

- **Source of truth:** the code audited is `master` at `6a17def` (2026-11-25), read with `git show` and `git grep`.
  These files were first drafted in a stale worktree and then moved to `work/travel-intel-2026-11-25`, cut
  from `master` `6a17def`.
- **Graphify** was skipped (Windows Application Control blocks it), so Grep and Read were used instead.
- **Web evidence:** official pages were preferred. Each claim is marked as checked against an official page,
  official but only partly read, or secondary. Where an official page did not state a fact, it is called
  **not stated**. No endpoint, price, quota or approval rule was invented. A website is never called an API.
- **Constraints applied:** the owner decisions listed in memory (Google-only maps, places and hotels; Skyscanner then
  Amadeus for flights; no API Setu; no live booking; TRAVEL-11/12/13 BLOCKED_EXTERNAL; offline-first retired; free
  keys bundled encrypted; paid keys per person; no 3.0 code; finance, investments and family untouched).

## Phase 1: repository audit (master 6a17def)

### What Travel already has

| Area | Where | What works | Requirement |
| --- | --- | --- | --- |
| Models | `apps/mobility/models.py` (migrations up to `0015_vehicle_and_travel_currency`) | TravelPlan, planning, research and evidence sessions, provider state and request telemetry, destination history, preferences, feedback, trip logs, photos and videos, bike models | TRAVEL-01..23, BIKE-* |
| Endpoints | `apps/mobility/urls.py`, `planner_views.py`, `views.py` | Planner sessions, affordability, savings, stay details, preferences, provider usage, feedback, media, plans, logs, bikes | |
| Provider base | `services/travel/providers/base.py`, `cache.py` | Typed results, freshness labels (LIVE … UNKNOWN), leases, backoff, minute/hour/day/month budgets, safe HTTP through `public_http` | TRAVEL-21/22/23 COMPLETE_VERIFIED |
| Map | `google_tiles.py` (same-origin proxy, key in header), `offline_maps.py` (Protomaps PMTiles per country, size shown first, resumable), `mapping.py` (GeoJSON) | Online Google tiles; offline OSM country map as fallback | TRAVEL-17 verified; TRAVEL-18 IMPLEMENTED_NOT_ACCEPTED |
| Places and hotels | `providers/geocoding.py`, `places.py`, `photos.py` | Google Places text and nearby search, lodging, destination ideas, one photo on demand | TRAVEL-02/03/10 verified |
| Routing | `providers/routing.py` | `GoogleRoutes` (two-wheeler, car, walk, three alternatives, avoid tolls and highways) and `GoogleTransit` | TRAVEL-07/08 partial, TRAVEL-09 not accepted |
| Route order | `route_optimiser.py` | Stop ordering inside ride-hour limits | TRAVEL-04 |
| Restrictions | `restrictions.py` | Owner-reviewed `.gov.in`/`.nic.in` reference per route; `motorcycle_legal` always UNKNOWN | TRAVEL-08 partial |
| Weather | `providers/weather.py` | `GoogleWeather` 10-day forecast; `OpenMeteoClimate` (archive API) for same-dates climate | TRAVEL-16 verified |
| Safety | `providers/safety.py`, `proactive.py` | USGS earthquakes near the destination, Google Air Quality, pre-trip steps | none |
| Flights | `providers/transport.py`, `flight_status.py`, `short_keep.py` | `SkyscannerFlights` (waits for key), `AmadeusFlights` and `AmadeusAirports` (live-checked 2026-11-19), AeroDataBox status of a booked flight, 15-minute purge of offers | TRAVEL-12 BLOCKED_EXTERNAL |
| Trains | `IndianRailProvider` | Unavailable boundary plus IRCTC and NTES links; never implies seats or fares | TRAVEL-13 BLOCKED_EXTERNAL |
| Buses | `links.py` `BOOKING_SITES` | Reviewed KSRTC, Kerala RTC, TNSTC and TGSRTC home pages | TRAVEL-14 NOT_IMPLEMENTED |
| Permits | `providers/permits.py` | Dated official references for Chembra, Kudremukh (Aranya Vihaara), Arunachal e-ILP, Nagaland, Manipur and Mizoram ILP, Lakshadweep | TRAVEL-15 partial |
| Holidays | `providers/holidays.py` | Nager.Date public holidays and long weekends | |
| Visited regions | `world.py` | Offline countries and states from the bundled dr5hn dataset (ODbL) | |
| Exports, packing, reminders | `pdf_export.py`, `gpx_export.py`, `ics_export.py`, `packing.py`, `reminders.py` | Private exports and opt-in reminders | TRAVEL2-003/004 |
| Tests | 46 Travel and mobility test modules on master, including `test_travel_google_maps`, `test_offline_maps`, `test_travel_short_keep`, `test_travel_route_optimiser` | | |

Status rows on master (`docs/PROJECT_STATUS.md`): COMPLETE_VERIFIED TRAVEL-01, 02, 03, 05, 06, 10, 16, 17, 19, 21, 22
and 23; IMPLEMENTED_NOT_ACCEPTED TRAVEL-04, 09, 18 and 20; PARTIALLY_IMPLEMENTED TRAVEL-07, 08 and 15; BLOCKED_EXTERNAL
TRAVEL-11, 12 and 13; NOT_IMPLEMENTED TRAVEL-14. BIKE-01, 02, 04 and 06 COMPLETE_VERIFIED; BIKE-03 and 05 partial.
Relevant RUNTIME rows: RUNTIME-06 (offline startup) and RUNTIME-10 (HTTP safeguards) are verified. Baseline 85/143,
extensions 0/13. This research changes none of these.

### What is missing

1. **Official Indian weather warnings.** TRAVEL_PROVIDERS says "official warnings unavailable". No IMD, NDMA SACHET or
   CWC source is integrated (`git grep` finds no `imd.gov`, `sachet` or `ndma` in `apps/` or `alfred_ai/`).
2. **Offline routing.** Google Routes is the only router, and Google's terms forbid drawing its line on the offline
   map. With no network there is no route.
3. **Motorcycle legality.** This is still UNKNOWN by design. No authoritative machine-readable source exists (see
   Phase 2).
4. **Tolls.** There is an avoid-tolls switch but no toll cost or plaza list.
5. **Bus and train inventory.** Out of reach: deferred, blocked or restricted.
6. **Permits beyond seven places.** Ladakh, Sikkim, Rohtang, wildlife safaris and drone zones are not covered.
7. **Tourism data.** Destination ideas come from Google listings only. Official monument and tourism lists are unused.

### Duplicates and drift found (docs only, not fixed)

- `docs/TRAVEL_PROVIDERS.md` says Open-Meteo was "removed on 2026-11-14 and no longer called", but `research.py`
  calls `OpenMeteoClimate` (archive API). It is a real, separate use. The doc should say so, and it should note that
  Open-Meteo's free tier is non-commercial only.
- `docs/ALFRED_EXTERNAL_INTEGRATIONS.md` still lists Google Maps as "link-outs, not authenticated Maps APIs" and
  Open-Meteo as the weather and geocoding provider. Both rows are stale.
- **TRAVEL-12 depends on Skyscanner approval.** Skyscanner's own acceptance criteria require "an established business
  with a large audience (over 100k monthly traffic)". A personal desktop app is unlikely to qualify, so Amadeus
  Travel Builder is in practice the flight source, and the TRAVEL-12 next step should say so.
- `world.json` (dr5hn) and `country_boxes.json` (Natural Earth) look like two country datasets, but they serve
  different jobs: names and states versus tile bounding boxes. This is not a real duplicate.
- **No recreation needed:** Google maps, places, routes and weather, offline country maps, Amadeus flights,
  permits references, holidays, the earthquake and air-quality safety notes and the booking-site allow-list already
  work. The roadmap below extends them and does not rebuild them.

## Phase 2–3: research findings (checked 2026-11-25)

Classification key: VERIFIED_PRODUCTION_API, VERIFIED_FREE_PUBLIC_DATASET, VERIFIED_FREE_PUBLIC_SERVICE,
RESTRICTED_PRODUCTION_API, PAID_PRODUCTION_API, SANDBOX_ONLY, WEBSITE_ONLY, UNVERIFIED. The full table is in the
[access matrix](TRAVEL_API_ACCESS_MATRIX.md).

### Tourism

- **data.tourism.gov.in** (Ministry of Tourism, Research & Analytics). Statistics only: foreign arrivals, domestic
  visits and earnings. It has no places or opening hours. Search results describe it as free and open, with no
  registration needed; the pages themselves were not opened. → VERIFIED_FREE_PUBLIC_DATASET (statistics), and of low
  value for trip planning.
- **data.gov.in (OGD platform).** A free API key comes from "My Account" after registering; an individual can
  register. Data is under the Government Open Data License – India (gazetted 13 Feb 2017). Secondary summaries say
  it allows commercial and non-commercial use with attribution. The official licence page returned 403 to automated
  reads, so the exact exemptions must be read by a person. → VERIFIED_FREE_PUBLIC_SERVICE. Dataset quality varies:
  the railway timetable listing showed "No Result Found", and flight schedule resources said the API "does not exist".
- **ASI.** It publishes "Centrally Protected Monuments/Sites: State-wise and Circle-wise" as a PDF (asi.nic.in). A
  Rajya Sabha answer counts 506 centrally protected sites in Karnataka, across the Bangalore, Hampi and Dharwad
  circles. No API and no reuse licence is stated. → WEBSITE_ONLY (PDF list), with reuse terms UNVERIFIED.
- **Incredible India, Karnataka Tourism (karnatakatourism.org), KSTDC, other state portals.** These are websites with
  no documented API. → WEBSITE_ONLY. ALFRED already links KSTDC from its allow-list.

### Maps

- **Bhuvan (ISRO NRSC).** The official API page (bhuvan-app1.nrsc.gov.in/api) lists proximity, village geocoding and
  reverse geocoding, LULC statistics, shortest-path routing and geoid conversion. Registration and token rules come
  only from non-official sources (one says a token lasts 24 hours). → UNVERIFIED for production use. It needs a
  person to register and read the terms.
- **Survey of India.** The online maps portal (onlinemaps.surveyofindia.gov.in) requires registration and agreement
  to the Geospatial Data Guidelines (2021) and the National Geospatial Policy 2022. Its catalogue marks products
  "G2G Free, G2P Paid". It is a download store, not an API. → WEBSITE_ONLY (paid and free downloads).
- **OpenStreetMap.** Data is under ODbL: attribute "© OpenStreetMap contributors" and link openstreetmap.org/copyright.
  An adapted database that is used publicly must be offered under ODbL. The OSMF tile policy bans offline and
  "download country" use of tile.openstreetmap.org. ALFRED complies: it uses Protomaps builds, which are an "ODbL
  Produced Work", and never the OSMF tile server for bulk downloads. → VERIFIED_FREE_PUBLIC_DATASET (Geofabrik extracts
  and Protomaps builds).

### Local routing on Windows

| Engine | Licence | Windows | Motorcycle | Fit |
| --- | --- | --- | --- | --- |
| OSRM | BSD-2-Clause (Debian packaging, CRAN copy) | Upstream has a Windows CI badge and wiki build notes. Docker images are Debian-based and reported to be over two years old | Profiles are Lua; no stock motorcycle profile | Fast but rigid; a heavy build on Windows |
| Valhalla | MIT | The library and tools build through vcpkg, but "support for Windows is not yet fully exploited" | Has a `motorcycle` costing | Good features; a fragile Windows build |
| GraphHopper | Apache-2.0 (core and server); the Maps UI uses an AGPL dependency, so do not ship that UI | Pure Java: `java -jar graphhopper-web-*.jar server config.yml` with JDK 17 or later runs natively | Stock `motorcycle` vehicle, a `curvature` preference, custom models | **Best Windows fit** |

All three read OSM extracts (for example the Geofabrik southern-zone or India extract). Their routes are ODbL Produced
Works and need OSM attribution. None of them makes a road legal for motorcycles: OSM tags such as
`motorroad=yes` and `motorcycle=no` are crowd-sourced hints, not law. The owner decided on 2026-11-14 that Google is the
only router, so a local router needs a new owner decision (roadmap P6).

### Transport

- **MoRTH Data Sharing Policy (Aug 2025) for VAHAN and SARATHI.** It allows select verification fields for
  authorised entities, through API keys and IP whitelisting under DPDP rules. It does not cover individuals, and it
  concerns personal records that ALFRED does not need. → RESTRICTED_PRODUCTION_API. Parivahan services for
  citizens are websites (WEBSITE_ONLY).
- **API Setu.** Consumer registration needs an organisation PAN, a GST certificate, a certificate of incorporation
  and a domain-registered email; access is granted "only after the publisher's approval". → RESTRICTED. **Not chosen**
  (owner decision 2026-11-25, no GST). Documents arrive by DigiLocker download and upload instead.
- **NHAI and tolls.** The Toll Information System (tis.nhai.gov.in) is a website; the JSON behind its map is
  undocumented, so it is not an API and must not be scraped. NPCI publishes monthly "Plaza Master" PDFs with plaza
  code, name, state, district, operator and coordinates, but no fees. NETC FASTag APIs serve issuer and acquirer
  banks only. No public fee API was found. → NHAI: WEBSITE_ONLY; NPCI plaza list: VERIFIED_FREE_PUBLIC_DATASET
  (locations, licence not stated); FASTag: RESTRICTED. The Google Routes API can return estimated tolls as an extra
  computation, but whether it covers India was **not verified**.
- **KSRTC and other state RTCs.** These are booking websites with no public API (verified on 2026-11-02 for the
  allow-list). → WEBSITE_ONLY. TRAVEL-14 stays deferred.
- **Bengaluru BMTC and BMRCL.** The June 2024 announcement of an open GTFS portal led to app integrations (Namma Yatri,
  Tummoc), but no official public download page was found. Community feeds (Vonter, built from the app and timetable
  images) are unofficial. → UNVERIFIED. Delhi's Open Transit Data (otd.delhi.gov.in) is the working model: static
  GTFS, plus realtime "for authorised users" with a private key. Its terms PDF was not read. `GoogleTransit` already
  covers Bengaluru transit trips where Google has the data.
- **Indian Railways, CRIS and NTES.** NTES is a CRIS website and app with no public developer API. The data.gov.in
  timetable listing is stale. → NTES: WEBSITE_ONLY; timetable dataset: UNVERIFIED.
- **IRCTC.** Rail e-ticketing goes through Principal Service Providers and registered agents. Agent fees are set by
  each PSP (one advertises ₹3,999 a year, a third-party figure). Tourism-package API integration is free for PSPs.
  Every route needs a business identity and KYC. → RESTRICTED_PRODUCTION_API. TRAVEL-13 stays BLOCKED_EXTERNAL, and
  trains stay as links.
- **AAI and flight data.** No official AAI schedule API was found. AIKOSH lists a flight-schedule dataset under the
  Open Government License (download only, not opened). Live flight data is commercial: AeroDataBox on RapidAPI is
  already used, with each person's own key, and Aviation Edge and Cirium are alternatives. Skyscanner is
  RESTRICTED (business, over 100k monthly traffic). Amadeus Travel Builder is a free personal beta that is
  search-only, forbids AI training and limits caching. Its live check passed on 2026-11-19, per `TRAVEL_PROVIDERS.md`.
  → Amadeus: VERIFIED_PRODUCTION_API (beta); Skyscanner: RESTRICTED.

### Weather and safety

- **IMD API platform (api.imd.gov.in).** The official reference lists `cityforecast`, `cityforecastloc`,
  `current_wx`, `districtnowcast`, `stationnowcast`, `districtwarning`, `subdivisionwarning`,
  `state_district_rainfall_forecast`, `districtrainfall`, `aws_data`, cyclone, port and coastal bulletins, `sunmoon`,
  and "NHAI Highway Nowcast Warning / Highway Warning – 5 Days". Access is by IP whitelisting: the
  city.imd.gov.in request form asks for one public IP, internal or external status and purpose, then says "Kindly
  contact through mail". The platform now shows Register and Login, but those pages returned 404. **Quotas, fees,
  terms and the contact email are not stated.** IMD has restricted AWS data to designated users and bars commercial
  use of it. → RESTRICTED_PRODUCTION_API. Risk: a home connection usually has a changing public IP, so an IP
  whitelist suits a server and fits a desktop app poorly.
- **NDMA SACHET (CAP).** A PIB release lists RSS among SACHET's official channels. Feeds are national and per state
  (for example Karnataka), and each item links to a CAP 1.2 XML alert. The national feed URL
  `https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml` comes from an aggregator and still needs a check
  by a person. Reuse terms are not stated. → VERIFIED_FREE_PUBLIC_SERVICE (with the URL and terms still to confirm).
  It needs no key, so it is **the best free source of official warnings**.
- **CWC.** ffs.india-water.gov.in gives flood monitoring and short-range forecasts. A 2026 CWC presentation mentions
  an API mechanism for state nodal officers only. → WEBSITE_ONLY for individuals.
- **KSNDMC (Karnataka).** The website, the Varuna Mitra helpdesk and the Megha Sandesha app give 24–72 hour forecasts.
  No API was found. → WEBSITE_ONLY.
- **Already in ALFRED:** Google Weather (10 days), Open-Meteo archive climate (non-commercial, CC BY 4.0), USGS
  earthquakes and Google Air Quality.

### Road safety

- **MoRTH "Road Accidents in India".** Annual PDFs from 2008 to 2023, with state counts of black spots (5,803 for
  2016–18 and 9,733 across three series). Black-spot locations are not published. A data.gov.in resource gives the
  state top-ten black spots for 2016–18. → VERIFIED_FREE_PUBLIC_DATASET (aggregate only; no locations).
- The IMD NHAI highway warnings are listed under IMD above and are restricted.

### Permits

- **Inner Line Permits:** Arunachal e-ILP, Nagaland, Manipur and Mizoram portals, plus the Lakshadweep e-permit. All
  are WEBSITE_ONLY and already referenced in `permits.py` (reviewed 2026-11-25).
- **PAP and RAP (MHA Foreigners Division).** Foreign nationals need them; inside India they apply through e-FRRO. →
  WEBSITE_ONLY. This matters only when a traveller on the plan is a foreign national.
- **Karnataka treks (Aranya Vihaara).** The official portal, aranyavihaara.karnataka.gov.in (launched October 2024),
  takes bookings with a login and fees that vary by zone and group. Certified guides are mandatory, and slot booking
  has been suspended during fire seasons. → WEBSITE_ONLY. Treks other than Kudremukh can be added as dated references.
- **Wildlife and forest safaris.** No official API was found. → WEBSITE_ONLY / UNVERIFIED per park.
- **Drones (DigitalSky, DGCA).** The airspace map shows green, yellow and red zones (Drone Rules 2021). A UIN is
  needed for drones heavier than 250 g; one guidance excerpt gives the fee as ₹1,000; individuals are eligible ("Except
  foreign entity all others are eligible"). No public API is documented. → WEBSITE_ONLY (map); API UNVERIFIED.

## Individual-developer access (no registered company)

| Can do now, free | Needs a person to apply | Needs a business | Paid |
| --- | --- | --- | --- |
| data.gov.in key; NDMA SACHET RSS; NPCI plaza PDFs; MoRTH reports; ASI list; Geofabrik and Protomaps OSM data; GraphHopper, OSRM and Valhalla software; Open-Meteo (non-commercial); USGS; Nager.Date | IMD whitelisting (email plus a static IP); Bhuvan token (registration); Survey of India portal account; Delhi OTD realtime key; DigitalSky UIN (only if flying a drone); Amadeus Travel Builder (done) | Skyscanner Travel API; IRCTC/PSP API; VAHAN/SARATHI; API Setu; NETC FASTag; CWC API (state nodal officers) | Google Maps Platform beyond the India free usage (70,000 Essentials, 35,000 Pro and 7,000 Enterprise requests a month per SKU); AeroDataBox beyond its free tier; Survey of India G2P products |

### Application checklist (for the owner, when approved)

1. **data.gov.in:** sign up with your email, open My Account, copy the API key and put it in Settings (free keys ship
   encrypted; this one is personal). Keep the GODL-India attribution string with any dataset used.
2. **IMD:** confirm whether your connection has a fixed public IP (ask your ISP; a static IP is often a paid add-on).
   Without one, stop here. With one, send the IMD request form, then the email below.
3. **Bhuvan:** register at bhuvan.nrsc.gov.in, read the API terms page, and record the token lifetime and any
   usage cap before any code is written.
4. **Delhi OTD (only for a Delhi trip):** read the terms PDF and request a realtime key.
5. **BMTC and BMRCL:** send the request below, and use Google Transit until an official feed exists.
6. **CWC and KSNDMC:** send the request below (expect "no" for individuals), and link the websites meanwhile.

### Draft emails (send only after approval; fill the brackets yourself)

**IMD API whitelisting.** To: the address IMD gives after the form (not stated publicly). Subject: Request for IMD API
access for a personal travel safety application.

> Dear Sir/Madam, I am an individual developer building a personal, non-commercial desktop application that warns a
> traveller of IMD district warnings and nowcasts for the places on their own trip. I request access to
> `districtwarning`, `districtnowcast` and `cityforecastloc` from public IP [static IP]. Expected use: at most
> [N] requests a day, cached for [hours], attributed to IMD and never resold or redistributed. Please let me know the
> usage terms, any rate limit and whether an individual can be whitelisted. Regards, [name], [city].

**CWC flood forecast data.** To: the CWC Flood Forecast Monitoring Directorate (address from cwc.gov.in). Subject:
Access to flood forecast data for personal travel safety.

> Dear Sir/Madam, I build a personal, non-commercial travel planner. Is the API mentioned for state nodal officers
> available to individuals? If not, may I show a link to ffs.india-water.gov.in station pages beside a trip near a
> forecast station? Regards, [name].

**BMTC / BMRCL GTFS.** To: the BMTC and BMRCL public information officers. Subject: Public GTFS feed for Bengaluru bus
and metro.

> Dear Sir/Madam, the June 2024 announcement said BMTC and BMRCL would publish GTFS data on a public portal. Could you
> share the official download location and licence? I would use it offline in a personal, non-commercial trip
> planner, with attribution. Regards, [name].

**KSNDMC.** To: KSNDMC (ksndmc.org contact page). Subject: Programmatic access to rainfall forecasts.

> Dear Sir/Madam, is there a documented feed or API for the 24–72 hour rainfall forecasts or alerts? I build a personal,
> non-commercial travel planner and would attribute KSNDMC. Regards, [name].

No draft is given for Skyscanner, IRCTC, VAHAN, API Setu or FASTag: each requires a business, which the owner has
said they do not have.

## Sources (opened or returned by search on 2026-11-25)

- IMD API reference: https://api.imd.gov.in/public/api_reference.html · platform: https://api.imd.gov.in/ ·
  whitelisting form: https://city.imd.gov.in/citywx/api_request.php · AWS restriction report:
  https://www.downtoearth.org.in/amp/story/climate-change/imd-locking-up-its-awsarg-data-portal-hampers-public-weather-alerts-experts
- NDMA SACHET: https://sachet.ndma.gov.in · PIB channels: https://pib.gov.in/PressReleasePage.aspx?PRID=1855808 ·
  CAP note: https://thejeshgn.com/?p=34865
- CWC: https://nidm.gov.in/pdf/acrc26/Preparatory%20Session/2.%20CWC.pdf · KSNDMC: https://ksndmc.org/en/Activities/Weather
- data.gov.in licence: https://data.gov.in/government-open-data-license-india (403 to automated read) · summary:
  https://www.wikipedia.org/wiki/Template:GODL-India-text
- data.tourism.gov.in: https://data.tourism.gov.in/ · ASI list: https://asi.nic.in/pdf/CPM_List.pdf
- Bhuvan API: https://bhuvan-app1.nrsc.gov.in/api · Survey of India portal: https://onlinemaps.surveyofindia.gov.in
- OSM tiles: https://operations.osmfoundation.org/policies/tiles/ · ODbL summary:
  https://opendatacommons.org/licenses/odbl/summary/ · attribution:
  https://osmfoundation.org/wiki/Licence/Attribution_Guidelines · Protomaps: https://docs.protomaps.com/basemaps/downloads
- GraphHopper: https://github.com/graphhopper/graphhopper · Valhalla: https://github.com/valhalla/valhalla · OSRM:
  https://github.com/Project-OSRM/osrm-backend
- Google India pricing: https://developers.google.com/maps/billing-and-pricing/pricing-categories ·
  https://developers.google.com/maps/billing-and-pricing/india
- MoRTH data sharing policy: https://morth.nic.in/sites/default/files/circulars_document/Data-Sharing-policy-20082025-merged.pdf
- API Setu: https://docs.apisetu.gov.in/document-central/explore-apisetu/Overview.html · SOP:
  https://cdn.apisetu.gov.in/portal/assets/sop-apisetu-v0.pdf
- NPCI plaza master: https://www.npci.org.in/PDF/netc/Plaza-Master-May-2025.pdf · NETC FAQ:
  https://npci.org.in/what-we-do/netc-fastag/faqs
- IRCTC PSPs: https://irctctourism.com/TravelAgents/InternetTicketingAgents.html · rail timetable listing:
  https://www.data.gov.in/catalog/indian-railways-train-time-table
- Skyscanner criteria: https://skyscannerpartnersupport.zendesk.com/hc/en-us/articles/10881149122717-What-is-the-acceptance-criteria-for-the-Travel-API
- AIKOSH flight schedule: https://aikosh.indiaai.gov.in/home/datasets/details/flight_schedule.html
- Delhi OTD: https://otd.delhi.gov.in/documentation · BMTC/BMRCL announcement:
  https://deccanherald.com/india/karnataka/bengaluru/in-historic-first-namma-metro-bmtc-open-up-their-data-to-help-public-transport-users-in-bengaluru-3160955
- MHA PAP/RAP: https://www.mha.gov.in/en/divisionofmha/foreigners-division/protected-area-permit-pap-restricted-area-permit-rap
- Aranya Vihaara: https://aranyavihaara.karnataka.gov.in/ · news:
  https://newskarnataka.com/karnataka/aranya-vihaara-new-online-portal-for-regulated-trekking-in-karnataka/05102024/
- DigitalSky map: https://www.inkl.com/news/govt-releases-drone-map-for-users · UTM framework:
  https://www.civilaviation.gov.in/sites/default/files/migration/National-UTM-Policy-Framework-2021_24_Oct_2021.pdf
- MoRTH accident reports: https://morth.nic.in/sites/default/files/Road-Accident-in-India-2023-Publications.pdf ·
  black spots: https://data.gov.in/resource/states-wise-list-top-ten-black-spots-2016-2018
- Open-Meteo terms: https://open-meteo.com/en/terms
