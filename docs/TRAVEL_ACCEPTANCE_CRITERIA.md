# Travel intelligence acceptance criteria

Criteria for the [roadmap](TRAVEL_IMPLEMENTATION_ROADMAP.md) tasks. Passing them makes a task **locally accepted**,
not owner accepted and not a promoted requirement. Every test uses synthetic fixtures; no test touches the owner's
runtime at `F:\ALFRED` or a live key.

## Rules for every task

1. **Provenance:** each shown fact names its source, links an official HTTPS page, and carries retrieved-at and
   expires-at times. The freshness label is one of the existing set (LIVE … UNKNOWN).
2. **Abstention:** if a source is off, failing, stale, over budget or not approved, the UI says "not checked" or
   "unknown". It never says "no warnings", "no permit needed", "no tolls" or "road is legal".
3. **No silent actions:** nothing is booked, paid, applied for or sent. Links open only after the owner clicks them.
4. **Privacy:** only place, coordinates, dates and public route parameters leave the PC. Never names, chats,
   documents, vehicle numbers or bookings.
5. **Budgets:** every network call goes through the existing provider lease, backoff and minute/hour/day/month caps.
   A forced refresh is still budgeted.
6. **Licence:** attribution is shown as listed in [TRAVEL_DATA_LICENSING.md](TRAVEL_DATA_LICENSING.md). Data with an
   unknown licence is not bundled in the installer.
7. **Security:** untrusted XML and JSON are size-bounded and parsed without entity expansion. Links pass
   `normalized_link`. Every new view is owner-scoped and CSRF-protected.
8. **Quality gates:** zero skipped tests in the touched modules. Browser checks pass axe in light and dark at desktop
   width with keyboard focus. `scripts/project_execution.py --check` passes. The CI duration file is updated for any
   new browser test.
9. **Money:** any cost (tolls, fees) is a Decimal string in the stated currency and never converted for calculations
   (the owner's currency contract). Travel never writes finance records.

## Per task

| ID | Task | Pass when |
| --- | --- | --- |
| A0 | Docs drift | The three stale rows are corrected; the TRAVEL-12 next step names Amadeus as the practical source; tracker check passes; counts unchanged |
| A1 | SACHET alerts | (a) A fixture with an active Karnataka alert covering the destination shows severity, event, agency, times and link. (b) Expired, out-of-area and malformed alerts are not shown. (c) A feed timeout shows "official warnings not checked". (d) Entity-expansion XML is refused. (e) Evidence is owner-scoped. (f) Browser block passes axe in light and dark. (g) A person confirms the live feed URL and records the check date |
| A2 | IMD | (a) Off by default; with the grant off, no request is sent. (b) Fixture district warning and nowcast parse correctly. (c) A 403 shows "IMD not reachable from this connection". (d) Budget caps hold. (e) The owner runs one live check from the whitelisted IP and compares it with mausam.imd.gov.in |
| A3 | Reference data | (a) Plazas within the corridor are counted from the fixture route, and the UI says "fees not known". (b) A toll amount appears only from a provider that returned one, labelled an estimate. (c) Each file shows `checked_on`; after 180 days it is labelled stale. (d) The monument badge requires name plus distance under 1 km. (e) Licences are confirmed by a person before bundling |
| A4 | Permits | (a) Every entry has an official HTTPS host, a quote, a reviewed date and a booking link. (b) It turns STALE after its window. (c) The PAP/RAP note appears only for a traveller flagged as a foreign national. (d) The drone note links to DigitalSky and says a UIN may be needed. (e) No permit is ever shown as granted or available |
| A5 | Bengaluru transit | (a) Five synthetic city trips return Google Transit legs or "not available". (b) Only an official GTFS feed with a licence is imported. (c) The timetable is labelled "scheduled, not live" |
| A6 | Local routing | (a) The owner decision is recorded. (b) The fallback order is Google, then local, then "no route". (c) A local route carries OSM attribution and is drawn only on the offline map. (d) `motorcycle_legal` stays UNKNOWN. (e) Package size, RAM use and graph build time are measured on the owner's PC and recorded. (f) Smart App Control does not block the bundled runtime |
| A7 | Held items | Existing tests still show TRAVEL-11/12/13 as BLOCKED_EXTERNAL and TRAVEL-14 deferred, with reviewed links only |

## Owner acceptance (after local acceptance)

For A1–A6 the owner opens one real trip (Bengaluru to Chikkamagaluru by motorcycle is the suggested scenario) and
compares each new section with the official site it links. They then answer "Works" or describe what is wrong.
Only then may the related PROJECT_STATUS row move, and only for the scope checked.
