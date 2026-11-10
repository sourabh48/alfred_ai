# Execution decisions

## 2026-11-11 - stream saved local general conversations

- NEXT selects USE-03/saved-general-streaming from the existing authorized usability
  ledger. Original queue items retain owner/external/dependency blockers; no original
  requirement or whole capability is promoted by this bounded prerequisite exception.
- Share AlfredPersonalInsightsAPI.answer between its ordinary POST and the saved
  stream worker. Reuse current prepare/context/append/replay, local streaming,
  source revalidation and UI lifecycle. No parallel financial or conversation engine.
- Only local general chat gains saved streaming. History fields are complete/typed;
  client page-context injection, domain streaming and cloud consent remain rejected.
  Operator availability and owner retention consent remain off unless already chosen.
- The existing append transaction gains an optional cancellation/session check
  before processing and after its SQL write, allowing rollback before commit. Stop
  cannot undo a completed commit; the UI warns of a possibly saved completed turn.
  Same-request replay recovers it without another inference or duplicate turn.
- Retain existing 30-second deadline, output/context limits, model digest guards,
  figure/source buffering, owner boundaries and no automatic fact promotion.
- NO_UPSTREAM_ADOPTION. Existing Django/vault/JavaScript services are reused; no new
  dependency/schema, MCP service, paid provider, runtime activation or external action.

## 2026-11-11 - private saved-message search

- NEXT selects USE-03/private-message-search from the existing authorized usability
  ledger. Canonical queue entries remain blocked by their actual recorded gates;
  no original requirement or whole conversation capability is promoted.
- Reuse ConversationHistory.list and the authenticated MemoryAPI lifecycle. Explicit
  POST search scans at most 50 encrypted conversations/20 turns each, using literal
  case-insensitive matching and a 128-character phrase. No model, fuzzy/semantic
  index, transcript excerpts, extra persistence, schema or dependency is needed.
- Return all owned metadata plus match flags, so nonmatching current conversations
  do not appear deleted. Existing UI/history lifecycle preserves draft, expiry,
  active revision conflicts and permission-loss clearing. Recheck both session and
  consent after reading; invalid/corrupt records fail closed without replacement.
- The 261-test receipt remains bound to b60d809. Later commits change only a browser
  timing assertion; final d1ba657 has its own 53 focused and six Chrome receipts.
  No CI check is transferred between SHAs, and tests overlap rather than add counts.
- NO_UPSTREAM_ADOPTION. Existing vault/Django/JavaScript behavior is reused; no MCP,
  provider activation, private-history availability change or external action.

## 2026-11-11 - independent page-only questions during history outage

- USE-03/history-outage-page-only-sources is the single selected NEXT task; continue
  finishes it. The usability exception fixes a reproduced UI blocker in existing
  source paths; baseline approval/external-evidence gates are unchanged.
- Career progress and reviewed records from one document already avoid conversation
  storage at the API boundary. Their UI source readiness must not depend on a history
  status object. Other modes still wait for known status and unresolved saved
  conversation conflicts still require reopening. Server ownership, revisions,
  consent, session and financial validation are unchanged.
- Retry history status reuses the existing authenticated metadata GET and history
  request lifecycle. It retains drafts and retention choices, clears cloud consent,
  and cannot clear a conflict on an active saved conversation. Permission loss
  still clears private page contents. No vault/key repair or activation is performed.
- NO_UPSTREAM_ADOPTION. No new service, schema, dependency, model/provider, MCP
  transport, financial calculation or personal-runtime write is introduced.

## 2026-11-11 - reviewed Career timeline recovery

- NEXT selects USE-02/career-history-recovery under the authorized usability
  milestone. This later-phase prerequisite exception unblocks manual recovery of
  existing records; earlier baseline approval/external-evidence gates are unchanged.
- NO_UPSTREAM_ADOPTION. Reuse the existing Career application tracker and its MIT
  Career Ops attribution/pin4df3d0525a0a466f6b08928a7c3bd23946cb410f; no upstream
  component/runtime/license changes or second calculation/scheduling engine.
- Recovery starts an explicitly owner-reported stage/date timeline; it does not
  fabricate or silently repair historical dates. Exact original application JSON
  and unrelated opportunity fields remain private in the owned canonical record.
  Earlier follow-ups stay archived and do not count in the new timeline.
- Reuse existing action identity, keyed fingerprint, expiry and SQLite-first-write
  claim conventions. The Career adapter binds owner/target/exact fields/full source
  revision; ten-minute expiry, cancellation, atomic archive/write/receipt and single-use
  idempotent retry prevent stale or repeated canonical changes. Audit payloads are
  redacted fingerprints/status/times, never raw histories, resumes or personal dates.
- Source views are authenticated/no-store/session-rechecked; untrusted JSON is inert
  text. Inspect original before preview, then explicit confirmation. No model,
  provider, external message, new key, schema/dependency or personal-runtime change.
- Bounds:16KiB current timeline,128KiB retained review envelope, five archives and
  twenty pending reviews per ten minutes. Unsupported data remains intact; no pruning.

## 2026-11-11 - Career follow-up integrity repair

- NEXT selects one bounded usability repair, USE-04/career-follow-up-integrity,
  after reproducible missing-date guesses and malformed-history read failures.
  Earlier queue entries remain approval/external-evidence blocked. This later-phase
  exception repairs existing services, not AI-12/15/16 or parent Career acceptance.
- NO_UPSTREAM_ADOPTION. Existing application_tracker cadence and Career Ops MIT
  attribution/pin4df3d0525a0a466f6b08928a7c3bd23946cb410f are retained. Independently
  validate source history rather than adding another scheduling/calculation engine.
- Shared validation owns dates/shapes/chronology/current-stage consistency. Reads
  return unavailable instead of inventing dates or failing the entire opportunity
  list. The assistant's duplicate guard is removed in favor of this same service.
- Invalid histories remain unchanged; updates reject with a generic review message.
  UI shows affected records and pauses their edits, while valid records remain
  usable. Historical correction needs a separate reviewed recovery flow; do not
  silently discard raw histories or initialize fresh personal records.
- Valid explicit edits preserve existing provenance fields. No schema/dependency,
  model/provider/credential, sending, owner-runtime or financial-policy changes.

## 2026-11-11 - recorded Career progress in the assistant

- NEXT selects exactly USE-04/career-application-progress under the authorized
  usability milestone. Earlier queue gates are unchanged. This prerequisite
  exception connects existing deterministic services only; AI-12/15/16, Career
  quality, owner/package/provider acceptance and original143/13 counts are not promoted.
- NO_UPSTREAM_ADOPTION. Reuse ALFRED's application_tracker unchanged, including its
  Career Ops MIT attribution/pin4df3d0525a0a466f6b08928a7c3bd23946cb410f.
  No upstream code/dependency/runtime was imported; matrix/architecture boundaries stand.
- Career profile auto-syncs unreviewed extraction. Exclude it rather than presenting
  it as verified personal facts. Read only owned saved application reports; no
  salary, contacts, raw resume/JD, private job URLs, provider calls or canonical writes.
- Use the existing stage/timing service, but require recorded valid stage dates:
  its legacy missing-date fallback must not become assistant evidence. Malformed
  dates remain unavailable. Bound the scan to300 and recent details to3, with
  explicit omission counts. A valid saved stage does not prove external submission.
- Revalidate owned snapshots before returning. Career is page-only even with
  history enabled, uses no model/vault and rechecks the current session before/after.
  No new schema, calculation engine, paid API or application MCP server is introduced.

## 2026-11-11 - bounded local read registry

- Resume the explicitly selected usability task; earlier canonical queue acceptance
  still needs owner/provider/package evidence. Original143/13-extension counts unchanged.
- Wrap existing source_context adapters, retaining canonical services and post-model
  source revalidation. Typed fields generate the advertised schemas. Model/document
  text cannot select/register tools or override the authenticated owner.
- Catalogue is authenticated, metadata-only and private/no-store. No execution API,
  MCP transport, new remote server, credential, planner or financial write introduced.
- Five-second deadline rejects late validated results without forcibly interrupting
  SQLite/file reads. Audit logs contain fixed tool ID/outcome/time, no owner/payload.
- NO_UPSTREAM_ADOPTION for this scope. Existing reference matrix/license boundaries
  and canonical Decimal behavior preserved; no second financial/travel engine.

## 2026-11-10 - typed financial display only

A source classification cannot turn every numeric metadata field into money.
Identifiers stay scalar text; monetary display uses the existing exact typed amount
block and recorded currency, without changing currency or valuation policy. Known
limitation strings use text-node lists; model/document HTML remains inert. Static
review headings describe a review rather than asserting no save after an uncertain
network reply. No upstream code adopted or new calculation engine introduced.

## 2026-11-10 - source cards survive local inference failure

A supported canonical question may recover from EmbeddingUnavailable using only
current owner-scoped source cards after the same source revalidation. This does
not accept failed model prose, introduce calculations, infer currency, bypass
source selection/session checks, use cloud fallback or persist a turn. Normal
successful inference behavior stays intact. No upstream adoption or second engine.

## 2026-11-10 - existing action safety before further tool expansion

- The existing savings-goal action was already reachable. Reproduced financial-write
  flaws justify this bounded USE-05 exception before full USE-04 expansion; earlier
  queue items still need owner/provider/package evidence. No baseline acceptance added.
- Reuse OperationalLog as the redacted server proposal/receipt, with keyed payload
  and exact goal revision bindings. No plaintext request/amount/name is logged, no
  cache-dependent claim or new schema. Public audit serialization excludes bindings/IDs.
- Claim and canonical Decimal write share one database transaction, with first-write
  serialization for SQLite. Replay returns the outcome without reapplying changes.
  Cancellation is persisted, and ambiguous network errors never claim nothing saved.
- No upstream component adopted in this scope. Existing reference matrix boundaries
  and canonical engines preserved. New tools/actions, application MCP connections,
  real-account/independent/package/release/3.0 gates remain unaccepted.

- 2026-11-10 `next`: selected USE-03 safe answer formatting while earlier baseline
  queue items still require owner/provider/package evidence. No baseline acceptance
  is inferred from this separate usability slice; one task only.
- Reuse the current final/historical renderTurn and raw answer for speech/memory/
  encrypted history. A small DOM-only formatter supports headings, emphasis, inline/
  fenced code, flat lists, quotes and simple pipe tables. No HTML parsing, executable
  links/images, external requests, dependency or alternate UI/backend introduced.
- Model URLs/HTML and identifiers preserve literal characters; verified source-card
  links remain the sole citation controls. Questions/previews/withheld narratives
  and deterministic financial cards retain their current rendering/authority.
- Limit structural formatting to existing 8192-byte answer, 512 lines and simple
  tables of 2-12 columns/at most 100 data rows. Irregular/oversized tables fall back
  to text. No claim of full CommonMark, nested syntax or syntax highlighting.

-2026-11-10 continuation: reuse OllamaReasoner/hybrid_answer for bounded page-only
 streaming. No second reasoning/financial engine. Native Waitress remains four
 threads; at most two transient inference workers/eight queued frames each. The
 same30s deadline, fixed loopback model/digest checks,8192 context/4096byte supplied
 context/8192byte answer apply. No schema/dependency or owner runtime change.
- Stop/disconnect closes the active local socket; cancellation never becomes cloud
 fallback. Preview lacks figures/number words/currency and is suppressed for
 financial dialogue or owned-source context. Final hybrid revalidation and narrative
 guard decide acceptance; partial output has no save/promotion/citation controls.
- Saved-history, domain and public-fallback requests retain the existing complete
 path. Streaming endpoint rejects those inputs and never appends transcripts. The
 shared financial/currency regexes are reused without changing their final verdicts.
- Current `continue` completes one bounded task and stops READY_FOR_NEXT. No next
 task was selected and no agent was launched. Baseline/extension acceptance unchanged.

- Sprint2026-11-10 completed four local slices without changing the canonical
  baseline: guided readinessa78096e, answer budgetsb535299, conversation controls
  a173b3e and page dialoguec365a38. No new store, schema or dependency introduced.
- Recent page dialogue is ephemeral, unverified local general-chat context. It is
  bounded to three pairs/768bytes per message/4096byte model payload and cleared on
  new/page lifecycle. It cannot mix with saved history or financial scope, and is
  omitted from consented cloud fallback. Transcript retention remains opt-in.
- Rename reuses encrypted records and keys, increments the existing revision and
  preserves original expiry/turns. Concurrent/stale changes are rejected. Title
  search filters the existing bounded owned list in-page; no plaintext index or
  search URL/log is introduced. Full transcript search is not implemented.
- Context handoff after final checks is CODEX_TO_CLAUDE_READY. No automation has
  launched Claude, no independent audit occurred, and final/release readiness stays NO.

2026-11-09 owner instruction authorizes a continuous scoped 2.0 sprint, then 3.0
only after 2.0 acceptance and required release/branch approvals. It supersedes
stop-after-one-task selection for this active execution; safety gates remain.

- Existing Django/DRF/Waitress/Huey/SQLite/JavaScript/Ollama architecture retained.
- Canonical 143 requirements and 13 extensions retain their existing ledgers.
  These coordination files link them and do not create competing counts.
- Codex is the sole writer. Claude is a future handoff/final independent reviewer,
  not a launched concurrent agent. No external messages or review requests sent.
- Existing repository author identity from Git history is used via command-scoped
  configuration for authorized local commits; no invented identity/global changes.
- Work remains on the existing preparation branch. No master merge, installation,
  publication, new external service or private-data transmission is implied.
- Statement review will reuse existing upload JSON, parser, money/identity helpers
  and canonical posting services; no second ledger or unapproved schema migration.
- Statement source0f35605 makes extraction/retry preview-only. Confirmation binds
  the owned source revision and relevant account state, posts transactionally and
  returns a receipt on identical retry. Canonical fingerprint precision and cents
  remain unchanged. Source retention supersedes extraction-time automatic deletion
  for this reviewed statement flow; duplicate sources are retained. Confirmation
  does not approve separate loan postings/closures. Bounded local acceptance is not
  owner, packaged or parent capability acceptance.
- Host GitHub/IDE/browser capabilities may assist development. ALFRED application
  MCP connections require explicit source/permissions and never imply free data.

- 2026-11-10: actual continuation agent is Codex, not Claude. Exact expected branch/
  HEAD and sole dirty cache file verified; no concurrent CLI writer found or launched.
- Loan extraction/retry stages existing JSON, not new schema. Canonical LoanSerializer
  and loan_money validate confirmed new loans. Existing loans only receive source
  links, never document-driven field updates. Source-identity correction edits the
  draft; confirmed source deletion preserves canonical loans. No balance/date/tenure/
  currency guesses. Canonical monetary math and currency/valuation policy unchanged.
- Explicitly retain reviewed loan sources despite extraction cleanup settings.
  Single-use signed confirmation binds source bytes, candidate revision and current
  relevant loans; atomic compare-and-swap protects SQLite replay/concurrency. No new
  financial engine/dependencies/migrations. This is local source acceptance only.

- Consequential data-preservation follow-up took priority after investment tracing:
  reproduced legacy source removal deleting a confirmed loan; fixed the shared path
  to retain all canonical loans and updated the actual UI confirmation. Independent
  loan deletion remains in the existing loan controls. Sourcec2d1517 accepted locally.
- Context handoff remains Codex?Claude even though the owner's continuation prompt
  called the agent Claude: Codex executed and no automatic transfer was attempted.

-2026-11-10 continuation: reuse existing investment parser, source JSON/M2M,
  canonical InvestmentSerializer/investment_money and evidence capture. The existing
  bank/loan owner-confirmation pattern supplies bounded signed review. No new engine,
  schema, dependency, currency inference or upstream component adoption occurred.
- All investment import entry points prepare drafts, including the existing binary
  attachment caller. Existing holdings are link-only; editing a source cannot change
  a valuation or rename/delete a canonical holding. Existing holding-edit controls
  remain the deliberate route for those changes. Source retention supersedes automatic
  extraction cleanup for this reviewed flow.
- Positional amounts and inferred asset/rate fields require owner review, with
  unresolved currency/SIP left blank. Decimal text and negative signs are preserved;
  rounding and validation remain canonical. Source evidence is distinct from owner
  entry and issuer authentication.
- `continue` resumed and completed the recorded investment task. READY_FOR_NEXT is
  the resulting protocol state; no subsequent task or Claude launch was inferred.
