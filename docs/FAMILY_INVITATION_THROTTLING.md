# Family invitation abuse protection

Only authenticated POSTs to `/api/family/account-links/` and
`/api/family/account-links/accept/` consume independent account quotas.
Authentication and CSRF run first. Invalid, malformed and failed attempts count.
Creation has no target field; payload targets and client headers cannot change
the authenticated account's quota. Users sharing an IP keep separate quotas.

Set these environment variables in untracked local configuration:

| Variable | Default | Meaning |
|---|---:|---|
| `ALFRED_FAMILY_INVITE_CREATE_LIMIT` | 5 | Creation attempts per rolling window |
| `ALFRED_FAMILY_INVITE_CREATE_WINDOW_SECONDS` | 3600 | Creation window in seconds |
| `ALFRED_FAMILY_INVITE_ACCEPT_LIMIT` | 10 | Acceptance attempts per rolling window |
| `ALFRED_FAMILY_INVITE_ACCEPT_WINDOW_SECONDS` | 600 | Acceptance window in seconds |

Limits and windows must be positive. `ALFRED_FAMILY_INVITE_THROTTLE_DIR` defaults
to `ALFRED_DATA_DIR/artifacts/security/family-invites` (checkout root when the data
directory is unset). Use a separate directory on local disk, shared by all app
processes on this one host; do not reuse the ordinary cache or clear active
protection state. This store uses the already installed diskcache dependency.

Reservation uses one `Cache.transact()` transaction for checking and updating
bounded timestamp histories. No default Django/DRF cache atomicity is assumed.
Active quotas survive default-cache clearing and process restarts; expired
histories are removed on subsequent attempts. Eviction is disabled. Stored
values contain only account IDs, scopes and timestamps, never invitation codes,
family names or financial information. Keep the system clock accurate.

Exhaustion returns HTTP 429 with `Retry-After` before invitation service writes.
Storage/configuration failures fail closed with safe HTTP 503 and class/reference
logs. Complete unusable codes receive one generic HTTP 400 message; incomplete
codes retain format guidance. Reads, consent/revocation and other APIs keep their
existing behavior. This is per-account abuse protection, not a general network
DoS or cross-account brute-force defense. No Django migration is required.

Verification: isolated API tests plus simultaneous thread/process reservations;
real Chrome checks throttling feedback, retry acceptance and financial opt-in.
Development only: source promotion remains a separate controlled operation.
