# Chat-first Travel Planner

Alfred now starts travel planning from dates, a budget, duration or a craving.
Open **Travel Planner** and try:

> I have holiday from 2 October to 5 October. Budget is ₹15,000. Suggest me somewhere.

Alfred reuses your configured starting city; enter a different city to change it. It compares
up to three destinations with your saved travel history and preferences. Choose
one, select **Build itinerary**, and adjust it in chat. For example, **Day 2 is too
busy. Make it relaxed.** Save a draft at any point, or **Save Travel Plan** once
the destination, dates and itinerary are established.

## What is included

- Persistent messages, quick replies, source/provenance details, destination
  cards, comparison and a flexible day-by-day itinerary.
- Nullable destination and dates for draft/research/suggestions-ready plans.
  Existing records and fields are preserved by mobility migration `0009`.
  Migrations `0010`–`0012` add provider evidence, usage, destination history and bus mode.
- Explicit destination selection. “What about option 2?” is a reference, not
  consent to choose it. Model suggestions and inferred home/vehicle choices
  retain their source, confidence and confirmation state.
- Budget allowances in INR: minimum, expected and comfortable totals, category
  breakdowns, assumptions and lower-cost alternatives.
- Vehicle-profile mileage and tank data when available. Unknown mechanical
  limits, fuel-station availability and road suitability are not invented.
- Background research with database progress, bounded source requests, cached
  public findings, duplicate-worker leases and restart recovery.
- Recheck Trip and automatic stale-evidence refresh when reopening a saved trip
  within 15 days of departure. Rechecks preserve itinerary edits.
- Settings → Travel Preferences: edit/accept/remove preferences, choose Mostly
  New/Balanced/Mostly Familiar, turn learning on/off, reset learned signals.
  Explicit preferences survive a learned-preference reset. Inferred signals
  lose ranking weight with age.
- Optional post-trip ratings and preference feedback. Uploaded photos may be
  unassigned. EXIF date/GPS or supplied metadata can propose associations;
  **Add**, **Review** and **Ignore** leave the decision with the user.
- Photo preference signals require both media-learning opt-in and a favourite
  with user-supplied tags. Photo counts never imply satisfaction.

## Budget rounding and quoted prices

Planning allowances use Decimal arithmetic and whole INR amounts, rounded half up.
The same rule applies to itinerary edits: a 25% reduction of a ₹1,006 stay
allowance produces ₹755. A per-person target is rounded to whole rupees before
multiplying by the traveller count. Edits preserve category/daily totals and the
existing emergency buffer; minimum/comfortable totals agree with their line items.

Provider quote amounts retain their supplied precision as decimal strings. Only
current, compatible whole-trip INR quotes with a source and available status enter
the selected-price list. They remain separate from estimated allowances and do not
establish a booking. Invalid, expired or incompatible quotes do not replace estimates.

## Evidence and present coverage

The local conversation engine uses structured intent extraction and transparent
ranking. It does **not** send chats to a hosted language model. It supports the
documented requests and edits, and asks for clarification for unsupported edits.
It is not a general-purpose conversational language model.

No-key Wikivoyage discovery can find geotagged destinations beyond the 13-place
offline seed catalogue. Coverage is incomplete and community maintained. Failed
or unsuitable discovery falls back to the seed catalogue with a visible reason.
Arbitrary named destinations can use configured geocoding; ambiguous results
require selection. Unknown origin distances remain unknown.

The research panels show weather, stays, transport, permit/source leads, places,
estimated cost formulas and provider freshness. Configured adapters support
Open-Meteo, openrouteservice, authorized Overpass and opt-in Duffel stay/flight
search. See [provider configuration and limits](TRAVEL_PROVIDERS.md). Their
implementation and fixture tests do not establish live-account acceptance.
Missing credentials leave the affected category unavailable and retain the plan.

Use **Load map** to display saved route/place geometry and opt into browser tile
requests. No tile request occurs before that action. Map tiles can be disabled;
geometry still works. Car-profile routes do not establish motorcycle legality.
The staff-only **Internal provider usage** panel lists usage and configuration
status by category without exposing credentials.

Weather predictions have retrieval/expiry times; dates outside the forecast
window stay **UNKNOWN**. Saved API reads age forecasts and offers, remove expired
weather proposals, and label expired availability as unknown. Cached results are
never presented as a new live fetch. Rechecks retain edited days and allowances.

Broad web research needs configured Brave storage rights/paid-use opt-in or an
authorized SearXNG endpoint. Wikivoyage is the limited community fallback. Search
snippets and tourism links are leads; they do not verify current permits, opening,
fees or inventory. Rail and bus availability remain unavailable without authorized
integrations. External stay, transport and map links are unchecked searches.
ALFRED makes no bookings, reservations or payments.

Every research run keeps its evidence, timestamps, freshness, uncertainty and
request snapshot. Private names, home addresses, travel logs, vehicle details and
media are excluded from public research queries. The planner sends only required
public place names, city coordinates, dates, route modes and search categories;
occupancy is included for stay/flight searches. Free-form conversations are not sent.

## Run and configuration

Keep runtime secrets in untracked `config/local.env` under the selected data
directory (the checkout for source runs). Both source and native startup load it.
Process environment variables take precedence, followed by `config/local.env`,
then legacy `.env`. Native `config/native.env` retains control of signing secrets.
Restart the source server and worker after changes. No cloud hosting or model API
key is required. Provider account decisions remain optional and explicit.

For source development, with the configured Python environment:

```powershell
python manage.py migrate
python manage.py runserver
```

Run the existing Celery worker **and beat** for background research in the normal
source/LAN profile. Its `travel-research-recovery` schedule runs every two minutes.
The native Windows launcher already starts its local Huey worker and scheduler;
it needs no Redis or external worker service. Research queued while a worker is
unavailable is retained in the database. Restart the worker or use Retry Research.

Before migrating a real installation, stop ALFRED and back up its data directory.
The migration changes nullability and adds tables; it does not clear destinations
or delete old plans. Reverting to the old non-null schema while drafts exist is
not a safe downgrade; use a consistent pre-upgrade backup for rollback.

## Verification

```powershell
python manage.py test tests.test_travel_planner tests.test_travel_continuation tests.test_travel_providers tests.test_travel_web tests.test_travel_http --noinput
python scripts/run_browser_regressions.py tests.test_travel_planner_browser --browser Chrome --require-browser
python scripts/verify_travel_runtime.py
```

The last command creates a disposable native data folder under
`artifacts/travel-runtime/`, uses synthetic account data, runs research according
to the supplied provider configuration, and verifies queued jobs and saved context after restart. It
does not migrate or write the user's live database. Evidence is written to
`artifacts/ops/travel-runtime-verification.json`.

Browser checks cover the exact discovery request, origin confirmation, cards,
comparison, selection, itinerary, targeted edits, saving, reopening, draft quick
chips, preference editing and actual 390/768-pixel emulated viewports. These use
deterministic weather fixtures. The native drill checks configured-provider behavior
and restart recovery; live-weather validation requires usable provider configuration.

The planner is included in **1.1.0-preview.1**. Earlier Windows installations
need the new installer; pulling source alone does not update a frozen executable.
To verify that executable in a disposable data folder:

```powershell
python scripts/verify_travel_runtime.py --executable dist/ALFRED/ALFRED.exe --report artifacts/ops/travel-packaged-verification.json
```
