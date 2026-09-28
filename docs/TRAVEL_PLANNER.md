# Chat-first Travel Planner

Alfred now starts travel planning from dates, a budget, duration or a craving.
Open **Travel Planner** and try:

> I have holiday from 2 October to 5 October. Budget is ₹15,000. Suggest me somewhere.

Confirm your configured starting city, or enter a different city. Alfred compares
up to three destinations with your saved travel history and preferences. Choose
one, select **Build itinerary**, and adjust it in chat. For example, **Day 2 is too
busy. Make it relaxed.** Save a draft at any point, or **Save Travel Plan** once
the destination, dates and itinerary are established.

## What is included

- Persistent messages, quick replies, source/provenance details, destination
  cards, comparison and a flexible day-by-day itinerary.
- Nullable destination and dates for draft/research/suggestions-ready plans.
  Existing records and fields are preserved by mobility migration `0009`.
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

## Evidence and present coverage

The local conversation engine uses structured intent extraction and transparent
ranking. It does **not** send chats to a hosted language model. It supports the
documented requests and edits, and asks for clarification for unsupported edits.
It is not a general-purpose conversational language model.

The initial offline discovery catalogue covers Nandi Hills, Chikmagalur, Sakleshpur,
Wayanad, Coorg, Gokarna, Hampi, Ooty, Puducherry, Lonavala, Rishikesh, Jaipur and
Darjeeling. It is an editable seed catalogue, not an exhaustive world travel
search. Recommendations outside these locations require additional catalogue
coverage. Unknown origin distances remain unknown.

Live weather uses the project's existing verified Open-Meteo integration and
cache. Forecasts are model predictions, labelled **LIKELY**, with retrieval and
expiry timestamps. Dates outside the forecast window stay **UNKNOWN**.
Deep Research adds bounded public-news searches for travel/closure/permit leads;
headlines are not treated as confirmation of a closure, opening or safety.

Authoritative tourism links are reference links; displaying one does not imply
its page was fetched or its contents verified. Road distances and travel times
are explicitly labelled town-centre estimates. Stays, meals, fuel prices, entry
fees, tolls, permits and other costs are allowances, not live quotes. The app has
no configured live hotel inventory, booking, train/flight availability, verified
turn-by-turn routing or comprehensive restriction/permit provider. Those facts
remain unknown or estimated until an approved provider is integrated. No page is
blind-scraped and no access protection is bypassed.

Every research run keeps its evidence, timestamps, freshness, uncertainty and
request snapshot. Private names, home addresses, travel logs, vehicle details and
media are excluded from public research queries. The planner sends destination
coordinates and date windows for weather, and destination-only notice queries.

## Run and configuration

Keep runtime secrets in untracked local configuration. The planner introduces
no cloud hosting, new credentials or required model API key.

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
python manage.py test tests.test_travel_planner --noinput
python scripts/run_browser_regressions.py tests.test_travel_planner_browser --browser Chrome --require-browser
python scripts/verify_travel_runtime.py
```

The last command creates a disposable native data folder under
`artifacts/travel-runtime/`, uses synthetic account data, performs real public
weather research, and verifies queued jobs and saved context after restart. It
does not migrate or write the user's live database. Evidence is written to
`artifacts/ops/travel-runtime-verification.json`.

Browser checks cover the exact discovery request, origin confirmation, cards,
comparison, selection, itinerary, targeted edits, saving, reopening, draft quick
chips, preference editing and actual 390/768-pixel emulated viewports. These use
deterministic weather fixtures; the separate native drill checks live weather.

The downloaded 1.0.1 preview predates this planner feature. A source change does
not update an already-installed frozen executable; a new Windows build is needed.
