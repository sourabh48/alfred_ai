# Project Status

## Active post-audit implementation — 2026-10-15

Production remains 3932f391; audit baseline bced104 is preserved. Isolated work:
F:/ALFRED_DEV/post-audit, feature/fin-money-tail-20261016. Audit is complete;
the 143-feature inventory is not regenerated. AWS is decommissioned by the user;
older activation advice is superseded. No live configuration, ACL, database,
service, paid provider or GitHub operation is authorized here.

### FIN-MONEY — User, Career and Mobility tail complete locally, 2026-10-16

User source: `2f48d3edf50555299e4072dfd2f9441a3b435af9`; Career source:
`f8c7ebb2400113713ba640e43e76d8340e4607b5`; Mobility source:
`ddb7fca22588f469ff4086766d014732f393cc6c`, based on Career. This documentation
checkpoint follows that tested source. All audited tail register
fields are now Decimal cents in development; the earlier Budget unit is retained
without repeating its migration tests. No production remediation/deployment is
claimed. Frozen release `4aa7ac70` remains unchanged and is not this new source.

Mobility scope: BikeProfile estimated_market_value/monthly_income_support,
BikeServiceRecord.cost, FuelRefillLog.total_cost, TravelPlan.budget,
TripLog.spend_amount, BikeIssueReport projected_cost/nullable actual_cost,
BikeDocument.premium_amount. Reuses M13 finite bounded 14/2 HALF_UP storage and
numeric API fields. Existing signed-value rules and Travel API negative-budget
rejection remain; null actual cost differs from zero. Measurements, rates,
confidence, raw parsed evidence and fingerprints remain unchanged.

`mobility.0013_mobility_money_decimal` is the sole Mobility schema unit, depending
on mobility.0012, the existing expenses.0005 policy and swappable User. It validates
all source amounts/parent owners before capture, retains owned originals and
typed source/parent links, and applies normalized cents with markers. Reverse
restores only unchanged applied values with matching source/owner/parents; edits,
new rows and deleted records survive safely. Reset removes owned orphan evidence.
No currency column, inference, dependency upgrade or unrelated migration.

Derived boundaries were updated where Decimal money met float quantities or JSON:
canonical vehicle cost accumulation, fuel/cost-per-km output, service model
features, dashboards/cache, saved-plan state/preferences/feedback and document
review fallback. Money remains Decimal through canonical accumulation; existing
numeric API/JSON and statistical model contracts are preserved. Initial tests
reproduced mixed-type and Travel JSON failures; regression evidence is retained.

Final `money-integration-final`: **156 backend PASS**, zero failures/skips in one
actual combined run covering User/Career/Mobility, profile boundaries, canonical
finance, projections, reset, vehicle accounting, APIs, extraction/review and Travel.
Final `mobility-browser-final`: **3 Chrome PASS**, vehicle accounting, invoice-cent
correction and saved-plan desktop/mobile reload; screenshots reviewed and Travel
console empty. Earlier User two/Career one focused Chrome flows also passed.
Final system/drift/exact Mobility migration-plan checks PASS. New migration tests
cover originals, nullable zero, finite/boundary inputs, owner/parent guards,
idempotence, edits/deletion and zero cent-history canonical baseline mismatches.
`three-domain-rehearsal-verified`: one enhanced rehearsal PASS after the combined
run, starting with all three preceding schemas and asserting exactly the three
User/Career/Mobility migrations. Independent SQLite backup/restore, integrity/FKs,
converted monetary equality, unrelated typed rows, family permissions, account/
transfer fingerprints, exact reverse and source bytes reconcile with zero
unexpected mismatches. Converted SQLite numeric affinity can change a zero's
storage type; compare its exact value while keeping strict type hashes for all
unconverted columns. This is not a financial discrepancy or a waived check.
`mobility-outputs-final`: one strengthened output regression PASS, exact numeric
dashboard totals and HALF_UP fuel-price/cost-per-km formatting. These two
post-combined test enhancements changed assertions only, not runtime source;
their counts are reported separately, not added to 156.
Evidence: `artifacts/post-audit/fin-money-profiles-20261016/`; failed initial runs
remain diagnostic evidence, not accepted outcomes. No full release/package gate.

Production read-only check at 2026-10-16 09:20 UTC: no port-8000 listener or
production runtime process; HEAD remains 3932f391. Prior stale pre-reboot state is
preserved. No restart, repair, live DB access, backup/ACL/key/remote action. AWS
retired; real OpenAI/cloud OFF. Next is the separate currency design below and a
future authorized candidate integration/release gate, not a production migration.
Changed-source credential/private-path scan: PASS, 28 files, no findings;
AST-only graph update completed successfully. No external scan/API used.

### FIN-CURRENCY — reviewed decision contract, 2026-10-16

Review baseline: `feb650834deb782f0b3f813d4c9231b911eb5255`, isolated worktree
F:/ALFRED_DEV/post-audit. **REVIEW COMPLETE; CONTRACT NOT APPROVED; SCHEMA BLOCKED.**
Budget/User/Career/Mobility conversions are complete and not reopened. No runtime,
schema, migration, provider or historical value changes are authorized by this
review. The recommendations below are proposals, not approved defaults in code.

#### Actual execution boundaries and proposed ownership

| Domain | Inspected implementation today | Proposed currency owner after approval |
| --- | --- | --- |
| Banking / Expenses | [models](../apps/expenses/models.py), [serializers](../apps/expenses/serializers.py), [statement parser](../apps/expenses/services/statement_import.py), [posting/deduplication](../apps/expenses/services/statement_lifecycle.py), [identity](../apps/expenses/services/transaction_intelligence.py): numeric amounts; no canonical currency field or parser currency contract. Account uniqueness is user + account_number. | Account denomination plus immutable transaction settlement denomination and statement evidence. Explicitly confirmed account currency may prefill a **new** posting, never relabel history. Foreign merchant amount/fee/booked FX need separate evidence; account number alone may not identify a multi-currency subaccount. |
| Loans / settlement / closure | [models](../apps/loans/models.py), [API](../apps/loans/serializers.py), [PDF parser](../apps/loans/services/loan_pdf_parser.py), [import](../apps/loans/views.py), [settlement](../apps/loans/services/loan_foreclosure_service.py): Decimal contract/payment/closure amounts, no denomination guard. | Loan contract denomination owns principal/EMI/balance; child evidence records its actual source denomination. Cross-currency payment needs explicit bank-booked credited amount/rate/fees, never a reference-rate guess. |
| Investments | [models](../apps/investments/models.py), [serializers](../apps/investments/serializers.py), [imports](../apps/investments/services/portfolio_intelligence.py), [summary/growth](../apps/investments/views.py): InvestmentCurrencySerializerField validates **amounts**, not ISO codes; totals have no currency partition. | Explicit position valuation/cost-basis denomination; each source quote keeps its own denomination/as-of. Asset units such as crypto are not fiat currency codes. Do not subtract cost from valuation or combine SIPs without compatible denomination. |
| User / Career income / rent | [User fields](../apps/users/models.py), [profile API](../apps/users/serializers.py), [Career model](../apps/career/models.py), [income selection](../apps/career/services/income_intelligence.py), [opportunity form](../apps/career/forms.py), [job evidence](../apps/career/services/job_intelligence.py): profile salary has no currency; opportunity JSON carries currency/period but contains INR fallbacks and `$` -> USD interpretation. | Separate currency for each income/rent input or a reviewed income-source record; do not make one User.country/profile default authoritative for all amounts. Career salary period must stay explicit alongside currency; advisory job JSON never labels profile history. |
| Budgets / savings / cash flow | [Budget](../apps/budgets/models.py), [API](../apps/budgets/serializers.py), [plan selection](../apps/budgets/services/budget_intelligence.py), [canonical baseline](../apps/expenses/services/financial_intelligence.py): month-based plans and derived income/obligation/savings totals lack currency partitions. | One denomination per Budget; spend and utilization only compare compatible amounts. Derived savings/cash flow inherit a validated input group, not a display locale. No automatic correction of recorded Budget.spent. |
| Mobility / Travel | [registers](../apps/mobility/models.py), [APIs](../apps/mobility/serializers.py), [plan persistence](../apps/mobility/services/travel_conversation.py), [budget](../apps/mobility/services/travel/costs.py), [quote precision](../apps/mobility/services/travel/money.py), [stays](../apps/mobility/services/travel/providers/accommodation.py), [flights](../apps/mobility/services/travel/providers/transport.py): stored amounts lack codes; Travel estimates explicitly use INR; provider quote strings carry currency and sometimes a separate due-at-property currency. Only matching INR whole-trip quotes qualify in the current budget evidence path; no FX. | Each valuation, receipt, fuel cost, trip spend and quote owns denomination. Plan budget is a **target** denomination, not all trip transactions' currency. Retain raw provider scale, freshness, scope and separate fee/property currency; never equate an estimate with a booked price. |
| Family / tax / risk / reports | [Family totals](../apps/family/views.py) sum consented member baselines; [Indian tax policy](../apps/ml_engine/services/tax_policy.py) and [deductions](../apps/ml_engine/services/tax_optimizer.py) use amounts without a record currency contract. [Report API](../apps/reports/views.py) lists owned GeneratedReport file references, not a currency-aware export engine. | Preserve owner consent before grouping summaries. Indian tax inputs need explicit INR eligibility; country/policy does not prove a historical record's currency. Reports/ratios/forecasts carry source groups, as-of, completeness and FX basis; no universal scalar across currencies. |
| UI / AI / cache | [formatter](../static/js/app.js) uses legacy INR; [source_context/present_answer](../apps/ml_engine/services/hybrid_intelligence.py) emit currency null/not_recorded and suppress unsupported numeric prose; [baseline/revision](../apps/expenses/services/financial_intelligence.py) and [relationship matching](../apps/expenses/services/financial_relationships.py) have no currency partition. | Locale only formats. AI may cite certified structured groups, never supply code/rate/amount. Currency/provenance corrections invalidate owner caches and derived reports; they never enlarge Family access or private memory/document access. |

#### Decision matrix

| ID / decision required | Recommended safe contract | Blocking condition / current behavior |
| --- | --- | --- |
| C1 — ownership and denomination changes | Recommend metadata on existing records, per monetary input where a row can differ (User income/rent and BikeProfile value/income support); a common code only for an explicitly same-denomination contract/position/Budget. Retain source, confirmation basis, actor/time and prior value. Do not add a parallel financial register. | Approve this ownership layout, parent/child invariants and multi-currency account identity. Account/loan denomination cannot silently change after postings. Salary period also needs evidence; currency approval does not authorize inferring historical periods or rescaling salaries. No model changes now. |
| C2 — unknown historical currency | Persist null; API currency null + not_recorded. Unknown is a state, not an ISO code (`UNKNOWN`/`XXX` must not stand for guessed currency). Corrections require reviewed independent evidence or explicit owner attestation, with provenance. | Already a user constraint: never backfill from INR labels, location, model prose, ambiguous symbols, existing advisory defaults or a newly set account preference. Zero amount does not establish currency. |
| C3 — mixed totals / missing coverage | Certified totals, net worth, budgets, percentages and family sums operate per **known matching** currency. Unknown records remain a review collection with counts/source values, **not a certified unknown-currency subtotal**. Missing components make results incomplete, not zero. | Approve legacy scalar behavior before known mixed records can enter calculations. Existing canonical totals are legacy arithmetic conventions, not proven same-currency financial facts. |
| C4 — ISO codes and precision | Version an offline reviewed ISO 4217 registry: uppercase alphabetic code, validity dates and minor unit. Preserve valid historical withdrawn codes. Proposed initial posting allowlist INR/USD/EUR/GBP fits current 14/2 storage; not a claim that these are configured today. | Approve initial supported set and scale policy. Current cent quantizers cannot preserve three-decimal monetary input; do not silently round unsupported currencies, fund/metal units or crypto into cents. Retain provider evidence separately. No registry download at app startup. |
| C5 — reporting currency | Optional owner-selected reporting preference controls presentation/derived conversion only. It never supplies record denomination or labels historical amounts. | Decide whether an overall converted report is needed in phase one. Recommended first delivery: grouped totals with **FX disabled**; no reporting base selected automatically. |
| C6 — FX source, purpose and freshness | Reference FX is optional, read-only valuation evidence: base/quote, rate direction/precision, provider, effective date, fetched time, publication calendar, source/hash and policy version. Use an on-or-before as-of fixing; never a future rate. Certified conversion requires the expected published fixing; missing/stale/suspended pairs abstain. Round final derived amounts only under an approved policy. | No FX engine or approved source exists. A future reference feed must not supply actual settlement/tax filing values. ECB is an informational candidate, not selected or authorized; actual booked FX remains bank evidence. Approve source coverage/terms, historical-date policy, staleness/calendar and rounding before activation. |
| C7 — API/UI compatibility | Proposed additive typed money evidence uses exact decimal text + code/null + status/provenance, with per-currency groups/completeness. Preserve existing numeric fields during an agreed transition; missing totals are not coerced to zero. Clearly distinguish legacy-assumption output from certified output. | Choose versioned endpoint/opt-in versus coordinated contract change. A known mixed input cannot continue through an unlabeled legacy scalar: reject incompatible writes or make the total explicitly unavailable under the approved API. Existing consumers must be inventoried at cutover. |
| C8 — imports / matching / corrections | Preserve original amount text, parser evidence, owner/account links, transfer legs and historical fingerprints. Currency candidates stay unverified until approved evidence resolves ambiguity/conflict. Gate new transfer/loan-payment/portfolio matching on compatible denomination; cross-FX allocation needs explicit evidence. | Do not rewrite existing deduplication hashes/signatures. Approve versioned rules for genuinely distinct new multi-currency postings, reimport/correction idempotence and atomic rejection with no partial financial writes. |
| C9 — reports, caches and privacy | Every new report/AI amount identifies source currency, as-of, completeness and any FX estimate separately. Invalidation keys include currency/provenance/policy revisions. Apply existing owner/Family consent filtering **before** grouping. | Reports, tax, Career comparisons, budget utilization, family aggregation, model features and display helpers must be covered before mixed-currency activation. No private amount or account data is sent to a rate provider. |
| C10 — reversible migration / downgrade | After approval, separate expand-only nullable metadata migrations by domain, no money rewrite/backfill/default INR. Keep owner-scoped original metadata and guarded correction history; rehearse exact counts, values, identities, ownership, forward/reverse and independent restore. | Reversibility is conditional: refuse downgrade if it would erase new denomination/FX semantics or make an old app combine mixed data. Preserve evidence and require an explicitly reviewed source/data rollback path; never blindly drop metadata or inherit the M15 recovery waiver. |

**Approval package:** (1) record/profile/account ownership C1; (2) grouped/incomplete
totals and API transition C3/C7; (3) supported ISO set/precision C4; (4) guarded
metadata migration/downgrade C8/C10. C2 and privacy boundaries remain mandatory.
C5/C6 can safely be deferred by approving grouped-only operation with no FX;
provider approval is not required just to finish the local metadata contract.
Do not enable mixed-currency writes before all relevant consumers are guarded.

Required post-approval regressions: explicit/unknown/ambiguous/withdrawn codes;
supported/unsupported scales; account/transaction/loan/position/profile currency
conflicts; mixed and incomplete owner/Family totals; consent revocation; numeric
API transition; import/reimport/fingerprint stability; cache/report invalidation;
no LLM override; later FX calendar/weekend/stale/missing/future-rate cases; guarded
forward/reverse with post-migration edits and independent restore. Existing
[AI currency tests](../tests/test_intelligence_currency.py) cover presentation,
not an ISO/FX/accounting implementation. No completed Decimal suite was repeated.

Standards checked read-only on 2026-10-16: [SIX ISO 4217 maintenance lists](https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html)
provide current/historical codes and minor units. [ECB reference-rate documentation](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
describes working-day publication around 16:00 CET and discourages transaction use.
These are documentation checks, not real-provider acceptance, a chosen service,
API integration or authorization. No rate values were imported.

Next safe action: approve or amend C1/C3/C4/C7/C8/C10, explicitly keep C5/C6 OFF,
then implement only the first approved nullable metadata domain and its synthetic
rehearsal. This review itself is complete, not blocked by production downtime.
The next independent roadmap item, AI-HISTORY, needs its own encrypted storage/
retention/recovery contract (UNIT 9); AI-GROUND finance tools depend on currency.
AI-HISTORY contract work can proceed independently while currency approval waits;
it must preserve existing encrypted memory and require explicit history consent.

### FIN-MONEY — Career salary complete locally, 2026-10-16

User implementation committed as `2f48d3edf50555299e4072dfd2f9441a3b435af9`.
CareerProfile.last_salary now uses the existing bounded finite Decimal-cent field
and numeric serializer, preserving the previous signed-value policy. Experience,
scores, confidence, raw resume evidence and income/projection rules are unchanged.
New migration `career.0005_career_salary_decimal` depends on career.0004 plus the
existing User dependency. Owned original snapshots, applied markers, guarded
reverse and owner/orphan reset follow M13. No currency inference or production use.

Evidence in `artifacts/post-audit/fin-money-profiles-20261016`: career-focused
15 PASS; career-integration **63 backend PASS**, including canonical baseline,
projection and document correction/retry; career-contract-final one full-PUT
contract PASS; career-browser-final **one Chrome PASS**, salary save/reload and
experience preserved. Initial browser fixture sent blank skills and correctly
received HTTP 400 under the existing required-skills API contract; fixture now
supplies skills, and an explicit backend regression verifies both outcomes.
Failed diagnostic receipts remain. Zero final skips/failures. System/drift and
exact one-Career-migration plan PASS. Synthetic alias backup/restore, integrity/FK,
forward/reverse, raw evidence/parent/owner preservation and unrelated financial/
family row hashes reconcile. Cent-valued salary fallback baseline unchanged.

At this Career checkpoint, Mobility was next; it is now completed above. No new
full release/package gate and no change to frozen 4aa7ac70 or production 3932f391.

### FIN-MONEY — User income/rent complete locally, 2026-10-16

Based on FIN-MONEY checkpoint `814d4dad`, same isolated branch. User
monthly_income/variable_income/rent_or_emi persist bounded Decimal cents. Existing
strict finite/non-negative/two-decimal input validation and numeric API outputs
remain; signup optional blanks remain zero. Rates/model features and income-mode
heuristics were not redefined. No historical currency inference or new currency
field. Frozen runtime candidate 4aa7ac70 and production 3932f391 unchanged.

New migration: `users.0003_user_money_decimal`, depending on users.0002 only.
It atomically validates all profiles, retains original float representations and
HALF_UP normalized cents in UserMoneySnapshot, and applies with markers. Reverse
only restores unchanged, applied, correctly linked values; new accounts and edits
survive. Passwords, groups, sessions, identifiers, consents and related financial
records are preserved. Owner reset/account deletion removes owned evidence.
Snapshots remain private canonical-DB evidence, never profile API fields.

Evidence: `artifacts/post-audit/fin-money-profiles-20261016/`: user-focused
20 PASS; user-integration **98 backend PASS** (includes focused scope), no skips
or failures; user-browser **two Chrome PASS** (profile cent save/reload and tax);
user-rehearsal-final **one enhanced rehearsal PASS**, adding nonempty family data.
SQLite backup/independent restore, integrity/FKs, alias isolation, original source
bytes, exact reverse and unrelated typed row hashes all reconcile. Cent-valued
history has zero canonical baseline mismatches. Existing login/session/group
compatibility verified synthetically. user-checks system/drift PASS and plan is
exactly the one User migration from the preceding schema. No production DB access.

Read-only operational recheck: production port 8000 has no listener or runtime
process; the prior stale pre-reboot runtime finding remains. No start/stop/repair.
The subsequent Career and Mobility conversions are completed above. Currency
metadata/FX policy stays separate; no deployment or provider activation authorized.

### Banking regression and production diagnosis — 2026-10-16

Development starts at `08f39a88`; frozen runtime candidate `4aa7ac70` and its
package remain unchanged. Read-only production diagnosis: no port-8000 listener,
HTTP connection fails, no production server/worker process or matching Windows
service. Native scheduler belongs to that absent worker. Recorded supervisor
11376/worker 7740 are absent; `runtime.json` says running but predates the latest
Windows boot (2026-10-15 13:40 UTC), as do both runtime logs. Current-user ALFRED
autostart is not registered. Consistent with no restart after reboot; a crash
cause is not established. No live database was opened or service action taken.
Operator action is required to restore service using the documented explicit
`F:/ALFRED/restored-runtime` data directory, not an implicit launcher default.

The intermittent Banking workflow was reproduced in isolation: it actually
fails on Loan sorting with `StaleElementReferenceException`. The refresh root
covered only the hero, excluding form/table controls; an in-flight refresh could
also replace rows after interaction began. The root now encloses the workspace
and late background responses recheck the existing interaction guard. Foreground
actions remain immediate; the next idle refresh fetches fresh data.

Evidence under `artifacts/post-audit/fin-money-20261016`: production-health.json;
banking-baseline-1/diagnostic.json (original failure); loan-race-before and
loan-race-fixed (preserved deterministic failures); loan-race-scope-fixed
(13 PASS: two Chrome workflows + eleven HTTP/UI contract tests); banking-fixed-0
through -2 (three additional independent runs of the original workflow PASS).
Zero skips in successful runs. No full gate or package rebuild. Correction commit:
`0e7e1df35c5afe279050253b97e92ad0ecfc04fc`. Historical currency stays unrecorded.

### FIN-MONEY — Budget register complete locally, 2026-10-16

Verified implementation: `cd696572f0a3ce69260fb1cf212ce700836fb453`; later
documentation-only checkpoints do not change that tested runtime source.

Scope: `Budget.base_budget`, `inflation_adjusted`, `spent`, their model/form/API
boundaries, dashboard amounts and owner reset. Reuses Expense money helpers and
the existing M13 original-snapshot/guarded-reverse pattern. Money is Decimal cents
with HALF_UP normalization, finite/non-negative validation and maximum stored
amount `999999999999.99`; numeric API fields remain compatible. Dashboard stored
amounts and actual Expense accumulation stay Decimal until numeric output;
statistical suggestions/forecasts remain estimates. No balance, loan, investment,
transfer identity or ownership algorithm was replaced.

Pending development migration: [budgets.0002_budget_money_decimal](../apps/budgets/migrations/0002_budget_money_decimal.py),
depending only on budgets.0001 and the existing swappable User dependency.
It validates the complete register, retains exact original float representations
and independent normalized values in owned snapshots, then applies cents with
markers atomically. Invalid historical amounts block conversion without partial
evidence or financial writes. Reverse restores original precision only for
unchanged, applied, still-owned fields; corrections/new rows remain, deleted rows
are not recreated. Owner reset removes owned snapshots, including orphan evidence.
Snapshots are private canonical-DB recovery evidence, not encrypted AI memories.
No currency column/backfill or FX assumption is introduced; legacy screen INR
conventions remain unchanged. Other domain conversions and currency design are
separate work; see newer FIN-MONEY checkpoints above for current progress.

Validation evidence under `artifacts/post-audit/fin-money-20261016/`:
- `budget-focused/receipt.json`: 14 focused tests PASS (included in the combined run).
- `budget-integration/receipt.json`: **74 backend PASS**, zero failures/skips:
  Budget runtime/migrations, canonical baseline, user-data acceptance/reset,
  abuse limits, family boundaries and Expense identity.
- `finance-browser-final/receipt.json`: **three Chrome workflows PASS**, zero
  failures/skips (delayed Loan response, Banking/filter navigation, sample finance).
- `configuration/receipt.json`: system/drift checks PASS; synthetic baseline plan
  contains exactly the one Budget migration. New tests are in the existing M20
  backend selection; no completed M20/M21 gate was rerun.

The file-backed synthetic rehearsal uses SQLite backup and an independent restore,
checks integrity/FKs, forwards on a separate alias, compares all unrelated tables
with typed row hashes (accounts, transfer fingerprints/legs, loans, investments,
family and owners), reverses to exact original row hashes, and proves source bytes
unchanged. No real private records or backup material were used. Screenshots of
the corrected Loan table and final finance workflow were reviewed.

**Local unit PASS; FIN-MONEY overall PARTIAL; no deployment authorization.**
Production still 3932f391; new migration is not applied there. Frozen 4aa7ac70
and package evidence remain their own immutable scope. No native rebuild/full
release gate for this new unit yet. Existing clean-PC/installer, normal-account,
independent device-loss/key recovery and remote CI/protection acceptance remain
pending. The next unit at this Budget checkpoint was User income/rent; newer
checkpoints above supersede that next action. Never infer historical currency.

### Verified local runtime candidate — 2026-10-16

Frozen branch `release/post-audit-runtime-20261016` points exactly to
`4aa7ac70fa27c1410e695470af5c3987235244b1`. It integrates 28 commits / 156 changed
tracked paths since M15 `3932f391`; the source manifest is authoritative for that
inventory. Production and GitHub master remain at `3932f391`; their source and
operator files were not changed. Documentation checkpoints after the frozen
commit do not change the tested source or substitute their HEAD for this SHA.

**Local technical decision PASS; production promotion BLOCKED and unauthorized.**
Exact-source combined results: **797 backend / 40 Chrome / 34 source-native/Ollama
checks PASS, zero failures/skips**. Source/privacy, system and migration-drift
checks passed; no new migration. Earlier dependency changes remain explicitly
declared: Django 6.0.9 and removal of nine retired direct SDK requirements.
Evidence: `artifacts/release-gates/post-audit-quiescence-20261016/release.json`.

Actual M21 at `F:/ALFRED_DEV/post-audit-rehearsal-4aa7ac7/rehearsal.json` PASS:
authenticated encrypted local restore, typed financial/family reconciliation,
exact fast-forward, nine Chrome checks, restart/memory persistence, injected
worker crash, source rollback and nine after-rollback browser checks. The failure
child deliberately records FAIL with rollback PASS; the parent is PASS. The
older failed 874639f sandbox and all recovery evidence remain preserved. Test
servers on 8140/8150/8160 were closed. These are synthetic fixture-bound results,
not live-backup, real-account or device-loss acceptance.

Fresh portable package at `artifacts/releases/post-audit-4aa7ac7-28624710` PASS:
**35 packaged native checks including seven Chrome flows**, actual local Ollama,
encrypted memory, owner/deletion isolation, launcher, worker/scheduler, outage and
restart checks. Desktop Travel and mobile assistant screenshots were reviewed.
No ignored files existed under the packaged project-data directories; the bundle
inspector passed all 10,322 files. A second clean assembly in
`post-audit-4aa7ac7-repeat-fa68edd5` produced **identical paths and bytes for all
10,322 files**, including both executable hashes. This is same-host/same-SDK
repeatability; independent clean-PC installation is NOT_RUN.

The clean Python 3.12.10 SDK matched all 151 planned application packages; pip
and those packages were unchanged when five declared build-tool dependencies
were added. Pip check passed. The package directory contains hash-pinned inputs
for 156 distributions (154 wheels / two source archives), plus the bootstrap pip
version. Source-archive build-backend provenance is an additional independent
replay consideration. The 468,439,826-byte portable ZIP passed every entry's size
and SHA-256 comparison. It is an application archive, not a financial-data backup.
See [Windows package evidence](WINDOWS_PACKAGE.md).

M16 and M17 implementation are complete locally. M18 clean dependency/security
validation and M19 same-host portable/repeat-build acceptance PASS. M20 local
engine and M21 same-host rehearsal PASS; installer/clean-PC, normal-account,
independent archive/key/device-loss recovery, remote CI and branch protection
remain NOT_RUN. No new waiver or production authorization exists. The backup
adapter's default native-layout proof does not establish coverage of custom
external media/configuration paths; review coverage before any live operation.
Production ACL repair and dependency/runtime promotion remain separately gated.
The latest read-only check still could not reach `127.0.0.1:8000`; no startup,
shutdown, private DB access or repair was attempted.

Next: obtain the required installer/clean-PC environment and scoped CI/human
acceptance approvals, or continue the next independent confirmed roadmap item on
the development branch. Preserve the frozen source, all backups and the cancelled
key-dialog decision. Do not repeat completed P0/M16/M17/full local gates.

### Implementation checkpoint before the full gate — 2026-10-16

The clean SDK at `artifacts/post-audit/m18-clean-resolver-be31990d/venv`
passed **792 backend / 40 Chrome / 34 source-native/Ollama checks**, zero final
failures/skips, at exact source `874639f142f224255c6704d9c32409f79bb0bb73`.
The initial full browser failure, interrupted retry and later successful retry
remain recorded; the intermittent Banking error was not reproduced in the
40-test diagnostic run or completed normal retry. Its cause is unconfirmed.
The Travel preference loading/save race was independently reproduced and fixed.
Source/privacy, dependency policy and migration checks passed. Evidence:
`artifacts/release-gates/post-audit-clean-874639f/release.json`.

That source's actual M21 promotion, nine browser checks, local restore and restart
persistence passed, but worker-crash rollback was **BLOCKED/native_writer_running**.
Preserve `F:/ALFRED_DEV/post-audit-rehearsal-874639f/rehearsal.json` and its archives.
Recorded PIDs can remain alive briefly after clean shutdown or be reused; the
backup guard incorrectly treated them as proof of a writer. The correction uses
the existing supervisor/worker OS locks and SQLite write reservations throughout
capture. Active writers still block. Native shutdown now waits for both locks
after the stopped status is published and keeps its bounded failure result.

Reproductions: `writer-barrier-repro-4e872736` (14 tests, three errors) and
`shutdown-lock-repro-65f45f6e` (two tests, three failed subtest/assertion results),
under `artifacts/post-audit`. The backup-only correction passed 100 focused tests;
the complete shutdown/recovery correction passed **66 focused tests, zero skips
or failures** (`shutdown-recovery-fixed-4daa6f27/receipt.json`). These overlap and
are not summed. Changed implementation is in `alfred_native.py` and
`scripts/release_recovery.py`, with native/recovery regressions. No migration,
dependency, financial-value or production change. AST graph updated locally.

**Readiness at that checkpoint was BLOCKED.** The following work was pending then
and the verified local candidate above supersedes that pending state: a new pinned
full gate and actual M21 rehearsal before fresh packaging. M19 tools are staged;
Inno Setup is unavailable. Separate-PC/installer, normal-account, independent
device-loss recovery and remote CI acceptance remain unverified; no waiver is
inherited. A read-only check on 2026-10-15 found port 8000 unreachable; no service
action was taken. Production source/operator files remained unchanged.

### Earlier frozen critical-fix evidence

**Frozen source: b162c8fb2c43b357e840c3a298d06ffa4bed3251.**
753 backend tests, 37 Chrome tests and 34 source-native/Ollama checks PASS,
zero failures/skips. Actual M21 exact promotion, nine browser checks, restart/
encrypted memory persistence, independent local restore, typed financial/family
reconciliation, injected worker crash and source rollback PASS. Evidence:
artifacts/release-gates/post-audit-critical-b162c8f/release.json and
F:/ALFRED_DEV/post-audit-rehearsal-b162c8f/rehearsal.json. The failure-injection
child report deliberately records FAIL with rollback PASS; the parent rehearsal
is PASS. No database was overwritten by source rollback. All recovery assets
and failed earlier evidence remain. Screenshots reviewed at the preceding
3a46e1c equivalent UI gate; current Chrome gate also PASS.

At that frozen source M20 technical decision was PASS; production promotion
remained BLOCKED and unauthorized. The latest correction above needs its own gate.
Off-device copy/key/device-loss restore, fresh package, normal account, separate
PC, installer, remote Git/CI and branch protection are NOT_RUN. Source-native
checks are not a frozen executable proof. The M15 HDD waiver is not inherited.
P0 fixes and Django 6.0.9 are development-only; live ACL repair/deployment need
separate authorization. Newer M16 source progress is recorded below.

M16/T09 request retention is now implemented in development: configurable 7-day
non-network/90-day network history, current UTC quota windows preserved, active
attempts deferred, bounded oldest-first batches, dry-run CLI and shared 15-minute
source/native scheduling. Saved plans/evidence, owners, expenses, balances, cache
results and provider state are not cleanup targets. Full backups retain telemetry;
post-start canonical reconciliation excludes only the expiring request table.
**156 focused Travel/worker/recovery/promotion tests PASS, zero skips; system and
migration drift PASS** (artifacts/post-audit/m16-integration-a065eaeb/receipt.json).
These overlap prior tests and are not added to 753. This extension is after the
frozen critical candidate; its full combined/package gate has not run.
M16 retention and selective-refresh implementation is now COMPLETE in isolated
development. Category-scoped jobs reuse unrelated fresh/expired caches without
network calls, preserve provenance and quota/lease guards, prioritize the latest
web topic and selected location, and supersede older incompatible jobs. Date
edits invalidate candidate/itinerary forecasts, offers, quote snapshots and old
research banners while retaining independent route/place evidence. Same-length
date shifts retain edited days/allowances; changed duration requires schedule and
budget review. Plan/session changes are atomic on invalidation failure.
**196 targeted backend tests / 5 Chrome workflows PASS, zero failures/skips;
system and migration drift PASS.** Receipts:
artifacts/post-audit/m16-verified-d421da86/receipt.json and
artifacts/post-audit/m16-final-chrome-56feb12f/receipt.json.
Desktop/mobile screenshots were reviewed; changed-dates-no-old-forecast.png
shows the corrected date warning. No migration or dependency was added.
Initial reproduced failures and two corrected synthetic fixture failures are
retained in selective-refresh-repro-072cd2a5, date-invalidation-repro-28a7f490,
m16-selective-integration-8ecbf0b8 and m16-final-contract-3f61f4cd. The latter
rollback assertion needed a DB reload after save_plan's confirmed-state write;
safe class/frame diagnosis is in m16-rollback-diagnostic-865c4715. The initial
Chrome pass also exposed an old banner claim, corrected before final acceptance.
Counts overlap earlier checks and are never added together. Exact source pin and
limited gate scope: artifacts/release-gates/post-audit-m16-selective/release.json.
Full combined/native/package release gates are NOT_RUN for this newer source.
Next scoped unit after M16 was M17; its completed implementation is recorded below.
Implementation commit d66ce9904e560ade110ccf41be210eedc6f7b7e8 also passed exact
source/privacy/dependency/migration preflight and nine targeted retention tests
(artifacts/release-gates/post-audit-m16-d66ce99/release.json). Its full backend,
browser and native gates correctly remain NOT_RUN; the targeted success is not
transferred into a release PASS.

M17 cleanup is COMPLETE in development. The unrouted self-improve package
(missing patch generator, eager GPT-2 pipelines and production-root scanner),
SelfImproveAPI and orphan Google speech/gTTS voice prototype were retired from
source/package module inventory. Their preserved M15 history is linked from the
audit/matrix; no working AI Council or voice feature is claimed. Supported hybrid
reasoning, encrypted memory, registry and consented training remain.
Legacy interactive Gmail/Outlook setup, plaintext CWD token writer, unreachable
Gmail transport and counter-only fake auto-import method were removed. Existing
encrypted EmailConnection models and historical token/recovery files are untouched.
The IMAP portfolio service retains inline attachment parsing; standalone refetch
is explicitly unsupported. Each import gets its own connection, with a deterministic
two-owner concurrency regression. Connection/scan/cleanup failures use existing
safe diagnostic references/classification, never raw server/credential contents;
logout is attempted even after close fails.
**114 focused backend tests PASS, zero skips/failures; system/drift PASS**:
artifacts/post-audit/m17-integration-2bf509e2/receipt.json. This includes seven new
retirement/privacy/isolation checks, supported mail/ML/training/reasoning, finance,
auth and source-native boundary checks. Six original failures are retained in
m17-repro-d0730c23; the intermediate six-test pass is m17-fixed-240a62d7.
Pinned source/privacy/targeted scope:
artifacts/release-gates/post-audit-m17-cleanup/release.json.
No migration/dependency/provider activation; new full/native/package gates NOT_RUN.
Real mail/account/provider acceptance is still pending. No production remediation
or deployment is inferred. Next: M18 clean dependency reproducibility, then M19
fresh native package; reuse constraints/package tooling and do not repeat P0/M15.

Exact implementation pins: M16 3344ce21588dcaf41eb7655579cd978142c5fee2;
M17 86947a62e78359a5a62a51dacbcbbe2d3a3f484e. Both source/privacy/dependency/
migration preflights and targeted CLI runs passed; full newer-source release
gates remain NOT_RUN. M16/M17 documentation checks passed for 12 changed documents,
986 local links and seven archived-source links verified against preserved Git
blobs (artifacts/post-audit/m16-m17-doc-links-8971b1d4/receipt.json).

M18 is IN PROGRESS. Nine unused direct OAuth/voice SDK requirements were removed
after caller/import verification; supported ML/OCR/financial packages and the
historical Windows constraint snapshot remain. A fresh disposable resolver passed
with 151 packages/no conflicts/no retired direct requirements:
artifacts/post-audit/m18-clean-resolver-be31990d/receipt.json. Django startup and
URL checks also passed with retired SDK imports blocked
(artifacts/post-audit/m18-no-retired-sdks-eaa4689f/receipt.json). Resolution is not
an installed-runtime proof. The subsequent clean installation PASS exactly matched
all 151 planned packages; pip check, isolated Django 6.0.9, system/drift PASS with
no baseline fallback (m18-clean-resolver-be31990d/installation-receipt.json).
No production SDK changed.

The pinned 5f6bb76 clean-SDK full gate passed **792 backend tests/zero skips**,
then failed Chrome (38 executed, one error in quick-ideas/preferences). Correct
fail-fast left native/Ollama NOT_RUN; it is not a release PASS:
artifacts/release-gates/post-audit-clean-5f6bb76/release.json. The isolated original
test passed, but a deterministic delayed-read reproduction proved that an old
initial GET could erase a successful preference save from the UI while the DB
retained it (preferences-read-stages-cf247671/diagnostic.json). Both new loading/
outage regressions failed before correction (preferences-loading-repro-1010ed2d).
Travel preferences now use a disabled fieldset until loading completes, serialize
saves, expose aria-busy/status and retain disabled privacy controls after a failed
initial read. Both script callers use v2 assets. APIs/auth/CSRF are unchanged.
**Seven clean-SDK Chrome workflows PASS, zero skips/failures**, including delayed
GET/PATCH and load failure; mobile/error screenshots reviewed; JS syntax PASS:
artifacts/post-audit/preferences-loading-fixed-45eabf1a/receipt.json.
The corrected 874639f candidate received the combined and failed rollback results
recorded above; its later shutdown/recovery correction needs a new gate.
M19 PyInstaller 6.22.3 and declared tool wheels are staged
with hashes at artifacts/post-audit/m19-build-tools-3b6aacd1/receipt.json; not
installed during validation. Inno Setup is unavailable in checked PATH/standard/
registered locations, as already documented historically. Fresh portable package,
installer lifecycle and external/real-account recovery acceptance remain pending.

### Earlier development evidence (preserved; current result above supersedes pending actions)

Latest pinned integration: **3a46e1cb24234c586a40be446501a83c48cce2ea — 751 backend,
37 Chrome and 34 source-native/Ollama checks PASS; zero failures/skips**. Isolated
pip check PASS (shared baseline libraries, not clean-install/package proof).
Evidence: artifacts/release-gates/post-audit-final-3a46e1c/release.json. Synthetic
dashboard/mobile Travel screenshots reviewed. Overall promotion remains BLOCKED.
Actual M21 in F:/ALFRED_DEV/post-audit-rehearsal-3a46e1c passed exact promotion,
nine browser checks, financial preservation and memory restart persistence, then
failed before worker-crash injection because its nested evidence directory did
not exist. Reproduced FileNotFoundError; sandbox approval now creates/verifies
that private directory before writing. 33 focused acceptance/promotion/recovery
tests PASS (artifacts/post-audit/m21-output-directory-2f27f838/receipt.json).
All failed evidence/backups remain; complete actual rollback acceptance is pending.

P0 temporary-file follow-up: uploads and both isolated OCR paths now create
private parent directories before opening document files. Tightening a file ACL
after creation alone cannot revoke an already-open read handle. The creation-time
regression reproduced all three gaps (temp-parent-repro-ee45ea20). Streamed files
retain Django's Windows-safe temporary wrapper; the first attempt using Python's
different sharing mode failed and is preserved (private-temp-parent-efce6af0).
Corrected **115 focused storage/upload/document/loan/finance tests PASS**, zero
skips (artifacts/post-audit/private-temp-fixed-900cdd22/receipt.json). Temporary
directories close with their files; OCR uses private scoped input and safe
classified errors, without raw cleanup paths. No production ACL/file change.

| Unit | Development status | Evidence / remaining acceptance |
| --- | --- | --- |
| P0-B profile money | Implemented: finite, bounded cent validation at API/form/model/ORM and Career scenario inputs; existing Float SQL schema/API numeric contract preserved | 47 combined focused tests PASS, zero skips; migration drift PASS; production not remediated |
| P0-C private media | Implemented: source/debug and native use the same owner-filtered handler; safe missing/permission response, public static assets separate | Same 47-test gate includes anonymous/invalid session/foreign owner/traversal/deletion/source/native tests; packaged/live acceptance pending |
| P0-A Windows storage | Implemented: native and source/debug SQLite/config/cache checks, private retained/streamed uploads, memory/parser/recovery protection; pinned quiesced repair/rollback | Native unit: 117 focused PASS, 11 overlapping CLI PASS, 18 native PASS. Source extension: 89 focused PASS, system/drift PASS. Production ACL repair remains approval-gated |
| P0-D M20 gates | Reused/merged existing 0052410 engine: ignored target file collisions fail before mutation; quoted JSON credentials fail with redacted findings | Both original failures reproduced; 70 focused gate/recovery/promotion/acceptance tests PASS; 13 overlapping incomplete-run/privacy tests PASS |
| AWS / replacement | AWS runtime provider removed; provisioning rejects before prompts/writes; historical flags report disabled. Old protocol is network-free test quarantine only | 86 focused memory/sync/UI tests PASS; 2 final decommission tests and SyntaxWarning-as-error compile PASS; neutral encryption/sync unchanged; R2 is an unimplemented candidate |
| M18 Django security patch | Development requirements and Windows constraints pinned to 6.0.9 | Separate development venv: 227 focused security/finance/upload/document tests PASS, zero skips; system/drift PASS; fresh browser/native/package gates pending |

Changed money/media files: apps/users/money.py, models.py, serializers.py, forms.py;
apps/career/serializers.py; alfred_ai/urls.py, native_views.py; new boundary/profile
tests. Test receipt: artifacts/post-audit/money-media-3570b592/receipt.json (local,
synthetic). First money test attempt exposed a test transaction/savepoint issue;
the fixture was corrected without weakening validation. Historical failed receipt
is preserved. No migration, financial record conversion or balance change.

Storage files: alfred_private_storage.py; alfred_native.py; local_config.py;
memory_key.py; bounded_parser.py; document_extraction.py; statement_import.py;
backup/verification/recovery scripts and synthetic permission fixtures.
Evidence: artifacts/post-audit/storage-final-f320dc9c/receipt.json (117 tests and
WAL/config/media backup fixture); storage-cli-0dc1fcd2/receipt.json (11 tests);
storage-native-final-7e6dbb9c/receipt.json (18 actual native checks). Earlier native
attempt reached 16 checks then refused inherited restored-directory permissions;
the guard now accepts exact owner/SYSTEM inheritance only from a verified private
ancestor. Its failed receipt is preserved. No source/debug database encryption,
portable-key verification or production ACL remediation is claimed.

M20 integration preserves its prior history and both recovery-verifier changes:
private scratch protection plus caller-selected scratch roots. Recovery fixtures
now create private directories before seeding synthetic data; the initial mixed
branch failure is retained under m20-focused-7e820d51. Fixed receipts:
artifacts/post-audit/m20-corrected-67461836/receipt.json and
m20-incomplete-d8fd4607/receipt.json. Zero/skipped successful runner output now
reports NOT_RUN and blocks readiness; an actual failing runner remains FAIL.
The source scanner retains exact path/value-hash exemptions for six reviewed
public synthetic identifiers, never a blanket test-file exception. New P0
regressions are included in the standard release backend gate. M20 full pinned
integration and actual M21 native rehearsal are still pending; production approval,
off-device/key recovery, real-account and external CI gates are not filled by tests.

M20 integration commit: 6045904824a86413396eac16d5b16d9464dcd2fa. Its actual
pinned preflight source/privacy/dependency/migration scope PASS is saved at
artifacts/release-gates/post-audit-m20-6045904/release.json. Overall readiness is
correctly BLOCKED on unexecuted technical/operational gates and approval.

Django 6.0.9 is the compatible 6.0 security patch dated 2026-10-06; it addresses
language/header parsing denial of service and additional scoped security fixes.
No framework major upgrade or schema change is included.
[Official release notes](https://docs.djangoproject.com/en/6.0/releases/6.0.9/).
Receipt: artifacts/post-audit/django609-focused-4084887b/receipt.json. The isolated
.venv supplies its own Django while sharing other baseline libraries read-only;
this is not a clean full dependency installation or reproducible package proof.
Production's interpreter and requirements remain unchanged. Broader dependency
maintenance and M19/clean-PC acceptance remain open.

AWS decommission changes: memory_cloud.py, memory API/status and sync command,
configure_memory_cloud.py, synthetic-only proof script and test fixture. No stored
profile/key is removed or rotated. Active provider documentation and the existing
master prompt/roadmap carry the explicit override; the 143 audit rows/history are
preserved. Receipts: artifacts/post-audit/aws-off-9cadde31/receipt.json (86 tests)
and aws-final-582984f8/receipt.json (two overlapping tests plus strict syntax check).
The documented regex warning was fixed in the quarantined fixture using raw
patterns; no AWS transport is imported by application runtime.

Non-AWS choice: R2 implementation candidate after official atomic CAS, token,
security/pricing/limits review. No adapter/account is activated. Private bucket
configuration proof and least-privilege verification must be resolved before an
implementation can claim readiness; no checkbox replaces that proof. Alternatives
and exact constraints are in the [provider register](ALFRED_EXTERNAL_INTEGRATIONS.md#non-aws-intelligence-storage-decision).
Real cloud, real OpenAI and device-loss recovery remain unaccepted/OFF.

Pinned 3b73d78916b4c5f545e8148ec0abcaee143855cd combined attempt:
**736 backend PASS / zero skips; 34 native/Ollama checks PASS; 36 of 37 Chrome
tests PASS, one Travel quick-ideas timeout.** Overall gate correctly FAIL, not
release-ready. The isolated failing browser test reran PASS without source changes
(travel-browser-debug-7812ac83); a whole browser retry is required, not a claimed
fix. Evidence: artifacts/release-gates/post-audit-integrated-3b73d78/release.json.
Loan/investment monetary screenshots reviewed; their captures were intentional
successful evidence, not additional browser failures.

Source storage extension closes a reproduced part of P0-A: ordinary source/debug
SQLite, retained media and streamed temporary uploads inherited broad fixture
permissions. Synthetic receipt: source-storage-repro-final-84402574. New checks
run before source SQLite/cache use or configuration reads; PrivateFileSystemStorage
and PrivateTemporaryUploadHandler protect data before payload writes. Static
assets stay separate. Existing unsafe directories/files fail for approved repair;
none are automatically changed. Receipt: artifacts/post-audit/source-storage-final-62f32718/receipt.json
(89 PASS / zero skips); system/drift PASS in source-storage-fixed-12c75b59.
The first upload fixture run failed because its intentionally shared media/temp
directory was broad; the disposable fixture is now protected before seeding.
No money, schema, provider, key or production change is included.

8978fe1 combined attempt retained: 744 backend executed, 26 failures/28 errors
from pre-existing broad shared media fixtures; 37 Chrome executed with one different
intermittent navigation error; 34 native/Ollama checks PASS. Overall FAIL remains.
The guard was not weakened. Corrected release environments now select a fresh
ALFRED_MEDIA_ROOT; source startup protects it before preview/document generation.
The shared M14F temp/media fixture is private before seeding. Standalone browser
runs use the same stripped, disposable environment instead of inheriting operator
DB/media/cloud settings. 150 focused document/loan/upload/financial tests PASS
(artifacts/post-audit/media-isolation-fixed-20c05611/receipt.json); 22 overlapping
runner/isolation/fail-fast tests PASS (runner-final-67f8460e). Backend/browser
failure stops subsequent expensive gates and leaves unexecuted gates NOT_RUN.

Pinned e4c66471e34a4eae14eb90a1bae3ce13577a5925 passed **747 backend / 37 Chrome /
34 native-Ollama checks**, zero failures/skips. Source/privacy/configuration/drift
PASS. Receipt: artifacts/release-gates/post-audit-isolated-e4c6647/release.json.
Actual M21 sandbox F:/ALFRED_DEV/post-audit-rehearsal-e4c6647 independently backed
up/restored synthetic data, booted the baseline and exercised fast-forward. It
then failed operator_file_changed_after_promotion because clean tracked checkpoint
source changes were incorrectly hashed as operator overlays. Authorized synthetic
source rollback PASS; data/configuration and all evidence/backups preserved.
This is a real M21 failure, not COMPLETE or real-account acceptance.

Correction: hash protected operator files only when the candidate does not change
them; clean tracked source advances normally, while dirty overlapping operator
edits and ignored-file collisions still block. CLI main/imports share GateError
identity so fixed errors stay actionable. 58 focused M20/promotion tests PASS
(artifacts/post-audit/m21-operator-fix-d24c0908/receipt.json); three overlapping
actual CLI boundary tests PASS (m21-cli-final-18f0f3fd). New candidate requires
fresh combined validation and a new disposable M21 rehearsal.

Pinned f79690a8c42eab6b2ae3182445af5002a87da6a8 retry executed 750 backend tests,
zero skips, with one error; browser/native correctly remained NOT_RUN. Evidence:
artifacts/release-gates/post-audit-m21-resume-f79690a/release.json. The earlier
post-audit-m21-f79690a attempt was interrupted before a final receipt, not PASS.
The redactor omitted setup/subtest failure headers; its reproduced regression
now retains test/class identifiers without parameter values or exception content.
15 runner tests PASS (failure-log-fix-49532b0a); 27 overlapping source/acceptance
tests PASS (m21-three-debug-296f6a15). These targeted results do not clear the
combined failure. Preserve all receipts; repeat the pinned combined gate, identify
any repeated error, then perform the new disposable M21 rehearsal.

The safe failure-header correction is committed at 3a46e1c. Its full rerun passed
as recorded above; the earlier one-error run did not reproduce, and is retained.
Next action: finish the private temporary-parent P0 follow-up under focused tests,
pin the corrected candidate and repeat actual M21 acceptance. No production action.
Specialized audit/runbooks and
historical results below remain reference material, not fresh acceptance.

**Current status — 2026-10-15:** M14/M15 consolidated source is deployed and GitHub master matches 3932f391aa4eed7b3200ad3b034f7991435e01e4. Dated release results are 619 backend/15 Chrome/35 native (overlapping packaged scope); this audit independently ran 86 focused tests, zero skips, plus isolated system/drift checks. Normal-account, real-provider, clean-PC and device-loss acceptance remain incomplete. Port 8000 did not respond during the audit; no service action was taken. M20 is unfinished separate development; M16–M19/M21 are not declared complete.

Use the [authoritative feature matrix](ALFRED_MASTER_FEATURE_MATRIX.md), [completion roadmap](ALFRED_COMPLETION_ROADMAP.md) and [acceptance plan](ALFRED_END_TO_END_ACCEPTANCE.md). The earlier progress narrative below is historical module detail, not proof of current production availability or comprehensive AI accuracy.

Final read-only observation: /health/live/ returned 200 on a runserver listener;
/health/native/ returned 404. No audit restart occurred. Actual DB/worker/native
readiness remains unconfirmed; the initial unavailable observation is historical.

The [completion audit](COMPLETION_AUDIT.md) records the current verification
results and remaining local/LAN runtime work. The sections below describe
implemented capabilities, not a guarantee of complete real-data coverage.

The [29 September travel release continuation](TRAVEL_RELEASE_VERIFICATION_20260929.md)
records the 1.1.0 preview packaging, current travel tests and local upgrade evidence.

The [28 September continuation](WINDOWS_TRAY_VERIFICATION_20260928.md) records
the current tray, branding, website, attribution and cleanup work.

The [27 September release verification](WINDOWS_PACKAGE_VERIFICATION_20260927.md)
records the previous installer/uninstaller, 407 passing backend tests and nine
passing Chrome workflows. All six installer lifecycle checks passed. The same
native executables passed the
[26 September runtime checks](WINDOWS_PACKAGE_VERIFICATION_20260926.md), including
23 packaged checks and a 24-user load test. Overnight attempts interrupted by
host restarts are retained separately. The supervisor restarts verification
after Windows sign-in; use its Status action for the current attempt and expected
finish. Completed overnight acceptance remains pending; 16 focused tests
passed for the observation and supervisor logic.

The active Windows runtime is [Waitress + Huey + SQLite](NATIVE_WINDOWS.md),
with a double-click launcher, persistent task queue, shared local cache and
standalone installer build. The [earlier recovery proof](NATIVE_RECOVERY_PROOF.md)
records the original SQLite snapshot/restore. Current native verification also
exercises real HTTP, worker execution, retries, restart and an isolated restore.
Docker/PostgreSQL/Redis/Celery remain an optional, separately unverified runtime.
The BIOS virtualization issue does not block native Windows operation.
The [native verification report](NATIVE_WINDOWS_VERIFICATION.md) records the
passing full suite, Chrome workflows, packaged OCR, worker/recovery tests and
preservation of the existing account data.

The [18 September hardening report](NATIVE_HARDENING_VERIFICATION.md) adds
durable job claims/recovery, post-reboot retention proof, 12 concurrent-user
checks, mobile and automated accessibility coverage, and project cleanup.
The separate-PC test, real overnight outcomes and independently checked model
accuracy remain open; the report links the fresh verification branch/CI run.

The [sample-user acceptance audit](USER_DATA_ACCEPTANCE.md) records an isolated
signup/API scenario, independently reconciled money totals, correction tests,
and browser checks of the finance pages. It also documents the calculation,
cache, validation and wording defects found and fixed in that pass.

## Completed So Far

### Dashboards and UI

- finance dashboards wired across major sections
- dedicated sign-up and sign-in entry points are now available for users
- expense financial-flow charts now switch between monthly, quarterly, and yearly aggregation
- centralized `/documents/` upload hub for statements, loan PDFs, vehicle files, service bills, resumes, and credit reports
- centralized `/documents/` upload hub now also includes diagnostics, low-confidence review queues, all-scope retry controls, and linked delete behavior for document-derived data
- multi-file upload handling across the document hub, expenses, loans, career, credit-report, and vehicle-service pages
- dedicated vehicle-service dashboard
- mobility dashboard for travel plans, logs, gallery, and heat map
- rebuilt/fixed behavioral page empty-state and duplicate-insight handling
- roadmap and completion tracking moved into a separate superuser-only project-details dashboard instead of the main dashboard
- project-details is now a live superuser operations console with internal-clock timestamps, evidence watchlists, ticket-routing counts, report-library rollups, and adaptive learning progress
- project-details learning progress now refreshes live through a dedicated JSON endpoint instead of only on full page loads
- project-details in-progress progress bars now bind to named learning tracks instead of sorted positions, preventing progress drift as module maturity changes
- live-refresh pages now use interaction guards and selective DOM updates so active forms and dropdowns are not torn down every second
- browser interaction coverage now has a dedicated Selenium runner, a CI browser workflow, separate local Chrome/Edge and CI Chrome `browser_regression_summary.json` proof records, and failure artifacts for screenshots, page HTML, metadata, and browser logs where supported
- heavy finance, mobility, bike-service, and career dashboard reads now use cache-aware materialized payloads keyed to data revisions
- investment summary, allocation, and growth reads now also use cache-aware materialized payloads keyed to portfolio revision
- deterministic staging traffic now exercises all 21 registered materialized cache namespaces and records hit/miss, TTL, generation latency, stale regeneration, revision, and invalidation proof without marking production cache maturity complete
- Project Details selects readiness checks for the active runtime; native Windows checks use Huey, while Celery worker/beat requirements apply to the optional Compose runtime
- the shared `tests/` package is now discoverable by default so the normal `manage.py test` command runs the suite instead of silently skipping it
- supported ML models now persist training state, run history, quality estimates, and freshness windows in the database
- supported ML models can train on the scheduled nightly cycle when consent, data and runtime gates pass; the native Windows runtime disables startup training
- project status now treats local/LAN hosting as the only active operating path; provider-specific deployment leftovers have been removed from tracked source, IDE metadata, artifacts, and local cached evidence

### Vehicle and Mobility

- upload-first vehicle documents
- service-log import from service bills and work notes
- manual service logging fallback
- imported and manual service logs are now summarized together so long-term vehicle history stays usable
- issue/fault reporting with probable cause, suggestion, and projected cost
- condition snapshots with score and condition assessment
- parts-and-performance impact guidance based on service history, condition state, and open issues
- structured service-log and vehicle-document payloads now use centralized merge helpers so partial updates do not drop nested parsed data
- multiple saved vehicle profiles with primary-vehicle behavior
- travel advisor with weather, offbeat suggestions, stay-budget guidance, and vehicle-readiness context
- the vehicle catalog now includes broader official manufacturer coverage and model guidance across Royal Enfield, Suzuki, Honda, TVS, Bajaj, Yamaha, Ather, Tata, Mahindra, Kia, and NEXA-backed entries
- the service dashboard now attaches model-specific maintenance highlights with proof links where the catalog has official references
- the official vehicle catalog now filters model choices by selected vehicle type before the user picks a catalog entry

### Data Verification

- document relevance checks against selected vehicle profiles
- source-aware evidence cache for external data
- freshness tracking and stale cleanup rules for external intelligence
- circuit-breaker-backed stale fallback when verified sources repeatedly fail
- scheduled background refresh for verified external evidence
- foreclosure documents are now checked against the selected loan before a close action is allowed
- chart paths were audited to keep live API-backed data or empty states instead of user-facing demo/report widgets
- document parsers now share a layered extraction engine for PDF text, layout, table flattening, repaired-PDF fallback, and OCR retries
- parser-learning memory now adapts statement, loan-document, loan-closure-document, investment-document, recruiter/JD-document, credit-report, vehicle-document, and resume confidence from repeated uploads, accepted corrections, and retry outcomes
- operational diagnostics now persist document-processing failures, metadata-only saves, retry outcomes, and client-side visualization issues with timestamps and payload context
- recommendation and tax advisory outputs now expose freshness-backed evidence blocks and explicit grounding notes instead of opaque summaries
- investment guidance now exposes verified market and macro proof, freshness metadata, and materialized portfolio payloads
- relationship alignment now exposes factors, grounding notes, and freshness-backed proof instead of a fixed placeholder score
- verified external job feeds now filter blocked cloud-provider skill tokens before storing career evidence, and prior matching local cached job-evidence rows were purged

### Risk and Career

- career projection now uses macro context instead of a fixed placeholder growth rate
- career now shows dated risk-taking windows for job switches, promotion asks, skill upgrades, and side-income moves
- risk outlook now blends user-entered risk snapshots with macro context, market signals, financial pressure, behavioral pressure, and vehicle readiness
- related risk news is now consolidated under Risk Radar instead of being split across multiple module views
- resume uploads are parsed into role/skills/experience signals across broader formats including html, rtf, odt, and image-based CV uploads
- resume parser learning memory is now stored per user so parser adaptation does not leak across users
- pasted job links are analyzed for fit score, missing skills, and market risk
- recruiter mail and JD intake can now be parsed into the same career-fit pipeline, including optional attachment extraction
- study recommendations are now generated from experience stage, latest skill gaps, and live opening signals
- compensation benchmark summaries are now derived when salary-bearing evidence exists in job pages or recruiter/JD intake
- public job parsing now has deeper adapters for JSON-LD pages plus Greenhouse and Lever style openings
- layoff news and suggested openings are pulled from live configured internet sources with evidence
- scanned/image CV uploads now fall into review state instead of breaking the upload flow when OCR is unavailable on the server
- credit score surfaces now distinguish internal estimates from official bureau pulls instead of saving fake bureau pulls as real scores
- relationship alignment is now grounded in partner inputs, user cash-flow pressure, verified planning context, and a bounded optional relationship-model blend

### Expense Import Integrity

- statement intake now supports bank, credit-card, loan, investment, and other statement kinds
- parser status, confidence, and extracted payload are retained even when transaction extraction is incomplete
- account-scoped transaction fingerprints now reduce duplicate statement imports
- same-account repeated uploads are skipped more reliably
- similar transactions on different bank accounts are preserved instead of being deduped incorrectly
- mixed-overlap statement imports now keep new rows even when duplicate rows share the same reference and amount
- malformed or truncated statement PDFs now degrade to a stored review item instead of crashing the import flow
- structurally broken statement PDFs that still contain page objects can now be rebuilt to salvage metadata before they fall back to review
- structurally broken statement PDFs can now also fall through an isolated OCR worker to recover holder/account/period metadata even when the in-process OCR runtime is unhealthy
- metadata-only statement uploads now remain visible in the expenses workspace and central document hub with parser notes and recovered header details
- low-confidence statement uploads now queue deeper background retries instead of staying permanently dead-ended after the first pass
- repaired broken bank PDFs can now import partial OCR-preview transactions immediately, keep page-progress metadata on the upload, and continue deeper retries in the background for the remaining pages
- accepted corrections on partial or metadata-only statements now force a deeper retry window so OCR-recoverable uploads can populate expenses after review instead of only saving header fixes
- imported loan-like statement entries are now matched against the active loan book with confidence and review flags
- assets and liabilities are now surfaced in the expense intelligence view, including vehicle classification based on usage and utility

### Loans And Support Workflow

- active loans can now be consolidated into a new loan record while source loans are marked prepaid
- loan foreclosure now requires an uploaded closure or no-due document
- loan PDF imports now expose detected document type and parse confidence for sanction letters, statements, and repayment schedules
- uploaded loan PDFs are now saved as first-class import records, even when the parse is weak and only a review item can be created
- manual user ticket creation is no longer part of the normal user flow
- Alfred can auto-create summarized tickets when loan matching is low-confidence or a closure document is rejected
- low and medium severity tickets are now auto-handled by ALFRED, while high severity is escalated to superuser developers
- reports and ticket-routing visibility are now superuser-only
- the central document hub now exposes retry controls for statement, loan, vehicle, resume, and credit-report items instead of statement-only retry
- the central document hub now also supports review, correction, retry, and parser-learning feedback for loan-closure, investment-import, and recruiter/JD intake documents
- accepted corrections for invoice-style vehicle documents now update linked service-record fields such as service date, workshop, odometer, cost, and work summary instead of stopping at the document shell
- the document hub and expense intake now keep recent upload stacks scrollable and capped to the latest 10 visible cards per panel so the page height stays stable as history grows
- unresolved retries now create internal retry tickets keyed to the retry count, so ALFRED can auto-handle lower-severity parsing failures and escalate exhausted cases to developers
- parser-confidence calibration is now a trainable ML path that learns from parser outcome history instead of relying only on static confidence heuristics
- relationship-model training is now a safe, bounded path that only activates when enough scored partner profiles exist

## Pending acceptance

- Clean second-PC installation and reboot acceptance. Installer, host-reboot retention and backup/restore checks have passed on the development PC.
- Full overnight scheduled refresh, cleanup and eligible-training outcomes. The September 18 report was interrupted after 4.1344 hours; it is not an active or passing observation.
- More independently checked documents and model outcomes, with enough consenting data to pass quality and freshness gates. The September 25 comparison passed 68 checked fields across three private documents.
- Manual screen-reader testing and heavier real usage. Nine Chrome workflows and a 24-user/480-write synthetic load check passed; the three newly found dropdown-label issues are fixed and included in packaged verification.
- A real Windows sign-in check. Current-user startup registration succeeded on September 25 and remains registered.

See the [September 25 continuation](ACCEPTANCE_20260925.md),
[standalone package guide](WINDOWS_PACKAGE.md) and
[completion audit](COMPLETION_AUDIT.md) for acceptance conditions and dated
evidence. The earlier Windows/Chrome CI proof is dated September 18; current
continuation checks are local.

## Optional extensions

- LAN access and live email/bureau integrations, with the required account access and consent.
- More vehicle catalog models, job sources and geography coverage, informed by real usage.
- Additional model families and richer career/market/risk guidance after current models have sufficient validation evidence.

The [future scope](FUTURE_SCOPE.md) records broader product ideas. Public/cloud
deployment requires a separate explicit decision and is outside current scope.

## Risks Remaining

- browser-only issues can still exist where no driver-backed Selenium pass was recorded; normal test runs still skip browser tests unless `ALFRED_RUN_BROWSER_TESTS=true`, and full UI maturity still needs repeated no-skip browser summaries from both local and CI jobs
- selective fragment refresh now prevents most interaction resets, but any remaining page that still swaps whole DOM blocks in-browser could regress until it gets the same treatment
- some external sources are authoritative APIs, but market data still relies on Yahoo Finance
- multiple-vehicle support is structurally improved, but some naming remains bike-centric in code paths for backward compatibility
- job-link parsing is robust for many public pages, but some portals can still block direct fetches or hide content behind script/runtime layers
- project-details is now dynamic from live operational data, but it is still not generated from a formal release registry
- large-data hardening has deterministic staging proof for all registered cache namespaces, but production maturity still requires shared-cache telemetry under realistic concurrency and payload volume
- public-production readiness remains inactive and decision-gated; native Waitress/Huey/SQLite with a shared disk cache is the active Windows path, and Docker/PostgreSQL/Redis/Celery is an optional alternative
- balance-sheet vehicle classification is heuristic and should still be reviewed against real ownership/use patterns where the financial treatment matters
- auto-training is now safe and stateful, but several modules still remain heuristic, placeholder, or data-poor and should not be treated as fully learned systems yet
- parser adaptation is materially stronger now, but "all document types without fail" is still not a truthful guarantee for arbitrary or severely degraded files
