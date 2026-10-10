# Local/LAN request protection

The existing Family invitation rolling-window reservation now lives in the
shared throttling service. Its scopes, limits, persistent store and semantics
are unchanged. Runtime guards use a separate non-evicting persistent store;
ordinary cache clearing and process restart do not clear quotas. All applicable
buckets are checked/reserved in one transaction, without partial reservations
after rejection. Expired histories are removed deterministically.

| Scope | Default limit/window |
| --- | --- |
| Login username | 10 / 600 seconds |
| Login peer IP | 30 / 600 seconds |
| All logins | 100 / 600 seconds |
| Signup peer IP | 20 / 3600 seconds |
| All signups | 50 / 3600 seconds |
| Authenticated API account | 120 / 60 seconds |
| All authenticated API requests | 600 / 60 seconds |
| Expensive account operations | 30 / 3600 seconds |
| All expensive operations | 120 / 3600 seconds |

Login includes `/`, `/login/` and `/admin/login/`. Expensive operations include
actual file uploads, import/payoff/retry, provider refresh/research/discovery,
Career matching, AI explanations and runtime-control endpoints. General API
quotas also cover reads and prevent alternate paths from bypassing a bound.
Native listener/task caps and M14E streamed/parser budgets remain independent.
This is a rolling quota, not an account lock flag; successful and failed attempts
both count and a successful login does not reset protection.

Each scope has `ALFRED_<SCOPE>_LIMIT` and `ALFRED_<SCOPE>_WINDOW_SECONDS` settings,
using the names LOGIN_ACCOUNT, LOGIN_IP, LOGIN_GLOBAL, SIGNUP_IP, SIGNUP_GLOBAL,
API_ACCOUNT, API_GLOBAL, EXPENSIVE_ACCOUNT and EXPENSIVE_GLOBAL.
`ALFRED_ABUSE_THROTTLE_DIR` must be an absolute persistent directory; it defaults
under the owner's ALFRED_DATA_DIR/artifacts/security/runtime-limits. Values must
be positive. Invalid configuration or unavailable storage fails closed with a
safe 503 reference/class log. Quota rejection returns 429 with Retry-After,
no-store and safe browser/API feedback before the view can mutate data.

Username/IP/account keys are keyed hashes; passwords, usernames, document text,
URLs and financial values are not stored or logged. Peer IP comes from
REMOTE_ADDR; untrusted forwarding headers do not create new budgets. Account
identity includes immutable account creation time so recreated local/test
databases do not inherit another account's quota. A shared global quota contains
attempts spread across accounts or peer addresses.

Authentication, ownership and CSRF still run independently. The guard does not
grant access. File framing may be rejected first with the existing 400/413, and
bounded multipart parsing precedes the guard; rejected files do not reach the
parser/import view. No migration or new dependency is required.
