# Connecting current hotel prices and availability

Provider key, prebook and pricing documentation rechecked on 17 November 2026; alternative provider prerequisites checked on 16 November. No provider account was created, credentials inspected, subscription purchased or real booking attempted.

## Recommended next step: evaluate Nuitée Connect

Nuitée Connect (formerly LiteAPI) has a self-service sandbox and a Rates → Prebook → Book workflow. This is a practical candidate for ALFRED, subject to production eligibility, Indian destination coverage, payment/support needs and its usage terms. It is not connected in this branch.

1. Create an account at [Nuitée Connect](https://connect.nuitee.com). The [official setup guide](https://docs.nuitee.com/docs/getting-a-sandbox-key) says a sandbox key requires no credit card.
2. In Developer tools → API Keys, obtain a **sandbox** key. Keep it out of chat, source control and screenshots. Sandbox results are test data, never a real availability promise.
3. Before enabling live service, review [usage conditions and pricing](https://docs.nuitee.com/reference/api-pricing-usage-costs). Core booking calls are subject to the documented 5000:1 search-to-book ratio; excess searches may be billed; location/index and optional dashboard services may cost money. Do not turn a personal research bot into frequent inventory polling.
4. Production setup is separate. The setup guide currently requires attaching a credit card for a production key. Review eligibility and terms with the provider before doing that.
5. Once account access is available, implement the adapter using ALFRED's private key storage, pinned HTTP boundary, request budgets and Health diagnostics. Do not paste its key into the Google Maps field. No Nuitée credential field or working booking adapter exists yet.

## Required integration contract

- Request rates only after hotel identity, check-in/out, rooms, adults, child ages if applicable, currency and guest nationality are known. Nationality cannot be inferred from a starting city.
- Show provider identity, exact stay/occupancy, room and board type, currency, total/taxes/fees, payment and cancellation terms, and original fetch time. Match the response to those exact request inputs.
- A successful HTTP status alone is insufficient: the [Rates guide](https://docs.nuitee.com/docs/step-2-requesting-room-rates) documents error objects inside HTTP 200 responses. An error or empty result means unavailable.
- Recheck the selected offer using [Prebook](https://docs.nuitee.com/docs/step-3-pre-booking-a-room). If the price changes or inventory disappears, present the new result and request confirmation again. Do not reuse an expired offer.
- Confirm the exact reservation before submitting it. Use hosted/tokenized payment, provider-supported idempotency and booking-status reconciliation after timeouts. A timeout is never proof that booking failed; avoid duplicate reservations.
- Keep research, quote review, reservation confirmation, cancellation and refund states distinct. Only a verified provider booking identifier/confirmation establishes a booked stay.
- Test rate changes, sold-out offers, changed dates/guests, session ownership, concurrent clicks, cancellation, payment failures, retries and outages before enabling production.

## What this branch actually provides

The Google Places integration supplies listings and attributed photos. It does not establish room prices or availability. The planner builds drafts automatically, shows attraction/stay/map research and dated external hotel searches, and offers a stay review with booking-site continuation. Expired hotel evidence does not display old prices or availability as current.

The stock research flow refreshes public data when searching and keeps original fetch timestamps when cached. It uses daily Yahoo market observations, not an exchange real-time quote feed; stale evidence cannot produce a positive research summary. Executable trade prices need a separately authorized broker/exchange feed.

Booking.com requires a managed affiliate account and contract: [prerequisites](https://developers.booking.com/demand/docs/getting-started/prerequisites). Expedia Rapid requires partner credentials and production enablement: [getting started](https://developers.expediagroup.com/docs/products/rapid/setup/getting-started). These are alternatives if an appropriate commercial relationship becomes available.
