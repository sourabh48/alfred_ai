# M15 encrypted cloud adapter pre-connection record

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
