# ALFRED whole-project audit — 2026-10-15

## Executive decision

ALFRED has a deployed M15 finance/AI/UI baseline, not a fully accepted original product. Public main source and independently queried GitHub master both equal **3932f391aa4eed7b3200ad3b034f7991435e01e4**. The audit is isolated in **audit/alfred-master-completion-20261015**, at F:/ALFRED_DEV/alfred-master-audit. Application source was not changed by this audit.

The [143-feature matrix](../../docs/ALFRED_MASTER_FEATURE_MATRIX.md) is authoritative for bounded capability status: 61 COMPLETE_VERIFIED, 29 IMPLEMENTED_NOT_ACCEPTED, 34 PARTIALLY_IMPLEMENTED, 11 NOT_IMPLEMENTED, five BLOCKED_APPROVAL and three BLOCKED_EXTERNAL. These are inventory counts, not a percentage of product completion. COMPLETE_VERIFIED denotes technical scope with named evidence; it does not certify real-account, real-provider or model accuracy.

Priority findings are broad Windows read permissions on private DB/configuration, accepted nonfinite User income input, a subsequent Django security release and two reproducible failures in unfinished M20 gates. Initial port 8000/PID checks did not establish service health. A later read-only poll found a runserver listener, /health/live/ 200 and /health/native/ 404; runtime/database/worker identity is not re-established by that response. No start/stop, permission repair or DB mutation was performed.

M14 protections and the tested M15 memory/UI scope remain implemented. The next engineering work is targeted correctness/privacy remediation and completion of the existing M20 branch, followed by M21 acceptance. Broader Travel, AI-document and product gaps must follow bounded decisions rather than another redesign.

## Evidence boundary and methodology

- Read local instructions and checkpoint; used scoped Graphify navigation before source traces.
- Inventoried all public Python and tracked Markdown content, routes, imports, model fields/relationships, symbols and dependencies. [Inventory summary](master-audit-inventory-20261015/inventory-summary.json), [source index](master-audit-inventory-20261015/source-inventory.json) and [Markdown index](master-audit-inventory-20261015/markdown-inventory.json) retain public metadata, not runtime secrets.
- Traced root URL → domain URL → view → shared service → owner model or encrypted store → frontend callers. The matrix links concrete files/tests for every feature, including absent capability boundaries.
- Read migration history, provider implementations, model training/readiness paths, background tasks, native launcher/package/backup tooling, CI workflows and Git worktree ancestry.
- Reconciled dated release evidence with current source and current read-only runtime/remote observations.
- Executed isolated focused tests, an isolated serializer diagnostic and two generated-repository M20 reproductions. No real provider, paid model, private financial record or recovery-key content was used.
- Consulted current official OpenAI, Django and selected provider documentation. Contract/account-specific prices or quotas not verified are marked unverified in the [provider register](../../docs/ALFRED_EXTERNAL_INTEGRATIONS.md).
- All Markdown received full-content inventory/link scanning; project-owned active guides also received semantic/current-status reconciliation. Third-party/vendor and dated evidence bodies were preserved. This does not imply a new execution proof for every historical statement.
- Historical conversations outside this session are unavailable. The user restated A–M as audit scope; this is not blanket approval to activate integrations or implement every assistant proposal.

Static presence, AST syntax validity, a historical test, a fresh focused test, a mock provider, a real provider and a normal user's browser session are different evidence classes. They are never silently substituted.

## Source and worktree history

| Worktree/branch | Inspected HEAD | Relationship/status |
| --- | --- | --- |
| Main master | 3932f391aa4eed7b3200ad3b034f7991435e01e4 | M15 deployed source; fresh remote master matches |
| m15 / codex/m15-persistent-memory-20261011 | 03ab0aecdecda72dcb4db7866c46821e7c4264bf | Original frozen candidate preserved |
| m15-hardening | 081e30e1259936a0898798c89e7f30f76a0d500c | Hardened ancestor incorporated in integrated release |
| m15-ui | 75b6f50b4cb8561b2e1423d02516d8176f512316 | UI/freeze evidence incorporated in integrated release |
| m15-integrated | 3932f391aa4eed7b3200ad3b034f7991435e01e4 | Same exact deployed release; no duplicate merge needed |
| m20-release-gates / feature/m20-release-gates | 0052410bcc6726c6881713002902fd9c1ae7bc59 | Development only; incomplete acceptance and confirmed gate flaws |
| alfred-master-audit | Read actual HEAD | Documentation/diagnostics only, based on exact production source |

Main operator edits were present before the audit: continuation/promotion documents, skills-lock.json and four untracked deployment/restoration/acceptance documents. They were preserved and not imported wholesale into public source. Frozen candidates and all backups remain intact.

## Test/evidence ledger

| Evidence | Exact scope/source | Result | Limits |
| --- | --- | --- | --- |
| M15 integrated gate, 2026-10-14 | 3932f391; [frozen report](M15_INTEGRATED_RELEASE_20261014.md) | 619 backend, 15 Chrome, 35 native, including seven packaged Chrome | Dated exact-source evidence, not rerun/added together |
| Actual M15 deployment, 2026-10-15 | Local operator deployment report, inspected read-only | 21 HTTP/queue; 26 private-copy compatibility; 34 main-source native including seven Chrome | Separate overlapping checks; real-account visual acceptance pending |
| Fresh audit focused gate | Seven named test modules in [receipt](master-audit-inventory-20261015/focused-checks.json) | **86 PASS**, zero skips, 59.061s | Synthetic disposable DB; finance/family/hybrid/evidence/currency/session/tax scope |
| Fresh Django checks | Isolated audit runtime | system PASS; makemigrations --check --dry-run PASS | Not a current private DB schema query |
| Audit helper tests | tests/test_audit_project.py | Five PASS, 0.064s, including matrix/source/prompt coverage | Not product/browser/model acceptance |
| Public AST inventory | All inventoried Python | No syntax errors | Import/runtime correctness is separate |
| Package requirements | Configured Python 3.12 SDK metadata; pip check | No broken requirements | Not vulnerability or reproducibility certification |
| UserSerializer synthetic diagnostic | No database writes | monthly_income Infinity accepted; Budget rejects nonfinite input | Serializer-level reproduction, not a private API write |
| Source/debug media diagnostic | Disposable synthetic text file, DEBUG=true, non-native URL configuration | Anonymous response 200 | Native profile uses protected owner media; no real file or current production DEBUG setting tested |
| M20 focused evidence | Development HEAD 0052410 | Prior combined 65 PASS; later narrow checks overlap | Interrupted full validation has no final backend/browser/native result |
| M20 audit reproductions | Generated disposable Git repos only | Two gate failures reproduced | [Safe receipt](master-audit-inventory-20261015/m20-diagnostic-receipt.json); no real credentials |
| Current HTTP/native service | Read-only localhost checks | Initial unavailable/stored PIDs absent; later /health/live/ 200, /health/native/ 404 with runserver listener | Native DB/worker identity and sustained readiness unconfirmed; no service action |
| Remote master | Fresh git ls-remote | Exact 3932f391 match | No push; a Pages CI result is not application CI |
| Real providers, new browser/package/native runs | Audit session | NOT_RUN | No approval or need for a repeat full M15 gate |
| Device-loss recovery | HDD user report/M15 waiver | UNVERIFIED | Checksums/current-profile decryptability are insufficient |

Final counts/checksums and documentation validation are recorded in the [audit continuation](ALFRED_MASTER_AUDIT_CONTINUATION.md). Historical counts above must not be summed.

## Confirmed findings

### AUD-01 — broad filesystem read grants (HIGH, operational privacy)

Read-only Get-Acl found Allow ReadData for S-1-5-11 (Authenticated Users) and S-1-5-32-545 (local Users) on the live db.sqlite3 and runtime config/native.env and config/local.env, with inheritance enabled and no matching broad deny. A read of only the database format header confirmed plaintext SQLite. No record or secret value was inspected.

Impact: another account with these effective grants can potentially read financial data/configuration. This is a local filesystem boundary, not a demonstrated remote authentication bypass. Memory encryption does not encrypt the canonical Django database.

Fix: separately authorized owner/SYSTEM-only ACL maintenance, include containing directories and durable queue/media/key files; preserve owner/service access and ACL rollback. Review volume encryption as device-theft protection. Regressions: synthetic Windows ACL tests, service-account access, other-account denial and restoration permissions. Never automate permission repair during an audit.

### AUD-02 — nonfinite personal income accepted (HIGH, correctness)

[UserSerializer](../../apps/users/serializers.py) uses DRF FloatField(min_value=0) without isfinite for monthly_income/variable_income/rent_or_emi. Synthetic partial validation accepts Infinity. [BudgetSerializer](../../apps/budgets/serializers.py) already rejects nonfinite values and must not be reopened as the same bug.

Impact: unsupported values can enter the personal finance boundary, risking invalid calculations/serialization. No actual private row corruption was demonstrated or observed.

Fix: shared or local finite-money validation at this User boundary and any confirmed remaining monetary inputs; 400/no mutation on NaN/±Infinity, exponent overflow and excessive values. Then scoped remaining Decimal migrations, with old/new snapshots and forward/reverse rehearsal. Do not mechanically convert rates/measurements.

### AUD-03 — subsequent Django security patch (HIGH priority dependency maintenance)

The deployed dependency is Django 6.0.8; official 6.0.9, released 2026-10-06, fixes security issues including quadratic header processing. Scope applicability must be traced; GeoDjango/formset-specific issues are not automatically ALFRED exploits. See [official release notes](https://docs.djangoproject.com/en/6.0/releases/6.0.9/).

Fix: M18 dependency follow-up in isolation, review requirements/Windows constraints and framework compatibility, security regressions and fresh package. Do not change the production environment automatically. Existing M01A was completed historically; a newer advisory is a new bounded maintenance task.

The inspected SDK also contains requests 2.31.0 and cryptography 43.0.3. Upstream
Requests advisories cover verify=False Session reuse and direct extract_zipped_paths
usage; neither pattern was found in the inspected application paths. New PyCA
advisories concern X.509 verification/path building, whereas ALFRED memory uses
Fernet; no application X.509 verification caller was found. These need version/
transitive build review, not invented proof of a current ALFRED exploit.
[Requests Session advisory](https://github.com/psf/requests/security/advisories/GHSA-9wx4-h78v-vm56),
[Requests ZIP utility advisory](https://github.com/psf/requests/security/advisories/GHSA-gc5v-m9x4-r6x2),
[PyCA path-building advisory](https://github.com/pyca/cryptography/security/advisories/GHSA-jwv3-5hgf-82ww),
[PyCA name-constraints advisory](https://github.com/pyca/cryptography/security/advisories/GHSA-m959-cc7f-wv43).

### AUD-04 — ignored operator file overwritten despite M20 PASS (HIGH, development gate)

At M20 HEAD 0052410, source_checks reports operators PASS when candidate begins tracking an ignored config/operator.local.json that exists as an untracked operator file in the target. Ordinary fast-forward overwrites it in a generated fixture.

Impact: unfinished deployment automation can destroy operator configuration despite a passing preservation gate.

Fix: enumerate candidate tracked path additions against every protected/untracked/ignored target collision, reject reparse/path aliases and preserve a captured operator manifest. Repeat source validation immediately before promotion. Regression must reproduce the ignored-file collision and confirm no source/data mutation.

### AUD-05 — M20 JSON credential classifier misses quoted token (HIGH, development gate)

A generated provider-profile.json containing a synthetic access_token passes privacy at M20 HEAD 0052410. The assignment regex does not recognize that quoted JSON structure/token name. No live secret is present in the receipt.

Fix: scan supported structured configurations and robust credential patterns with strict fixture-scoped exclusions; cover JSON/YAML/env, key aliases, binary/path limits and intermediate commits. Redact findings; never transmit source secrets to external scanners. The existing incomplete scan is not a privacy certification.

### AUD-06 — incomplete monetary/currency schema (MEDIUM/HIGH correctness)

Core Expense/BankAccount/Investment/Loan amounts use Decimal and migration evidence exists. Remaining money floats include User income/rent, Budget base_budget/inflation_adjusted/spent, CareerProfile.last_salary and Mobility service/fuel/budget/spend/projected cost/value/premium fields. Most finance models do not persist currency.

Fix: complete the existing remaining M13 domains first; explicit currency storage/backfill/FX policy is separately scoped. Preserve legacy INR convention and AI currency-not-recorded labels. Float display conversions are not by themselves proof that canonical Decimal posting is wrong.

### AUD-07 — persistent Travel request telemetry lacks cleanup (MEDIUM privacy/resource)

[Travel cache](../../apps/mobility/services/travel/cache.py) writes TravelProviderRequest on outcomes including cache/unavailable paths. No production cleanup was found. Quota queries need recent/current-month history; active/in-progress work must survive cleanup.

Fix: established T09/M16 configurable deterministic retention, aggregated quota evidence where needed, idempotence/restart/owner tests, then dependency-aware selective invalidation. Do not build an unrelated telemetry stack.

### AUD-08 — experimental self-improve and legacy mail dead ends (MEDIUM latent/maintenance)

Post-audit disposition: M17 retires these unsupported paths in development;
[PROJECT_STATUS.md](../../docs/PROJECT_STATUS.md) records verification and remaining
acceptance. The finding below preserves the original M15 source evidence.

[advanced_engine.py](https://github.com/sourabh48/alfred_ai/blob/3932f391aa4eed7b3200ad3b034f7991435e01e4/apps/ml_engine/self_improve/advanced_engine.py) imports nonexistent patch_generator. SelfImproveAPI is not routed. No working coding/review AI Council exists. [email_integration.py](../../apps/integrations/services/email_integration.py) has an unrouted legacy OAuth helper writing plaintext token JSON in CWD; no live token was found or helper executed.

Fix: M17 classify callers/package inclusion, quarantine/retire unneeded experiments or complete a separately approved workflow. Reuse encrypted EmailConnection/token rotation rather than the legacy writer. Do not infer current remote exposure from unreachable code.

### AUD-09 — runtime acceptance identity unconfirmed (MEDIUM operational acceptance)

Historical M15 deployment succeeded. Initial 8000/PID checks failed to establish
health; the final read-only observation found /health/live/ 200 and
/health/native/ 404 on a manage.py runserver listener. No audit start/restart
occurred. This is not proof of an outage now or of the intended restored-runtime
DB/worker/scheduler readiness. Establish actual source/config/data and writers in
an authorized operational acceptance task; don't start a second server blindly.

### AUD-10 — paid model lifecycle and recovery acceptance (MEDIUM/HIGH readiness)

Pinned gpt-4.1-mini-2025-04-14 has announced retirement on 2027-01-14. Real access is disabled, so no current paid outage was demonstrated. Independent off-device archive/key restore remains unverified; a DPAPI copy requires its original Windows context.

Fix: explicit model/provider choice with current rates and synthetic adapter contract tests before any approved paid request. Separately choose portable secure recovery without reopening cancelled passphrase dialogs. The historical waiver is not inherited by future releases. [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations).

### AUD-11 — unprotected source/debug media route (HIGH conditional privacy)

[Root URLs](../../alfred_ai/urls.py) use authenticated owner-filtered
[private_media](../../alfred_ai/native_views.py) when native mode is active, but
fall back to Django static media serving when non-native DEBUG is true.
Local source settings default DEBUG to LOCAL_RUNTIME. A disposable synthetic
file returned 200 to AnonymousUser through that route; [receipt](master-audit-inventory-20261015/source-debug-media-receipt.json).
No private file or actual live DEBUG/media configuration was queried. This proves
the source-profile boundary gap, not current private production disclosure.

Fix: reuse protected owner media handling across supported runtime profiles;
public static assets remain separate. Regression: anonymous/foreign-owner media
denied, owned supported documents accessible, paths/no-store and source/native
profile coverage. No schema change or automatic production configuration edit.
Native M14 ownership controls remain implemented; this is a distinct profile gap.

## Module conclusions

### Finance, liabilities and investments

Dashboard/cash flow/obligations/savings/net worth share the canonical financial baseline. Statement fingerprints and transfer treatment are account scoped; card payments/investments/transfers are not blindly counted as living spend. Reviewed document corrections/retries and loan payment reversal exist. Foreclosure and settlement allocations use Decimal/cents and evidence; closed loans do not remain active EMI liabilities.

No dedicated persistent savings-goal workflow or comprehensive multi-currency ledger was found. Forecasts, risk classes, portfolio watchlists, career timing and vehicle service predictions require explicit assumption/quality labels. Family growth already labels its 8% heuristic; do not reopen a resolved labeling claim. Financial export is distributed across reports/review, not one demonstrated comprehensive portable export.

Portfolio AMFI/Yahoo/history/news logic has evidence/cache paths, not universal current market knowledge. Uploaded bureau records and estimates are distinct; official live bureau integration requires approval/contracts.

### Documents and AI

The document center joins module-owned uploads, visual correction, retry, confidence and parser-learning feedback. OCR fallback and resources are bounded. It is not a universal semantic document knowledge base.

M15 local encrypted memory/index/journal, verified-vs-hypothesis separation, deduplication, semantic retrieval, corrections/tombstones, privacy and trusted checkpoint behavior are implemented. Hybrid tools read six finance baseline metrics, owner Travel preferences and verified closure projections. General assistant conversation history is UI-local; Travel messages are persistently modeled separately. Broad PDF/bank/investment/resume Q&A and safe autonomous mutation are not implemented.

Local model registry/training/orchestration, sample thresholds and freshness/quality gates exist. Synthetic quality thresholds do not prove general prediction accuracy, drift stability or sufficient genuine training outcomes. Sustained eligible cycles and reviewed chronological holdouts remain open. The old voice service is not a demonstrated user-facing integration.

### OpenAI and cloud intelligence

Public-only Responses adapter, encrypted provisioning, operator/owner/per-request gates, bounded time/output, strict model/usage validation and spending reservations exist. Private financial context remains local; paid access stays OFF. Current rates match existing reservations but the pinned model lifecycle requires a choice.

Mock/AWS synthetic encrypted sync supports local-first retry, lifecycle hooks, ownership, authenticity, conditional conflicts, tombstones/pruning and high-water checkpoints. It is memory sync, not raw database backup. Real AWS bucket/IAM/region/cost acceptance, multi-device recovery and portable key/checkpoint acceptance remain missing. No Azure/Google Drive/OneDrive intelligence adapter is established by source.

### Travel

Structured conversation, origin/preferences, dynamic destination discovery, day edits, forecasts, estimates, source freshness, route geometry and source-based research exist. Earlier static-only, unsafe HTTP, freshness and basic typed-pillion gaps were addressed; do not duplicate those fixes.

Large ranked pools/show-more, true alternate/scenic route requests, verified motorcycle restrictions, road-network detours/corridors, general multi-stop optimization and broader conversational reasoning are incomplete. Hotels/flights have disabled provider adapters; rail is contract/unavailable; buses are link-outs; permits are dated references. POIs/photos are not verified inventory, video ingestion or a public social profile. Mapping uses local geometry/Leaflet, not a comprehensive Google Maps or offline tile package.

### Career, family, behavior and mobility

Resume/manual recruiter intake, job-page/feed adapters, skill matching, opportunity outcome contracts and salary-bearing geography evidence exist. They do not prove universal location-specific coverage, recruiter-mail automation, calibrated career forecasting or an interactive interview coach.

Family relationships/financial opt-in/revocation/throttles are implemented. The deployed migration reset historical sharing OFF; memories/documents do not inherit sharing. Relationship/behavior/risk blend canonical and entered evidence with heuristics; no clinically validated or universally predictive accuracy is established.

Vehicle profiles/catalog include Hunter 350 support, service/fuel/documents/conditions, Travel wear and net-worth integration. Current manufacturer intervals, part compatibility and actual vehicle outcomes require acceptance. Mobility money remains part of the FloatField tail.

### Windows, performance and release

Native launcher/tray/durable queue/scheduler, isolated data directories, packaged assets/fonts and controlled shutdown/restart were historically tested. Fresh-PC installer lifecycle, actual Windows sign-in, long observation and normal account acceptance remain open. No new native/browser/package run was needed for a documentation-only audit.

Materialized cache contracts and historical synthetic high-volume/concurrency evidence exist; these are not a current production performance/SLO or multi-user throughput guarantee. CI has manual/PR browser/native coverage; the observed Pages run does not prove M15 application CI or required branch protections. M20/M21 tooling is separate unfinished development and now has confirmed failure cases.

## Requirements and completion policy

Read the [roadmap](../../docs/ALFRED_COMPLETION_ROADMAP.md), [external integration register](../../docs/ALFRED_EXTERNAL_INTEGRATIONS.md), [acceptance plan](../../docs/ALFRED_END_TO_END_ACCEPTANCE.md) and [executable master prompt](ALFRED_MASTER_COMPLETION_CODEX_PROMPT.md).

Full product completion requires owner-approved scope, bounded technical completion, actual normal-account acceptance, calibrated claimed AI behavior, current provider permissions/acceptance where claimed, clean-PC install/upgrade/recovery and an exact approved release. Optional providers can remain disabled only if the product explicitly communicates that limitation; they cannot be described as completed live capabilities.

Production, private database, recovery assets, keys and remote master were not changed. No credentials, private rows or encrypted-memory contents are included in this report.
