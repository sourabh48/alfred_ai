> Historical operator evidence, preserved during consolidation on 2026-10-21. Current state and instructions: [PROJECT_STATUS.md](PROJECT_STATUS.md). Dated deployment/acceptance claims below are not current release approval.

# M14 controlled live deployment - 2026-10-11

## Release-closure follow-up - 2026-10-11

Installed application source still equals 30e0b3f75e785f639897ad36c19090c6a4e8675f;
native loopback health rechecked HTTP 200. No live database, credentials, tokens,
service configuration or application source was changed during this follow-up.
Existing operator changes and every backup remain preserved. M15 development
continues only in its separate worktree; no M15 source was integrated here.
Final M15 HEAD: b05c3b0549241efd206e34f4c214db27c7d23f2a, clean separate branch,
following protocol f29d6d0c49d384c49d99559a85d2dfe959710ae3. Actual M15 gate:
108 backend, two synthetic Chrome and 19 native checks PASS; real local Ollama
encrypted mock upload/restart/download/retrieval PASS. No real cloud/OpenAI call.

Recovery supplement SHA-256 rechecked unchanged:
670a495a2114b92dd5c0782195725eb4e7700db1733025dc172e1b0cf875a061.
Its 9691-entry authenticated decryption/hash receipt remains PASS. Original
portable archive/header encryption and separate known password are independent
of Windows DPAPI. The 9690-file DPAPI recovery set requires the current protected
profile; the supplement can be decrypted independently using its recovery key.
The supplement/key remain on this device. No approved external destination or
separate secure key location was provided; export and restore using off-device
material are PENDING. Fixed internal drives are not off-device recovery. No
archive, backup or recovery key was deleted or exposed. Existing prepromotion
archives represent their recorded snapshot, not a new postdeployment snapshot.

Real-account normal browser sign-in has been requested without credentials in chat.
No normal-session visual observation has occurred during this follow-up:

| Required acceptance area | Observed result |
| --- | --- |
| Dashboard/financial summaries | PENDING |
| Expenses/bank accounts | PENDING |
| Investments | PENDING |
| Loans/EMI details | PENDING |
| Family relationships/consent | PENDING |
| Travel history/saved plans | PENDING |
| Documents/media | PENDING |
| Session/logout | PENDING |

Synthetic Chrome/HTTP checks do not replace these acceptance items. No existing
account password was changed and no replacement account was created. Diagnose
any actual sign-in failure safely before offering an authorized supported reset.

Fresh fetch: origin/master da74570681165cfa46dd3186f95ee400643c41d6 remains an
ancestor of frozen local master; M15/runtime/private files remain excluded. The
ordinary push is prepared but explicitly awaits authorization. Re-fetch/recheck
ancestry before `git push origin 30e0b3f75e785f639897ad36c19090c6a4e8675f:refs/heads/master`;
stop on divergence, never force. Independently compare remote SHA after any
authorized push. No push was performed.

Deployment authorization: user explicitly approved only the frozen release and
family-sharing migration, subject to the final safety gates. Installed branch:
`master`; exact source `30e0b3f75e785f639897ad36c19090c6a4e8675f`.
Application/test source has no working-tree difference from this commit. Original
operator checkpoint additions, skill-lock changes and two untracked documents are
preserved. No M15 source was promoted; no remote push was performed.

Runtime: `F:/ALFRED/restored-runtime`, database `db.sqlite3`, service listening only
on `127.0.0.1:8000`. It was initially already stopped; graceful stop confirmed no
writers. Source was switched only after backup freshness and rehearsal passed.
The family migration and reconciliation completed before service startup.

## Recovery gates

Preserved recovery set: `F:/ALFRED_BACKUPS/m14-prepromotion-20261011-1645`.
All 9690 DPAPI-protected files were decrypted and hash verified. The original
portable Desktop recovery archive still matches its previously verified hash.
Fresh quiesced SQLite backup and independent restoration passed integrity and
foreign-key checks; all tables matched the protected baseline and live source.
Current configuration, encryption keys, media, models and operator files matched
the recovery manifest. After deployment 9681 config/key/media/model file hashes
still match. Jobs and protection history are preserved; normal new startup probes,
heartbeats, cache entries and request-limiter activity are expected runtime state.

An additional profile-independent authenticated-encrypted recovery supplement is
verified at `portable-current-recovery.encrypted.zip` under that recovery set.
It contains 9691 encrypted entries, including the fresh snapshot, protected config,
keys, media, queue, source bundle and operator files. Reopening and decrypting every
entry with the separate `portable-current-recovery.key` passed every hash without
DPAPI. That key is ACL-private, never printed or committed; preserve it separately
with the archive. No off-device export was performed. Original recovery archives
and every diagnostic/snapshot file are retained; no deletion was performed.

Rollback remains the existing controlled-promotion plan: stop access/writers,
preserve evidence and later writes, recover source `a9d096e` plus compatible private
DB/config/key/media/queue data into a separate recovery folder if required. Keep
family sharing OFF and LAN closed on older source. Never restore over accepted
later writes. Live token rotation/fallback retirement is separately authorized and
was not performed.

## Migration and reconciliation

Only `family.0004_financial_sharing_opt_in` was pending and applied. Dependency
`family.0003_familyaccountlink_share_financial_summary` and M13C/M13D migrations
remain applied. The refreshed private-copy forward/reverse/replay rehearsal passed.
Historical financial sharing is OFF in both directions; family relationships remain
intact. Users must explicitly opt in again. No financial calculation, account,
balance, expense, loan, investment, identity/fingerprint or other canonical record
changed. Comparison covers every table, excluding only the two consent columns
and the single expected added migration-history row. Post-start reconciliation,
integrity, foreign keys, system checks and migration drift passed. No migration is
pending and no live email token was re-encrypted.

## Validation and acceptance

Frozen-source regression evidence remains 357 backend, 12 Chrome and 19 native
source/runtime checks, zero failures/skips. No application source changed since.
Deployment added 21 actual loopback HTTP/worker checks PASS: four health endpoints
200; login password/CSRF form 200; page authentication redirects; anonymous APIs
403; token-only authentication refused; native oversized-body request 413; current
worker heartbeat, queued startup probe and durable queue integrity PASS. No new
failed jobs or interrupted claims. Service was reconciled again before final start.

Separately, 21 authenticated compatibility checks passed on an isolated current
private database copy: Finance, Family, Loans, Expenses, Investments, Travel and
Documents pages/APIs; existing loan history; CSRF rejection; configured parser/
upload budgets; oversized upload 413; three existing owned document downloads and
foreign-owner refusal. No private document was parsed as an automated test fixture,
no cloud access was permitted, and no live session/financial row was changed by
this harness. It does not prove actual existing-account password sign-in.

Earlier harness failures are preserved in the recovery folder. Django test login
attempted a last-login write which the read-only database rejected; the Family GET
performs invitation-expiry maintenance and also cannot run on a read-only connection.
The harness was moved to an isolated private copy. An empty synthetic request
omitted its Content-Type; a nonempty one correctly exercised the 413 boundary.
A local HTTP helper name shadowed its module and was corrected. No deployment
source correction, live corruption or unexplained application failure resulted;
the runtime was stopped during diagnosis and reconciled before restarting.

LIVE SERVICE = HEALTHY; DATABASE RECONCILIATION = PASS.
Final real-account acceptance remains PENDING: normal password sign-in and browser
inspection of the requested screens, balances, owned documents and explicit family
consent. Some restored accounts already have unusable/unrecognized password formats;
format-only evidence is private, all credential rows remain unchanged. No password
reset or credential substitution is authorized/performed. A user acceptance prompt
is pending; complete acceptance before declaring the entire deployment complete.

## GitHub and M15

Fresh `origin/master` is `da74570681165cfa46dd3186f95ee400643c41d6` and is an
ancestor of the installed frozen release: ordinary fast-forward is safe at this
check. Re-fetch immediately before any separately authorized push; stop if the
remote diverges. No force push and no remote update were performed.

M15 remains clean and isolated at `F:/ALFRED_DEV/m15`, branch
`codex/m15-persistent-memory-20261011`, HEAD
`a06f3e114f9bb1a53fccfbaedb9e0833dc93a20f`.

Safe deployment receipt and detailed local evidence reside in the recovery set,
including `deployment-apply-proof.json`, `deployment-reconcile-proof.json`,
`deployment-live-http-health.json`, `deployment-readonly-smoke.json`,
`deployment-backup-verification.json` and `portable-current-verification.json`.
Do not publish private recovery manifests, keys, snapshots, configuration or logs.
