# M15 encrypted cloud adapter pre-connection record

**2026-10-15 architecture decision: AWS IS DECOMMISSIONED.** Do not execute the
historical provisioning/IAM/activation steps below. Post-audit development removes
the AWS provider from application runtime, disables its provisioning command
before any credential prompt, and ignores historical AWS activation flags/profile
data. Existing encrypted profiles and recovery assets are preserved. The legacy
wire adapter exists only in tests with a transport that refuses network access.
The neutral encrypted journal, snapshots, tombstones, queues and checkpoints remain.
Production M15 code is unchanged and real cloud remains OFF.

Cloudflare R2 is the selected **implementation candidate**, not an approved
account or active adapter. See the [non-AWS contract evaluation](ALFRED_EXTERNAL_INTEGRATIONS.md#non-aws-intelligence-storage-decision).
Private provider/account activation, permissions and portable recovery need
separate acceptance and authorization.

## Historical M15 evidence — superseded activation instructions

**Current pre-connection status — 2026-10-15:** Adapter source is deployed within 3932f391; no real AWS account/region/bucket acceptance is recorded and cloud stays OFF. Endpoint validation is AWS-specific, not arbitrary S3-compatible/Drive/Azure support. Initial synthetic results below are dated evidence. Portable key/checkpoint recovery remains pending; the historical M15 HDD waiver does not authorize private cloud use. [Provider register](ALFRED_EXTERNAL_INTEGRATIONS.md).

2026-10-11. Initial development provider: Amazon S3, configurable through the
existing provider-neutral synchronization protocol. No real account is connected,
no credentials have been supplied and no private/paid request has been made.
Mock remains supported; Azure/other providers are not implemented.

## Authorization and authentication

Real contact defaults OFF: `ALFRED_MEMORY_SYNC_PROVIDER` is empty and
`ALFRED_MEMORY_CLOUD_AUTHORIZED` is false. The legacy explicitly configured mock
directory still selects mock. An operator may provision one restricted profile
with `configure_memory_cloud --user <id> --bucket <bucket> --region <region>
--account <12-digit-owner>`, using an interactive terminal with masked prompts.
Credentials are stored in the existing encrypted owner vault, never arguments,
browser APIs, Git, provider logs or ambient AWS profiles/instance metadata.
Provisioning does not enable cloud contact or owner consent. Destination changes
after publication are refused; credential updates require synchronization OFF.
Temporary session credentials are supported and fail closed when expired.

Before enabling contact, obtain explicit user approval for the provider/account,
review restricted credentials and bucket policy, export the owner's sync key to
a separately approved portable recovery location, retain a trusted high-water
checkpoint, and verify restoration. Windows DPAPI alone is not device-loss
recovery. Existing M14 backups are preserved and their missing off-device export
is still PENDING. Do not enable private use merely because synthetic tests pass.

### Trusted fresh-vault recovery checkpoint

Fresh-vault downloads now require an independently retained, latest trusted
checkpoint as well as the recovered owner sync key. This closes authenticated
old-head replay after loss of the local revision history. Established vaults
continue using their existing high-water revision; lost upload responses may
acknowledge an exactly identical authenticated local snapshot.

Export is local, password-free and contains encrypted owner/revision/head metadata
only, never an encryption key, memory, embedding or credential. Pending edits,
deletions, expiration or conflicts must synchronize before export. From the
isolated M15 configuration, use:

```powershell
python manage.py memory_sync_checkpoint export --user <id> --file <absolute-checkpoint-file> --confirm
```

After restoring the SAME canonical account identity and its separately protected
owner key into an unused vault, import the latest independently trusted file:

```powershell
python manage.py memory_sync_checkpoint import --user <id> --file <absolute-checkpoint-file> --confirm
```

Neither command prompts for a password or contacts a provider. Export refuses
existing destination files. Import validates authenticity, schema, owner and
bounded size; it preserves existing data/keys/checkpoints and leaves sync consent
OFF. Explicit consent is still required before any subsequent download. Remote
revisions below the checkpoint and same-revision forks fail closed, including
explicit conflict recovery. Newer revisions must prove their bounded linked
history; deleted memories cannot return from an older cloud head. No API contract,
Django migration or financial model changes.

This checkpoint is NOT a backup of the owner key. Windows DPAPI-only keys still
need an approved, separately recoverable storage mechanism before device-loss
recovery/private cloud use. The latest trusted checkpoint must be retained outside
the provider's control. An older checkpoint cannot establish deletions made after
its export; old backups and offline recipients can still retain historical data.
M14 Desktop archive staging and current SQLite restoration are verified locally,
but separate-key/off-device recovery remains PENDING. The operator cancelled the
new passphrase workflow; do not prompt for it or claim sealing is complete.

## Encryption, ownership and permission review

TLS uses ALFRED's centralized public HTTPS transport: pinned validated public
DNS, original-host TLS verification, no proxies/cookies/redirects/ambient keys,
bounded DNS/socket reads and a shared five-second deadline. Signature V4 follows
the [AWS signing specification](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/sig-v4-header-based-auth.html)
and is checked against its public example. Only ordinary regional AWS S3 HTTPS
endpoints are constructed; custom URLs, access-point aliases and bucket dots are
refused. Every request requires the expected bucket-owner account.

ALFRED encrypts/authenticates records, snapshots and the current key manifest
before the network boundary; SSE-S3 AES256 additionally protects remote storage.
Paths contain only a hashed immutable owner, schema and ciphertext hash. The
adapter refuses another owner's prefix. Before access it requires all four S3
Public Access Block controls, BucketOwnerEnforced ownership and a bucket that
has NEVER enabled versioning. Suspended versioning is refused: old key manifests
could retain revoked record keys. Object-lock/head retention and external bucket
replication/backup policies must also be reviewed before authorization.

Restrict IAM Get/Put/DeleteObject to `alfred-memory-v1/<owner>/`, ListBucket to
that owner's snapshots prefix, and allow read-only GetBucketVersioning,
GetBucketPublicAccessBlock and GetBucketOwnershipControls. Deny non-TLS/public
access and configuration changes. Independently test that the credentials cannot
read/write sibling prefixes; client owner checks do not replace IAM. Verify no
other principals have unintended access. No bucket or cloud deployment wiring is
created by this source milestone.

## Costs, limits, conflicts and cancellation

Review [regional S3 pricing](https://aws.amazon.com/s3/pricing/) and a user-approved
storage/request/egress budget before connection; no universal price is assumed.
Each opted-in minute tick normally performs three bucket-control reads plus one
head read per processed owner; changes add object/head PUTs and history reads.
Maximum 16 rotating accounts/tick, five seconds shared (two seconds periodic),
32 MiB/object, 128 KiB encrypted manifest, 512 memories, 4096 journal events,
128 ancestors/64 MiB history and 4096 listing entries apply. Configure AWS billing
alarms/account limits separately; local request bounds cannot cap unrelated AWS
usage or provider price changes. This release makes no chargeable test call.

Local writes commit first. Existing encrypted retries/backoff survive startup,
offline operation, interruption and bounded shutdown after draining writers.
Startup/minute/shutdown use the same selected factory and opt-in protocol.
Immutable objects use If-None-Match; the current manifest uses ETag If-Match CAS,
following [AWS conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).
Lost acknowledgements are recognized; orphan objects from an interrupted upload
contain no record keys. Races/conflicting edits require explicit verified merge.
Downloads must pass SHA-256, authenticated encryption, owner/schema/version/
embedding validation and trusted history checks before index changes. Only changed
encrypted index entries are rewritten. No SQLite/WAL/SHM file is synchronized.

## Deletion and retention

Deletes/resets/expiry propagate authenticated tombstones and remove record keys
from the current non-versioned manifest; older snapshots contain ciphertext only.
Current replicas invalidate keys/indexes and cannot restore a revoked memory.
An offline replica with previously received keys is not instantly erased.

Explicit confirmed `sync` action `prune` first authenticates current ownership/
checkpoint and up to 128 ancestors. It retains the current plus 128 ancestors,
refuses dirty/conflicting/changing state, and removes at most 16 older, unreferenced
objects per five-second pass. Objects must predate owner retention AND the oldest
retained ancestor by at least one day. Missing legacy mock timestamps are treated
as current. A deadline/history/listing failure before removal preserves objects;
a later interruption leaves an idempotently resumable pass. No recovery backup
file is removed. Slow real-provider history may require a trusted newer checkpoint
or another maintenance pass; it never gets an unlimited shutdown deadline.

Historic backups, exported keys, recipient devices and provider copies may retain
deleted data until retention expires or relevant keys are securely retired. No
irreversible erasure is promised. Memory is supplementary knowledge, never the
authority for financial balances, loans or deterministic Django calculations.

## Synthetic verification

Signed S3 wire fixtures validate authentication, expected-owner header, encrypted
objects, conditional writes and SSE headers without any real AWS call. Tests cover
offline startup, interrupted/lost-ack uploads, duplicates, CAS/edit conflicts,
partial/corrupt downloads, unauthorized scope, tombstones/non-resurrection,
129-version retention, mock deletion guards and encrypted masked provisioning.
Focused gate: 73 PASS, 27.313 seconds. Final combined: 169 backend/3 Chrome PASS,
zero failures/skips. Real two-process Ollama through signed S3 fixtures restores
the same verified memory: 384 dimensions, score 0.518286, zero external calls.
Focused results and the final combined result are recorded in the continuation
checkpoint and F:/ALFRED_DEV/isolated-tests/m15-cloud-manifest.json after commit.
Real-provider permissions/costs/device-loss recovery remain awaiting authorization.

## Proposed AWS acceptance after explicit provider approval

2026-10-12 preparation only. AWS S3 is the existing adapter's supported real
provider, not a selected or authorized destination. No bucket, credentials, IAM
policy, cloud object or real request has been created by this preparation.
Use a dedicated private general-purpose bucket with no past versioning, all
four Public Access Block settings and BucketOwnerEnforced ownership. Review
Object Lock, replication, external backups and retention separately. Reject
those that can preserve old current key manifests without an accepted deletion
policy. Expected bucket-owner account, region, budget and destination must be
approved before provisioning. Do not reuse the private financial/recovery bucket.

The following IAM example is an uninstalled review template. Replace placeholders
only after selection; give each synthetic owner separate restricted credentials.
The action/resource split follows [AWS's S3 permission mapping](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html).

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect":"Allow","Action":["s3:GetBucketVersioning","s3:GetBucketPublicAccessBlock","s3:GetBucketOwnershipControls"],"Resource":"arn:aws:s3:::APPROVED_BUCKET"},
    {"Effect":"Allow","Action":"s3:ListBucket","Resource":"arn:aws:s3:::APPROVED_BUCKET","Condition":{"StringLike":{"s3:prefix":["alfred-memory-v1/OWNER_SHA256/snapshots/*"]}}},
    {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject"],"Resource":["arn:aws:s3:::APPROVED_BUCKET/alfred-memory-v1/OWNER_SHA256/head","arn:aws:s3:::APPROVED_BUCKET/alfred-memory-v1/OWNER_SHA256/snapshots/*"]},
    {"Effect":"Allow","Action":"s3:DeleteObject","Resource":"arn:aws:s3:::APPROVED_BUCKET/alfred-memory-v1/OWNER_SHA256/snapshots/*"},
    {"Effect":"Deny","Action":"s3:*","Resource":["arn:aws:s3:::APPROVED_BUCKET","arn:aws:s3:::APPROVED_BUCKET/*"],"Condition":{"Bool":{"aws:SecureTransport":"false"}}}
  ]
}
```

An operator must independently check effective permissions, including other
attached policies and bucket principals; this template is not proof of isolation.
With two pre-created synthetic namespaces, require owner A's credential to get,
put and delete A's test objects but receive authorization denial on B's known test
object/list/write/delete and on bucket configuration changes. Use an independent
AWS permission test; the adapter's client-side owner refusal is not an IAM test.
Do not treat missing-object 404 as evidence of authorization denial. Keep test
object names/content synthetic; never use real account or recovery identifiers.

Connection diagnostics use existing gates: masked local configure_memory_cloud
provisioning remains source-CLI only, encrypted owner profile, operator real-contact
authorization, explicit owner consent, and MemorySyncAPI status/result. Status GET
is local only; configured availability does not prove authentication or IAM.
After approval, the first bounded sync checks bucket controls/expected ownership
and authenticated head/schema/history. Record result/category/reference/revision/
pending/conflict only; no credentials, payloads, upstream bodies or HTTP wire logs.
An expired credential, wrong owner, invalid bucket control or failed signature
must preserve local state and fail closed. A credential failure must not trigger
provisioning/recovery/key rotation automatically. Packaged provisioning currently
requires the operator's source management CLI; no browser credential field exists.

Synthetic-only live acceptance, AFTER authorization and independent key recovery:

1. Create two isolated canonical synthetic accounts and separate owner profiles.
   Export/retain their approved recovery material and trusted checkpoint separately
   from the provider. Keep OpenAI disabled and all real financial data excluded.
2. Save one verified synthetic memory locally; consent to encrypted sync; run a
   bounded upload. Independently inspect that objects are ciphertext with AES256
   SSE and owned prefixes, never SQLite/WAL/SHM or document files.
3. Restart a second synthetic vault with the same account identity and independently
   recovered owner key/latest checkpoint. Enable download explicitly; authenticate
   and retrieve the same memory using local Ollama. Require owner B rejection.
4. Make an incremental local update and observe the next minute worker tick.
   Stop with a pending edit and verify bounded final upload or durable pending state.
5. Disconnect network, update/correct locally, restart offline and prove retention
   of encrypted pending changes. Reconnect and verify acknowledged publication.
6. Force two stale-head concurrent edits. Require conflict preservation and explicit
   confirmed recovery; no silent overwrite. Inject a truncated download/corrupt
   object and an interrupted/lost-ack upload; require no partial index mutation,
   correct retry/acknowledgement and unchanged local verified data.
7. Delete/reset/expire a memory and propagate tombstones. Reconcile a stale replica
   and old authenticated snapshot against the trusted checkpoint; require no
   resurrection. Test bounded explicit pruning only on synthetic objects.
8. Record exact lifecycle/ownership/recovery results, object/request counts and cost
   within the approved limit. Keep evidence and existing backups. Removing the
   synthetic test bucket/objects is a separate approved action, not automatic cleanup.

Current record: real provider AWAITING APPROVAL; synthetic wire/mock tests only.
Private cloud use and a production readiness claim remain blocked by real IAM/
cost/retention acceptance and separately recoverable keys/checkpoints.
