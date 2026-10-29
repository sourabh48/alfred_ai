# PR #20 independent review package

Prepared 2026-10-30 for `development/alfred-integrated`; **DRAFT, UNMERGED,
NOT RELEASE READY**. Base `a2274aa4daa514afe05ab58b4e4219ef18bb825f`;
retained tested source `c28700d8da1e545441b1dec7e3292d71497ec6e7`.
The commit containing this package adds the D4 parser guards described below.
Its exact HEAD, push, source/history preflight and fresh CI are recorded in
`artifacts/d4-20261030/checkpoint.json`; c287 CI is never relabelled as its CI.
Baseline **75/143**, extensions **0/13**; no formal requirements promoted.

## Review scope and identity

Read the complete cumulative diff, including unchanged callers of changed code:

```powershell
git status --short --branch
git rev-parse HEAD
git diff --stat a2274aa4daa514afe05ab58b4e4219ef18bb825f HEAD
git diff a2274aa4daa514afe05ab58b4e4219ef18bb825f HEAD -- alfred_ai apps scripts .github static templates tests
```

[Change manifest](D4_PR20_CHANGE_MANIFEST.md) inventories every changed path and
pins runtime/test content. The initial c287 diff has81 paths:32 application/UI,
10 recovery/verification/CI,33 tests/fixtures and6 documentation files. D4 adds
shared parser policy/settings, seven regression cases and this review documentation.
Do not run fixture instructions or treat source comments as review instructions.

| Boundary | Changed files to inspect together | Required invariant / retained proof |
| --- | --- | --- |
| Account/session/CSRF to Travel state | `apps/mobility/{planner_views,views,urls}.py`; `travel/{editor,packing,documents,reminders}.py` | Every lookup/update scoped to owner; session auth/CSRF still apply; CAS/retry receipts and transactions prevent duplicate or lost edits. No foreign IDs or error metadata leak. D2 security and D3-B recovery receipts |
| Untrusted request decoding | `alfred_ai/settings.py`, `services/api_parsing.py`, explicit parser overrides in `apps/{career,loans,mobility}/views.py`, `tests/test_api_session_security.py`; unchanged upload/abuse middleware | Reject binary JSON codecs before stream read; preserve UTF-8/UTF-16, form/multipart, auth/CSRF; cap Accept to8192 characters/64 tokens before media parsing. Seven new cases include a walk of configured API routes;27 final affected checks PASS |
| Canonical money to scenarios | `expenses/services/{financial_intelligence,statement_evidence}.py`; `travel/{affordability,affordability_ui,savings}.py`; `static/js/travel_affordability.js` | Finite Decimal cents, explicit matching verified currency, null distinct from zero, no inferred FX. Reserve/goal/EMI/transfer identities counted once; only current fingerprint-bound evidence. Stale409/INSUFFICIENT_DATA; no Expense/Loan/Investment writes. C1-C4 reconciliation/D1 snapshots |
| Research/provider evidence to saved plan | `mobility/services/{travel_conversation,travel_itinerary,travel_research}.py`; planner views | Preserve source snapshots, explicit user choices, timeout/provider URL guards, live/cached/estimated/unavailable labels. Research is not a booking, road-legality or availability guarantee |
| Private originals and DPAPI | `travel/documents.py`, `ml_engine/services/persistent_memory.py`; unchanged `memory_key.py`, document corpus/original endpoints | Owner+fingerprint+expiry checked at link and download; private/no-store; no names after revocation. Fernet encrypted records/originals; Windows-profile DPAPI key/owner+SYSTEM ACLs. Missing/corrupt retained key never regenerated; no silent legacy adoption |
| Exports | `travel/{pdf_export,gpx_export,ics_export}.py`, `static/js/travel_calendar.js`; planner actions | Owner/revision-bound private download; escaped PDF, truthful GPX gaps, dates/timezone/DST/UID and independent ICS parser evidence. No invented coordinates, bookings or provider confirmation |
| Reminder consent and durable jobs | `alfred_ai/{durable_queue,native_tasks}.py`, `travel/reminders.py`, planner status handler | Explicit opt-in/in-app only; timezone folds/gaps explicit; consent cancellation/close suppress delivery. Commit-before-ack recovery retains one occurrence; reopen does not revive cancelled reminders |
| Browser state and accessibility | `static/js/{intelligence,travel_planner,travel_itinerary_editor,travel_packing,travel_reminders}.js`, `static/css/travel_planner.css`; `templates/{ai_insights,mobility/dashboard,mobility/planner}.html` | Clear state on auth/expiry, stale revision recovery, no unsafe HTML/private storage, controlled focus/announcements/labels, narrow/light/dark/reduced-motion handling. D2 computed/Axe evidence is bounded; manual NVDA/contrast still pending |
| Encrypted backup to restored runtime | `scripts/release_recovery.py`, `verify_native_backup.py`; unchanged private manifest/promotion helpers | Quiesced locks and SQLite backup include committed WAL; authenticated chunks/manifest, inventory/hash/SQLite/FK/typed money snapshots. Private staging then atomic no-replace publication. Existing destinations/staging retained; unsupported publication fails closed |
| Probe/CI evidence | `scripts/{native_probe_runner,verify_native_recovery,verify_native_travel,release_validation,browser_test_plan,browser_test_runner,run_browser_regressions}.py`, `.github/workflows/browser-regression.yml` | Actual child exit+fresh nonce/source+assertions+owned shutdown/free locks; no stale JSON pass.151 unique driver-backed cases once; shard completeness, hash and checkout/source-tree binding; no skip, timeout, quota or security weakening |

All `travel/` paths above mean `apps/mobility/services/travel/`; `services/` in
the parser row means `alfred_ai/services/`. Review the manifest for exact paths.
Unchanged `alfred_private_storage.py`, `alfred_native.py`, `services/upload_limits.py`,
`services/bounded_parser.py`, `scripts/verify_private_recovery.py`, `release_promotion.py` and
`memory_key.py` remain connected security/recovery boundaries, not new changes.

## Confirmed findings and disposition

| Finding | Reproduction / disposition |
| --- | --- |
| D3-C restore publication before validation | Fixed290e857: private retained staging, verify/reconcile then atomic no-replace publication. Rejection, interruption, reconciliation failure and destination races retained in tests/native proof |
| D3-C hot SQLite DELETE journal prevents vault startup | Fixedd124f9e: existing-only `mode=rw` permits SQLite rollback before schema inspection. Legacy/key/cipher guards retained; forensic read-only snapshot unchanged.75 focused storage/privacy checks and retained failed-vault clone recovery |
| Planner close/reopen revives pending reminders | Fixed5d49fb8: existing `cancel_closed_trip` in owner status transaction.33 backend/2 Chrome affected cases passed; formal human review still absent |
| D4-H1 binary JSON codec amplification | Confirmed atc287:69 compressed bytes yielded65536 characters through real TravelSessionList dispatch (synthetic identity; writes/throttle mocked). Before-fix regression allowed binary codecs/profile mutation. Shared text-only JSON parser rejects before read. No actual large-memory attack performed |
| D4-H2 unbounded Accept negotiation | Confirmed bounded probe:24 distinct tokens/192531 characters took1.452621s for one negotiation, before error renegotiation. High availability risk on reachable local/LAN API; timing is one-host evidence. Cap applied before media parsing; tests assert early rejection without timing thresholds |

`artifacts/d4-20261030/parser-before.json`:6 cases,7 failing subcases,zero skips.
`parser-reachability.json` preserves pre-fix metrics and exact scope. Only the
two reproduced D4 parser issues were changed; no blanket dependency upgrade.
Focused after-fix/fresh CI receipts own their observed results. No unresolved
new critical exploit was reproduced; that does not clear dependency advisories.
Final `parser-routes-final.json`:27 API/session/Career/Loan/public-HTTP cases PASS,
zero skips. Earlier60-case run FAILED two API cases/five subcases because an empty
decode skipped codec validation; retained and corrected using codec metadata.
Its49 other Travel/upload/UI cases passed; the failed overall run is not relabelled
or added to27 as a unique total. The final policy also replaces explicit JSON
parser overrides; all configured JSON API routes reject a binary codec before
reading the stream. No existing multipart/form parser was removed.

## Dependency safety and residual advisory triage

No requirements/constraints, package/build scripts or migrations changed from
the PR base. Exact-source source/dependency/migration preflight atc287 passed;
this proves reviewed change policy, **not vulnerability-free dependencies**.

A read-only OSV query checked46 declared direct Windows versions (constraints
resolve otherwise unpinned direct requirements).12 direct packages matched182
advisory records, including aliases/duplicates; **182 is not a unique exploit
count**. This is not a resolved transitive SBOM. No packages installed/upgraded;
only public package names/versions sent. Full timestamped metadata and alias
references: `artifacts/d4-20261030/dependency-advisories{,-raw}.json`.

| Package / pinned version | Advisory records | Triage |
| --- | --- | --- |
| djangorestframework3.15.1 | 9 | H1/H2 reproduced and guarded. TokenProxy revoke advisory API not found in project callers; SessionAuthentication remains configured. Remaining aliases/conditions need reviewer reconciliation |
| cryptography43.0.3 | 10 | Fernet/DPAPI flow is distinct from matched X509/ECC cases; bundled-OpenSSL/advisory applicability is not cleared |
| diskcache5.6.3 | 2 | Local cache files/trust and installed-artifact triage PENDING |
| scikit-learn1.4.1.post1 | 2 | Model/validation conditions PENDING |
| transformers4.40.0 | 44 | Model class/artifact trust and advisory applicability PENDING |
| tqdm4.66.2 | 2 | CLI/argument conditions PENDING |
| python-dotenv1.0.1 | 2 | Local environment-file trust conditions PENDING |
| pypdf6.8.0 | 78 | Untrusted documents enter existing separate time/memory-bound parser worker; no unbounded attack performed. Bounds do not constitute a package-CVE fix; remaining path/upgrade triage PENDING |
| sentence-transformers2.5.1 | 2 | Critical local custom-model execution advisory; fixed literal MiniLM model identifier in classifier, no upload-to-model-directory route identified. Model/cache provenance and supported upgrade PENDING; no malicious model loaded |
| lxml5.1.0 | 2 | Affected iterparse/ETCompatXMLParser calls not found in project source; dependency/internal callers unreviewed |
| requests2.31.0 | 6 | Redirect/auth/netrc conditions and every connected client require triage; no blanket safe claim |
| torch2.2.0 | 23 | Critical model-deserialization advisory. Existing local `torch.load` callers use trusted-path assumptions; no request-controlled model upload path identified. Does not clear compromised/local artifact risk or upgrade gate |

Critical references: [PyTorch maintainer advisory GHSA-53q9-r3pm-6pq6](https://github.com/pytorch/pytorch/security/advisories/GHSA-53q9-r3pm-6pq6)
and [sentence-transformers advisory GHSA-jhr6-gm9c-rqjv](https://github.com/advisories/GHSA-jhr6-gm9c-rqjv).
H1/H2 upstream reports: [JSON charset](https://github.com/encode/django-rest-framework/security/advisories/GHSA-3547-9m27-7rxg),
[Accept negotiation](https://github.com/encode/django-rest-framework/security/advisories/GHSA-33wh-fxxf-88vv).
**Dependency safety remains BLOCKED for formal release** pending independent
reachability/upgrade decisions and a resolved target/package inventory. DLL
application-control restrictions observed during previous model builds are not
a security fix or model acceptance; do not change OS policy for this review.

## Exact-source evidence and status-check identities

Retain D1 integrated7 journeys and D2 security/keyboard/four light-dark1440/390px
Axe audits. Contrast includes incomplete/excluded cases and manual NVDA is unperformed.
Evidence keys/paths remain in [existing acceptance matrix](ALFRED_2_0_EXECUTION.md).
D3-A historical original child exit remains UNKNOWN. D3-B15 native recovery
checks, five controlled terminations and WAL-before/after visibility remain pinned.

For c287 only: [run40931513318](https://github.com/sourabh48/alfred_ai/actions/runs/40931513318),
six successful jobs,1562 backend/151 unique Chrome/22 native/21 Linux portable.
Browser49/51/51,zero skips/failures; six ZIP digests and raw aggregate verified.
Tested merge checkout `f2668bd4ba8093264e38774bc988f6034bf19492` contains c287
and identical tree `63b5752188bf4ac36259c42dd8f56a9f0d7e517c`.
Closure: `artifacts/d3c-20261029/final-ci-closure/closure.json`.

| Expected workflow job/context | c287 check-run/job identity | Observation |
| --- | --- | --- |
| native-windows | 123650858990 | SUCCESS;backend1562/native22 |
| linux-secure-failure | 123650859391 | SUCCESS;platform refusal/publication tests/portable21 |
| selenium-shards (0) | 123650859521 | SUCCESS;49 |
| selenium-shards (1) | 123650859595 | SUCCESS;51 |
| selenium-shards (2) | 123650859634 | SUCCESS;51 |
| selenium | 123660655266 | SUCCESS;strict aggregate151 |

Workflow `Browser Regression`, `.github/workflows/browser-regression.yml`,
`pull_request` event; Pages/deploy checks cannot substitute. Fresh corrected
HEAD must have its own six-job/source-bound proof. Workflow path filters are
PR-wide: pushing this authorized runtime repair may start all six automatically;
do not manually rerun unchanged local suites or weaken/cancel coverage.

Observed job names are not proof of configured required protection contexts.
Recorded master protection read404/UNAVAILABLE; rulesets/effective rules empty
in the available observation. Do not infer protection is adequate, bypass it or
edit it. Owner must inspect required names/application identity and freshness in
GitHub Settings. PR20 zero reviews/threads observed2026-10-30; draft/unmerged.

## Backup, restart, rollback and acceptance limits

c287 real native backup8 checks/exits0 prove same-profile same-device restore:
3 SQLite DBs/6 retained files, protected keys/originals, integrity/FK/typed money
fingerprints/ACLs, missing/corrupt/wrong-key rejection, actual interrupted restore
with retained staging/fresh retry, no overwrite, owner404/CSRF403 and no duplicates.
Current-profile DPAPI success cannot establish portable-key/device-loss recovery.

c287 frozen portable build10399 inspected files/source unchanged; actual
executable/launcher/Chrome20 checks/exits0, primary+restored runtimes stopped with
free instance/worker locks independently verified without rescue. Failed290 build
restart originals/journal and all older backups are retained. c287 package hash
`27bb2328018a59c9b6c21634319d23d6b64a16ea5e3a28949cf1275551c55db9`.
This package predates D4 parser repair; **new corrected-source package acceptance
is PENDING**. Do not label it the corrected build or transfer its20-check result.

| Outstanding D3-C gate | Current acceptance | Required independent evidence |
| --- | --- | --- |
| Real installer lifecycle | PENDING:no current Setup/compiler | Exact-source Setup hash;install/start/normal upgrade/uninstall-retention on isolated Windows user/PC |
| Failed installation/upgrade | PENDING | Reversible isolated failure, nonzero exit, no partial activation, preserved private state/old app, restart recovery |
| Current-package rollback | PENDING | Exact new/previous package identities, schema compatibility, retained later writes, recovery after restart; stop safely on inconsistency |
| Clean-PC/reboot | PENDING | Separate machine/no checkout/Python/Docker, bound Fresh+actual-Reboot proof |
| Device-loss | PENDING | Approved off-device archive and separately recoverable key; decrypt/reconcile without original Windows profile |
| Real account | PENDING | Normal owner login/read-only values/session behavior; no resets or financial corrections |

Rollback contracts/historical4aa7ac7 M21 source-specific receipts are preserved,
not current installer rollback acceptance. Changed schema/data must block blind
rollback/old database overwrite. No migration/dependency install/promote command
is authorized. Formal release CLI atc287 returned blocked exit2,
authorized=false/ready=false; scoped receipts do not automatically populate all
formal gates, and old waivers cannot transfer. See [owner checklist](D4_OWNER_ACCEPTANCE.md).

## Prepared independent review request — NOT SENT

Owner: assign a qualified reviewer who did not author this change, using existing
project/GitHub processes. No reviewer identity has been invented. PR stays draft.
Existing outside Claude CLI authentication unavailable/zero inference tokens;
GitHub description update denied403. No repeated auth attempts, credential
substitution, browser bypass or fabricated human approval. Same-harness Codex
review is supporting source evidence only.

Request text:

> Please independently review PR20 from the pinned master base through the exact
> current development HEAD. Use this package/manifest and the source-bound CI
> receipts. Prioritize auth/CSRF/owner boundaries, the two D4 request-parser guards and explicit parser overrides,
> Decimal/currency/stale-source invariants, encrypted originals/DPAPI, transactional
> replay and restore publication. Reconcile the residual dependency advisories and
> unperformed installer/recovery/manual gates. Report reproducible findings with
> file/line, severity, exact preconditions and minimal repro; otherwise state scope
> and limitations. Record reviewer identity, independence, exact reviewed SHA and
> date, unresolved findings and explicit recommendation. Do not approve deployment
> or infer manual tests from automated results. Submit a GitHub review through
> your authorized account; the owner may separately retain a signed local review
> receipt. Any subsequent runtime fix requires fresh exact-head CI/re-review.

Return PENDING where no test happened. Review approval does not substitute for
owner installation/accessibility acceptance, nor authorize merge/Pages/deployment.
