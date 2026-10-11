# M14A Career job-page transport — 2026-10-07

Career job-page parsing now uses the existing pinned public HTTPS transport
instead of validate-then-requests.get. Redirects and private DNS results are
blocked; HTML/XHTML responses are limited to 2 MB with bounded timeouts and
compression rejection. Parser adapter behavior is retained.

Validation: 17 focused tests passed, no skips/failures, 3.947 s; system check
passed. Five new Career transport tests plus existing Career evidence/adapters
and shared HTTP tests ran with synthetic configuration, in-memory SQLite and
locmem cache. No private DB, migration, network provider or live promotion used.

Recovery is closed for development as user-reviewed preliminary UI acceptance.
Untested UI areas remain unverified. Docker classification is deferred; all
backups, Docker/VHDX and recovery assets retained. Other M14 HTTP/auth/privacy
items remain open; next is scoped M14B password enforcement. T09 is deferred.
