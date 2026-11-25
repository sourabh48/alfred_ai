# Travel API access matrix

Checked 2026-11-25. The evidence and source links are in [TRAVEL_INTELLIGENCE_RESEARCH.md](TRAVEL_INTELLIGENCE_RESEARCH.md).
"In ALFRED" refers to `master` 6a17def. Implemented is not accepted: this table promotes no requirement.

Individual access means a person without a registered company can lawfully get it. Cost is what the official page
states. Where an official page states nothing, the cell says "not stated".

## Tourism and places

| Source | Classification | Individual access | Cost | Quota or limit | In ALFRED | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| Google Places (New), text, nearby and photos | PAID_PRODUCTION_API, with monthly free usage | Yes, with a Google Cloud billing account | India: free usage per SKU each month (Essentials 70,000; Pro 35,000; Enterprise 7,000), then per-1,000 rates | App caps 10 a minute, 60 an hour, 200 a day, 3,000 a month | Yes | Keep. TRAVEL-18 owner check |
| data.gov.in OGD API | VERIFIED_FREE_PUBLIC_SERVICE | Yes (sign up, key under My Account) | Free | Not stated | No | P3: pick datasets by hand |
| data.tourism.gov.in | VERIFIED_FREE_PUBLIC_DATASET (statistics) | Yes, no login (secondary) | Free | n/a | No | Postpone; no places data |
| ASI centrally protected monuments PDF | WEBSITE_ONLY (PDF); reuse UNVERIFIED | Yes, to read | Free | n/a | No | P3: dated reference list after licence check |
| Incredible India, Karnataka Tourism, KSTDC, other state portals | WEBSITE_ONLY | Read only | Free | n/a | KSTDC link | Links only |
| Wikivoyage | VERIFIED_FREE_PUBLIC_SERVICE (CC BY-SA) | Yes | Free | API etiquette | Removed 2026-11-14 | None (owner chose Google) |

## Maps

| Source | Classification | Individual access | Cost | Limit | In ALFRED | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| Google Map Tiles | PAID_PRODUCTION_API, with free usage | Yes | India free usage 700,000 a month for Map Tiles SKUs | App cap 3,000 tiles a day | Yes (proxy) | Keep |
| Protomaps daily OSM build | VERIFIED_FREE_PUBLIC_DATASET (ODbL Produced Work) | Yes | Free; "hotlinking … discouraged" | Builds kept one week | Yes (offline country maps) | Keep; recheck attribution text |
| OSM tile.openstreetmap.org | VERIFIED_FREE_PUBLIC_SERVICE, no offline or bulk use | Yes | Free | Tile policy | No | Never use for offline |
| Geofabrik OSM extracts | VERIFIED_FREE_PUBLIC_DATASET (ODbL) | Yes | Free | n/a | No | P6 input |
| Bhuvan APIs (geocode, routing, LULC) | UNVERIFIED (service list official; token and terms not read) | Registration claimed optional for viewing; APIs need a token (secondary) | Not stated | Not stated | No | Register and read the terms before any decision |
| Survey of India online maps | WEBSITE_ONLY (store); "G2G Free, G2P Paid" | Yes, individual registration | Paid for the public (prices not checked) | n/a | No | Postpone |

## Routing (self-hosted software, not providers)

| Engine | Licence | Windows | Cost | Next action |
| --- | --- | --- | --- | --- |
| GraphHopper | Apache-2.0 (do not ship the AGPL Maps UI) | Native, Java 17 or later | Free; the PC's RAM and disk | P6, if the owner reverses "Google is the only router" |
| Valhalla | MIT | vcpkg build, incomplete | Free | Fallback candidate |
| OSRM | BSD-2-Clause | Build notes, stale Docker images | Free | Not recommended |
| Google Routes and Transit | PAID_PRODUCTION_API, with free usage | Yes | Free usage per SKU | In ALFRED; keep |

## Weather and safety

| Source | Classification | Individual access | Cost | Limit | In ALFRED | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| IMD API platform (district warnings, nowcast, city forecast, highway warnings) | RESTRICTED_PRODUCTION_API (IP whitelist through a form and email) | Unclear: the form takes "external" users and one public IP; terms not stated | Not stated | Not stated | No | P2: owner applies if they have a static IP |
| NDMA SACHET CAP RSS (India and per state) | VERIFIED_FREE_PUBLIC_SERVICE (RSS is an official channel; exact URL to confirm) | Yes, no key | Free | Not stated | No | **P1: build first** |
| CWC flood forecasts (ffs.india-water.gov.in) | WEBSITE_ONLY (API for state nodal officers) | Read only | Free | n/a | No | Link; send the CWC email |
| KSNDMC / Varuna Mitra | WEBSITE_ONLY | Read only | Free | n/a | No | Link; send the KSNDMC email |
| Google Weather | PAID_PRODUCTION_API, with free usage | Yes | Free usage per SKU | 10 days ahead | Yes | Keep |
| Open-Meteo archive | VERIFIED_FREE_PUBLIC_SERVICE, **non-commercial only**, CC BY 4.0 | Yes | Free | 600 a minute, 5,000 an hour, 10,000 a day, 300,000 a month | Yes (climate) | Fix the doc drift (P0) |
| USGS earthquakes | VERIFIED_FREE_PUBLIC_SERVICE | Yes | Free | Not checked here | Yes | Keep |
| Google Air Quality | PAID_PRODUCTION_API, with free usage | Yes | Free usage per SKU | | Yes | Keep |

## Road safety and tolls

| Source | Classification | Individual access | Cost | In ALFRED | Next action |
| --- | --- | --- | --- | --- | --- |
| MoRTH Road Accidents in India (annual PDFs) | VERIFIED_FREE_PUBLIC_DATASET (aggregate; no black-spot locations) | Yes | Free | No | P3: state-level context line only |
| data.gov.in state top-ten black spots, 2016–18 | VERIFIED_FREE_PUBLIC_DATASET | Yes | Free | No | P3, labelled dated |
| NHAI TIS (tis.nhai.gov.in) | WEBSITE_ONLY (undocumented JSON is not an API) | Read only | Free | No | Link; no scraping |
| NPCI NETC Plaza Master PDFs | VERIFIED_FREE_PUBLIC_DATASET (plaza locations, no fees; licence not stated) | Yes | Free | No | P3: plazas near the route, "fees not known" |
| NETC FASTag APIs | RESTRICTED_PRODUCTION_API (banks and acquirers) | No | n/a | No | Unavailable |
| Google Routes toll estimate | PAID_PRODUCTION_API; `IN_FASTAG` pass documented, India coverage **UNVERIFIED** | Yes (user's Google key) | Compute Routes Enterprise SKU | Yes, car routes (2026-11-26) | Estimate only; "not reported" is never shown as toll-free |
| MoRTH VAHAN / SARATHI (Data Sharing Policy 2025) | RESTRICTED_PRODUCTION_API | No | n/a | No | Not needed; unavailable |

## Bus, train and flights

| Source | Classification | Individual access | Cost | In ALFRED | Next action |
| --- | --- | --- | --- | --- | --- |
| KSRTC, Kerala RTC, TNSTC, TGSRTC | WEBSITE_ONLY | Book on the site | Ticket price | Allow-list links | Keep; TRAVEL-14 deferred |
| BMTC / BMRCL GTFS | UNVERIFIED (no official public feed found) | Unknown | n/a | Google Transit | P5: email; use Google Transit meanwhile |
| Delhi Open Transit Data | VERIFIED_FREE_PUBLIC_DATASET (static GTFS); realtime needs a key (terms unread) | Static: yes. Realtime: not stated | Free | No | Postpone (not Karnataka) |
| NTES (CRIS) | WEBSITE_ONLY | Read only | Free | Link | Keep link |
| data.gov.in railway timetable | UNVERIFIED (listing stale) | Yes | Free | No | Postpone |
| IRCTC rail e-ticketing (PSPs and agents) | RESTRICTED_PRODUCTION_API | No (business, KYC, PSP contract) | PSP-specific fees | Link | Unavailable; TRAVEL-13 stays BLOCKED_EXTERNAL |
| Skyscanner Travel API | RESTRICTED_PRODUCTION_API ("established business", over 100k monthly traffic) | Unlikely | Free if approved (secondary) | Adapter waits for a key | Re-scope TRAVEL-12 next step to Amadeus |
| Amadeus Travel Builder (beta) | VERIFIED_PRODUCTION_API (search only; no AI training; short cache) | Yes (owner holds a key) | Free beta | Yes | Keep; low-cost Indian airlines not covered |
| AeroDataBox (RapidAPI) | PAID_PRODUCTION_API (freemium, per person; tiers not checked) | Yes | Per the RapidAPI plan | Yes (booked-flight status) | Keep |
| AAI | WEBSITE_ONLY; AIKOSH flight-schedule dataset UNVERIFIED | Read only | Free | No | Postpone |

## Permits

| Source | Classification | Individual access | Cost | In ALFRED | Next action |
| --- | --- | --- | --- | --- | --- |
| Arunachal e-ILP, Nagaland, Manipur, Mizoram ILP; Lakshadweep e-permit | WEBSITE_ONLY | Apply on the site | Per portal | Dated references | Keep; review dates |
| Karnataka Aranya Vihaara (treks) | WEBSITE_ONLY | Login and booking | Varies by zone and group | Kudremukh only | P4: more treks as dated references |
| MHA PAP / RAP (foreign nationals; e-FRRO) | WEBSITE_ONLY | Foreign travellers apply | Not stated | No | P4: a note when a traveller is foreign |
| Wildlife safaris and forest stays | WEBSITE_ONLY / UNVERIFIED per park | Book on the site | Varies | No | P4: per-park reviewed links |
| DigitalSky airspace map (DGCA) | WEBSITE_ONLY; API UNVERIFIED | View the map; UIN for drones over 250 g (₹1,000 fee in one guidance excerpt) | Free to view | No | P4: drone note and link |
| API Setu | RESTRICTED (organisation PAN, GST, incorporation, domain email) | No | n/a | No | **Not chosen** (owner 2026-11-25) |
